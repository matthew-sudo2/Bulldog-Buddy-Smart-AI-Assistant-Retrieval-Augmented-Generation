"""
User Settings and Personalization Module for Bulldog Buddy
Handles profile icons, themes, and model behavior preferences
"""

import streamlit as st
from typing import Dict, List, Optional
try:
    from .database import BulldogBuddyDatabase
except ImportError:
    from database import BulldogBuddyDatabase
import json

# Available profile icons (emoji-based)
PROFILE_ICONS = {
    "🐶": "Bulldog (Classic)",
    "🎓": "Graduate Cap",
    "📚": "Books",
    "🤖": "Robot",
    "🌟": "Star",
    "🔥": "Fire",
    "⚡": "Lightning", 
    "🎯": "Target",
    "🚀": "Rocket",
    "💎": "Diamond",
    "🎨": "Artist",
    "🏆": "Trophy",
    "🦄": "Unicorn",
    "🐱": "Cat",
    "🐸": "Frog",
    "🦊": "Fox",
    "🐰": "Rabbit",
    "🐼": "Panda"
}

# Color themes
COLOR_THEMES = {
    "university": {
        "name": "🏫 University Blue",
        "primary": "#2E4057",
        "secondary": "#1A252F", 
        "background": "#F8F9FA",
        "accent": "#6C757D",
        "description": "Classic university colors"
    },
    "forest": {
        "name": "🌲 Forest Green",
        "primary": "#2D5016",
        "secondary": "#1A3009",
        "background": "#F0F8F0",
        "accent": "#4A7C59",
        "description": "Nature-inspired green theme"
    },
    "sunset": {
        "name": "🌅 Sunset Orange",
        "primary": "#E67E22",
        "secondary": "#D35400",
        "background": "#FDF2E9",
        "accent": "#F39C12",
        "description": "Warm sunset colors"
    },
    "ocean": {
        "name": "🌊 Ocean Blue",
        "primary": "#3498DB",
        "secondary": "#2980B9",
        "background": "#EBF5FB",
        "accent": "#5DADE2",
        "description": "Cool ocean blue theme"
    },
    "royal": {
        "name": "👑 Royal Purple",
        "primary": "#8E44AD",
        "secondary": "#7D3C98",
        "background": "#F4F0F8",
        "accent": "#A569BD",
        "description": "Elegant purple theme"
    },
    "crimson": {
        "name": "🔴 Crimson Red",
        "primary": "#C0392B",
        "secondary": "#A93226",
        "background": "#FDEDEC",
        "accent": "#E74C3C",
        "description": "Bold crimson theme"
    },
    "dark": {
        "name": "🌙 Dark Mode",
        "primary": "#1E1E1E",
        "secondary": "#2D2D2D",
        "background": "#121212",
        "accent": "#BB86FC",
        "description": "Easy on the eyes"
    }
}

# Model personality settings
PERSONALITY_TYPES = {
    "friendly": {
        "name": "😊 Friendly & Casual",
        "description": "Warm, approachable, uses casual language",
        "prompt_modifier": "Respond in a very friendly, warm, and casual tone. Use conversational language and be approachable."
    },
    "professional": {
        "name": "💼 Professional & Formal",
        "description": "Clear, direct, business-like communication",
        "prompt_modifier": "Respond in a professional, formal tone. Be clear, direct, and business-like in your communication."
    },
    "enthusiastic": {
        "name": "🎉 Enthusiastic & Energetic",
        "description": "Upbeat, exciting, motivational responses",
        "prompt_modifier": "Respond with high energy, enthusiasm, and motivation. Be upbeat and exciting in your responses."
    },
    "scholarly": {
        "name": "🎓 Scholarly & Academic",
        "description": "Detailed, educational, research-focused",
        "prompt_modifier": "Respond in an academic, scholarly tone. Provide detailed, educational information with research-focused explanations."
    },
    "supportive": {
        "name": "🤗 Supportive & Encouraging",
        "description": "Empathetic, encouraging, helpful guidance",
        "prompt_modifier": "Respond with empathy, encouragement, and supportive guidance. Be understanding and helpful."
    },
    "concise": {
        "name": "⚡ Concise & Direct",
        "description": "Brief, to-the-point, efficient responses",
        "prompt_modifier": "Respond concisely and directly. Be brief, to-the-point, and efficient with your responses."
    }
}

