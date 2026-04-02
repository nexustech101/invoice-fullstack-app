"""Invoice domain service."""

from __future__ import annotations

from datetime import date
import re

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from api.models import Client, Invoice, LineItem
from api.services.business_service import BusinessService
from api.services.common import invoice_totals, line_item_subtotal, money, resolve_invoice_status
from api.services.document_service import DocumentService
from api.services.email_service import EmailService


class InvoiceService:
    """Create, update, send, and export invoices."""

    INVOICE_PATTERN = re.compile(r"^INV-(\d{4})-(\d{4})$")

    @staticmethod
    def _base_query(db: Session):
        return db.query(Invoice).options(
            selectinload(Invoice.client),
            selectinload(Invoice.business),
            selectinload(Invoice.line_items),
            selectinload(Invoice.payments),
        )

    @staticmethod
    def get(db: Session, invoice_id: int) -> Invoice:
        invoice = InvoiceService._base_query(db).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return invoice

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50) -> list[Invoice]:
        return (
            InvoiceService._base_query(db)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def _build_line_items(invoice: Invoice, payload_items: list) -> list[LineItem]:
        line_items: list[LineItem] = []
        for index, item in enumerate(payload_items, start=1):
            sub_total = line_item_subtotal(item.qty, item.rate, item.adjustment_pct)
            line_items.append(
                LineItem(
                    invoice=invoice,
                    seq_order=index,
                    description=item.description,
                    details=item.details,
                    qty=money(item.qty),
                    rate=money(item.rate),
                    adjustment_pct=money(item.adjustment_pct),
                    sub_total=sub_total,
                )
            )
        return line_items

    @staticmethod
    def _generate_invoice_number(db: Session, invoice_date: date) -> str:
        year = invoice_date.year
        prefix = f"INV-{year}-"
        invoice_numbers = (
            db.query(Invoice.invoice_number)
            .filter(Invoice.invoice_number.like(f"{prefix}%"))
            .all()
        )
        next_sequence = 1
        for (invoice_number,) in invoice_numbers:
            match = InvoiceService.INVOICE_PATTERN.match(invoice_number)
            if match and int(match.group(1)) == year:
                next_sequence = max(next_sequence, int(match.group(2)) + 1)
        return f"INV-{year}-{next_sequence:04d}"

    @staticmethod
    def create(db: Session, payload) -> Invoice:
        client = db.query(Client).filter(Client.id == payload.client_id).first()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

        business = BusinessService.get_or_create(db)
        invoice = Invoice(
            client_id=payload.client_id,
            business_id=business.id,
            invoice_number=InvoiceService._generate_invoice_number(db, payload.invoice_date),
            order_number=payload.order_number,
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            tax_rate_pct=money(payload.tax_rate_pct),
            notes=payload.notes,
            status="draft",
        )
        invoice.line_items = InvoiceService._build_line_items(invoice, payload.line_items)
        subtotal, tax_amount, total = invoice_totals(invoice.line_items, invoice.tax_rate_pct)
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total = total
        invoice.paid_amount = money("0.00")

        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return InvoiceService.get(db, invoice.id)

    @staticmethod
    def update(db: Session, invoice_id: int, updates) -> Invoice:
        invoice = InvoiceService.get(db, invoice_id)
        if invoice.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft invoices can be edited",
            )

        payload = updates.model_dump(exclude_unset=True)
        line_items = payload.pop("line_items", None)
        for field, value in payload.items():
            setattr(invoice, field, value)

        if line_items is not None:
            invoice.line_items.clear()
            invoice.line_items = InvoiceService._build_line_items(invoice, updates.line_items)

        subtotal, tax_amount, total = invoice_totals(invoice.line_items, invoice.tax_rate_pct)
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total = total
        invoice.status = resolve_invoice_status(invoice.status, invoice.due_date, invoice.paid_amount, invoice.total)

        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return InvoiceService.get(db, invoice.id)

    @staticmethod
    def delete(db: Session, invoice_id: int) -> None:
        invoice = InvoiceService.get(db, invoice_id)
        if invoice.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft invoices can be deleted",
            )
        db.delete(invoice)
        db.commit()

    @staticmethod
    def send(db: Session, invoice_id: int) -> dict:
        invoice = InvoiceService.get(db, invoice_id)
        pdf_bytes = DocumentService.generate_invoice_pdf(invoice)
        email_result = EmailService.send_invoice(invoice, pdf_bytes, invoice.public_url)
        if invoice.status == "draft":
            invoice.status = "sent"
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "payment_url": invoice.public_url,
            "email": email_result,
        }

    @staticmethod
    def pdf_bytes(db: Session, invoice_id: int) -> tuple[Invoice, bytes]:
        invoice = InvoiceService.get(db, invoice_id)
        return invoice, DocumentService.generate_invoice_pdf(invoice)

    @staticmethod
    def mark_paid(db: Session, invoice_id: int) -> Invoice:
        invoice = InvoiceService.get(db, invoice_id)
        invoice.paid_amount = money(invoice.total)
        invoice.status = "overdue_paid" if invoice.due_date < date.today() else "paid"
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return InvoiceService.get(db, invoice.id)

    @staticmethod
    def mark_overdue(db: Session, invoice_id: int) -> Invoice:
        invoice = InvoiceService.get(db, invoice_id)
        if money(invoice.paid_amount) >= money(invoice.total):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid invoices cannot be overdue")
        invoice.status = "overdue"
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return InvoiceService.get(db, invoice.id)
