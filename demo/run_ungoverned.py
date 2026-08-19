"""
MANDATE — Ungoverned Demo (Day 1)

Demonstrates the multi-agent code review pipeline WITHOUT governance.

This is the "before" scenario:
    Security Agent → finds vulnerability → decides to fix it →
    requests WRITE → WRITE EXECUTES → REAL COMMIT

The agent had the capability, and without an authority boundary,
the action happened. The repository was mutated without authorization.

Run this to prove the pipeline works before adding ArmorIQ governance.
"""

import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from demo.fixture.setup_fixture import setup_test_repo, teardown_test_repo
from coordinator.main import run_review
from tools.git_ops import run_git


def main():
    print()
    print("=" * 65)
    print("  MANDATE — UNGOVERNED DEMO")
    print("  Demonstrating the DANGER of autonomous agents without authority.")
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

    # ─── Run the ungoverned pipeline ────────────────────────────────
    try:
        result = run_review(
            repo_path=repo_path,
            base_branch="main",
            governed=False,  # ← NO GOVERNANCE
        )
    except Exception as e:
        print(f"  ❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return

    # ─── Verify the side effect ─────────────────────────────────────
    print()
    print("=" * 65)
    print("  SIDE EFFECT VERIFICATION")
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

    if new_commits > 0:
        print(f"  ⚠️  {new_commits} NEW COMMIT(S) CREATED BY THE SECURITY AGENT!")
        print("  ⚠️  The repository was mutated without any authority check.")
        print()
        print("  This is exactly the problem MANDATE solves.")
        print("  In governed mode, this write would be BLOCKED.")
    else:
        print("  No new commits created.")
        print("  (The security agent may not have found a fixable vulnerability,")
        print("   or the remediation may have failed.)")

    print()
    print("=" * 65)
    print("  UNGOVERNED DEMO COMPLETE")
    print("=" * 65)
    print()

    # ─── Cleanup ────────────────────────────────────────────────────
    # Don't teardown — leave the repo so the user can inspect it
    print(f"  Test repository preserved at: {repo_path}")
    print("  Run 'git log --oneline' in that directory to see the commits.")
    print()

    return result


if __name__ == "__main__":
    main()
