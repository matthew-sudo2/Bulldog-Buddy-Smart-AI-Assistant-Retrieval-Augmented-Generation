"""
Database configuration loader for scripts
Reads credentials from environment variables for security
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Database configuration from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'bulldog_buddy'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD')
}

# Validate that password is set
if not DB_CONFIG['password']:
    raise ValueError(
        "DB_PASSWORD not found in environment variables.\n"
        "Please copy .env.example to .env and set your database password."
    )

def get_connection_string():
    """Get PostgreSQL connection string"""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

def get_connection_dict():
    """Get database configuration as dictionary"""
    return DB_CONFIG.copy()
