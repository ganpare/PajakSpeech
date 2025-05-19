FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including FFmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

# Copy application code
COPY . .

# Create directory for uploads
RUN mkdir -p uploads

# Expose the port
EXPOSE 5000

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]