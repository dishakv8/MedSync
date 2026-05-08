from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.db.session import engine, Base

# Import all models so Alembic/SQLAlchemy sees them
from app.models import models  # noqa: F401

from app.api.routes import auth, patients, consultations, insights

# Auto-create tables on startup (use Alembic for production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered longitudinal healthcare memory system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded audio files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register routers
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(consultations.router)
app.include_router(insights.router)


@app.get("/", tags=["health"])
def root():
    return {"success": True, "message": f"{settings.APP_NAME} is running 🚀", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health():
    return {"success": True, "data": {"status": "healthy"}, "message": "OK"}
