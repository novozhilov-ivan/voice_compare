FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ backend/
COPY static/ static/
COPY data/ data/
COPY run.py .

# Create necessary directories
RUN mkdir -p data/videos data/audio data/models

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "run.py"]
