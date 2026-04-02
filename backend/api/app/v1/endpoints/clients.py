"""Client endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from api.db import get_db
from api.app.v1.schemas import ClientCreate, ClientUpdate, ClientRead, InvoiceRead
from api.services import ClientService

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db)
):
    """Create a new client."""
    return ClientService.create(db, client.model_dump())


@router.get("", response_model=List[ClientRead])
async def list_clients(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    """List all clients with optional search."""
    return ClientService.list(db, skip=skip, limit=limit, search=search)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific client by ID."""
    return ClientService.get(db, client_id)


@router.put("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db)
):
    """Update a client."""
    return ClientService.update(db, client_id, client_update.model_dump(exclude_unset=True))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Delete a client."""
    ClientService.delete(db, client_id)


@router.get("/{client_id}/invoices", response_model=List[InvoiceRead])
async def get_client_invoices(
    client_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all invoices for a specific client."""
    return ClientService.invoices(db, client_id, skip=skip, limit=limit)
