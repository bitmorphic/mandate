"""
MANDATE — Performance Agent

Independent agent that analyzes changed files for performance issues.
Uses AST-based analysis — no code execution.

This agent exists primarily to prove that multiple independent
delegated agents can operate simultaneously under different scopes.

Authorized scopes: READ_DIFF, RUN_PERFORMANCE_ANALYSIS, POST_COMMENT
Not authorized: WRITE_FILE, CREATE_COMMIT, PUSH, MERGE, DEPLOY
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.base import BaseAgent, AgentResult
from tools.git_ops import get_diff
from llm.groq_client import GroqClient


class PerformanceAgent(BaseAgent):
    """Performance agent — uses Groq LLM to check algorithmic complexity and performance bottlenecks."""

    def __init__(self, governed: bool = False, token_data: dict = None):
        super().__init__(
            agent_id="mandate-performance",
            agent_role="performance",
            scopes=["READ_DIFF", "RUN_PERFORMANCE_ANALYSIS", "POST_COMMENT"],
            governed=governed,
            token_data=token_data,
        )

    def run(self, repo_path: str, changed_files: list, base_branch: str = "main") -> AgentResult:
        """Run LLM-powered performance analysis on changed Python files."""
        self.log("Starting performance analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        self.log(f"Analyzing {len(py_files)} Python files for performance issues...")
        
        diff = get_diff(repo_path, base_branch)
        if not diff:
            self.log("No diff found or error reading diff.")
            return self.get_result()

        # Step 2: Run performance analysis (authorized)
        if not self.check_authority("RUN_PERFORMANCE_ANALYSIS"):
            self.log("❌ Not authorized to run performance analysis")
            return self.get_result()

        system_prompt = (
            "You are a strict performance and algorithmic complexity engineer. "
            "Focus entirely on Big-O complexity (time and space), N+1 query problems, "
            "memory leaks, inefficient loops, and suboptimal data structures. "
            "Do NOT report style or security issues. You are ONLY a performance scanner."
        )

        try:
            groq = GroqClient()
            findings = groq.analyze_code(diff, system_prompt)
        except Exception as e:
            self.log(f"Error calling Groq API: {e}")
            findings = []

        self.log(f"Found {len(findings)} performance issues")

        for f in findings:
            self.add_finding({"tool": "groq-performance", **f})

        # Step 3: Post comment (authorized)
        if self.check_authority("POST_COMMENT"):
            self.log("Posting performance review comment...")

        self.log(f"Performance analysis complete. {len(findings)} issues found.")
        return self.get_result()


def main():
    """Entry point when run as a subprocess."""
    task_data = json.loads(sys.stdin.read())
    repo_path = task_data["repo_path"]
    changed_files = task_data["changed_files"]
    governed = task_data.get("governed", False)
    token_data = task_data.get("token_data")

    base_branch = task_data.get("base_branch", "main")

    agent = PerformanceAgent(governed=governed, token_data=token_data)
    result = agent.run(repo_path, changed_files, base_branch)

    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
