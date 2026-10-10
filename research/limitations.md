# Research Limitations & Threats to Validity

## 1. Threats to Internal Validity (Static Analysis Constraints)
1. **Dynamic Imports**: Python allows dynamic module loading at runtime via `importlib.import_module()` or `__import__()`. Static AST parsing cannot resolve variable string module paths prior to execution.
2. **Reflection & Metaprogramming**: Constructs like `getattr(obj, func_name)()`, `setattr()`, `eval()`, and `exec()` cannot be mapped statically.
3. **Decorator Wrappers**: High-order decorator wrappers that replace function signatures without preserving AST function names may obscure call target resolution.
4. **Third-Party C Extensions**: Calls into binary shared objects (`.so`, `.pyd`, C/C++ extensions) lack Python AST nodes and cannot be traversed statically.

## 2. Threats to External Validity (Dataset & Benchmark Scale)
1. **Synthetic Repository Evaluation**: Initial benchmarks were performed on synthetic e-commerce repositories (`ecommerce_demo`). While representative of multi-layer Python module architecture, synthetic suites may not exhibit the non-deterministic timing, flaky tests, or complex dependencies of million-line open-source projects.
2. **Test Framework Conventions**: The current selector focuses on standard `pytest` naming conventions (`test_*.py`, `*_test.py`). Frameworks with non-standard runner wrappers require custom adapter logic.

## 3. Execution Security & Isolation Bounds
1. **Subprocess Isolation Bounds**: Executing tests in isolated Python subprocesses with wall-clock timeouts prevents infinite loops and crashes from halting the main dashboard. However, subprocess isolation shares the host kernel, file system permissions, and environment variables.
2. **Container Security Recommendation**: For untrusted multi-tenant uploaded repositories, test execution should strictly run inside Docker containers with restricted network access and resource quotas.
