"""
Phase 6 Automated Documentation Engine (engineering review Recommendation 9):
introspection-based Markdown API reference generation, and AST-based module dependency
graph generation (DOT export, cycle detection).
"""

from viralai.docs_engine.api_reference import discover_modules, document_module, generate_markdown
from viralai.docs_engine.dependency_graph import build_dependency_graph, find_cycles, to_dot

__all__ = [
    "discover_modules",
    "document_module",
    "generate_markdown",
    "build_dependency_graph",
    "to_dot",
    "find_cycles",
]
