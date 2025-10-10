# Bulldog Buddy - Project Structure

## 📁 Directory Structure

```
Paw-sitive AI/
├── .env                        # Environment configuration (DO NOT COMMIT)
├── .env.example                # Environment template (safe to commit)
├── start.py                    # Main system launcher
├── stop.py                     # System shutdown utility
├── core/                       # Core application modules
│   ├── __init__.py
│   ├── auth.py                # Authentication system
│   ├── conversation_history.py # Conversation management
│   ├── database.py            # PostgreSQL + pgvector operations
│   ├── settings.py            # User settings management
│   ├── ui.py                  # Streamlit UI (optional)
│   └── user_context.py        # User context/memory management
├── models/                     # AI/ML models and systems
│   ├── __init__.py
│   ├── enhanced_rag_system.py # Main RAG implementation
│   └── web_scraper.py         # Web scraping utilities
├── api/                        # API Bridge Layer
│   └── bridge_server_enhanced.py # FastAPI bridge (port 8001)
├── frontend/                   # Express Frontend
│   ├── server.js              # Express server (port 3000)
│   ├── database.js            # PostgreSQL user model
│   ├── package.json           # Node dependencies
│   └── public/
│       ├── index.html         # Landing page
│       ├── login.html         # Login page
│       ├── username.html      # Registration page
│       └── main-redesigned.html # Main chat interface
├── data/                       # Data files
│   └── student-handbook-structured.csv
├── infrastructure/             # Deployment and configuration
│   ├── docker-compose.yml     # PostgreSQL + pgAdmin containers
│   ├── init.sql               # Database schema initialization
│   └── requirements.txt       # Python dependencies
├── scripts/                    # Utility and maintenance scripts
│   ├── migrations/            # Database migration scripts
│   │   ├── README.md         # Migration documentation
│   │   ├── add_settings_columns.sql # Add settings columns
│   │   ├── add_profile_icon.py      # Add profile icon column
│   │   └── apply_settings_migration.py # Execute migrations
│   ├── add_personalization_columns.py
│   ├── check_user_consistency.py
│   ├── cleanup_duplicates.py
│   ├── migrate_google_oauth.py
│   └── upgrade_database.py
├── docs/                       # Documentation
│   ├── README.md              # Main documentation
│   ├── setup.md               # Setup instructions
│   └── PGADMIN_CONNECTION_GUIDE.md
└── enhanced_chroma_db/         # Vector database storage (DO NOT COMMIT)
    ├── chroma.sqlite3
    └── 6b8762dd-caa7-4075-a25e-94ace6324e2c/
```

## 🚀 Usage

```bash
# Start the complete system (Frontend + API Bridge + Database)
python start.py

# Or use Windows batch file
start_all.bat

# Stop the system
python stop.py

# Access the application
# Frontend: http://localhost:3000
# API Health: http://localhost:8001/api/health
# API Docs: http://localhost:8001/docs
```

## 🔧 Database Migrations

Located in `scripts/migrations/`:

```bash
# Run all settings migrations
python scripts/migrations/apply_settings_migration.py

# Add profile icon column only
python scripts/migrations/add_profile_icon.py

# See migrations/README.md for more details
```

## ✅ Import Structure

- `core/` modules use relative imports (`.database`, `.auth`, etc.)
- `models/` imports from `core` package (`core.user_context`)
- `scripts/` imports from `core` package (`core.database`, `core.conversation_history`)
- File paths automatically resolve to project root regardless of execution location