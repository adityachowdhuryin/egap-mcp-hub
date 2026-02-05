# Use Python 3.11 slim image for smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run uses PORT environment variable (default 8080)
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run uvicorn with production settings
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
