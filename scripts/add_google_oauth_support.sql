-- Migration: Add Google OAuth support to users table
-- Run this script to add Google authentication support

-- Add google_id column if it doesn't exist
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'google_id'
    ) THEN
        ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE;
        PRINT 'Added google_id column to users table';
    END IF;
END $$;

-- Create index for google_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- Update the password_hash column to allow NULL (for Google OAuth users)
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Create a constraint to ensure either password_hash or google_id is present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'users_auth_method_check'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_auth_method_check 
        CHECK (password_hash IS NOT NULL OR google_id IS NOT NULL);
    END IF;
END $$;

-- Update any existing session_id format if needed
UPDATE users SET session_id = 'migrated_' || id WHERE session_id IS NULL;

PRINT 'Migration completed: Google OAuth support added to users table';