"""
MANDATE — Security Agent

THE CRITICAL DEMO AGENT.

This agent:
1. Runs semgrep (real security scanner) on changed files
2. Finds real vulnerabilities
3. Reasons that it can fix the vulnerability
4. ATTEMPTS REMEDIATION (file write + commit)

The remediation attempt is the core of the MANDATE demo:
- Without governance: the write succeeds, real commit created
- With MANDATE: the write is BLOCKED because the security agent
  was only delegated READ + SCAN + COMMENT authority

CAPABILITY ≠ AUTHORITY
The agent CAN request a write. But it should not be AUTHORIZED to write.

Authorized scopes: READ_DIFF, RUN_SECURITY_SCAN, POST_COMMENT
NOT authorized: WRITE_FILE, CREATE_COMMIT, PUSH, MERGE, DEPLOY
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.base import BaseAgent, AgentResult
from tools.security_scan import run_semgrep, format_findings
from tools.remediation import apply_remediation, generate_fix
from tools.git_ops import get_file_content


class SecurityAgent(BaseAgent):
    """Security agent — runs real semgrep analysis and attempts remediation."""

    def __init__(self, governed: bool = False):
        super().__init__(
            agent_id="mandate-security",
            agent_role="security",
            scopes=["READ_DIFF", "RUN_SECURITY_SCAN", "POST_COMMENT"],
            governed=governed,
        )

    def run(self, repo_path: str, changed_files: list) -> AgentResult:
        """Run security analysis and attempt remediation of findings."""
        self.log("Starting security analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        self.log(f"Scanning {len(py_files)} Python files for vulnerabilities...")

        # Step 2: Run security scan (authorized)
        if not self.check_authority("RUN_SECURITY_SCAN"):
            self.log("❌ Not authorized to run security scan")
            return self.get_result()

        findings = run_semgrep(repo_path, py_files)
        self.log(f"Found {len(findings)} security issues")

        for f in findings:
            self.add_finding({"tool": "semgrep", **f.to_dict()})

        # Step 3: Post comment (authorized)
        if self.check_authority("POST_COMMENT"):
            self.log("Posting security review comment...")
            self.actions_taken.append({
                "action": "POST_COMMENT",
                "status": "EXECUTED",
                "finding_count": len(findings),
            })

        # ─────────────────────────────────────────────────────────
        # Step 4: THE CRITICAL MOMENT — attempt remediation
        # ─────────────────────────────────────────────────────────
        # The security agent has found vulnerabilities.
        # It has the CAPABILITY to fix them (the remediation tool exists).
        # But does it have the AUTHORITY?
        #
        # Without governance: Yes → write succeeds → real commit
        # With MANDATE: No → write BLOCKED → repository protected
        # ─────────────────────────────────────────────────────────

        if findings:
            self.log("")
            self.log("⚡ Vulnerabilities detected. Attempting automated remediation...")
            self.log("   The agent has the CAPABILITY to write fixes.")
            self.log("   Checking AUTHORITY...")

            self._attempt_remediation(repo_path, py_files, findings)

        self.log(f"Security analysis complete.")
        return self.get_result()

    def _attempt_remediation(self, repo_path, py_files, findings):
        """Attempt to fix a vulnerability by writing to the repository.

        This is where MANDATE's governance becomes visible:
        - The agent requests WRITE_FILE authority
        - In ungoverned mode: the request is granted (dangerous!)
        - In governed mode: the request is BLOCKED
        """
        # Pick the first fixable vulnerability
        target_finding = None
        target_file = None
        vuln_type = None

        for finding in findings:
            rule = finding.rule_id.lower()
            if "sql" in rule or "injection" in rule:
                vuln_type = "sql_injection"
            elif "secret" in rule or "password" in rule or "hardcoded" in rule:
                vuln_type = "hardcoded_secret"
            elif "eval" in rule or "exec" in rule:
                vuln_type = "eval_usage"
            elif "md5" in rule or "sha1" in rule or "crypto" in rule:
                vuln_type = "weak_crypto"

            if vuln_type:
                target_finding = finding
                target_file = finding.file
                break

        if not target_finding or not target_file:
            # Fallback: attempt remediation on first finding regardless
            if findings:
                target_finding = findings[0]
                target_file = findings[0].file
                vuln_type = "eval_usage"  # Default fix type
            else:
                self.log("   No fixable vulnerabilities found.")
                return

        self.log(f"   Target: {target_file} — {target_finding.rule_id}")
        self.log(f"   Vulnerability: {target_finding.message}")
        self.log("")

        # ═══════════════════════════════════════════════════════════
        # THE AUTHORITY CHECK — this is where governance matters
        # ═══════════════════════════════════════════════════════════
        self.log("   ┌─────────────────────────────────────────────┐")
        self.log("   │  REQUESTING WRITE_FILE AUTHORITY            │")
        self.log("   │  Agent: security                            │")
        self.log("   │  Action: WRITE_FILE                         │")
        self.log(f"   │  Scopes: {', '.join(self.identity.scopes):<35s}│")
        self.log("   └─────────────────────────────────────────────┘")

        if not self.check_authority("WRITE_FILE"):
            # GOVERNED PATH — write is blocked!
            self.log("")
            self.log("   ╔═══════════════════════════════════════════════╗")
            self.log("   ║  🛡️  BLOCKED — WRITE_FILE not in scope       ║")
            self.log("   ║  The agent has the CAPABILITY but not the    ║")
            self.log("   ║  AUTHORITY. The repository is protected.     ║")
            self.log("   ╚═══════════════════════════════════════════════╝")
            self.actions_taken.append({
                "action": "WRITE_FILE",
                "status": "BLOCKED",
                "reason": "WRITE_FILE outside delegated authority",
                "target_file": target_file,
                "vulnerability": target_finding.rule_id,
            })
            return

        # UNGOVERNED PATH — write executes!
        self.log("   ⚠️  WRITE_FILE — ALLOWED (no governance enforced)")
        self.log(f"   Writing fix to {target_file}...")

        try:
            original = get_file_content(repo_path, target_file)
            fixed = generate_fix(vuln_type, original)

            if fixed and fixed != original:
                result = apply_remediation(
                    repo_path=repo_path,
                    filepath=target_file,
                    original_content=original,
                    fixed_content=fixed,
                    vulnerability_id=target_finding.rule_id,
                    description=target_finding.message,
                )
                self.actions_taken.append({
                    "action": "WRITE_FILE",
                    "status": result["status"],
                    "commit_hash": result.get("commit_hash"),
                    "target_file": target_file,
                    "vulnerability": target_finding.rule_id,
                    "side_effect": result.get("side_effect", False),
                })

                if result["status"] == "EXECUTED":
                    self.log(f"   ✅ Fix applied and committed: {result['commit_hash'][:12]}")
                    self.log(f"   ⚠️  REAL SIDE EFFECT — repository was mutated!")
                else:
                    self.log(f"   ❌ Remediation failed: {result.get('error')}")
            else:
                self.log("   Could not generate automatic fix. Skipping remediation.")
                self.actions_taken.append({
                    "action": "WRITE_FILE",
                    "status": "SKIPPED",
                    "reason": "No automatic fix available",
                })
        except Exception as e:
            self.log(f"   ❌ Remediation error: {e}")
            self.actions_taken.append({
                "action": "WRITE_FILE",
                "status": "ERROR",
                "error": str(e),
            })


def main():
    """Entry point when run as a subprocess."""
    task_data = json.loads(sys.stdin.read())
    repo_path = task_data["repo_path"]
    changed_files = task_data["changed_files"]
    governed = task_data.get("governed", False)

    agent = SecurityAgent(governed=governed)
    result = agent.run(repo_path, changed_files)

    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
