from cart import calculate_cart_total


def process_order(order_id: str, items: list, user_email: str, discount_code: str = "") -> dict:
    if not order_id or not user_email:
        raise ValueError("Order ID and user email are required.")

    cart_summary = calculate_cart_total(items, discount_code)
    
    return {
        "order_id": order_id,
        "user_email": user_email,
        "status": "CONFIRMED",
        "cart_summary": cart_summary
    }
