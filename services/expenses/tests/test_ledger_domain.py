from app.domain.ledger import ExpenseLine, compute_ledger


def test_no_expenses_means_everyone_is_at_zero():
    assert compute_ledger([2, 1], []) == {1: 0, 2: 0}


def test_payer_is_owed_the_others_shares():
    dinner = ExpenseLine(paid_by_member_id=1, amount_cents=6000, shares={1: 2000, 2: 2000, 3: 2000})
    assert compute_ledger([1, 2, 3], [dinner]) == {1: 4000, 2: -2000, 3: -2000}


def test_several_expenses_add_up_and_sum_to_zero():
    dinner = ExpenseLine(paid_by_member_id=1, amount_cents=1000, shares={1: 334, 2: 333, 3: 333})
    taxi = ExpenseLine(paid_by_member_id=2, amount_cents=500, shares={2: 250, 3: 250})
    net = compute_ledger([1, 2, 3], [dinner, taxi])
    assert net == {1: 666, 2: -83, 3: -583}
    assert sum(net.values()) == 0


def test_member_not_in_any_expense_stays_at_zero():
    taxi = ExpenseLine(paid_by_member_id=1, amount_cents=500, shares={1: 250, 2: 250})
    assert compute_ledger([1, 2, 3], [taxi])[3] == 0


def test_paying_only_for_others():
    gift = ExpenseLine(paid_by_member_id=3, amount_cents=900, shares={1: 450, 2: 450})
    assert compute_ledger([1, 2, 3], [gift]) == {1: -450, 2: -450, 3: 900}
