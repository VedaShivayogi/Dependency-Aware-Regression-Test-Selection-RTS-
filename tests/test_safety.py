import io
import zipfile
import pytest
from pathlib import Path
from src.safety import validate_zip_file, safe_extract_zip, SafetyError


def test_validate_zip_file_path_traversal(tmp_path):
    zip_file_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("../evil.py", "print('hacked')")

    is_valid, msg = validate_zip_file(zip_file_path)
    assert not is_valid
    assert "Path traversal" in msg


def test_validate_zip_file_valid(tmp_path):
    zip_file_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("app/main.py", "print('hello')")

    is_valid, msg = validate_zip_file(zip_file_path)
    assert is_valid
    assert "validated successfully" in msg


def test_safe_extract_zip_prevents_traversal(tmp_path):
    zip_file_path = tmp_path / "bad.zip"
    target_extract = tmp_path / "extracted"

    with zipfile.ZipFile(zip_file_path, "w") as zf:
        zf.writestr("../../outside.py", "bad code")

    with pytest.raises(SafetyError):
        safe_extract_zip(zip_file_path, target_extract)
