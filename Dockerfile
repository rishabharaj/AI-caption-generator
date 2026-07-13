# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables for fast startup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# Disable pip version check for faster installs
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
# Reduce Python startup time
ENV PYTHONOPTIMIZE=2
# Limit OpenMP threads for low-resource containers
ENV OMP_NUM_THREADS=2
ENV MKL_NUM_THREADS=2

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# ffmpeg: required for video and audio processing, frame extraction, and caption burning
# fontconfig & libfontconfig1 & libfreetype6: required for FFmpeg's drawtext filter to render fonts
# libass9: high quality subtitle renderer library (often used by ffmpeg)
# curl: required for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    libfontconfig1 \
    libfreetype6 \
    libass9 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for temporary uploads/outputs and ensure it is writeable
RUN mkdir -p temp uploads outputs frames audio && chmod -R 777 temp uploads outputs frames audio

# Expose the port the app runs on
EXPOSE 8000

# HEALTHCHECK so Docker/automation knows when the app is ready
# Checks every 5s, gives 3s timeout per check, starts after 5s, fails after 3 retries
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application using uvicorn with fast startup settings
# --timeout-keep-alive 5: reduce keep-alive for faster recycling
# --limit-max-requests 1000: recycle workers to prevent memory leaks
# --timeout-graceful-shutdown 5: shut down quickly
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --timeout-keep-alive 5 --limit-max-requests 1000 --timeout-graceful-shutdown 5
