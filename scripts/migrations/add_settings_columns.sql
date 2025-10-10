-- ============================================================================
-- Migration: Add User Settings Columns
-- Created: 2025-10-10
-- Purpose: Add personalization and settings columns to users table
-- ============================================================================

-- Add settings columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_icon VARCHAR(10) DEFAULT '🐶';
ALTER TABLE users ADD COLUMN IF NOT EXISTS color_theme VARCHAR(50) DEFAULT 'university';
ALTER TABLE users ADD COLUMN IF NOT EXISTS personality_type VARCHAR(50) DEFAULT 'friendly';
ALTER TABLE users ADD COLUMN IF NOT EXISTS response_length VARCHAR(50) DEFAULT 'balanced';
ALTER TABLE users ADD COLUMN IF NOT EXISTS custom_instructions TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT true;

-- Create index for faster settings lookups
CREATE INDEX IF NOT EXISTS idx_users_settings ON users(color_theme, personality_type);

-- Verify columns were added successfully
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN (
    'profile_icon', 
    'color_theme', 
    'personality_type', 
    'response_length', 
    'custom_instructions', 
    'notifications_enabled'
)
ORDER BY column_name;

-- ============================================================================
-- Expected Output:
-- - 6 columns should be listed
-- - All should have appropriate defaults
-- - All should allow NULL (is_nullable = YES)
-- ============================================================================
