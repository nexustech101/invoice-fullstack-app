"""Email helpers for invoice and receipt delivery."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from api.config import settings
from api.models import Invoice, Payment


class EmailService:
    """SMTP-backed email sender with graceful fallback when SMTP is not configured."""

    @staticmethod
    def _is_configured() -> bool:
        return bool(
            settings.SMTP_HOST
            and settings.SMTP_PORT
            and settings.SMTP_USER
            and settings.SMTP_PASSWORD
        )

    @staticmethod
    def _send_message(message: EmailMessage) -> dict:
        if not EmailService._is_configured():
            return {"status": "skipped", "reason": "SMTP not configured"}

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return {"status": "sent"}

    @staticmethod
    def send_invoice(invoice: Invoice, pdf_bytes: bytes, public_url: str) -> dict:
        message = EmailMessage()
        message["Subject"] = f"Invoice #{invoice.invoice_number}"
        message["From"] = settings.SMTP_USER or "noreply@invoicing.app"
        message["To"] = invoice.client.email
        message.set_content(
            "\n".join(
                [
                    f"Hi {invoice.client.name},",
                    "",
                    f"Please find attached invoice #{invoice.invoice_number}.",
                    f"Amount due: ${invoice.total}",
                    f"Due date: {invoice.due_date.isoformat()}",
                    "",
                    f"View and pay invoice online: {public_url}",
                    "The payment page includes any enabled Stripe or PayPal options, plus bank transfer details.",
                ]
            )
        )
        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"invoice-{invoice.invoice_number}.pdf",
        )
        return EmailService._send_message(message)

    @staticmethod
    def send_receipt(invoice: Invoice, payment: Payment, pdf_bytes: bytes) -> dict:
        message = EmailMessage()
        message["Subject"] = f"Payment Received - Invoice #{invoice.invoice_number}"
        message["From"] = settings.SMTP_USER or "noreply@invoicing.app"
        message["To"] = invoice.client.email
        message.set_content(
            "\n".join(
                [
                    f"Hi {invoice.client.name},",
                    "",
                    f"Thank you. We received your payment of ${payment.amount}.",
                    f"Invoice: #{invoice.invoice_number}",
                    f"Date paid: {payment.date.isoformat()}",
                    f"Method: {payment.method}",
                ]
            )
        )
        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"receipt-{payment.id}.pdf",
        )
        return EmailService._send_message(message)
