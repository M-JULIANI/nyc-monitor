# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-root

# Copy the monitor system code
COPY monitor/ ./monitor/

# Create a non-root user for security
RUN useradd -m -u 1000 monitor && \
    chown -R monitor:monitor /app
USER monitor

# Set the entry point to the monitor job
CMD ["python", "-m", "monitor.scheduler.monitor_job"]