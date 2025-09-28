"""
Authentication module for Bulldog Buddy Streamlit app
Handles login, registration, and session management
"""

import streamlit as st
import re
try:
    from .database import BulldogBuddyDatabase
except ImportError:
    from database import BulldogBuddyDatabase
from typing import Dict, Optional

def init_session_state():
    """Initialize authentication session state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"  # "login" or "register"

def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_username(username: str) -> bool:
    """Validate username format"""
    # Username should be 3-20 characters, alphanumeric and underscores only
    username_pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(username_pattern, username) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if len(password) > 128:
        return False, "Password must be less than 128 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    return True, "Password is valid"

def show_login_form():
    """Display login form"""
    st.markdown("### 🔑 Login to Bulldog Buddy")
    
    with st.form("login_form"):
        login = st.text_input("Email or Username", placeholder="Enter your email or username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            login_button = st.form_submit_button("🚀 Login", use_container_width=True)
        with col2:
            if st.form_submit_button("📝 Need an account?", use_container_width=True):
                st.session_state.auth_mode = "register"
                st.rerun()
        
        if login_button:
            if not login or not password:
                st.error("Please fill in all fields")
                return
            
            # Authenticate user
            try:
                db = BulldogBuddyDatabase()
                result = db.authenticate_user(login, password)
                
                if result["success"]:
                    st.session_state.authenticated = True
                    st.session_state.user = result["user"]
                    st.success(f"Welcome back, {result['user']['first_name']}! 🐶")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(result["message"])
                    
            except Exception as e:
                st.error(f"Login failed: {str(e)}")

def show_register_form():
    """Display registration form"""
    st.markdown("### 📝 Register for Bulldog Buddy")
    st.markdown("*Join the pack and get personalized campus assistance!*")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name *", placeholder="Enter your first name")
            email = st.text_input("Email *", placeholder="your.email@university.edu")
            password = st.text_input("Password *", type="password", placeholder="Create a strong password")
            
        with col2:
            last_name = st.text_input("Last Name *", placeholder="Enter your last name")
            username = st.text_input("Username *", placeholder="Choose a unique username")
            confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Confirm your password")
        
        student_id = st.text_input("Student ID (Optional)", placeholder="e.g., STU123456")
        
        st.markdown("*Fields marked with * are required*")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            register_button = st.form_submit_button("🎓 Create Account", use_container_width=True)
        with col2:
            if st.form_submit_button("🔑 Already have account?", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
        
        if register_button:
            # Validation
            errors = []
            
            if not all([first_name, last_name, email, username, password, confirm_password]):
                errors.append("Please fill in all required fields")
            
            if email and not validate_email(email):
                errors.append("Please enter a valid email address")
            
            if username and not validate_username(username):
                errors.append("Username must be 3-20 characters, letters, numbers, and underscores only")
            
            if password:
                is_valid, message = validate_password(password)
                if not is_valid:
                    errors.append(message)
            
            if password != confirm_password:
                errors.append("Passwords do not match")
            
            if errors:
                for error in errors:
                    st.error(error)
                return
            
            # Register user
            try:
                db = BulldogBuddyDatabase()
                result = db.register_user(
                    email=email,
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    student_id=student_id if student_id else None
                )
                
                if result["success"]:
                    st.success("🎉 Account created successfully!")
                    st.success("Please log in with your new credentials")
                    st.session_state.auth_mode = "login"
                    st.balloons()
                    st.rerun()
                else:
                    st.error(result["message"])
                    
            except Exception as e:
                st.error(f"Registration failed: {str(e)}")

def show_auth_page():
    """Display authentication page"""
    init_session_state()
    
    # Header
    st.markdown('<div class="main-header">🐶 Bulldog Buddy</div>', unsafe_allow_html=True)
    st.markdown('<div class="tagline">Your Smart Campus Assistant</div>', unsafe_allow_html=True)
    
    # Create centered columns for the form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Show appropriate form based on mode
        if st.session_state.auth_mode == "login":
            show_login_form()
        else:
            show_register_form()
        
        # Features section
        st.markdown("---")
        st.markdown("### 🌟 What Bulldog Buddy offers:")
        
        features_col1, features_col2 = st.columns(2)
        
        with features_col1:
            st.markdown("""
            - 🎯 **Smart Q&A** - Ask about courses, schedules, policies
            - 📚 **Academic Help** - Study tips and resources  
            - 🗺️ **Campus Guide** - Directions and locations
            """)
        
        with features_col2:
            st.markdown("""
            - 🍕 **Dining Info** - Meal plans and restaurant hours
            - 📅 **Events** - Campus activities and important dates
            - 💬 **24/7 Support** - Always here to help!
            """)

def logout():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.clear()  # Clear all session state
    st.success("You've been logged out successfully! 👋")
    st.rerun()

def show_user_info():
    """Display user information in sidebar"""
    if st.session_state.authenticated and st.session_state.user:
        user = st.session_state.user
        
        # Get user settings (including profile icon)
        user_settings = st.session_state.get("user_settings", {})
        profile_icon = user_settings.get("profile_icon", "🐶")
        
        with st.sidebar:
            # Profile section with icon
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #2E405715, #6C757D15); border-radius: 10px; margin-bottom: 1rem;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">{profile_icon}</div>
                <strong style="font-size: 1.1rem;">{user['first_name']} {user['last_name']}</strong><br>
                <span style="color: #6C757D; font-size: 0.9rem;">@{user['username']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if user.get('student_id'):
                st.info(f"🎓 Student ID: {user['student_id']}")
            
            st.info(f"🏷️ Role: {user['role'].title()}")
            
            # Settings and logout buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⚙️ Settings", use_container_width=True):
                    st.session_state.show_settings = True
                    st.rerun()
            with col2:
                if st.button("🚪 Logout", use_container_width=True):
                    logout()
            
            st.markdown("---")

def require_auth():
    """Decorator function to require authentication"""
    if not st.session_state.get("authenticated", False):
        show_auth_page()
        return False
    return True