# Backend Test Suite

Unit tests for the DevOps Chatbot backend services.

## Quick Start

### 1. Create Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Tests
```bash
# Run all tests
python run_tests.py

# Or run with pytest directly
pytest tests/ -v
```

## Test Files

- `test_chat_service.py` - ChatService tests
- `test_conversation_service.py` - ConversationService tests  
- `test_mcp_service.py` - MCPWebSearchService tests
- `test_rag_service.py` - RAGService tests
- `test_chatbot_core.py` - DevOpsChatbot tests

## Run Specific Tests

```bash
# Single test file
pytest tests/test_chat_service.py -v

# Single test class
pytest tests/test_chat_service.py::TestChatService -v

# Single test method
pytest tests/test_chat_service.py::TestChatService::test_process_chat_message_success -v
```

## Troubleshooting

If you get permission errors:
```bash
chmod +x run_tests.py
```

If you get module import errors, make sure you're in the `backend` directory and the virtual environment is activated.
