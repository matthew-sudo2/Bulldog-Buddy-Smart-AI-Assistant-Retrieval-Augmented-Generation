"""
Migration Script: Add profile_icon column to users table
Created: 2025-10-10
Purpose: Add profile icon personalization support
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

def main():
    """Add profile_icon column to users table"""
    db = BulldogBuddyDatabase()
    
    print("📝 Adding profile_icon column to users table...")
    
    # Add profile_icon column
    db.execute_query(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_icon VARCHAR(10) DEFAULT '🐶'", 
        fetch=False
    )
    
    print("✅ profile_icon column added successfully!")
    
    # Verify
    result = db.execute_query(
        """SELECT column_name, data_type, column_default 
           FROM information_schema.columns 
           WHERE table_name = 'users' AND column_name = 'profile_icon'""",
        fetch=True
    )
    
    if result:
        print(f"✅ Verified: {result[0]['column_name']} column exists")
        print(f"   Type: {result[0]['data_type']}")
        print(f"   Default: {result[0]['column_default']}")
    else:
        print("❌ Column not found")

if __name__ == "__main__":
    main()
