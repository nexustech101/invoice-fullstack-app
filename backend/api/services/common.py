"""Shared service helpers for invoice domain logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


TWOPLACES = Decimal("0.01")
HUNDRED = Decimal("100")


def money(value: Decimal | int | float | str) -> Decimal:
    """Normalize a numeric value to a two-decimal currency amount."""
    if isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(str(value))
    return decimal_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def line_item_subtotal(qty: Decimal, rate: Decimal, adjustment_pct: Decimal) -> Decimal:
    """Calculate a line item subtotal including any percentage adjustment."""
    base = money(qty) * money(rate)
    multiplier = Decimal("1") + (adjustment_pct / HUNDRED)
    return money(base * multiplier)


def invoice_totals(line_items: Iterable[object], tax_rate_pct: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate subtotal, tax amount, and total for a collection of line items."""
    subtotal = money(sum((money(item.sub_total) for item in line_items), Decimal("0.00")))
    tax_amount = money(subtotal * (tax_rate_pct / HUNDRED))
    total = money(subtotal + tax_amount)
    return subtotal, tax_amount, total


def resolve_invoice_status(current_status: str, due_date: date, paid_amount: Decimal, total: Decimal) -> str:
    """Determine invoice status based on outstanding balance and due date."""
    paid_amount = money(paid_amount)
    total = money(total)
    if paid_amount >= total and total > Decimal("0.00"):
        return "overdue_paid" if current_status == "overdue" or due_date < date.today() else "paid"
    if due_date < date.today():
        return "overdue"
    if current_status == "draft" and paid_amount == Decimal("0.00"):
        return "draft"
    return "sent"
