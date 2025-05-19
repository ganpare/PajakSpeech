import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.models import init_db

def create_app():
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Audio Transcription Application using NVIDIA Parakeet ASR Model",
        version="1.0.0"
    )
    
    # Mount static files
    app.mount(
        "/static",
        StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
        name="static"
    )
    
    # Initialize database
    init_db()
    
    # Include API router
    app.include_router(api_router)
    
    return app
