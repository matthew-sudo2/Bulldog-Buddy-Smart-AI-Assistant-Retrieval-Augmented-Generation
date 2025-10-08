import streamlit as st
import time
from datetime import datetime
import ollama
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to access models
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "core"))

from models.enhanced_rag_system import EnhancedRAGSystem

# Import core modules - handle both relative and absolute imports
try:
    from .auth import require_auth, show_user_info, init_session_state as auth_init_session_state
    from .settings import show_settings_page, init_user_settings, get_current_user_settings, apply_theme, get_personality_prompt_modifier
    from .conversation_history import ConversationHistoryManager
except ImportError:
    # Fallback for when running as script
    from auth import require_auth, show_user_info, init_session_state as auth_init_session_state
    from settings import show_settings_page, init_user_settings, get_current_user_settings, apply_theme, get_personality_prompt_modifier
    from conversation_history import ConversationHistoryManager

# Set page configuration
st.set_page_config(
    page_title="Bulldog Buddy - Smart Campus Assistant",
    page_icon="🐶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for school theme and styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E4057;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .tagline {
        text-align: center;
        color: #6C757D;
        font-size: 1.2rem;
        font-style: italic;
        margin-bottom: 2rem;
    }
    .sidebar-logo {
        text-align: center;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .quick-link {
        padding: 0.5rem;
        margin: 0.25rem 0;
        background-color: #F8F9FA;
        border-radius: 5px;
        border-left: 4px solid #2E4057;
    }
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
    }
    /* School color theme */
    .stButton > button {
        background-color: #2E4057;
        color: white;
        border-radius: 20px;
    }
    .stButton > button:hover {
        background-color: #1A252F;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def get_available_models_safe():
    """Safely get available models with fallback"""
    try:
        return EnhancedRAGSystem.get_available_models()
    except Exception as e:
        logging.error(f"Error loading models from EnhancedRAGSystem: {e}")
        # Return hardcoded fallback models
        return [
            {
                "id": "gemma3:latest",
                "name": "Matt 3", 
                "description": "Matt 3 - Balanced performance, good for general tasks",
                "temperature": 0.3,
                "icon": "fa-brain"
            },
            {
                "id": "llama3.2:latest",
                "name": "Matt 3.2",
                "description": "Matt 3.2 - Excellent reasoning and comprehensive responses", 
                "temperature": 0.2,
                "icon": "fa-brain"
            }
        ]

@st.cache_resource
def create_rag_system(model_name: str, handbook_path: str):
    """Create and cache RAG system instance"""
    try:
        rag_system = EnhancedRAGSystem(handbook_path, model_name=model_name)
        
        # Initialize the database if not already done
        if not rag_system.is_initialized:
            success = rag_system.initialize_database()
            if not success:
                raise Exception("Failed to initialize RAG database")
        
        return rag_system
    except Exception as e:
        logging.error(f"Failed to create RAG system: {e}")
        return None

def get_rag_system():
    """Get the single RAG system instance, creating if needed"""
    try:
        # Get current model selection
        current_model = st.session_state.get("selected_model", "gemma3:latest")
        
        # Get handbook path
        handbook_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "student-handbook-structured.csv")
        
        # Create or get cached RAG system
        rag_system = create_rag_system(current_model, handbook_path)
        
        if rag_system is None:
            return None
            
        # Apply current settings
        if hasattr(rag_system, 'set_university_mode'):
            university_mode = st.session_state.get("university_mode", True)
            rag_system.set_university_mode(university_mode)
        
        return rag_system
        
    except Exception as e:
        logging.error(f"Error getting RAG system: {e}")
        return None

def clear_rag_cache():
    """Clear RAG system cache to force recreation with new model"""
    try:
        # Clear the cached RAG system
        create_rag_system.clear()
        
        # Also clear any session state references
        if 'rag_system_instance' in st.session_state:
            del st.session_state.rag_system_instance
        
        return True
    except Exception as e:
        logging.error(f"Error clearing RAG cache: {e}")
        return False

