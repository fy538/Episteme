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
COPY backend/requirements/production.txt /app/requirements/production.txt

# Use production requirements for deployments
# (Can override with docker-compose for local dev)
ARG REQUIREMENTS_FILE=production.txt
RUN pip install --no-cache-dir -r requirements/${REQUIREMENTS_FILE}

# Copy application code
COPY backend /app/

# Create non-root user
RUN useradd -m -u 1000 episteme && chown -R episteme:episteme /app
USER episteme

# Expose port
EXPOSE 8000

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Default command for production (gunicorn)
# docker-compose overrides this with runserver for dev
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
