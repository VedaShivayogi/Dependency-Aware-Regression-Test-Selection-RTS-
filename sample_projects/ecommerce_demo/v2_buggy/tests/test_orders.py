import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orders import process_order


def test_process_order():
    items = [{"price": 20.0, "quantity": 1}]
    order = process_order("ORD-101", items, "user@example.com", discount_code="SAVE20")
    assert order["status"] == "CONFIRMED"
    assert order["order_id"] == "ORD-101"
    assert order["cart_summary"]["subtotal"] == 20.0
    assert order["cart_summary"]["discount"] == 4.0
