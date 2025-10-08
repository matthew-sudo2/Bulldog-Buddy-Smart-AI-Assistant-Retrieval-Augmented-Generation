#!/usr/bin/env python3
"""
Fix Missing Conversation Tables
Adds conversation_sessions and conversation_messages tables to the database
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

def run_migration():
    """Run the conversation tables migration"""
    print("🔧 Fixing conversation tables...")
    print("="*60)
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="bulldog_buddy",
            user="postgres",
            password="bulldog_buddy_password_2025",
            cursor_factory=RealDictCursor
        )
        
        # Read SQL migration file
        sql_file = Path(__file__).parent / "add_conversation_tables.sql"
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Execute migration
        with conn.cursor() as cur:
            print("📊 Creating conversation tables...")
            cur.execute(sql_script)
            conn.commit()
            
        print("\n✅ Migration completed successfully!")
        print("\nTables created:")
        print("  ✓ conversation_sessions")
        print("  ✓ conversation_messages")
        print("  ✓ user_context")
        print("\n✅ Indexes created for performance")
        print("✅ Triggers created for auto-updates")
        print("✅ Personalization columns added to users table")
        print("\n🐶 You can now create conversations without errors!")
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        print(f"   Code: {e.pgcode}")
        if conn:
            conn.rollback()
    except FileNotFoundError:
        print(f"\n❌ SQL file not found: {sql_file}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("\n📡 Database connection closed")

if __name__ == "__main__":
    run_migration()
