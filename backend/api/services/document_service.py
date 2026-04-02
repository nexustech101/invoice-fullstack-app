"""Wrappers around the existing PDF generator modules."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from api.config import settings
from api.models import Invoice, Payment
from api.modules.invoice import (
    BusinessInfo as InvoiceBusinessInfo,
    ClientInfo as InvoiceClientInfo,
    InvoiceData,
    InvoiceMetadata,
    InvoicePDFGenerator,
    LineItem as InvoiceLineItem,
)
from api.modules.receipt import (
    BusinessInfo as ReceiptBusinessInfo,
    ClientInfo as ReceiptClientInfo,
    InvoiceInfo as ReceiptInvoiceInfo,
    LineItem as ReceiptLineItem,
    ReceiptData,
    ReceiptPDFGenerator,
)


class DocumentService:
    """Generate invoice and receipt PDFs using the preserved module files."""

    @staticmethod
    def _logo_path() -> str | None:
        logo_path = Path(settings.LOGO_PATH)
        return str(logo_path) if logo_path.exists() else None

    @staticmethod
    def _render_invoice_pdf(payload: InvoiceData) -> bytes:
        with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            InvoicePDFGenerator(payload).generate(temp_path)
            return temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def generate_invoice_pdf(invoice: Invoice) -> bytes:
        business = invoice.client and getattr(invoice, "business", None)
        business_record = business if business is not None else None
        online_payment_methods: list[str] = []
        if settings.STRIPE_SECRET_KEY:
            online_payment_methods.append("Stripe")
        if settings.PAYPAL_URL:
            online_payment_methods.append("PayPal")

        payment_instructions = (
            "Pay by bank transfer using the account details below."
            if not online_payment_methods
            else "Scan the QR code to open the secure payment page"
            + f" and pay online with {' or '.join(online_payment_methods)}."
        )

        invoice_notes = invoice.notes or ""
        if online_payment_methods:
            online_note = "Online payment options are available from the invoice payment page."
            invoice_notes = f"{invoice_notes}\n\n{online_note}".strip()

        payload = InvoiceData(
            business=InvoiceBusinessInfo(
                name=business_record.name if business_record else "Architech, LLC",
                address_line1=business_record.address_line1 if business_record else "",
                address_line2=business_record.address_line2 if business_record else "",
                city_state_zip=business_record.city_state_zip if business_record else "",
                email=business_record.email if business_record else "",
                phone=business_record.phone if business_record else "",
                abn_or_tax_id=business_record.tax_id if business_record else "",
            ),
            client=InvoiceClientInfo(
                name=invoice.client.name,
                address_line1=invoice.client.address_line1,
                address_line2=invoice.client.address_line2 or invoice.client.city_state_zip,
                email=invoice.client.email,
            ),
            meta=InvoiceMetadata(
                invoice_number=invoice.invoice_number,
                order_number=invoice.order_number or "",
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                payment_terms=(business_record.payment_terms if business_record else "Net 30"),
            ),
            line_items=[
                InvoiceLineItem(
                    qty=item.qty,
                    description=item.description,
                    rate=item.rate,
                    details=item.details,
                    adjustment_pct=item.adjustment_pct,
                )
                for item in invoice.line_items
            ],
            tax_rate_pct=invoice.tax_rate_pct,
            payment_url=invoice.public_url,
            bank_name=business_record.bank_name if business_record else "",
            account_number=business_record.account_number if business_record else "",
            bsb=business_record.bsb if business_record and business_record.bsb else "",
            payment_instructions=payment_instructions,
            notes=invoice_notes,
            logo_path=DocumentService._logo_path(),
            overdue=invoice.status == "overdue",
        )

        try:
            return DocumentService._render_invoice_pdf(payload)
        except RuntimeError as exc:
            if "QR generation failed" not in str(exc):
                raise
            payload.payment_url = ""
            return DocumentService._render_invoice_pdf(payload)

    @staticmethod
    def generate_receipt_pdf(invoice: Invoice, payment: Payment) -> bytes:
        business_record = getattr(invoice, "business", None)
        payload = ReceiptData(
            business=ReceiptBusinessInfo(
                name=business_record.name if business_record else "Architech, LLC",
                address_line1=business_record.address_line1 if business_record else "",
                address_line2=business_record.address_line2 if business_record else "",
                city_state_zip=business_record.city_state_zip if business_record else "",
                email=business_record.email if business_record else "",
            ),
            client=ReceiptClientInfo(
                name=invoice.client.name,
                address_line1=invoice.client.address_line1,
                address_line2=invoice.client.address_line2 or invoice.client.city_state_zip,
                email=invoice.client.email,
            ),
            invoice=ReceiptInvoiceInfo(
                receipt_number=f"REC-{payment.id:04d}",
                receipt_date=payment.date,
                total_paid=payment.amount,
            ),
            line_items=[
                ReceiptLineItem(
                    qty=item.qty,
                    description=item.description,
                    rate=item.rate,
                    details=item.details,
                    adjustment_pct=item.adjustment_pct,
                )
                for item in invoice.line_items
            ],
            tax_rate_pct=invoice.tax_rate_pct,
            bank_name=business_record.bank_name if business_record else "",
            account_number=business_record.account_number if business_record else "",
            bsb=business_record.bsb if business_record and business_record.bsb else "",
            notes=f"Payment received via {payment.method.replace('_', ' ')}.",
            paid=True,
            logo_path=DocumentService._logo_path(),
        )

        with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            ReceiptPDFGenerator().generate(payload, temp_path)
            return temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)
