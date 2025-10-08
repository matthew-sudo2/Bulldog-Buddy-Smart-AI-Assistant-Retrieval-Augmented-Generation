# Bulldog Buddy - AI Coding Assistant Instructions

## Project Overview
University chatbot system with RAG (Retrieval Augmented Generation) combining Python/Streamlit backend, React/Express frontend, and PostgreSQL + pgvector + ChromaDB for knowledge retrieval. Provides both university-specific (handbook) and general knowledge responses with ChatGPT-like conversation memory.

## Architecture - Multi-Service Design

**Three-tier architecture:**
1. **Python Backend** (Streamlit on port 8501/8503): Core AI/RAG system
2. **API Bridge** (FastAPI on port 8001): Connects frontend to backend services
3. **Node.js Frontend** (Express on port 3000): User interface and authentication

**Database split:**
- PostgreSQL: User accounts, conversation history, user context, settings
- ChromaDB: Vector embeddings for handbook knowledge retrieval
- Migration from MongoDB completed (see `MONGODB_TO_POSTGRESQL_MIGRATION.md`)

## Critical Startup Patterns

**Multi-service startup** - Use `start_all.bat` (Windows) or `start_system.py`:
```bash
# Starts all three services with proper sequencing
start_all.bat
```

**Individual services** (for development):
```powershell
# API Bridge (required for frontend-backend communication)
.\.venv\Scripts\python.exe -m uvicorn api.bridge_server:app --host 127.0.0.1 --port 8001

# Frontend (Express)
cd frontend; node server.js

# Streamlit (optional, for direct UI access)
.\.venv\Scripts\streamlit.exe run core/ui.py
```

**Required AI models** (must be installed via Ollama):
```bash
ollama pull gemma3:latest
ollama pull llama3.2:latest
ollama pull embeddinggemma:latest
```

## Core Components & Their Roles

### `models/enhanced_rag_system.py` - AI Brain
- **Dual-mode operation**: University handbook queries vs. general knowledge
- **Model switching**: Matt 3 (`gemma3:latest`) or Matt 3.2 (`llama3.2:latest`) selectable at runtime
- **10-message conversation memory** via LangChain's `ConversationBufferWindowMemory`
- **Web scraping integration**: Can temporarily ingest external URLs into vector store
- Key method: `query()` - routes questions to appropriate model based on classification

### `core/database.py` - BulldogBuddyDatabase
- **PostgreSQL + pgvector** for semantic search
- **Connection pooling**: `ThreadedConnectionPool` (max 10 + 20 overflow)
- Environment vars: `DATABASE_URL`, `PGVECTOR_DIMENSION=768`
- Manages users, conversations, messages, user_context, settings tables
- Vector operations use cosine similarity: `1 - (embedding <=> query_vector::vector)`

### `core/conversation_history.py` - ConversationHistoryManager
- **Session-based conversations**: Each chat has unique UUID
- **Message embeddings**: Uses `all-MiniLM-L6-v2` for semantic conversation search
- **Auto-summarization**: Generates titles from first messages
- Methods: `create_conversation_session()`, `add_message()`, `get_conversation_history()`

### `core/user_context.py` - UserContextManager
- **ChatGPT-like memory**: Extracts and stores user info (name, major, interests) from conversations
- **Regex pattern matching**: Automatically detects personal details in messages
- **Context injection**: Adds user info to prompts for personalized responses
- Stores in `user_context` table with confidence scores

### `core/settings.py` - User Personalization
- Profile icons (18 emoji options), color themes (6 presets)
- Model preferences (temperature, personality modifiers)
- Functions: `get_user_settings()`, `save_user_settings()`, `get_personality_prompt_modifier()`

### `api/bridge_server_enhanced.py` - FastAPI Bridge
- **Streaming responses**: `/api/chat/stream` endpoint for real-time AI output
- **Session management**: Maintains conversation continuity between frontend/backend
- **CORS enabled**: Allows localhost:3000 frontend connections
- Key endpoints: `/api/chat`, `/api/history`, `/api/user-context`, `/api/settings`

