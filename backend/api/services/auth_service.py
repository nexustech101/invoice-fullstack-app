"""Admin authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.config import settings
from api.db import get_db
from api.models import AdminAccount


http_bearer = HTTPBearer(auto_error=False)


class AuthService:
    """Token issuance and admin credential management."""

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000)
        return base64.urlsafe_b64encode(hashed).decode("utf-8")

    @staticmethod
    def _new_password_material(password: str) -> tuple[str, str]:
        salt = os.urandom(16)
        return (
            base64.urlsafe_b64encode(salt).decode("utf-8"),
            AuthService._hash_password(password, salt),
        )

    @staticmethod
    def _verify_password(password: str, salt_b64: str, password_hash: str) -> bool:
        salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
        computed = AuthService._hash_password(password, salt)
        return hmac.compare_digest(computed, password_hash)

    @staticmethod
    def _sign(data: bytes) -> str:
        signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), data, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(signature).decode("utf-8")

    @staticmethod
    def _encode_token(payload: dict) -> str:
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")
        signature = AuthService._sign(encoded_payload.encode("utf-8"))
        return f"{encoded_payload}.{signature}"

    @staticmethod
    def _decode_token(token: str) -> dict:
        try:
            encoded_payload, signature = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        expected_signature = AuthService._sign(encoded_payload.encode("utf-8"))
        if not hmac.compare_digest(expected_signature, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

        payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode("utf-8")).decode("utf-8"))
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if expires_at <= datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return payload

    @staticmethod
    def issue_token(admin: AdminAccount) -> str:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
        return AuthService._encode_token(
            {
                "sub": admin.username,
                "ver": admin.token_version,
                "exp": int(expires_at.timestamp()),
            }
        )

    @staticmethod
    def ensure_default_admin(db: Session) -> AdminAccount:
        admin = db.query(AdminAccount).first()
        if admin:
            return admin

        salt, password_hash = AuthService._new_password_material("admin")
        admin = AdminAccount(
            username="admin",
            password_salt=salt,
            password_hash=password_hash,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin

    @staticmethod
    def login(db: Session, username: str, password: str) -> tuple[AdminAccount, str]:
        admin = db.query(AdminAccount).filter(AdminAccount.username == username).first()
        if not admin or not AuthService._verify_password(password, admin.password_salt, admin.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        admin.last_login = datetime.utcnow()
        db.add(admin)
        db.commit()
        db.refresh(admin)
        token = AuthService.issue_token(admin)
        return admin, token

    @staticmethod
    def get_current_admin(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
        db: Session = Depends(get_db),
    ) -> AdminAccount:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        payload = AuthService._decode_token(credentials.credentials)
        admin = db.query(AdminAccount).filter(AdminAccount.username == payload["sub"]).first()
        if not admin or admin.token_version != payload["ver"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid")
        return admin

    @staticmethod
    def update_credentials(
        db: Session,
        admin: AdminAccount,
        current_password: str,
        new_username: str,
        new_password: str,
    ) -> AdminAccount:
        if not AuthService._verify_password(current_password, admin.password_salt, admin.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        existing = (
            db.query(AdminAccount)
            .filter(AdminAccount.username == new_username, AdminAccount.id != admin.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

        salt, password_hash = AuthService._new_password_material(new_password)
        admin.username = new_username
        admin.password_salt = salt
        admin.password_hash = password_hash
        admin.token_version += 1
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
