from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from .config import settings
from .database import engine, Base
from .routers import auth, jobs, admin, public
from .routers.linucb import router_linucb

import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="PES Scan API",
    description="API for quantum chemistry PES (Potential Energy Surface) scans",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(public.router_public)
app.include_router(router_linucb)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend",
                             "dist")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes"""
        if full_path.startswith("api/"):
            return {"error": "API endpoint not found"}

        # Serve index.html for all frontend routes
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return {"error": "Frontend not built"}


@app.get("/")
async def root():
    return {"message": "PES Scan API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
