from pricing import calculate_item_price, calculate_tax, calculate_discount


def calculate_cart_total(items: list, discount_code: str = "") -> dict:
    """
    Calculates subtotal, tax, discount, and grand total for cart items.
    items format: [{'price': 10.0, 'quantity': 2}, ...]
    """
    subtotal = 0.0
    for item in items:
        subtotal += calculate_item_price(item['price'], item['quantity'])

    discount = calculate_discount(subtotal, discount_code)
    discounted_subtotal = max(0.0, subtotal - discount)
    tax = calculate_tax(discounted_subtotal)
    grand_total = round(discounted_subtotal + tax, 2)

    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "tax": round(tax, 2),
        "grand_total": grand_total
    }
