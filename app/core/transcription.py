import os
import time
import json
import logging
# These imports will be available in the Docker container
# import torch
# import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import shutil
import tempfile
# from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq

# Placeholder for Docker implementation
import numpy as np
class DummyModule:
    pass

from app.core.config import settings
from app.core.models import TranscriptionJob, JobStatus, db_session
from app.core.file_processing import preprocess_audio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store job progress
JOB_PROGRESS = {}

def get_job_progress(job_id: str) -> float:
    """
    Get current progress for a job
    """
    return JOB_PROGRESS.get(job_id, 0.0)

def update_job_progress(job_id: str, progress: float) -> None:
    """
    Update progress for a job
    """
    JOB_PROGRESS[job_id] = progress
    
    # Update database
    job = TranscriptionJob.get_by_id(job_id)
    if job:
        job.progress = progress
        job.save()

def transcribe_audio(job_id: str) -> None:
    """
    Main function to preprocess and transcribe audio file
    """
    logger.info(f"Starting transcription for job {job_id}")
    
    # Get job from database
    job = TranscriptionJob.get_by_id(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return
    
    try:
        # Update job status
        job.status = JobStatus.PREPROCESSING
        job.save()
        
        # Preprocess audio file
        logger.info(f"Preprocessing audio for job {job_id}")
        audio_file = Path(job.file_path)
        processed_file = preprocess_audio(audio_file)
        
        # Update job status
        job.status = JobStatus.PROCESSING
        job.save()
        
        # Run transcription
        logger.info(f"Running transcription for job {job_id}")
        results = run_asr_model(processed_file, job_id)
        
        # Save results
        results_path = Path(settings.UPLOAD_DIR) / job_id / "results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
        
        # Update job status
        job.status = JobStatus.COMPLETED
        job.save()
        
        logger.info(f"Transcription completed for job {job_id}")
    
    except Exception as e:
        logger.error(f"Error in transcription for job {job_id}: {str(e)}")
        
        # Update job status
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.save()
        
        # Clean up progress tracking
        if job_id in JOB_PROGRESS:
            del JOB_PROGRESS[job_id]

def run_asr_model(audio_file: Path, job_id: str) -> Dict[str, Any]:
    """
    Run ASR model on the processed audio file
    """
    # Initialize model and processor
    update_job_progress(job_id, 5.0)
    
    logger.info("Loading ASR model and processor")
    processor = AutoProcessor.from_pretrained(settings.ASR_MODEL)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(settings.ASR_MODEL)
    
    # Check if GPU is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    
    update_job_progress(job_id, 10.0)
    
    # For long audio, we'll need to split it into chunks
    # First, load the audio data
    import librosa
    logger.info(f"Loading audio file {audio_file}")
    audio_data, sampling_rate = librosa.load(str(audio_file), sr=16000)
    
    # Calculate total duration
    duration = len(audio_data) / sampling_rate
    logger.info(f"Audio duration: {duration:.2f} seconds")
    
    # Split audio into chunks if needed
    chunk_size = settings.MAX_CHUNK_DURATION * sampling_rate
    
    if len(audio_data) <= chunk_size:
        # Process entire audio at once
        segments = process_audio_chunk(audio_data, processor, model, device)
        results = {"segments": segments, "duration": duration}
    else:
        # Process in chunks
        all_segments = []
        chunk_count = (len(audio_data) + chunk_size - 1) // chunk_size
        
        for i in range(chunk_count):
            logger.info(f"Processing chunk {i+1}/{chunk_count}")
            
            # Calculate progress based on chunks
            progress = 10.0 + (i / chunk_count) * 85.0
            update_job_progress(job_id, progress)
            
            # Get chunk
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, len(audio_data))
            chunk = audio_data[start_idx:end_idx]
            
            # Process chunk
            offset = start_idx / sampling_rate
            segments = process_audio_chunk(chunk, processor, model, device, offset)
            all_segments.extend(segments)
        
        # Merge adjacent segments if they belong together
        all_segments = merge_adjacent_segments(all_segments)
        
        results = {"segments": all_segments, "duration": duration}
    
    # Add word-level timing if available
    for segment in results["segments"]:
        if "words" not in segment:
            # For models that don't provide word-level timing, we'll estimate
            segment["words"] = estimate_word_timings(segment["text"], segment["start"], segment["end"])
    
    update_job_progress(job_id, 100.0)
    return results

def process_audio_chunk(audio_data: np.ndarray, processor, model, device: str, offset: float = 0.0) -> List[Dict[str, Any]]:
    """
    Process a chunk of audio data with the ASR model
    """
    # Prepare inputs
    inputs = processor(audio_data, sampling_rate=16000, return_tensors="pt")
    inputs = inputs.to(device)
    
    # Generate outputs
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_features, 
            language="en",
            task="transcribe",
            return_timestamps=True
        )
    
    # Convert outputs to segments
    result = processor.batch_decode(outputs, skip_special_tokens=False)
    
    # Process model output to extract timestamps
    segments = []
    current_segment = None
    
    # Process the tokens and extract timestamps
    for token in result[0].split():
        # Check for timestamp tokens
        if token.startswith("<|") and token.endswith("|>") and "time" in token:
            time_value = float(token.split("_")[1].split("|")[0])
            
            # Adjust time by offset for chunked processing
            time_value += offset
            
            if current_segment is None:
                # Start of a new segment
                current_segment = {
                    "start": time_value,
                    "text": ""
                }
            else:
                # End of current segment
                current_segment["end"] = time_value
                segments.append(current_segment)
                current_segment = None
        elif current_segment is not None and not token.startswith("<|") and not token.endswith("|>"):
            # Add regular tokens to the current segment text
            if current_segment["text"]:
                current_segment["text"] += " "
            current_segment["text"] += token
    
    # Handle the last segment if it's not closed
    if current_segment is not None and "end" not in current_segment:
        # Estimate end time based on last token
        current_segment["end"] = current_segment["start"] + (len(current_segment["text"].split()) * 0.3)
        segments.append(current_segment)
    
    return segments

def merge_adjacent_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge adjacent segments that are part of the same sentence
    """
    if not segments:
        return []
    
    merged = []
    current = segments[0].copy()
    
    for segment in segments[1:]:
        # Check if this segment should be merged with the current one
        # Criteria: time gap is small and current doesn't end with period/question/etc.
        time_gap = segment["start"] - current["end"]
        last_char = current["text"][-1] if current["text"] else ""
        
        if time_gap < 0.5 and last_char not in ".!?;":
            # Merge with current segment
            current["end"] = segment["end"]
            current["text"] += " " + segment["text"]
        else:
            # Add current to merged list and start a new current
            merged.append(current)
            current = segment.copy()
    
    # Add the last segment
    merged.append(current)
    
    return merged

def estimate_word_timings(text: str, start_time: float, end_time: float) -> List[Dict[str, Any]]:
    """
    Estimate word timings for a segment when the model doesn't provide them
    """
    words = text.strip().split()
    if not words:
        return []
    
    # Calculate average duration per word
    total_duration = end_time - start_time
    avg_word_duration = total_duration / len(words)
    
    word_timings = []
    current_time = start_time
    
    for word in words:
        word_duration = len(word) * avg_word_duration / 5  # Adjust duration based on word length
        word_duration = max(0.1, min(word_duration, 1.0))  # Keep between 0.1 and 1.0 seconds
        
        word_timings.append({
            "word": word,
            "start": current_time,
            "end": current_time + word_duration
        })
        
        current_time += word_duration
    
    # Adjust last word to match segment end time
    if word_timings:
        word_timings[-1]["end"] = end_time
    
    return word_timings
