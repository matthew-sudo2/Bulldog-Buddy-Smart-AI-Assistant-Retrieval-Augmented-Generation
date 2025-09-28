# Bulldog Buddy - Project Structure

## 📁 Or## 🚀 Usage

```bash
# Method 1: Use the main app launcher (recommended)
python app.py

# Method 2: Run streamlit directly
.\.venv\Scripts\streamlit.exe run core/ui.py

# Method 3: If streamlit is in PATH
streamlit run core/ui.py
```irectory Structure

```
Paw-sitive AI/
├── app.py                      # Main application entry point
├── core/                       # Core application modules
│   ├── __init__.py
│   ├── auth.py                # Authentication system
│   ├── conversation_history.py # Conversation management
│   ├── database.py            # Database operations
│   ├── settings.py            # User settings management
│   ├── ui.py                  # Main Streamlit UI
│   └── user_context.py        # User context management
├── models/                     # AI/ML models and systems
│   ├── __init__.py
│   ├── enhanced_rag_system.py # Main RAG implementation
│   └── web_scraper.py         # Web scraping utilities
├── data/                       # Data files
│   └── student-handbook-structured.csv
├── infrastructure/             # Deployment and configuration
│   ├── docker-compose.yml     # Docker services
│   ├── init.sql               # Database initialization
│   └── requirements.txt       # Python dependencies
├── scripts/                    # Utility and maintenance scripts
│   ├── add_personalization_columns.py
│   ├── check_user_consistency.py
│   ├── cleanup_duplicates.py
│   └── upgrade_database.py
├── docs/                       # Documentation
│   ├── README.md              # Main documentation
│   ├── setup.md               # Setup instructions
│   └── PGADMIN_CONNECTION_GUIDE.md
└── enhanced_chroma_db/         # Vector database storage
    ├── chroma.sqlite3
    └── 6b8762dd-caa7-4075-a25e-94ace6324e2c/
```

## 🚀 Key Features

- **Conversational RAG**: Enhanced AI assistant with follow-up detection and context maintenance
- **Clean Architecture**: Organized into logical directories for maintainability
- **Proper Imports**: All modules use relative imports within their packages
- **Main Entry Point**: `app.py` serves as the application launcher
- **Path Resolution**: Automatic path resolution for cross-directory file access

## 🔧 Usage

```bash
# Run the application
python app.py

# Or directly with streamlit
streamlit run core/ui.py
```

## ✅ Import Structure

- `core/` modules use relative imports (`.database`, `.auth`, etc.)
- `models/` imports from `core` package (`core.user_context`)
- `scripts/` imports from `core` package (`core.database`, `core.conversation_history`)
- File paths automatically resolve to project root regardless of execution location