#!/bin/bash

echo "🚀 DevOps Tutor Chatbot Setup"

# Check Docker requirements
if ! command -v docker &> /dev/null || ! command -v docker compose &> /dev/null; then
    echo "❌ Docker and Docker Compose required"
    exit 1
fi

# Build and start
docker compose build
docker compose up -d

echo "✅ Setup complete!"
echo "Frontend: http://localhost:3001"
echo "Backend: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
