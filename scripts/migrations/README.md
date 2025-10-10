# Database Migrations

This directory contains SQL migration scripts and Python utilities for database schema changes.

## 📁 Directory Structure

```
scripts/migrations/
├── add_settings_columns.sql        # SQL: Add user personalization columns
├── add_profile_icon.py             # Python: Add profile icon column
└── apply_settings_migration.py     # Python: Execute SQL migrations
```

## 🚀 Running Migrations

### Method 1: Execute SQL Directly

```bash
# Connect to PostgreSQL
psql -U postgres -d bulldog_buddy -f scripts/migrations/add_settings_columns.sql
```

### Method 2: Use Python Script

```bash
# From project root directory
cd "c:\Users\shanaya\Documents\ChatGPT-Clone\Paw-sitive AI"

# Activate virtual environment
.\.venv\Scripts\activate

# Run migration script
python scripts\migrations\apply_settings_migration.py
```

### Method 3: Run Specific Migration

```bash
# Add profile icon column only
python scripts\migrations\add_profile_icon.py
```

## 📝 Available Migrations

### 1. Add Settings Columns (`add_settings_columns.sql`)

**Purpose**: Add user personalization and settings columns to `users` table

**Columns Added**:
- `profile_icon` (VARCHAR 10) - User's profile emoji
- `color_theme` (VARCHAR 50) - UI theme preference
- `personality_type` (VARCHAR 50) - AI personality setting
- `response_length` (VARCHAR 50) - Response detail preference
- `custom_instructions` (TEXT) - User's custom AI instructions
- `notifications_enabled` (BOOLEAN) - Notification preference

**Indexes Created**:
- `idx_users_settings` on (color_theme, personality_type)

**Usage**:
```bash
python scripts/migrations/apply_settings_migration.py
```

### 2. Add Profile Icon (`add_profile_icon.py`)

**Purpose**: Add profile icon column with UTF-8 emoji support

**Usage**:
```bash
python scripts/migrations/add_profile_icon.py
```

## ✅ Verification

After running migrations, verify the changes:

```bash
# Check if columns exist
python scripts/debug/check_schema.py

# Or use SQL directly
psql -U postgres -d bulldog_buddy -c "
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('profile_icon', 'color_theme', 'personality_type');
"
```

## ⚠️ Important Notes

1. **Backup First**: Always backup your database before running migrations:
   ```bash
   docker exec bulldog-buddy-db pg_dump -U postgres bulldog_buddy > backup.sql
   ```

2. **Idempotent**: All migrations use `IF NOT EXISTS` - safe to run multiple times

3. **Default Values**: All new columns have sensible defaults:
   - profile_icon: '🐶'
   - color_theme: 'university'
   - personality_type: 'friendly'
   - response_length: 'balanced'
   - notifications_enabled: true

4. **Virtual Environment**: Always activate `.venv` before running Python migrations

## 🔍 Troubleshooting

### Error: "Module not found: core.database"

**Solution**: Run from project root with activated virtual environment:
```bash
cd "c:\Users\shanaya\Documents\ChatGPT-Clone\Paw-sitive AI"
.\.venv\Scripts\activate
python scripts\migrations\apply_settings_migration.py
```

### Error: "Permission denied"

**Solution**: Ensure PostgreSQL is running and credentials in `.env` are correct:
```bash
docker ps  # Check if bulldog-buddy-db is running
```

### Error: "Column already exists"

**Solution**: This is safe - the migration uses `IF NOT EXISTS`. The column is already added.

## 📚 Related Documentation

- [Database Schema](../../infrastructure/init.sql) - Initial schema
- [Troubleshooting Guides](../docs/troubleshooting/) - Common issues
- [Settings Fix Documentation](../../SETTINGS_AND_CONVERSATIONS_FIXED.md) - Context for these migrations

---

**Created**: 2025-10-10  
**Last Updated**: 2025-10-10  
**Maintainer**: Development Team
