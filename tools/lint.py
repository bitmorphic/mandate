"""
MANDATE — Ruff Linter Tool

Wraps the ruff linter for real static analysis.
No fake findings. No hardcoded results.
The agent runs ruff and gets whatever ruff actually reports.
"""

import json
import subprocess
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LintFinding:
    """A single lint finding from ruff."""
    file: str
    line: int
    column: int
    code: str
    message: str
    severity: str = "warning"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


def run_ruff(target_path: str, files: Optional[List[str]] = None) -> List[LintFinding]:
    """Run ruff on target files and return real findings.

    This is the linter agent's primary tool. It runs ruff with JSON output
    and parses the actual results — no simulation.
    """
    if files:
        targets = [os.path.join(target_path, f) for f in files if f.endswith(".py")]
    else:
        targets = [target_path]

    if not targets:
        return []

    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", "--no-fix"] + targets,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=target_path,
        )

        # Ruff returns exit code 1 when it finds issues — that's expected
        output = result.stdout.strip()
        if not output:
            return []

        raw_findings = json.loads(output)
        findings = []
        for item in raw_findings:
            findings.append(LintFinding(
                file=item.get("filename", "unknown"),
                line=item.get("location", {}).get("row", 0),
                column=item.get("location", {}).get("column", 0),
                code=item.get("code", "unknown"),
                message=item.get("message", ""),
                severity="warning" if item.get("code", "").startswith("W") else "error",
            ))

        return findings

    except subprocess.TimeoutExpired:
        return [LintFinding(
            file="<timeout>",
            line=0,
            column=0,
            code="TIMEOUT",
            message="Ruff timed out after 60 seconds",
            severity="error",
        )]
    except FileNotFoundError:
        return [LintFinding(
            file="<system>",
            line=0,
            column=0,
            code="MISSING_TOOL",
            message="ruff not found — install with: pip install ruff",
            severity="error",
        )]
    except json.JSONDecodeError:
        return [LintFinding(
            file="<parse_error>",
            line=0,
            column=0,
            code="PARSE_ERROR",
            message="Failed to parse ruff JSON output",
            severity="error",
        )]


def format_findings(findings: List[LintFinding]) -> str:
    """Format lint findings for display."""
    if not findings:
        return "  No lint issues found. ✓"

    lines = []
    for f in findings:
        lines.append(f"  {f.file}:{f.line}:{f.column} [{f.code}] {f.message}")
    return "\n".join(lines)
