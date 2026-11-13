"""Client for expenses-service GET /groups/{id}/ledger.

Agreed response shape (with expenses-service):
    {"group_id": 1, "balances": [{"member_id": 3, "net_cents": -1250}, ...]}
net_cents = paid minus owed, integer cents, summing to zero across the group.
"""

import httpx

from app.config import get_settings

# Applies to each phase (connect, read, ...), so a dead or hanging
# expenses-service fails fast instead of blocking the request.
LEDGER_TIMEOUT_SECONDS = 2.0
UNAVAILABLE_MESSAGE = "Expenses service unavailable, try again shortly"


class ExpensesUnavailableError(Exception):
    """expenses-service timed out, refused, or answered badly. The API returns 503."""


class GroupNotFoundError(Exception):
    """expenses-service has no such group. The API returns 404."""


def fetch_ledger(group_id: int, transport: httpx.BaseTransport | None = None) -> dict[int, int]:
    """Return member_id -> net cents for one group.

    `transport` is only for tests (httpx.MockTransport); production uses the network.
    """
    settings = get_settings()
    try:
        with httpx.Client(
            base_url=settings.expenses_url,
            timeout=LEDGER_TIMEOUT_SECONDS,
            headers={"X-API-Key": settings.api_key},
            transport=transport,
        ) as client:
            response = client.get(f"/groups/{group_id}/ledger")
    except httpx.HTTPError as exc:
        raise ExpensesUnavailableError(UNAVAILABLE_MESSAGE) from exc

    if response.status_code == 404:
        raise GroupNotFoundError(f"Group {group_id} not found")
    if response.status_code != 200:
        raise ExpensesUnavailableError(UNAVAILABLE_MESSAGE)

    try:
        rows = response.json()["balances"]
        return {int(row["member_id"]): int(row["net_cents"]) for row in rows}
    except (ValueError, KeyError, TypeError) as exc:
        raise ExpensesUnavailableError(UNAVAILABLE_MESSAGE) from exc
