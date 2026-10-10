import pytest
from pathlib import Path
from src.dependency_graph import DependencyGraph


def test_dependency_graph_building(tmp_path):
    mod_a = tmp_path / "mod_a.py"
    mod_b = tmp_path / "mod_b.py"

    mod_a.write_text("def func_a():\n    return 42\n", encoding="utf-8")
    mod_b.write_text("from mod_a import func_a\ndef func_b():\n    return func_a()\n", encoding="utf-8")

    dep_graph = DependencyGraph(tmp_path)
    g = dep_graph.build_graph([mod_a, mod_b])

    assert "mod:mod_a" in g
    assert "mod:mod_b" in g
    assert "func:mod_a.func_a" in g
    assert "func:mod_b.func_b" in g

    # mod_b imports mod_a
    assert g.has_edge("mod:mod_b", "mod:mod_a")
    # func_b calls func_a
    assert g.has_edge("func:mod_b.func_b", "func:mod_a.func_a")


def test_circular_dependency_handling(tmp_path):
    mod_x = tmp_path / "mod_x.py"
    mod_y = tmp_path / "mod_y.py"

    mod_x.write_text("import mod_y\ndef x_fn(): pass\n", encoding="utf-8")
    mod_y.write_text("import mod_x\ndef y_fn(): pass\n", encoding="utf-8")

    dep_graph = DependencyGraph(tmp_path)
    g = dep_graph.build_graph([mod_x, mod_y])

    assert g.has_edge("mod:mod_x", "mod:mod_y")
    assert g.has_edge("mod:mod_y", "mod:mod_x")

    # Traverse dependents without infinite loop
    dependents_x = dep_graph.get_dependent_nodes("mod:mod_x")
    assert "mod:mod_y" in dependents_x