# Response length preferences
RESPONSE_LENGTHS = {
    "brief": "Brief (1-2 sentences)",
    "moderate": "Moderate (1-2 paragraphs)",
    "detailed": "Detailed (Multiple paragraphs)",
    "comprehensive": "Comprehensive (Full explanations)"
}

def get_user_settings(user_id: int) -> Dict:
    """Get user personalization settings from database"""
    try:
        db = BulldogBuddyDatabase()
        conn = db.get_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT profile_icon, color_theme, personality_type, response_length,
                       custom_instructions, notifications_enabled
                FROM users 
                WHERE id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            
        db.return_connection(conn)
        
        if result:
            return {
                "profile_icon": result.get("profile_icon", "🐶"),
                "color_theme": result.get("color_theme", "university"), 
                "personality_type": result.get("personality_type", "friendly"),
                "response_length": result.get("response_length", "moderate"),
                "custom_instructions": result.get("custom_instructions", ""),
                "notifications_enabled": result.get("notifications_enabled", True)
            }
        else:
            # Return default settings
            return {
                "profile_icon": "🐶",
                "color_theme": "university",
                "personality_type": "friendly", 
                "response_length": "moderate",
                "custom_instructions": "",
                "notifications_enabled": True
            }
            
    except Exception as e:
        print(f"Error loading settings: {e}")  # Use print instead of st.error for non-Streamlit contexts
        return {}

