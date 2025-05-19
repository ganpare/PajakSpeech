import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application settings
    """
    PROJECT_NAME: str = "Audio Transcription App"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # Database
    DATABASE_URL: str = "sqlite:///./transcription.db"
    
    # NVIDIA ASR Model
    ASR_MODEL: str = "nvidia/parakeet-tdt-0.6b-v2"
    
    # Processing settings
    MAX_CHUNK_DURATION: int = 30  # in seconds, for long audio processing

    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings()

# Create necessary directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
