"""
Test script to verify model switching functionality in the Enhanced RAG system
"""

import sys
sys.path.append('.')

from models.enhanced_rag_system import EnhancedRAGSystem
import logging

# Reduce noise
logging.basicConfig(level=logging.ERROR)

def test_model_switching():
    print("🧪 Testing Model Switching Functionality")
    print("=" * 60)
    
    # Test available models
    print("📋 Available Models:")
    available_models = EnhancedRAGSystem.get_available_models()
    for model_key, model_info in available_models.items():
        print(f"   • {model_info['name']} ({model_key})")
        print(f"     Description: {model_info['description']}")
        print(f"     Temperature: {model_info['temperature']}")
        print()
    
    print("-" * 60)
    
    # Test creating system with different models
    models_to_test = ["gemma3:latest"]  # Start with available model
    
    # Check if llama3.2:latest is available by trying to create system
    try:
        print("🔍 Testing Llama 3.2 availability...")
        test_rag = EnhancedRAGSystem('data/student-handbook-structured.csv', model_name="llama3.2:latest")
        models_to_test.append("llama3.2:latest")
        print("✅ Llama 3.2 is available!")
        del test_rag
    except Exception as e:
        print(f"⚠️  Llama 3.2 not available: {e}")
        print("   (This is normal if the model hasn't been downloaded)")
    
    print("-" * 60)
    
    # Test each available model
    for model_name in models_to_test:
        print(f"\n🤖 Testing Model: {model_name}")
        print("-" * 40)
        
        try:
            # Create RAG system with specific model
            rag = EnhancedRAGSystem('data/student-handbook-structured.csv', model_name=model_name)
            
            # Get model info
            model_info = rag.get_current_model_info()
            print(f"✅ Model initialized successfully!")
            print(f"   Display Name: {model_info['display_name']}")
            print(f"   Description: {model_info['description']}")
            print(f"   Temperature: {model_info['temperature']}")
            
            # Test model switching
            if len(models_to_test) > 1:
                other_models = [m for m in models_to_test if m != model_name]
                if other_models:
                    switch_to = other_models[0]
                    print(f"\n🔄 Testing switch to {switch_to}...")
                    success = rag.switch_model(switch_to)
                    if success:
                        new_info = rag.get_current_model_info()
                        print(f"✅ Successfully switched to {new_info['display_name']}")
                    else:
                        print("❌ Model switch failed")
            
            # Test a simple question (without initializing full database to save time)
            print(f"\n💬 Testing question routing...")
            question = "what is machine learning"
            is_general = not rag._is_university_specific_query(question)
            print(f"   Question: {question}")
            print(f"   Classified as general: {is_general}")
            
            del rag
            
        except Exception as e:
            print(f"❌ Error with model {model_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 Model switching test complete!")

if __name__ == "__main__":
    test_model_switching()
