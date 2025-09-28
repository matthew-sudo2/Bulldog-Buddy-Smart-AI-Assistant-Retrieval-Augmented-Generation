"""
Bulldog Buddy Database Connection Class
PostgreSQL + pgvector integration for RAG system
"""

import os
import json
import logging
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BulldogBuddyDatabase:
    """
    Database connection and operations class for Bulldog Buddy RAG system
    """
    
    def __init__(self):
        """Initialize database connection pool"""
        self.database_url = os.getenv('DATABASE_URL')
        self.dimension = int(os.getenv('PGVECTOR_DIMENSION', 768))
        self.pool_size = int(os.getenv('DB_POOL_SIZE', 10))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', 20))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', 30))
        
        # Initialize connection pool
        self._init_connection_pool()
        
        # Test connection
        self._test_connection()
    
    def _init_connection_pool(self):
        """Initialize threaded connection pool"""
        try:
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size + self.max_overflow,
                dsn=self.database_url
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _test_connection(self):
        """Test database connection and pgvector extension"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                # Test basic connection
                cur.execute("SELECT version();")
                version = cur.fetchone()['version']
                logger.info(f"Connected to: {version[:50]}...")
                
                # Test pgvector extension
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');")
                has_pgvector = cur.fetchone()['exists']
                if has_pgvector:
                    logger.info("✅ pgvector extension is available")
                else:
                    logger.error("❌ pgvector extension not found")
                    raise Exception("pgvector extension is required")
                
                # Test schema
                cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
                table_count = cur.fetchone()['count']
                logger.info(f"Database schema loaded with {table_count} tables")
                
            self.return_connection(conn)
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool"""
        try:
            conn = self.pool.getconn()
            conn.cursor_factory = RealDictCursor
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        """
        Execute a query and return results
        Used by conversation_history.py and other modules
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params)
                
                if fetch:
                    # For SELECT queries or queries with RETURNING clause
                    result = cur.fetchall()
                    # Check if this was a modifying query (INSERT, UPDATE, DELETE)
                    if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                        conn.commit()
                    return result
                else:
                    # For INSERT, UPDATE, DELETE queries without RETURNING
                    conn.commit()
                    return True
                    
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Query execution failed: {e}")
            return None if fetch else False
            
        finally:
            if conn:
                self.return_connection(conn)
    
    def close_all_connections(self):
        """Close all connections in pool"""
        try:
            self.pool.closeall()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
    
    # User Management
    def create_or_update_user_session(self, session_id: str, preferred_model: str = 'gemma3') -> int:
        """Create new user session or update existing one"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (session_id, preferred_model, last_active, total_queries)
                    VALUES (%s, %s, NOW(), 1)
                    ON CONFLICT (session_id) 
                    DO UPDATE SET 
                        last_active = NOW(),
                        total_queries = users.total_queries + 1,
                        preferred_model = EXCLUDED.preferred_model
                    RETURNING id, total_queries
                """, (session_id, preferred_model))
                
                result = cur.fetchone()
                conn.commit()
                
                logger.info(f"User session {session_id} updated. Total queries: {result['total_queries']}")
                return result['id']
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating/updating user session: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_user_by_session(self, session_id: str) -> Optional[Dict]:
        """Get user information by session ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, session_id, preferred_model, total_queries, created_at, last_active
                    FROM users 
                    WHERE session_id = %s
                """, (session_id,))
                
                return cur.fetchone()
                
        except Exception as e:
            logger.error(f"Error getting user by session: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    # Authentication Methods
    def register_user(self, email: str, username: str, password: str, 
                     first_name: str, last_name: str, student_id: str = None) -> Dict:
        """Register a new user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Check if email or username already exists
                cur.execute("""
                    SELECT id FROM users 
                    WHERE email = %s OR username = %s
                """, (email, username))
                
                if cur.fetchone():
                    return {"success": False, "message": "Email or username already exists"}
                
                # Generate session ID
                session_id = str(uuid.uuid4())
                
                # Insert new user (password will be hashed by database function)
                cur.execute("""
                    INSERT INTO users (session_id, email, username, password_hash, 
                                     first_name, last_name, student_id, role, is_verified, is_active)
                    VALUES (%s, %s, %s, hash_password(%s), %s, %s, %s, 'student', false, true)
                    RETURNING id, session_id, email, username, first_name, last_name, role
                """, (session_id, email, username, password, first_name, last_name, student_id))
                
                user_data = cur.fetchone()
                conn.commit()
                
                logger.info(f"User registered successfully: {email}")
                return {
                    "success": True, 
                    "message": "User registered successfully",
                    "user": dict(user_data)
                }
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registering user: {e}")
            return {"success": False, "message": "Registration failed. Please try again."}
        finally:
            self.return_connection(conn)
    
    def authenticate_user(self, login: str, password: str) -> Dict:
        """Authenticate user by email/username and password"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Find user by email or username
                cur.execute("""
                    SELECT id, session_id, email, username, password_hash, 
                           first_name, last_name, role, is_active, is_verified
                    FROM users 
                    WHERE (email = %s OR username = %s) AND is_active = true
                """, (login, login))
                
                user = cur.fetchone()
                if not user:
                    return {"success": False, "message": "User not found"}
                
                # Verify password using database function
                cur.execute("""
                    SELECT verify_password(%s, %s) as password_valid
                """, (password, user['password_hash']))
                
                password_check = cur.fetchone()
                
                if password_check['password_valid']:
                    # Update last active timestamp
                    cur.execute("""
                        UPDATE users 
                        SET last_active = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (user['id'],))
                    conn.commit()
                    
                    # Remove password_hash from returned data
                    user_data = dict(user)
                    del user_data['password_hash']
                    
                    logger.info(f"User authenticated successfully: {user['email']}")
                    return {
                        "success": True,
                        "message": "Login successful",
                        "user": user_data
                    }
                else:
                    return {"success": False, "message": "Invalid password"}
                    
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {"success": False, "message": "Authentication failed. Please try again."}
        finally:
            self.return_connection(conn)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by user ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, session_id, email, username, first_name, last_name, 
                           role, student_id, is_active, is_verified, created_at, last_active,
                           preferred_model, total_queries
                    FROM users 
                    WHERE id = %s AND is_active = true
                """, (user_id,))
                
                return cur.fetchone()
                
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def update_user_profile(self, user_id: int, **kwargs) -> Dict:
        """Update user profile information"""
        conn = self.get_connection()
        try:
            # Build dynamic update query
            allowed_fields = ['first_name', 'last_name', 'student_id', 'preferred_model']
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    update_fields.append(f"{field} = %s")
                    values.append(value)
            
            if not update_fields:
                return {"success": False, "message": "No valid fields to update"}
            
            values.append(user_id)
            query = f"""
                UPDATE users 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, email, username, first_name, last_name, role, student_id, preferred_model
            """
            
            with conn.cursor() as cur:
                cur.execute(query, values)
                updated_user = cur.fetchone()
                conn.commit()
                
                if updated_user:
                    return {
                        "success": True,
                        "message": "Profile updated successfully",
                        "user": dict(updated_user)
                    }
                else:
                    return {"success": False, "message": "User not found"}
                    
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating user profile: {e}")
            return {"success": False, "message": "Update failed. Please try again."}
        finally:
            self.return_connection(conn)
    
    # Knowledge Base Operations
    def add_knowledge_document(self, section: str, category: str, title: str, 
                             content: str, embedding: np.ndarray, 
                             metadata: Optional[Dict] = None, 
                             source_file: Optional[str] = None) -> int:
        """Add document to knowledge base"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO knowledge_base (section, category, title, content, embedding, metadata, source_file)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (section, category, title, content, embedding.tolist(), Json(metadata), source_file))
                
                doc_id = cur.fetchone()['id']
                conn.commit()
                
                logger.info(f"Added knowledge document: {title} (ID: {doc_id})")
                return doc_id
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding knowledge document: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def search_knowledge_base(self, query_embedding: np.ndarray, 
                            category: Optional[str] = None,
                            similarity_threshold: float = 0.70,
                            max_results: int = 5) -> List[Dict]:
        """Search knowledge base using vector similarity"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                if category:
                    cur.execute("""
                        SELECT * FROM search_knowledge_base(%s::vector(768), %s, %s, %s)
                    """, (query_embedding.tolist(), category, similarity_threshold, max_results))
                else:
                    cur.execute("""
                        SELECT * FROM search_knowledge_base(%s::vector(768), NULL, %s, %s)
                    """, (query_embedding.tolist(), similarity_threshold, max_results))
                
                results = cur.fetchall()
                logger.info(f"Found {len(results)} relevant documents")
                return results
                
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    def get_knowledge_by_category(self, category: str, limit: int = 100) -> List[Dict]:
        """Get all knowledge documents by category"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, section, category, title, content, metadata, created_at
                    FROM knowledge_base 
                    WHERE category = %s 
                    ORDER BY section, created_at
                    LIMIT %s
                """, (category, limit))
                
                return cur.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting knowledge by category: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    # Conversation Management
    def save_conversation(self, user_id: int, session_id: str, 
                         message_history: List[Dict], model_used: str) -> int:
        """Save or update conversation with message history limit"""
        conn = self.get_connection()
        try:
            # Limit to last 10 messages
            limited_history = message_history[-10:] if len(message_history) > 10 else message_history
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO conversations (user_id, session_id, message_history, model_used, total_messages, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id)
                    DO UPDATE SET 
                        message_history = EXCLUDED.message_history,
                        model_used = EXCLUDED.model_used,
                        total_messages = EXCLUDED.total_messages,
                        updated_at = NOW()
                    RETURNING id
                """, (user_id, session_id, Json(limited_history), model_used, len(message_history)))
                
                conv_id = cur.fetchone()['id']
                conn.commit()
                
                logger.info(f"Saved conversation for session {session_id} with {len(limited_history)} messages")
                return conv_id
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving conversation: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def get_conversation_history(self, session_id: str) -> Optional[List[Dict]]:
        """Get conversation history for session"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT message_history, model_used, updated_at
                    FROM conversations 
                    WHERE session_id = %s
                """, (session_id,))
                
                result = cur.fetchone()
                if result:
                    return result['message_history']
                return []
                
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    # Query Logging
    def log_query(self, user_id: int, session_id: str, question: str, 
                  query_type: str, confidence_score: float, model_used: str,
                  response_sources: List[int], response_time_ms: int) -> int:
        """Log user query for analytics"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO query_logs 
                    (user_id, session_id, user_question, query_type, confidence_score, 
                     model_used, response_sources, response_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, session_id, question, query_type, confidence_score, 
                      model_used, response_sources, response_time_ms))
                
                log_id = cur.fetchone()['id']
                conn.commit()
                
                return log_id
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging query: {e}")
            return 0
        finally:
            self.return_connection(conn)
    
    def get_user_analytics(self, session_id: str) -> Dict:
        """Get user analytics and statistics"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        u.total_queries,
                        u.preferred_model,
                        u.created_at,
                        u.last_active,
                        COUNT(DISTINCT ql.query_type) as query_types_used,
                        AVG(ql.confidence_score) as avg_confidence,
                        AVG(ql.response_time_ms) as avg_response_time
                    FROM users u
                    LEFT JOIN query_logs ql ON u.id = ql.user_id
                    WHERE u.session_id = %s
                    GROUP BY u.id, u.total_queries, u.preferred_model, u.created_at, u.last_active
                """, (session_id,))
                
                return cur.fetchone() or {}
                
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}
        finally:
            self.return_connection(conn)
    
    # Financial Information
    def get_current_tuition_rates(self) -> List[Dict]:
        """Get current active tuition rates"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM current_tuition_rates")
                return cur.fetchall()
                
        except Exception as e:
            logger.error(f"Error getting tuition rates: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    # System Configuration
    def get_system_config(self, config_key: str) -> Any:
        """Get system configuration value"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT config_value FROM system_config WHERE config_key = %s
                """, (config_key,))
                
                result = cur.fetchone()
                return result['config_value'] if result else None
                
        except Exception as e:
            logger.error(f"Error getting system config: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def update_system_config(self, config_key: str, config_value: Any) -> bool:
        """Update system configuration"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE system_config 
                    SET config_value = %s, updated_at = NOW()
                    WHERE config_key = %s
                """, (Json(config_value), config_key))
                
                conn.commit()
                return cur.rowcount > 0
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating system config: {e}")
            return False
        finally:
            self.return_connection(conn)
    
    # Maintenance Functions
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old conversations and logs"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Clean old conversations
                cur.execute("""
                    DELETE FROM conversations 
                    WHERE updated_at < NOW() - INTERVAL '%s days'
                """, (days_old,))
                conversations_deleted = cur.rowcount
                
                # Clean old query logs (keep more for analytics)
                cur.execute("""
                    DELETE FROM query_logs 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """, (days_old * 3,))  # Keep logs 3x longer
                logs_deleted = cur.rowcount
                
                conn.commit()
                
                result = {
                    'conversations_deleted': conversations_deleted,
                    'logs_deleted': logs_deleted
                }
                
                logger.info(f"Cleanup completed: {result}")
                return result
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during cleanup: {e}")
            return {'conversations_deleted': 0, 'logs_deleted': 0}
        finally:
            self.return_connection(conn)

# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize database
        db = BulldogBuddyDatabase()
        
        # Test user session
        user_id = db.create_or_update_user_session("test_session_123", "gemma3")
        print(f"Created user session with ID: {user_id}")
        
        # Test getting tuition rates
        rates = db.get_current_tuition_rates()
        print(f"Current tuition rates: {len(rates)} levels available")
        
        # Test system config
        max_history = db.get_system_config("max_conversation_history")
        print(f"Max conversation history: {max_history}")
        
        # Test user analytics
        analytics = db.get_user_analytics("test_session_123")
        print(f"User analytics: {analytics}")
        
        print("✅ Database connection and operations test successful!")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    finally:
        if 'db' in locals():
            db.close_all_connections()