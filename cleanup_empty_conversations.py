"""
Cleanup script to delete empty 'New Conversation' entries
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

db = BulldogBuddyDatabase()

print("\n" + "="*70)
print("CLEANUP: DELETE EMPTY 'NEW CONVERSATION' ENTRIES")
print("="*70 + "\n")

# Find empty conversations
empty_convs = db.execute_query(
    """
    SELECT session_uuid, title, created_at
    FROM conversation_sessions 
    WHERE user_id = 7
      AND title = 'New Conversation'
      AND message_count = 0
    ORDER BY created_at DESC
    """,
    fetch=True
)

print(f"Found {len(empty_convs)} empty 'New Conversation' entries\n")

if len(empty_convs) == 0:
    print("✅ No empty conversations to delete!")
else:
    print("These conversations will be deleted:")
    print("-" * 70)
    for i, conv in enumerate(empty_convs, 1):
        created = conv['created_at'].strftime('%Y-%m-%d %H:%M:%S') if conv['created_at'] else 'Unknown'
        print(f"  {i}. {conv['session_uuid']} (created {created})")
    
    print("\n" + "="*70)
    response = input(f"Delete all {len(empty_convs)} empty conversations? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print("\n🗑️  Deleting empty conversations...")
        
        result = db.execute_query(
            """
            DELETE FROM conversation_sessions 
            WHERE user_id = 7
              AND title = 'New Conversation'
              AND message_count = 0
            """,
            fetch=False
        )
        
        if result:
            print(f"✅ Successfully deleted {len(empty_convs)} empty conversations!")
            
            # Verify
            remaining = db.execute_query(
                "SELECT COUNT(*) as count FROM conversation_sessions WHERE user_id = 7",
                fetch=True
            )
            print(f"📊 Remaining conversations for user 7: {remaining[0]['count']}")
        else:
            print("❌ Failed to delete conversations")
    else:
        print("❌ Cancelled - no conversations deleted")

print("\n" + "="*70)
