from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Any

from src.test_runner import TestExecutionResult
from src.test_selector import SelectionRationale


@dataclass
class EvaluationMetrics:
    """Calculated metrics comparing test selection mode against full suite reference."""
    mode_name: str
    total_tests_available: int
    tests_selected: int
    tests_executed: int
    selection_ratio: float  # Selected / Available
    execution_time_seconds: float
    time_reduction_percent: float  # (Full_time - Mode_time) / Full_time * 100
    regressions_detected: int
    total_known_regressions: int
    failure_detection_rate: float  # Detected / Known * 100
    missed_regressions_count: int
    precision: float  # Selected_Affected / Selected
    recall: float  # Selected_Affected / Total_Affected
    execution_success_rate: float  # Executed / Selected * 100
    analysis_overhead_seconds: float
    unresolved_dependencies_count: int


def calculate_metrics(
    mode_name: str,
    selected_result: TestExecutionResult,
    full_suite_result: TestExecutionResult,
    rationale: SelectionRationale,
    analysis_overhead_sec: float = 0.0,
    known_failing_test_ids: Optional[Set[str]] = None
) -> EvaluationMetrics:
    """Calculates quantitative metrics comparing selected mode against full-suite baseline."""
    total_available = full_suite_result.total_discovered or full_suite_result.total_selected or 1
    selected_count = selected_result.total_selected
    executed_count = selected_result.total_executed

    # Selection ratio
    selection_ratio = (selected_count / total_available) if total_available > 0 else 0.0

    # Execution time reduction
    full_time = full_suite_result.duration_seconds
    sel_time = selected_result.duration_seconds
    if full_time > 0:
        time_reduction_pct = max(0.0, ((full_time - sel_time) / full_time) * 100.0)
    else:
        time_reduction_pct = 0.0

    # Failure detection metrics
    full_failing_tests = {
        outcome.test_id for outcome in full_suite_result.test_outcomes
        if outcome.status in ("failed", "error")
    }

    if known_failing_test_ids is not None:
        ground_truth_failures = known_failing_test_ids
    else:
        ground_truth_failures = full_failing_tests

    selected_failing_tests = {
        outcome.test_id for outcome in selected_result.test_outcomes
        if outcome.status in ("failed", "error")
    }

    detected_regressions = len(selected_failing_tests.intersection(ground_truth_failures))
    total_regressions = len(ground_truth_failures)

    if total_regressions > 0:
        failure_detection_rate = (detected_regressions / total_regressions) * 100.0
    else:
        failure_detection_rate = 100.0  # No regressions existed to miss

    missed_regressions = max(0, total_regressions - detected_regressions)

    # Precision & Recall against ground truth affected/failing tests
    selected_set = set(rationale.selected_test_ids)
    affected_selected = selected_set.intersection(ground_truth_failures)

    precision = (len(affected_selected) / len(selected_set)) if selected_set else 1.0
    recall = (len(affected_selected) / len(ground_truth_failures)) if ground_truth_failures else 1.0

    # Execution success rate
    success_rate = (executed_count / selected_count * 100.0) if selected_count > 0 else 100.0

    unresolved_count = len(rationale.uncertainty_warnings)

    return EvaluationMetrics(
        mode_name=mode_name,
        total_tests_available=total_available,
        tests_selected=selected_count,
        tests_executed=executed_count,
        selection_ratio=round(selection_ratio, 4),
        execution_time_seconds=round(sel_time, 3),
        time_reduction_percent=round(time_reduction_pct, 2),
        regressions_detected=detected_regressions,
        total_known_regressions=total_regressions,
        failure_detection_rate=round(failure_detection_rate, 2),
        missed_regressions_count=missed_regressions,
        precision=round(precision, 4),
        recall=round(recall, 4),
        execution_success_rate=round(success_rate, 2),
        analysis_overhead_seconds=round(analysis_overhead_sec, 3),
        unresolved_dependencies_count=unresolved_count
    )
