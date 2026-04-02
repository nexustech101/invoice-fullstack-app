"""Client CRUD service."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from api.models import Client, Invoice


class ClientService:
    """Client data access helpers with API-friendly exceptions."""

    @staticmethod
    def create(db: Session, payload: dict) -> Client:
        client = Client(**payload)
        db.add(client)
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 50, search: str | None = None) -> list[Client]:
        query = db.query(Client).order_by(Client.name.asc())
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(Client.name.ilike(term), Client.email.ilike(term)))
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get(db: Session, client_id: int) -> Client:
        client = (
            db.query(Client)
            .options(selectinload(Client.invoices))
            .filter(Client.id == client_id)
            .first()
        )
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    @staticmethod
    def update(db: Session, client_id: int, updates: dict) -> Client:
        client = ClientService.get(db, client_id)
        for field, value in updates.items():
            setattr(client, field, value)
        db.add(client)
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def delete(db: Session, client_id: int) -> None:
        client = ClientService.get(db, client_id)
        db.delete(client)
        db.commit()

    @staticmethod
    def invoices(db: Session, client_id: int, skip: int = 0, limit: int = 50) -> list[Invoice]:
        ClientService.get(db, client_id)
        return (
            db.query(Invoice)
            .options(selectinload(Invoice.line_items), selectinload(Invoice.client))
            .filter(Invoice.client_id == client_id)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
