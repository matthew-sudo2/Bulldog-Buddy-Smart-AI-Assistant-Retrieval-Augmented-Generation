-- Add missing conversation history tables

-- Create conversation_sessions table
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_uuid VARCHAR(255) UNIQUE NOT NULL,
    title TEXT DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create conversation_messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    embedding vector(384), -- For vector search (using pgvector)
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_uuid ON conversation_sessions(session_uuid);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_type ON conversation_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at);

-- Create vector similarity search index if pgvector is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        CREATE INDEX IF NOT EXISTS idx_conversation_messages_embedding ON conversation_messages USING ivfflat (embedding vector_cosine_ops);
    END IF;
END $$;

-- Create function to clean old conversation messages (keep last 50 per session)
CREATE OR REPLACE FUNCTION cleanup_old_conversation_messages()
RETURNS void AS $$
BEGIN
    DELETE FROM conversation_messages 
    WHERE id NOT IN (
        SELECT id 
        FROM (
            SELECT id, 
                   ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY created_at DESC) as rn
            FROM conversation_messages
        ) ranked 
        WHERE rn <= 50
    );
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at in conversation_sessions
CREATE OR REPLACE FUNCTION update_conversation_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation_session_timestamp ON conversation_sessions;
CREATE TRIGGER trigger_update_conversation_session_timestamp
    BEFORE UPDATE ON conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_session_timestamp();

-- Grant permissions
GRANT ALL PRIVILEGES ON conversation_sessions TO postgres;
GRANT ALL PRIVILEGES ON conversation_messages TO postgres;
GRANT USAGE, SELECT ON SEQUENCE conversation_sessions_id_seq TO postgres;
GRANT USAGE, SELECT ON SEQUENCE conversation_messages_id_seq TO postgres;

-- Display success message
SELECT 'Conversation history tables created successfully!' as status;