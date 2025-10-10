"""
Migration Script: Apply settings columns migration
Created: 2025-10-10
Purpose: Execute SQL migration to add user settings columns
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

def main():
    """Apply settings columns migration from SQL file"""
    db = BulldogBuddyDatabase()
    
    print("📝 Adding settings columns to users table...")
    
    # Get SQL file path (same directory as this script)
    sql_file = Path(__file__).parent / 'add_settings_columns.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return
    
    # Read and execute the SQL file
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_commands = f.read().split(';')
    
    print(f"📄 Loaded {len(sql_commands)} SQL commands from {sql_file.name}")
    
    for i, command in enumerate(sql_commands, 1):
        command = command.strip()
        if command and not command.startswith('--'):
            try:
                # Execute SELECT queries with fetch=True
                is_select = command.upper().startswith('SELECT')
                result = db.execute_query(command, fetch=is_select)
                
                if result:
                    print(f"\n✅ Command {i} executed successfully")
                    if is_select:
                        print("   Verification results:")
                        for row in result:
                            print(f"     {row}")
            except Exception as e:
                print(f"❌ Error executing command {i}: {e}")
                print(f"   Command: {command[:100]}...")
    
    print("\n✅ Settings columns migration completed!")
    print("💡 Run 'python scripts/debug/check_schema.py' to verify.")

if __name__ == "__main__":
    main()
