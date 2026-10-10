import ast
import difflib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from src.ast_analyzer import analyze_python_file, FunctionSymbol, ClassSymbol


@dataclass
class ChangedSymbol:
    """Represents a function, class, or module symbol that has changed."""
    symbol_name: str
    symbol_type: str  # 'function', 'class', 'module'
    file_path: Path
    change_type: str  # 'modified', 'added', 'deleted'
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class ChangeDetectionResult:
    """Complete summary of changes between two versions or snapshots."""
    modified_files: List[Path] = field(default_factory=list)
    added_files: List[Path] = field(default_factory=list)
    deleted_files: List[Path] = field(default_factory=list)
    renamed_files: List[Tuple[Path, Path]] = field(default_factory=list)
    changed_symbols: List[ChangedSymbol] = field(default_factory=list)
    is_uncertain: bool = False
    warning_message: Optional[str] = None


def detect_changes_git(repo_dir: Path, target_commit: str = "HEAD~1", source_commit: str = "HEAD") -> ChangeDetectionResult:
    """Uses git diff to detect file status changes between commits or working directory."""
    repo_dir = repo_dir.resolve()
    result = ChangeDetectionResult()

    try:
        cmd = ["git", "diff", "--name-status", f"{target_commit}..{source_commit}"]
        proc = subprocess.run(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        if proc.returncode != 0:
            # Fallback to unstaged / staged diff against HEAD
            cmd = ["git", "diff", "--name-status", "HEAD"]
            proc = subprocess.run(cmd, cwd=repo_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)

        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split('\t')
                status = parts[0][0]
                if status == 'M' and len(parts) >= 2:
                    result.modified_files.append(repo_dir / parts[1])
                elif status == 'A' and len(parts) >= 2:
                    result.added_files.append(repo_dir / parts[1])
                elif status == 'D' and len(parts) >= 2:
                    result.deleted_files.append(repo_dir / parts[1])
                elif status == 'R' and len(parts) >= 3:
                    result.renamed_files.append((repo_dir / parts[1], repo_dir / parts[2]))
                    result.modified_files.append(repo_dir / parts[2])
    except Exception as e:
        result.is_uncertain = True
        result.warning_message = f"Git diff execution failed: {str(e)}. Falling back to snapshot comparison."

    return result


def detect_changes_between_files(
    old_file_path: Optional[Path],
    new_file_path: Optional[Path],
    root_path: Path
) -> List[ChangedSymbol]:
    """Compares AST symbols between two Python source file versions."""
    changed_symbols: List[ChangedSymbol] = []

    if old_file_path is None and new_file_path is not None:
        # Added file
        new_ast = analyze_python_file(new_file_path, root_path)
        changed_symbols.append(ChangedSymbol(
            symbol_name=new_ast.module_name,
            symbol_type="module",
            file_path=new_file_path,
            change_type="added"
        ))
        for func in new_ast.functions:
            changed_symbols.append(ChangedSymbol(
                symbol_name=func.qualified_name,
                symbol_type="function",
                file_path=new_file_path,
                change_type="added",
                line_start=func.start_line,
                line_end=func.end_line
            ))
        return changed_symbols

    if old_file_path is not None and new_file_path is None:
        # Deleted file
        old_ast = analyze_python_file(old_file_path, root_path)
        changed_symbols.append(ChangedSymbol(
            symbol_name=old_ast.module_name,
            symbol_type="module",
            file_path=old_file_path,
            change_type="deleted"
        ))
        return changed_symbols

    if old_file_path is None or new_file_path is None:
        return changed_symbols

    # Both file versions exist -> parse AST and compare unified diff lines against function spans
    try:
        old_content = old_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        new_content = new_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        changed_symbols.append(ChangedSymbol(
            symbol_name=new_file_path.stem,
            symbol_type="module",
            file_path=new_file_path,
            change_type="modified"
        ))
        return changed_symbols

    if old_content == new_content:
        return []

    new_ast = analyze_python_file(new_file_path, root_path)

    # Compute line diff numbers in new file
    matcher = difflib.SequenceMatcher(None, old_content, new_content)
    changed_new_lines: Set[int] = set()

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ('replace', 'insert'):
            for line_no in range(j1 + 1, j2 + 1):  # 1-indexed line numbers
                changed_new_lines.add(line_no)

    matched_function = False
    all_funcs = new_ast.functions + [m for c in new_ast.classes for m in c.methods]

    for func in all_funcs:
        func_range = set(range(func.start_line, func.end_line + 1))
        if func_range.intersection(changed_new_lines):
            matched_function = True
            changed_symbols.append(ChangedSymbol(
                symbol_name=func.qualified_name,
                symbol_type="function",
                file_path=new_file_path,
                change_type="modified",
                line_start=func.start_line,
                line_end=func.end_line
            ))

    # If changes occurred outside defined functions (e.g. module level / globals / imports), fall back to module level
    if not matched_function or not all_funcs:
        changed_symbols.append(ChangedSymbol(
            symbol_name=new_ast.module_name,
            symbol_type="module",
            file_path=new_file_path,
            change_type="modified"
        ))

    return changed_symbols


def detect_changes_snapshots(
    old_dir: Path,
    new_dir: Path
) -> ChangeDetectionResult:
    """Compares two repository snapshots (old_dir vs new_dir)."""
    old_dir = old_dir.resolve()
    new_dir = new_dir.resolve()
    result = ChangeDetectionResult()

    old_files = {p.relative_to(old_dir): p for p in old_dir.rglob("*.py")}
    new_files = {p.relative_to(new_dir): p for p in new_dir.rglob("*.py")}

    all_rel_paths = set(old_files.keys()).union(set(new_files.keys()))

    for rel_path in sorted(all_rel_paths):
        old_path = old_files.get(rel_path)
        new_path = new_files.get(rel_path)

        if old_path and not new_path:
            result.deleted_files.append(old_path)
            symbols = detect_changes_between_files(old_path, None, old_dir)
            result.changed_symbols.extend(symbols)
        elif new_path and not old_path:
            result.added_files.append(new_path)
            symbols = detect_changes_between_files(None, new_path, new_dir)
            result.changed_symbols.extend(symbols)
        elif old_path and new_path:
            symbols = detect_changes_between_files(old_path, new_path, new_dir)
            if symbols:
                result.modified_files.append(new_path)
                result.changed_symbols.extend(symbols)

    return result
