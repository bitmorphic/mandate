"""
MANDATE — Governed Demo (Day 2)

Demonstrates the multi-agent code review pipeline WITH governance.

This is the "after" scenario — the exact same pipeline, same vulnerability,
same security agent behavior, but now with MANDATE enforcing authority:

    Security Agent → finds vulnerability → decides to fix it →
    requests WRITE → MANDATE checks scope → WRITE NOT AUTHORIZED → BLOCKED

The repository remains protected. The agent had the capability but not
the authority. The audit trail records the decision.

"We don't tell agents what not to do. We make it impossible for them
to exceed their authority."
"""

import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from demo.fixture.setup_fixture import setup_test_repo, teardown_test_repo
from coordinator.main import run_review
from tools.git_ops import run_git


def main():
    print()
    print("=" * 65)
    print("  MANDATE — GOVERNED DEMO")
    print("  Demonstrating governance: same agent, same capability,")
    print("  but now constrained by AUTHORITY.")
    print("=" * 65)
    print()

    # ─── Setup: Create deterministic test repository ────────────────
    print("Setting up test repository with vulnerable code...")
    repo_path = setup_test_repo()
    print(f"  Repository: {repo_path}")
    print(f"  Branch: feature/add-user-system")
    print()

    # Show initial state
    _, log_before, _ = run_git(["log", "--oneline"], cwd=repo_path)
    print("  Git history BEFORE review:")
    for line in log_before.splitlines():
        print(f"    {line}")
    print()

    # ─── Run the GOVERNED pipeline ──────────────────────────────────
    try:
        result = run_review(
            repo_path=repo_path,
            base_branch="main",
            governed=True,  # ← GOVERNANCE ENABLED
        )
    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return

    # ─── Verify the repository is PROTECTED ─────────────────────────
    print()
    print("=" * 65)
    print("  GOVERNANCE VERIFICATION")
    print("=" * 65)
    print()

    _, log_after, _ = run_git(["log", "--oneline"], cwd=repo_path)
    print("  Git history AFTER review:")
    for line in log_after.splitlines():
        print(f"    {line}")
    print()

    commits_before = len(log_before.splitlines())
    commits_after = len(log_after.splitlines())
    new_commits = commits_after - commits_before

    if new_commits == 0:
        print("  ✅ ZERO new commits. The repository is PROTECTED.")
        print()
        print("  The security agent had the CAPABILITY to write.")
        print("  But MANDATE enforced its AUTHORITY boundary.")
        print("  The unauthorized write was BLOCKED.")
        print()
        print("  'We don't rely on the agent promising not to do something.")
        print("   The authority boundary makes the unauthorized action impossible.'")
    else:
        print(f"  ⚠️  {new_commits} new commits — governance may not have worked correctly.")

    print()
    print("=" * 65)
    print("  GOVERNED DEMO COMPLETE")
    print("=" * 65)
    print()

    # ─── Comparison summary ─────────────────────────────────────────
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │  BEFORE vs AFTER                                    │")
    print("  ├──────────────────────────────────────────────────────┤")
    print("  │  UNGOVERNED: Agent writes → commit created → ⚠️     │")
    print("  │  GOVERNED:   Agent writes → BLOCKED by scope → 🛡️   │")
    print("  │                                                      │")
    print("  │  Same agent. Same capability. Different authority.   │")
    print("  └──────────────────────────────────────────────────────┘")
    print()

    print(f"  Test repository preserved at: {repo_path}")
    print()

    return result


if __name__ == "__main__":
    main()
