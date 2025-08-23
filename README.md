# DevOps Learning Chatbot

A conversational AI assistant for learning DevOps topics, powered by LangChain/LangGraph with RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol) integration.

## Features

- 🤖 **AI-Powered Learning**: Interactive chatbot specialized in DevOps topics
- 📚 **RAG Integration**: Retrieval-Augmented Generation for accurate, context-aware responses
- 🔍 **MCP Web Search**: Falls back to web search when local knowledge is insufficient
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
- (Optional) MCP Web Search server

## Quick Start

1. **Clone the repository**
   ```bash
   cd /path/to/devops-chatbot
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
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
3. **Web Search Fallback**: If local knowledge is insufficient, queries the MCP web search server
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

# MCP Web Search
MCP_WEB_SEARCH_URL=http://localhost:3000

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

## MCP Integration

The chatbot can integrate with MCP (Model Context Protocol) servers for enhanced web search capabilities. If the MCP server is not available, it falls back to predefined DevOps content.

To set up an MCP web search server:
1. Deploy an MCP-compatible web search server
2. Update `MCP_WEB_SEARCH_URL` in your `.env` file

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
