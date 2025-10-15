"""
Interactive demo showing the name personalization feature
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.user_context import UserContextManager
from models.enhanced_rag_system import EnhancedRAGSystem
import os

def demo_name_personalization():
    """Demonstrate the complete name personalization workflow"""
    
    print("\n" + "="*70)
    print("BULLDOG BUDDY - NAME PERSONALIZATION FEATURE DEMO")
    print("="*70 + "\n")
    
    # Initialize components
    print("🔧 Initializing components...")
    context_manager = UserContextManager()
    
    # Simulate a new user (ID 1 - typically exists in database)
    user_id = 1
    
    print("✅ Components initialized\n")
    
    # Demo 1: User introduces themselves
    print("="*70)
    print("DEMO 1: User Introduces Themselves")
    print("="*70 + "\n")
    
    message1 = "Hi! My name is Matthew and I have a question about grades"
    print(f"User says: \"{message1}\"\n")
    
    # Extract name
    extracted = context_manager.extract_user_info(message1, user_id)
    if 'name' in extracted:
        name = extracted['name']['value']
        print(f"✅ System extracted name: '{name}'")
        print(f"   Confidence: {extracted['name']['confidence']}")
        print(f"   Stored in database: user_context table\n")
    
    # Show how it would be used in a response
    context_prompt = context_manager.build_context_prompt(user_id)
    print("📝 Context prompt that will be sent to AI:")
    print("-" * 70)
    print(context_prompt[:300] + "..." if len(context_prompt) > 300 else context_prompt)
    print("-" * 70 + "\n")
    
    # Demo 2: Follow-up question (name remembered)
    print("="*70)
    print("DEMO 2: Follow-up Question (Name Remembered)")
    print("="*70 + "\n")
    
    message2 = "What about incomplete grades?"
    print(f"User asks: \"{message2}\"\n")
    
    # Get user context
    context_data = context_manager.get_user_context(user_id)
    if context_data and 'name' in context_data:
        name = context_data['name']['value']
        greeting = f"Hey {name}! "
        print(f"✅ System remembers name from previous conversation")
        print(f"   Greeting will be: \"{greeting}\"\n")
        print(f"💬 Response would start with:")
        print(f"   \"{greeting}Woof! Great follow-up question! Let me explain...")
        print(f"   how incomplete grades work...\"\n")
    
    # Demo 3: New session without re-introduction
    print("="*70)
    print("DEMO 3: New Session (Name Still Remembered)")
    print("="*70 + "\n")
    
    print("User starts a new conversation without re-introducing...")
    message3 = "Can you help me understand the tuition fees?"
    print(f"User asks: \"{message3}\"\n")
    
    # System retrieves stored name
    context_data = context_manager.get_user_context(user_id)
    if context_data and 'name' in context_data:
        name = context_data['name']['value']
        print(f"✅ System retrieves name from database: '{name}'")
        print(f"   No need for user to re-introduce themselves!\n")
        print(f"💬 Response:")
        print(f"   \"Hey {name}! Woof! I'd be happy to help you understand")
        print(f"   the tuition fees... 🐶\"\n")
    
    # Demo 4: Fallback to registered username
    print("="*70)
    print("DEMO 4: Fallback to Registered Username")
    print("="*70 + "\n")
    
    # Clear stored name for this demo
    print("Simulating a user who never introduced themselves...")
    
    # Try to get registered name
    registered_name = context_manager.get_user_registered_name(user_id)
    if registered_name:
        print(f"✅ System retrieves registered username: '{registered_name}'")
        print(f"   Source: users table in database\n")
        print(f"💬 Response would use registered name:")
        print(f"   \"Hey {registered_name}! Woof! How can I help you today?\"\n")
    else:
        print(f"ℹ️  No registered name found (user may not exist in database)")
        print(f"   System will use generic greeting: 'Woof!'\n")
    
    # Demo 5: No name available
    print("="*70)
    print("DEMO 5: No Name Available (Graceful Degradation)")
    print("="*70 + "\n")
    
    print("When no name is available from any source...")
    print(f"💬 Response uses friendly generic greeting:")
    print(f"   \"Woof! I'm here to help! What can I assist you with")
    print(f"   today? 🐶\"\n")
    
    print("="*70)
    print("DEMO COMPLETE")
    print("="*70 + "\n")
    
    print("Key Features Demonstrated:")
    print("✓ Automatic name extraction from conversations")
    print("✓ Persistent name memory across sessions")
    print("✓ Fallback to registered username")
    print("✓ Graceful handling when no name available")
    print("✓ Natural, context-aware greetings\n")

if __name__ == "__main__":
    try:
        demo_name_personalization()
        
        print("\n💡 To see this in action with real AI responses:")
        print("   1. Start the system: start_all.bat")
        print("   2. Login/register")
        print("   3. Introduce yourself: 'Hi, my name is [YourName]'")
        print("   4. Ask questions and see personalized responses!\n")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
