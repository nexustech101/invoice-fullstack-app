"""Business profile service helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from api.models import Business


DEFAULT_BUSINESS = {
    "name": "Architech, LLC",
    "email": "admin@architech.com",
    "phone": "+1-555-0101",
    "address_line1": "Suite 5A-1204",
    "address_line2": "123 Somewhere Street",
    "city_state_zip": "Phoenix, AZ 85001",
    "tax_id": "ABN 12 345 678 901",
    "logo_url": None,
    "bank_name": "ANZ Bank",
    "account_number": "****1234",
    "bsb": "123-456",
    "payment_terms": "Net 30",
}


class BusinessService:
    """Single-record business profile operations."""

    @staticmethod
    def get_or_create(db: Session) -> Business:
        business = db.query(Business).first()
        if business:
            return business

        business = Business(**DEFAULT_BUSINESS)
        db.add(business)
        db.commit()
        db.refresh(business)
        return business

    @staticmethod
    def update(db: Session, updates: dict) -> Business:
        business = BusinessService.get_or_create(db)
        for field, value in updates.items():
            setattr(business, field, value)
        db.add(business)
        db.commit()
        db.refresh(business)
        return business
