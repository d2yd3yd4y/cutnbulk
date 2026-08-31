def avg_values(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def avg_total(total: float, count: int) -> float:
    if count <= 0:
        return 0
    return round(total / count, 1)
