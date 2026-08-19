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
from tools.performance import analyze_performance, format_findings


class PerformanceAgent(BaseAgent):
    """Performance agent — runs real AST-based performance analysis."""

    def __init__(self, governed: bool = False):
        super().__init__(
            agent_id="mandate-performance",
            agent_role="performance",
            scopes=["READ_DIFF", "RUN_PERFORMANCE_ANALYSIS", "POST_COMMENT"],
            governed=governed,
        )

    def run(self, repo_path: str, changed_files: list) -> AgentResult:
        """Run performance analysis on changed Python files."""
        self.log("Starting performance analysis...")
        self.log(f"Identity: {self.identity.fingerprint}")
        self.log(f"Authorized scopes: {', '.join(self.identity.scopes)}")

        # Step 1: Read diff (authorized)
        if not self.check_authority("READ_DIFF"):
            self.log("❌ Not authorized to read diff")
            return self.get_result()

        py_files = [f for f in changed_files if f.endswith(".py")]
        self.log(f"Analyzing {len(py_files)} Python files for performance issues...")

        # Step 2: Run performance analysis (authorized)
        if not self.check_authority("RUN_PERFORMANCE_ANALYSIS"):
            self.log("❌ Not authorized to run performance analysis")
            return self.get_result()

        findings = analyze_performance(repo_path, py_files)
        self.log(f"Found {len(findings)} performance issues")

        for f in findings:
            self.add_finding({"tool": "perf-analyzer", **f.to_dict()})

        # Step 3: Post comment (authorized)
        if self.check_authority("POST_COMMENT"):
            self.log("Posting performance review comment...")
            self.actions_taken.append({
                "action": "POST_COMMENT",
                "status": "EXECUTED",
                "finding_count": len(findings),
            })

        self.log(f"Performance analysis complete. {len(findings)} issues found.")
        return self.get_result()


def main():
    """Entry point when run as a subprocess."""
    task_data = json.loads(sys.stdin.read())
    repo_path = task_data["repo_path"]
    changed_files = task_data["changed_files"]
    governed = task_data.get("governed", False)

    agent = PerformanceAgent(governed=governed)
    result = agent.run(repo_path, changed_files)

    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
