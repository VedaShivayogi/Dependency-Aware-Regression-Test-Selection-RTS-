import pytest
from pathlib import Path
from src.dependency_graph import DependencyGraph
from src.change_detector import ChangeDetectionResult, ChangedSymbol
from src.test_discovery import TestItem
from src.test_selector import TestSelector


def test_test_selector_modes(tmp_path):
    root = tmp_path
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (root / "test_calc.py").write_text("from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
    (root / "test_other.py").write_text("def test_unrelated():\n    assert True\n", encoding="utf-8")

    dep_graph = DependencyGraph(root)
    dep_graph.build_graph([root / "calc.py", root / "test_calc.py", root / "test_other.py"])

    all_tests = [
        TestItem("test_calc.py::test_add", root / "test_calc.py", "test_calc", "test_add"),
        TestItem("test_other.py::test_unrelated", root / "test_other.py", "test_other", "test_unrelated"),
    ]

    selector = TestSelector(dep_graph, all_tests)

    # 1. Full Suite
    full_rat = selector.select_full_suite()
    assert len(full_rat.selected_test_ids) == 2

    # 2. Dependency Aware for change in calc.py
    changes = ChangeDetectionResult(
        modified_files=[root / "calc.py"],
        changed_symbols=[ChangedSymbol("calc.add", "function", root / "calc.py", "modified")]
    )

    dep_rat = selector.select_dependency_aware(changes, conservative=False)
    assert "test_calc.py::test_add" in dep_rat.selected_test_ids
    assert "test_other.py::test_unrelated" not in dep_rat.selected_test_ids
