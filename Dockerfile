FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install system dependencies (FFmpeg and build tools for optional webrtcvad)
RUN : \
    && apt-get update \
        --quiet \
    && apt-get install \
        --quiet \
        --no-install-recommends \
        --assume-yes \
            curl \
            ffmpeg \
            build-essential \
            gcc \
            g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    :

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies (cached layer)
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend /app/backend
COPY static /app/static
COPY run.py /app/

# Create necessary directories
RUN mkdir -p data/videos data/audio data/models

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "run.py"]
