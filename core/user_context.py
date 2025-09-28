"""
Enhanced User Context System for ChatGPT-like memory
Stores and retrieves user information, preferences, and important context
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
try:
    from .database import BulldogBuddyDatabase
except ImportError:
    from database import BulldogBuddyDatabase
import logging

logger = logging.getLogger(__name__)

class UserContextManager:
    """
    Manages user context information like ChatGPT
    Stores personal details, preferences, and conversation context
    """
    
    def __init__(self):
        self.db = BulldogBuddyDatabase()
        self._ensure_context_table()
    
    def _ensure_context_table(self):
        """Create user_context table if it doesn't exist"""
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_context (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        context_key VARCHAR(100) NOT NULL,
                        context_value TEXT,
                        context_type VARCHAR(50) DEFAULT 'info',
                        confidence FLOAT DEFAULT 1.0,
                        source VARCHAR(100) DEFAULT 'conversation',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, context_key)
                    );
                """)
                
                # Create index for faster lookups
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_context_user_id 
                    ON user_context(user_id);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_context_type 
                    ON user_context(user_id, context_type);
                """)
                
                conn.commit()
                
            self.db.return_connection(conn)
            logger.info("✅ User context table ensured")
            
        except Exception as e:
            logger.error(f"Error creating user context table: {e}")
    
    def extract_user_info(self, message: str, user_id: int) -> Dict[str, Any]:
        """
        Extract user information from a message using NLP patterns
        Similar to how ChatGPT remembers user details
        """
        extracted_info = {}
        
        # Pattern matching for common user info
        patterns = {
            'name': [
                r"(?:my name is|i'm|i am|call me|i'm called)\s+([a-zA-Z]+)",
                r"(?:i'm|i am)\s+([a-zA-Z]+)",
            ],
            'age': [
                r"(?:i'm|i am|my age is)\s+(\d+)\s*(?:years?\s*old)?",
                r"(\d+)\s*(?:years?\s*old)",
            ],
            'year_level': [
                r"(?:i'm|i am|i'm in)\s+(?:a\s+)?(\d+)(?:st|nd|rd|th)?\s*year",
                r"(?:year|grade)\s*(\d+)",
                r"(?:freshman|sophomore|junior|senior)",
            ],
            'major': [
                r"(?:i'm studying|my major is|i study|i'm majoring in)\s+([^.!?]+)",
                r"(?:computer science|engineering|business|psychology|biology|chemistry|physics|mathematics|english|history)",
            ],
            'location': [
                r"(?:i live in|i'm from|i'm in|my location is)\s+([^.!?]+)",
                r"(?:from|in)\s+([A-Z][a-zA-Z\s]+)",
            ],
            'interests': [
                r"(?:i like|i love|i enjoy|i'm interested in)\s+([^.!?]+)",
                r"(?:my hobbies are|my interests include)\s+([^.!?]+)",
            ],
            'goals': [
                r"(?:i want to|i plan to|my goal is|i hope to)\s+([^.!?]+)",
                r"(?:planning to|hoping to|trying to)\s+([^.!?]+)",
            ]
        }
        
        message_lower = message.lower()
        
        for info_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                if matches:
                    value = matches[0].strip()
                    if len(value) > 1:  # Avoid single characters
                        extracted_info[info_type] = {
                            'value': value,
                            'confidence': 0.8,  # Base confidence
                            'pattern': pattern
                        }
                        break
        
        # Store extracted information
        for info_type, info_data in extracted_info.items():
            self.store_user_context(
                user_id=user_id,
                context_key=info_type,
                context_value=info_data['value'],
                context_type='personal_info',
                confidence=info_data['confidence'],
                source='conversation_extraction'
            )
        
        return extracted_info
    
    def store_user_context(self, user_id: int, context_key: str, context_value: str, 
                          context_type: str = 'info', confidence: float = 1.0, 
                          source: str = 'conversation') -> bool:
        """Store or update user context information"""
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_context (user_id, context_key, context_value, context_type, confidence, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, context_key) 
                    DO UPDATE SET 
                        context_value = EXCLUDED.context_value,
                        confidence = EXCLUDED.confidence,
                        source = EXCLUDED.source,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, context_key, context_value, context_type, confidence, source))
                
                conn.commit()
                
            self.db.return_connection(conn)
            logger.info(f"Stored context for user {user_id}: {context_key} = {context_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing user context: {e}")
            return False
    
    def get_user_context(self, user_id: int, context_key: Optional[str] = None) -> Dict[str, Any]:
        """Get user context information"""
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                if context_key:
                    cur.execute("""
                        SELECT context_key, context_value, context_type, confidence, source, updated_at
                        FROM user_context 
                        WHERE user_id = %s AND context_key = %s
                    """, (user_id, context_key))
                    
                    result = cur.fetchone()
                    if result:
                        return {
                            'key': result['context_key'],
                            'value': result['context_value'],
                            'type': result['context_type'],
                            'confidence': result['confidence'],
                            'source': result['source'],
                            'updated_at': result['updated_at']
                        }
                else:
                    cur.execute("""
                        SELECT context_key, context_value, context_type, confidence, source, updated_at
                        FROM user_context 
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                    """, (user_id,))
                    
                    results = cur.fetchall()
                    context_dict = {}
                    
                    for row in results:
                        context_dict[row['context_key']] = {
                            'value': row['context_value'],
                            'type': row['context_type'],
                            'confidence': row['confidence'],
                            'source': row['source'],
                            'updated_at': row['updated_at']
                        }
                    
                    return context_dict
                    
            self.db.return_connection(conn)
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}
        
        return {}
    
    def build_context_prompt(self, user_id: int) -> str:
        """
        Build a context prompt similar to ChatGPT's memory
        """
        context_data = self.get_user_context(user_id)
        
        if not context_data:
            return ""
        
        # Group context by type
        personal_info = {}
        preferences = {}
        goals = {}
        other = {}
        
        for key, data in context_data.items():
            ctx_type = data['type']
            value = data['value']
            
            if ctx_type == 'personal_info':
                personal_info[key] = value
            elif ctx_type == 'preference':
                preferences[key] = value
            elif ctx_type == 'goal':
                goals[key] = value
            else:
                other[key] = value
        
        # Build context prompt
        context_parts = []
        
        if personal_info:
            context_parts.append("Personal Information:")
            for key, value in personal_info.items():
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        if preferences:
            context_parts.append("\\nPreferences:")
            for key, value in preferences.items():
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        if goals:
            context_parts.append("\\nGoals:")
            for key, value in goals.items():
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        if other:
            context_parts.append("\\nOther Context:")
            for key, value in other.items():
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        if context_parts:
            full_context = "\\n".join(context_parts)
            return f"""
IMPORTANT USER CONTEXT (Remember this information about the user):
{full_context}

Please use this information to personalize your responses. Reference their name when appropriate, remember their goals, interests, and preferences. Be conversational and remember what they've told you about themselves.
"""
        
        return ""
    
    def analyze_follow_up_context(self, message: str, previous_response: str, user_id: int) -> str:
        """
        Analyze follow-up questions and maintain context like ChatGPT
        """
        message_lower = message.lower()
        
        # Common follow-up patterns
        follow_up_indicators = [
            "what about", "how about", "and what", "can you also", "also",
            "additionally", "furthermore", "moreover", "besides",
            "what else", "anything else", "more information"
        ]
        
        pronoun_references = ["it", "that", "this", "they", "them", "he", "she"]
        
        context_hint = ""
        
        # Check for follow-up indicators
        if any(indicator in message_lower for indicator in follow_up_indicators):
            context_hint += "\\n[CONTEXT: This is a follow-up question related to the previous response]"
        
        # Check for pronoun references
        if any(pronoun in message_lower.split() for pronoun in pronoun_references):
            context_hint += "\\n[CONTEXT: The user is referring to something mentioned previously]"
        
        # Check for short questions (likely follow-ups)
        if len(message.split()) <= 5 and message.endswith('?'):
            context_hint += "\\n[CONTEXT: This appears to be a short follow-up question]"
        
        return context_hint
    
    def update_conversation_context(self, user_id: int, user_message: str, 
                                  assistant_response: str, conversation_history: List[Dict]) -> None:
        """
        Update context based on conversation like ChatGPT does
        """
        # Extract new user information
        extracted_info = self.extract_user_info(user_message, user_id)
        
        # Store conversation topics for better context
        if len(conversation_history) > 0:
            # Analyze conversation topic
            recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
            
            # Extract main topics from recent conversation
            topics = self._extract_conversation_topics(recent_messages)
            
            if topics:
                self.store_user_context(
                    user_id=user_id,
                    context_key=f"recent_topic_{datetime.now().strftime('%Y%m%d')}",
                    context_value=', '.join(topics),
                    context_type='conversation_topic',
                    confidence=0.7,
                    source='conversation_analysis'
                )
    
    def _extract_conversation_topics(self, messages: List[Dict]) -> List[str]:
        """Extract main topics from conversation messages"""
        # Simple topic extraction based on keywords
        topic_keywords = {
            'academics': ['study', 'course', 'class', 'exam', 'homework', 'assignment', 'grade', 'professor', 'teacher'],
            'university': ['university', 'college', 'campus', 'tuition', 'scholarship', 'enrollment', 'registration'],
            'career': ['job', 'career', 'internship', 'work', 'employment', 'salary', 'interview'],
            'personal': ['family', 'friend', 'relationship', 'hobby', 'interest', 'goal', 'plan'],
            'technology': ['computer', 'programming', 'software', 'app', 'website', 'AI', 'technology'],
            'health': ['health', 'exercise', 'diet', 'sleep', 'stress', 'mental', 'physical']
        }
        
        topics = []
        all_text = ' '.join([msg.get('content', '') for msg in messages]).lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in all_text for keyword in keywords):
                topics.append(topic)
        
        return topics[:3]  # Return max 3 topics
    
    def get_context_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of all user context for debugging/display"""
        context_data = self.get_user_context(user_id)
        
        summary = {
            'total_context_items': len(context_data),
            'personal_info_count': 0,
            'preference_count': 0,
            'goal_count': 0,
            'recent_topics': [],
            'last_updated': None
        }
        
        for key, data in context_data.items():
            ctx_type = data['type']
            
            if ctx_type == 'personal_info':
                summary['personal_info_count'] += 1
            elif ctx_type == 'preference':
                summary['preference_count'] += 1
            elif ctx_type == 'goal':
                summary['goal_count'] += 1
            elif ctx_type == 'conversation_topic':
                summary['recent_topics'].append(data['value'])
            
            # Track most recent update
            if not summary['last_updated'] or data['updated_at'] > summary['last_updated']:
                summary['last_updated'] = data['updated_at']
        
        return summary