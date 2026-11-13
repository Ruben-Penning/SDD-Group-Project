"""HTTP layer. Add routers here; keep business rules in app/domain."""

from fastapi import APIRouter

from app.api import groups

router = APIRouter()
router.include_router(groups.router)
