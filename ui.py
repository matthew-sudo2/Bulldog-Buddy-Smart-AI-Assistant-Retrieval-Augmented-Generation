import streamlit as st
import time
from datetime import datetime
import ollama
import json
import logging
import os
from models.enhanced_rag_system import EnhancedRAGSystem

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

def initialize_session_state():
    """Initialize session state variables for chat history"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message with personality
        welcome_msg = {
            "role": "assistant", 
            "content": "Woof woof! 🐶 Hey there, student! I'm Bulldog Buddy, your loyal Smart Campus Assistant! I'm absolutely tail-wagging excited to help you with anything you need - from finding your way around campus to answering questions about classes, dining, library hours, or just chatting about student life! What can this faithful pup help you with today? 🐾",
            "timestamp": datetime.now().strftime("%H:%M")
        }
        st.session_state.messages.append(welcome_msg)
    
    # Initialize RAG system
    if "rag_system" not in st.session_state:
        try:
            handbook_path = "./data/student-handbook-structured.csv"
            # Default model
            if "selected_model" not in st.session_state:
                st.session_state.selected_model = "gemma3:latest"
            
            st.session_state.rag_system = EnhancedRAGSystem(handbook_path, model_name=st.session_state.selected_model)
            st.session_state.rag_initialized = False
        except Exception as e:
            st.session_state.rag_system = None
            st.session_state.rag_error = str(e)

def get_rag_system_with_model(model_name: str = "gemma3:latest"):
    """Get RAG system with specific model (not cached to allow model switching)"""
    try:
        handbook_path = "./data/student-handbook-structured.csv"
        rag_system = EnhancedRAGSystem(handbook_path, model_name=model_name)
        return rag_system
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {e}")
        return None

@st.cache_resource
def get_rag_system():
    """Get or initialize RAG system (cached)"""
    try:
        handbook_path = "./data/student-handbook-structured.csv"
        rag_system = EnhancedRAGSystem(handbook_path)
        return rag_system
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {e}")
        return None

def get_bot_response(user_message):
    """
    Get response from Enhanced RAG system with Bulldog Buddy personality
    """
    try:
        # Get the selected model from session state
        selected_model = st.session_state.get("selected_model", "gemma3:latest")
        
        # Get RAG system with selected model (create fresh instance to use new model)
        rag_system = get_rag_system_with_model(selected_model)
        
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
                
                # Use the enhanced RAG system's ask_question method
                response_data = rag_system.ask_question(user_message)
                
                # Get the complete response directly from enhanced RAG
                complete_response = response_data['answer']
                confidence = response_data['confidence']
                source_docs = response_data['source_documents']
                
                # Display confidence if available
                if confidence > 0:
                    st.sidebar.metric("Response Confidence", f"{confidence:.1%}")
                
                # Display source documents
                if source_docs:
                    with st.sidebar.expander(f"📚 Sources ({len(source_docs)})", expanded=False):
                        for i, source in enumerate(source_docs):
                            st.write(f"**{i+1}. {source['title']}**")
                            st.write(f"Category: {source['category']}")
                            st.write(source['content'][:150] + "...")
                            st.divider()
                
                # Stream the response with typewriter effect
                with st.chat_message("assistant", avatar="🐶"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    # Typewriter effect
                    for chunk in complete_response.split():
                        full_response += chunk + " "
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.02)
                    
                    message_placeholder.markdown(complete_response)
                
                # Add to conversation history
                st.session_state.messages.append({"role": "assistant", "content": complete_response})
                return
                
            except Exception as e:
                logging.error(f"Enhanced RAG error: {e}")
                st.error(f"RAG system error: {str(e)}")
                # Fall back to basic ollama response
        
        system_prompt = """You are Bulldog Buddy, a friendly and loyal Smart Campus Assistant. You have the personality of a helpful bulldog - loyal, protective, energetic, and always eager to help students.

Key personality traits:
- Start responses with "Woof!" occasionally but not every time
- Be enthusiastic and supportive 
- Use bulldog/dog-related expressions naturally (like "That's paw-some!" or "I'm doggone excited to help!")
- Be knowledgeable about campus life, academics, and student concerns
- Always be encouraging and positive
- Use emojis appropriately, especially 🐶, 🐾, 📚, 🏫
- Keep responses helpful, informative, and school-appropriate
- If you don't know something specific about the campus, be honest but still helpful
- Don't make up answers; if unsure, guide the student to official resources

Remember: You're a smart, loyal companion who genuinely cares about helping students succeed!"""

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
    # Initialize session state
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        # School logo/mascot
        st.markdown('<div class="sidebar-logo">🐶</div>', unsafe_allow_html=True)
        st.markdown("### Bulldog Buddy")
        st.markdown("*Your Smart Campus Assistant*")
        
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
        current_model_display = EnhancedRAGSystem.get_available_models().get(
            st.session_state.get("selected_model", "gemma3:latest"), 
            {"name": "Gemma 3"}
        )["name"]
        
        st.markdown(f"""
        **Bulldog Buddy** is your AI-powered 24/7 campus companion! 🤖🐶
        
        **Current Model:** {current_model_display}  
        **Embeddings:** EmbeddingGemma  
        **Vector DB:** ChromaDB  
        **Knowledge:** National University Student Handbook  
        **Memory:** Remembers last 10 conversations for context
        
        **I can help with:**
        - 📚 Academic questions & study tips
        - 🏫 Campus information & directions  
        - 🍽️ Dining options & hours
        - 📅 Events & important dates
        - 💡 General advice & support
        - 🔄 Follow-up questions using conversation history
        - 🎓 And much more!
        
        *I'm always learning and getting smarter! Woof!* 🐾
        """)
        
        # Model Selection
        st.markdown("### 🤖 AI Model Selection")
        
        # Get available models
        available_models = EnhancedRAGSystem.get_available_models()
        model_options = {}
        for model_key, model_info in available_models.items():
            model_options[f"{model_info['name']} ({model_key})"] = model_key
        
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
            st.session_state.selected_model = new_model_key
            
            # Clear cache and reinitialize system with new model
            st.cache_resource.clear()
            if "rag_system" in st.session_state:
                del st.session_state.rag_system
            
            st.success(f"✅ Switched to {available_models[new_model_key]['name']}!")
            st.info("💡 The system will use the new model for your next question.")
            st.rerun()
        
        # Show current model info
        current_model_info = available_models[st.session_state.selected_model]
        st.info(f"🎯 **Current Model:** {current_model_info['name']}\n\n{current_model_info['description']}")
        
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
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", key="clear", use_container_width=True):
            st.session_state.messages = []
            initialize_session_state()  # This will add the welcome message back
            st.rerun()
        
        # Clear system cache button (for developers/testing)
        if st.button("🔄 Refresh System", key="refresh_system", use_container_width=True):
            st.cache_resource.clear()
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
        # Add user message to chat history
        timestamp = datetime.now().strftime("%H:%M")
        user_message = {"role": "user", "content": prompt, "timestamp": timestamp}
        st.session_state.messages.append(user_message)
        
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