#!/usr/bin/env python3
"""
Fix session_id constraint violation in users table
Addresses: error: duplicate key value violates unique constraint "users_session_id_key"
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase
from psycopg2.extras import RealDictCursor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def fix_session_id_constraint():
    """Update NULL session_id values in users table"""
    
    try:
        # Initialize database
        db = BulldogBuddyDatabase()
        logger.info("Database connection initialized")
        
        # Get connection
        conn = db.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check for users with NULL/empty session_id
                cur.execute("SELECT COUNT(*) as count FROM users WHERE session_id IS NULL OR session_id = ''")
                result = cur.fetchone()
                null_count = result['count'] if result else 0
                logger.info(f"Found {null_count} users with NULL/empty session_id")
                
                if null_count > 0:
                    # Update NULL session_ids
                    logger.info("Updating users with NULL/empty session_id...")
                    cur.execute("""
                        UPDATE users 
                        SET session_id = 'migrated_' || id || '_' || EXTRACT(epoch FROM NOW())::bigint || '_' || substr(md5(random()::text), 1, 8)
                        WHERE session_id IS NULL OR session_id = ''
                    """)
                    
                    updated_count = cur.rowcount
                    logger.info(f"Updated {updated_count} users")
                    
                    # Verify fix
                    cur.execute("SELECT COUNT(*) as count FROM users WHERE session_id IS NULL OR session_id = ''")
                    result = cur.fetchone()
                    remaining_null = result['count'] if result else 0
                    
                    if remaining_null == 0:
                        logger.info("✅ All users now have valid session_id values")
                    else:
                        logger.warning(f"⚠️  {remaining_null} users still have NULL session_id")
                        
                    # Show sample of updated users
                    cur.execute("""
                        SELECT id, session_id, email, username 
                        FROM users 
                        WHERE session_id LIKE 'migrated_%' 
                        ORDER BY id 
                        LIMIT 5
                    """)
                    updated_users = cur.fetchall()
                    
                    if updated_users:
                        logger.info("Sample of updated users:")
                        for user in updated_users:
                            logger.info(f"  ID: {user['id']}, Session: {user['session_id'][:30]}..., Email: {user['email']}, Username: {user['username']}")
                else:
                    logger.info("✅ No users with NULL session_id found")
                    
            # Commit changes
            conn.commit()
            logger.info("Changes committed successfully")
            
        finally:
            db.return_connection(conn)
            
    except Exception as e:
        logger.error(f"Error fixing session_id constraint: {e}")
        raise

if __name__ == "__main__":
    fix_session_id_constraint()
    logger.info("Session ID constraint fix completed")