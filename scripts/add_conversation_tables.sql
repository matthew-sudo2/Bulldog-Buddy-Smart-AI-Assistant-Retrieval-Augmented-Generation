-- Add conversation tables for proper conversation history management

-- Create conversation sessions table
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_uuid UUID UNIQUE NOT NULL,
    title VARCHAR(500) DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_pinned BOOLEAN DEFAULT false,
    message_count INTEGER DEFAULT 0
);

-- Create conversation messages table  
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL,
    message_role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_session FOREIGN KEY (session_id) REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    CONSTRAINT chk_role CHECK (message_role IN ('user', 'assistant', 'system'))
);

-- Create user context table
CREATE TABLE IF NOT EXISTS user_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    context_key VARCHAR(100) NOT NULL,
    context_value TEXT NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.00,
    source_message_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, context_key)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id ON conversation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_uuid ON conversation_sessions(session_uuid);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_updated_at ON conversation_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_role ON conversation_messages(message_role);
CREATE INDEX IF NOT EXISTS idx_user_context_user_id ON user_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_context_key ON user_context(context_key);

-- Create trigger function
CREATE OR REPLACE FUNCTION update_conversation_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversation_sessions 
    SET updated_at = NOW(), 
        message_count = (SELECT COUNT(*) FROM conversation_messages WHERE session_id = NEW.session_id)
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_update_session_timestamp ON conversation_messages;
CREATE TRIGGER trigger_update_session_timestamp
    AFTER INSERT ON conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_session_timestamp();
