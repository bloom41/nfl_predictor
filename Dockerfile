# NFL Assistant Flask Application Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements_flask.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_flask.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data_cache models templates

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PORT=5000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1

# Create non-root user
RUN useradd -r -s /bin/false nfluser && \
    chown -R nfluser:nfluser /app

USER nfluser

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]