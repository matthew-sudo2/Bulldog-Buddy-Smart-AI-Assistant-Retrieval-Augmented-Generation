#!/usr/bin/env python3

from core.database import BulldogBuddyDatabase

def check_users():
    db = BulldogBuddyDatabase()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, username, email FROM users LIMIT 5')
            users = cur.fetchall()
            print('Users in database:')
            for user in users:
                print(f"  ID: {user['id']}, Username: {user['username']}, Email: {user['email']}")
            if not users:
                print('No users found in database')
                    
    finally:
        db.return_connection(conn)

if __name__ == "__main__":
    check_users()