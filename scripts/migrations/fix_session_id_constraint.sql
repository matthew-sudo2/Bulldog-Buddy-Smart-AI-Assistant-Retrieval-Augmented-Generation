-- Fix NULL session_id values in users table
-- This addresses the unique constraint violation on users_session_id_key

-- Update any users with NULL or empty session_id
UPDATE users 
SET session_id = 'migrated_' || id || '_' || EXTRACT(epoch FROM NOW())::bigint || '_' || substr(md5(random()::text), 1, 8)
WHERE session_id IS NULL OR session_id = '';

-- Verify the fix
SELECT COUNT(*) as users_with_null_session_id FROM users WHERE session_id IS NULL OR session_id = '';

-- Show sample of updated users
SELECT id, session_id, email, username 
FROM users 
WHERE session_id LIKE 'migrated_%' 
ORDER BY id 
LIMIT 5;