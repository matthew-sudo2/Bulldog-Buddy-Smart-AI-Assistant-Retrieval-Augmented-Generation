import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate

class EnhancedRAGSystem:
    """Enhanced RAG system using LangChain for better retrieval and QA"""
    
    # Available models configuration
    AVAILABLE_MODELS = {
        "gemma3:latest": {
            "name": "Gemma 3",
            "description": "Google's Gemma 3 - Balanced performance, good for general tasks",
            "temperature": 0.3
        },
        "llama3.2:latest": {
            "name": "Llama 3.2", 
            "description": "Meta's Llama 3.2 - Excellent reasoning and comprehensive responses",
            "temperature": 0.2
        }
    }
    
    def __init__(self, handbook_path: str, db_path: str = "./enhanced_chroma_db", model_name: str = "gemma3:latest"):
        self.handbook_path = handbook_path
        self.db_path = db_path
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        
        # Validate model
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model {model_name} not supported. Available models: {list(self.AVAILABLE_MODELS.keys())}")
        
        # Initialize components
        self.vectorstore = None
        self.qa_chain = None
        self.conversational_chain = None
        self.is_initialized = False
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(model="embeddinggemma:latest")
        
        # Initialize LLM with selected model
        model_config = self.AVAILABLE_MODELS[model_name]
        self.llm = OllamaLLM(
            model=model_name,
            temperature=model_config["temperature"],
        )
        
        # Text splitter for better chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", ".", " ", ""],
            length_function=len,
        )
        
        # Conversation memory
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Remember last 10 exchanges
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
    def initialize_database(self, force_rebuild: bool = False):
        """Initialize the enhanced vector database with LangChain"""
        try:
            # Check if database already exists
            if os.path.exists(self.db_path) and not force_rebuild:
                try:
                    # Load existing vectorstore
                    self.vectorstore = Chroma(
                        persist_directory=self.db_path,
                        embedding_function=self.embeddings
                    )
                    
                    # Check if it has content
                    collection = self.vectorstore._collection
                    if collection.count() > 0:
                        self.logger.info(f"Loaded existing database with {collection.count()} documents")
                        self._initialize_chains()
                        self.is_initialized = True
                        return True
                except Exception as e:
                    self.logger.warning(f"Failed to load existing database: {e}")
            
            self.logger.info("Creating new enhanced RAG database...")
            
            # Process CSV directly (our current format)
            documents = self._process_csv_content()
            
            # Create vectorstore
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.db_path
            )
            
            # Note: persist() is automatic in newer versions of Chroma
            
            # Initialize QA chains
            self._initialize_chains()
            
            self.is_initialized = True
            self.logger.info(f"Enhanced RAG database initialized with {len(documents)} documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced database: {e}")
            return False
    
    def _process_csv_content(self) -> List[Document]:
        """Process structured CSV content into LangChain Documents"""
        try:
            df = pd.read_csv(self.handbook_path)
            documents = []
            
            for _, row in df.iterrows():
                # Create content combining title and content
                content = f"Section: {row.get('title', '')}\n\n{row.get('content', '')}"
                
                # Create metadata
                metadata = {
                    'section_number': str(row.get('section_number', '')),
                    'section_type': str(row.get('section_type', '')),
                    'title': str(row.get('title', '')),
                    'category': str(row.get('category', 'General')),
                    'word_count': int(row.get('word_count', 0)),
                    'source': 'Student Handbook'
                }
                
                # Split content into chunks if it's too long
                chunks = self.text_splitter.split_text(content)
                
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_id'] = i
                    chunk_metadata['total_chunks'] = len(chunks)
                    
                    documents.append(Document(
                        page_content=chunk,
                        metadata=chunk_metadata
                    ))
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error processing CSV content: {e}")
            return []
    
    def _initialize_chains(self):
        """Initialize the QA and conversational chains"""
        # Custom prompt template for better responses
        custom_prompt = PromptTemplate(
            template="""You are Bulldog Buddy, a friendly and loyal Smart Campus Assistant. 

Use the context below only as background knowledge when helpful:

Context: {context}

Question: {question}

Instructions:
- Always answer as if you already know the information (never mention the context or handbook directly)
- Be enthusiastic and supportive with a bulldog personality
- Use "Woof!" occasionally but naturally
- Provide accurate and concise answers
- If the context doesn't contain relevant information, be honest about it
- Use emojis appropriately (🐶, 🐾, 📚, 🏫)
- Keep responses helpful and student-focused

Bulldog Buddy's Answer:""",
            input_variables=["context", "question"]
        )
        
        # Initialize RetrievalQA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 8}  
            ),
            return_source_documents=True,
            chain_type_kwargs={"prompt": custom_prompt}
        )
        
        # Initialize Conversational Retrieval Chain
        self.conversational_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 8}),  # Increased from 5 to 8
            memory=self.memory,
            return_source_documents=True,
            verbose=True
        )
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """Get information about the currently selected model"""
        model_config = self.AVAILABLE_MODELS[self.model_name]
        return {
            "model_name": self.model_name,
            "display_name": model_config["name"],
            "description": model_config["description"],
            "temperature": model_config["temperature"],
            "is_initialized": self.is_initialized
        }
    
    def switch_model(self, new_model_name: str) -> bool:
        """Switch to a different model"""
        try:
            if new_model_name not in self.AVAILABLE_MODELS:
                self.logger.error(f"Model {new_model_name} not supported")
                return False
            
            if new_model_name == self.model_name:
                self.logger.info(f"Already using model {new_model_name}")
                return True
            
            # Update model configuration
            self.model_name = new_model_name
            model_config = self.AVAILABLE_MODELS[new_model_name]
            
            # Create new LLM instance
            self.llm = OllamaLLM(
                model=new_model_name,
                temperature=model_config["temperature"],
            )
            
            # Re-initialize chains if database is ready
            if self.is_initialized and self.vectorstore:
                self._initialize_chains()
            
            self.logger.info(f"Successfully switched to model: {new_model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to switch model: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> Dict[str, Dict[str, str]]:
        """Get list of available models"""
        return cls.AVAILABLE_MODELS
    
    def ask_question(self, question: str, use_conversation_history: bool = True) -> Dict[str, Any]:
        """Ask a question and get an enhanced response with sources"""
        if not self.is_initialized:
            if not self.initialize_database():
                return {
                    "answer": "Woof! I'm having trouble accessing my knowledge base right now. 🐶",
                    "source_documents": [],
                    "confidence": 0.0
                }
        
        try:
            # Check if this is a financial/tuition query and handle specially
            if self._is_financial_query(question):
                return self._handle_financial_query(question)
            
            # Check if this is a university-specific query or general knowledge question
            if self._is_university_specific_query(question):
                # Use RAG for university-specific questions
                if use_conversation_history and self.conversational_chain:
                    # Use conversational chain for follow-up questions
                    result = self.conversational_chain({
                        "question": question
                    })
                else:
                    # Use simple QA chain
                    result = self.qa_chain({
                        "query": question
                    })
                
                # Extract source information
                source_docs = result.get("source_documents", [])
                sources = []
                
                for doc in source_docs:
                    sources.append({
                        "title": doc.metadata.get("title", "Unknown Section"),
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "category": doc.metadata.get("category", "General"),
                        "section_number": doc.metadata.get("section_number", ""),
                    })
                
                return {
                    "answer": result.get("answer", result.get("result", "")),
                    "source_documents": sources,
                    "confidence": self._calculate_confidence(question, source_docs)
                }
            else:
                # Handle general knowledge questions without forcing handbook context
                return self._handle_general_query(question)
            
        except Exception as e:
            self.logger.error(f"Error in ask_question: {e}")
            return {
                "answer": f"Woof! I encountered an error: {str(e)} 🐶",
                "source_documents": [],
                "confidence": 0.0
            }
    
    def stream_answer(self, question: str):
        """Stream answer for typewriter effect"""
        if not self.is_initialized:
            if not self.initialize_database():
                yield "Woof! I'm having trouble accessing my knowledge base right now. 🐶"
                return
        
        try:
            # Get the full response first
            response = self.ask_question(question, use_conversation_history=True)
            answer = response["answer"]
            
            # Stream the answer word by word
            words = answer.split()
            for i, word in enumerate(words):
                if i == 0:
                    yield word
                else:
                    yield " " + word
                    
        except Exception as e:
            error_msg = f"Woof! I encountered an error: {str(e)} 🐶"
            yield error_msg
    
    def _calculate_confidence(self, question: str, source_docs: List[Document]) -> float:
        """Calculate confidence score based on source relevance"""
        if not source_docs:
            return 0.0
        
        # Simple confidence calculation based on:
        # - Number of sources found
        # - Length of source content
        # - Presence of question keywords in sources
        
        question_words = set(question.lower().split())
        
        total_score = 0
        for doc in source_docs:
            doc_words = set(doc.page_content.lower().split())
            overlap = len(question_words.intersection(doc_words))
            total_score += overlap / max(len(question_words), 1)
        
        # Normalize between 0 and 1
        confidence = min(total_score / len(source_docs), 1.0)
        return round(confidence, 2)
    
    def clear_conversation_history(self):
        """Clear the conversation memory"""
        self.memory.clear()
        self.logger.info("Conversation history cleared")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get enhanced database statistics"""
        try:
            if not self.is_initialized or not self.vectorstore:
                return {"status": "not_initialized"}
            
            collection = self.vectorstore._collection
            count = collection.count()
            
            # Get some sample metadata for analysis
            sample_docs = self.vectorstore.similarity_search("", k=min(count, 10))
            categories = set()
            sections = set()
            
            for doc in sample_docs:
                categories.add(doc.metadata.get("category", "General"))
                sections.add(doc.metadata.get("title", "Unknown"))
            
            return {
                "status": "initialized",
                "total_documents": count,
                "unique_categories": len(categories),
                "unique_sections": len(sections),
                "categories": list(categories),
                "database_type": "Enhanced LangChain ChromaDB",
                "memory_size": len(self.memory.buffer) if self.memory else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def search_by_category(self, category: str, question: str = "", top_k: int = 5) -> List[Dict]:
        """Search within a specific category"""
        if not self.is_initialized:
            return []
        
        try:
            # Use metadata filtering if available
            retriever = self.vectorstore.as_retriever(
                search_kwargs={
                    "k": top_k,
                    "filter": {"category": category}
                }
            )
            
            # If no specific question, get general content from category
            if not question:
                question = f"information about {category}"
            
            docs = retriever.get_relevant_documents(question)
            
            results = []
            for doc in docs:
                results.append({
                    "title": doc.metadata.get("title", "Unknown"),
                    "content": doc.page_content,
                    "category": doc.metadata.get("category", "General"),
                    "section_number": doc.metadata.get("section_number", "")
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching by category: {e}")
            return []
    
    def _is_financial_query(self, question: str) -> bool:
        """Check if question is about financial matters"""
        financial_keywords = [
            'tuition', 'fees', 'cost', 'payment', 'financial', 'money', 'price', 
            'charges', 'schedule of fees', 'how much', 'expensive', 'pay'
        ]
        return any(keyword in question.lower() for keyword in financial_keywords)
    
    def _is_university_specific_query(self, question: str) -> bool:
        """Check if question is about university-specific matters that would be in the handbook"""
        university_keywords = [
            # Academic terms
            'university', 'college', 'campus', 'student', 'academic', 'semester', 'course', 'class',
            'enrollment', 'registration', 'transcript', 'grade', 'gpa', 'credit', 'degree',
            'major', 'minor', 'graduation', 'diploma', 'faculty', 'professor', 'instructor',
            
            # University services & facilities
            'library', 'dormitory', 'housing', 'cafeteria', 'bookstore', 'parking', 'shuttle',
            'health center', 'counseling', 'financial aid', 'scholarship', 'loan',
            
            # University policies & procedures  
            'policy', 'procedure', 'requirement', 'prerequisite', 'deadline', 'application',
            'admission', 'transfer', 'withdrawal', 'drop', 'add', 'schedule',
            
            # University-specific terms that might be in handbook
            'bulldog', 'handbook', 'catalog', 'syllabus', 'orientation', 'advising'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in university_keywords)
    
    def _handle_general_query(self, question: str) -> Dict[str, Any]:
        """Handle general knowledge questions without forcing handbook context"""
        try:
            # Create a general prompt that doesn't force handbook usage
            general_prompt = f"""You are Bulldog Buddy, a friendly and knowledgeable Smart Campus Assistant! 

Question: {question}

Instructions:
- Answer this question using your general knowledge
- Be enthusiastic and supportive with a bulldog personality  
- Use "Woof!" occasionally but naturally
- Provide accurate, helpful, and educational answers
- Use emojis appropriately (🐶, 🐾, 📚, 🧠, 💡)
- Keep responses informative yet friendly
- If you don't know something, be honest about it

Bulldog Buddy's Answer:"""

            # Get response from LLM without forcing handbook context
            response = self.llm.invoke(general_prompt)
            
            return {
                "answer": response,
                "source_documents": [],  # No handbook sources for general questions
                "confidence": 0.8  # Good confidence for general knowledge
            }
            
        except Exception as e:
            self.logger.error(f"Error in general query handler: {e}")
            return {
                "answer": "Woof! I encountered an error while thinking about that question. Please try again! 🐶",
                "source_documents": [],
                "confidence": 0.0
            }
    
    def _handle_financial_query(self, question: str) -> Dict[str, Any]:
        """Handle financial queries with targeted search"""
        try:
            # Try to get Section 4.1 directly first (Schedule of Fees)
            section_41_docs = self.vectorstore.similarity_search(
                "Section 4.1: Schedule of Fees and Other Charges",
                k=1
            )
            
            # Also get other financial documents
            financial_docs = self.vectorstore.similarity_search(
                question,
                k=5,
                filter={"category": "Financial"}
            )
            
            # Combine and prioritize Section 4.1
            all_docs = section_41_docs + [doc for doc in financial_docs if doc not in section_41_docs]
            
            if all_docs:
                # Create context from financial documents
                context_parts = []
                for doc in all_docs[:3]:  # Use top 3 documents
                    context_parts.append(f"Section: {doc.metadata.get('title', 'Unknown')}\n\n{doc.page_content}")
                
                context = "\n\n".join(context_parts)
                
                # Create a focused prompt for financial queries
                prompt = f"""You are Bulldog Buddy, a friendly and loyal Smart Campus Assistant.

                Use the context below only as background knowledge when helpful:

Context: {context}

Question: {question}

Instructions:
- Always answer as if you already know the information (never mention the context or handbook directly)
- Be enthusiastic and supportive with a bulldog personality
- Use "Woof!" occasionally but naturally
- Provide accurate and concise answers
- If the context doesn’t provide relevant info, be honest and guide the student where possible
- Use emojis appropriately (🐶, 🐾, 📚, 🏫)
- Keep responses helpful and student-focused
"""
                response = self.llm.invoke(prompt)
                
                # Format source documents
                sources = []
                for doc in all_docs[:3]:
                    sources.append({
                        "title": doc.metadata.get("title", "Unknown Section"),
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "category": doc.metadata.get("category", "Financial"),
                        "section_number": doc.metadata.get("section_number", ""),
                    })
                
                return {
                    "answer": response,
                    "source_documents": sources,
                    "confidence": 0.9  # High confidence for targeted financial search
                }
            
            # Fallback if no financial docs found
            return {
                "answer": "Woof! I'm having trouble finding specific financial information right now. Please try asking about 'Schedule of Fees' or check with the Finance Office directly. 🐶💰",
                "source_documents": [],
                "confidence": 0.1
            }
            
        except Exception as e:
            self.logger.error(f"Error in financial query handler: {e}")
            return {
                "answer": "Woof! I encountered an error while searching for financial information. Please try again! 🐶",
                "source_documents": [],
                "confidence": 0.0
            }

# Test function
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test the enhanced RAG system
    rag = EnhancedRAGSystem("./data/student-handbook-structured.csv")
    
    success = rag.initialize_database(force_rebuild=True)
    print(f"Initialization: {'Success' if success else 'Failed'}")
    
    if success:
        # Test question
        response = rag.ask_question("What are the tuition fees?")
        print(f"\nAnswer: {response['answer']}")
        print(f"Confidence: {response['confidence']}")
        print(f"Sources: {len(response['source_documents'])}")
