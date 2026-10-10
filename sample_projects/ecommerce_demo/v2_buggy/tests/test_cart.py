import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cart import calculate_cart_total


def test_calculate_cart_total():
    items = [
        {"price": 10.0, "quantity": 2},
        {"price": 30.0, "quantity": 1}
    ]
    summary = calculate_cart_total(items, discount_code="SAVE10")
    assert summary["subtotal"] == 50.0
    assert summary["discount"] == 5.0
    assert summary["tax"] == 3.6
    assert summary["grand_total"] == 48.6
