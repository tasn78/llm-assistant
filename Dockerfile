# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential sqlite3 && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the data directory for the database and set permissions
RUN mkdir -p /data && chown -R appuser:appuser /data
VOLUME /data

# Copy application source code and all necessary files
COPY --chown=appuser:appuser . .

# Switch to the non-root user
USER appuser

# Pre-download the summarization model
RUN python -c "from transformers import pipeline; pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')"

# Expose the HTTPS port
EXPOSE 443

# Command to run the application directly
CMD ["python3", "app.py"]
