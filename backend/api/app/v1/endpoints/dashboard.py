"""Dashboard and statistics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.db import get_db
from api.app.v1.schemas import DashboardResponse
from api.services import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db)
):
    """Get dashboard summary statistics (revenue, invoice counts, etc.)."""
    return DashboardService.full_dashboard(db)


@router.get("/revenue/monthly")
async def get_monthly_revenue(
    year: int | None = None,
    db: Session = Depends(get_db)
):
    """Get monthly revenue breakdown."""
    return DashboardService.monthly_revenue(db, year=year)


@router.get("/invoices/status-summary")
async def get_invoice_status_summary(
    db: Session = Depends(get_db)
):
    """Get summary of invoices by status (draft, sent, paid, overdue)."""
    return DashboardService.status_summary(db)


@router.get("/clients/top")
async def get_top_clients(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get top clients by revenue."""
    return DashboardService.top_clients(db, limit=limit)


@router.get("/payments/recent")
async def get_recent_payments(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get recent payment records."""
    return DashboardService.recent_payments(db, limit=limit)
