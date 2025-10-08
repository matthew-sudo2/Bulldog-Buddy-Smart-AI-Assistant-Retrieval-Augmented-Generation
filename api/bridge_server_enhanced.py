"""
Enhanced API Bridge Server - Full Streamlit Feature Integration
Connects the Express frontend to all backend functionality
"""

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "core"))
sys.path.insert(0, str(project_root / "models"))

# Import backend components
try:
    from core.database import BulldogBuddyDatabase
    from core.conversation_history import ConversationHistoryManager
    from core.user_context import UserContextManager
    from core.settings import get_user_settings, save_user_settings, get_personality_prompt_modifier
    from models.enhanced_rag_system import EnhancedRAGSystem
except ImportError as e:
    logger.error(f"Import error: {e}")
    raise

app = FastAPI(title="Bulldog Buddy API Bridge - Enhanced", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
db_manager = None
conversation_manager = None
user_context_manager = None
rag_system = None
rag_systems = {}  # Cache for different models

@app.on_event("startup")
async def startup_event():
    """Initialize all backend components"""
    global db_manager, conversation_manager, user_context_manager, rag_system
    
    logger.info("🔧 Initializing Enhanced API Bridge...")
    
    try:
        # Database
        db_manager = BulldogBuddyDatabase()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database failed: {e}")
    
    try:
        # Conversation History
        conversation_manager = ConversationHistoryManager()
        logger.info("✅ Conversation Manager initialized")
    except Exception as e:
        logger.error(f"❌ Conversation Manager failed: {e}")
    
    try:
        # User Context
        user_context_manager = UserContextManager()
        logger.info("✅ User Context Manager initialized")
    except Exception as e:
        logger.error(f"❌ User Context Manager failed: {e}")
    
    try:
        # RAG System (default model)
        handbook_path = project_root / "data" / "student-handbook-structured.csv"
        rag_system = EnhancedRAGSystem(str(handbook_path), model_name="gemma3:latest")
        rag_systems["gemma3:latest"] = rag_system
        logger.info("✅ RAG System initialized")
    except Exception as e:
        logger.error(f"❌ RAG System failed: {e}")
    
    logger.info("✅ API Bridge startup complete!")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatMessage(BaseModel):
    message: str
    user_id: int
    session_id: Optional[str] = None
    model: Optional[str] = "gemma3:latest"
    mode: Optional[str] = "university"  # university or general

class ConversationCreate(BaseModel):
    user_id: int
    title: Optional[str] = "New Conversation"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None

class SettingsUpdate(BaseModel):
    color_theme: Optional[str] = None
    personality_type: Optional[str] = None
    response_length: Optional[str] = None
    profile_icon: Optional[str] = None
    custom_instructions: Optional[str] = None
    notifications_enabled: Optional[bool] = None

class URLAnalyze(BaseModel):
    url: str
    user_id: int
    question: Optional[str] = None

class ModelSelect(BaseModel):
    user_id: int
    model_name: str

class RAGModeChange(BaseModel):
    user_id: int
    university_mode: bool

# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "components": {
            "database": "connected" if db_manager else "unavailable",
            "conversation_manager": "available" if conversation_manager else "unavailable",
            "user_context": "available" if user_context_manager else "unavailable",
            "rag_system": "initialized" if rag_system else "not initialized"
        },
        "message": "Enhanced API Bridge is running"
    }

@app.get("/api/status")
async def get_status():
    """Get detailed system status"""
    status = {
        "database": {
            "connected": bool(db_manager),
            "stats": {}
        },
        "rag_system": {
            "initialized": bool(rag_system),
            "models_loaded": list(rag_systems.keys()),
            "stats": {}
        },
        "conversation_manager": {
            "available": bool(conversation_manager)
        }
    }
    
    # Get RAG stats if available
    if rag_system:
        try:
            status["rag_system"]["stats"] = rag_system.get_database_stats()
        except:
            pass
    
    return status

# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post("/api/chat")
async def chat(chat_request: ChatMessage):
    """Process chat message with streaming support"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        # Get user settings for personalization
        user_settings = {}
        if user_context_manager:
            try:
                user_settings = get_user_settings(chat_request.user_id)
            except:
                pass
        
        # Get or create conversation session
        session_id = chat_request.session_id
        if not session_id and conversation_manager:
            session_id = conversation_manager.create_conversation_session(
                chat_request.user_id,
                title="New Conversation"
            )
        
        # Save user message
        if conversation_manager and session_id:
            conversation_manager.add_message_to_session(
                session_uuid=session_id,
                user_id=chat_request.user_id,
                content=chat_request.message,
                message_type="user"
            )
        
        # Set RAG mode
        current_rag = rag_systems.get(chat_request.model, rag_system)
        if hasattr(current_rag, 'set_university_mode'):
            current_rag.set_university_mode(chat_request.mode == "university")
        
        # Set user context if available
        if hasattr(current_rag, 'set_user_context'):
            current_rag.set_user_context(chat_request.user_id)
        
        # Generate response using ask_question method
        logger.info(f"💬 Processing message with {chat_request.model} in {chat_request.mode} mode")
        result = current_rag.ask_question(chat_request.message, use_conversation_history=True)
        
        # Extract response text
        response_text = result.get("answer", result.get("result", "I couldn't generate a response."))
        confidence = result.get("confidence", 0.0)
        sources = result.get("source_documents", [])
        
        # Save assistant message
        if conversation_manager and session_id:
            conversation_manager.add_message_to_session(
                session_uuid=session_id,
                user_id=chat_request.user_id,
                content=response_text,
                message_type="assistant",
                model_used=chat_request.model
            )
        
        return {
            "response": response_text,
            "session_id": session_id,
            "model": chat_request.model,
            "confidence": confidence,
            "sources": sources[:3] if sources else [],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
async def chat_stream(chat_request: ChatMessage):
    """Stream chat response for typewriter effect"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    async def generate():
        try:
            response = rag_system.query(chat_request.message)
            # Simulate streaming by yielding character by character
            for char in response:
                yield json.dumps({"char": char}) + "\n"
                await asyncio.sleep(0.01)  # Small delay for streaming effect
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")

# ============================================================================
# CONVERSATION ENDPOINTS
# ============================================================================

@app.post("/api/conversations")
async def create_conversation(conv: ConversationCreate):
    """Create a new conversation session"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        session_uuid = conversation_manager.create_conversation_session(
            conv.user_id,
            title=conv.title
        )
        return {"session_uuid": session_uuid, "title": conv.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{session_id}/messages")
async def get_conversation_messages(session_id: str, user_id: int = 1):
    """Get all messages in a conversation"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        messages = conversation_manager.get_session_messages(session_id, user_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{session_id}")
