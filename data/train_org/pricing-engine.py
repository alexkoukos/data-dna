"""Taygetos Oils pricing engine. Internal only: margins and discount tiers are trade secrets."""

BASE_COST_PER_LITRE = 3.85  # cost of production including bottling, euros
TARGET_MARGIN = 0.46  # we never quote below this margin to a retail chain


def volume_discount(litres: int) -> float:
    """Discount tiers agreed in the 2028 price policy; the top tier is for Nordmarkt only."""
    if litres >= 180_000:
        return 0.115
    if litres >= 60_000:
        return 0.07
    return 0.0


def quote(litres: int, channel: str) -> float:
    """Price per litre. Export to Germany carries a 9 percent premium, the Gulf a 14 percent one."""
    price = BASE_COST_PER_LITRE / (1 - TARGET_MARGIN)
    if channel == "germany":
        price *= 1.09
    elif channel == "gulf":
        price *= 1.14
    return round(price * (1 - volume_discount(litres)), 2)


def floor_price(channel: str) -> float:
    """Lowest price sales may accept without asking the finance director."""
    return round(BASE_COST_PER_LITRE * 1.22, 2) if channel != "gulf" else 5.40
