"""
Script to upgrade the existing database with authentication features
"""
import psycopg2
from psycopg2.extras import RealDictCursor

def upgrade_database():
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
            print("🔧 Upgrading database schema for authentication...")
            
            # Add missing extensions
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                CREATE EXTENSION IF NOT EXISTS "pgcrypto";
            """)
            print("✅ Extensions added")
            
            # Add missing enum types
            cur.execute("""
                DO $$ BEGIN
                    CREATE TYPE user_role_enum AS ENUM ('student', 'admin', 'guest');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            print("✅ Enum types added")
            
            # Add authentication columns to existing users table
            auth_columns = [
                ("user_uuid", "UUID DEFAULT uuid_generate_v4() UNIQUE"),
                ("email", "VARCHAR(255) UNIQUE"),
                ("username", "VARCHAR(100) UNIQUE"),
                ("password_hash", "TEXT"),
                ("first_name", "VARCHAR(100)"),
                ("last_name", "VARCHAR(100)"),
                ("role", "user_role_enum DEFAULT 'student'"),
                ("student_id", "VARCHAR(50) UNIQUE"),
                ("is_active", "BOOLEAN DEFAULT true"),
                ("is_verified", "BOOLEAN DEFAULT false"),
                ("last_login", "TIMESTAMP")
            ]
            
            for column_name, column_def in auth_columns:
                try:
                    # Use individual transaction for each column
                    cur.execute(f"""
                        DO $$ 
                        BEGIN 
                            ALTER TABLE users ADD COLUMN {column_name} {column_def};
                        EXCEPTION 
                            WHEN duplicate_column THEN 
                                -- Column already exists, do nothing
                                NULL;
                        END $$;
                    """)
                    conn.commit()  # Commit each column addition
                    print(f"   ✅ Column {column_name} ready")
                except Exception as e:
                    print(f"   ❌ Error with column {column_name}: {e}")
                    conn.rollback()
            
            # Create authentication-related tables
            auth_tables = [
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    verified BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
                    theme VARCHAR(20) DEFAULT 'light',
                    language VARCHAR(10) DEFAULT 'en',
                    notifications_enabled BOOLEAN DEFAULT true,
                    preferred_model VARCHAR(50) DEFAULT 'gemma3',
                    conversation_history_limit INTEGER DEFAULT 10,
                    auto_save_conversations BOOLEAN DEFAULT true,
                    settings JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            ]
            
            for table_sql in auth_tables:
                try:
                    cur.execute(table_sql)
                    table_name = table_sql.split("CREATE TABLE IF NOT EXISTS ")[1].split(" (")[0]
                    print(f"   ✅ Created table: {table_name}")
                except Exception as e:
                    print(f"   ❌ Error creating table: {e}")
            
            # Create password hashing functions
            cur.execute("""
                CREATE OR REPLACE FUNCTION hash_password(password TEXT)
                RETURNS TEXT AS $$
                BEGIN
                    RETURN crypt(password, gen_salt('bf'));
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            cur.execute("""
                CREATE OR REPLACE FUNCTION verify_password(password TEXT, hash TEXT)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN hash = crypt(password, hash);
                END;
                $$ LANGUAGE plpgsql;
            """)
            print("✅ Password functions created")
            
            # Add pgvector extension and conversation history tables
            print("\n🧠 Adding conversation history with vector search...")
            
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ pgvector extension enabled")
            
            # Create conversation sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    session_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
                    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
                    summary TEXT,
                    message_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    is_pinned BOOLEAN DEFAULT false,
                    is_archived BOOLEAN DEFAULT false,
                    tags TEXT[] DEFAULT ARRAY[]::TEXT[]
                );
            """)
            print("✅ Conversation sessions table created")
            
            # Create conversation messages with vector embeddings
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES conversation_sessions(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    message_order INTEGER NOT NULL,
                    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    embedding vector(384), -- 384-dimensional vectors for sentence-transformers
                    confidence_score FLOAT DEFAULT 0.0,
                    model_used VARCHAR(50),
                    sources_used TEXT[],
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    
                    UNIQUE(session_id, message_order)
                );
            """)
            print("✅ Conversation messages table created")
            
            # Create vector search function
            cur.execute("""
                CREATE OR REPLACE FUNCTION search_conversation_history(
                    search_user_id INTEGER,
                    query_embedding vector(384),
                    similarity_threshold FLOAT DEFAULT 0.3,
                    result_limit INTEGER DEFAULT 10
                ) 
                RETURNS TABLE (
                    session_id INTEGER,
                    session_title VARCHAR(255),
                    message_id INTEGER,
                    message_content TEXT,
                    message_type VARCHAR(20),
                    similarity_score FLOAT,
                    created_at TIMESTAMP
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        cs.id as session_id,
                        cs.title as session_title,
                        cm.id as message_id,
                        cm.content as message_content,
                        cm.message_type,
                        (1 - (cm.embedding <=> query_embedding)) as similarity_score,
                        cm.created_at
                    FROM conversation_messages cm
                    JOIN conversation_sessions cs ON cm.session_id = cs.id
                    WHERE cm.user_id = search_user_id 
                        AND cm.embedding IS NOT NULL
                        AND (1 - (cm.embedding <=> query_embedding)) > similarity_threshold
                    ORDER BY (cm.embedding <=> query_embedding) ASC
                    LIMIT result_limit;
                END;
                $$ LANGUAGE plpgsql;
            """)
            print("✅ Vector search function created")
            
            # Create indexes for new columns
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)", 
                "CREATE INDEX IF NOT EXISTS idx_users_student_id ON users(student_id)",
                "CREATE INDEX IF NOT EXISTS idx_users_uuid ON users(user_uuid)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)",
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)",
                
                # Conversation history indexes
                "CREATE INDEX IF NOT EXISTS idx_conv_sessions_user_id ON conversation_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conv_sessions_updated_at ON conversation_sessions(updated_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_conv_sessions_pinned ON conversation_sessions(user_id, is_pinned) WHERE is_pinned = true",
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_session_id ON conversation_messages(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_user_id ON conversation_messages(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_order ON conversation_messages(session_id, message_order)",
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_type ON conversation_messages(message_type)",
                "CREATE INDEX IF NOT EXISTS idx_conv_messages_created_at ON conversation_messages(created_at DESC)"
            ]
            
            for index_sql in indexes:
                try:
                    cur.execute(index_sql)
                except Exception as e:
                    if "already exists" not in str(e):
                        print(f"   ⚠️  Index error: {e}")
            
            print("✅ Regular indexes created")
            
            # Create vector index for conversation similarity search
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_messages_embedding
                    ON conversation_messages 
                    USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100);
                """)
                print("✅ Vector similarity index created")
            except Exception as e:
                print(f"⚠️  Vector index warning: {e}")
            
            # Create trigger for automatic session stats update
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_conversation_session_stats() 
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE conversation_sessions 
                    SET 
                        message_count = (
                            SELECT COUNT(*) 
                            FROM conversation_messages 
                            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
                        ),
                        updated_at = NOW()
                    WHERE id = COALESCE(NEW.session_id, OLD.session_id);
                    
                    RETURN COALESCE(NEW, OLD);
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS trigger_update_session_stats ON conversation_messages;
                CREATE TRIGGER trigger_update_session_stats
                    AFTER INSERT OR UPDATE OR DELETE ON conversation_messages
                    FOR EACH ROW
                    EXECUTE FUNCTION update_conversation_session_stats();
            """)
            print("✅ Conversation management triggers created")
            
            # Update existing user record with proper authentication data
            cur.execute("""
                UPDATE users 
                SET 
                    email = 'admin@bulldogbuddy.com',
                    username = 'admin',
                    password_hash = hash_password('admin123'),
                    first_name = 'Admin',
                    last_name = 'User',
                    role = 'admin',
                    is_verified = true,
                    is_active = true
                WHERE id = 1 AND email IS NULL
            """)
            print("✅ Updated existing admin user")
            
            # Add sample users with authentication
            sample_users = [
                ('student1@nu.edu.ph', 'student1', 'password123', 'John', 'Doe', 'student', '2025001'),
                ('student2@nu.edu.ph', 'student2', 'password123', 'Jane', 'Smith', 'student', '2025002'),
                ('test.user@nu.edu.ph', 'testuser', 'test123', 'Test', 'User', 'student', '2025003')
            ]
            
            for email, username, password, first_name, last_name, role, student_id in sample_users:
                try:
                    cur.execute("""
                        INSERT INTO users (session_id, email, username, password_hash, first_name, last_name, role, student_id, is_verified, is_active)
                        VALUES (%s, %s, %s, hash_password(%s), %s, %s, %s, %s, true, true)
                        ON CONFLICT (email) DO NOTHING
                        ON CONFLICT (username) DO NOTHING
                        ON CONFLICT (student_id) DO NOTHING
                    """, (f"session_{username}", email, username, password, first_name, last_name, role, student_id))
                except Exception as e:
                    print(f"   ⚠️  User {email}: {e}")
            
            print("✅ Sample users added")
            
            # Add sample knowledge base entries
            knowledge_entries = [
                ('1.1', 'Academic', 'Course Registration', 
                 'Students must register for courses during the designated enrollment period. Registration opens two weeks before the semester begins.'),
                 
                ('2.1', 'Financial', 'Tuition Fees', 
                 'Undergraduate tuition is PHP 2,800 per unit. Students can pay in full or choose installment plans.'),
                 
                ('3.1', 'Admissions', 'Requirements', 
                 'High school diploma or equivalent required. Minimum GPA of 2.5 for undergraduate programs.'),
                 
                ('4.1', 'Student Life', 'Campus Facilities', 
                 'University provides libraries, computer labs, cafeteria, gymnasium, and student lounges.'),
                 
                ('5.1', 'Policies', 'Attendance Policy', 
                 'Students must maintain at least 80% attendance in each course.')
            ]
            
            for section, category, title, content in knowledge_entries:
                # Generate a simple embedding (random for demo - in production use real embeddings)
                import random
                fake_embedding = [random.random() for _ in range(768)]
                
                try:
                    cur.execute("""
                        INSERT INTO knowledge_base (section, category, title, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (section, category, title, content, fake_embedding, '{"source": "handbook"}'))
                except Exception as e:
                    print(f"   ⚠️  Knowledge entry {title}: {e}")
            
            print("✅ Sample knowledge base entries added")
            
            conn.commit()
            print("\n🎉 Database upgrade completed successfully!")
            
            # Final verification
            cur.execute("SELECT COUNT(*) as count FROM users")
            users_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM knowledge_base")
            kb_count = cur.fetchone()['count']
            
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            tables = cur.fetchall()
            
            print(f"\n📊 Final Database Status:")
            print(f"   Total Tables: {len(tables)}")
            print(f"   Users: {users_count}")
            print(f"   Knowledge Base: {kb_count}")
            
            # Add personalization settings columns
            print(f"\n🎨 Adding personalization settings...")
            
            personalization_columns = [
                ("profile_icon", "VARCHAR(10) DEFAULT '🐶'"),
                ("color_theme", "VARCHAR(50) DEFAULT 'university'"),
                ("personality_type", "VARCHAR(50) DEFAULT 'friendly'"),
                ("response_length", "VARCHAR(20) DEFAULT 'moderate'"),
                ("custom_instructions", "TEXT DEFAULT ''"),
                ("notifications_enabled", "BOOLEAN DEFAULT true")
            ]
            
            for col_name, col_def in personalization_columns:
                try:
                    cur.execute(f"""
                        ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def};
                    """)
                    print(f"   ✅ Added {col_name} column")
                except Exception as e:
                    print(f"   ⚠️  Column {col_name} might already exist: {str(e)[:50]}...")
            
            # Update existing users with default personalization settings
            cur.execute("""
                UPDATE users 
                SET profile_icon = COALESCE(profile_icon, '🐶'),
                    color_theme = COALESCE(color_theme, 'university'),
                    personality_type = COALESCE(personality_type, 'friendly'),
                    response_length = COALESCE(response_length, 'moderate'),
                    custom_instructions = COALESCE(custom_instructions, ''),
                    notifications_enabled = COALESCE(notifications_enabled, true),
                    updated_at = CURRENT_TIMESTAMP;
            """)
            
            print(f"   ✅ Updated existing users with default personalization settings")
            
            print(f"\n📋 Available Tables:")
            for table in tables:
                print(f"   - {table['table_name']}")
            
            print(f"\n🌐 Access pgAdmin at: http://localhost:8080")
            print(f"   Login: admin@bulldogbuddy.com / admin123")
            print(f"\n🔗 Database Connection:")
            print(f"   Host: postgres")
            print(f"   Port: 5432") 
            print(f"   Database: bulldog_buddy")
            print(f"   Username: postgres")
            print(f"   Password: bulldog_buddy_password_2025")
            
    except Exception as e:
        print(f"❌ Upgrade failed: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    upgrade_database()