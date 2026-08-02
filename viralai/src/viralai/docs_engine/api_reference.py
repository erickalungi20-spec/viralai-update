"""
Automated API reference generation (engineering review Recommendation 9).

Introspects a Python package using the standard library (`pkgutil`, `inspect`) and
generates a Markdown API reference from actual docstrings and signatures -- documentation
produced as part of the build, not written by hand after the fact and left to drift out of
sync with the code.

This only documents what's actually there: modules with no public classes/functions are
skipped, and anything without a docstring is flagged rather than silently omitted, since a
missing docstring is a documentation gap worth surfacing, not hiding.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from types import ModuleType


@dataclass
class DocumentedMember:
    name: str
    kind: str  # "class" or "function"
    signature: str
    summary: str
    has_docstring: bool


@dataclass
class DocumentedModule:
    name: str
    docstring_summary: str
    members: list[DocumentedMember] = field(default_factory=list)


def discover_modules(package: ModuleType) -> list[str]:
    """All importable module names under `package`, e.g. 'viralai.core.idm'."""
    prefix = package.__name__ + "."
    return sorted(
        name for _, name, is_pkg in pkgutil.walk_packages(package.__path__, prefix) if not is_pkg
    )


def document_module(module_name: str) -> DocumentedModule:
    module = importlib.import_module(module_name)
    doc = DocumentedModule(
        name=module_name,
        docstring_summary=_first_line(inspect.getdoc(module)),
    )

    for member_name, member_obj in inspect.getmembers(module):
        if member_name.startswith("_"):
            continue
        if not (inspect.isclass(member_obj) or inspect.isfunction(member_obj)):
            continue
        if inspect.getmodule(member_obj) is not module:
            continue  # skip re-exported names -- document them at their defining module

        docstring = inspect.getdoc(member_obj)
        try:
            signature = str(inspect.signature(member_obj))
        except (ValueError, TypeError):
            signature = "(...)"

        doc.members.append(
            DocumentedMember(
                name=member_name,
                kind="class" if inspect.isclass(member_obj) else "function",
                signature=signature,
                summary=_first_line(docstring) or "(no docstring)",
                has_docstring=docstring is not None,
            )
        )

    doc.members.sort(key=lambda m: (m.kind, m.name))
    return doc


def generate_markdown(package: ModuleType) -> str:
    lines = [f"# API Reference: {package.__name__}", ""]

    undocumented: list[str] = []

    for module_name in discover_modules(package):
        doc = document_module(module_name)
        if not doc.members:
            continue  # nothing public to document in this module

        lines.append(f"## `{doc.name}`")
        if doc.docstring_summary:
            lines.append("")
            lines.append(doc.docstring_summary)
        lines.append("")

        for member in doc.members:
            lines.append(f"### `{member.name}{member.signature}`")
            lines.append("")
            lines.append(f"*{member.kind}* -- {member.summary}")
            lines.append("")
            if not member.has_docstring:
                undocumented.append(f"{doc.name}.{member.name}")

    if undocumented:
        lines.append("## Documentation gaps")
        lines.append("")
        lines.append("The following public members have no docstring:")
        lines.append("")
        for item in undocumented:
            lines.append(f"- `{item}`")
        lines.append("")

    return "\n".join(lines)


def _first_line(docstring: str | None) -> str:
    if not docstring:
        return ""
    return docstring.strip().splitlines()[0]
