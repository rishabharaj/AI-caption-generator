# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# ffmpeg: required for video and audio processing, frame extraction, and caption burning
# fontconfig & libfontconfig1 & libfreetype6: required for FFmpeg's drawtext filter to render fonts
# libass9: high quality subtitle renderer library (often used by ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    libfontconfig1 \
    libfreetype6 \
    libass9 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for temporary uploads/outputs and ensure it is writeable
RUN mkdir -p temp uploads outputs frames audio && chmod -R 777 temp uploads outputs frames audio

# Expose the port the app runs on
EXPOSE 8000

# Run the application using uvicorn, allowing port override via PORT environment variable
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
