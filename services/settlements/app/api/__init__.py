"""HTTP layer. Add routers here; keep business rules in app/domain."""

from fastapi import APIRouter

from app.api import balances, payments

router = APIRouter()
router.include_router(payments.router)
router.include_router(balances.router)