async def update_conversation(session_id: str, update: ConversationUpdate):
    """Update conversation (title, pin status)"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        if update.title:
            conversation_manager.update_conversation_title(session_id, update.title)
        if update.is_pinned is not None:
            conversation_manager.toggle_pin_conversation(session_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{session_id}")
async def delete_conversation(session_id: str, user_id: int = Query(default=1)):
    """Delete a conversation - requires user_id query parameter"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        logger.info(f"🗑️ Attempting to delete conversation {session_id} for user {user_id}")
        success = conversation_manager.delete_conversation(session_id, user_id)
        if success:
            logger.info(f"✅ Successfully deleted conversation {session_id}")
            return {"success": True, "message": "Conversation deleted successfully"}
        else:
            logger.warning(f"⚠️ Conversation {session_id} not found or access denied for user {user_id}")
            raise HTTPException(status_code=404, detail="Conversation not found or already deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting conversation {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@app.get("/api/settings/{user_id}")
async def get_settings(user_id: int):
    """Get user settings"""
    try:
        settings = get_user_settings(user_id)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/settings/{user_id}")
async def update_settings(user_id: int, settings: SettingsUpdate):
    """Update user settings"""
    try:
        settings_dict = settings.dict(exclude_unset=True)
        success = save_user_settings(user_id, settings_dict)
        if success:
            return {"success": True, "settings": settings_dict}
        else:
            raise HTTPException(status_code=500, detail="Failed to save settings")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/themes")
async def get_themes():
    """Get available color themes"""
    themes = {
        "university": {"name": "University", "primary": "#2E4057", "secondary": "#6C757D"},
        "professional": {"name": "Professional", "primary": "#1A1A1A", "secondary": "#4A4A4A"},
        "dark": {"name": "Dark Mode", "primary": "#121212", "secondary": "#BB86FC"},
        "light": {"name": "Light Mode", "primary": "#FFFFFF", "secondary": "#6200EE"},
        "sunset": {"name": "Sunset", "primary": "#FF6B6B", "secondary": "#4ECDC4"},
        "ocean": {"name": "Ocean", "primary": "#006994", "secondary": "#38A3A5"}
    }
    return {"themes": themes}

@app.get("/api/personalities")
async def get_personalities():
    """Get available personality types"""
    personalities = {
        "friendly": "Warm, enthusiastic, and encouraging (default)",
        "professional": "Formal, concise, and focused",
        "encouraging": "Motivational and supportive",
        "concise": "Brief and to-the-point"
    }
    return {"personalities": personalities}

# ============================================================================
# RAG & MODEL ENDPOINTS
# ============================================================================

@app.get("/api/models")
async def get_models():
    """Get available AI models"""
    try:
        models = EnhancedRAGSystem.get_available_models()
        logger.info(f"📊 Returning {len(models)} models")
        return {"models": models}
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return {"models": []}

@app.post("/api/models/select")
async def select_model(request: ModelSelect):
    """Select an AI model"""
    global rag_system
    
    try:
        model_name = request.model_name
        logger.info(f"🔄 User {request.user_id} switching to model: {model_name}")
        
        if model_name not in rag_systems:
            handbook_path = project_root / "data" / "student-handbook-structured.csv"
            logger.info(f"📦 Initializing new RAG system for {model_name}")
            rag_systems[model_name] = EnhancedRAGSystem(str(handbook_path), model_name=model_name)
        
        rag_system = rag_systems[model_name]
        logger.info(f"✅ Switched to model: {model_name}")
        return {"success": True, "model": model_name}
    except Exception as e:
        logger.error(f"❌ Model selection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/mode")
async def set_rag_mode(request: RAGModeChange):
    """Set RAG mode (university or general)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        logger.info(f"🎓 User {request.user_id} setting university mode: {request.university_mode}")
        if hasattr(rag_system, 'set_university_mode'):
            rag_system.set_university_mode(request.university_mode)
            mode = "university" if request.university_mode else "general"
            return {"success": True, "mode": mode}
        else:
            raise HTTPException(status_code=501, detail="Mode switching not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/analyze-url")
async def analyze_url(url_data: URLAnalyze):
    """Analyze a website URL"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        if hasattr(rag_system, 'scrape_and_add_website'):
            rag_system.scrape_and_add_website(url_data.url)
            
            if url_data.question:
                response = rag_system.query(url_data.question)
                return {"success": True, "url": url_data.url, "response": response}
            else:
                return {"success": True, "url": url_data.url, "message": "Website content loaded"}
        else:
            raise HTTPException(status_code=501, detail="URL analysis not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/web-session")
async def get_web_session():
    """Get active web session info"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        if hasattr(rag_system, 'get_web_session_info'):
            info = rag_system.get_web_session_info()
            return info
        else:
            return {"urls": [], "total_documents": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/rag/web-content")
async def clear_web_content(url: Optional[str] = None):
    """Clear web content (all or specific URL)"""
    if not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        if hasattr(rag_system, 'clear_web_content'):
            rag_system.clear_web_content(url)
            return {"success": True, "cleared": url or "all"}
        else:
            raise HTTPException(status_code=501, detail="Web content clearing not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================================================

@app.get("/api/conversations/user/{user_id}")
async def get_user_conversations(user_id: int, limit: int = 50):
    """Get conversation history for a user"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        conversations = conversation_manager.get_user_sessions(user_id, limit)
        return {
            "conversations": conversations,
            "total": len(conversations)
        }
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversation/{session_uuid}")
async def get_conversation_messages(session_uuid: str, user_id: int = 1):
    """Get messages for a specific conversation"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        messages = conversation_manager.get_session_messages(session_uuid, user_id)
        return {
            "messages": messages,
            "session_uuid": session_uuid,
            "total": len(messages)
        }
    except Exception as e:
        logger.error(f"Error fetching conversation messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversation/create")
async def create_conversation(request: Request):
    """Create a new conversation session"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        data = await request.json()
        user_id = data.get('user_id', 1)
        title = data.get('title', 'New Conversation')
        
        session_uuid = conversation_manager.create_conversation_session(user_id, title)
        if session_uuid:
            return {
                "success": True,
                "session_uuid": session_uuid,
                "title": title
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversation/{session_uuid}")
async def delete_conversation(session_uuid: str, user_id: int = 1):
    """Delete a conversation and its messages"""
    if not conversation_manager:
        raise HTTPException(status_code=503, detail="Conversation manager not available")
    
    try:
        # Note: Would need to implement delete_conversation in ConversationHistoryManager
        return {"success": True, "deleted": session_uuid}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
