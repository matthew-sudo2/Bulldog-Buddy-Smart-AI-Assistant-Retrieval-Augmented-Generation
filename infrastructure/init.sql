-- Bulldog Buddy Database Schema
-- PostgreSQL + pgvector setup for RAG system with Authentication

-- Enable pgvector extension and other required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types for better data integrity
CREATE TYPE query_type_enum AS ENUM ('university_specific', 'general_knowledge');
CREATE TYPE knowledge_category_enum AS ENUM ('Academic', 'Admissions', 'Financial', 'Policies', 'Student Life', 'General');
CREATE TYPE education_level_enum AS ENUM ('undergraduate', 'masters', 'doctoral');
CREATE TYPE model_type_enum AS ENUM ('gemma3', 'llama3.2');
CREATE TYPE user_role_enum AS ENUM ('student', 'admin', 'guest');

-- Users table with full authentication support
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    username VARCHAR(100) UNIQUE,
    password_hash TEXT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role user_role_enum DEFAULT 'student',
    student_id VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    preferred_model model_type_enum DEFAULT 'gemma3',
    total_queries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Knowledge base for university handbook (RAG system)
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    section VARCHAR(255) NOT NULL,
    category knowledge_category_enum NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    embedding vector(768), -- embeddinggemma dimension
    metadata JSONB,
    confidence_threshold DECIMAL(3,2) DEFAULT 0.80,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations with 10-message history
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    message_history JSONB NOT NULL DEFAULT '[]', -- Store last 10 messages
    model_used model_type_enum,
    total_messages INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Query logs for analytics and improvement
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    user_question TEXT NOT NULL,
    query_type query_type_enum,
    confidence_score DECIMAL(4,3),
    model_used model_type_enum,
    response_sources INTEGER[], -- Array of knowledge_base ids
    response_time_ms INTEGER,
    was_helpful BOOLEAN, -- User feedback
    created_at TIMESTAMP DEFAULT NOW()
);

