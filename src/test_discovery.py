import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Optional

from src.ast_analyzer import analyze_python_file


@dataclass
class TestItem:
    """Represents a discovered test function or method."""
    __test__ = False
    test_id: str  # e.g., "tests/test_cart.py::test_add_to_cart"
    file_path: Path
    module_name: str
    func_name: str
    class_name: Optional[str] = None
    line_number: int = 1


def discover_tests_via_ast(test_files: List[Path], root_path: Path) -> List[TestItem]:
    """Discovers tests in test_files statically using AST analysis."""
    root_path = root_path.resolve()
    discovered: List[TestItem] = []

    for test_file in test_files:
        test_file = test_file.resolve()
        ast_info = analyze_python_file(test_file, root_path)

        try:
            rel_file_str = test_file.relative_to(root_path).as_posix()
        except ValueError:
            rel_file_str = test_file.as_posix()

        # Standalone test functions
        for func in ast_info.functions:
            if func.name.startswith("test_") or func.name.endswith("_test"):
                test_id = f"{rel_file_str}::{func.name}"
                discovered.append(TestItem(
                    test_id=test_id,
                    file_path=test_file,
                    module_name=ast_info.module_name,
                    func_name=func.name,
                    line_number=func.start_line
                ))

        # Test class methods
        for cls in ast_info.classes:
            if cls.name.startswith("Test") or cls.name.endswith("Test") or cls.name.endswith("Tests"):
                for method in cls.methods:
                    if method.name.startswith("test_") or method.name.endswith("_test"):
                        test_id = f"{rel_file_str}::{cls.name}::{method.name}"
                        discovered.append(TestItem(
                            test_id=test_id,
                            file_path=test_file,
                            module_name=ast_info.module_name,
                            func_name=method.name,
                            class_name=cls.name,
                            line_number=method.start_line
                        ))

    return discovered
