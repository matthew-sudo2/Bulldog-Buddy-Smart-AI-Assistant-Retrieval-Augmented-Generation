"""
Rebuild ChromaDB Vector Database
---------------------------------
This script rebuilds the ChromaDB vector store with updated handbook data.
Use this when you've updated the student-handbook-structured.csv file.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.enhanced_rag_system import EnhancedRAGSystem

def rebuild_database():
    """Rebuild the vector database with updated CSV data"""
    print("=" * 60)
    print("🔄 REBUILDING CHROMADB VECTOR DATABASE")
    print("=" * 60)
    print()
    print("This will:")
    print("  1. Delete the existing ChromaDB database")
    print("  2. Re-read the student-handbook-structured.csv")
    print("  3. Generate new embeddings for all content")
    print("  4. Create a fresh ChromaDB vector store")
    print()
    print("⏱️  This process may take 2-5 minutes...")
    print()
    
    try:
        # Get paths
        handbook_path = project_root / "data" / "student-handbook-structured.csv"
        
        if not handbook_path.exists():
            print(f"❌ ERROR: Handbook file not found at {handbook_path}")
            return False
        
        print(f"📄 Using handbook: {handbook_path}")
        
        # Initialize RAG system with force_rebuild=True
        print("📦 Initializing RAG system...")
        rag_system = EnhancedRAGSystem(
            handbook_path=str(handbook_path),
            model_name="gemma3:latest"
        )
        
        print("🗑️  Deleting old database and rebuilding...")
        success = rag_system.initialize_database(force_rebuild=True)
        
        if success:
            print()
            print("=" * 60)
            print("✅ DATABASE REBUILD SUCCESSFUL!")
            print("=" * 60)
            print()
            print("The ChromaDB vector store has been rebuilt with:")
            print("  ✓ Updated Dean's Honors List requirements (GWA 3.25)")
            print("  ✓ Updated Uniform Policy details")
            print("  ✓ All current handbook information")
            print()
            print("🔄 Please restart your application to use the updated database:")
            print("   1. Stop the current application (Ctrl+C)")
            print("   2. Run: python start.py")
            print()
            return True
        else:
            print()
            print("❌ DATABASE REBUILD FAILED")
            print("Check the logs above for error details.")
            return False
            
    except Exception as e:
        print()
        print("❌ ERROR DURING REBUILD:")
        print(f"   {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    rebuild_database()
