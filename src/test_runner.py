import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from config.settings import DEFAULT_TEST_TIMEOUT_SEC


@dataclass
class SingleTestOutcome:
    """Outcome of an individual test execution."""
    test_id: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float
    failure_message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestExecutionResult:
    """Overall result summary of a pytest execution run."""
    __test__ = False
    total_discovered: int
    total_selected: int
    total_executed: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_count: int
    duration_seconds: float
    exit_code: int
    is_timeout: bool = False
    is_success: bool = False
    status_summary: str = "Completed"
    test_outcomes: List[SingleTestOutcome] = field(default_factory=list)
    raw_output: str = ""


def run_tests_safe(
    repo_root: Path,
    test_ids: List[str],
    total_discovered_count: int,
    timeout_sec: int = DEFAULT_TEST_TIMEOUT_SEC,
    use_docker: bool = False
) -> TestExecutionResult:
    """
    Executes selected test IDs safely in an isolated subprocess with timeout and pytest-json-report collection.
    """
    repo_root = repo_root.resolve()
    if not test_ids:
        return TestExecutionResult(
            total_discovered=total_discovered_count,
            total_selected=0,
            total_executed=0,
            passed_count=0,
            failed_count=0,
            skipped_count=0,
            error_count=0,
            duration_seconds=0.0,
            exit_code=0,
            is_success=True,
            status_summary="No tests selected for execution."
        )

    # Prepare temporary report file path
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_report:
        report_json_path = Path(tmp_report.name)

    try:
        # Construct pytest command line
        cmd = [
            "python", "-m", "pytest",
            *test_ids,
            "--json-report",
            f"--json-report-file={report_json_path.as_posix()}",
            "-v",
            "--tb=short"
        ]

        start_time = time.time()

        try:
            proc = subprocess.run(
                cmd,
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec
            )
            wall_clock_duration = time.time() - start_time
            exit_code = proc.returncode
            raw_stdout = proc.stdout + "\n" + proc.stderr
            is_timeout = False
        except subprocess.TimeoutExpired as te:
            wall_clock_duration = time.time() - start_time
            return TestExecutionResult(
                total_discovered=total_discovered_count,
                total_selected=len(test_ids),
                total_executed=0,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                error_count=len(test_ids),
                duration_seconds=wall_clock_duration,
                exit_code=-1,
                is_timeout=True,
                is_success=False,
                status_summary=f"Test execution timed out after {timeout_sec} seconds.",
                raw_output=te.stdout.decode() if te.stdout else "Process timed out."
            )

        # Parse pytest JSON report
        outcomes: List[SingleTestOutcome] = []
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        if report_json_path.exists() and report_json_path.stat().st_size > 0:
            try:
                report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
                for test_data in report_data.get("tests", []):
                    nodeid = test_data.get("nodeid", "")
                    outcome_str = test_data.get("outcome", "failed")
                    dur = test_data.get("duration", 0.0)

                    fail_msg = None
                    tb = None
                    call_stage = test_data.get("call", {}) or test_data.get("setup", {})
                    if "longrepr" in call_stage:
                        tb = str(call_stage["longrepr"])
                        fail_msg = tb.splitlines()[-1] if tb.splitlines() else "Test failed."

                    if outcome_str == "passed":
                        passed += 1
                    elif outcome_str == "failed":
                        failed += 1
                    elif outcome_str == "skipped":
                        skipped += 1
                    else:
                        errors += 1

                    outcomes.append(SingleTestOutcome(
                        test_id=nodeid,
                        status=outcome_str,
                        duration=dur,
                        failure_message=fail_msg,
                        traceback=tb
                    ))
            except Exception as pe:
                raw_stdout += f"\n[Warning] Failed to parse JSON report: {str(pe)}"

        total_executed = len(outcomes)
        is_success = (exit_code == 0) or (exit_code == 1 and total_executed > 0)

        return TestExecutionResult(
            total_discovered=total_discovered_count,
            total_selected=len(test_ids),
            total_executed=total_executed,
            passed_count=passed,
            failed_count=failed,
            skipped_count=skipped,
            error_count=errors,
            duration_seconds=wall_clock_duration,
            exit_code=exit_code,
            is_timeout=False,
            is_success=is_success,
            status_summary="Execution finished cleanly" if exit_code in (0, 1) else f"Exit code {exit_code}",
            test_outcomes=outcomes,
            raw_output=raw_stdout
        )

    finally:
        if report_json_path.exists():
            try:
                os.remove(report_json_path)
            except OSError:
                pass
