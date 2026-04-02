"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ============================================================================
# Business Schemas
# ============================================================================

class BusinessBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city_state_zip: str
    tax_id: Optional[str] = None
    logo_url: Optional[str] = None
    bank_name: str
    account_number: str
    bsb: Optional[str] = None
    payment_terms: str = "Net 30"
    paypal_url: Optional[str] = None
    stripe_enabled: bool = False
    stripe_webhook_ready: bool = False
    payment_currency: str = "USD"


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city_state_zip: Optional[str] = None
    tax_id: Optional[str] = None
    logo_url: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    bsb: Optional[str] = None
    payment_terms: Optional[str] = None


class BusinessRead(BusinessBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessSummary(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city_state_zip: str
    logo_url: Optional[str] = None
    bank_name: str
    account_number: str
    bsb: Optional[str] = None
    payment_terms: str
    paypal_url: Optional[str] = None
    stripe_enabled: bool = False
    stripe_webhook_ready: bool = False
    payment_currency: str = "USD"

    class Config:
        from_attributes = True


# ============================================================================
# Client Schemas
# ============================================================================

class ClientBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city_state_zip: str
    tax_id: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city_state_zip: Optional[str] = None
    tax_id: Optional[str] = None


class ClientRead(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientSummary(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True


# ============================================================================
# LineItem Schemas
# ============================================================================

class LineItemBase(BaseModel):
    description: str
    details: Optional[str] = None
    qty: Decimal = Field(..., gt=0)
    rate: Decimal = Field(..., ge=0)
    adjustment_pct: Decimal = Field(default=Decimal("0.00"), ge=-100, le=100)


class LineItemCreate(LineItemBase):
    pass


class LineItemRead(LineItemBase):
    id: int
    invoice_id: int
    seq_order: int
    sub_total: Decimal

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Schemas
# ============================================================================

class InvoiceLineItemCreate(BaseModel):
    description: str
    details: Optional[str] = None
    qty: Decimal = Field(..., gt=0)
    rate: Decimal = Field(..., ge=0)
    adjustment_pct: Decimal = Field(default=Decimal("0.00"), ge=-100, le=100)


class InvoiceCreate(BaseModel):
    client_id: int
    order_number: Optional[str] = None
    invoice_date: date
    due_date: date
    tax_rate_pct: Decimal = Decimal("10.00")
    notes: Optional[str] = None
    line_items: List[InvoiceLineItemCreate]


class InvoiceUpdate(BaseModel):
    order_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    tax_rate_pct: Optional[Decimal] = None
    notes: Optional[str] = None
    line_items: Optional[List[InvoiceLineItemCreate]] = None


class InvoiceRead(BaseModel):
    id: int
    invoice_number: str
    order_number: Optional[str] = None
    client_id: int
    invoice_date: date
    due_date: date
    subtotal: Decimal
    tax_rate_pct: Decimal
    tax_amount: Decimal
    total: Decimal
    paid_amount: Decimal
    status: str
    notes: Optional[str] = None
    line_items: List[LineItemRead] = []
    client: Optional[ClientSummary] = None
    business: Optional[BusinessSummary] = None
    public_url: Optional[str] = None
    amount_due: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceSendResponse(BaseModel):
    invoice_id: int
    invoice_number: str
    status: str
    payment_url: str
    email: dict


class StripeCheckoutSessionResponse(BaseModel):
    url: str


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentCreate(BaseModel):
    invoice_id: int
    date: date
    amount: Decimal = Field(..., gt=0)
    method: str  # bank_transfer, stripe, paypal, cash, other
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class PaymentRead(PaymentCreate):
    id: int
    invoice_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Dashboard Schemas
# ============================================================================

class DashboardSummary(BaseModel):
    total_invoices: int
    total_revenue: Decimal
    paid_invoices: int
    paid_amount: Decimal
    outstanding_amount: Decimal
    overdue_invoices: int
    overdue_amount: Decimal


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    by_status: dict
    monthly_revenue: List[dict]
    top_clients: List[dict]
    recent_payments: List[dict]


# ============================================================================
# Auth Schemas
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    last_login: Optional[datetime] = None


class AdminProfile(BaseModel):
    username: str
    last_login: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class CredentialUpdateRequest(BaseModel):
    current_password: str
    new_username: str = Field(..., min_length=3)
    new_password: str = Field(..., min_length=4)
