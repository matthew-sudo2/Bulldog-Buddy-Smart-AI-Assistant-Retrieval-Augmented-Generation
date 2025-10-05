# 🔒 Security Configuration Guide

## ⚠️ IMPORTANT: Files Already Exposed

**Your repository currently contains sensitive information that has already been committed to GitHub.** 

### Files with Exposed Credentials:
1. `frontend/.env` - Contains database password and Google OAuth secrets
2. `infrastructure/docker-compose.yml` - Contains database password
3. Multiple scripts in `scripts/` folder with hardcoded passwords
4. `start.py` - Shows password in console output
5. `README.md` and `docs/setup.md` - Document the database password

### ⚡ Immediate Actions Required

#### 1. Stop Tracking Sensitive Files
```bash
# Remove from git tracking (but keep locally)
git rm --cached frontend/.env
git rm --cached frontend/.env.local
git rm --cached .env
git commit -m "Remove sensitive environment files from tracking"
git push origin main
```

#### 2. Change All Passwords Immediately
Since these passwords are now public on GitHub, you **must** change them:

**Database Password:**
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Change password
ALTER USER postgres WITH PASSWORD 'your_new_secure_password_here';
```

**Google OAuth:**
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Navigate to your project
- Regenerate OAuth client secret
- Update your local `.env` files with new secrets

**Session Secret:**
- Generate a new random secret:
```bash
# On Windows (PowerShell)
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

#### 3. Create Local Environment Files

**Root `.env` file:**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**Frontend `.env` file:**
```bash
cd frontend
cp .env.example .env
# Edit frontend/.env with your actual credentials
```

#### 4. Update Configuration Files

The following files need to be updated to read from environment variables instead of hardcoded values:

**a. `infrastructure/docker-compose.yml`**
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}  # Instead of hardcoded password
```

**b. Scripts in `scripts/` folder:**
Create a `scripts/db_config.py` (add to .gitignore):
```python
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'bulldog_buddy'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD')
}
```

Then update scripts to use:
```python
from db_config import DB_CONFIG
conn = psycopg2.connect(**DB_CONFIG)
```

**c. `start.py`**
Update to not print passwords:
```python
# Instead of:
print(f"Password: bulldog_buddy_password_2025")

# Use:
print(f"Password: {'*' * 8} (from .env file)")
```

## 📋 Updated .gitignore

The `.gitignore` file has been updated to exclude:

```
# Environments and Secrets
.env
.env.local
.env.production
.env.development
frontend/.env
frontend/.env.local
frontend/.env.production

# Database configuration files with credentials
**/config.py
**/database_config.py
**/secrets.py

# Scripts with hardcoded credentials
scripts/*_config.py
scripts/fix_*.py
scripts/check_*.py
scripts/test_*.py
```

## 🔐 Best Practices

### 1. Never Commit Secrets
- Always use `.env` files for secrets
- Keep `.env` files in `.gitignore`
- Only commit `.env.example` with placeholder values

### 2. Use Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()

DB_PASSWORD = os.getenv('DB_PASSWORD')
if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable not set")
```

### 3. Rotate Credentials Regularly
- Change passwords every 90 days
- Regenerate API keys when team members leave
- Use different credentials for dev/staging/production

### 4. Use Strong Passwords
```bash
# Generate strong password (32 characters)
openssl rand -base64 32
```

### 5. Secure Docker Secrets
For production, use Docker secrets or environment variables:
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

secrets:
  db_password:
    external: true
```

## 🚨 GitHub Security Features

### Enable Secret Scanning
1. Go to your repository on GitHub
2. Settings → Security → Code security and analysis
3. Enable "Secret scanning"
4. Enable "Push protection" to prevent future commits with secrets

### GitHub Secrets (for CI/CD)
Store secrets securely for GitHub Actions:
1. Repository → Settings → Secrets and variables → Actions
2. Add secrets like `DB_PASSWORD`, `GOOGLE_CLIENT_SECRET`
3. Reference in workflows: `${{ secrets.DB_PASSWORD }}`

## 📦 Setup for New Developers

Create a `SETUP.md` file with instructions:

```markdown
## Initial Setup

1. Clone the repository
2. Copy environment templates:
   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env
   ```
3. Ask team lead for actual credentials
4. Update `.env` files with real values
5. Never commit `.env` files!
```

## ✅ Verification Checklist

After implementing these changes:

- [ ] `frontend/.env` removed from git tracking
- [ ] `.gitignore` updated to exclude all `.env` files
- [ ] Database password changed
- [ ] Google OAuth secret regenerated
- [ ] Session secret regenerated
- [ ] All scripts updated to use environment variables
- [ ] `docker-compose.yml` updated to use env vars
- [ ] Documentation updated to not show real credentials
- [ ] `.env.example` files created with placeholders
- [ ] GitHub secret scanning enabled
- [ ] Team members notified of password changes

## 🔗 Additional Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Secrets_Management)
- [12 Factor App - Config](https://12factor.net/config)

## 🆘 If Secrets Were Exposed

1. **Rotate immediately** - Change all exposed credentials
2. **Check access logs** - Look for unauthorized access
3. **Revoke tokens** - Invalidate any exposed API keys
4. **Use git-secrets** - Tool to prevent committing secrets: https://github.com/awslabs/git-secrets
5. **Consider git history cleanup** - Use BFG Repo-Cleaner to remove secrets from history (destructive operation)

---

**Remember: Security is not a one-time setup, it's an ongoing practice!**
