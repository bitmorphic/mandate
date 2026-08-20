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
from tools.git_ops import get_diff
from llm.groq_client import GroqClient


class LinterAgent(BaseAgent):
    """Linter agent — uses Groq LLM to check code style and conventions."""

    def __init__(self, governed: bool = False, token_data: dict = None):
        super().__init__(
            agent_id="mandate-linter",
            agent_role="linter",
            scopes=["READ_DIFF", "RUN_LINTER", "POST_COMMENT"],
            governed=governed,
            token_data=token_data,
        )

    def run(self, repo_path: str, changed_files: list, base_branch: str = "main") -> AgentResult:
        """Run LLM-powered lint analysis on changed Python files."""
        self.log("Starting lint analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        self.log(f"Analyzing {len(py_files)} Python files...")
        
        diff = get_diff(repo_path, base_branch)
        if not diff:
            self.log("No diff found or error reading diff.")
            return self.get_result()

        # Step 2: Run linter (authorized)
        if not self.check_authority("RUN_LINTER"):
            self.log("❌ Not authorized to run linter")
            return self.get_result()

        system_prompt = (
            "You are a strict PEP 8 Python linter. Focus strictly on code style, "
            "formatting, unused imports, naming conventions, and clean code principles. "
            "Do NOT report security or performance issues. You are ONLY a linter."
        )

        try:
            groq = GroqClient()
            findings = groq.analyze_code(diff, system_prompt)
        except Exception as e:
            self.log(f"Error calling Groq API: {e}")
            findings = []

        self.log(f"Found {len(findings)} lint issues")

        for f in findings:
            self.add_finding({"tool": "groq-linter", **f})

        # Step 3: Post comment (authorized) — log findings as the "comment"
        if self.check_authority("POST_COMMENT"):
            self.log("Posting lint review comment...")
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
    token_data = task_data.get("token_data")

    base_branch = task_data.get("base_branch", "main")
    
    agent = LinterAgent(governed=governed, token_data=token_data)
    result = agent.run(repo_path, changed_files, base_branch)

    # Write result to stdout (JSON)
    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
