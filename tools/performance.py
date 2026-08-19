"""
MANDATE — Performance Analysis Tool

Lightweight Python performance analysis via AST inspection.
Identifies common performance anti-patterns without running code.

This agent exists primarily to prove that multiple independent
agents can operate simultaneously under different scopes.
"""

import ast
import os
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PerfFinding:
    """A single performance finding."""
    file: str
    line: int
    issue: str
    severity: str  # HIGH, MEDIUM, LOW
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "issue": self.issue,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


class PerfAnalyzer(ast.NodeVisitor):
    """AST-based performance anti-pattern detector."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.findings: List[PerfFinding] = []

    def visit_For(self, node: ast.For):
        """Detect nested loops (potential O(n²) or worse)."""
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child is not node:
                self.findings.append(PerfFinding(
                    file=self.filepath,
                    line=node.lineno,
                    issue="Nested loop detected — potential O(n²) complexity",
                    severity="MEDIUM",
                    suggestion="Consider using sets, dicts, or itertools for better performance",
                ))
                break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect known slow patterns."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Detect time.sleep (blocking)
        if func_name == "sleep":
            self.findings.append(PerfFinding(
                file=self.filepath,
                line=node.lineno,
                issue="Blocking sleep() call detected",
                severity="LOW",
                suggestion="Consider async/await patterns for non-blocking waits",
            ))

        # Detect eval() (both security AND performance issue)
        if func_name == "eval":
            self.findings.append(PerfFinding(
                file=self.filepath,
                line=node.lineno,
                issue="eval() call — slow and dynamically compiled each invocation",
                severity="HIGH",
                suggestion="Replace with direct function calls or ast.literal_eval()",
            ))

        # Detect string concatenation in loops
        if func_name == "join":
            pass  # join is actually good

        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        """Check for deeply nested comprehensions."""
        if len(node.generators) > 2:
            self.findings.append(PerfFinding(
                file=self.filepath,
                line=node.lineno,
                issue="Deeply nested list comprehension (3+ generators)",
                severity="MEDIUM",
                suggestion="Consider breaking into separate operations for readability and perf",
            ))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Detect imports of heavy modules that suggest potential issues."""
        for alias in node.names:
            if alias.name in ("pickle", "shelve"):
                self.findings.append(PerfFinding(
                    file=self.filepath,
                    line=node.lineno,
                    issue=f"Import of '{alias.name}' — slow serialization",
                    severity="LOW",
                    suggestion="Consider json or msgpack for better performance",
                ))
        self.generic_visit(node)


def analyze_performance(
    target_path: str,
    files: Optional[List[str]] = None,
) -> List[PerfFinding]:
    """Analyze Python files for performance anti-patterns.

    Uses AST inspection — no code execution required.
    """
    if files:
        py_files = [
            os.path.join(target_path, f)
            for f in files
            if f.endswith(".py")
        ]
    else:
        py_files = []
        for root, dirs, filenames in os.walk(target_path):
            # Skip hidden dirs and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in filenames:
                if fname.endswith(".py"):
                    py_files.append(os.path.join(root, fname))

    all_findings = []
    for filepath in py_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            # Use relative path for cleaner output
            rel_path = os.path.relpath(filepath, target_path)
            analyzer = PerfAnalyzer(rel_path)
            analyzer.visit(tree)
            all_findings.extend(analyzer.findings)
        except (SyntaxError, UnicodeDecodeError):
            continue

    return all_findings


def format_findings(findings: List[PerfFinding]) -> str:
    """Format performance findings for display."""
    if not findings:
        return "  No performance issues found. ✓"

    lines = []
    for f in findings:
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}.get(f.severity, "⚪")
        lines.append(f"  {icon} {f.file}:{f.line} [{f.severity}]")
        lines.append(f"     {f.issue}")
        if f.suggestion:
            lines.append(f"     → {f.suggestion}")
    return "\n".join(lines)
