# 🐕 Bulldog Buddy - AI University Assistant

> **Smart AI chatbot with RAG (Retrieval Augmented Generation) for university students**  
> Powered by Matt 3 & Matt 3.2 models with intelligent handbook knowledge retrieval

---

## 📋 Table of Contents

- [Demo Screenshots](#-demo-screenshots)
- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Troubleshooting](#-troubleshooting)
- [Documentation](#-documentation)

---

## 📸 Demo Screenshots

<div align="center">

### Landing Page
<img src="frontend/src/assets/images/Landing-page.PNG" alt="Bulldog Buddy Landing Page" width="800"/>

*Welcome to Bulldog Buddy - Your Smart Campus Assistant*

---

### User Authentication

<table>
<tr>
<td width="50%">
<img src="frontend/src/assets/images/Login-page.PNG" alt="Login Page" width="100%"/>
<p align="center"><b>Login Page</b><br/>Secure authentication with Google OAuth support</p>
</td>
<td width="50%">
<img src="frontend/src/assets/images/Register-page.PNG" alt="Register Page" width="100%"/>
<p align="center"><b>Registration Page</b><br/>Quick and easy account creation</p>
</td>
</tr>
</table>

---

### Main Chat Interface
<img src="frontend/src/assets/images/Chat-interface.PNG" alt="Chat Interface" width="800"/>

*Intelligent AI chat with RAG system, conversation history, and customizable settings*

</div>

---

## ✨ Features

- 🤖 **Dual AI Models**: Choose between Matt 3 and Matt 3.2
- 📚 **RAG System**: Intelligent university handbook knowledge retrieval
- 💬 **Conversation Memory**: Maintains context across 10 messages
- 👤 **User Context**: Remembers user preferences and information
- 🎨 **Modern UI**: Clean, responsive chat interface
- 🔐 **Authentication**: Secure login with Google OAuth support
- 🗄️ **Vector Search**: PostgreSQL + pgvector + ChromaDB for semantic search
- 🌐 **Web Scraping**: Can analyze external URLs for information

---

## � Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

1. **Python 3.8 or higher**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Node.js 16 or higher**
   - Download: https://nodejs.org/
   - Verify: `node --version`

3. **Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop
   - Required for PostgreSQL database
   - Verify: `docker --version`

4. **Ollama** (AI Model Runtime)
   - Download: https://ollama.ai/
   - Required for running AI models
   - Verify: `ollama --version`

### Required AI Models

After installing Ollama, pull the required models:

```bash
ollama pull gemma3:latest
ollama pull llama3.2:latest
ollama pull embeddinggemma:latest
```

---

## 🔧 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/matthew-sudo2/Bulldog-Buddy-Smart-AI-Assistant-Retrieval-Augmented-Generation.git
cd Bulldog-Buddy-Smart-AI-Assistant-Retrieval-Augmented-Generation
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r infrastructure/requirements.txt
```

### Step 3: Set Up Node.js Dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings (optional)
# Default settings work for local development
```

### Step 5: Start PostgreSQL Database

```bash
# Start database using Docker
cd infrastructure
docker-compose up -d
cd ..

# Wait ~10 seconds for database to initialize
```

Verify database is running:
```bash
docker ps
# Should see: bulldog-buddy-db, bulldog-buddy-pgadmin, bulldog-buddy-adminer
```

---

## 🚀 Quick Start

### Start the System

```bash
python start.py
```

This will automatically start:
1. ✅ PostgreSQL database (if not already running)
2. ✅ API Bridge server (port 8001)
3. ✅ Frontend server (port 3000)

### Access the Application

Open your browser and navigate to:
- **Main Application**: http://localhost:3000

### First Time Setup

After starting the system for the first time:
1. Navigate to http://localhost:3000
2. Click "Sign Up" to create your account
3. Or use Google OAuth to sign in

### Stop the System

```bash
python stop.py
```

Then close the PowerShell/Terminal windows that were opened.

---

## ⚙️ Configuration

### Database Access

**PostgreSQL Database:**
- Host: `localhost`
- Port: `5432`
- Database: `bulldog_buddy`
- User: See `.env` file
- Password: See `.env` file

**Database Management Tools:**
- **pgAdmin**: http://localhost:8080
  - Credentials: Check your `.env` file or `docker-compose.yml`
- **Adminer**: http://localhost:8081
  - Use PostgreSQL credentials from `.env`

> ⚠️ **Security Note**: Default credentials are for local development only.  
> For production deployment, change all passwords in `.env` and `docker-compose.yml`.

### API Endpoints

- **API Health Check**: http://127.0.0.1:8001/api/health
- **API Documentation**: http://127.0.0.1:8001/docs
- **Available Models**: http://127.0.0.1:8001/api/models

### Environment Variables

Edit `.env` file to customize:

```ini
# Database Configuration
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/bulldog_buddy
PGVECTOR_DIMENSION=768

# API Bridge
API_BRIDGE_PORT=8001

# Frontend
FRONTEND_PORT=3000

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

> 📝 **Note**: Copy `.env.example` to `.env` and update with your values.

---

## 💡 Usage

### Chat Interface

1. **Select Model**: Choose between Matt 3 or Matt 3.2 from dropdown
2. **Toggle Mode**: Switch between University mode (handbook) and General mode
3. **Ask Questions**: Type your question and press Enter or click Send
4. **View History**: Access previous conversations from the sidebar

### Settings Panel

Click the settings icon to customize:
- 🎨 **Theme**: University, Dark, Light, Mint, Sunset, Ocean
- 🤖 **Personality**: Friendly, Professional, Casual, Academic
- 📏 **Response Length**: Concise, Balanced, Detailed
- 🔧 **Display Options**: Confidence scores, sources, timestamps

### Creating New Account

1. Go to http://localhost:3000
2. Click "Sign Up"
3. Enter your email and create a secure password
4. Set your display name
5. Start chatting!

---

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│   Frontend      │  Express.js (Port 3000)
│   (Node.js)     │  User Interface
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Bridge    │  FastAPI (Port 8001)
│   (Python)      │  Request Handler
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   RAG System    │  LangChain + Ollama
│   (Python)      │  AI Models & Retrieval
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌──────┐  ┌──────┐
│ PG + │  │Chroma│  Vector Storage
│vector│  │  DB  │  Semantic Search
└──────┘  └──────┘
```

### Technologies Used

- **Backend**: Python, FastAPI, LangChain, Ollama
- **Frontend**: Node.js, Express, Vanilla JavaScript
- **Database**: PostgreSQL with pgvector extension
- **Vector DB**: ChromaDB for embeddings
- **AI Models**: Matt 3 (gemma3), Matt 3.2 (llama3.2)
- **Authentication**: bcrypt, Google OAuth 2.0

---

## � Troubleshooting

### Common Issues

**❌ "Docker is not running"**
```bash
# Start Docker Desktop application
# Wait for Docker to fully start
# Then run: python start.py
```

**❌ "Port already in use"**
```bash
# Check what's using the port
netstat -ano | findstr :3000
netstat -ano | findstr :8001

# Kill the process or change ports in .env file
```

**❌ "Ollama models not found"**
```bash
# Pull required models
ollama pull gemma3:latest
ollama pull llama3.2:latest
ollama pull embeddinggemma:latest

# Verify models
ollama list
```

**❌ "Database connection failed"**
```bash
# Restart database
cd infrastructure
docker-compose restart
cd ..

# Check logs
docker logs bulldog-buddy-db
```

**❌ "Module not found" errors**
```bash
# Reinstall Python dependencies
.venv\Scripts\activate
pip install -r infrastructure/requirements.txt --force-reinstall
```

**❌ Frontend not loading**
```bash
# Reinstall Node dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
cd ..
```

### Logs and Debugging

**Check API Bridge logs:**
- Look at the PowerShell window running the API Bridge

**Check Frontend logs:**
- Look at the PowerShell window running the Frontend

**Check Database:**
```bash
docker logs bulldog-buddy-db
```

**Test API Health:**
```bash
curl http://127.0.0.1:8001/api/health
```

---

## 📚 Documentation

For more detailed information, see:

- **Setup Guide**: `docs/setup.md`
- **User Documentation**: `docs/README.md`
- **Developer Guide**: `.github/copilot-instructions.md`

---

## 🤝 Support

For issues or questions:
- Check the [Troubleshooting](#-troubleshooting) section
- Review documentation in `docs/` folder
- Open an issue on GitHub

---

## 📄 License

This project is licensed under the MIT License.

---

## 🎉 Quick Command Reference

```bash
# Start everything
python start.py

# Stop everything
python stop.py

# Check system status
python check_system.py

# Start database only
cd infrastructure && docker-compose up -d

# Stop database
cd infrastructure && docker-compose down

# View database logs
docker logs bulldog-buddy-db

# Restart services (after code changes)
# 1. Close PowerShell windows
# 2. Run: python start.py
```

---

**Made with ❤️ for National University Students**
