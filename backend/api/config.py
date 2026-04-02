"""
FastAPI configuration and settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./invoicing.db"
    
    # API
    API_TITLE: str = "Invoice API"
    API_VERSION: str = "1.0.0"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3001"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 12
    PAYMENT_CURRENCY: str = "usd"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    PAYPAL_URL: Optional[str] = None
    
    # Email (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Paths
    LOGO_PATH: str = "./static/logo.png"
    
    class Config:
        env_file = (".env", "backend/.env", "api/.env")
        case_sensitive = True


settings = Settings()
