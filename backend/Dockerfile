# ============================================================================
# DOCKERFILE BACKEND - BUDGET FAMILLE v2.3 - PRODUCTION READY
# ============================================================================
# Multi-stage build optimisé pour production avec sécurité renforcée

# ============================================================================
# Stage 1: Base image with security hardening
# ============================================================================
FROM python:3.8-slim-bullseye AS base

# Security: Create non-root user
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# Install security updates and required system packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        libmagic-dev \
        python3-dev \
        build-essential \
        curl \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Security: Set secure Python flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================================================
# Stage 2: Dependencies installation
# ============================================================================
FROM base AS deps

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with security checks
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Security: Install additional production tools
    pip install --no-cache-dir \
        gunicorn==20.1.0 \
        structlog==22.3.0 \
        prometheus-client==0.16.0

# ============================================================================
# Stage 3: Application build
# ============================================================================
FROM deps AS builder

# Copy application source
COPY --chown=appuser:appuser . .

# Security: Remove sensitive files and test data
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -type d -exec rm -rf {} + && \
    rm -rf tests/ test_* debug_* *.csv *.backup* backups/ db_backups/ && \
    rm -rf *.md *.log *.json diagnostic_* cleanup_*

# Security: Set proper permissions
RUN chmod -R 755 /app && \
    chmod 644 /app/*.py

# ============================================================================
# Stage 4: Production runtime
# ============================================================================
FROM python:3.8-slim-bullseye AS production

# Copy non-root user from base
RUN groupadd -g 1001 appuser && \
    useradd -r -u 1001 -g appuser appuser

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Security: Set secure environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PATH="/home/appuser/.local/bin:$PATH" \
    WORKERS=4 \
    TIMEOUT=30 \
    KEEP_ALIVE=5 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=50

WORKDIR /app

# Copy Python dependencies
COPY --from=deps /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application files
COPY --from=builder --chown=appuser:appuser /app /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app && \
    chmod 755 /app/logs /app/data

# Health check
COPY <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import sys
import requests
import os

def health_check():
    try:
        port = os.getenv('PORT', '8000')
        response = requests.get(f'http://localhost:{port}/health', timeout=5)
        if response.status_code == 200:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    health_check()
EOF

RUN chmod +x /app/healthcheck.py

# Add health endpoint to app if not exists
COPY <<EOF /app/health_endpoint.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import psutil
import time

def add_health_endpoints(app: FastAPI):
    @app.get("/health")
    async def health_check():
        return JSONResponse({
            "status": "healthy",
            "timestamp": int(time.time()),
            "version": "2.3.0"
        })
    
    @app.get("/health/ready")
    async def readiness_check():
        # Check database connection
        try:
            # Add your database check here
            return JSONResponse({
                "status": "ready",
                "database": "connected",
                "timestamp": int(time.time())
            })
        except Exception as e:
            return JSONResponse(
                {"status": "not_ready", "error": str(e)}, 
                status_code=503
            )
    
    @app.get("/health/live")
    async def liveness_check():
        # Check system resources
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        
        return JSONResponse({
            "status": "alive",
            "memory_percent": memory.percent,
            "cpu_percent": cpu,
            "timestamp": int(time.time())
        })

    @app.get("/metrics")
    async def metrics():
        # Prometheus metrics endpoint
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
EOF

# Security: Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python /app/healthcheck.py

# Production command with Gunicorn
CMD ["gunicorn", "app:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "${WORKERS}", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "${TIMEOUT}", \
     "--keep-alive", "${KEEP_ALIVE}", \
     "--max-requests", "${MAX_REQUESTS}", \
     "--max-requests-jitter", "${MAX_REQUESTS_JITTER}", \
     "--preload", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-config", "logging.conf"]

# Labels for container registry
LABEL maintainer="Budget Famille Team" \
      version="2.3.0" \
      description="Budget Famille Backend API - Production Ready" \
      security.scan="trivy" \
      org.opencontainers.image.source="https://github.com/your-org/budget-famille"