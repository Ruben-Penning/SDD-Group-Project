"""Rules for adding an expense. Pure functions: no database or HTTP imports."""

MAX_DESCRIPTION_LENGTH = 200


class InvalidExpenseError(ValueError):
    """An expense that breaks a business rule (the API turns it into a 400)."""


def clean_description(description: str) -> str:
    description = description.strip()
    if not description:
        raise InvalidExpenseError("description must not be empty")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise InvalidExpenseError(
            f"description must be at most {MAX_DESCRIPTION_LENGTH} characters"
        )
    return description


def check_members_in_group(
    paid_by_member_id: int, member_ids: list[int], group_member_ids: set[int]
) -> None:
    """The payer and everyone sharing the cost must be members of the group."""
    if paid_by_member_id not in group_member_ids:
        raise InvalidExpenseError("paid_by_member_id is not a member of this group")
    unknown = sorted(set(member_ids) - group_member_ids)
    if unknown:
        raise InvalidExpenseError(f"member_ids not in this group: {unknown}")


def split_equally(amount_cents: int, member_ids: list[int]) -> dict[int, int]:
    """Split an amount in cents equally between members: {member_id: share_cents}.

    When it does not divide exactly, the leftover cents go one each to the
    members with the lowest ids, so the shares always add up to the amount.
    Example: 1000 between 3 members -> 334, 333, 333.
    """
    if amount_cents <= 0:
        raise InvalidExpenseError("amount_cents must be greater than 0")
    if not member_ids:
        raise InvalidExpenseError("member_ids must contain at least one member")
    if len(set(member_ids)) != len(member_ids):
        raise InvalidExpenseError("member_ids must not contain duplicates")

    base, leftover = divmod(amount_cents, len(member_ids))
    return {
        member_id: base + (1 if position < leftover else 0)
        for position, member_id in enumerate(sorted(member_ids))
    }
