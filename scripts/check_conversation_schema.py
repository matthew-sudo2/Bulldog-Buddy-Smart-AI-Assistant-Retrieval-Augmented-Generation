import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='bulldog_buddy',
    user='postgres',
    password='bulldog_buddy_password_2025'
)

cur = conn.cursor()

# Check conversation_messages
print("=" * 60)
print("conversation_messages table structure:")
print("=" * 60)
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'conversation_messages' 
    ORDER BY ordinal_position
""")
for col in cur.fetchall():
    print(f"  {col[0]:20} {col[1]:20} nullable={col[2]:5} default={col[3]}")

# Check conversation_sessions
print("\n" + "=" * 60)
print("conversation_sessions table structure:")
print("=" * 60)
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'conversation_sessions' 
    ORDER BY ordinal_position
""")
for col in cur.fetchall():
    print(f"  {col[0]:20} {col[1]:20} nullable={col[2]:5} default={col[3]}")

# Check constraints
print("\n" + "=" * 60)
print("conversation_messages constraints:")
print("=" * 60)
cur.execute("""
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'conversation_messages'
""")
for cons in cur.fetchall():
    print(f"  {cons[0]:40} {cons[1]}")

cur.close()
conn.close()
