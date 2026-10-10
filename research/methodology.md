# Experimental Methodology & Reproducibility Guide

## 1. Experimental Setup

The evaluation framework evaluates three test selection strategies across controlled code change scenarios:

### Selection Modes Evaluated:
1. **Mode 1: Full Suite Baseline (`full`)**:
   - Reference baseline where 100% of discovered tests are executed.
2. **Mode 2: Changed-File Baseline (`changed_file`)**:
   - Heuristic selection based on direct file modification matching and header file imports.
3. **Mode 3: Dependency-Aware Selection (`dependency_aware`)**:
   - Proposed method utilizing static AST symbol extraction and NetworkX directed graph reachability.

## 2. Benchmark Dataset
The evaluation uses the `ecommerce_demo` synthetic benchmark repository containing multi-level module dependencies:
- **`v1`**: Baseline version with 100% passing tests.
- **`v2_buggy`**: Introduces an intentional numerical regression in tax calculation (`pricing.py` -> `calculate_tax`), affecting dependent modules `cart.py` and `orders.py`, while leaving `shipping.py` unaffected.
- **`v2_clean`**: Contains a non-buggy refactoring of `calculate_tax`.

## 3. Execution Environment & Measurement Protocol
- **Python Version**: 3.10+
- **Test Runner**: `pytest` via subprocess isolation with `--json-report` output parsing.
- **Repetitions**: Each scenario is executed over multiple repetitions to average wall-clock duration.

## 4. Execution Commands

To reproduce the experimental results:

```bash
# 1. Run full unit test suite
python -m pytest tests/

# 2. Execute benchmark scenarios
python experiments/run_experiments.py
```
