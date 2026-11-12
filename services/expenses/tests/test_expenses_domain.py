import pytest

from app.domain.expenses import (
    InvalidExpenseError,
    check_members_in_group,
    clean_description,
    split_equally,
)


def test_even_split():
    assert split_equally(6000, [1, 2]) == {1: 3000, 2: 3000}


def test_leftover_cents_go_to_lowest_ids_and_shares_add_up():
    shares = split_equally(1000, [3, 1, 2])
    assert shares == {1: 334, 2: 333, 3: 333}
    assert sum(shares.values()) == 1000


def test_one_member_pays_it_all():
    assert split_equally(999, [7]) == {7: 999}


def test_amount_smaller_than_member_count():
    assert split_equally(2, [1, 2, 3]) == {1: 1, 2: 1, 3: 0}


@pytest.mark.parametrize("amount", [0, -100])
def test_amount_must_be_positive(amount):
    with pytest.raises(InvalidExpenseError, match="greater than 0"):
        split_equally(amount, [1, 2])


def test_needs_at_least_one_member():
    with pytest.raises(InvalidExpenseError, match="at least one member"):
        split_equally(1000, [])


def test_duplicate_member_ids_are_rejected():
    with pytest.raises(InvalidExpenseError, match="duplicates"):
        split_equally(1000, [1, 1, 2])


def test_description_is_trimmed():
    assert clean_description("  Dinner  ") == "Dinner"


def test_empty_description_is_rejected():
    with pytest.raises(InvalidExpenseError, match="must not be empty"):
        clean_description("  ")


def test_too_long_description_is_rejected():
    with pytest.raises(InvalidExpenseError, match="at most 200"):
        clean_description("x" * 201)


def test_members_in_group_pass():
    check_members_in_group(1, [1, 2], {1, 2, 3})


def test_payer_must_be_in_group():
    with pytest.raises(InvalidExpenseError, match="paid_by_member_id"):
        check_members_in_group(9, [1], {1, 2})


def test_shared_members_must_be_in_group():
    with pytest.raises(InvalidExpenseError, match=r"not in this group: \[8, 9\]"):
        check_members_in_group(1, [1, 9, 8], {1, 2})
