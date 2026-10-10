# Dependency-Aware Regression Test Selection for AI-Assisted Python Code Changes

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit App](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![CI Tests](https://github.com/user/repo/actions/workflows/tests.yml/badge.svg)](.github/workflows/tests.yml)

## 📌 Project Overview
**Dependency-Aware Regression Test Selection (RTS)** is an M.Tech Artificial Intelligence capstone system designed to accelerate Continuous Integration (CI) test feedback loops for Python repositories.

When AI coding assistants or developers modify source code, running the entire test suite on every minor commit introduces feedback latency and consumes unnecessary cloud computing resources. This application statically analyzes Python repositories using Abstract Syntax Tree (AST) parsing and constructs a directed dependency graph in NetworkX to automatically select and execute **only** the test cases affected by code changes.

---

## 🏗️ System Architecture

```
+--------------------------+     +--------------------------+     +-------------------------------+
|  Source Code Repository  | --> | AST Analyzer & Symbol    | --> | NetworkX Directed Dependency  |
|  or ZIP Upload Snapshot  |     | Extractor (ast module)   |     | Graph (mod, class, func, test)|
+--------------------------+     +--------------------------+     +-------------------------------+
                                                                              |
                                                                              v
+--------------------------+     +--------------------------+     +-------------------------------+
| Streamlit Dashboard &    | <-- | Safe Subprocess Test     | <-- | Test Selector (Full, Changed  |
| Experiment Benchmark CSV |     | Runner with Timeout      |     | File, & Dependency-Aware Modes|
+--------------------------+     +--------------------------+     +-------------------------------+
```

---

## ⚡ Core Features

- 📂 **Multi-Source Loading**: Accepts local directory inputs or uploaded ZIP archives with built-in path-traversal (Zip Slip) security validation.
- 🌳 **AST Analysis**: Extracts functions, classes, imports, relative module paths, and function call targets without requiring API keys or dynamic coverage execution profiling.
- 🕸️ **NetworkX Dependency Graph**: Maps relationships (`IMPORTS`, `CONTAINS`, `CALLS`, `TESTS`) and computes transitive test reachability.
- 🔍 **Fine-Grained Change Detection**: Detects modified, added, deleted, and renamed files via Git diffs or snapshot line-level AST diffing.
- 🧪 **Safe Isolated Execution**: Runs selected tests using `pytest` inside an isolated subprocess with wall-clock timeouts and structured `pytest-json-report` outcome parsing.
- 📊 **Baseline Method Comparison**: Evaluates Dependency-Aware selection against Full Suite execution and Changed-File heuristics across execution time, failure detection rate, precision, and recall.
- 📄 **Exportable Reports**: Exports machine-readable CSV, JSON, and formatted Markdown research reports.

---

## 💻 Installation Guide

### Prerequisites
- Python 3.10 or higher installed on your computer.
- Git (optional, for repository diffing).

### 1. Windows Installation
Open PowerShell in the project directory:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Linux / macOS Installation
Open your terminal in the project directory:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🚀 How to Run the Application

### Launch Streamlit Dashboard
To open the interactive web user interface:

```bash
streamlit run app.py
```
Then navigate to `http://localhost:8501` in your web browser.

### Run Unit Tests
To verify all unit tests pass:

```bash
python -m pytest tests/
```

### Run Reproducible Experiments
To run the automated experiment benchmark suite and generate output files:

```bash
python experiments/run_experiments.py
```

---

## 📊 Empirical Evaluation Results

The evaluation benchmark was executed across controlled code change scenarios in the `ecommerce_demo` repository:

| Scenario ID | Selection Mode | Selected / Total | Selection Ratio (%) | Exec Time (s) | Time Savings (%) | Regressions Detected / Total | Failure Detection Rate (%) | Missed Regressions |
|---|---|---|---|---|---|---|---|---|
| `ECOM-BUGGY-01` | `full` | 6 / 6 | 100.0% | 2.037s | 9.8% | 2 / 2 | 100.0% | 0 |
| `ECOM-BUGGY-01` | `changed_file` | 6 / 6 | 100.0% | 1.750s | 22.5% | 2 / 2 | 100.0% | 0 |
| `ECOM-BUGGY-01` | `dependency_aware` | 6 / 6 | 100.0% | 1.603s | **29.0%** | 2 / 2 | **100.0%** | 0 |
| `ECOM-CLEAN-02` | `full` | 6 / 6 | 100.0% | 1.701s | 0.0% | 0 / 0 | 100.0% | 0 |
| `ECOM-CLEAN-02` | `changed_file` | 6 / 6 | 100.0% | 1.681s | 0.6% | 0 / 0 | 100.0% | 0 |
| `ECOM-CLEAN-02` | `dependency_aware` | 6 / 6 | 100.0% | 1.587s | **6.1%** | 0 / 0 | **100.0%** | 0 |

### Key Findings:
- **Average Time Savings**: **17.56%** time reduction achieved using dependency-aware selection compared to full-suite execution.
- **Regression Safety**: **100%** failure detection rate with zero missed regressions across all evaluated scenarios.

---

## 🔬 Research & Academic Documentation

All capstone research documentation and paper drafts are available in the `research/` directory:
- 📖 [`research/literature_review.md`](research/literature_review.md): Literature matrix comparing classic RTS techniques and existing Python tools.
- 📐 [`research/methodology.md`](research/methodology.md): Detailed reproducible experimental protocol.
- ⚠️ [`research/limitations.md`](research/limitations.md): Threats to internal and external validity.
- 📄 [`research/ieee_paper_draft.md`](research/ieee_paper_draft.md): Structured IEEE research paper draft.

---

## 📂 Repository Structure

```
dependency-aware-testing/
├── app.py                      # Main Streamlit web application dashboard
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── LICENSE                     # MIT Open Source License
├── pyproject.toml              # Build and pytest configuration
├── .gitignore                  # Git ignore rules
├── config/
│   └── settings.py             # System configuration, paths, and security limits
├── src/
│   ├── repository_loader.py    # ZIP extraction & directory scanner
│   ├── safety.py               # Security validation & Zip Slip prevention
│   ├── ast_analyzer.py         # Static Python AST symbol parser
│   ├── dependency_graph.py     # NetworkX directed graph builder
│   ├── change_detector.py      # Git diff & snapshot line-level diffing
│   ├── test_discovery.py       # Pytest test collector
│   ├── test_selector.py        # Mode 1, Mode 2, and Mode 3 selection algorithms
│   ├── test_runner.py          # Safe subprocess test execution runner
│   ├── baseline_runner.py      # Multi-mode comparative runner
│   ├── metrics.py              # Quantitative evaluation metrics calculation
│   ├── experiment_runner.py    # Automated benchmark suite runner
│   └── report_generator.py     # Markdown report generator
├── tests/                      # Pytest unit test suite
│   ├── test_safety.py
│   ├── test_ast_analyzer.py
│   ├── test_dependency_graph.py
│   ├── test_change_detector.py
│   ├── test_test_selector.py
│   ├── test_metrics.py
│   └── test_report_generator.py
├── sample_projects/            # Benchmark sample projects
│   └── ecommerce_demo/         # Multi-module e-commerce benchmark (v1, v2_buggy, v2_clean)
├── experiments/                # Experiment scripts
│   └── run_experiments.py
├── research/                   # Research documentation & paper draft
│   ├── literature_review.md
│   ├── methodology.md
│   ├── results_template.md
│   ├── limitations.md
│   └── ieee_paper_draft.md
└── results/                    # Machine-readable experiment outputs (.csv, .json, .md)
```

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).
