#!/usr/bin/env python3

from core.database import BulldogBuddyDatabase

def check_messages():
    db = BulldogBuddyDatabase()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Check sessions with message counts
            cur.execute('''
                SELECT cs.session_uuid, cs.title, COUNT(cm.id) as message_count 
                FROM conversation_sessions cs 
                LEFT JOIN conversation_messages cm ON cs.id = cm.session_id 
                WHERE cs.user_id = 1 
                GROUP BY cs.session_uuid, cs.title 
                ORDER BY message_count DESC
            ''')
            sessions = cur.fetchall()
            print("Sessions with message counts:")
            for session in sessions:
                print(f"  UUID: {session['session_uuid']}, Title: {session['title']}, Messages: {session['message_count']}")
                    
    finally:
        db.return_connection(conn)

if __name__ == "__main__":
    check_messages()