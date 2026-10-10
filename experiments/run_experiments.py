import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.experiment_runner import ExperimentRunner
from src.report_generator import generate_markdown_experiment_report
from config.settings import RESULTS_DIR, SAMPLE_PROJECTS_DIR


def main():
    print("======================================================================")
    print("STARTING REPRODUCIBLE REGRESSION TEST SELECTION EXPERIMENTS")
    print("======================================================================")

    runner = ExperimentRunner(output_dir=RESULTS_DIR)
    results = []

    # Scenario 1: E-commerce Buggy Change (v1 vs v2_buggy)
    sc1_base = SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v1"
    sc1_changed = SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v2_buggy"

    if sc1_base.exists() and sc1_changed.exists():
        print("\n--> Running Scenario 1: E-Commerce Tax Buggy Change...")
        res1 = runner.run_scenario(
            scenario_id="ECOM-BUGGY-01",
            scenario_name="E-Commerce Tax Calculation Regression Bug",
            base_repo_path=sc1_base,
            changed_repo_path=sc1_changed,
            repetitions=2
        )
        results.append(res1)
        print("    [+] Scenario 1 Complete.")

    # Scenario 2: E-commerce Clean Change (v1 vs v2_clean)
    sc2_base = SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v1"
    sc2_changed = SAMPLE_PROJECTS_DIR / "ecommerce_demo" / "v2_clean"

    if sc2_base.exists() and sc2_changed.exists():
        print("\n--> Running Scenario 2: E-Commerce Tax Refactoring Clean Change...")
        res2 = runner.run_scenario(
            scenario_id="ECOM-CLEAN-02",
            scenario_name="E-Commerce Tax Refactoring Clean Change",
            base_repo_path=sc2_base,
            changed_repo_path=sc2_changed,
            repetitions=2
        )
        results.append(res2)
        print("    [+] Scenario 2 Complete.")

    # Export results
    print("\n--> Exporting experimental outputs to results/ directory...")
    csv_path, json_path = runner.export_results(results, filename_prefix="experiment_results")

    # Generate Markdown Summary
    report_md = generate_markdown_experiment_report(results)
    summary_md_path = RESULTS_DIR / "experiment_summary.md"
    summary_md_path.write_text(report_md, encoding="utf-8")

    print(f"\n[SUCCESS] Experiments Finished!")
    print(f" - CSV Results:  {csv_path}")
    print(f" - JSON Results: {json_path}")
    print(f" - Markdown Summary: {summary_md_path}")
    print("======================================================================")


if __name__ == "__main__":
    main()
