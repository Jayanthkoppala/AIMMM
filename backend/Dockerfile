FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Upgrade pip and setuptools for better dependency resolution
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (only backend files)
COPY backend/app/ ./app/

# Expose port (Railway/Render will set PORT env var)
EXPOSE 8000

# Health check (using curl which is available in the image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command (PORT env var will be set by hosting platform)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