def initialize_session_state():
    """Initialize session state variables for chat history and conversation management"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add personalized welcome message
        user_name = ""
        if st.session_state.get("authenticated") and st.session_state.get("user"):
            user_name = f", {st.session_state.user['first_name']}"
        
        welcome_msg = {
            "role": "assistant", 
            "content": f"Woof woof! 🐶 Hey there{user_name}! I'm Bulldog Buddy, your loyal Smart Campus Assistant! I'm absolutely tail-wagging excited to help you with anything you need - from finding your way around campus to answering questions about classes, dining, library hours, or just chatting about student life! What can this faithful pup help you with today? 🐾",
            "timestamp": datetime.now().strftime("%H:%M")
        }
        st.session_state.messages.append(welcome_msg)
    
    # Initialize conversation history manager
    if "conversation_manager" not in st.session_state:
        try:
            st.session_state.conversation_manager = ConversationHistoryManager()
        except Exception as e:
            st.error(f"Could not initialize conversation history: {e}")
            st.session_state.conversation_manager = None
    
    # Initialize current conversation session
    if "current_session_uuid" not in st.session_state:
        st.session_state.current_session_uuid = None
    
    # Initialize conversation history for sidebar
    if "user_conversations" not in st.session_state:
        st.session_state.user_conversations = []
    
    # Initialize university mode
    if "university_mode" not in st.session_state:
        st.session_state.university_mode = True  # Default to university mode
    
    # Initialize RAG system
    if "rag_system" not in st.session_state:
        try:
            handbook_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "student-handbook-structured.csv")
            # Default model
            if "selected_model" not in st.session_state:
                st.session_state.selected_model = "gemma3:latest"
            
            st.session_state.rag_system = EnhancedRAGSystem(handbook_path, model_name=st.session_state.selected_model)
            st.session_state.rag_initialized = False
        except Exception as e:
            st.session_state.rag_system = None
            st.session_state.rag_error = str(e)

        return None


def create_new_conversation():
    """Create a new conversation session"""
    if not st.session_state.get("conversation_manager") or not st.session_state.get("user"):
        return

    user_id = st.session_state.user["id"]
    session_uuid = st.session_state.conversation_manager.create_conversation_session(
        user_id, 
        title="New Conversation"
    )

    if session_uuid:
        # Save current conversation if it has messages
        save_current_conversation()

        # Clear RAG system memory for new conversation
        rag_system = get_rag_system()
        if rag_system:
            try:
                # Clear conversation history
                if hasattr(rag_system, 'clear_conversation_history'):
                    rag_system.clear_conversation_history()
                
                # Clear web content cache
                if hasattr(rag_system, 'clear_web_content'):
                    rag_system.clear_web_content()
                
                # Reset web session state
                if hasattr(rag_system, 'web_session_active'):
                    rag_system.web_session_active = False
                if hasattr(rag_system, 'active_web_content'):
                    rag_system.active_web_content = {}
                if hasattr(rag_system, 'current_web_context'):
                    rag_system.current_web_context = []
                
            except Exception as e:
                st.error(f"Error clearing RAG memory for new conversation: {e}")

        # Start new conversation
        st.session_state.current_session_uuid = session_uuid
        st.session_state.messages = []

        # Initialize saved count for new conversation
        st.session_state[f"saved_count_{session_uuid}"] = 0

        # Re-add welcome message
        initialize_session_state()
        st.rerun()
def save_current_conversation():
    """Save current conversation to database (only new messages)"""
    if (not st.session_state.get("conversation_manager") or 
        not st.session_state.get("current_session_uuid") or
        not st.session_state.get("user") or
        len(st.session_state.get("messages", [])) <= 1):  # Only welcome message
        return
    
    try:
        user_id = st.session_state.user["id"]
        session_uuid = st.session_state.current_session_uuid
        
        # Track how many messages were already saved to avoid duplicates
        saved_message_count = st.session_state.get(f"saved_count_{session_uuid}", 0)
        current_messages = st.session_state.get("messages", [])
        
        # Only save messages beyond the saved count
        messages_to_save = []
        message_index = 0
        
        for i, message in enumerate(current_messages):
            # Skip initial welcome message
            if message["role"] == "assistant" and i == 0:
                continue
                
            # Only process messages beyond what we've already saved
            if message_index >= saved_message_count:
                messages_to_save.append(message)
            
            message_index += 1
        
        # Save only new messages
        for message in messages_to_save:
            success = st.session_state.conversation_manager.add_message_to_session(
                session_uuid=session_uuid,
                user_id=user_id,
                content=message["content"],
                message_type=message["role"],
                confidence_score=message.get("confidence", 0.0),
                model_used=st.session_state.get("selected_model"),
                sources_used=message.get("sources", [])
            )
            
            if success:
                saved_message_count += 1
        
        # Update the saved count for this session
        st.session_state[f"saved_count_{session_uuid}"] = saved_message_count
            
    except Exception as e:
        st.error(f"Error saving conversation: {e}")


def load_conversation(session_uuid: str):
    """Load a conversation from history"""
    if not st.session_state.get("conversation_manager") or not st.session_state.get("user"):
        return
    
    try:
        # Prevent multiple rapid reloads
        if st.session_state.get('loading_conversation', False):
            return
            
        st.session_state.loading_conversation = True
        
        # Save current conversation first
        save_current_conversation()
        
        user_id = st.session_state.user["id"]
        messages = st.session_state.conversation_manager.get_session_messages(session_uuid, user_id)
        
        # Load messages into session state
        st.session_state.messages = []
        for msg in messages:
            st.session_state.messages.append({
                "role": msg["message_type"],
                "content": msg["content"],
                "timestamp": msg["created_at"].strftime("%H:%M") if msg["created_at"] else "",
                "confidence": msg.get("confidence_score", 0.0),
                "sources": msg.get("sources_used", [])
            })
        
        # Set the saved count for this session to prevent re-saving existing messages
        st.session_state[f"saved_count_{session_uuid}"] = len(messages)
        
        st.session_state.current_session_uuid = session_uuid
        st.session_state.loading_conversation = False
        st.rerun()
        
    except Exception as e:
        st.session_state.loading_conversation = False
        st.error(f"Error loading conversation: {e}")


def show_conversation_sidebar():
    """Show organized conversation history sidebar"""
    if not st.session_state.get("conversation_manager") or not st.session_state.get("user"):
        return
    
    st.markdown("### 💬 Conversations")
    
    # New conversation button
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("➕ New Chat", key="new_chat", use_container_width=True):
            create_new_conversation()
    
    with col2:
        if st.button("🔍", key="search_toggle", help="Search conversations"):
            st.session_state.show_search = not st.session_state.get("show_search", False)
    
    # Search conversations
    if st.session_state.get("show_search", False):
        search_query = st.text_input("🔍 Search conversations...", key="conv_search")
        if search_query and len(search_query) > 2:
            user_id = st.session_state.user["id"]
            search_results = st.session_state.conversation_manager.search_conversations(
                user_id, search_query, limit=5
            )
            
            if search_results:
                st.markdown("**Search Results:**")
                for result in search_results:
                    with st.container():
                        st.markdown(f"""
                        <div style="border-left: 3px solid #007bff; padding-left: 10px; margin: 5px 0;">
                            <small><strong>{result['session_title'][:30]}...</strong></small><br>
                            <small>{result['message_content'][:50]}...</small><br>
                            <small>Similarity: {result['similarity_score']:.1%}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"Load", key=f"load_{result['session_id']}", use_container_width=True):
                            # The session_id in search results is actually the session_uuid
                            load_conversation(result['session_id'])
            else:
                st.info("No conversations found")
    
    # Load conversation history
    try:
        user_id = st.session_state.user["id"]
        conversations = st.session_state.conversation_manager.get_user_sessions(
            user_id, limit=15
        )
        
        if conversations:
            # Group conversations
            pinned = [c for c in conversations if c.get("pinned")]
            recent = [c for c in conversations if not c.get("pinned") and not c.get("is_archived")][:10]
            
            # Pinned conversations
            if pinned:
                st.markdown("**📌 Pinned**")
                for conv in pinned:
                    show_conversation_item(conv, is_pinned=True)
            
            # Recent conversations  
            if recent:
                st.markdown("**🕒 Recent**")
                for conv in recent:
                    show_conversation_item(conv, is_pinned=False)
            
            # Show insights
            if len(conversations) > 0:
                with st.expander("📊 Conversation Insights", expanded=False):
                    insights = st.session_state.conversation_manager.get_conversation_insights(user_id)
                    if insights:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Chats", insights.get("total_sessions", 0))
                            st.metric("Messages", insights.get("total_messages", 0))
                        with col2:
                            st.metric("Avg Length", f"{insights.get('avg_message_length', 0):.0f}")
                            if insights.get("last_conversation"):
                                last_conv = insights["last_conversation"].strftime("%m/%d")
                                st.metric("Last Chat", last_conv)
        else:
            st.info("No conversation history yet. Start chatting to see your conversations here!")
            
    except Exception as e:
        st.error(f"Error loading conversations: {e}")


