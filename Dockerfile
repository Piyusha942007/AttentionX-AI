# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for video/audio processing
# libgl1-mesa-glx and libglib2.0-0 are required by OpenCV (MediaPipe)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    wget \
    curl \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the requirements file explicitly
COPY requirements.txt .

# Install packages (using the CPU-specific index included in requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code only
COPY backend/ .

# Expose the correct port for Render
EXPOSE 8000

# Set environment variables for temporary execution paths
# (Render ephemeral storage will drop these on restart, which is fine for queues)
ENV UPLOAD_DIR="/tmp/uploads"
ENV OUTPUT_DIR="/tmp/output_clips"
ENV CACHE_DIR="/tmp/cache/transcripts"

# Start FastAPI server using Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
