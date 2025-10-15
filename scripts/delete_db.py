"""
Force delete ChromaDB directory
"""
import shutil
from pathlib import Path
import time

db_path = Path("enhanced_chroma_db")

if db_path.exists():
    print(f"🗑️  Deleting {db_path}...")
    try:
        shutil.rmtree(db_path)
        print("✅ Deleted successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTrying again after 1 second...")
        time.sleep(1)
        try:
            shutil.rmtree(db_path)
            print("✅ Deleted successfully on second try!")
        except Exception as e2:
            print(f"❌ Still failed: {e2}")
else:
    print(f"✅ {db_path} does not exist")
