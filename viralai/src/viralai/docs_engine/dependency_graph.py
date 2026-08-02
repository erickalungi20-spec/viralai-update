"""
Module dependency graph generation (engineering review Recommendation 9).

Parses internal `viralai.*` imports out of each source file using the `ast` module (no
code execution, so this is safe to run on any source tree, not just importable ones), and
builds a `networkx.DiGraph` of module-to-module dependencies. Exports to Graphviz DOT
format -- plain text, no `graphviz` binary dependency required to *generate* the file;
rendering it to an image needs `dot` installed locally, which is a reasonable thing to
require of a developer machine rather than bundle as a Python dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path

import networkx as nx


def build_dependency_graph(package_root: Path | str, package_name: str = "viralai") -> nx.DiGraph:
    """Walk every `.py` file under `package_root`, extract its internal
    `package_name.*` imports, and return a directed graph (module -> module it imports).
    """
    package_root = Path(package_root)
    graph = nx.DiGraph()

    for py_file in sorted(package_root.rglob("*.py")):
        module_name = _module_name_for_file(py_file, package_root, package_name)
        if module_name is None:
            continue
        graph.add_node(module_name)

        for imported in _extract_internal_imports(py_file, package_name):
            if imported != module_name:
                graph.add_edge(module_name, imported)

    return graph


def to_dot(graph: nx.DiGraph) -> str:
    """Render `graph` as Graphviz DOT text."""
    lines = ["digraph dependencies {", "  rankdir=LR;"]
    for node in graph.nodes:
        lines.append(f'  "{node}";')
    for source, target in graph.edges:
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)


def find_cycles(graph: nx.DiGraph) -> list[list[str]]:
    """Circular internal dependencies -- a real architectural smell worth surfacing.
    Uses networkx's cycle detection rather than hand-rolling graph traversal, same
    reasoning as ADR-006's choice to use networkx for the Research Graph.
    """
    return list(nx.simple_cycles(graph))


def _module_name_for_file(py_file: Path, package_root: Path, package_name: str) -> str | None:
    try:
        relative = py_file.relative_to(package_root)
    except ValueError:
        return None
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return package_name
    return package_name + "." + ".".join(parts)


def _extract_internal_imports(py_file: Path, package_name: str) -> set[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(package_name + ".") or alias.name == package_name:
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (
                node.module.startswith(package_name + ".") or node.module == package_name
            ):
                imports.add(node.module)
    return imports
