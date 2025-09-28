#!/usr/bin/env python3
"""Check user and conversation data consistency"""

from core.database import BulldogBuddyDatabase
from core.conversation_history import ConversationHistoryManager

def check_user_consistency():
    print("🔍 Checking User and Conversation Data Consistency...")
    
    db = BulldogBuddyDatabase()
    cm = ConversationHistoryManager()
    
    # Check users
    print("\n1. Users in database:")
    users = db.execute_query('SELECT id, session_id, username, email FROM users ORDER BY id')
    if users:
        for user in users:
            print(f"   User ID: {user['id']}, Session: {user['session_id']}, Username: {user['username']}, Email: {user['email']}")
    else:
        print("   No users found")
    
    # Check conversation sessions  
    print("\n2. All conversation sessions:")
    sessions = db.execute_query('SELECT id, user_id, session_uuid, title FROM conversation_sessions ORDER BY updated_at DESC')
    if sessions:
        for session in sessions:
            print(f"   Session: {session['session_uuid']}, User ID: {session['user_id']}, Title: '{session['title']}'")
    else:
        print("   No sessions found")
    
    # Check messages for each session
    print("\n3. Messages per session:")
    for session in sessions[:5] if sessions else []:  # Check first 5 sessions
        messages = db.execute_query('SELECT message_type, content FROM conversation_messages WHERE session_id = %s ORDER BY message_order', (session['id'],))
        print(f"   Session '{session['title']}' has {len(messages) if messages else 0} messages:")
        if messages:
            for msg in messages:
                content_preview = msg['content'][:50] + '...' if len(msg['content']) > 50 else msg['content']
                print(f"     [{msg['message_type']}] {content_preview}")
    
    # Test getting conversations for user ID 1 (which is used in tests)
    print("\n4. Testing conversation retrieval for User ID 1:")
    user_sessions = cm.get_user_sessions(1, limit=10)
    print(f"   Found {len(user_sessions)} sessions for User ID 1")
    for session in user_sessions:
        print(f"   - '{session['title']}' ({session['message_count']} messages)")
    
    print("\n🔍 Check Complete!")

if __name__ == "__main__":
    check_user_consistency()