import json
import os
import platform
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd

from config.settings import RESULTS_DIR
from src.repository_loader import scan_repository
from src.dependency_graph import DependencyGraph
from src.change_detector import ChangeDetectionResult, detect_changes_snapshots
from src.test_discovery import discover_tests_via_ast
from src.test_selector import TestSelector
from src.test_runner import run_tests_safe
from src.metrics import calculate_metrics, EvaluationMetrics


@dataclass
class ScenarioResult:
    """Stores experimental evaluation results for a single test scenario."""
    scenario_id: str
    scenario_name: str
    repo_path: str
    timestamp: str
    python_version: str
    metrics: Dict[str, EvaluationMetrics]  # mode_name -> EvaluationMetrics


class ExperimentRunner:
    """Automated benchmark runner for executing controlled code-change experiments."""

    def __init__(self, output_dir: Path = RESULTS_DIR):
        self.output_dir = output_dir.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_scenario(
        self,
        scenario_id: str,
        scenario_name: str,
        base_repo_path: Path,
        changed_repo_path: Path,
        repetitions: int = 1
    ) -> ScenarioResult:
        """
        Runs experiment scenario comparing base_repo vs changed_repo.
        Executes Mode 1 (Full Suite), Mode 2 (Changed-File), and Mode 3 (Dependency-Aware).
        Averages timing over specified repetitions.
        """
        base_repo_path = base_repo_path.resolve()
        changed_repo_path = changed_repo_path.resolve()

        # Step 1: Detect changes between base and changed snapshots
        changes = detect_changes_snapshots(base_repo_path, changed_repo_path)

        # Step 2: Build AST and Dependency Graph on changed repo
        start_overhead = time.time()
        repo_info = scan_repository(changed_repo_path)
        dep_graph = DependencyGraph(changed_repo_path)
        dep_graph.build_graph(repo_info.python_files)
        analysis_overhead_sec = time.time() - start_overhead

        # Step 3: Discover tests
        all_tests = discover_tests_via_ast(repo_info.test_files, changed_repo_path)
        selector = TestSelector(dep_graph, all_tests)

        # Step 4: Run Mode 1 (Full Suite) reference
        full_rationale = selector.select_full_suite()
        full_exec = run_tests_safe(changed_repo_path, full_rationale.selected_test_ids, len(all_tests))

        metrics_map: Dict[str, EvaluationMetrics] = {}

        # Step 5: Evaluate all 3 modes
        for mode in ["full", "changed_file", "dependency_aware"]:
            rationale = selector.select_tests(mode, changes)

            # Average execution over repetitions if requested
            exec_times = []
            final_exec_result = None

            for i in range(repetitions):
                exec_result = run_tests_safe(changed_repo_path, rationale.selected_test_ids, len(all_tests))
                exec_times.append(exec_result.duration_seconds)
                final_exec_result = exec_result

            if final_exec_result and exec_times:
                final_exec_result.duration_seconds = sum(exec_times) / len(exec_times)

            m = calculate_metrics(
                mode_name=mode,
                selected_result=final_exec_result,
                full_suite_result=full_exec,
                rationale=rationale,
                analysis_overhead_sec=analysis_overhead_sec
            )
            metrics_map[mode] = m

        scenario_res = ScenarioResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            repo_path=str(changed_repo_path),
            timestamp=datetime.now().isoformat(),
            python_version=sys.version.split()[0],
            metrics=metrics_map
        )

        return scenario_res

    def export_results(self, scenario_results: List[ScenarioResult], filename_prefix: str = "experiment_results") -> Tuple[Path, Path]:
        """Exports experiment results to CSV and JSON files."""
        json_path = self.output_dir / f"{filename_prefix}.json"
        csv_path = self.output_dir / f"{filename_prefix}.csv"

        rows = []
        serializable_list = []

        for sr in scenario_results:
            sr_dict = {
                "scenario_id": sr.scenario_id,
                "scenario_name": sr.scenario_name,
                "repo_path": sr.repo_path,
                "timestamp": sr.timestamp,
                "python_version": sr.python_version,
                "metrics": {m_name: asdict(m_val) for m_name, m_val in sr.metrics.items()}
            }
            serializable_list.append(sr_dict)

            for m_name, m_val in sr.metrics.items():
                row = {
                    "Scenario ID": sr.scenario_id,
                    "Scenario Name": sr.scenario_name,
                    "Selection Mode": m_name,
                    "Tests Selected": m_val.tests_selected,
                    "Total Tests": m_val.total_tests_available,
                    "Selection Ratio (%)": round(m_val.selection_ratio * 100, 2),
                    "Exec Time (s)": m_val.execution_time_seconds,
                    "Time Reduction (%)": m_val.time_reduction_percent,
                    "Regressions Detected": m_val.regressions_detected,
                    "Known Regressions": m_val.total_known_regressions,
                    "Detection Rate (%)": m_val.failure_detection_rate,
                    "Missed Regressions": m_val.missed_regressions_count,
                    "Precision": m_val.precision,
                    "Recall": m_val.recall,
                    "Analysis Overhead (s)": m_val.analysis_overhead_seconds,
                }
                rows.append(row)

        json_path.write_text(json.dumps(serializable_list, indent=2), encoding="utf-8")
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False)

        return csv_path, json_path
