"""HTTP layer. Add routers here; keep business rules in app/domain."""

from fastapi import APIRouter

from app.api import expenses, groups, ledger

router = APIRouter()
router.include_router(groups.router)
router.include_router(expenses.router)
router.include_router(ledger.router)
