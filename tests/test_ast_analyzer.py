import pytest
from pathlib import Path
from src.ast_analyzer import analyze_python_file, analyze_repository_ast


def test_analyze_valid_python_file(tmp_path):
    py_file = tmp_path / "math_utils.py"
    py_file.write_text(
        "import math\n"
        "from os import path\n\n"
        "class Calculator:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n\n"
        "def compute_square(x):\n"
        "    calc = Calculator()\n"
        "    return calc.add(x, x)\n",
        encoding="utf-8"
    )

    ast_info = analyze_python_file(py_file, tmp_path)
    assert ast_info.syntax_error is None
    assert ast_info.module_name == "math_utils"
    assert len(ast_info.imports) == 2
    assert len(ast_info.classes) == 1
    assert len(ast_info.functions) == 1  # compute_square (add is inside class)
    assert ast_info.classes[0].name == "Calculator"
    assert len(ast_info.classes[0].methods) == 1


def test_analyze_invalid_syntax_file(tmp_path):
    py_file = tmp_path / "broken.py"
    py_file.write_text("def broken_func(:\n    pass\n", encoding="utf-8")

    ast_info = analyze_python_file(py_file, tmp_path)
    assert ast_info.syntax_error is not None
    assert "syntax" in ast_info.syntax_error.message.lower()
