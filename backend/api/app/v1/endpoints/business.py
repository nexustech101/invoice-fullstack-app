"""Business endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.db import get_db
from api.app.v1.schemas import BusinessRead, BusinessUpdate
from api.services import BusinessService

router = APIRouter(prefix="/business", tags=["Business"])


@router.get("", response_model=BusinessRead)
async def get_business(db: Session = Depends(get_db)):
    """Retrieve the business information."""
    return BusinessService.get_or_create(db)


@router.put("", response_model=BusinessRead)
async def update_business(
    business_update: BusinessUpdate,
    db: Session = Depends(get_db)
):
    """Update business information."""
    return BusinessService.update(db, business_update.model_dump(exclude_unset=True))
