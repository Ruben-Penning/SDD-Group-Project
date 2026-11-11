"""Rules for recording a payment. Pure functions: no database or HTTP imports."""


class InvalidPaymentError(ValueError):
    """A payment that breaks a business rule (the API turns it into a 400)."""


def validate_payment(from_member_id: int, to_member_id: int, amount_cents: int) -> None:
    if amount_cents <= 0:
        raise InvalidPaymentError("amount_cents must be greater than 0")
    if from_member_id <= 0 or to_member_id <= 0:
        raise InvalidPaymentError("member ids must be positive")
    if from_member_id == to_member_id:
        raise InvalidPaymentError("a member cannot pay themselves")
