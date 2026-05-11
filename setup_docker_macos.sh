#!/bin/bash

# Setup script for running PWA Map application with Docker on macOS

echo "🔍 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop for Mac from:"
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

echo "✅ Docker found: $(docker --version)"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
fi

echo "✅ Docker Compose found"

echo ""
echo "📁 Checking if workspace directory is accessible to Docker..."
echo "   Current directory: $(pwd)"
echo "   Directory contents:"
ls -la

echo ""
echo "🔧 Testing Docker file access..."
docker run --rm -v "$(pwd)":/test alpine ls -la /test/backend/Dockerfile 2>&1
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  WARNING: Docker cannot access files in this directory!"
    echo ""
    echo "To fix this on macOS:"
    echo "1. Open Docker Desktop"
    echo "2. Go to Settings (⚙️) → Resources → File Sharing"
    echo "3. Add your workspace directory: $(pwd)"
    echo "4. Click 'Apply & Restart'"
    echo ""
    echo "Alternatively, move this project to a shared location like:"
    echo "   - ~/Documents/"
    echo "   - ~/Projects/"
    echo "   - /Users/yourusername/"
    exit 1
fi

echo "✅ Docker can access files successfully"

echo ""
echo "🚀 Starting application with Docker Compose..."

# Use 'docker compose' (v2) or fallback to 'docker-compose' (v1)
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --build
else
    docker compose up -d --build
fi

echo ""
echo "✅ Application started!"
echo ""
echo "📍 Access points:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   Database: localhost:5432"
echo ""
echo "📊 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Stop application:"
echo "   docker compose down"
