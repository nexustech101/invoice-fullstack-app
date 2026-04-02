"""Main API router - registers all v1 endpoints."""

from fastapi import APIRouter, Depends

# Import all endpoint routers
from api.app.v1.endpoints import (
    auth,
    health,
    business,
    invoices,
    clients,
    payments,
    dashboard,
    stripe,
)
from api.services import AuthService

router = APIRouter(prefix="/api/v1")

# Register all routers
router.include_router(health.router)
router.include_router(stripe.router)
router.include_router(auth.router)
router.include_router(invoices.public_router)
router.include_router(business.router, dependencies=[Depends(AuthService.get_current_admin)])
router.include_router(invoices.router, dependencies=[Depends(AuthService.get_current_admin)])
router.include_router(clients.router, dependencies=[Depends(AuthService.get_current_admin)])
router.include_router(payments.router, dependencies=[Depends(AuthService.get_current_admin)])
router.include_router(dashboard.router, dependencies=[Depends(AuthService.get_current_admin)])
