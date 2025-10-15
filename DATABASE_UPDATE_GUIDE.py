"""
COMPLETE DATABASE UPDATE GUIDE
===============================

The ChromaDB vector database contains OLD cached embeddings and needs to be completely rebuilt.

STEP-BY-STEP INSTRUCTIONS:
==========================

1. STOP ALL RUNNING SERVICES
   ---------------------------
   - Stop the backend (API bridge server)
   - Stop the frontend
   - Stop any Streamlit instances
   
   In your terminals, press Ctrl+C to stop all running processes.
   OR run: python stop.py


2. DELETE THE OLD DATABASE
   ------------------------
   Once all services are stopped, delete the database folder:
   
   PowerShell command:
   Remove-Item -Recurse -Force "enhanced_chroma_db"
   
   OR manually delete the folder:
   c:\Users\shanaya\Documents\ChatGPT-Clone\Paw-sitive AI\enhanced_chroma_db


3. REBUILD THE DATABASE
   ---------------------
   Run the rebuild script:
   
   python rebuild_database.py
   
   This will:
   - Create a fresh ChromaDB from scratch
   - Read the updated student-handbook-structured.csv
   - Generate new embeddings with:
     ✓ Corrected Dean's List (GWA 3.25, 12 units)
     ✓ Updated Uniform Policy
     ✓ All other current handbook data


4. RESTART THE SYSTEM
   -------------------
   Start your services again:
   
   python start.py
   
   OR start manually:
   - Backend: .\.venv\Scripts\python.exe -m uvicorn api.bridge_server_enhanced:app --host 127.0.0.1 --port 8001
   - Frontend: cd frontend ; node server.js


5. TEST THE CHANGES
   -----------------
   Ask the question: "What is the GWA required for dean's list?"
   
   EXPECTED RESPONSE should mention:
   - GWA of 3.25 minimum
   - Dean's First Honors (GWA 3.50 or higher)
   - Dean's Second Honors (GWA 3.25 to 3.49)
   - 12 academic units minimum
   - No grade below 2.5


WHY THIS IS NECESSARY:
======================
The ChromaDB vector store caches embeddings (mathematical representations) of the handbook content.
Even though we updated the CSV file, the old embeddings are still in the database.
The database must be completely deleted and rebuilt to reflect the new information.


TROUBLESHOOTING:
================
If you get "file in use" errors when deleting:
1. Make absolutely sure ALL Python processes are stopped
2. Check Task Manager for any python.exe, uvicorn, or node processes
3. Close VS Code if it has the folder open
4. Try again to delete the enhanced_chroma_db folder


VERIFICATION:
=============
After rebuilding, the logs should show:
- "Enhanced RAG database initialized with 39 documents"
- Query test should return correct GWA 3.25 information
"""

print(__doc__)
