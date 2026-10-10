def calculate_item_price(price: float, quantity: int) -> float:
    """Calculates subtotal for item price and quantity."""
    if price < 0 or quantity < 0:
        raise ValueError("Price and quantity must be non-negative.")
    return round(price * quantity, 2)


def calculate_tax(subtotal: float, rate: float = 0.08) -> float:
    """Calculates tax based on rate."""
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative.")
    return round(subtotal * rate, 2)


def calculate_discount(total: float, code: str) -> float:
    """Calculates discount amount for coupon code."""
    if total < 0:
        return 0.0
    if code == "SAVE10":
        return round(total * 0.10, 2)
    elif code == "SAVE20":
        return round(total * 0.20, 2)
    return 0.0
