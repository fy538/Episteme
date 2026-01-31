FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements/base.txt /app/requirements/base.txt
COPY backend/requirements/development.txt /app/requirements/development.txt
RUN pip install --no-cache-dir -r requirements/development.txt

# Copy application code
COPY backend /app/

# Create non-root user
RUN useradd -m -u 1000 episteme && chown -R episteme:episteme /app
USER episteme

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
