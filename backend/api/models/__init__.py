"""
SQLAlchemy ORM models for the invoicing application.
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from decimal import Decimal
from api.db import Base
from api.config import settings


class Business(Base):
    """Single record storing the business owner's information."""
    __tablename__ = "business"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city_state_zip = Column(String, nullable=False)
    tax_id = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    bsb = Column(String, nullable=True)
    payment_terms = Column(String, default="Net 30")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="business")

    @property
    def paypal_url(self) -> str | None:
        return settings.PAYPAL_URL

    @property
    def stripe_enabled(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    @property
    def stripe_webhook_ready(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)

    @property
    def payment_currency(self) -> str:
        return settings.PAYMENT_CURRENCY.upper()


class AdminAccount(Base):
    """Single admin credential record for dashboard authentication."""
    __tablename__ = "admin_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_salt = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    token_version = Column(Integer, default=1, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Client(Base):
    """Customer information."""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city_state_zip = Column(String, nullable=False)
    tax_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")


class Invoice(Base):
    """Invoice data."""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    order_number = Column(String, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    business_id = Column(Integer, ForeignKey("business.id"), default=1)
    
    # Dates
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    
    # Financial
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"))
    tax_rate_pct = Column(Numeric(5, 2), default=Decimal("10.00"))
    tax_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    total = Column(Numeric(12, 2), default=Decimal("0.00"))
    paid_amount = Column(Numeric(12, 2), default=Decimal("0.00"))
    
    # Status: draft, sent, paid, overdue, overdue_paid
    status = Column(String, default="draft", index=True)
    
    # Metadata
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="invoices")
    client = relationship("Client", back_populates="invoices")
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    @property
    def public_url(self) -> str:
        base_url = settings.FRONTEND_URL.rstrip("/")
        return f"{base_url}/pay/{self.id}"

    @property
    def amount_due(self) -> Decimal:
        return max(Decimal("0.00"), (self.total or Decimal("0.00")) - (self.paid_amount or Decimal("0.00")))


class LineItem(Base):
    """Individual row items in an invoice."""
    __tablename__ = "line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    seq_order = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    details = Column(String, nullable=True)
    qty = Column(Numeric(8, 2), nullable=False)
    rate = Column(Numeric(12, 2), nullable=False)
    adjustment_pct = Column(Numeric(5, 2), default=Decimal("0.00"))
    sub_total = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")


class Payment(Base):
    """Payment records for invoices."""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    method = Column(String, nullable=False)  # bank_transfer, stripe, paypal, cash, other
    transaction_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
