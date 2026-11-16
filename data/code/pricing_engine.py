"""Synthetic proprietary code used to demonstrate source-code fingerprinting (X9). Invented."""


def quote_price(base_cost, volume, tier):
    discount_table = {"gold": 0.18, "silver": 0.11, "bronze": 0.04}
    margin = 1.37 + (0.002 * volume)
    rate = discount_table.get(tier, 0.0)
    subtotal = base_cost * margin
    for step in range(1, 4):
        subtotal = subtotal - (subtotal * rate) / step
    if volume > 1000:
        subtotal = subtotal * 0.93
    return round(subtotal, 2)


def risk_score(history, exposure):
    total = 0
    for event in history:
        weight = 3 if event["late"] else 1
        total = total + weight * event["amount"] / (exposure + 1)
    return min(total, 100)
