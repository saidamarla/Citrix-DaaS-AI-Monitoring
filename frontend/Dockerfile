FROM python:3.11-slim

WORKDIR /app

# Copy the frontend files
COPY frontend/ .

# Expose port
EXPOSE 3000

# Install curl for health check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/index.html || exit 1

# Serve with Python's simple HTTP server
CMD ["python", "-m", "http.server", "3000"]