### `frontend/server.js` - Express Authentication
- **PostgreSQL user authentication** (bcrypt password hashing)
- **Google OAuth 2.0 integration**
- **Session persistence**: express-session with secure cookies
- User model in `frontend/database.js` uses raw `pg` queries, not ORM

## Development Conventions

### Path Resolution Pattern
All Python modules use project root path resolution:
```python
from pathlib import Path
project_root = Path(__file__).parent.parent  # Adjust depth as needed
sys.path.insert(0, str(project_root))
```

### Import Hierarchy
- `core/` modules: Use relative imports (`.database`, `.auth`)
- `models/`: Import from `core` package (`from core.user_context import...`)
- `scripts/`: Import from `core` package for database operations
- Frontend: CommonJS `require()` for Node modules

### Database Access Pattern
Always use context managers with connection return:
```python
conn = self.db.get_connection()
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        result = cur.fetchall()
    conn.commit()
finally:
    self.db.return_connection(conn)
```

### Error Handling in RAG System
- University mode toggle: `rag_system.university_mode_enabled` (boolean)
- Fallback responses: Always provide "Woof! I'll try my best..." when uncertain
- Streaming must catch exceptions and yield error messages to avoid breaking UI

## Testing & Debugging

**Test scripts:**
- `test_registration.py`: Tests API bridge endpoints (registration, login, health)
- `api/test_bridge.py`: Async test for chat streaming
- `check_system.py`: Validates database connections and service status

**Database inspection:**
```powershell
# Connect via psql or use scripts
.\.venv\Scripts\python.exe scripts/check_user_consistency.py
```

**Common issues:**
1. **"Connection refused" on API bridge**: Ensure uvicorn started on port 8001
2. **"pgvector extension not found"**: Run `CREATE EXTENSION vector;` in PostgreSQL
3. **Ollama model errors**: Verify models pulled: `ollama list`

## Data Flow - Chat Request

1. Frontend sends POST to `http://127.0.0.1:8001/api/chat` with `{message, userId, conversationId}`
2. Bridge server (`api/bridge_server_enhanced.py`) loads user context + conversation history
3. Calls `EnhancedRAGSystem.query()` with personalized prompt
4. RAG system:
   - Classifies query (university vs. general)
   - Retrieves from ChromaDB if university query
   - Generates response via Ollama (gemma3/llama3.2)
   - Maintains 10-message window memory
5. Bridge saves message to PostgreSQL conversation_messages
6. Streams response back to frontend

## Environment Configuration

Required `.env` variables:
```ini
DATABASE_URL=postgresql://postgres:password@localhost:5432/bulldog_buddy
PGVECTOR_DIMENSION=768  # Must match embedding model output
DB_POOL_SIZE=10
API_BRIDGE_PORT=8001
GOOGLE_CLIENT_ID=...  # For OAuth
```

## Key Design Decisions

- **Why dual database (PostgreSQL + ChromaDB)?** PostgreSQL for relational data, ChromaDB optimized for vector similarity search in RAG pipeline
- **Why three servers?** Separation of concerns: Streamlit for rapid UI prototyping, FastAPI for production API, Express for frontend flexibility
- **Why model switching?** Different users prefer different LLM behaviors (Matt 3 vs. Matt 3.2 reasoning styles)
- **10-message memory limit:** Balances context window size vs. token costs and response latency

## When Modifying...

**Adding new AI models:** Update `AVAILABLE_MODELS` dict in `enhanced_rag_system.py`, ensure Ollama has model pulled
**Database schema changes:** Create migration script in `scripts/`, update `infrastructure/init.sql`
**New API endpoints:** Add to `api/bridge_server_enhanced.py` + update frontend fetch calls in `frontend/public/*.html`
**Authentication changes:** Coordinate `frontend/database.js` (PostgreSQL schema) + `frontend/server.js` (session logic)

## Documentation Reference

- `docs/README.md`: User-facing features and installation
- `PROJECT_STRUCTURE.md`: Directory organization
- `MODELS_INTEGRATION.md`: LangChain + Ollama setup details
- `INTEGRATION_PLAN.md`: Frontend-backend connection architecture
