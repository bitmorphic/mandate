import os
import sys
import argparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from coordinator.main import run_review

def main():
    parser = argparse.ArgumentParser(description="Run MANDATE code review on a real repository.")
    parser.add_argument("repo_path", help="Absolute path to your local Git repository")
    parser.add_argument("--branch", default="main", help="The base branch to compare against (default: main)")
    parser.add_argument("--ungoverned", action="store_true", help="Run without governance (WARNING: agent may write files!)")

    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)
    
    if not os.path.exists(os.path.join(repo_path, ".git")):
        print(f"❌ Error: {repo_path} is not a valid Git repository.")
        sys.exit(1)

    print(f"🚀 Running MANDATE review on: {repo_path}")
    print(f"🌿 Comparing against branch: {args.branch}")
    print(f"🛡️  Governance Enabled: {not args.ungoverned}")
    print("=" * 60)

    try:
        run_review(
            repo_path=repo_path,
            base_branch=args.branch,
            governed=not args.ungoverned,
        )
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
