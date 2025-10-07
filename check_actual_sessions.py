#!/usr/bin/env python3
"""
Check what conversation sessions actually exist for user 1
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

def check_actual_sessions():
    db = BulldogBuddyDatabase()
    
    # Get all sessions for user 1
    query = '''
    SELECT cs.session_uuid, cs.title, cs.created_at, 
           COUNT(cm.id) as message_count
    FROM conversation_sessions cs
    LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
    WHERE cs.user_id = 1
    GROUP BY cs.id, cs.session_uuid, cs.title, cs.created_at
    ORDER BY cs.created_at DESC
    '''
    results = db.execute_query(query, fetch=True)
    print(f'Found {len(results)} sessions for user 1:')
    for session in results:
        uuid_short = session["session_uuid"][:8]
        title = session["title"]
        msg_count = session["message_count"]
        print(f'- {uuid_short}... "{title}" ({msg_count} messages)')
        
        # If this session has messages, show the first message
        if msg_count > 0:
            msg_query = '''
            SELECT cm.message_role, cm.content
            FROM conversation_messages cm
            JOIN conversation_sessions cs ON cm.session_id = cs.id
            WHERE cs.session_uuid = %s
            ORDER BY cm.created_at ASC
            LIMIT 1
            '''
            msg_result = db.execute_query(msg_query, (session["session_uuid"],), fetch=True)
            if msg_result:
                first_msg = msg_result[0]
                print(f'  First message: {first_msg["message_role"]}: {first_msg["content"][:60]}...')

if __name__ == "__main__":
    check_actual_sessions()