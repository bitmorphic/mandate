"""
MANDATE — Linter Agent

Independent agent that runs ruff on changed files.
Authorized scopes: READ_DIFF, RUN_LINTER, POST_COMMENT
Not authorized: WRITE_FILE, CREATE_COMMIT, PUSH, MERGE, DEPLOY

This agent runs ruff (a real linter) and reports findings.
It does not attempt any write operations.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.base import BaseAgent, AgentResult
from tools.lint import run_ruff, format_findings


class LinterAgent(BaseAgent):
    """Linter agent — runs real ruff analysis on changed files."""

    def __init__(self, governed: bool = False):
        super().__init__(
            agent_id="mandate-linter",
            agent_role="linter",
            scopes=["READ_DIFF", "RUN_LINTER", "POST_COMMENT"],
            governed=governed,
        )

    def run(self, repo_path: str, changed_files: list) -> AgentResult:
        """Run ruff linter on changed Python files."""
        self.log("Starting lint analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        self.log(f"Analyzing {len(py_files)} Python files...")

        # Step 2: Run linter (authorized)
        if not self.check_authority("RUN_LINTER"):
            self.log("❌ Not authorized to run linter")
            return self.get_result()

        findings = run_ruff(repo_path, py_files)
        self.log(f"Found {len(findings)} lint issues")

        for f in findings:
            self.add_finding({"tool": "ruff", **f.to_dict()})

        # Step 3: Post comment (authorized) — log findings as the "comment"
        if self.check_authority("POST_COMMENT"):
            self.log("Posting review comment with findings...")
            self.actions_taken.append({
                "action": "POST_COMMENT",
                "status": "EXECUTED",
                "finding_count": len(findings),
            })

        self.log(f"Lint analysis complete. {len(findings)} issues found.")
        return self.get_result()


def main():
    """Entry point when run as a subprocess."""
    # Read task from stdin (JSON)
    task_data = json.loads(sys.stdin.read())
    repo_path = task_data["repo_path"]
    changed_files = task_data["changed_files"]
    governed = task_data.get("governed", False)

    agent = LinterAgent(governed=governed)
    result = agent.run(repo_path, changed_files)

    # Write result to stdout (JSON)
    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
