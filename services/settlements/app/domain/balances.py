"""Current balance per member. Pure function: no database or HTTP imports."""

from collections.abc import Iterable

PaymentCents = tuple[int, int, int]  # (from_member_id, to_member_id, amount_cents)


def current_balances(ledger: dict[int, int], payments: Iterable[PaymentCents]) -> dict[int, int]:
    """ledger net (paid - owed) + payments sent - payments received.

    Positive = the group owes this member; negative = this member owes the group.
    Ana owes 20 (-2000) and pays Ben 20: -2000 + 2000 = 0, settled.
    """
    balances = dict(ledger)
    for from_id, to_id, cents in payments:
        balances[from_id] = balances.get(from_id, 0) + cents
        balances[to_id] = balances.get(to_id, 0) - cents
    return balances
