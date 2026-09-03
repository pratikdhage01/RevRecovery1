"""
Dashboard aggregate stats API.
"""
from fastapi import APIRouter
from app.services import recovery_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    """Aggregate dashboard metrics."""
    return await recovery_service.get_dashboard_stats()
