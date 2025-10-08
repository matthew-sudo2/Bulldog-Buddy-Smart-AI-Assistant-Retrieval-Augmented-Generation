#!/usr/bin/env python3
"""
Migration script to add Google OAuth support to PostgreSQL users table
"""

import psycopg2
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

def run_migration():
    """Run the Google OAuth migration"""
    try:
        # Initialize database connection
        print("🔧 Connecting to PostgreSQL database...")
        db = BulldogBuddyDatabase()
        
        # Get a connection
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("📝 Running Google OAuth migration...")
        
        # Check if google_id column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'google_id'
            );
        """)
        
        result = cursor.fetchone()
        google_id_exists = result[0] if result else False
        
        if not google_id_exists:
            print("➕ Adding google_id column...")
            cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;")
            
            print("📋 Creating index for google_id...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);")
            
            print("✅ Google ID column added successfully")
        else:
            print("ℹ️  Google ID column already exists")
        
        # Make password_hash nullable
        print("🔄 Making password_hash nullable for OAuth users...")
        cursor.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;")
        
        # Add constraint to ensure either password or google_id exists
        print("🔒 Adding authentication method constraint...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'users_auth_method_check'
                ) THEN
                    ALTER TABLE users ADD CONSTRAINT users_auth_method_check 
                    CHECK (password_hash IS NOT NULL OR google_id IS NOT NULL);
                END IF;
            END $$;
        """)
        
        # Update session_id for existing users
        print("🔄 Updating session IDs for existing users...")
        cursor.execute("""
            UPDATE users 
            SET session_id = 'migrated_' || id::text || '_' || extract(epoch from now())::text
            WHERE session_id IS NULL OR session_id = '';
        """)
        
        # Commit changes
        conn.commit()
        
        print("✅ Migration completed successfully!")
        print("📊 Google OAuth support has been added to the users table")
        
        # Show current table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position;
        """)
        
        print("\n📋 Current users table structure:")
        for row in cursor.fetchall():
            nullable = "NULL" if row[2] == "YES" else "NOT NULL"
            print(f"  {row[0]}: {row[1]} ({nullable})")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            db.return_connection(conn)

if __name__ == "__main__":
    run_migration()