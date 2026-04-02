"""Authentication endpoints for the admin dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.app.v1.schemas import (
    AdminProfile,
    CredentialUpdateRequest,
    LoginRequest,
    LoginResponse,
)
from api.db import get_db
from api.models import AdminAccount
from api.services import AuthService


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate the admin dashboard user."""
    admin, token = AuthService.login(db, payload.username, payload.password)
    return LoginResponse(
        access_token=token,
        username=admin.username,
        last_login=admin.last_login,
    )


@router.get("/me", response_model=AdminProfile)
async def get_me(admin: AdminAccount = Depends(AuthService.get_current_admin)):
    """Return the active admin profile."""
    return admin


@router.post("/change-credentials", response_model=LoginResponse)
async def change_credentials(
    payload: CredentialUpdateRequest,
    db: Session = Depends(get_db),
    admin: AdminAccount = Depends(AuthService.get_current_admin),
):
    """Update the dashboard username and password, then rotate the session."""
    updated_admin = AuthService.update_credentials(
        db=db,
        admin=admin,
        current_password=payload.current_password,
        new_username=payload.new_username,
        new_password=payload.new_password,
    )
    token = AuthService.issue_token(updated_admin)
    return LoginResponse(
        access_token=token,
        username=updated_admin.username,
        last_login=updated_admin.last_login,
    )
