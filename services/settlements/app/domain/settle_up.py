"""Minimum transfers to clear a group's debts. Pure function: no database or HTTP imports."""

Transfer = tuple[int, int, int]  # (from_member_id, to_member_id, amount_cents)


def settle_up(balances: dict[int, int]) -> list[Transfer]:
    """Greedy match of the biggest debtor to the biggest creditor.

    balances: member_id -> cents (positive = is owed, negative = owes). Must sum to zero.
    Settles n members with non-zero balances in at most n - 1 transfers.
    """
    if sum(balances.values()) != 0:
        raise ValueError("balances must sum to zero")
    creditors = sorted(((b, m) for m, b in balances.items() if b > 0), reverse=True)
    debtors = sorted(((-b, m) for m, b in balances.items() if b < 0), reverse=True)
    transfers: list[Transfer] = []
    while creditors and debtors:
        c_amt, c = creditors.pop(0)
        d_amt, d = debtors.pop(0)
        amt = min(c_amt, d_amt)
        transfers.append((d, c, amt))
        if c_amt > amt:
            creditors.append((c_amt - amt, c))
            creditors.sort(reverse=True)
        if d_amt > amt:
            debtors.append((d_amt - amt, d))
            debtors.sort(reverse=True)
    return transfers
