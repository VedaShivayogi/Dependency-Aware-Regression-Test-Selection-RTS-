# Literature Review: Regression Test Selection (RTS)

## 1. Overview
Regression Test Selection (RTS) techniques aim to reduce test execution duration by selecting a subset of an existing test suite affected by software code modifications.

This review synthesizes foundational literature and existing open-source tools for Python regression test selection.

## 2. Comparative Matrix of Existing RTS Approaches

| Tool / Paper | Authors / Year | Granularity | Analysis Technique | Primary Advantage | Key Limitation |
|---|---|---|---|---|---|
| **Rothermel & Harrold (1997)** | Rothermel & Harrold (1997) | Control-flow graph / Statements | Control Flow Graph (CFG) diffing | Precise statement-level selection | High graph construction overhead |
| **Graves et al. (2001)** | Graves et al. (2001) | Test suite empirical evaluation | Empirical benchmark comparison | Comprehensive empirical baseline | Evaluated primarily on C/C++ legacy suites |
| **pytest-testmon** | t-b (2015-2024) | Function / Bytecode line execution | Dynamic execution coverage tracing | Captures actual runtime call paths | Coverage collection adds runtime execution overhead |
| **pytest-picked** | Anibal (2019) | File level | Uncommitted Git status diffing | Zero-overhead fast file matching | Misses transitive function call dependencies |
| **This Capstone Work** | Capstone Team (2026) | Function & Module level | Static AST + NetworkX Dependency Graph | Zero-runtime coverage overhead; offline static analysis | Cannot resolve dynamic imports (`importlib`) statically |

## 3. Key Findings & Research Gap
1. **Dynamic Tracing Overhead vs. Static Graph Parsing**: Tools like `pytest-testmon` rely on `sys.settrace` or coverage collection during previous test runs. While precise, dynamic tracing introduces runtime execution overhead (10-30%) and requires pre-existing coverage databases.
2. **File-Level Heuristics**: Lightweight tools like `pytest-picked` only inspect uncommitted git files without tracing multi-level module imports, missing regressions in dependent consumer modules.
3. **Static AST Tradeoff**: Pure static AST parsing enables immediate test selection without prior test suite execution or database setup. However, dynamic features (e.g., `getattr`, `eval`, `importlib`) necessitate a conservative fallback mode to prevent missed regressions.