-- Financial information for university
CREATE TABLE financial_info (
    id SERIAL PRIMARY KEY,
    level education_level_enum NOT NULL,
    rate_per_unit DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'PHP',
    effective_date DATE NOT NULL,
    payment_options JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Academic calendar and important dates
CREATE TABLE academic_calendar (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(100), -- 'deadline', 'holiday', 'semester_start', etc.
    event_date DATE NOT NULL,
    description TEXT,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- System configuration and settings
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User sessions for login management
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Email verification tokens
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User preferences
CREATE TABLE user_preferences (
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
);

-- Create indexes for performance optimization
CREATE INDEX idx_users_session_id ON users(session_id);
CREATE INDEX idx_users_last_active ON users(last_active);

CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX idx_knowledge_base_section ON knowledge_base(section);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);

CREATE INDEX idx_query_logs_user_id ON query_logs(user_id);
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX idx_query_logs_query_type ON query_logs(query_type);

CREATE INDEX idx_financial_info_level ON financial_info(level);
CREATE INDEX idx_financial_info_effective_date ON financial_info(effective_date);
CREATE INDEX idx_financial_info_active ON financial_info(is_active);

CREATE INDEX idx_academic_calendar_date ON academic_calendar(event_date);
CREATE INDEX idx_academic_calendar_type ON academic_calendar(event_type);

-- Create functions for password hashing
CREATE OR REPLACE FUNCTION hash_password(password TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN crypt(password, gen_salt('bf'));
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION verify_password(password TEXT, hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN hash = crypt(password, hash);
END;
$$ LANGUAGE plpgsql;

-- Insert sample users with authentication
INSERT INTO users (session_id, email, username, password_hash, first_name, last_name, role, student_id, is_verified, is_active) VALUES 
('admin_session', 'admin@bulldogbuddy.com', 'admin', hash_password('admin123'), 'Admin', 'User', 'admin', NULL, true, true),
('john_session', 'john.doe@nu.edu.ph', 'johndoe', hash_password('password123'), 'John', 'Doe', 'student', '2025001', true, true),
('jane_session', 'jane.smith@nu.edu.ph', 'janesmith', hash_password('password123'), 'Jane', 'Smith', 'student', '2025002', true, true),
('test_session', 'test.user@nu.edu.ph', 'testuser', hash_password('test123'), 'Test', 'User', 'student', '2025003', true, true);

-- Insert sample knowledge base entries
INSERT INTO knowledge_base (section, category, title, content, metadata) VALUES 
('1.1', 'Academic', 'Course Registration', 'Students must register for courses during the designated enrollment period. Registration opens two weeks before the semester begins.', '{"source": "handbook", "page": 15}'),
('1.2', 'Academic', 'Grading System', 'National University uses a 1.0 to 5.0 grading system where 1.0 is the highest grade and 3.0 is the passing grade.', '{"source": "handbook", "page": 18}'),
('2.1', 'Admissions', 'Undergraduate Requirements', 'High school diploma or equivalent required. Minimum GPA of 2.5 for undergraduate programs.', '{"source": "handbook", "page": 5}'),
('2.2', 'Admissions', 'Graduate Requirements', 'Masters program applicants need a bachelors degree from an accredited institution with minimum GPA of 2.75.', '{"source": "handbook", "page": 7}'),
('3.1', 'Financial', 'Tuition Payment', 'Undergraduate tuition is PHP 2,800 per unit. Students can pay in full or choose installment plans.', '{"source": "handbook", "page": 20}'),
('3.2', 'Financial', 'Scholarship Programs', 'Merit-based scholarships available for students with GPAs above 3.5. Applications due March 1st.', '{"source": "handbook", "page": 22}'),
('4.1', 'Policies', 'Attendance Policy', 'Students must maintain at least 80% attendance in each course. Excessive absences may result in failure.', '{"source": "handbook", "page": 25}'),
('4.2', 'Policies', 'Academic Integrity', 'Cheating and plagiarism are strictly prohibited and may result in course failure or expulsion.', '{"source": "handbook", "page": 28}'),
('5.1', 'Student Life', 'Campus Facilities', 'University provides libraries, computer labs, cafeteria, gymnasium, and student lounges.', '{"source": "handbook", "page": 35}'),
('5.2', 'Student Life', 'Student Organizations', 'Over 50 student organizations available including academic clubs, sports teams, and cultural groups.', '{"source": "handbook", "page": 40}');

-- Insert initial financial data (National University Philippines rates)
INSERT INTO financial_info (level, rate_per_unit, effective_date, payment_options) VALUES 
('undergraduate', 2800.00, '2025-01-01', '{"full_payment": true, "installment_2": true, "installment_3": true, "discount_early": 0.05}'),
('masters', 3200.00, '2025-01-01', '{"full_payment": true, "installment_2": true, "installment_3": true, "discount_early": 0.03}'),
('doctoral', 3500.00, '2025-01-01', '{"full_payment": true, "installment_2": true, "installment_3": true, "discount_early": 0.03}');

-- Insert system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES 
('max_conversation_history', '10', 'Maximum number of messages to keep in conversation history'),
('default_confidence_threshold', '0.80', 'Default confidence threshold for RAG retrieval'),
('embedding_model', '"embeddinggemma"', 'Default embedding model for vector operations'),
('response_temperature', '0.7', 'Default temperature for AI responses'),
('max_retrieval_docs', '5', 'Maximum number of documents to retrieve for RAG');

-- Insert sample academic calendar events
INSERT INTO academic_calendar (event_name, event_type, event_date, description) VALUES 
('First Semester Start', 'semester_start', '2025-08-15', 'Beginning of Academic Year 2025-2026 First Semester'),
('Enrollment Deadline', 'deadline', '2025-08-10', 'Last day for student enrollment'),
('Midterm Exams', 'exam_period', '2025-10-15', 'Midterm examination period'),
('Christmas Break Start', 'holiday', '2025-12-20', 'Start of Christmas vacation'),
('Second Semester Start', 'semester_start', '2026-01-15', 'Beginning of Second Semester'),
('Final Exams', 'exam_period', '2026-05-15', 'Final examination period'),
('Graduation', 'ceremony', '2026-06-15', 'Commencement exercises');

-- Create a view for active financial information
CREATE VIEW current_tuition_rates AS
SELECT 
    level,
    rate_per_unit,
    currency,
    payment_options,
    effective_date
FROM financial_info 
WHERE is_active = TRUE 
AND effective_date <= CURRENT_DATE
ORDER BY level, effective_date DESC;

-- Create a function to clean old conversation history
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM conversations 
    WHERE updated_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a function to update user activity
CREATE OR REPLACE FUNCTION update_user_activity(p_session_id VARCHAR(255))
RETURNS INTEGER AS $$
DECLARE
    user_id INTEGER;
BEGIN
    UPDATE users 
    SET last_active = NOW(), 
        total_queries = total_queries + 1
    WHERE session_id = p_session_id
    RETURNING id INTO user_id;
    
    IF user_id IS NULL THEN
        INSERT INTO users (session_id, last_active, total_queries)
        VALUES (p_session_id, NOW(), 1)
        RETURNING id INTO user_id;
    END IF;
    
    RETURN user_id;
END;
$$ LANGUAGE plpgsql;

-- Create a function for vector similarity search
CREATE OR REPLACE FUNCTION search_knowledge_base(
    query_embedding vector(768),
    search_category knowledge_category_enum DEFAULT NULL,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.70,
    max_results INTEGER DEFAULT 5
)
RETURNS TABLE (
    kb_id INTEGER,
    section VARCHAR(255),
    category knowledge_category_enum,
    title VARCHAR(500),
    content TEXT,
    similarity_score DECIMAL(4,3),
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.section,
        kb.category,
        kb.title,
        kb.content,
        (1 - (kb.embedding <=> query_embedding))::DECIMAL(4,3) as similarity_score,
        kb.metadata
    FROM knowledge_base kb
    WHERE (search_category IS NULL OR kb.category = search_category)
      AND (1 - (kb.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (for application user if needed)
-- CREATE USER bulldog_buddy_app WITH PASSWORD 'app_password_2025';
-- GRANT CONNECT ON DATABASE bulldog_buddy TO bulldog_buddy_app;
-- GRANT USAGE ON SCHEMA public TO bulldog_buddy_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bulldog_buddy_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bulldog_buddy_app;

-- Show setup completion
DO $$
BEGIN
    RAISE NOTICE 'Bulldog Buddy database schema created successfully!';
    RAISE NOTICE 'pgvector extension: %', (SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector'));
    RAISE NOTICE 'Total tables created: %', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE');
    RAISE NOTICE 'Setup completed at: %', NOW();
END $$;