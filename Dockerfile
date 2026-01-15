# Use official Python runtime
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# build-essential: for compiling some python packages
# curl: for health checks or downloading files
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for cache efficiency)
COPY requirements.txt .

# Install dependencies (upgrade pip first)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for data (LanceDB) & set permissions
RUN mkdir -p /app/data && chmod 777 /app/data
RUN mkdir -p /app/instance && chmod 777 /app/instance

# Environment Variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose the port used by Hugging Face Spaces
EXPOSE 7860

# Run seed.py to initialize DB, then start Gunicorn
CMD python seed.py && gunicorn app:app --bind 0.0.0.0:7860 --timeout 120 --workers 2
