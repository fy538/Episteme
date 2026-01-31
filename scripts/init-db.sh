#!/bin/bash

# Initialize database with migrations and seed data

set -e

echo "🔧 Initializing Episteme database..."

# Wait for DB to be ready
echo "⏳ Waiting for database..."
sleep 5

# Create migrations
echo "📝 Creating migrations..."
docker-compose exec -T backend python manage.py makemigrations

# Apply migrations
echo "📦 Applying migrations..."
docker-compose exec -T backend python manage.py migrate

echo ""
echo "✅ Database initialized successfully!"
echo ""
echo "Next: Create a superuser"
echo "  docker-compose exec backend python manage.py createsuperuser"
echo ""