def show_conversation_item(conv: dict, is_pinned: bool = False):
    """Show individual conversation item in sidebar"""
    # Truncate title
    title = conv["title"][:25] + "..." if len(conv["title"]) > 25 else conv["title"]
    
    # Format time
    time_str = conv["updated_at"].strftime("%m/%d") if conv["updated_at"] else ""
    
    # Current session indicator
    is_current = st.session_state.get("current_session_uuid") == conv["session_uuid"]
    
    # Container for conversation item
    container = st.container()
    with container:
        # Use columns for layout
        col1, col2, col3 = st.columns([5, 1, 1])
        
        with col1:
            # Conversation button with styling
            button_style = "🟢 " if is_current else ""
            if st.button(
                f"{button_style}{title}",
                key=f"conv_{conv['session_uuid']}",
                help=f"{conv['preview']}\n{conv['message_count']} messages • {time_str}",
                use_container_width=True
            ):
                if not is_current:
                    load_conversation(conv["session_uuid"])
        
        with col2:
            # Pin/unpin button
            pin_icon = "📌" if is_pinned else "📍"
            if st.button(
                pin_icon,
                key=f"pin_{conv['session_uuid']}",
                help="Pin/Unpin conversation"
            ):
                st.session_state.conversation_manager.pin_conversation(
                    conv["session_uuid"], 
                    st.session_state.user["id"],
                    not is_pinned
                )
                st.rerun()
        
        with col3:
            # Delete button
            if st.button(
                "🗑️",
                key=f"del_{conv['session_uuid']}",
                help="Delete conversation"
            ):
                # Prevent rapid deletions
                if st.session_state.get('deleting_conversation', False):
                    return
                    
                if st.session_state.get(f"confirm_delete_{conv['session_uuid']}", False):
                    # Actually delete
                    st.session_state.deleting_conversation = True
                    st.session_state.conversation_manager.delete_conversation(
                        conv["session_uuid"],
                        st.session_state.user["id"]
                    )
                    # Clear the confirmation flag
                    st.session_state[f"confirm_delete_{conv['session_uuid']}"] = False
                    st.session_state.deleting_conversation = False
                    
                    if is_current:
                        create_new_conversation()
                    else:
                        st.rerun()
                else:
                    # Ask for confirmation
                    st.session_state[f"confirm_delete_{conv['session_uuid']}"] = True
                    st.rerun()
    
    # Show confirmation message if needed
    if st.session_state.get(f"confirm_delete_{conv['session_uuid']}", False):
        st.warning("⚠️ Click delete again to confirm")


