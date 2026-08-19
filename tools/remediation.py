"""
MANDATE — Remediation Tool

THIS IS THE DANGEROUS CAPABILITY.

The security agent can detect vulnerabilities and reason that it should fix them.
This tool gives it the technical capability to write files and create commits.

CAPABILITY ≠ AUTHORITY

The security agent has the capability to call these functions.
But under MANDATE governance, it should NOT have the authority to do so.

Without governance: remediation executes, real commit created.
With governance: MANDATE blocks the write, repository stays protected.
"""

import os
from typing import Optional

from tools.git_ops import write_file, create_commit


def apply_remediation(
    repo_path: str,
    filepath: str,
    original_content: str,
    fixed_content: str,
    vulnerability_id: str,
    description: str,
) -> dict:
    """Apply a security fix to the repository.

    ⚠️ THIS IS THE CRITICAL DEMO OPERATION.

    This function:
    1. Writes the fixed content to the file (WRITE operation)
    2. Creates a commit with the fix (COMMIT operation)

    Without governance: both succeed, creating a real side effect.
    With MANDATE + ArmorIQ: the write should be BLOCKED because
    the security agent was only delegated READ + SCAN + COMMENT authority.

    Returns:
        dict with 'status', 'commit_hash', and details about what happened.
    """
    result = {
        "action": "REMEDIATION",
        "filepath": filepath,
        "vulnerability_id": vulnerability_id,
        "description": description,
    }

    try:
        # Step 1: Write the fixed file
        write_file(repo_path, filepath, fixed_content)
        result["file_written"] = True

        # Step 2: Create a commit
        commit_message = (
            f"fix({vulnerability_id}): {description}\n\n"
            f"Automated remediation by MANDATE Security Agent.\n"
            f"Vulnerability: {vulnerability_id}"
        )
        commit_hash = create_commit(
            repo_path,
            commit_message,
            files=[filepath],
        )
        result["commit_hash"] = commit_hash
        result["status"] = "EXECUTED"
        result["side_effect"] = True

        return result

    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)
        result["side_effect"] = False
        return result


def generate_fix(
    vulnerability_type: str,
    original_code: str,
) -> Optional[str]:
    """Generate a fix for a known vulnerability type.

    For the demo, we use deterministic fixes for known vulnerability patterns.
    In production, this could use an LLM for more sophisticated remediation.
    """
    fixes = {
        "sql_injection": _fix_sql_injection,
        "hardcoded_secret": _fix_hardcoded_secret,
        "eval_usage": _fix_eval_usage,
        "weak_crypto": _fix_weak_crypto,
    }

    fixer = fixes.get(vulnerability_type)
    if fixer:
        return fixer(original_code)
    return None


def _fix_sql_injection(code: str) -> str:
    """Replace string-formatted SQL with parameterized queries."""
    # Replace f-string SQL with parameterized version
    code = code.replace(
        'f"SELECT * FROM users WHERE username = \'{username}\'"',
        '"SELECT * FROM users WHERE username = ?", (username,)'
    )
    code = code.replace(
        'f"SELECT * FROM users WHERE id = {user_id}"',
        '"SELECT * FROM users WHERE id = ?", (user_id,)'
    )
    return code


def _fix_hardcoded_secret(code: str) -> str:
    """Replace hardcoded secrets with environment variable lookups."""
    import re
    # Replace hardcoded API keys with os.environ.get()
    code = re.sub(
        r'(API_KEY|SECRET_KEY|PASSWORD)\s*=\s*["\']([^"\']+)["\']',
        r'\1 = os.environ.get("\1", "")',
        code,
    )
    if "import os" not in code:
        code = "import os\n" + code
    return code


def _fix_eval_usage(code: str) -> str:
    """Replace eval() with ast.literal_eval() where possible."""
    code = code.replace("eval(", "ast.literal_eval(")
    if "import ast" not in code:
        code = "import ast\n" + code
    return code


def _fix_weak_crypto(code: str) -> str:
    """Replace MD5/SHA1 with SHA-256."""
    code = code.replace("hashlib.md5(", "hashlib.sha256(")
    code = code.replace("hashlib.sha1(", "hashlib.sha256(")
    return code
