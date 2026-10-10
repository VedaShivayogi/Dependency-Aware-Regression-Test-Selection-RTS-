import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

from config.settings import (
    TEMP_WORKSPACE_DIR,
    IGNORE_DIRS,
    IGNORE_FILES,
)
from src.safety import safe_extract_zip, SafetyError


@dataclass
class RepositoryInfo:
    """Summary information of loaded repository."""
    repo_id: str
    root_path: Path
    total_files: int
    python_files: List[Path]
    test_files: List[Path]
    source_files: List[Path]
    is_temporary: bool = False

    def get_relative_path(self, path: Path) -> str:
        """Returns relative path string normalized with forward slashes."""
        try:
            return path.resolve().relative_to(self.root_path.resolve()).as_posix()
        except ValueError:
            return path.as_posix()


def is_ignored(path: Path, root_path: Path) -> bool:
    """Checks if a path or any of its parent directories match ignore criteria."""
    try:
        rel_parts = path.relative_to(root_path).parts
    except ValueError:
        rel_parts = path.parts

    for part in rel_parts:
        if part in IGNORE_DIRS or part.startswith('.'):
            return True
        for pattern in IGNORE_DIRS:
            if pattern.startswith('*') and part.endswith(pattern[1:]):
                return True
    return False


def scan_repository(root_path: Path) -> RepositoryInfo:
    """Scans a repository directory to locate Python files, test files, and source files."""
    root_path = root_path.resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise FileNotFoundError(f"Repository directory does not exist: {root_path}")

    repo_id = str(uuid.uuid4())[:8]
    total_files = 0
    python_files: List[Path] = []
    test_files: List[Path] = []
    source_files: List[Path] = []

    for file_path in root_path.rglob("*"):
        if file_path.is_file():
            if is_ignored(file_path, root_path):
                continue

            total_files += 1

            if file_path.suffix.lower() == ".py":
                python_files.append(file_path)
                filename = file_path.name.lower()
                rel_posix = file_path.relative_to(root_path).as_posix().lower()

                # Test file heuristics: named test_*.py or *_test.py or in tests/ directory
                if (filename.startswith("test_") or 
                    filename.endswith("_test.py") or 
                    "tests/" in rel_posix or 
                    "/test/" in rel_posix):
                    test_files.append(file_path)
                else:
                    source_files.append(file_path)

    return RepositoryInfo(
        repo_id=repo_id,
        root_path=root_path,
        total_files=total_files,
        python_files=python_files,
        test_files=test_files,
        source_files=source_files,
        is_temporary=False,
    )


def load_repository_from_zip(zip_path: Path) -> RepositoryInfo:
    """Safely unpacks a ZIP upload into temporary directory and scans structure."""
    temp_dir_name = f"upload_{uuid.uuid4().hex[:10]}"
    target_dir = TEMP_WORKSPACE_DIR / temp_dir_name

    extracted_dir = safe_extract_zip(zip_path, target_dir)
    
    # Handle single nested directory in zip (e.g., repo-main/...)
    subitems = [item for item in extracted_dir.iterdir() if not item.name.startswith('.')]
    if len(subitems) == 1 and subitems[0].is_dir():
        scan_root = subitems[0]
    else:
        scan_root = extracted_dir

    repo_info = scan_repository(scan_root)
    repo_info.is_temporary = True
    return repo_info


def get_file_tree(root_path: Path) -> Dict[str, Any]:
    """Builds a nested dictionary representation of the directory tree."""
    tree: Dict[str, Any] = {"name": root_path.name, "type": "directory", "children": []}

    def build_node(current_path: Path) -> Dict[str, Any]:
        node: Dict[str, Any] = {
            "name": current_path.name,
            "path": current_path.as_posix(),
            "type": "directory" if current_path.is_dir() else "file",
        }
        if current_path.is_dir():
            children = []
            for child in sorted(current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if is_ignored(child, root_path):
                    continue
                children.append(build_node(child))
            node["children"] = children
        return node

    return build_node(root_path)


def cleanup_repository(repo_info: RepositoryInfo) -> None:
    """Removes temporary repository directory if repo_info is temporary."""
    if repo_info.is_temporary and repo_info.root_path.exists():
        shutil.rmtree(repo_info.root_path, ignore_errors=True)
