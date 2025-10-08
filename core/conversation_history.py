"""
Conversation History Manager with Vector Search
Handles conversation sessions and message storage with pgvector
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
try:
    from .database import BulldogBuddyDatabase
except ImportError:
    from database import BulldogBuddyDatabase

# Check for sentence-transformers availability
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class ConversationHistoryManager:
    """
    Manages conversation history with vector search capabilities
    """
    
    def __init__(self):
        """Initialize conversation history manager"""
        self.db = BulldogBuddyDatabase()
        self.logger = logging.getLogger(__name__)
        
        # Initialize embedding model for conversation search
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dim = 384
                self.embedding_enabled = True
                self.logger.info("Sentence transformer model loaded for conversation embeddings")
            except Exception as e:
                self.logger.warning(f"Could not load embedding model: {e}")
                self.embedding_enabled = False
        else:
            self.logger.info("Sentence transformers not available - conversation search disabled")
            self.embedding_model = None
            self.embedding_dim = 384
            self.embedding_enabled = False
    
    def create_conversation_session(self, user_id: int, title: str = "New Conversation") -> Optional[str]:
        """
        Create a new conversation session
        Returns session UUID if successful
        """
        session_uuid = str(uuid.uuid4())
        
        try:
            query = """
                INSERT INTO conversation_sessions (user_id, session_uuid, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, session_uuid
            """
            
            now = datetime.now()
            result = self.db.execute_query(
                query, 
                (user_id, session_uuid, title, now, now),
                fetch=True
            )
            
            if result:
                self.logger.info(f"Created conversation session {session_uuid} for user {user_id}")
                return session_uuid
            else:
                self.logger.error("Failed to create conversation session")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating conversation session: {e}")
            return None
    
    def _get_session_id(self, session_uuid: str) -> Optional[int]:
        """Get internal session ID from UUID"""
        try:
            result = self.db.execute_query(
                "SELECT id FROM conversation_sessions WHERE session_uuid = %s",
                (session_uuid,),
                fetch=True
            )
            return result[0]['id'] if result else None
        except Exception as e:
            self.logger.error(f"Error getting session ID: {e}")
            return None
    
    def add_message_to_session(self, session_uuid: str, user_id: int, content: str, 
                              message_type: str, confidence_score: float = 0.0,
                              model_used: str = None, sources_used: List[str] = None) -> bool:
        """
        Add a message to a conversation session with vector embedding
        """
        try:
            # Get session ID
            session_id = self._get_session_id(session_uuid)
            if not session_id:
                self.logger.error(f"Session {session_uuid} not found")
                return False
            
            # Get next message order
            order_query = """
                SELECT COALESCE(MAX(message_order), 0) + 1 as next_order
                FROM conversation_messages 
                WHERE session_id = %s
            """
            order_result = self.db.execute_query(order_query, (session_id,), fetch=True)
            message_order = order_result[0]['next_order'] if order_result else 1
            
            # Generate embedding if enabled
            embedding = None
            if self.embedding_enabled and content.strip():
                try:
                    embedding_array = self.embedding_model.encode(content)
                    embedding = embedding_array.tolist()
                except Exception as e:
                    self.logger.warning(f"Could not generate embedding: {e}")
            
            # Insert message
            insert_query = """
                INSERT INTO conversation_messages (
                    session_id, user_id, message_order, message_type, message_role, content,
                    embedding, confidence_score, model_used, sources_used, 
                    metadata, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            import json
            
            metadata = {
                "character_count": len(content),
                "word_count": len(content.split()),
                "has_embedding": embedding is not None
            }
            
            success = self.db.execute_query(
                insert_query,
                (
                    session_id, user_id, message_order, message_type, message_type, content,
                    embedding, confidence_score, model_used, sources_used or [],
                    json.dumps(metadata), datetime.now()
                ),
                fetch=False
            )
            
            if success:
                # Update session title if this is the first user message and title is generic
                if message_type == 'user' and message_order == 1:
                    self._update_session_title(session_id, content)
                
                self.logger.info(f"Added {message_type} message to session {session_uuid}")
                return True
            else:
                self.logger.error("Failed to insert message")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding message to session: {e}")
            return False
    
    def get_user_sessions(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user's conversation sessions with summary info
        """
        try:
            query = """
                SELECT 
                    cs.session_uuid,
                    cs.title,
                    cs.is_pinned,
                    cs.created_at,
                    cs.updated_at,
                    COUNT(cm.id) as message_count,
                    STRING_AGG(
                        CASE WHEN cm.message_order <= 2 THEN SUBSTRING(cm.content, 1, 100) END, 
                        ' | ' ORDER BY cm.message_order
                    ) as preview
                FROM conversation_sessions cs
                LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
                WHERE cs.user_id = %s
                GROUP BY cs.id, cs.session_uuid, cs.title, cs.is_pinned, cs.created_at, cs.updated_at
                ORDER BY cs.is_pinned DESC, cs.updated_at DESC
                LIMIT %s
            """
            
            results = self.db.execute_query(query, (user_id, limit), fetch=True)
            
            sessions = []
            for row in results:
                sessions.append({
                    'session_uuid': row['session_uuid'],
                    'title': row['title'],
                    'pinned': row['is_pinned'] or False,
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'message_count': row['message_count'],
                    'preview': row['preview'] or "No messages yet..."
                })
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Error getting user sessions: {e}")
            return []
    
    def get_session_messages(self, session_uuid: str, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all messages from a conversation session
        """
        try:
            query = """
                SELECT 
                    cm.content,
                    cm.message_role,
                    cm.metadata,
                    cm.created_at
                FROM conversation_messages cm
                JOIN conversation_sessions cs ON cm.session_id = cs.id
                WHERE cs.session_uuid = %s AND cs.user_id = %s
                ORDER BY cm.created_at ASC
            """
            
            results = self.db.execute_query(query, (session_uuid, user_id), fetch=True)
            
            messages = []
            for row in results:
                messages.append({
                    'content': row['content'],
                    'message_type': row['message_role'],  # Map message_role to message_type for frontend
                    'role': row['message_role'],  # Also include role for compatibility
                    'metadata': row['metadata'] or {},
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting session messages: {e}")
            return []
    
    def search_conversations(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search through user's conversations using vector similarity
        """
        if not self.embedding_enabled:
            return []
            
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            search_query = """
                SELECT 
                    cs.session_uuid,
                    cs.title,
                    cm.id as message_id,
                    cm.content as message_content,
                    cm.message_type,
                    cm.embedding <-> %s::vector as similarity_score,
                    cm.created_at
                FROM conversation_messages cm
                JOIN conversation_sessions cs ON cm.session_id = cs.id
                WHERE cs.user_id = %s 
                    AND cm.embedding IS NOT NULL
                ORDER BY cm.embedding <-> %s::vector
                LIMIT %s
            """
            
            results = self.db.execute_query(
                search_query, 
                (query_embedding, user_id, query_embedding, limit),
                fetch=True
            )
            
            search_results = []
            for row in results:
                search_results.append({
                    'session_id': row['session_uuid'],
                    'session_title': row['title'],
                    'message_id': row['message_id'],
                    'message_content': row['message_content'],
                    'message_type': row['message_type'],
                    'similarity_score': float(row['similarity_score']),
                    'created_at': row['created_at']
                })
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Error searching conversation history: {e}")
            return []
    
    def pin_conversation(self, session_uuid: str, user_id: int, pinned: bool = True) -> bool:
        """
        Pin or unpin a conversation session
        """
        try:
            query = """
                UPDATE conversation_sessions 
                SET pinned = %s, updated_at = %s
                WHERE session_uuid = %s AND user_id = %s
            """
            
            success = self.db.execute_query(
                query, 
                (pinned, datetime.now(), session_uuid, user_id),
                fetch=False
            )
            
            if success:
                self.logger.info(f"{'Pinned' if pinned else 'Unpinned'} session {session_uuid}")
                return True
            else:
                self.logger.error(f"Failed to {'pin' if pinned else 'unpin'} session")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pinning conversation: {e}")
            return False
    
    def update_session_title(self, session_uuid: str, user_id: int, title: str) -> bool:
        """
        Update conversation session title
        """
        try:
            query = """
                UPDATE conversation_sessions 
                SET title = %s, updated_at = %s
                WHERE session_uuid = %s AND user_id = %s
            """
            
            success = self.db.execute_query(
                query, 
                (title, datetime.now(), session_uuid, user_id),
                fetch=False
            )
            
            if success:
                self.logger.info(f"Updated session {session_uuid} title to: {title}")
                return True
            else:
                self.logger.error("Failed to update session title")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating session title: {e}")
            return False
    
    def delete_conversation(self, session_uuid: str, user_id: int) -> bool:
        """
        Delete a conversation session and all its messages
        Returns True only if a row was actually deleted
        """
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                query = """
                    DELETE FROM conversation_sessions 
                    WHERE session_uuid = %s AND user_id = %s
                """
                cur.execute(query, (session_uuid, user_id))
                rows_deleted = cur.rowcount
                conn.commit()
                
                if rows_deleted > 0:
                    self.logger.info(f"✅ Deleted conversation {session_uuid} for user {user_id} ({rows_deleted} row(s))")
                    return True
                else:
                    self.logger.warning(f"⚠️ No conversation found with UUID {session_uuid} for user {user_id}")
                    return False
                    
        except Exception as e:
            conn.rollback()
            self.logger.error(f"❌ Error deleting conversation: {e}")
            return False
        finally:
            self.db.return_connection(conn)
    
    def cleanup_old_conversations(self, user_id: int, days_old: int = 90) -> int:
        """
        Clean up old unpinned conversations
        Returns number of conversations deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            query = """
                DELETE FROM conversation_sessions 
                WHERE user_id = %s 
                    AND pinned = FALSE 
                    AND updated_at < %s
                RETURNING session_uuid
            """
            
            results = self.db.execute_query(query, (user_id, cutoff_date), fetch=True)
            deleted_count = len(results) if results else 0
            
            self.logger.info(f"Cleaned up {deleted_count} old conversations for user {user_id}")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error during conversation cleanup: {e}")
            return 0
    
    def get_conversation_summary(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get summary information about a conversation
        """
        try:
            query = """
                SELECT 
                    cs.title,
                    cs.created_at,
                    cs.updated_at,
                    COUNT(cm.id) as message_count,
                    COUNT(CASE WHEN cm.message_type = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN cm.message_type = 'assistant' THEN 1 END) as assistant_messages
                FROM conversation_sessions cs
                LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
                WHERE cs.session_uuid = %s
                GROUP BY cs.id, cs.title, cs.created_at, cs.updated_at
            """
            
            result = self.db.execute_query(query, (session_uuid,), fetch=True)
            
            if result:
                row = result[0]
                return {
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'total_messages': row['message_count'],
                    'user_messages': row['user_messages'],
                    'assistant_messages': row['assistant_messages']
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting conversation summary: {e}")
            return None
    
    def get_recent_context(self, session_uuid: str, message_count: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent messages from a conversation for context
        """
        try:
            query = """
                SELECT 
                    cm.content,
                    cm.message_type,
                    cm.created_at
                FROM conversation_messages cm
                JOIN conversation_sessions cs ON cm.session_id = cs.id
                WHERE cs.session_uuid = %s
                ORDER BY cm.message_order DESC
                LIMIT %s
            """
            
            result = self.db.execute_query(query, (session_uuid, message_count), fetch=True)
            
            if result:
                return [dict(row) for row in reversed(result)]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting recent context: {e}")
            return []
    
    def get_conversation_insights(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get conversation insights and statistics for a user
        """
        try:
            # Get total sessions and messages
            stats_query = """
                SELECT 
                    COUNT(DISTINCT cs.id) as total_sessions,
                    COUNT(cm.id) as total_messages,
                    AVG(LENGTH(cm.content)) as avg_message_length,
                    MAX(cs.updated_at) as last_conversation
                FROM conversation_sessions cs
                LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
                WHERE cs.user_id = %s
            """
            
            result = self.db.execute_query(stats_query, (user_id,), fetch=True)
            
            if result and result[0]:
                row = result[0]
                return {
                    'total_sessions': int(row['total_sessions'] or 0),
                    'total_messages': int(row['total_messages'] or 0),
                    'avg_message_length': float(row['avg_message_length'] or 0),
                    'last_conversation': row['last_conversation']
                }
            else:
                return {
                    'total_sessions': 0,
                    'total_messages': 0,
                    'avg_message_length': 0,
                    'last_conversation': None
                }
                
        except Exception as e:
            self.logger.error(f"Error getting conversation insights: {e}")
            return None
    
    def _update_session_title(self, session_id: int, first_message: str):
        """
        Update session title based on first user message
        """
        try:
            # Generate a meaningful title from the first message
            title = first_message[:50].strip()
            if len(first_message) > 50:
                title += "..."
            
            query = "UPDATE conversation_sessions SET title = %s, updated_at = %s WHERE id = %s"
            self.db.execute_query(query, (title, datetime.now(), session_id), fetch=False)
            
        except Exception as e:
            self.logger.error(f"Error updating session title: {e}")