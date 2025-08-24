# DevOps Learning Chatbot

A conversational AI assistant for learning DevOps topics, powered by LangChain/LangGraph with RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol) integration.

## Features

- 🤖 **AI-Powered Learning**: Interactive chatbot specialized in DevOps topics
- 📚 **RAG Integration**: Retrieval-Augmented Generation for accurate, context-aware responses
- 🔍 **Web Search Integration**: Local web search powered by web-search-mcp server (no API key required)
- 💬 **Conversation History**: Persistent chat history with session management
- 🎯 **Topic Focus**: Stays on-topic and prevents unrelated conversations
- 🎨 **Modern UI**: Beautiful chat interface inspired by AI assistants like Claude
- 🐳 **Fully Dockerized**: Easy deployment with Docker Compose

## Supported Topics

- Kubernetes (K8s)
- Docker & Containerization
- CI/CD Pipelines
- AWS CLI & Services
- Google Cloud (gcloud)
- Terraform (Infrastructure as Code)
- Ansible (Configuration Management)
- Monitoring (Prometheus, Grafana)
- And more DevOps topics!

## Prerequisites

- Docker and Docker Compose
- OpenAI API Key (for the LLM)
- (Optional) LangChain API Key for tracing

## Quick Start

1. **Clone the repository**
   ```bash
   cd /path/to/devops-chatbot
   ```

2. **Set up environment variables**
   ```bash
   # Create .env file with the following variables:
   # OPENAI_API_KEY=your_openai_api_key_here
   # POSTGRES_PASSWORD=your_secure_password_here
   # SECRET_KEY=your_super_secure_secret_key_here
   # LESSON_SIZE=medium  # Options: brief, medium, detailed, comprehensive
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Seed the database with DevOps content** (optional but recommended)
   ```bash
   docker-compose exec backend python seed_data.py
   ```

5. **Access the application**
   - Frontend: http://localhost:3001
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Architecture

### Backend (FastAPI + LangChain)
- **FastAPI**: RESTful API framework
- **LangChain/LangGraph**: Orchestrates the conversational flow
- **PostgreSQL + pgvector**: Vector database for RAG
- **OpenAI Embeddings**: For semantic search
- **Async architecture**: High-performance async operations

### Frontend (Vue.js)
- **Vue 3**: Composition API
- **Tailwind CSS**: Utility-first styling
- **Marked.js**: Markdown rendering
- **Highlight.js**: Code syntax highlighting

### Database Schema
- **conversations**: Stores conversation metadata
- **messages**: Chat message history
- **documents**: RAG knowledge base with vector embeddings

## How It Works

1. **Topic Extraction**: When a user starts a conversation, the system extracts the DevOps topic
2. **RAG Search**: First searches the local knowledge base using vector similarity
3. **Web Search Enhancement**: Performs multi-engine web search for comprehensive, up-to-date information
4. **Response Generation**: Combines context from RAG/web search to generate educational responses
5. **Topic Validation**: Ensures conversations stay focused on the initial DevOps topic

## API Endpoints

### Chat Endpoints
- `POST /api/chat/send` - Send a message to the chatbot
- `GET /api/chat/messages/{conversation_id}` - Get messages for a conversation

### Conversation Endpoints
- `GET /api/conversations/` - List user conversations
- `GET /api/conversations/{conversation_id}` - Get conversation details
- `DELETE /api/conversations/{conversation_id}` - Delete a conversation

## Configuration

### Environment Variables

```env
# PostgreSQL
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=chatbot123
POSTGRES_DB=devops_chatbot

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# LangChain (optional)
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=devops-chatbot

# Frontend
VITE_API_URL=http://localhost:8000
```

## Development

### Running Locally (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Adding DevOps Content

Edit `backend/seed_data.py` to add more DevOps topics and content to the RAG knowledge base.

## Web Search Integration

The chatbot integrates with web-search-mcp server through the MCP (Model Context Protocol) for enhanced web search capabilities. This provides:

- **Multi-Engine Search**: Automatically tries Bing, Brave, and DuckDuckGo for best results
- **Full Content Extraction**: Fetches and extracts complete page content from search results
- **No API Key Required**: Works with direct connections to search engines
- **Smart Fallbacks**: Automatically switches between browser and HTTP requests for reliability
- **Concurrent Processing**: Extracts content from multiple pages simultaneously

### Available Search Tools

1. **Full Web Search**: Comprehensive search with content extraction
2. **Search Summaries**: Lightweight search returning only snippets
3. **Page Content Extraction**: Extract content from specific URLs

The web-search-mcp server runs automatically as part of the Docker Compose stack with Playwright browsers for reliable content extraction.

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

### API Connection Issues
- Verify backend is running: `docker-compose logs backend`
- Check CORS settings if accessing from a different domain

### Frontend Build Issues
- Clear node_modules: `docker-compose down && docker-compose up --build`

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
