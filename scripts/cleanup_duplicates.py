#!/usr/bin/env python3
"""Clean up duplicate messages in the database"""

from core.conversation_history import ConversationHistoryManager
from core.database import BulldogBuddyDatabase

def cleanup_duplicate_messages():
    print("🧹 Cleaning up duplicate messages in database...")
    
    db = BulldogBuddyDatabase()
    cm = ConversationHistoryManager()
    
    # Get all sessions that might have duplicates
    all_sessions = db.execute_query("""
        SELECT cs.id, cs.session_uuid, cs.user_id, cs.title,
               COUNT(cm.id) as message_count
        FROM conversation_sessions cs
        LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
        GROUP BY cs.id, cs.session_uuid, cs.user_id, cs.title
        HAVING COUNT(cm.id) > 10  -- Focus on sessions with many messages
        ORDER BY COUNT(cm.id) DESC
    """)
    
    if not all_sessions:
        print("   No sessions with excessive messages found.")
        return
    
    print(f"\n   Found {len(all_sessions)} sessions with potentially duplicate messages:")
    
    total_removed = 0
    
    for session in all_sessions:
        session_id = session['id']
        session_uuid = session['session_uuid']
        user_id = session['user_id']
        title = session['title']
        message_count = session['message_count']
        
        print(f"\n   Processing: '{title}' ({message_count} messages)")
        
        # Get all messages for this session
        messages = db.execute_query("""
            SELECT id, message_type, content, message_order, created_at
            FROM conversation_messages 
            WHERE session_id = %s
            ORDER BY message_order, created_at
        """, (session_id,))
        
        if not messages:
            continue
        
        # Find duplicates (same content + message_type)
        unique_messages = []
        seen_combinations = set()
        duplicate_ids = []
        
        for msg in messages:
            combo = (msg['message_type'], msg['content'])
            if combo not in seen_combinations:
                unique_messages.append(msg)
                seen_combinations.add(combo)
            else:
                duplicate_ids.append(msg['id'])
        
        duplicates_found = len(duplicate_ids)
        if duplicates_found > 0:
            print(f"     Found {duplicates_found} duplicates to remove")
            
            # Remove duplicates from database
            for dup_id in duplicate_ids:
                success = db.execute_query("""
                    DELETE FROM conversation_messages WHERE id = %s
                """, (dup_id,), fetch=False)
                
                if success:
                    total_removed += 1
            
            print(f"     ✅ Removed {duplicates_found} duplicate messages")
            
            # Update message orders to be sequential
            for i, msg in enumerate(unique_messages, 1):
                db.execute_query("""
                    UPDATE conversation_messages 
                    SET message_order = %s
                    WHERE id = %s
                """, (i, msg['id']), fetch=False)
        else:
            print(f"     ✅ No duplicates found")
    
    print(f"\n🧹 Cleanup complete! Removed {total_removed} duplicate messages total.")
    
    # Verify cleanup
    print("\n   Verifying cleanup...")
    updated_sessions = db.execute_query("""
        SELECT cs.title, COUNT(cm.id) as message_count
        FROM conversation_sessions cs
        LEFT JOIN conversation_messages cm ON cs.id = cm.session_id
        WHERE cs.user_id = 5  -- User 5 had the most duplicates
        GROUP BY cs.id, cs.title
        ORDER BY COUNT(cm.id) DESC
    """)
    
    if updated_sessions:
        print("   User 5's sessions after cleanup:")
        for session in updated_sessions:
            print(f"     - '{session['title']}': {session['message_count']} messages")

if __name__ == "__main__":
    cleanup_duplicate_messages()