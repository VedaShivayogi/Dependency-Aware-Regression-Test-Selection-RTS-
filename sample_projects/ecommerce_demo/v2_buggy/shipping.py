def calculate_shipping_cost(weight_kg: float, zone: str) -> float:
    if weight_kg <= 0:
        raise ValueError("Weight must be positive.")

    base_rate = 5.0
    zone_multipliers = {
        "DOMESTIC": 1.0,
        "REGIONAL": 1.5,
        "INTERNATIONAL": 3.0
    }
    
    multiplier = zone_multipliers.get(zone.upper(), 1.0)
    cost = base_rate + (weight_kg * 2.0 * multiplier)
    return round(cost, 2)
