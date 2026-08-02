from pathlib import Path

from viralai.docs_engine.dependency_graph import build_dependency_graph, find_cycles, to_dot


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_build_dependency_graph_on_simple_fixture(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "from mypkg.b import something\n")
    _write(root / "b.py", "x = 1\n")

    graph = build_dependency_graph(root, package_name="mypkg")

    assert "mypkg.a" in graph.nodes
    assert "mypkg.b" in graph.nodes
    assert graph.has_edge("mypkg.a", "mypkg.b")


def test_build_dependency_graph_ignores_external_imports(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "import os\nimport numpy as np\nfrom collections import Counter\n")

    graph = build_dependency_graph(root, package_name="mypkg")

    assert list(graph.successors("mypkg.a")) == []


def test_build_dependency_graph_handles_import_statement_style(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "import mypkg.b\n")
    _write(root / "b.py", "x = 1\n")

    graph = build_dependency_graph(root, package_name="mypkg")

    assert graph.has_edge("mypkg.a", "mypkg.b")


def test_to_dot_produces_valid_looking_dot_syntax(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "from mypkg.b import x\n")
    _write(root / "b.py", "x = 1\n")

    graph = build_dependency_graph(root, package_name="mypkg")
    dot = to_dot(graph)

    assert dot.startswith("digraph dependencies {")
    assert dot.endswith("}")
    assert '"mypkg.a" -> "mypkg.b";' in dot


def test_find_cycles_detects_circular_dependency(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "from mypkg.b import x\n")
    _write(root / "b.py", "from mypkg.a import y\n")

    graph = build_dependency_graph(root, package_name="mypkg")
    cycles = find_cycles(graph)

    assert len(cycles) >= 1


def test_find_cycles_empty_for_acyclic_graph(tmp_path):
    root = tmp_path / "mypkg"
    _write(root / "__init__.py", "")
    _write(root / "a.py", "from mypkg.b import x\n")
    _write(root / "b.py", "x = 1\n")

    graph = build_dependency_graph(root, package_name="mypkg")
    assert find_cycles(graph) == []


def test_real_viralai_package_has_no_circular_dependencies():
    """A genuine architectural health check on the actual codebase, not just the test
    fixtures -- if this ever fails, it means a real circular import has been introduced.
    """
    package_root = Path(__file__).resolve().parents[2] / "src" / "viralai"
    graph = build_dependency_graph(package_root, package_name="viralai")

    cycles = find_cycles(graph)
    assert cycles == [], f"Circular dependencies detected: {cycles}"
