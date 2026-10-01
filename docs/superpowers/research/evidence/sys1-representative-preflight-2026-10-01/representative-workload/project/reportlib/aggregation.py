"""Combine item quantities in first-appearance order."""

from collections.abc import Iterable

from .parsing import Record


def item_totals(records: Iterable[Record]) -> list[tuple[str, int]]:
    totals = {}
    for record in records:
        totals[record.item] = totals.get(record.item, 0) + record.units * record.multiplier
    return list(totals.items())