def save_user_settings(user_id: int, settings: Dict) -> bool:
    """Save user personalization settings to database"""
    try:
        db = BulldogBuddyDatabase()
        conn = db.get_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET profile_icon = %s,
                    color_theme = %s,
                    personality_type = %s,
                    response_length = %s,
                    custom_instructions = %s,
                    notifications_enabled = %s
                WHERE id = %s
            """, (
                settings.get("profile_icon", "🐶"),
                settings.get("color_theme", "university"),
                settings.get("personality_type", "friendly"),
                settings.get("response_length", "moderate"),
                settings.get("custom_instructions", ""),
                settings.get("notifications_enabled", True),
                user_id
            ))
            
            conn.commit()
            
        db.return_connection(conn)
        return True
        
    except Exception as e:
        print(f"Error saving settings: {e}")  # Use print instead of st.error for non-Streamlit contexts
        return False

def apply_theme(theme_key: str):
    """Apply selected color theme to Streamlit interface"""
    if theme_key not in COLOR_THEMES:
        theme_key = "university"
    
    theme = COLOR_THEMES[theme_key]
    
    # Generate CSS for the selected theme
    theme_css = f"""
    <style>
        /* Main theme colors */
        .main-header {{
            color: {theme['primary']} !important;
        }}
        
        .stButton > button {{
            background-color: {theme['primary']} !important;
            color: white !important;
            border-radius: 20px !important;
            border: none !important;
        }}
        
        .stButton > button:hover {{
            background-color: {theme['secondary']} !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        }}
        
        .stSelectbox > div > div {{
            border-color: {theme['primary']} !important;
        }}
        
        .stTextInput > div > div > input {{
            border-color: {theme['primary']} !important;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: {theme['accent']} !important;
            box-shadow: 0 0 0 2px {theme['accent']}33 !important;
        }}
        
        .quick-link {{
            border-left-color: {theme['primary']} !important;
        }}
        
        /* Sidebar styling */
        .css-1d391kg {{
            background-color: {theme['background']} !important;
        }}
        
        /* Chat message styling */
        .stChatMessage {{
            border-left: 3px solid {theme['accent']} !important;
        }}
        
        /* Custom profile section */
        .profile-section {{
            background: linear-gradient(135deg, {theme['primary']}15, {theme['accent']}15);
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            border: 1px solid {theme['primary']}30;
        }}
        
        .settings-section {{
            background: {theme['background']};
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            border: 1px solid {theme['primary']}20;
        }}
    </style>
    """
    
    st.markdown(theme_css, unsafe_allow_html=True)

def get_personality_prompt_modifier(settings: Dict) -> str:
    """Get prompt modifier based on user personality settings"""
    personality = settings.get("personality_type", "friendly")
    length = settings.get("response_length", "moderate")
    custom = settings.get("custom_instructions", "")
    
    modifier = ""
    
    # Add personality modifier
    if personality in PERSONALITY_TYPES:
        modifier += PERSONALITY_TYPES[personality]["prompt_modifier"]
    
    # Add length preference
    if length == "brief":
        modifier += " Keep responses brief and concise."
    elif length == "detailed":
        modifier += " Provide detailed, thorough explanations."
    elif length == "comprehensive":
        modifier += " Give comprehensive, complete answers with examples."
    
    # Add custom instructions
    if custom.strip():
        modifier += f" Additional instructions: {custom.strip()}"
    
    return modifier

def show_settings_page():
    """Display the user settings page"""
    if not st.session_state.get("authenticated"):
        st.error("Please log in to access settings.")
        return
    
    user = st.session_state.user
    user_id = user["id"]
    
    # Load current settings
    current_settings = get_user_settings(user_id)
    
    # Apply current theme
    apply_theme(current_settings.get("color_theme", "university"))
    
    # Header
    st.markdown("# ⚙️ Personalization Settings")
    st.markdown(f"*Customize your Bulldog Buddy experience, {user['first_name']}!*")
    
    # Create tabs for different settings categories
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Profile", "🎨 Appearance", "🤖 AI Behavior", "🔔 Preferences"])
    
    # Initialize settings in session state if not exists
    if "temp_settings" not in st.session_state:
        st.session_state.temp_settings = current_settings.copy()
    
    with tab1:
        st.markdown("### 👤 Profile Settings")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**Current Icon:**")
            current_icon = st.session_state.temp_settings.get("profile_icon", "🐶")
            st.markdown(f'<div style="font-size: 4rem; text-align: center;">{current_icon}</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Choose Your Profile Icon:**")
            
            # Create a grid of icon options
            icon_cols = st.columns(6)
            selected_icon = current_icon
            
            for i, (icon, name) in enumerate(PROFILE_ICONS.items()):
                col_idx = i % 6
                with icon_cols[col_idx]:
                    if st.button(f"{icon}", key=f"icon_{icon}", help=name):
                        st.session_state.temp_settings["profile_icon"] = icon
                        st.rerun()
        
        st.markdown("---")
        
        # User info display
        st.markdown("### 📋 Account Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**Name:** {user['first_name']} {user['last_name']}")
            st.info(f"**Username:** @{user['username']}")
            
        with col2:
            st.info(f"**Email:** {user['email']}")
            if user.get('student_id'):
                st.info(f"**Student ID:** {user['student_id']}")
    
    with tab2:
        st.markdown("### 🎨 Appearance Settings")
        
        # Theme selection
        st.markdown("**Color Theme:**")
        
        current_theme = st.session_state.temp_settings.get("color_theme", "university")
        
        # Display themes in a grid
        theme_cols = st.columns(2)
        
        for i, (theme_key, theme_data) in enumerate(COLOR_THEMES.items()):
            col_idx = i % 2
            with theme_cols[col_idx]:
                # Theme preview card
                is_selected = theme_key == current_theme
                border_style = "3px solid #007bff" if is_selected else "1px solid #ddd"
                
                st.markdown(f"""
                <div style="
                    border: {border_style};
                    border-radius: 10px;
                    padding: 1rem;
                    margin: 0.5rem 0;
                    background: linear-gradient(135deg, {theme_data['primary']}15, {theme_data['background']});
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                        <div style="
                            width: 20px; 
                            height: 20px; 
                            background: {theme_data['primary']}; 
                            border-radius: 50%; 
                            margin-right: 10px;
                        "></div>
                        <strong>{theme_data['name']}</strong>
                    </div>
                    <small>{theme_data['description']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Select {theme_data['name']}", key=f"theme_{theme_key}"):
                    st.session_state.temp_settings["color_theme"] = theme_key
                    apply_theme(theme_key)
                    st.success(f"✨ {theme_data['name']} theme applied!")
                    st.rerun()
    
    with tab3:
        st.markdown("### 🤖 AI Behavior Settings")
        
        # Personality Type
        st.markdown("**AI Personality:**")
        current_personality = st.session_state.temp_settings.get("personality_type", "friendly")
        
        personality_option = st.selectbox(
            "How would you like Bulldog Buddy to respond?",
            options=list(PERSONALITY_TYPES.keys()),
            format_func=lambda x: PERSONALITY_TYPES[x]["name"],
            index=list(PERSONALITY_TYPES.keys()).index(current_personality),
            key="personality_select"
        )
        
        if personality_option != current_personality:
            st.session_state.temp_settings["personality_type"] = personality_option
        
        # Show description
        st.info(f"💡 **{PERSONALITY_TYPES[personality_option]['name']}**: {PERSONALITY_TYPES[personality_option]['description']}")
        
        st.markdown("---")
        
        # Response Length
        st.markdown("**Response Length Preference:**")
        current_length = st.session_state.temp_settings.get("response_length", "moderate")
        
        length_option = st.selectbox(
            "How detailed should responses be?",
            options=list(RESPONSE_LENGTHS.keys()),
            format_func=lambda x: RESPONSE_LENGTHS[x],
            index=list(RESPONSE_LENGTHS.keys()).index(current_length),
            key="length_select"
        )
        
        if length_option != current_length:
            st.session_state.temp_settings["response_length"] = length_option
            
        st.markdown("---")
        
        # Custom Instructions
        st.markdown("**Custom Instructions:**")
        current_custom = st.session_state.temp_settings.get("custom_instructions", "")
        
        custom_instructions = st.text_area(
            "Add any specific instructions for how you'd like Bulldog Buddy to behave:",
            value=current_custom,
            placeholder="e.g., 'Always include emojis in responses' or 'Focus on practical study tips'",
            height=100,
            key="custom_instructions"
        )
        
        st.session_state.temp_settings["custom_instructions"] = custom_instructions
    
    with tab4:
        st.markdown("### 🔔 General Preferences")
        
        # Notifications
        current_notifications = st.session_state.temp_settings.get("notifications_enabled", True)
        
        notifications_enabled = st.checkbox(
            "Enable system notifications",
            value=current_notifications,
            help="Receive notifications about updates and important announcements",
            key="notifications_checkbox"
        )
        
        st.session_state.temp_settings["notifications_enabled"] = notifications_enabled
        
        st.markdown("---")
        
        # Preview section
        st.markdown("### 👁️ Preview Your Settings")
        
        preview_settings = st.session_state.temp_settings
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Your Profile:**")
            st.markdown(f"""
            <div class="profile-section">
                <div style="text-align: center; font-size: 2rem;">
                    {preview_settings.get('profile_icon', '🐶')}
                </div>
                <div style="text-align: center; margin-top: 0.5rem;">
                    <strong>{user['first_name']} {user['last_name']}</strong><br>
                    <small>@{user['username']}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("**AI Behavior:**")
            personality_name = PERSONALITY_TYPES[preview_settings.get('personality_type', 'friendly')]['name']
            length_name = RESPONSE_LENGTHS[preview_settings.get('response_length', 'moderate')]
            
            st.markdown(f"""
            <div class="settings-section">
                <strong>Personality:</strong> {personality_name}<br>
                <strong>Response Length:</strong> {length_name}<br>
                <strong>Theme:</strong> {COLOR_THEMES[preview_settings.get('color_theme', 'university')]['name']}
            </div>
            """, unsafe_allow_html=True)
    
    # Save/Cancel buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            if save_user_settings(user_id, st.session_state.temp_settings):
                st.success("✅ Settings saved successfully!")
                st.balloons()
                # Update current settings in session state
                st.session_state.user_settings = st.session_state.temp_settings.copy()
                st.rerun()
            else:
                st.error("❌ Failed to save settings. Please try again.")
    
    with col3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.temp_settings = current_settings.copy()
            st.success("🔄 Settings reset to saved values!")
            st.rerun()

def init_user_settings():
    """Initialize user settings in session state"""
    if st.session_state.get("authenticated") and "user_settings" not in st.session_state:
        user_id = st.session_state.user["id"]
        st.session_state.user_settings = get_user_settings(user_id)

def get_current_user_settings() -> Dict:
    """Get current user settings from session state"""
    return st.session_state.get("user_settings", {
        "profile_icon": "🐶",
        "color_theme": "university",
        "personality_type": "friendly",
        "response_length": "moderate",
        "custom_instructions": "",
        "notifications_enabled": True
    })