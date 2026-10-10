import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
SRC_DIR = BASE_DIR / "src"
RESULTS_DIR = BASE_DIR / "results"
EXPERIMENTS_DIR = BASE_DIR / "experiments"
SAMPLE_PROJECTS_DIR = BASE_DIR / "sample_projects"
TEMP_WORKSPACE_DIR = BASE_DIR / "temp_workspaces"

# Ensure essential directories exist
for directory in [RESULTS_DIR, TEMP_WORKSPACE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Safety & Resource Limitations
MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_EXTRACTED_FILES = 1000
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_TEST_TIMEOUT_SEC = 60
MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB

# Analysis Settings
IGNORE_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
    ".venv", "venv", "env", "build", "dist", ".eggs", "*.egg-info",
    "node_modules", ".idea", ".vscode"
}

IGNORE_FILES = {
    ".gitignore", "pyproject.toml", "requirements.txt", "setup.py",
    "README.md", "LICENSE"
}
