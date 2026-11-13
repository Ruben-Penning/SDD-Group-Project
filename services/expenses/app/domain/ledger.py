"""The group ledger: what each member paid minus what they owe. Pure, no database or HTTP."""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenseLine:
    """The parts of one expense the ledger needs."""

    paid_by_member_id: int
    amount_cents: int
    shares: dict[int, int]  # member_id -> share_cents


def compute_ledger(member_ids: Iterable[int], expenses: Iterable[ExpenseLine]) -> dict[int, int]:
    """Return {member_id: net_cents} for every member, ordered by member id.

    net_cents = total paid - total owed. Positive means the group owes the member,
    negative means the member owes the group. Because each expense's shares add up
    to its amount, the nets of a group always sum to zero.
    """
    net = {member_id: 0 for member_id in sorted(member_ids)}
    for expense in expenses:
        net[expense.paid_by_member_id] += expense.amount_cents
        for member_id, share_cents in expense.shares.items():
            net[member_id] -= share_cents
    return net
