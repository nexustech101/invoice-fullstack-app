"""Stripe Checkout integration for public invoice payments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.config import settings
from api.models import Invoice
from api.services.payment_service import PaymentService

try:
    import stripe
except ImportError:  # pragma: no cover - handled at runtime when Stripe isn't installed yet.
    stripe = None


@dataclass
class _PaymentPayload:
    invoice_id: int
    date: date
    amount: Decimal
    method: str
    transaction_id: str
    notes: str | None = None


class StripeService:
    """Create Stripe Checkout sessions and reconcile webhook events."""

    @staticmethod
    def _require_secret_key() -> None:
        if stripe is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe SDK is not installed on the server",
            )
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured on the server",
            )
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def _minor_amount(amount: Decimal) -> int:
        normalized = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(normalized)

    @staticmethod
    def create_checkout_session(invoice: Invoice) -> str:
        StripeService._require_secret_key()

        amount_due = Decimal(invoice.amount_due or Decimal("0.00"))
        if amount_due <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invoice does not have an outstanding balance",
            )

        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=f"{invoice.public_url}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{invoice.public_url}?checkout=cancelled",
            customer_email=invoice.client.email,
            billing_address_collection="auto",
            line_items=[
                {
                    "price_data": {
                        "currency": settings.PAYMENT_CURRENCY.lower(),
                        "product_data": {
                            "name": f"Invoice {invoice.invoice_number}",
                            "description": f"Payment for invoice {invoice.invoice_number}",
                        },
                        "unit_amount": StripeService._minor_amount(amount_due),
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "client_email": invoice.client.email,
            },
        )
        checkout_url = getattr(session, "url", None)
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe did not return a checkout URL",
            )
        return checkout_url

    @staticmethod
    def handle_webhook(db: Session, payload: bytes, signature: str | None) -> dict:
        StripeService._require_secret_key()
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe webhook secret is not configured on the server",
            )
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature header",
            )

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe payload") from exc
        except stripe.error.SignatureVerificationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature") from exc

        event_type = event["type"]
        if event_type not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            return {"status": "ignored", "event_type": event_type}

        session_data = event["data"]["object"]
        if session_data.get("payment_status") != "paid":
            return {"status": "ignored", "event_type": event_type}

        invoice_id = int(session_data["metadata"]["invoice_id"])
        transaction_id = session_data.get("payment_intent") or session_data.get("id")
        amount_total = Decimal(session_data.get("amount_total", 0)) / Decimal("100")

        payment = PaymentService.create(
            db,
            _PaymentPayload(
                invoice_id=invoice_id,
                date=date.today(),
                amount=amount_total,
                method="stripe",
                transaction_id=transaction_id,
                notes=f"Stripe Checkout session {session_data.get('id')}",
            ),
        )
        return {
            "status": "processed",
            "event_type": event_type,
            "payment_id": payment.id,
            "invoice_id": payment.invoice_id,
        }
