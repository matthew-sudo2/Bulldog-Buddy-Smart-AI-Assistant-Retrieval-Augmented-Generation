#!/usr/bin/env python3
"""
Bulldog Buddy - Smart AI Assistant Entry Point
Main launcher for the Streamlit application
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add core directory to path
core_dir = project_root / "core"
sys.path.insert(0, str(core_dir))

if __name__ == "__main__":
    # Import and run the Streamlit app
    venv_streamlit = project_root / ".venv" / "Scripts" / "streamlit.exe"
    ui_path = core_dir / "ui.py"
    
    if venv_streamlit.exists():
        # Use subprocess for better path handling
        import subprocess
        subprocess.run([str(venv_streamlit), "run", str(ui_path)])
    else:
        # Fallback to global streamlit
        import subprocess
        subprocess.run(["streamlit", "run", str(ui_path)])