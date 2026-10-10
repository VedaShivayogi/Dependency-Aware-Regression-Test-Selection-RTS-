import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.metrics import EvaluationMetrics
from src.experiment_runner import ScenarioResult


def generate_markdown_experiment_report(scenario_results: List[ScenarioResult]) -> str:
    """Generates a comprehensive Markdown report summarizing experimental benchmarks."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# Experimental Evaluation Report")
    md.append("**Dependency-Aware Regression Test Selection for AI-Assisted Code Changes**\n")
    md.append(f"- **Generated At**: {now_str}")
    md.append(f"- **Python Version**: {sys.version.split()[0]}")
    md.append(f"- **Operating System**: {platform.system()} {platform.release()}")
    md.append(f"- **Scenarios Evaluated**: {len(scenario_results)}\n")
    md.append("---")

    md.append("## 1. Executive Summary Results\n")

    md.append("| Scenario ID | Mode | Selected / Total | Selection Ratio | Exec Time (s) | Time Savings (%) | Regressions Detected / Total | Detection Rate (%) | Missed Regressions |")
    md.append("|---|---|---|---|---|---|---|---|---|")

    for sr in scenario_results:
        for mode_name, m in sr.metrics.items():
            md.append(
                f"| `{sr.scenario_id}` | `{mode_name}` | {m.tests_selected} / {m.total_tests_available} | "
                f"{m.selection_ratio * 100:.1f}% | {m.execution_time_seconds:.3f}s | "
                f"**{m.time_reduction_percent:.1f}%** | {m.regressions_detected} / {m.total_known_regressions} | "
                f"**{m.failure_detection_rate:.1f}%** | {m.missed_regressions_count} |"
            )

    md.append("\n---")
    md.append("## 2. Key Findings & Discussion\n")
    
    # Calculate overall averages for dependency aware vs full
    dep_savings = []
    dep_detections = []
    dep_missed = 0

    for sr in scenario_results:
        if "dependency_aware" in sr.metrics:
            m = sr.metrics["dependency_aware"]
            dep_savings.append(m.time_reduction_percent)
            dep_detections.append(m.failure_detection_rate)
            dep_missed += m.missed_regressions_count

    avg_savings = (sum(dep_savings) / len(dep_savings)) if dep_savings else 0.0
    avg_detection = (sum(dep_detections) / len(dep_detections)) if dep_detections else 100.0

    md.append(f"- **Average Time Reduction**: {avg_savings:.2f}% test time saved using dependency-aware selection compared to running the full suite.")
    md.append(f"- **Average Failure Detection Rate**: {avg_detection:.2f}% of known regression failures captured.")
    md.append(f"- **Total Missed Regressions**: {dep_missed} regressions missed across all scenarios.")

    if avg_savings > 0 and dep_missed == 0:
        md.append("- **Conclusion**: Dependency-aware selection successfully accelerated test feedback without sacrificing regression safety in evaluated synthetic benchmarks.")
    elif dep_missed > 0:
        md.append("- **Conclusion**: Dependency-aware selection reduced execution time but missed regressions due to dynamic dependencies or uncaptured call paths. Conservative mode is recommended.")

    md.append("\n---")
    md.append("## 3. Methodology & Evaluation Parameters\n")
    md.append("1. **Mode 1 (Full Suite)**: Reference baseline running 100% of discovered tests.")
    md.append("2. **Mode 2 (Changed-File Baseline)**: Selects tests strictly matching changed file names or direct file import headers.")
    md.append("3. **Mode 3 (Dependency-Aware)**: Traces AST function call graphs and module import relations to select affected tests.")

    md.append("\n---")
    md.append("*Report generated automatically by Dependency-Aware Regression Test Selection System.*")

    return "\n".join(md)
