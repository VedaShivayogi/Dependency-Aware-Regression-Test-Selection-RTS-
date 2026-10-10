import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Tuple, List

from config.settings import (
    MAX_ZIP_SIZE_BYTES,
    MAX_EXTRACTED_FILES,
    MAX_FILE_SIZE_BYTES,
)


class SafetyError(Exception):
    """Custom exception raised for security or isolation validation failures."""
    pass


def validate_zip_file(zip_path: Path) -> Tuple[bool, str]:
    """
    Validates a ZIP file before extraction for security risks:
    - Path traversal attacks (Zip Slip)
    - File size limits
    - Total extracted file counts
    """
    if not zip_path.exists():
        return False, f"File does not exist: {zip_path}"

    if zip_path.stat().st_size > MAX_ZIP_SIZE_BYTES:
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        return False, f"ZIP file size ({size_mb:.2f} MB) exceeds maximum allowed limit of {MAX_ZIP_SIZE_BYTES // (1024 * 1024)} MB."

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            infolist = zf.infolist()
            if len(infolist) > MAX_EXTRACTED_FILES:
                return False, f"ZIP contains {len(infolist)} files, exceeding limit of {MAX_EXTRACTED_FILES} files."

            total_uncompressed = 0
            for member in infolist:
                # Zip slip prevention: check target path normalization
                filename = member.filename
                if filename.startswith('/') or filename.startswith('\\') or '..' in filename:
                    return False, f"Path traversal attempt detected in ZIP member: '{filename}'"

                total_uncompressed += member.file_size
                if member.file_size > MAX_FILE_SIZE_BYTES:
                    return False, f"Member '{filename}' size exceeds per-file limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."

    except zipfile.BadZipFile:
        return False, "Invalid or corrupted ZIP archive."
    except Exception as e:
        return False, f"Error inspecting ZIP archive: {str(e)}"

    return True, "ZIP file validated successfully."


def safe_extract_zip(zip_path: Path, target_dir: Path) -> Path:
    """
    Safely extracts a ZIP archive into target_dir preventing path traversal.
    """
    is_valid, message = validate_zip_file(zip_path)
    if not is_valid:
        raise SafetyError(message)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_dir_resolved = target_dir.resolve()

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.infolist():
            member_path = (target_dir / member.filename).resolve()
            # Ensure target path stays strictly inside target_dir
            try:
                member_path.relative_to(target_dir_resolved)
            except ValueError:
                raise SafetyError(f"Attempted path traversal extraction: {member.filename}")

            zf.extract(member, target_dir)

    return target_dir


def is_docker_available() -> bool:
    """Checks if Docker engine is running and accessible."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def get_execution_safety_warning() -> str:
    """Returns safety and isolation warning message for the UI/reports."""
    docker_status = "Available" if is_docker_available() else "Unavailable (Falling back to Subprocess Isolation)"
    return (
        f"SECURITY NOTICE & SAFETY ISOLATION:\n"
        f"- Docker Status: {docker_status}\n"
        f"- Subprocess isolation executes tests in separate process spaces with wall-clock timeouts.\n"
        f"- Caution: Running tests executes arbitrary Python code in the target environment.\n"
        f"- Never execute untrusted code without explicit verification."
    )
