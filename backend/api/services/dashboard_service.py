"""Dashboard and reporting helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from api.models import Invoice, Payment
from api.services.common import money


class DashboardService:
    """Aggregate dashboard metrics from invoices and payments."""

    @staticmethod
    def _invoices(db: Session) -> list[Invoice]:
        return (
            db.query(Invoice)
            .options(selectinload(Invoice.client), selectinload(Invoice.payments))
            .all()
        )

    @staticmethod
    def _payments(db: Session) -> list[Payment]:
        return (
            db.query(Payment)
            .options(selectinload(Payment.invoice).selectinload(Invoice.client))
            .order_by(Payment.date.desc(), Payment.id.desc())
            .all()
        )

    @staticmethod
    def summary(db: Session) -> dict:
        invoices = DashboardService._invoices(db)
        total_invoices = len(invoices)
        total_revenue = money(sum((money(invoice.paid_amount) for invoice in invoices), Decimal("0.00")))
        paid_invoices = sum(1 for invoice in invoices if invoice.status in {"paid", "overdue_paid"})
        paid_amount = total_revenue
        outstanding_amount = money(
            sum((money(invoice.total) - money(invoice.paid_amount) for invoice in invoices), Decimal("0.00"))
        )
        overdue_invoices = sum(1 for invoice in invoices if invoice.status == "overdue")
        overdue_amount = money(
            sum(
                (
                    money(invoice.total) - money(invoice.paid_amount)
                    for invoice in invoices
                    if invoice.status == "overdue"
                ),
                Decimal("0.00"),
            )
        )

        return {
            "total_invoices": total_invoices,
            "total_revenue": total_revenue,
            "paid_invoices": paid_invoices,
            "paid_amount": paid_amount,
            "outstanding_amount": outstanding_amount,
            "overdue_invoices": overdue_invoices,
            "overdue_amount": overdue_amount,
        }

    @staticmethod
    def status_summary(db: Session) -> dict:
        invoices = DashboardService._invoices(db)
        counts: dict[str, int] = defaultdict(int)
        for invoice in invoices:
            counts[invoice.status] += 1
        return dict(counts)

    @staticmethod
    def monthly_revenue(db: Session, year: int | None = None) -> list[dict]:
        target_year = year or date.today().year
        payments = DashboardService._payments(db)
        buckets: dict[int, Decimal] = {month: Decimal("0.00") for month in range(1, 13)}
        for payment in payments:
            if payment.date.year == target_year:
                buckets[payment.date.month] += money(payment.amount)

        return [
            {"month": month, "label": date(target_year, month, 1).strftime("%b"), "amount": money(amount)}
            for month, amount in buckets.items()
        ]

    @staticmethod
    def top_clients(db: Session, limit: int = 10) -> list[dict]:
        invoices = DashboardService._invoices(db)
        totals: dict[int, dict] = {}
        for invoice in invoices:
            if invoice.client_id not in totals:
                totals[invoice.client_id] = {
                    "client_id": invoice.client_id,
                    "client_name": invoice.client.name,
                    "amount": Decimal("0.00"),
                }
            totals[invoice.client_id]["amount"] += money(invoice.paid_amount)

        ranked = sorted(totals.values(), key=lambda entry: entry["amount"], reverse=True)[:limit]
        return [{**entry, "amount": money(entry["amount"])} for entry in ranked]

    @staticmethod
    def recent_payments(db: Session, limit: int = 10) -> list[dict]:
        payments = DashboardService._payments(db)[:limit]
        return [
            {
                "id": payment.id,
                "invoice_id": payment.invoice_id,
                "invoice_number": payment.invoice.invoice_number,
                "client_name": payment.invoice.client.name,
                "date": payment.date,
                "amount": money(payment.amount),
                "method": payment.method,
            }
            for payment in payments
        ]

    @staticmethod
    def full_dashboard(db: Session) -> dict:
        return {
            "summary": DashboardService.summary(db),
            "by_status": DashboardService.status_summary(db),
            "monthly_revenue": DashboardService.monthly_revenue(db),
            "top_clients": DashboardService.top_clients(db, limit=5),
            "recent_payments": DashboardService.recent_payments(db, limit=5),
        }
