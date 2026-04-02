"""Payment endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.db import get_db
from api.app.v1.schemas import PaymentCreate, PaymentRead
from api.services import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db)
):
    """Record a new payment for an invoice."""
    return PaymentService.create(db, payment)


@router.get("", response_model=List[PaymentRead])
async def list_payments(
    skip: int = 0,
    limit: int = 50,
    invoice_id: int | None = None,
    db: Session = Depends(get_db)
):
    """List all payments with optional invoice filter."""
    return PaymentService.list(db, skip=skip, limit=limit, invoice_id=invoice_id)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific payment by ID."""
    return PaymentService.get(db, payment_id)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    """Delete a payment record."""
    PaymentService.delete(db, payment_id)


@router.get("/invoice/{invoice_id}", response_model=List[PaymentRead])
async def get_invoice_payments(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Get all payments for a specific invoice."""
    return PaymentService.list(db, invoice_id=invoice_id)
