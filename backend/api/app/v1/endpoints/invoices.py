"""Invoice endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from api.db import get_db
from api.app.v1.schemas import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceRead,
    InvoiceSendResponse,
    StripeCheckoutSessionResponse,
)
from api.services import InvoiceService, StripeService

router = APIRouter(prefix="/invoices", tags=["Invoices"])
public_router = APIRouter(prefix="/public/invoices", tags=["Public Invoices"])


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db)
):
    """Create a new invoice."""
    return InvoiceService.create(db, invoice)


@router.get("", response_model=List[InvoiceRead])
async def list_invoices(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all invoices with pagination."""
    return InvoiceService.list(db, skip=skip, limit=limit)


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific invoice by ID."""
    return InvoiceService.get(db, invoice_id)


@router.put("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: Session = Depends(get_db)
):
    """Update an invoice."""
    return InvoiceService.update(db, invoice_id, invoice_update)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Delete an invoice."""
    InvoiceService.delete(db, invoice_id)


@router.post("/{invoice_id}/send", response_model=InvoiceSendResponse)
async def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Send invoice to client (via email)."""
    return InvoiceService.send(db, invoice_id)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Generate and return invoice as PDF."""
    invoice, pdf_bytes = InvoiceService.pdf_bytes(db, invoice_id)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{invoice.invoice_number}.pdf"'},
    )


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceRead)
async def mark_invoice_paid(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Mark invoice as paid."""
    return InvoiceService.mark_paid(db, invoice_id)


@router.post("/{invoice_id}/mark-overdue", response_model=InvoiceRead)
async def mark_invoice_overdue(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Mark invoice as overdue."""
    return InvoiceService.mark_overdue(db, invoice_id)


@public_router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_public_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve the public invoice view for client-facing payment pages."""
    return InvoiceService.get(db, invoice_id)


@public_router.get("/{invoice_id}/pdf")
async def get_public_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Return the public PDF invoice file for client-facing pages."""
    invoice, pdf_bytes = InvoiceService.pdf_bytes(db, invoice_id)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{invoice.invoice_number}.pdf"'},
    )


@public_router.post("/{invoice_id}/stripe-checkout-session", response_model=StripeCheckoutSessionResponse)
async def create_stripe_checkout_session(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout session for the invoice's outstanding balance."""
    invoice = InvoiceService.get(db, invoice_id)
    return StripeCheckoutSessionResponse(url=StripeService.create_checkout_session(invoice))
