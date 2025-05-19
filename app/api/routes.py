import os
import json
import shutil
import aiofiles
from fastapi import APIRouter, Request, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid
import time

from app.core.config import settings
from app.core.models import TranscriptionJob, JobStatus
from app.core.transcription import transcribe_audio, get_job_progress
from app.core.file_processing import preprocess_audio, generate_output_file
from app.utils.formatters import format_timestamp

# Initialize templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render main index page
    """
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """
    Render upload page
    """
    return templates.TemplateResponse("upload.html", {"request": request})

@router.get("/results/{job_id}", response_class=HTMLResponse)
async def results_page(request: Request, job_id: str):
    """
    Render results page for a specific job
    """
    # Check if job exists
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"Job with ID {job_id} not found"
        })
    
    return templates.TemplateResponse("results.html", {
        "request": request,
        "job_id": job_id,
        "job_status": job.status,
    })

@router.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload audio file endpoint
    """
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Create directory for this job if it doesn't exist
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    os.makedirs(job_dir, exist_ok=True)
    
    # Save the file to the job directory
    file_path = job_dir / file.filename
    
    try:
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Create job in database
        job = TranscriptionJob(
            id=job_id,
            filename=file.filename,
            file_path=str(file_path),
            status=JobStatus.UPLOADED,
            created_at=time.time()
        )
        job.save()
        
        return {"success": True, "job_id": job_id, "filename": file.filename}
    
    except Exception as e:
        # Clean up on error
        if job_dir.exists():
            shutil.rmtree(job_dir)
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/api/transcribe/{job_id}")
async def start_transcription(job_id: str, background_tasks: BackgroundTasks):
    """
    Start transcription process for the uploaded file
    """
    # Get job from database
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    if job.status != JobStatus.UPLOADED:
        return {"success": False, "message": f"Job is in {job.status} state, cannot start transcription"}
    
    # Update job status
    job.status = JobStatus.PREPROCESSING
    job.save()
    
    # Start transcription in background
    background_tasks.add_task(transcribe_audio, job_id)
    
    return {"success": True, "job_id": job_id, "status": job.status}

@router.get("/api/status/{job_id}")
async def check_status(job_id: str):
    """
    Check status of a transcription job
    """
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    # Get progress information if available
    progress = get_job_progress(job_id)
    
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": progress,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

@router.get("/api/results/{job_id}")
async def get_results(job_id: str):
    """
    Get transcription results
    """
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    if job.status != JobStatus.COMPLETED:
        return {"success": False, "message": f"Job is in {job.status} state, results not available"}
    
    # Get result file path
    results_path = Path(settings.UPLOAD_DIR) / job_id / "results.json"
    
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found")
    
    # Load and return results
    with open(results_path, "r") as f:
        results = json.load(f)
    
    return {"success": True, "job_id": job_id, "results": results}

@router.get("/api/download/{job_id}/{format}")
async def download_results(job_id: str, format: str):
    """
    Download transcription results in the specified format
    """
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is in {job.status} state, results not available")
    
    # Check if format is valid
    valid_formats = ["csv", "srt", "vtt", "json", "lrc"]
    if format not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format. Supported formats: {', '.join(valid_formats)}")
    
    # Generate the file if it doesn't exist
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    output_path = job_dir / f"transcription.{format}"
    
    if not output_path.exists():
        # Load results
        results_path = job_dir / "results.json"
        with open(results_path, "r") as f:
            results = json.load(f)
        
        # Generate output file
        generate_output_file(results, output_path, format)
    
    # Return file for download
    return FileResponse(
        path=output_path,
        filename=f"{job.filename.split('.')[0]}.{format}",
        media_type="application/octet-stream"
    )

@router.get("/api/segment_audio/{job_id}")
async def get_segment_audio(job_id: str, start_time: float, end_time: float):
    """
    Get audio segment for a specific time range
    """
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
    
    # Create segment directory if it doesn't exist
    job_dir = Path(settings.UPLOAD_DIR) / job_id
    segment_dir = job_dir / "segments"
    os.makedirs(segment_dir, exist_ok=True)
    
    # Generate segment filename
    segment_filename = f"segment_{start_time:.3f}_{end_time:.3f}.wav"
    segment_path = segment_dir / segment_filename
    
    # Extract segment if it doesn't exist
    if not segment_path.exists():
        try:
            import subprocess
            input_file = job.file_path
            
            # Use ffmpeg to extract segment
            cmd = [
                "ffmpeg", "-y", 
                "-i", input_file, 
                "-ss", str(start_time), 
                "-to", str(end_time), 
                "-c", "copy", 
                str(segment_path)
            ]
            subprocess.run(cmd, check=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting audio segment: {str(e)}")
    
    # Return audio segment
    return FileResponse(
        path=segment_path,
        filename=segment_filename,
        media_type="audio/wav"
    )
