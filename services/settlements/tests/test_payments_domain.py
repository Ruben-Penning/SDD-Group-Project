import pytest

from app.domain.payments import InvalidPaymentError, validate_payment


def test_valid_payment_passes():
    validate_payment(1, 2, 2000)


@pytest.mark.parametrize(
    "from_id,to_id,amount,message",
    [
        (1, 2, 0, "greater than 0"),
        (1, 2, -500, "greater than 0"),
        (0, 2, 100, "positive"),
        (1, -3, 100, "positive"),
        (3, 3, 100, "pay themselves"),
    ],
    ids=["zero-amount", "negative-amount", "zero-from-id", "negative-to-id", "pay-yourself"],
)
def test_invalid_payment_rejected(from_id, to_id, amount, message):
    with pytest.raises(InvalidPaymentError, match=message):
        validate_payment(from_id, to_id, amount)