"""
Bulldog Buddy System Startup Script
Starts all services and provides status check
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

def check_service(name, url, timeout=30):
    """Check if a service is running"""
    print(f"Checking {name}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is running at {url}")
                return True
        except requests.exceptions.RequestException:
            time.sleep(2)
    print(f"❌ {name} failed to start at {url}")
    return False

def main():
    print("=" * 60)
    print("🐶 Bulldog Buddy System Startup")
    print("=" * 60)
    
    # Check Docker containers
    print("\n1️⃣ Checking Docker containers...")
    result = subprocess.run(
        ["docker-compose", "ps"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent / "infrastructure"
    )
    print(result.stdout)
    
    # Start API Bridge
    print("\n2️⃣ Starting API Bridge Server...")
    print("Command: python -m uvicorn api.bridge_server:app --host 127.0.0.1 --port 8001")
    print("Please start this in a separate terminal window")
    print("Waiting for API Bridge to be ready...")
    time.sleep(5)
    
    api_running = check_service(
        "API Bridge",
        "http://127.0.0.1:8001/api/health"
    )
    
    # Start Frontend
    print("\n3️⃣ Starting Frontend Server...")
    print("Command: cd frontend && node server.js")
    print("Please start this in a separate terminal window")
    print("Waiting for Frontend to be ready...")
    time.sleep(5)
    
    frontend_running = check_service(
        "Frontend Server",
        "http://127.0.0.1:3000"
    )
    
    # Print Status Summary
    print("\n" + "=" * 60)
    print("📊 System Status Summary")
    print("=" * 60)
    print(f"Database (PostgreSQL):    {'✅ Running' if True else '❌ Not Running'}")
    print(f"API Bridge (Port 8001):   {'✅ Running' if api_running else '❌ Not Running'}")
    print(f"Frontend (Port 3000):     {'✅ Running' if frontend_running else '❌ Not Running'}")
    
    print("\n" + "=" * 60)
    print("🚀 Next Steps:")
    print("=" * 60)
    print("1. Open browser to: http://localhost:3000")
    print("2. Test credentials:")
    print("   Email: test@example.com")
    print("   Password: testpassword123")
    print("\n3. If services aren't running, start them manually:")
    print("   - API Bridge: .venv\\Scripts\\python.exe -m uvicorn api.bridge_server:app --host 127.0.0.1 --port 8001")
    print("   - Frontend:   cd frontend && node server.js")
    print("=" * 60)

if __name__ == "__main__":
    main()
