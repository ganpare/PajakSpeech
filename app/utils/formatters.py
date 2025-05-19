def format_timestamp(seconds: float, format_type: str = "default") -> str:
    """
    Format timestamp in various formats
    
    Args:
        seconds: Time in seconds
        format_type: Format type (default, srt, vtt, lrc)
        
    Returns:
        Formatted timestamp string
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
