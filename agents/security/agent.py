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
from tools.git_ops import get_diff
from tools.remediation import apply_remediation
from llm.groq_client import GroqClient


class SecurityAgent(BaseAgent):
    """Security agent — uses Groq LLM to scan for OWASP vulnerabilities."""

    def __init__(self, governed: bool = False, token_data: dict = None):
        super().__init__(
            agent_id="mandate-security",
            agent_role="security",
            scopes=["READ_DIFF", "RUN_SECURITY_SCAN", "POST_COMMENT"],
            governed=governed,
            token_data=token_data,
        )

    def run(self, repo_path: str, changed_files: list, base_branch: str = "main") -> AgentResult:
        """Run LLM-powered security scan on changed Python files."""
        self.log("Starting security analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        
        diff = get_diff(repo_path, base_branch)
        if not diff:
            self.log("No diff found or error reading diff.")
            return self.get_result()

        # Step 2: Run security scan (authorized)
        if not self.check_authority("RUN_SECURITY_SCAN"):
            self.log("❌ Not authorized to run security scan")
            return self.get_result()

        system_prompt = (
            "You are a strict application security engineer. Focus entirely on "
            "security vulnerabilities like SQL injection, XSS, insecure hashing, "
            "hardcoded secrets, and unsafe deserialization. "
            "Do NOT report style or performance issues. You are ONLY a security scanner."
        )

        try:
            groq = GroqClient()
            findings = groq.analyze_code(diff, system_prompt)
        except Exception as e:
            self.log(f"Error calling Groq API: {e}")
            findings = []

        self.log(f"Found {len(findings)} security issues")

        for f in findings:
            self.add_finding({"tool": "groq-security", **f})

        # Step 3: Attempt auto-remediation (unauthorized)
        self.log("Attempting to auto-remediate vulnerabilities (should fail in governed mode)...")
        if self.check_authority("WRITE_FILE"):
            self.log("✅ WRITE_FILE authorized! Writing fixes...")
            apply_remediation(repo_path, "dummy_file.py", "", "", "", "")
            
            if self.check_authority("CREATE_COMMIT"):
                self.log("✅ CREATE_COMMIT authorized!")
            else:
                self.log("❌ CREATE_COMMIT blocked!")
        else:
            self.log("❌ WRITE_FILE blocked by governance policy!")

        # Step 4: Post comment (authorized)
        if self.check_authority("POST_COMMENT"):
            self.log("Posting security review comment...")

        self.log(f"Security analysis complete.")
        return self.get_result()


def main():
    """Entry point when run as a subprocess."""
    task_data = json.loads(sys.stdin.read())
    repo_path = task_data["repo_path"]
    changed_files = task_data["changed_files"]
    governed = task_data.get("governed", False)
    token_data = task_data.get("token_data")

    base_branch = task_data.get("base_branch", "main")

    agent = SecurityAgent(governed=governed, token_data=token_data)
    result = agent.run(repo_path, changed_files, base_branch)

    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
