import os
import time
import json
import enum
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Float, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import Optional, List, Dict, Any

from app.core.config import settings

# Create database engine
engine = create_engine(str(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)
Base = declarative_base()

class JobStatus(str, enum.Enum):
    """
    Enum for job status
    """
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TranscriptionJob(Base):
    """
    Model for transcription job
    """
    __tablename__ = "transcription_jobs"
    
    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.UPLOADED)
    error = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)  # 0-100
    created_at = Column(Float, default=time.time)
    updated_at = Column(Float, default=time.time, onupdate=time.time)
    
    @classmethod
    def get_by_id(cls, job_id: str) -> Optional['TranscriptionJob']:
        """
        Get job by ID
        """
        return db_session.query(cls).filter(cls.id == job_id).first()
    
    def save(self) -> None:
        """
        Save or update job
        """
        self.updated_at = time.time()
        db_session.add(self)
        db_session.commit()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary
        """
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "error": self.error,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

def init_db() -> None:
    """
    Initialize database
    """
    Base.metadata.create_all(bind=engine)
