import psycopg2
from psycopg2.extras import RealDictCursor

def add_personalization_columns():
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
        
        with conn.cursor() as cur:
            print("🎨 Adding personalization settings columns...")
            
            # Check current table structure
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY column_name;
            """)
            existing_columns = [row['column_name'] for row in cur.fetchall()]
            print(f"📊 Current columns: {len(existing_columns)}")
            
            # Add personalization columns one by one
            new_columns = [
                ("profile_icon", "VARCHAR(10) DEFAULT '🐶'"),
                ("color_theme", "VARCHAR(50) DEFAULT 'university'"),
                ("personality_type", "VARCHAR(50) DEFAULT 'friendly'"),
                ("response_length", "VARCHAR(20) DEFAULT 'moderate'"),
                ("custom_instructions", "TEXT DEFAULT ''"),
                ("notifications_enabled", "BOOLEAN DEFAULT true")
            ]
            
            added_columns = 0
            for col_name, col_def in new_columns:
                if col_name not in existing_columns:
                    try:
                        cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
                        print(f"   ✅ Added {col_name}")
                        added_columns += 1
                    except Exception as e:
                        print(f"   ❌ Failed to add {col_name}: {e}")
                else:
                    print(f"   ⚠️  Column {col_name} already exists")
            
            # Update existing users with defaults where NULL
            cur.execute("""
                UPDATE users 
                SET profile_icon = COALESCE(profile_icon, '🐶'),
                    color_theme = COALESCE(color_theme, 'university'),
                    personality_type = COALESCE(personality_type, 'friendly'),
                    response_length = COALESCE(response_length, 'moderate'),
                    custom_instructions = COALESCE(custom_instructions, ''),
                    notifications_enabled = COALESCE(notifications_enabled, true)
                WHERE profile_icon IS NULL OR color_theme IS NULL OR personality_type IS NULL;
            """)
            
            affected_rows = cur.rowcount
            conn.commit()
            
            print(f"✅ Added {added_columns} new columns")
            print(f"✅ Updated {affected_rows} users with default settings")
            
            # Show final column count
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY column_name;
            """)
            final_columns = cur.fetchall()
            print(f"📊 Final column count: {len(final_columns)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_personalization_columns()