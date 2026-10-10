import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shipping import calculate_shipping_cost


def test_calculate_shipping_cost():
    assert calculate_shipping_cost(2.0, "DOMESTIC") == 9.0
    assert calculate_shipping_cost(1.0, "INTERNATIONAL") == 11.0
