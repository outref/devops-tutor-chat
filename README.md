# DevOps Chatbot - AI Learning Assistant

An intelligent chatbot system for Programming, DevOps, and AI education using **LangGraph**, **RAG search**, **MCP web search**, and interactive **quiz generation**.

## Architecture Overview

### LangGraph Workflow Engine
The chatbot uses **LangGraph** to orchestrate a sophisticated conversation flow:

```python
# Core workflow nodes
topic_extraction → topic_category_validation → rag_search → web_search → generate_lesson
                                            ↓
                        quiz_generation → process_quiz_answer
```

**Key Graph Nodes:**
- **Topic Extraction**: Identifies conversation topics using LLM
- **Topic Validation**: Ensures queries are within Programming/DevOps/AI domains  
- **RAG Search**: Vector similarity search against knowledge base
- **Web Search**: MCP-powered real-time web search fallback
- **Quiz Generation**: Creates personalized quizzes from conversation history
- **Content Generation**: Structured lesson creation and response generation

**State Management:**
- Persistent conversation state with `MemorySaver`
- Quiz progress tracking across sessions
- Used question tracking to prevent repetition

### RAG (Retrieval-Augmented Generation)

**Vector Database Setup:**
- **pgvector** extension on PostgreSQL for vector operations
- **OpenAI embeddings** (1536 dimensions) for semantic search
- **Similarity threshold**: 0.7 for high-quality results only

**Search Process:**
1. Query preprocessing and concept extraction using LLM
2. Vector similarity search with cosine distance
3. Quality filtering based on similarity scores
4. Fallback to web search if insufficient results

```python
# Semantic search with quality threshold
results = await rag_service.search(
    query, 
    similarity_threshold=0.7,
    limit=5
)
```

### MCP Web Search Integration

**Model Context Protocol (MCP)** implementation for real-time web search:

**Architecture:**
- Standalone **web-search-mcp** service with Playwright
- HTTP wrapper for JSON-RPC 2.0 communication
- Dockerized with browser dependencies (Chromium/Firefox)

**Web Search Flow:**
1. RAG search quality assessment
2. Trigger web search if RAG results insufficient  
3. MCP service processes search queries
4. Content extraction and relevance filtering
5. Integration with conversation context

### Quiz Generation System

**Smart Quiz Features:**
- **Dynamic Question Generation**: Creates questions from conversation history
- **Question Type Variety**: Multiple choice, true/false, short answer
- **Duplicate Prevention**: Tracks used questions across sessions
- **Progress Tracking**: Scores and feedback system
- **Adaptive Difficulty**: Questions based on discussed concepts

**Quiz Workflow:**
1. Analyze conversation history and extract key concepts
2. Generate 5 diverse questions using conversation context
3. Track question usage to avoid repetition
4. Process answers with detailed feedback
5. Provide completion scores and learning suggestions

```python
# Quiz state tracking
quiz_state = {
    "quiz_questions": [...],
    "current_quiz_index": 0,
    "quiz_scores": [...], 
    "used_quiz_questions": [...]  # Prevents repetition
}
```

## Technology Stack

**Backend:**
- **FastAPI** with async/await patterns
- **LangChain** + **LangGraph** for AI workflow orchestration
- **OpenAI GPT-4.1-mini** for language processing
- **PostgreSQL** + **pgvector** for vector search
- **SQLAlchemy 2.0** with async support

**Frontend:**  
- **Vue 3** with Composition API
- **TailwindCSS** for styling
- **WebSocket** support for real-time chat

**Infrastructure:**
- **Docker Compose** multi-service setup
- **MCP Server** for web search capabilities
- **RAG Data Seeding** tools with CSV import

## Quick Start

```bash
# Clone and setup environment
cp .env-example .env

# Start all services
docker compose up --build

# Seed RAG database (optional)
docker compose exec backend bash -c "cd /app/rag-data && ./seed_rag.sh"
```

**Services:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000  
- MCP Web Search: http://localhost:3000

## Key Features

✅ **Contextual Learning** - RAG-powered knowledge retrieval  
✅ **Real-time Web Search** - MCP integration for current information  
✅ **Interactive Quizzes** - Personalized question generation  
✅ **Graph-based Workflow** - LangGraph state management  
✅ **Topic Validation** - Programming/DevOps/AI focus  
✅ **Conversation Memory** - Persistent chat sessions  
✅ **Quality Filtering** - Similarity thresholds for relevant results

## Development

**Run Tests:**
```bash
docker compose exec backend python -m pytest
```

**Database Schema:**
- Conversations with topic tracking
- Messages with role-based storage  
- Documents with vector embeddings
- Quiz state persistence

The system combines modern AI techniques with robust engineering practices to create an intelligent, scalable learning assistant.
