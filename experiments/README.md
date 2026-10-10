# Experiment Suite Execution Guide

This folder contains scripts for running automated, reproducible regression test selection experiments across sample projects.

## How to Run Experiments

From the project root directory, run:

```bash
python experiments/run_experiments.py
```

This will execute:
1. Scenario 1 (`ecommerce_buggy`): Controlled tax calculation regression.
2. Scenario 2 (`ecommerce_clean`): Controlled refactoring without bugs.

Outputs are generated in `results/`:
- `results/experiment_results.csv`: Tabular evaluation metrics per mode.
- `results/experiment_results.json`: Full JSON experimental trace.
- `results/experiment_summary.md`: Formatted Markdown research report.
