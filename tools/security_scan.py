"""
MANDATE — Semgrep Security Scanner Tool

Wraps semgrep for real security analysis.
No fake vulnerabilities. No hardcoded findings.
The agent runs semgrep and gets whatever semgrep actually reports.

The security agent uses these real findings to decide whether remediation
is needed — and that remediation attempt is exactly what MANDATE governs.
"""

import json
import subprocess
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SecurityFinding:
    """A single security finding from semgrep."""
    file: str
    line_start: int
    line_end: int
    rule_id: str
    message: str
    severity: str  # ERROR, WARNING, INFO
    category: str = "security"
    fix_suggestion: Optional[str] = None
    snippet: str = ""

    def to_dict(self) -> dict:
        d = {
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
        }
        if self.fix_suggestion:
            d["fix_suggestion"] = self.fix_suggestion
        if self.snippet:
            d["snippet"] = self.snippet
        return d


def run_semgrep(
    target_path: str,
    files: Optional[List[str]] = None,
    rules: str = "auto",
) -> List[SecurityFinding]:
    """Run semgrep on target files and return real findings.

    Uses semgrep's built-in security rules by default.
    For the demo fixture, we also use a custom rule file if present.
    """
    if files:
        targets = [os.path.join(target_path, f) for f in files if f.endswith(".py")]
    else:
        targets = [target_path]

    if not targets:
        return []

    # Check for custom rules in the repo
    custom_rules = os.path.join(target_path, ".semgrep.yml")
    rule_arg = custom_rules if os.path.exists(custom_rules) else "auto"

    try:
        cmd = [
            "semgrep", "scan",
            "--json",
            "--config", rule_arg,
            "--no-git-ignore",
        ] + targets

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=target_path,
        )

        output = result.stdout.strip()
        if not output:
            return []

        data = json.loads(output)
        results = data.get("results", [])

        findings = []
        for item in results:
            extra = item.get("extra", {})
            findings.append(SecurityFinding(
                file=item.get("path", "unknown"),
                line_start=item.get("start", {}).get("line", 0),
                line_end=item.get("end", {}).get("line", 0),
                rule_id=item.get("check_id", "unknown"),
                message=extra.get("message", "Security issue detected"),
                severity=extra.get("severity", "WARNING"),
                category=extra.get("metadata", {}).get("category", "security"),
                fix_suggestion=extra.get("fix", None),
                snippet=extra.get("lines", ""),
            ))

        return findings

    except subprocess.TimeoutExpired:
        return [SecurityFinding(
            file="<timeout>",
            line_start=0,
            line_end=0,
            rule_id="TIMEOUT",
            message="Semgrep timed out after 120 seconds",
            severity="ERROR",
        )]
    except FileNotFoundError:
        return [SecurityFinding(
            file="<system>",
            line_start=0,
            line_end=0,
            rule_id="MISSING_TOOL",
            message="semgrep not found — install with: pip install semgrep",
            severity="ERROR",
        )]
    except json.JSONDecodeError:
        return [SecurityFinding(
            file="<parse_error>",
            line_start=0,
            line_end=0,
            rule_id="PARSE_ERROR",
            message="Failed to parse semgrep JSON output",
            severity="ERROR",
        )]


def format_findings(findings: List[SecurityFinding]) -> str:
    """Format security findings for display."""
    if not findings:
        return "  No security issues found. ✓"

    lines = []
    for f in findings:
        severity_icon = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(f.severity, "⚪")
        lines.append(f"  {severity_icon} {f.file}:{f.line_start} [{f.rule_id}]")
        lines.append(f"     {f.message}")
        if f.fix_suggestion:
            lines.append(f"     Fix: {f.fix_suggestion}")
    return "\n".join(lines)
