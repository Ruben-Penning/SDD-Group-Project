from app.domain.balances import current_balances


def test_no_payments_returns_ledger_unchanged():
    assert current_balances({1: 1500, 2: -1500}, []) == {1: 1500, 2: -1500}


def test_payment_sent_raises_payer_and_lowers_receiver():
    # Ana (1) owes 20, Ben (2) is owed 20. Ana pays Ben 20: both settled.
    assert current_balances({1: -2000, 2: 2000}, [(1, 2, 2000)]) == {1: 0, 2: 0}


def test_partial_payment_leaves_the_rest():
    assert current_balances({1: -2000, 2: 2000}, [(1, 2, 500)]) == {1: -1500, 2: 1500}


def test_several_payments_add_up():
    ledger = {1: -3000, 2: -1000, 3: 4000}
    payments = [(1, 3, 1000), (2, 3, 1000), (1, 3, 500)]
    assert current_balances(ledger, payments) == {1: -1500, 2: 0, 3: 1500}


def test_balances_still_sum_to_zero_after_payments():
    ledger = {1: 666, 2: -333, 3: -333}
    result = current_balances(ledger, [(2, 1, 333), (3, 2, 100)])
    assert sum(result.values()) == 0


def test_payment_for_member_not_in_ledger_is_still_counted():
    assert current_balances({}, [(1, 2, 700)]) == {1: 700, 2: -700}


def test_does_not_change_the_input():
    ledger = {1: -2000, 2: 2000}
    current_balances(ledger, [(1, 2, 2000)])
    assert ledger == {1: -2000, 2: 2000}
