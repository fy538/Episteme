#!/bin/bash

# Episteme Setup Script
# This script sets up the local development environment

set -e

echo "🚀 Setting up Episteme development environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️  Please review .env and update any necessary values"
else
    echo "✅ .env already exists"
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run migrations
echo "📦 Running database migrations..."
docker-compose exec -T backend python manage.py migrate

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Create a superuser: docker-compose exec backend python manage.py createsuperuser"
echo "  2. Access the API at: http://localhost:8000"
echo "  3. Access Django admin at: http://localhost:8000/admin"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f backend"
echo "  - Run tests: docker-compose exec backend pytest"
echo "  - Django shell: docker-compose exec backend python manage.py shell"
echo ""
