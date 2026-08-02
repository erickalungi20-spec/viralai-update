"""
Plugin Security Scanner (Blueprint Ch.35.4: "every plugin shall undergo code
inspection, dependency verification, digital signature validation, compatibility
testing, and security review").

This implements the "code inspection" piece as static AST analysis: flag dangerous
patterns (arbitrary code execution, filesystem/network/process access) that a plugin
should never need, since Ch.5.10's design constraint is "plugins shall provide data
rather than arbitrary executable logic". This is deliberately a pattern-matching scan,
not a full taint-analysis or sandboxed-execution security audit -- see ADR-012 for the
honest scope limit and why a determined malicious plugin could still evade this (e.g.
via `getattr(builtins, "e" + "val")`). It catches careless or lazy violations of the
plugin contract, not a determined adversary -- that's what digital signature validation
and human scientific review (Ch.16.5 Plugin Certification) are for, neither of which
this module replaces.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_DANGEROUS_CALL_NAMES = {
    "eval": "arbitrary code execution",
    "exec": "arbitrary code execution",
    "compile": "arbitrary code compilation",
    "__import__": "dynamic import (can load arbitrary modules)",
}

_DANGEROUS_MODULES = {
    "os": "filesystem/process access",
    "subprocess": "spawning external processes",
    "socket": "raw network access",
    "shutil": "filesystem manipulation",
    "sys": "interpreter/process manipulation",
}

_ALLOWED_STANDARD_IMPORTS = {"json", "pathlib", "typing", "dataclasses", "enum", "abc"}


@dataclass
class SecurityFinding:
    severity: str  # "high" or "medium"
    description: str
    line: int


def scan_plugin_source(source_path: Path | str) -> list[SecurityFinding]:
    """Scan one plugin source file for patterns that violate the "plugins provide data,
    not arbitrary logic" contract. Returns an empty list for a clean file.
    """
    path = Path(source_path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [
            SecurityFinding(
                severity="high", description=f"File does not parse as Python: {exc}", line=0
            )
        ]

    findings: list[SecurityFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _DANGEROUS_CALL_NAMES:
                findings.append(
                    SecurityFinding(
                        severity="high",
                        description=f"Call to '{node.func.id}()' -- {_DANGEROUS_CALL_NAMES[node.func.id]}",
                        line=node.lineno,
                    )
                )

        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if (
                    root_module in _DANGEROUS_MODULES
                    and root_module not in _ALLOWED_STANDARD_IMPORTS
                ):
                    findings.append(
                        SecurityFinding(
                            severity="medium",
                            description=f"Imports '{root_module}' -- {_DANGEROUS_MODULES[root_module]}",
                            line=node.lineno,
                        )
                    )

        if isinstance(node, ast.ImportFrom) and node.module:
            root_module = node.module.split(".")[0]
            if root_module in _DANGEROUS_MODULES and root_module not in _ALLOWED_STANDARD_IMPORTS:
                findings.append(
                    SecurityFinding(
                        severity="medium",
                        description=f"Imports from '{root_module}' -- {_DANGEROUS_MODULES[root_module]}",
                        line=node.lineno,
                    )
                )

    return findings


def scan_plugin_directory(plugin_dir: Path | str) -> dict[str, list[SecurityFinding]]:
    """Scan every .py file in a plugin package. Returns {filename: findings}, omitting
    files with no findings.
    """
    plugin_dir = Path(plugin_dir)
    results: dict[str, list[SecurityFinding]] = {}
    for py_file in sorted(plugin_dir.rglob("*.py")):
        findings = scan_plugin_source(py_file)
        if findings:
            results[py_file.relative_to(plugin_dir).as_posix()] = findings
    return results


def is_clean(scan_results: dict[str, list[SecurityFinding]]) -> bool:
    """True if a scan_plugin_directory() result has no HIGH-severity findings.
    Medium-severity findings (e.g. importing `os` for legitimate path handling in a
    quirky way) don't block certification on their own -- they're a prompt for human
    review during the Ch.16.5 certification process, not an automatic rejection.
    """
    return not any(
        finding.severity == "high" for findings in scan_results.values() for finding in findings
    )
