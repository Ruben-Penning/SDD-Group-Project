"""HTTP layer. Add routers here; keep business rules in app/domain."""

from fastapi import APIRouter

from app.api import balances, payments, settle_up

router = APIRouter()
router.include_router(payments.router)
router.include_router(balances.router)
router.include_router(settle_up.router)