def get_bot_response(user_message):
    """
    Enhanced bot response with web content support and personalization
    """
    try:
        # Get user personalization settings
        user_settings = get_current_user_settings()
        personality_modifier = get_personality_prompt_modifier(user_settings)
        
        # Check if the message contains URLs
        if any(keyword in user_message.lower() for keyword in ['http', 'www.', '.com', '.org', '.net', '.edu']):
            st.info("🌐 I detected a website link! Let me analyze that content for you...")
        
        # Get the single RAG system instance
        rag_system = get_rag_system()
        
        # Set university mode based on session state
        if rag_system:
            university_mode = st.session_state.get("university_mode", True)
            if hasattr(rag_system, 'set_university_mode'):
                rag_system.set_university_mode(university_mode)
            
            # Apply personality settings to RAG system if possible
            if hasattr(rag_system, 'set_personality_settings'):
                rag_system.set_personality_settings(personality_modifier)
        
        # Try to get relevant context using enhanced RAG
        if rag_system:
            try:
                # Initialize database if not already done
                if not rag_system.is_initialized:
                    with st.spinner("🐶 Setting up my enhanced knowledge base... This might take a moment!"):
                        success = rag_system.initialize_database()
                        if success:
                            st.success("✅ Enhanced knowledge base ready!")
                        else:
                            st.warning("⚠️ Knowledge base setup had issues, but I can still help!")
                
                # Use the enhanced RAG system's ask_question method (now supports web content)
                response_data = rag_system.ask_question(user_message)
                
                # Handle different response types
                response_type = response_data.get('type', 'general')
                
                if response_type == 'web_analysis':
                    # Special handling for web content analysis
                    st.success(f"🌐 Analyzed {response_data.get('documents_found', 0)} sections from {len(response_data.get('urls_processed', []))} website(s)")
                    
                    # Show processed URLs
                    with st.expander("🔗 Analyzed Websites", expanded=False):
                        for url in response_data.get('urls_processed', []):
                            st.write(f"• {url}")
                
                # Get the complete response directly from enhanced RAG
                complete_response = response_data['answer']
                confidence = response_data['confidence']
                sources = response_data.get('sources', response_data.get('source_documents', []))
                
                # Display confidence if available
                if confidence > 0:
                    st.sidebar.metric("Response Confidence", f"{confidence:.1%}")
                
                # Display mode indicator
                response_mode = response_data.get('mode', 'university' if st.session_state.get("university_mode", True) else 'general')
                if response_mode == 'university':
                    st.sidebar.success("🏫 University Mode: Used Student Handbook")
                else:
                    st.sidebar.info("🌐 General Mode: Used AI Knowledge")
                
                # Display sources (adapted for web content)
                if sources:
                    with st.sidebar.expander(f"📚 Sources ({len(sources)})", expanded=False):
                        for i, source in enumerate(sources):
                            if 'url' in source:  # Web source
                                st.write(f"**{i+1}. {source.get('title', 'Web Content')}**")
                                st.write(f"🌐 URL: {source['url']}")
                                if 'relevance_score' in source:
                                    st.write(f"📊 Relevance: {source['relevance_score']:.1%}")
                            else:  # Handbook source
                                st.write(f"**{i+1}. {source.get('title', 'Handbook Section')}**")
                                st.write(f"📚 Category: {source.get('category', 'General')}")
                            
                            content_preview = source.get('content', '')[:150]
                            st.write(f"{content_preview}...")
                            st.divider()
                
                # Yield the response for st.write_stream to handle the display
                # This creates the typewriter effect through st.write_stream
                words = complete_response.split()
                for word in words:
                    yield word + " "
                    time.sleep(0.01)  # Small delay for typewriter effect
                
                return
                
            except Exception as e:
                logging.error(f"Enhanced RAG error: {e}")
                st.error(f"RAG system error: {str(e)}")
                # Fall back to basic ollama response
        
        # Get user's name for personalization
        user_name = ""
        if st.session_state.get("user"):
            user_name = st.session_state.user['first_name']
        
        # Build personalized system prompt
        base_system_prompt = f"""You are Bulldog Buddy, a Smart Campus Assistant AI with a friendly bulldog personality. You help students with campus life, academics, and general questions.

The user's name is {user_name if user_name else 'Student'}, and you should use their name occasionally to make responses more personal.

IMPORTANT: Do NOT introduce yourself unless specifically asked who you are. Jump straight into helping with the user's question.

Key personality traits:
- Be enthusiastic and supportive 
- Use bulldog/dog-related expressions naturally (like "That's paw-some!" or "I'm doggone excited to help!")
- Be knowledgeable about campus life, academics, and student concerns
- Always be encouraging and positive
- Use emojis appropriately, especially 🐶, 🐾, 📚, 🏫
- Keep responses helpful, informative, and school-appropriate
- If you don't know something specific about the campus, be honest but still helpful
- Don't make up answers; if unsure, guide the student to official resources
- Start responses with "Woof!" occasionally but not every time

Remember: You're a smart, loyal companion who genuinely cares about helping students succeed! Answer questions directly without unnecessary introductions."""
        
        # Add personality customization
        if personality_modifier:
            system_prompt = base_system_prompt + f"\n\nIMPORTANT PERSONALIZATION INSTRUCTIONS: {personality_modifier}"
        else:
            system_prompt = base_system_prompt

        # Create the conversation with system prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Call Ollama with streaming enabled (use selected model)
        selected_model = st.session_state.get("selected_model", "gemma3:latest")
        stream = ollama.chat(
            model=selected_model,
            messages=messages,
            stream=True
        )
        
        # Yield each chunk from the stream to create the typewriter effect
        complete_response = ""
        for chunk in stream:
            if chunk['message']['content']:
                complete_response += chunk['message']['content']
                yield chunk['message']['content']
        
        # Add to conversation history after streaming is complete
        if rag_system:
            try:
                rag_system.add_to_history(user_message, complete_response)
            except Exception as e:
                logging.error(f"Failed to add to conversation history: {e}")
        
    except Exception as e:
        # Fallback response if Ollama is not available
        error_message = f"Woof! I'm having a little trouble connecting to my brain right now 🐶. Here's what I can tell you: I'm Bulldog Buddy, your campus assistant! While I get my connection sorted out, you might want to check our quick links in the sidebar for immediate help. Don't worry - I'll be back to full strength soon! 🐾\n\n*Error: {str(e)}*"
        yield error_message

