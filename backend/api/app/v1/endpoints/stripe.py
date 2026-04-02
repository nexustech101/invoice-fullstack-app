"""Public Stripe webhook endpoints."""

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from api.db import get_db
from api.services import StripeService


router = APIRouter(prefix="/stripe", tags=["Stripe"])


@router.post("/webhooks")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Receive Stripe webhook events for invoice payment reconciliation."""
    payload = await request.body()
    return StripeService.handle_webhook(db, payload, stripe_signature)
