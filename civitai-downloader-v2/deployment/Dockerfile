# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r civitai && useradd -r -g civitai -u 1001 civitai

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directories
RUN mkdir -p /app/data /app/logs /app/config /app/downloads /app/temp && \
    chown -R civitai:civitai /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=civitai:civitai . /app/

# Copy configuration files
COPY --chown=civitai:civitai deployment/config/ /app/config/

# Create required directories with proper permissions
RUN mkdir -p /app/data/cache /app/data/models /app/data/database && \
    chmod 755 /app/data /app/logs /app/config /app/downloads && \
    chmod 700 /app/data/database

# Health check script
COPY --chown=civitai:civitai deployment/healthcheck.py /app/healthcheck.py
RUN chmod +x /app/healthcheck.py

# Switch to non-root user
USER civitai

# Expose port for web interface
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py

# Default command
CMD ["python", "-m", "src.main", "--config", "/app/config/app_config.yml"]