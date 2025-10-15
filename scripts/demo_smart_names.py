"""
Demo script showing the smart name usage system in action
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.enhanced_rag_system import EnhancedRAGSystem
import os

def demo_smart_name_usage():
    print("\n" + "="*80)
    print("SMART NAME USAGE SYSTEM DEMO")
    print("="*80 + "\n")
    
    # Initialize RAG system
    handbook_path = project_root / "data" / "student-handbook-structured.csv"
    rag = EnhancedRAGSystem(str(handbook_path), model_name="gemma3:latest")
    rag.set_user_context(1)  # Set user ID
    
    print("Simulating a conversation with 8 exchanges...")
    print("(Name is: Matthew)\n")
    print("="*80 + "\n")
    
    # Simulate conversation exchanges
    simulated_exchanges = [
        ("Exchange 1", "What are the grading policies?"),
        ("Exchange 2", "What about incomplete grades?"),
        ("Exchange 3", "How do I handle absences?"),
        ("Exchange 4", "What are the tuition fees?"),
        ("Exchange 5", "Can I get a refund?"),
        ("Exchange 6", "What about payment plans?"),
        ("Exchange 7", "How do I register?"),
        ("Exchange 8", "What documents do I need?"),
    ]
    
    for exchange_num, question in simulated_exchanges:
        # Get greeting for this exchange
        greeting = rag.get_context_aware_greeting(force_name=False)
        
        # Show the greeting that would be used
        print(f"{exchange_num}: \"{question}\"")
        if greeting:
            print(f"   → Greeting: \"{greeting}\"")
        else:
            print(f"   → Greeting: (none - direct answer)")
        
        # Check if name was used
        if "Matthew" in greeting:
            print(f"   ✓ Name USED (strategic timing)")
        else:
            print(f"   ○ Name not used (avoiding repetition)")
        
        # Add to history to simulate conversation flow
        rag._add_to_conversation_history(question, f"{greeting}Response content here...")
        print()
    
    print("="*80)
    print("PATTERN ANALYSIS")
    print("="*80 + "\n")
    
    print("Name Usage Pattern:")
    print("  Exchange 1: ✓ Uses name (first interaction)")
    print("  Exchange 2: ○ Alternate greeting")
    print("  Exchange 3: ○ Alternate greeting")
    print("  Exchange 4: ○ Alternate greeting")
    print("  Exchange 5: ✓ Uses name (every 4th exchange)")
    print("  Exchange 6: ○ Alternate greeting")
    print("  Exchange 7: ○ Alternate greeting")
    print("  Exchange 8: ○ Alternate greeting\n")
    
    print("Alternate Greetings Cycle:")
    print("  1. \"Woof! \"")
    print("  2. \"Hey there! \"")
    print("  3. (no greeting - direct answer)")
    print("  4. \"Sure! \"")
    print("  5. \"Absolutely! \"\n")
    
    print("="*80)
    print("BENEFITS")
    print("="*80 + "\n")
    
    print("✅ Natural conversation flow")
    print("✅ Name used strategically, not repetitively")
    print("✅ Varied greetings prevent monotony")
    print("✅ Feels more human-like")
    print("✅ Avoids robotic 'Hey Name!' in every response\n")
    
    print("="*80)
    print("COMPARISON")
    print("="*80 + "\n")
    
    print("OLD SYSTEM (Repetitive):")
    print("  Q1: Hey Matthew! ...")
    print("  Q2: Hey Matthew! ...")
    print("  Q3: Hey Matthew! ...")
    print("  Q4: Hey Matthew! ...\n")
    
    print("NEW SYSTEM (Smart):")
    print("  Q1: Hey Matthew! ...")
    print("  Q2: Sure! ...")
    print("  Q3: Woof! ...")
    print("  Q4: Hey there! ...\n")
    
    print("="*80)
    print("TECHNICAL DETAILS")
    print("="*80 + "\n")
    
    print("Logic:")
    print("  - Use name if: exchange_count % 4 == 0 OR first exchange")
    print("  - Otherwise: cycle through alternate greetings")
    print("  - Can force name for specific query types (force_name=True)\n")
    
    print("Integration:")
    print("  - All query handlers use get_context_aware_greeting()")
    print("  - Greeting passed to prompt with instruction: 'use exactly as provided'")
    print("  - AI cannot override or add name again\n")

if __name__ == "__main__":
    try:
        demo_smart_name_usage()
        
        print("\n💡 To see this live:")
        print("   1. Start system: start_all.bat")
        print("   2. Introduce yourself: 'My name is [YourName]'")
        print("   3. Ask multiple questions")
        print("   4. Notice natural name usage pattern\n")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
