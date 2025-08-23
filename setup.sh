#!/bin/bash

# DevOps Chatbot Setup Script

echo "🚀 DevOps Chatbot Setup"
echo "======================"
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OpenAI API key"
    echo "   Run: nano .env"
    echo
fi

# Build and start containers
echo "🏗️  Building Docker containers..."
docker-compose build

echo
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    
    # Seed the database
    echo
    echo "🌱 Seeding database with DevOps content..."
    docker-compose exec backend python seed_data.py
    
    echo
    echo "🎉 Setup complete!"
    echo
    echo "📱 Access the application at:"
    echo "   Frontend: http://localhost:3001"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo
    echo "💡 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
else
    echo "❌ Failed to start services. Check the logs:"
    echo "   docker-compose logs"
    exit 1
fi
