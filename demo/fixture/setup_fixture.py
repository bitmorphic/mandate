"""
MANDATE — Fixture Setup

Creates a local git repository with a deterministic "pull request"
containing vulnerable code. This gives all three agents something
real to analyze without depending on GitHub or external services.
"""

import os
import shutil
import subprocess
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


FIXTURE_DIR = os.path.dirname(os.path.abspath(__file__))


def setup_test_repo(base_dir: str = None) -> str:
    """Create a test git repository with a vulnerable PR branch.

    Returns the path to the test repository.

    Structure:
        test_repo/
        ├── .git/
        ├── main branch (clean)
        │   └── app.py (simple, safe code)
        └── feature/add-user-system branch (vulnerable)
            └── app.py (vulnerable code)
    """
    if base_dir is None:
        base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_repos",
        )

    repo_path = os.path.join(base_dir, "test_repo")

    # Clean up if exists
    if os.path.exists(repo_path):
        # On Windows, git objects can be read-only
        def force_remove(func, path, excinfo):
            os.chmod(path, 0o777)
            func(path)
        shutil.rmtree(repo_path, onerror=force_remove)

    os.makedirs(repo_path, exist_ok=True)

    def git(*args):
        result = subprocess.run(
            ["git"] + list(args),
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 and "already exists" not in result.stderr:
            print(f"  git {' '.join(args)}: {result.stderr.strip()}", file=sys.stderr)
        return result

    # Initialize repo
    git("init")
    git("config", "user.email", "mandate@demo.local")
    git("config", "user.name", "MANDATE Demo")

    # Create safe initial code on main branch
    safe_code = '''"""
Application module — safe baseline code.
"""

def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    print(greet("World"))
'''
    with open(os.path.join(repo_path, "app.py"), "w") as f:
        f.write(safe_code)

    git("add", "-A")
    git("commit", "-m", "Initial commit: safe baseline code")

    # Rename default branch to main
    git("branch", "-M", "main")

    # Create the "PR" branch with vulnerable code
    git("checkout", "-b", "feature/add-user-system")

    # Copy the vulnerable fixture
    vulnerable_src = os.path.join(FIXTURE_DIR, "vulnerable.py")
    with open(vulnerable_src, "r") as f:
        vulnerable_code = f.read()

    with open(os.path.join(repo_path, "app.py"), "w") as f:
        f.write(vulnerable_code)

    # Also create a semgrep config for reliable detection
    semgrep_config = """rules:
  - id: hardcoded-secret
    patterns:
      - pattern: $VAR = "..."
      - metavariable-regex:
          metavariable: $VAR
          regex: (API_KEY|SECRET_KEY|PASSWORD|DATABASE_PASSWORD)
    message: "Hardcoded secret detected in variable $VAR"
    languages: [python]
    severity: ERROR

  - id: eval-usage
    pattern: eval(...)
    message: "Use of eval() detected — potential code injection"
    languages: [python]
    severity: ERROR

  - id: weak-hash-md5
    pattern: hashlib.md5(...)
    message: "MD5 is cryptographically weak — use SHA-256 or better"
    languages: [python]
    severity: WARNING

  - id: weak-hash-sha1
    pattern: hashlib.sha1(...)
    message: "SHA1 is cryptographically weak — use SHA-256 or better"
    languages: [python]
    severity: WARNING

  - id: sql-injection-format
    patterns:
      - pattern: |
          $CURSOR.execute(f"...")
    message: "SQL injection via f-string formatting"
    languages: [python]
    severity: ERROR
"""
    with open(os.path.join(repo_path, ".semgrep.yml"), "w") as f:
        f.write(semgrep_config)

    git("add", "-A")
    git("commit", "-m", "feat: add user system with authentication\n\nThis PR adds user management and API integration.")

    return repo_path


def teardown_test_repo(repo_path: str):
    """Clean up a test repository."""
    if os.path.exists(repo_path):
        def force_remove(func, path, excinfo):
            os.chmod(path, 0o777)
            func(path)
        shutil.rmtree(repo_path, onerror=force_remove)


if __name__ == "__main__":
    print("Setting up MANDATE test repository...")
    path = setup_test_repo()
    print(f"Test repository created at: {path}")
    print("Branch: feature/add-user-system (contains vulnerable code)")
    print("Base: main (contains safe code)")
