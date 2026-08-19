"""
MANDATE — Git Operations

Real git operations for the code review pipeline.
These are the tools that agents use — and that governance constrains.

READ operations are safe.
WRITE operations are dangerous — this is exactly the boundary MANDATE enforces.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class DiffEntry:
    """A single file change in a diff."""
    filepath: str
    status: str  # A(dded), M(odified), D(eleted)
    content: str = ""


def run_git(args: List[str], cwd: str) -> Tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ─── READ Operations (safe, authorized for all agents) ──────────────

def list_changed_files(repo_path: str, base_branch: str = "main") -> List[DiffEntry]:
    """List files changed between the current branch and base branch.

    This is a READ operation — safe for all agents.
    """
    code, stdout, stderr = run_git(
        ["diff", "--name-status", base_branch],
        cwd=repo_path,
    )
    if code != 0:
        raise RuntimeError(f"git diff failed: {stderr}")

    entries = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            status, filepath = parts
            entries.append(DiffEntry(filepath=filepath, status=status))
    return entries


def get_diff(repo_path: str, base_branch: str = "main") -> str:
    """Get the full diff between current branch and base.

    This is a READ operation — safe for all agents.
    """
    code, stdout, stderr = run_git(
        ["diff", base_branch],
        cwd=repo_path,
    )
    if code != 0:
        raise RuntimeError(f"git diff failed: {stderr}")
    return stdout


def get_file_content(repo_path: str, filepath: str) -> str:
    """Read a file from the repository.

    This is a READ operation — safe for all agents.
    """
    full_path = os.path.join(repo_path, filepath)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def get_current_branch(repo_path: str) -> str:
    """Get current git branch name."""
    code, stdout, stderr = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    if code != 0:
        raise RuntimeError(f"Failed to get branch: {stderr}")
    return stdout


# ─── WRITE Operations (DANGEROUS — these are what MANDATE governs) ──

def write_file(repo_path: str, filepath: str, content: str) -> str:
    """Write content to a file in the repository.

    ⚠️ THIS IS A WRITE OPERATION.
    Without governance: executes freely.
    With MANDATE: must be authorized by the agent's delegated scope.
    """
    full_path = os.path.join(repo_path, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


def create_commit(repo_path: str, message: str, files: Optional[List[str]] = None) -> str:
    """Create a git commit.

    ⚠️ THIS IS A WRITE OPERATION.
    Without governance: executes freely, creating a real commit.
    With MANDATE: must be authorized — security agent should NOT have this authority.
    """
    if files:
        for f in files:
            run_git(["add", f], cwd=repo_path)
    else:
        run_git(["add", "-A"], cwd=repo_path)

    code, stdout, stderr = run_git(
        ["commit", "-m", message, "--allow-empty"],
        cwd=repo_path,
    )
    if code != 0:
        raise RuntimeError(f"git commit failed: {stderr}")

    # Return the commit hash as proof of the real side effect
    code, commit_hash, _ = run_git(["rev-parse", "HEAD"], cwd=repo_path)
    return commit_hash
