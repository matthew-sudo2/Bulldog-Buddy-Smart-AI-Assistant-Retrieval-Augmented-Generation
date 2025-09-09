"""
Demo script showing the difference between Gemma 3 and Llama 3.2 models
"""

import sys
sys.path.append('.')

from models.enhanced_rag_system import EnhancedRAGSystem
import logging
import time

# Reduce noise
logging.basicConfig(level=logging.ERROR)

def demo_model_comparison():
    print("🎭 Model Comparison Demo")
    print("=" * 50)
    
    # Test questions
    test_questions = [
        "What is machine learning?",
        "Explain the difference between AI and machine learning",
        "What are the university admission requirements?"  # This will use handbook
    ]
    
    models_to_test = ["gemma3:latest", "llama3.2:latest"]
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        print("=" * 60)
        
        for model_name in models_to_test:
            print(f"\n🤖 {model_name.upper().replace(':', ' ').replace('.', '.')} Response:")
            print("-" * 50)
            
            try:
                # Create RAG system with specific model
                rag = EnhancedRAGSystem('data/student-handbook-structured.csv', model_name=model_name)
                
                # Get response (without full database initialization to save time)
                if "admission" in question.lower():
                    print("📚 [This would use the student handbook - initializing database...]")
                    rag.initialize_database()
                    response = rag.ask_question(question, use_conversation_history=False)
                    answer = response['answer'][:300] + "..." if len(response['answer']) > 300 else response['answer']
                    sources = len(response['source_documents'])
                    print(f"Answer: {answer}")
                    print(f"Sources used: {sources}")
                else:
                    print("🧠 [Using general knowledge - no handbook needed]")
                    response = rag._handle_general_query(question)
                    answer = response['answer'][:300] + "..." if len(response['answer']) > 300 else response['answer']
                    print(f"Answer: {answer}")
                
                del rag
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n" + "~" * 60)
    
    print(f"\n🎯 Demo complete! Try both models in the Streamlit app to see the full responses!")
    print(f"🌐 App URL: http://localhost:8504")

if __name__ == "__main__":
    demo_model_comparison()
