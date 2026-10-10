import pytest
from src.test_runner import TestExecutionResult, SingleTestOutcome
from src.test_selector import SelectionRationale
from src.metrics import calculate_metrics


def test_calculate_metrics_zero_denominators():
    full_res = TestExecutionResult(
        total_discovered=10,
        total_selected=10,
        total_executed=10,
        passed_count=10,
        failed_count=0,
        skipped_count=0,
        error_count=0,
        duration_seconds=10.0,
        exit_code=0,
        is_success=True
    )

    selected_res = TestExecutionResult(
        total_discovered=10,
        total_selected=3,
        total_executed=3,
        passed_count=3,
        failed_count=0,
        skipped_count=0,
        error_count=0,
        duration_seconds=3.0,
        exit_code=0,
        is_success=True
    )

    rat = SelectionRationale(
        selection_mode="dependency_aware",
        selected_test_ids=["t1", "t2", "t3"]
    )

    m = calculate_metrics("dependency_aware", selected_res, full_res, rat)

    assert m.selection_ratio == 0.3
    assert m.time_reduction_percent == 70.0
    assert m.failure_detection_rate == 100.0  # 0 known failures -> 100%
    assert m.missed_regressions_count == 0


def test_calculate_metrics_with_failures():
    full_res = TestExecutionResult(
        total_discovered=5,
        total_selected=5,
        total_executed=5,
        passed_count=3,
        failed_count=2,
        skipped_count=0,
        error_count=0,
        duration_seconds=10.0,
        exit_code=1,
        test_outcomes=[
            SingleTestOutcome("test1", "failed", 1.0),
            SingleTestOutcome("test2", "failed", 1.0),
            SingleTestOutcome("test3", "passed", 1.0),
            SingleTestOutcome("test4", "passed", 1.0),
            SingleTestOutcome("test5", "passed", 1.0),
        ]
    )

    selected_res = TestExecutionResult(
        total_discovered=5,
        total_selected=2,
        total_executed=2,
        passed_count=1,
        failed_count=1,
        skipped_count=0,
        error_count=0,
        duration_seconds=4.0,
        exit_code=1,
        test_outcomes=[
            SingleTestOutcome("test1", "failed", 1.0),
            SingleTestOutcome("test3", "passed", 1.0),
        ]
    )

    rat = SelectionRationale(
        selection_mode="dependency_aware",
        selected_test_ids=["test1", "test3"]
    )

    m = calculate_metrics("dependency_aware", selected_res, full_res, rat)
    assert m.regressions_detected == 1
    assert m.total_known_regressions == 2
    assert m.failure_detection_rate == 50.0
    assert m.missed_regressions_count == 1
