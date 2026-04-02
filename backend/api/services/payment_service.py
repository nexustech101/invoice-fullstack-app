"""Payment service logic."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from api.models import Invoice, Payment
from api.services.common import money, resolve_invoice_status
from api.services.document_service import DocumentService
from api.services.email_service import EmailService
from api.services.invoice_service import InvoiceService


class PaymentService:
    """Record and manage invoice payments."""

    @staticmethod
    def _base_query(db: Session):
        return db.query(Payment).options(
            selectinload(Payment.invoice).selectinload(Invoice.client),
            selectinload(Payment.invoice).selectinload(Invoice.business),
            selectinload(Payment.invoice).selectinload(Invoice.line_items),
        )

    @staticmethod
    def get(db: Session, payment_id: int) -> Payment:
        payment = PaymentService._base_query(db).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50, invoice_id: int | None = None) -> list[Payment]:
        query = PaymentService._base_query(db).order_by(Payment.date.desc(), Payment.id.desc())
        if invoice_id is not None:
            query = query.filter(Payment.invoice_id == invoice_id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, payload) -> Payment:
        if payload.transaction_id:
            existing = (
                PaymentService._base_query(db)
                .filter(Payment.transaction_id == payload.transaction_id)
                .first()
            )
            if existing:
                return existing

        invoice = InvoiceService.get(db, payload.invoice_id)
        outstanding = money(invoice.total) - money(invoice.paid_amount)
        if money(payload.amount) > outstanding:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment exceeds outstanding balance")

        payment = Payment(
            invoice_id=payload.invoice_id,
            date=payload.date,
            amount=money(payload.amount),
            method=payload.method,
            transaction_id=payload.transaction_id,
            notes=payload.notes,
        )
        invoice.paid_amount = money(invoice.paid_amount + payment.amount)
        invoice.status = resolve_invoice_status(invoice.status, invoice.due_date, invoice.paid_amount, invoice.total)

        db.add(payment)
        db.add(invoice)
        db.commit()
        db.refresh(payment)

        payment = PaymentService.get(db, payment.id)
        receipt_bytes = DocumentService.generate_receipt_pdf(payment.invoice, payment)
        EmailService.send_receipt(payment.invoice, payment, receipt_bytes)
        return payment

    @staticmethod
    def delete(db: Session, payment_id: int) -> None:
        payment = PaymentService.get(db, payment_id)
        invoice = payment.invoice
        invoice.paid_amount = money(invoice.paid_amount - payment.amount)
        invoice.status = resolve_invoice_status(invoice.status, invoice.due_date, invoice.paid_amount, invoice.total)
        db.add(invoice)
        db.delete(payment)
        db.commit()
