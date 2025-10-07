#!/usr/bin/env python3
"""
Check database directly for session and messages
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

def check_session_and_messages():
    db = BulldogBuddyDatabase()
    
    session_uuid = '42ef380e-c239-4e1a-a274-d2057b3ec674'
    
    # Check if session exists
    session_query = 'SELECT id, session_uuid, title, user_id FROM conversation_sessions WHERE session_uuid = %s'
    session_result = db.execute_query(session_query, (session_uuid,), fetch=True)
    print('Session info:', session_result)
    
    if session_result:
        session_id = session_result[0]['id']
        print(f'Session internal ID: {session_id}')
        print(f'User ID: {session_result[0]["user_id"]}')
        print(f'Title: {session_result[0]["title"]}')
        
        # Check messages for this session
        msg_query = 'SELECT * FROM conversation_messages WHERE session_id = %s'
        msg_result = db.execute_query(msg_query, (session_id,), fetch=True)
        print(f'Messages in this session: {len(msg_result)}')
        for i, msg in enumerate(msg_result):
            print(f'  {i+1}. {msg["message_role"]}: {msg["content"][:50]}...')
    else:
        print('Session not found!')

if __name__ == "__main__":
    check_session_and_messages()