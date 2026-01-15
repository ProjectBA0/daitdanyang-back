# Use official Python runtime
FROM python:3.10-slim

# Create a non-root user (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install system dependencies (Root required for apt)
USER root
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
USER user

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Create needed directories
RUN mkdir -p $HOME/app/data && mkdir -p $HOME/app/instance

# Expose port
EXPOSE 7860

# Run server only (DB is loaded from HF Dataset by engine.py)
CMD gunicorn app:app --bind 0.0.0.0:7860 --timeout 120 --workers 2