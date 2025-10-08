"""
Check how many conversations user 7 has and when they were created
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import BulldogBuddyDatabase

db = BulldogBuddyDatabase()

print("\n" + "="*70)
print("CHECKING CONVERSATIONS FOR USER 7")
print("="*70 + "\n")

# Get all conversations ordered by creation time
conversations = db.execute_query(
    """
    SELECT session_uuid, title, message_count, created_at, updated_at
    FROM conversation_sessions 
    WHERE user_id = 7
    ORDER BY created_at DESC
    LIMIT 20
    """,
    fetch=True
)

print(f"Total conversations: {len(conversations)}\n")
print("Most recent 20 conversations:")
print("-" * 70)

for i, conv in enumerate(conversations, 1):
    created = conv['created_at'].strftime('%Y-%m-%d %H:%M:%S') if conv['created_at'] else 'Unknown'
    updated = conv['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if conv['updated_at'] else 'Unknown'
    title = conv['title'][:40] + '...' if len(conv['title']) > 40 else conv['title']
    
    print(f"{i}. {title}")
    print(f"   UUID: {conv['session_uuid']}")
    print(f"   Messages: {conv['message_count']}")
    print(f"   Created: {created}")
    print(f"   Updated: {updated}")
    print()

# Check for duplicates created within last minute
recent_new_convs = db.execute_query(
    """
    SELECT COUNT(*) as count
    FROM conversation_sessions 
    WHERE user_id = 7
      AND title = 'New Conversation'
      AND message_count = 0
      AND created_at > NOW() - INTERVAL '1 hour'
    """,
    fetch=True
)

if recent_new_convs:
    recent_count = recent_new_convs[0]['count']
    print("="*70)
    print(f"⚠️  Empty 'New Conversation' entries created in last hour: {recent_count}")
    print("="*70)
    
    if recent_count > 5:
        print("\n🚨 WARNING: Multiple empty conversations being created!")
        print("This suggests the page is creating a new conversation on every reload.")
        print("\nPossible causes:")
        print("1. The 'if (conversations.length === 0)' check is failing")
        print("2. Multiple init() calls happening")
        print("3. Frontend creating conversations when it shouldn't")

print("\n" + "="*70)
