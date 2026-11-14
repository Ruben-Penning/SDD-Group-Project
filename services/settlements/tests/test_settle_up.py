"""settle_up() is pure, so these tests need no database or network."""

import pytest

from app.domain.settle_up import settle_up


def _apply(balances, transfers):
    """Balances after paying every transfer. Settled means all zero."""
    result = dict(balances)
    for from_id, to_id, cents in transfers:
        result[from_id] += cents
        result[to_id] -= cents
    return result


def test_empty_group_needs_no_transfers():
    assert settle_up({}) == []


def test_everyone_even_needs_no_transfers():
    assert settle_up({1: 0, 2: 0, 3: 0}) == []


def test_two_people_one_transfer():
    assert settle_up({1: 2000, 2: -2000}) == [(2, 1, 2000)]


def test_three_people_in_a_cycle_settle_in_at_most_two():
    # Ana paid 30 for Ben, Ben paid 30 for Cleo, Cleo paid 60 for Ana:
    # net Ana -30, Ben 0, Cleo +30.
    balances = {1: -3000, 2: 0, 3: 3000}
    transfers = settle_up(balances)
    assert transfers == [(1, 3, 3000)]
    assert all(b == 0 for b in _apply(balances, transfers).values())


def test_uneven_cents_settle_exactly():
    # 10.00 paid by member 1, split three ways: 334 / 333 / 333.
    balances = {1: 666, 2: -333, 3: -333}
    transfers = settle_up(balances)
    assert sorted(transfers) == [(2, 1, 333), (3, 1, 333)]
    assert all(b == 0 for b in _apply(balances, transfers).values())


def test_balances_not_summing_to_zero_raise():
    with pytest.raises(ValueError, match="sum to zero"):
        settle_up({1: 500, 2: -400})


@pytest.mark.parametrize(
    "balances",
    [
        {1: 5000, 2: -1000, 3: -1500, 4: -2500},
        {1: 1234, 2: 4321, 3: -2000, 4: -3555},
        {1: -1, 2: -1, 3: -1, 4: 3},
        {i: (i - 5) * 100 for i in range(1, 10)},
    ],
    ids=["one-creditor", "two-by-two", "single-cents", "nine-people"],
)
def test_any_group_settles_in_at_most_n_minus_1_positive_transfers(balances):
    transfers = settle_up(balances)
    nonzero = sum(1 for b in balances.values() if b != 0)
    assert len(transfers) <= nonzero - 1
    assert all(cents > 0 for _, _, cents in transfers)
    assert all(b == 0 for b in _apply(balances, transfers).values())


def test_does_not_change_the_input():
    balances = {1: 700, 2: -700}
    settle_up(balances)
    assert balances == {1: 700, 2: -700}
