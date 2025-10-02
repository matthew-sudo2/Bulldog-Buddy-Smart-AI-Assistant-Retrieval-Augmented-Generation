#!/usr/bin/env python3
"""
Bulldog Buddy - Complete System Startup Script
Starts database and all application services
"""

import subprocess
import sys
import time
import os
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

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.YELLOW}→ {text}{Colors.END}")

def check_docker():
    """Check if Docker is installed and running"""
    try:
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print_success("Docker is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker is not installed or not in PATH")
        print_info("Please install Docker Desktop: https://www.docker.com/products/docker-desktop")
        return False

def check_ollama_models():
    """Check and pull required Ollama models"""
    print_header("Checking Ollama Models")
    
    required_models = [
        "gemma3:latest",
        "llama3.2:latest",
        "embeddinggemma:latest"
    ]
    
    # Check if Ollama is installed
    try:
        subprocess.run(
            ["ollama", "--version"],
            check=True,
            capture_output=True,
            text=True
        )
        print_success("Ollama is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Ollama is not installed")
        print_info("Please install Ollama: https://ollama.com/download")
        return False
    
    # Pull each required model
    for model in required_models:
        print_info(f"Pulling {model}...")
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per model
            )
            
            if result.returncode == 0:
                print_success(f"Model {model} is ready")
            else:
                print_error(f"Failed to pull {model}")
                if result.stderr:
                    print(f"  Error: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print_error(f"Timeout while pulling {model}")
            print_info("This may happen with slow internet. You can try pulling manually later.")
        except Exception as e:
            print_error(f"Error pulling {model}: {e}")
    
    print_success("Ollama model check complete")
    return True

def start_database():
    """Start PostgreSQL database using Docker Compose"""
    print_header("Starting PostgreSQL Database")
    
    if not check_docker():
        return False
    
    try:
        # Navigate to infrastructure directory
        infrastructure_dir = Path(__file__).parent / "infrastructure"
        
        print_info("Starting database containers...")
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=infrastructure_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        print_success("Database containers started")
        
        # Wait for database to be ready
        print_info("Waiting for database to be ready (5 seconds)...")
        time.sleep(5)
        
        # Check if containers are running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=bulldog-buddy-db", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "Up" in result.stdout:
            print_success("PostgreSQL is running on port 5432")
            print_success("pgAdmin is running on http://localhost:8080")
            print_success("Adminer is running on http://localhost:8081")
            return True
        else:
            print_error("Database failed to start")
            return False
            
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to start database: {e}")
        if e.stderr:
            print(e.stderr)
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def start_api_bridge():
    """Start the FastAPI bridge server"""
    print_header("Starting API Bridge Server")
    
    project_root = Path(__file__).parent
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print_error("Virtual environment not found")
        print_info("Please create a virtual environment first")
        return None
    
    print_info("Starting API Bridge on port 8001...")
    
    # Start API bridge in a new PowerShell window
    cmd = f'powershell -NoExit -Command "cd \'{project_root}\'; Write-Host \'API Bridge Starting...\' -ForegroundColor Cyan; .\.venv\Scripts\python.exe -m uvicorn api.bridge_server_enhanced:app --host 127.0.0.1 --port 8001"'
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=project_root
    )
    
    time.sleep(3)
    print_success("API Bridge started on http://127.0.0.1:8001")
    
    return process

def start_frontend():
    """Start the Express frontend server"""
    print_header("Starting Frontend Server")
    
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"
    
    if not (frontend_dir / "node_modules").exists():
        print_error("Node modules not found")
        print_info("Please run 'npm install' in the frontend directory first")
        return None
    
    print_info("Starting Frontend on port 3000...")
    
    # Start frontend in a new PowerShell window
    cmd = f'powershell -NoExit -Command "cd \'{frontend_dir}\'; Write-Host \'Frontend Server Starting...\' -ForegroundColor Green; node server.js"'
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=frontend_dir
    )
    
    time.sleep(3)
    print_success("Frontend started on http://localhost:3000")
    
    return process

def main():
    """Main startup sequence"""
    print_header("Bulldog Buddy - System Startup")
    
    # Step 0: Check and pull Ollama models
    if not check_ollama_models():
        print_error("Ollama models check failed. System may not work properly.")
        print_info("You can continue, but AI features may not work.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Step 1: Start database
    if not start_database():
        print_error("Failed to start database. Exiting.")
        sys.exit(1)
    
    # Step 2: Start API Bridge
    api_process = start_api_bridge()
    if not api_process:
        print_error("Failed to start API Bridge. Exiting.")
        sys.exit(1)
    
    # Step 3: Start Frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print_error("Failed to start Frontend. Exiting.")
        sys.exit(1)
    
    # Print summary
    print_header("System Started Successfully!")
    print()
    print(f"{Colors.BOLD}Access the application:{Colors.END}")
    print(f"  {Colors.GREEN}→ Frontend:    {Colors.END}http://localhost:3000")
    print(f"  {Colors.GREEN}→ API Health:  {Colors.END}http://127.0.0.1:8001/api/health")
    print(f"  {Colors.GREEN}→ pgAdmin:     {Colors.END}http://localhost:8080")
    print(f"  {Colors.GREEN}→ Adminer:     {Colors.END}http://localhost:8081")
    print()
    print(f"{Colors.BOLD}Database Credentials:{Colors.END}")
    print(f"  {Colors.CYAN}Host:{Colors.END}     localhost")
    print(f"  {Colors.CYAN}Port:{Colors.END}     5432")
    print(f"  {Colors.CYAN}Database:{Colors.END} bulldog_buddy")
    print(f"  {Colors.CYAN}User:{Colors.END}     postgres")
    print(f"  {Colors.CYAN}Password:{Colors.END} bulldog_buddy_password_2025")
    print()
    print(f"{Colors.BOLD}Test Login:{Colors.END}")
    print(f"  {Colors.CYAN}Email:{Colors.END}    test@example.com")
    print(f"  {Colors.CYAN}Password:{Colors.END} testpassword123")
    print()
    print(f"{Colors.YELLOW}Press Ctrl+C to view this summary again{Colors.END}")
    print(f"{Colors.YELLOW}Close the PowerShell windows to stop services{Colors.END}")
    print()
    
    # Keep script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("System is still running in separate windows.")
        print("Close the PowerShell windows to stop services.")
        print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown initiated...")
        sys.exit(0)
