"""Setu AI — FastAPI Application Entry Point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.database import init_db, seed_schemes
from app.config import settings

app = FastAPI(
    title="Setu AI — सेतु AI",
    description="AI-powered assistant for government scheme access",
    version="1.0.0",
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "forms"), exist_ok=True)

# Mount upload directory for serving generated PDFs
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")

# Register API routes
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    """Initialize DB and seed data on startup."""
    init_db()
    seed_schemes()


@app.get("/")
async def root():
    return {
        "name": "Setu AI — सेतु AI",
        "status": "running",
        "version": "1.0.0",
        "description": "AI-powered assistant for accessing government schemes",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
