import os
import subprocess
import tempfile
import json
import csv
from pathlib import Path
from typing import Dict, Any, List

def preprocess_audio(audio_file: Path) -> Path:
    """
    Preprocess audio file to make it compatible with the ASR model
    - Convert to 16kHz mono WAV format
    - Normalize audio levels
    """
    # Create a temporary file for processed audio
    job_dir = audio_file.parent
    processed_file = job_dir / "processed_audio.wav"
    
    # Use ffmpeg to process the audio
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_file),
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            "-af", "dynaudnorm",
            str(processed_file)
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return processed_file
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error preprocessing audio: {e.stderr.decode()}")
    
    except Exception as e:
        raise RuntimeError(f"Error preprocessing audio: {str(e)}")

def generate_output_file(results: Dict[str, Any], output_path: Path, format: str) -> None:
    """
    Generate output file in the specified format
    """
    if format == "json":
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
    
    elif format == "csv":
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(["segment", "start_time", "end_time", "text"])
            
            # Write data
            for i, segment in enumerate(results["segments"]):
                writer.writerow([
                    i + 1,
                    format_timestamp(segment["start"], "seconds"),
                    format_timestamp(segment["end"], "seconds"),
                    segment["text"]
                ])
    
    elif format == "srt":
        with open(output_path, "w") as f:
            for i, segment in enumerate(results["segments"]):
                f.write(f"{i + 1}\n")
                f.write(f"{format_timestamp(segment['start'], 'srt')} --> {format_timestamp(segment['end'], 'srt')}\n")
                f.write(f"{segment['text']}\n\n")
    
    elif format == "vtt":
        with open(output_path, "w") as f:
            f.write("WEBVTT\n\n")
            
            for i, segment in enumerate(results["segments"]):
                f.write(f"{format_timestamp(segment['start'], 'vtt')} --> {format_timestamp(segment['end'], 'vtt')}\n")
                
                # Include word timings if available
                if "words" in segment and segment["words"]:
                    for word in segment["words"]:
                        start = format_timestamp(word["start"], "vtt")
                        end = format_timestamp(word["end"], "vtt")
                        f.write(f"<{start}>{word['word']}</{end}> ")
                    f.write("\n\n")
                else:
                    f.write(f"{segment['text']}\n\n")
    
    elif format == "lrc":
        with open(output_path, "w") as f:
            f.write("[ti:Transcription]\n")
            f.write("[ar:ASR System]\n")
            
            for segment in results["segments"]:
                start_time = format_timestamp(segment["start"], "lrc")
                f.write(f"[{start_time}]{segment['text']}\n")

def format_timestamp(seconds: float, format_type: str) -> str:
    """
    Format timestamp in various formats
    """
    if format_type == "seconds":
        return f"{seconds:.3f}"
    
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = seconds % 60
    
    if format_type == "srt":
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{int((secs - int(secs)) * 1000):03d}"
    
    elif format_type == "vtt":
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{int((secs - int(secs)) * 1000):03d}"
    
    elif format_type == "lrc":
        return f"{minutes:02d}:{int(secs):02d}.{int((secs - int(secs)) * 100):02d}"
    
    # Default to HH:MM:SS format
    return f"{hours:02d}:{minutes:02d}:{secs:.3f}"
