"""
MANDATE — Coordinator Agent

The coordinator receives a review request and delegates work to three
genuinely independent sub-agents:

    COORDINATOR
        ├── LINTER AGENT      (separate process)
        ├── SECURITY AGENT    (separate process)
        └── PERFORMANCE AGENT (separate process)

Each agent runs as its own subprocess with its own identity.
The coordinator collects and aggregates their findings.

In Day 1 (ungoverned): agents can do whatever they're capable of.
In Day 2 (governed): agents are constrained to their delegated authority.
"""

import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from governance.identity import (
    create_all_identities,
    display_identities,
    verify_identity_independence,
)
from governance.audit import AuditTrail
from governance.authority import GovernanceManager
from tools.git_ops import list_changed_files, get_current_branch


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Agent subprocess entry points
AGENT_MODULES = {
    "linter": os.path.join(PROJECT_ROOT, "agents", "linter", "agent.py"),
    "security": os.path.join(PROJECT_ROOT, "agents", "security", "agent.py"),
    "performance": os.path.join(PROJECT_ROOT, "agents", "performance", "agent.py"),
}


def run_agent_subprocess(
    agent_name: str,
    repo_path: str,
    changed_files: List[str],
    governed: bool = False,
    token_data: Optional[dict] = None,
    base_branch: str = "main",
) -> dict:
    """Run an agent as a genuinely separate subprocess.

    This is NOT a function call within the same process.
    Each agent is spawned as its own Python process with its own identity.
    """
    agent_module = AGENT_MODULES[agent_name]

    task = {
        "repo_path": repo_path,
        "changed_files": changed_files,
        "governed": governed,
        "token_data": token_data,
        "base_branch": base_branch,
    }

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, agent_module],
            input=json.dumps(task),
            capture_output=True,
            text=True,
            timeout=120,
            cwd=PROJECT_ROOT,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        # Print agent logs (sent to stderr) for the demo display
        if result.stderr:
            for log_line in result.stderr.strip().splitlines():
                print(log_line)

        if result.returncode != 0 and not (result.stdout or "").strip():
            # Agent process truly failed (no output at all)
            return {
                "agent_id": f"mandate-{agent_name}",
                "agent_role": agent_name,
                "status": "error",
                "error": (result.stderr or "")[:500] or "Unknown error",
                "findings": [],
                "actions_taken": [],
            }

        # Parse the agent's JSON output from stdout (clean, no log lines)
        raw_stdout = result.stdout or ""
        stdout_lines = raw_stdout.strip().split("\n")
        json_line = stdout_lines[-1]  # Last line should be the JSON result

        try:
            return json.loads(json_line)
        except json.JSONDecodeError:
            # Try to find JSON in output
            for line in reversed(stdout_lines):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
            return {
                "agent_id": f"mandate-{agent_name}",
                "agent_role": agent_name,
                "status": "error",
                "error": f"Could not parse agent output",
                "findings": [],
                "actions_taken": [],
                "raw_stdout": result.stdout[:500],
            }

    except subprocess.TimeoutExpired:
        return {
            "agent_id": f"mandate-{agent_name}",
            "agent_role": agent_name,
            "status": "timeout",
            "error": "Agent timed out after 120 seconds",
            "findings": [],
            "actions_taken": [],
        }


