# Sample Demonstration Projects

This directory contains synthetic benchmark Python repositories used to evaluate and demonstrate Dependency-Aware Regression Test Selection.

## 1. `ecommerce_demo/`
An e-commerce order processing module containing multi-level function dependencies:
- **`pricing.py`**: Tax calculation, item pricing, discount logic.
- **`cart.py`**: Cart total calculation (depends on `pricing.py`).
- **`orders.py`**: Order placement (depends on `cart.py` and `pricing.py`).
- **`shipping.py`**: Shipping fee calculation (independent module!).

### Snapshot Variants:
- **`v1/`**: Baseline version where 100% of unit tests pass.
- **`v2_buggy/`**: Contains a controlled regression bug in `pricing.py` (`calculate_tax`).
  - Affected components: `pricing.py` -> `cart.py` -> `orders.py`.
  - Unaffected component: `shipping.py`.
  - Regression detection: Tests in `test_pricing.py` and `test_cart.py` fail. `test_shipping.py` passes and is skipped in dependency-aware mode!
- **`v2_clean/`**: Refactored code change where all affected tests pass cleanly.
