import pytest
from src.metrics import EvaluationMetrics
from src.experiment_runner import ScenarioResult
from src.report_generator import generate_markdown_experiment_report


def test_generate_markdown_experiment_report():
    m_full = EvaluationMetrics(
        mode_name="full",
        total_tests_available=10,
        tests_selected=10,
        tests_executed=10,
        selection_ratio=1.0,
        execution_time_seconds=10.0,
        time_reduction_percent=0.0,
        regressions_detected=1,
        total_known_regressions=1,
        failure_detection_rate=100.0,
        missed_regressions_count=0,
        precision=0.1,
        recall=1.0,
        execution_success_rate=100.0,
        analysis_overhead_seconds=0.1,
        unresolved_dependencies_count=0
    )

    m_dep = EvaluationMetrics(
        mode_name="dependency_aware",
        total_tests_available=10,
        tests_selected=3,
        tests_executed=3,
        selection_ratio=0.3,
        execution_time_seconds=3.0,
        time_reduction_percent=70.0,
        regressions_detected=1,
        total_known_regressions=1,
        failure_detection_rate=100.0,
        missed_regressions_count=0,
        precision=0.3333,
        recall=1.0,
        execution_success_rate=100.0,
        analysis_overhead_seconds=0.1,
        unresolved_dependencies_count=0
    )

    sr = ScenarioResult(
        scenario_id="S1",
        scenario_name="Test Scenario",
        repo_path="/path/to/repo",
        timestamp="2026-10-10",
        python_version="3.10.9",
        metrics={"full": m_full, "dependency_aware": m_dep}
    )

    report_md = generate_markdown_experiment_report([sr])
    assert "# Experimental Evaluation Report" in report_md
    assert "`dependency_aware`" in report_md
    assert "70.0%" in report_md
