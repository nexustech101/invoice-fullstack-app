"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.db import engine, Base, SessionLocal
from api import models  # noqa: F401
from api.app.v1 import api
from api.services import AuthService

# Create database tables on startup
def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown."""
    # Startup
    create_tables()
    db = SessionLocal()
    try:
        AuthService.ensure_default_admin(db)
    finally:
        db.close()
    yield
    # Shutdown
    pass


# Initialize FastAPI app
app = FastAPI(
    title="Invoice Management API",
    description="RESTful API for invoice management and billing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://127.0.0.1:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API router
app.include_router(api.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Invoice Management API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
