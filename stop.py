#!/usr/bin/env python3
"""
Bulldog Buddy - System Shutdown Script
Stops all services and database
"""

import subprocess
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.YELLOW}→ {text}{Colors.END}")

def stop_database():
    """Stop PostgreSQL database containers"""
    print_header("Stopping Database Services")
    
    try:
        infrastructure_dir = Path(__file__).parent / "infrastructure"
        
        print_info("Stopping database containers...")
        subprocess.run(
            ["docker-compose", "down"],
            cwd=infrastructure_dir,
            check=True,
            capture_output=True
        )
        
        print_success("Database containers stopped")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Failed to stop database: {e}{Colors.END}")
        return False

def main():
    """Main shutdown sequence"""
    print_header("Bulldog Buddy - System Shutdown")
    
    print_info("Please close the PowerShell windows for:")
    print("  - API Bridge Server")
    print("  - Frontend Server")
    print()
    
    # Stop database
    stop_database()
    
    print()
    print_success("System shutdown complete!")
    print()
    print(f"{Colors.YELLOW}Note: If you want to remove all database data, run:{Colors.END}")
    print(f"{Colors.CYAN}  cd infrastructure && docker-compose down -v{Colors.END}")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown cancelled.")
        sys.exit(0)
