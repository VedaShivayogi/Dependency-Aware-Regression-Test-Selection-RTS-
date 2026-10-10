import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pricing import calculate_item_price, calculate_tax, calculate_discount


def test_calculate_item_price():
    assert calculate_item_price(10.0, 2) == 20.0
    assert calculate_item_price(5.5, 3) == 16.5
    with pytest.raises(ValueError):
        calculate_item_price(-1, 2)


def test_calculate_tax():
    assert calculate_tax(100.0, 0.08) == 8.0
    assert calculate_tax(50.0, 0.10) == 5.0
    with pytest.raises(ValueError):
        calculate_tax(-10.0)


def test_calculate_discount():
    assert calculate_discount(100.0, "SAVE10") == 10.0
    assert calculate_discount(100.0, "SAVE20") == 20.0
    assert calculate_discount(100.0, "INVALID") == 0.0