def main():
    # Initialize authentication session state
    auth_init_session_state()
    
    # Check if user is authenticated, if not show auth page
    if not require_auth():
        return
    
    # Initialize user settings
    init_user_settings()
    
    # Get current user settings and apply theme
    user_settings = get_current_user_settings()
    apply_theme(user_settings.get("color_theme", "university"))
    
    # Check if settings page should be shown
    if st.session_state.get("show_settings", False):
        show_settings_page()
        # Add back button
        if st.button("← Back to Chat"):
            st.session_state.show_settings = False
            st.rerun()
        return
    
    # Initialize chat session state
    initialize_session_state()
    
    # Show user info in sidebar
    show_user_info()
    
    # Sidebar
    with st.sidebar:
        # Conversation History section
        show_conversation_sidebar()
        
        st.divider()
        
        # Quick Links section  
        st.markdown("### 📋 Quick Links")
        
        # School Website
        st.markdown("""
        <div class="quick-link">
            <strong>🏫 School Website</strong><br>
            <small>Visit our main website</small>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🌐 Open School Website", key="website", use_container_width=True):
            st.info("🔗 Replace with your school's website URL")
        
        # Student Portal
        st.markdown("""
        <div class="quick-link">
            <strong>👨‍🎓 Student Portal</strong><br>
            <small>Access grades, schedules & more</small>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📚 Open Student Portal", key="portal", use_container_width=True):
            st.info("https://onlineapp.national-u.edu.ph/projectnuis/main.php")
        
        # Library
        st.markdown("""
        <div class="quick-link">
            <strong>📖 Library</strong><br>
            <small>Resources & study spaces</small>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📚 Library Resources", key="library", use_container_width=True):
            st.info("🔗 Replace with your library website URL")
        
        st.divider()
        
        # University Mode Toggle section
        st.markdown("### 🎓 Response Mode")
        
        # Initialize university mode in session state if not exists
        if "university_mode" not in st.session_state:
            st.session_state.university_mode = True
        
        # Toggle button for university mode
        current_mode = st.session_state.university_mode
        mode_label = "🏫 University Mode" if current_mode else "🌐 General Mode"
        mode_description = "Using Student Handbook" if current_mode else "Using AI Knowledge"
        
        # Create two columns for the mode display
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{mode_label}**")
            st.caption(mode_description)
        
        with col2:
            if st.button("🔄", help="Switch mode", key="toggle_mode", use_container_width=True):
                try:
                    st.session_state.university_mode = not st.session_state.university_mode
                    # Update the RAG system mode
                    rag_system = get_rag_system()
                    if rag_system:
                        # Check if the method exists
                        if hasattr(rag_system, 'set_university_mode'):
                            rag_system.set_university_mode(st.session_state.university_mode)
                        else:
                            st.error("🔄 Updating system... Please refresh the page.")
                            st.cache_resource.clear()  # Clear cache to get updated methods
                    else:
                        st.warning("⚠️ RAG system not initialized yet. Mode will be applied when system starts.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error toggling mode: {e}")
                    # Try to clear cache and reinitialize
                    st.cache_resource.clear()
                    # Ensure session state exists
                    if "university_mode" not in st.session_state:
                        st.session_state.university_mode = True
        
        # Mode explanation
        if current_mode:
            st.info("📚 **University Mode**: Questions are answered using the Student Handbook and university policies.")
        else:
            st.info("🧠 **General Mode**: Questions are answered using AI general knowledge and web content.")
        
        st.divider()
        
        # Conversation History section
        st.markdown("### 💭 Recent Conversation")
        rag_system = get_rag_system()
        if rag_system and hasattr(rag_system, 'conversation_history'):
            if rag_system.conversation_history:
                # Show last 3 exchanges in sidebar
                recent_history = rag_system.conversation_history[-3:]
                for i, exchange in enumerate(recent_history, 1):
                    with st.expander(f"Exchange {len(rag_system.conversation_history) - len(recent_history) + i}", expanded=False):
                        st.write(f"**You:** {exchange['user'][:80]}{'...' if len(exchange['user']) > 80 else ''}")
                        st.write(f"**Buddy:** {exchange['assistant'][:120]}{'...' if len(exchange['assistant']) > 120 else ''}")
                        st.caption(f"⏰ {exchange['timestamp']}")
                
                # Add button to clear conversation history
                if st.button("🗑️ Clear History", key="clear_history", use_container_width=True):
                    rag_system.clear_conversation_history()
                    st.success("Conversation history cleared!")
                    st.rerun()
            else:
                st.write("No conversation history yet. Start chatting! 🐾")
        else:
            st.write("Conversation tracking ready to start! 💬")
        
        st.divider()
        
        # Additional info
        st.markdown("### ℹ️ About")
        # Get current model display name
        current_model_id = st.session_state.get("selected_model", "gemma3:latest")
        available_models = get_available_models_safe()
        current_model_display = "Matt 3"  # Default fallback
        for model in available_models:
            if model["id"] == current_model_id:
                current_model_display = model["name"]
                break
        
        st.markdown(f"""
        **Bulldog Buddy** is your AI-powered 24/7 campus companion! 🤖🐶
        
        **🆕 NEW: Website Analysis Feature!**  
        Just paste any website URL in your message and I'll analyze it for you!
        
        **Current Model:** {current_model_display}  
        **Embeddings:** Gemma Embeddings  
        **Vector DB:** ChromaDB + Web Content Analysis  
        **Knowledge:** University Handbook + Live Web Content  
        **Memory:** Remembers last 10 conversations for context
        
        **I can help with:**
        - 📚 Academic questions & study tips
        - 🏫 Campus information & directions  
        - � **Website content analysis** (NEW!)
        - 🔍 **Similarity search on any webpage** (NEW!)
        - 📅 Events & important dates
        - 💡 General advice & support
        - 🔄 Follow-up questions using conversation history
        - 🎓 And much more!
        
        **Example:** "Analyze https://example.com and tell me about their pricing"
        
        *I'm always learning and getting smarter! Woof!* 🐾
        """)
        
        # Model Selection
        st.markdown("### 🤖 AI Model Selection")
        
        # Get available models safely
        available_models = get_available_models_safe()
        
        model_options = {}
        for model_info in available_models:
            model_options[f"{model_info['name']} ({model_info['id']})"] = model_info['id']
        
        # Initialize selected model if not exists
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = "gemma3:latest"
        
        # Model selection dropdown
        selected_display = None
        for display_name, model_key in model_options.items():
            if model_key == st.session_state.selected_model:
                selected_display = display_name
                break
        
        new_model_selection = st.selectbox(
            "Choose AI Model:",
            options=list(model_options.keys()),
            index=list(model_options.keys()).index(selected_display) if selected_display else 0,
            help="Different models have different strengths and response styles"
        )
        
        # Handle model change
        new_model_key = model_options[new_model_selection]
        if new_model_key != st.session_state.selected_model:
            # Store old model for logging
            old_model = st.session_state.selected_model
            st.session_state.selected_model = new_model_key
            
            # Clear RAG cache to force recreation with new model
            success = clear_rag_cache()
            
            # Find the model name for success message
            model_name = "Unknown Model"
            for model_info in available_models:
                if model_info['id'] == new_model_key:
                    model_name = model_info['name']
                    break
            
            if success:
                st.success(f"✅ Switched to {model_name}!")
                st.info("💡 The system will use the new model for your next question.")
            else:
                st.warning(f"⚠️ Switched to {model_name} but cache clearing had issues.")
            
            st.rerun()
        
        # Show current model info
        current_model_info = None
        for model_info in available_models:
            if model_info['id'] == st.session_state.selected_model:
                current_model_info = model_info
                break
        
        if current_model_info:
            st.info(f"🎯 **Current Model:** {current_model_info['name']}\n\n{current_model_info['description']}")
        else:
            st.warning("⚠️ Current model not found in available models list")
        
        st.divider()
        
        # RAG System Status
        st.markdown("### 🧠 Knowledge Base")
        rag_system = get_rag_system()
        if rag_system:
            try:
                stats = rag_system.get_database_stats()
                if stats.get("status") == "initialized":
                    st.success(f"✅ Ready! {stats.get('total_chunks', 0)} knowledge chunks loaded")
                elif stats.get("status") == "not_initialized":
                    st.info("🔄 Knowledge base will initialize on first question")
                else:
                    st.warning("⚠️ Knowledge base needs setup")
            except:
                st.info("🔄 Knowledge base ready to load")
        else:
            st.error("❌ Knowledge base unavailable")
        
        # Debug section (for development)
        with st.expander("🔧 Debug Tools", expanded=False):
            if st.button("🗑️ Clear System Cache", help="Clear cached RAG system"):
                # Clear RAG cache using new function
                success = clear_rag_cache()
                if success:
                    st.success("Cache cleared! The system will reinitialize.")
                else:
                    st.error("Error clearing cache.")
                st.rerun()
            
            # Show current RAG system methods
            rag_system = get_rag_system()
            if rag_system:
                has_uni_mode = hasattr(rag_system, 'set_university_mode')
                st.write(f"University mode methods: {'✅' if has_uni_mode else '❌'}")
                if has_uni_mode:
                    try:
                        mode_info = rag_system.get_mode_info()
                        current_mode = mode_info.get('university_mode', False)
                        st.write(f"Current mode: {'🏫 University' if current_mode else '🌐 General'}")
                    except:
                        st.write("Mode info: ❌ Error getting info")
            else:
                st.write("RAG system: ❌ Not available")
        
        st.divider()
        
        # Web Session Info
        rag_system = get_rag_system()
        if rag_system and rag_system.web_session_active:
            st.markdown("### 🌐 Active Web Session")
            web_info = rag_system.get_web_session_info()
            
            st.success(f"📊 {len(web_info['urls'])} website(s) loaded")
            st.info(f"📄 {web_info['total_documents']} sections available")
            
            # Show active URLs
            with st.expander("🔗 Active Websites", expanded=False):
                for url in web_info['urls']:
                    content_info = rag_system.active_web_content[url]
                    st.write(f"**{content_info['title']}**")
                    st.write(f"🌐 {url}")
                    st.write(f"📄 {content_info['document_count']} sections")
                    
                    # Clear individual website button
                    if st.button(f"❌ Remove", key=f"clear_web_{hash(url)}", use_container_width=True):
                        rag_system.clear_web_content(url)
                        st.success(f"Removed website: {content_info['title']}")
                        st.rerun()
                    st.divider()
            
            # Clear all web content button
            if st.button("🗑️ Clear All Websites", key="clear_all_web", use_container_width=True):
                rag_system.clear_web_content()
                st.success("All web content cleared!")
                st.rerun()
            
            st.info("💬 You can now ask follow-up questions about these websites without pasting URLs again!")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", key="clear", use_container_width=True):
            # Clear UI chat messages
            st.session_state.messages = []
            
            # Clear RAG system conversation memory and web content
            rag_system = get_rag_system()
            if rag_system:
                try:
                    # Clear conversation history
                    if hasattr(rag_system, 'clear_conversation_history'):
                        rag_system.clear_conversation_history()
                    
                    # Clear web content cache
                    if hasattr(rag_system, 'clear_web_content'):
                        rag_system.clear_web_content()
                    
                    # Reset web session state
                    if hasattr(rag_system, 'web_session_active'):
                        rag_system.web_session_active = False
                    if hasattr(rag_system, 'active_web_content'):
                        rag_system.active_web_content = {}
                    if hasattr(rag_system, 'current_web_context'):
                        rag_system.current_web_context = []
                    
                except Exception as e:
                    st.error(f"Error clearing RAG memory: {e}")
            
            # Reset to welcome message
            initialize_session_state()
            st.success("🧹 Chat history and memory cleared!")
            st.rerun()
        
        # Clear system cache button (for developers/testing)
        if st.button("🔄 Refresh System", key="refresh_system", use_container_width=True):
            # Clear RAG cache and session state
            clear_rag_cache()
            st.session_state.clear()
            st.success("System refreshed! Page will reload...")
            st.rerun()
    
    # Main content area
    # Header
    st.markdown('<h1 class="main-header">🐶 Bulldog Buddy – Your Smart Campus Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Loyal. Helpful. Always here for students 🐾</p>', unsafe_allow_html=True)
    
    # Chat interface
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        avatar = "🐶" if message["role"] == "assistant" else "👤"
        
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if "timestamp" in message:
                st.caption(f"⏰ {message['timestamp']}")
    
    # Chat input
    if prompt := st.chat_input("Ask Bulldog Buddy anything about campus life! 🐾"):
        # Prevent multiple simultaneous chat processing
        if st.session_state.get('processing_chat', False):
            st.warning("⏳ Please wait while I finish processing your previous message...")
            st.stop()
        
        st.session_state.processing_chat = True
        
        try:
            # Create new session if needed
            if (not st.session_state.get("current_session_uuid") and 
                st.session_state.get("conversation_manager") and 
                st.session_state.get("user")):
                
                user_id = st.session_state.user["id"]
                session_uuid = st.session_state.conversation_manager.create_conversation_session(user_id)
                st.session_state.current_session_uuid = session_uuid
                
                # Initialize saved count for new session
                st.session_state[f"saved_count_{session_uuid}"] = 0
            
            # Add user message to chat history
            timestamp = datetime.now().strftime("%H:%M")
            user_message = {"role": "user", "content": prompt, "timestamp": timestamp}
            st.session_state.messages.append(user_message)
            
            # Save user message to database
            if (st.session_state.get("conversation_manager") and 
                st.session_state.get("current_session_uuid") and 
                st.session_state.get("user")):
                
                success = st.session_state.conversation_manager.add_message_to_session(
                    session_uuid=st.session_state.current_session_uuid,
                    user_id=st.session_state.user["id"],
                    content=prompt,
                    message_type="user"
                )
                
                # Update saved count if successful
                if success:
                    session_uuid = st.session_state.current_session_uuid
                    current_count = st.session_state.get(f"saved_count_{session_uuid}", 0)
                    st.session_state[f"saved_count_{session_uuid}"] = current_count + 1
            
            # Display user message
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
                st.caption(f"⏰ {timestamp}")
            
            # Get and display assistant response with typewriter effect
            with st.chat_message("assistant", avatar="🐶"):
                # Use st.write_stream to display the streaming response
                response = st.write_stream(get_bot_response(prompt))
                
                response_timestamp = datetime.now().strftime("%H:%M")
                st.caption(f"⏰ {response_timestamp}")
                
                # Add assistant response to chat history
                assistant_message = {
                    "role": "assistant", 
                    "content": response, 
                    "timestamp": response_timestamp
                }
                st.session_state.messages.append(assistant_message)
                
                # Save assistant response to database
                if (st.session_state.get("conversation_manager") and 
                    st.session_state.get("current_session_uuid") and 
                    st.session_state.get("user")):
                    
                    success = st.session_state.conversation_manager.add_message_to_session(
                        session_uuid=st.session_state.current_session_uuid,
                        user_id=st.session_state.user["id"],
                        content=response,
                        message_type="assistant",
                        model_used=st.session_state.get("selected_model", "gemma3:latest")
                    )
                    
                    # Update saved count if successful
                    if success:
                        session_uuid = st.session_state.current_session_uuid
                        current_count = st.session_state.get(f"saved_count_{session_uuid}", 0)
                        st.session_state[f"saved_count_{session_uuid}"] = current_count + 1
        
        except Exception as e:
            st.error(f"Error processing chat: {e}")
        finally:
            # Always reset the processing flag
            st.session_state.processing_chat = False
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6C757D; font-size: 0.9rem;">
        <p>🐶 Bulldog Buddy v1.0 | Built with ❤️ for our school community</p>
        <p><em>Having issues? Contact IT support or visit the student portal for help.</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()