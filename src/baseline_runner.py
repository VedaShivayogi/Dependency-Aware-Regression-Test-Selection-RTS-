from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.repository_loader import scan_repository
from src.dependency_graph import DependencyGraph
from src.change_detector import ChangeDetectionResult, detect_changes_snapshots
from src.test_discovery import discover_tests_via_ast, TestItem
from src.test_selector import TestSelector, SelectionRationale
from src.test_runner import run_tests_safe, TestExecutionResult


@dataclass
class ModeComparisonResult:
    """Stores selection rationale and test execution results for a single mode."""
    mode_name: str
    rationale: SelectionRationale
    execution_result: TestExecutionResult


def run_all_modes_comparison(
    repo_root: Path,
    changes: ChangeDetectionResult,
    conservative: bool = True,
    timeout_sec: int = 60
) -> Dict[str, ModeComparisonResult]:
    """
    Executes and compares all three test selection modes on a repository snapshot:
    1. Full Suite (Mode 1)
    2. Changed-File Baseline (Mode 2)
    3. Dependency-Aware Selection (Mode 3)
    """
    repo_info = scan_repository(repo_root)
    dep_graph = DependencyGraph(repo_root)
    dep_graph.build_graph(repo_info.python_files)

    all_tests = discover_tests_via_ast(repo_info.test_files, repo_root)
    total_discovered = len(all_tests)

    selector = TestSelector(dep_graph, all_tests)

    results: Dict[str, ModeComparisonResult] = {}

    for mode in ["full", "changed_file", "dependency_aware"]:
        rationale = selector.select_tests(mode, changes, conservative=conservative)
        exec_result = run_tests_safe(
            repo_root=repo_root,
            test_ids=rationale.selected_test_ids,
            total_discovered_count=total_discovered,
            timeout_sec=timeout_sec
        )
        results[mode] = ModeComparisonResult(
            mode_name=mode,
            rationale=rationale,
            execution_result=exec_result
        )

    return results
