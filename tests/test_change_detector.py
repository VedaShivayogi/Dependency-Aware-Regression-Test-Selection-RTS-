import pytest
from pathlib import Path
from src.change_detector import detect_changes_snapshots, detect_changes_between_files


def test_detect_changes_between_snapshots(tmp_path):
    v1_dir = tmp_path / "v1"
    v2_dir = tmp_path / "v2"
    v1_dir.mkdir()
    v2_dir.mkdir()

    (v1_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (v2_dir / "utils.py").write_text("def add(a, b):\n    return a + b + 0\n", encoding="utf-8")

    res = detect_changes_snapshots(v1_dir, v2_dir)
    assert len(res.modified_files) == 1
    assert res.modified_files[0].name == "utils.py"
    assert len(res.changed_symbols) > 0


def test_detect_added_file(tmp_path):
    v1_dir = tmp_path / "v1"
    v2_dir = tmp_path / "v2"
    v1_dir.mkdir()
    v2_dir.mkdir()

    (v2_dir / "new_module.py").write_text("def new_func(): pass\n", encoding="utf-8")

    res = detect_changes_snapshots(v1_dir, v2_dir)
    assert len(res.added_files) == 1
    assert res.added_files[0].name == "new_module.py"