def run_review(
    repo_path: str,
    base_branch: str = "main",
    governed: bool = False,
) -> dict:
    """Run the full MANDATE code review pipeline.

    1. Create identities for all agents
    2. Get changed files from the PR branch
    3. Spawn each agent as an independent subprocess
    4. Collect and aggregate findings
    5. Display results and audit trail
    """
    mode = "GOVERNED" if governed else "UNGOVERNED"

    print()
    print("=" * 65)
    print("  ███╗   ███╗ █████╗ ███╗   ██╗██████╗  █████╗ ████████╗███████╗")
    print("  ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝")
    print("  ██╔████╔██║███████║██╔██╗ ██║██║  ██║███████║   ██║   █████╗  ")
    print("  ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██╔══██║   ██║   ██╔══╝  ")
    print("  ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝██║  ██║   ██║   ███████╗")
    print("  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝")
    print()
    print("  Autonomous AI. Governed by Authority.")
    print(f"  Mode: {mode}")
    print("=" * 65)
    print()

    audit = AuditTrail()

    # ─── Step 1: Create agent identities ────────────────────────────
    print("┌─ PHASE 1: Agent Identity Registry")
    identities = create_all_identities()
    verify_identity_independence(identities)
    print(display_identities(identities))
    
    # Initialize governance if governed
    governance = None
    if governed:
        governance = GovernanceManager(identities["coordinator"], is_coordinator=True)
        # Create the root plan encompassing all authorized scopes for the sub-agents
        # This defines the maximum authority envelope for the entire review task
        all_scopes = set()
        for agent_name in ["linter", "security", "performance"]:
            all_scopes.update(identities[agent_name].scopes)
            
        tool_calls = [{"name": scope, "arguments": "{}"} for scope in all_scopes]
        
        print("  ┌─ Minting root intent token for Code Review task")
        root_token = governance.capture_and_mint_token(
            goal="Code Review Pipeline", 
            steps=tool_calls
        )
        print(f"  │  Token ID: {root_token.token_id}")
        print("  └─ ✓")
        print()

    # ─── Step 2: Get changed files ──────────────────────────────────
    print("┌─ PHASE 2: Analyzing Pull Request")
    current_branch = get_current_branch(repo_path)
    print(f"  Repository: {repo_path}")
    print(f"  Branch: {current_branch}")
    print(f"  Base: {base_branch}")

    changed = list_changed_files(repo_path, base_branch)
    changed_files = [e.filepath for e in changed]
    print(f"  Changed files: {len(changed_files)}")
    for f in changed_files:
        print(f"    • {f}")
    print()

    # ─── Step 3: Delegate and run agents ────────────────────────────
    print("┌─ PHASE 3: Delegating to Sub-Agents")
    print("  Each agent runs as an INDEPENDENT SUBPROCESS.")
    print()

    results = {}
    for agent_name in ["linter", "security", "performance"]:
        identity = identities[agent_name]
        print(f"  ┌─ Spawning {agent_name.upper()} agent")
        print(f"  │  PID: (separate process)")
        print(f"  │  Identity: {identity.fingerprint}")
        print(f"  │  Scopes: {', '.join(identity.scopes)}")
        
        token_data = None
        if governed:
            # Delegate a subtree to the sub-agent
            print(f"  │  Delegating subtree token...")
            sub_token = governance.delegate_to_agent(
                target_agent=identity
            )
            token_data = sub_token.model_dump()
            print(f"  │  Delegated token ID: {sub_token.token_id}")
            
        print(f"  │")

        # Record delegation in audit trail
        audit.record_delegation(
            coordinator_id=identities["coordinator"].agent_id,
            agent_id=identity.agent_id,
            agent_role=identity.agent_role,
            scopes=identity.scopes,
        )

        # Run agent as separate subprocess
        start_time = time.time()
        agent_result = run_agent_subprocess(
            agent_name,
            repo_path,
            changed_files=changed_files,
            governed=governed,
            token_data=token_data,
            base_branch=base_branch,
        )
        elapsed = time.time() - start_time

        results[agent_name] = agent_result

        # Display results
        status = agent_result.get("status", "unknown")
        findings_count = len(agent_result.get("findings", []))
        actions = agent_result.get("actions_taken", [])

        status_icon = {"completed": "✅", "error": "❌", "timeout": "⏰"}.get(status, "❓")

        print(f"  │  Status: {status_icon} {status} ({elapsed:.1f}s)")
        print(f"  │  Findings: {findings_count}")

        for action in actions:
            action_status = action.get("status", "unknown")
            action_icon = "🛡️" if action_status == "BLOCKED" else (
                "⚠️" if action_status == "EXECUTED" else "•"
            )
            print(f"  │  Action: {action_icon} {action.get('action')} → {action_status}")

            # Record in audit trail
            decision = "BLOCK" if action_status == "BLOCKED" else "ALLOW"
            audit.record_tool_request(
                agent_id=agent_result.get("agent_id", f"mandate-{agent_name}"),
                agent_role=agent_name,
                tool=action.get("action", "unknown"),
                action=action.get("action", "unknown"),
                scopes=agent_result.get("scopes", []),
                decision=decision,
                reason=action.get("reason", f"Action {action_status}"),
                details=action,
            )

        if agent_result.get("error"):
            print(f"  │  Error: {agent_result['error'][:100]}")

        print(f"  └─ {agent_name.upper()} complete")
        print()

    # ─── Step 4: Aggregation ────────────────────────────────────────
    print("┌─ PHASE 4: Aggregated Review Results")
    print("│")

    total_findings = 0
    for agent_name, result in results.items():
        findings = result.get("findings", [])
        total_findings += len(findings)
        print(f"  │  {agent_name.upper()}: {len(findings)} findings")

    print(f"  │")
    print(f"  │  Total findings: {total_findings}")

    # Check for blocked actions (the critical demo evidence)
    blocked_actions = []
    executed_writes = []
    for agent_name, result in results.items():
        for action in result.get("actions_taken", []):
            if action.get("status") == "BLOCKED":
                blocked_actions.append((agent_name, action))
            elif action.get("action") == "WRITE_FILE" and action.get("status") == "EXECUTED":
                executed_writes.append((agent_name, action))

    print(f"  │")
    if executed_writes:
        print(f"  │  ⚠️  UNAUTHORIZED WRITES EXECUTED: {len(executed_writes)}")
        for agent_name, action in executed_writes:
            commit = action.get("commit_hash", "unknown")[:12]
            print(f"  │     {agent_name}: commit {commit}")
        print(f"  │  ⚠️  THE REPOSITORY WAS MUTATED WITHOUT AUTHORITY!")
    elif blocked_actions:
        print(f"  │  🛡️  UNAUTHORIZED WRITES BLOCKED: {len(blocked_actions)}")
        for agent_name, action in blocked_actions:
            print(f"  │     {agent_name}: {action.get('reason', 'blocked by policy')}")
        print(f"  │  ✅  THE REPOSITORY IS PROTECTED.")
    else:
        print(f"  │  No write attempts recorded.")

    print(f"  │")
    print("  └─ Review complete")
    print()

    # ─── Step 5: Audit trail ────────────────────────────────────────
    print(audit.display())

    # ─── Step 6: Verify identities are distinct ─────────────────────
    print()
    print("┌─ IDENTITY VERIFICATION")
    all_keys = set()
    for agent_name, result in results.items():
        pk = result.get("public_key", "")
        fp = result.get("fingerprint", "")
        if pk:
            assert pk not in all_keys, f"IDENTITY VIOLATION: {agent_name} shares a key!"
            all_keys.add(pk)
        print(f"  │  {agent_name}: {fp}")
    coordinator_pk = identities["coordinator"].public_key_hex
    assert coordinator_pk not in all_keys, "Coordinator shares a key with a sub-agent!"
    print(f"  │  coordinator: {identities['coordinator'].fingerprint}")
    print(f"  │")
    print(f"  │  All {len(all_keys) + 1} agents have DISTINCT identities ✓")
    print("  └─")
    print()

    return {
        "mode": mode,
        "results": results,
        "audit": audit.get_events(),
        "blocked_actions": len(blocked_actions),
        "executed_writes": len(executed_writes),
        "total_findings": total_findings,
    }
