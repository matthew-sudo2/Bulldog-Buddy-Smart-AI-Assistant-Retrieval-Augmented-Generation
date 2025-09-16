import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
import validators
import re
import time

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate

from .web_scraper import WebContentScraper

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
        
        # Web scraping components
        self.web_scraper = WebContentScraper()
        self.web_vectorstore = None  # Temporary store for web content
        
        # Persistent web content memory
        self.active_web_content = {}  # {url: {title, content, vectorstore, timestamp}}
        self.web_session_active = False
        self.current_web_context = []  # List of active URLs for context
        
        # University mode control
        self.university_mode_enabled = True  # Default to university mode
        
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
        
    def _get_enhanced_retriever(self, k: int = 8):
        """Get a custom retriever that uses keyword fallback when embedding search fails"""
        from langchain.schema import BaseRetriever
        
        class EnhancedRetriever(BaseRetriever):
            def __init__(self, rag_system, k=8):
                super().__init__()
                self.rag_system = rag_system
                self.k = k
                
            def _get_relevant_documents(self, query: str, *, run_manager=None):
                try:
                    # First try normal similarity search
                    docs = self.rag_system.vectorstore.similarity_search(query, k=self.k)
                    
                    # Check if we got good results for grading questions
                    if 'grading' in query.lower() or 'grade' in query.lower():
                        # Filter out documents with wrong grading scale
                        good_docs = []
                        for doc in docs:
                            # Skip documents with wrong 1.00-1.24 scale
                            if '1.00-1.24' in doc.page_content:
                                continue
                            good_docs.append(doc)
                        
                        # If we don't have enough good docs, use keyword fallback
                        if len(good_docs) < 2:
                            keywords = ['grading', 'grade', '4.0', 'excellent', 'gpa', 'marks']
                            fallback_docs = self.rag_system._keyword_search_fallback(query, keywords, self.k)
                            # Combine and deduplicate
                            all_docs = good_docs + fallback_docs
                            seen_content = set()
                            unique_docs = []
                            for doc in all_docs:
                                content_key = doc.page_content[:100]  # Use first 100 chars as key
                                if content_key not in seen_content:
                                    seen_content.add(content_key)
                                    unique_docs.append(doc)
                            return unique_docs[:self.k]
                        else:
                            return good_docs
                    
                    return docs
                    
                except Exception as e:
                    # If similarity search fails completely, use keyword fallback
                    self.rag_system.logger.warning(f"Similarity search failed, using keyword fallback: {e}")
                    if 'grading' in query.lower() or 'grade' in query.lower():
                        keywords = ['grading', 'grade', '4.0', 'excellent', 'gpa', 'marks']
                    else:
                        # Extract keywords from query
                        keywords = [word for word in query.lower().split() if len(word) > 3]
                    return self.rag_system._keyword_search_fallback(query, keywords, self.k)
        
        return EnhancedRetriever(self, k)
    
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
        
        # Initialize RetrievalQA chain (back to original)
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
        
        # Initialize Conversational Retrieval Chain (back to original)
        self.conversational_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 8}),
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
        
        # First check if there are URLs in the question
        clean_question, urls = self._detect_urls_in_query(question)
        
        if urls:
            return self.ask_question_with_web_content(question)
        
        # Continue with existing logic for non-web queries
        if not self.is_initialized:
            if not self.initialize_database():
                return {
                    "answer": "Woof! I'm having trouble accessing my knowledge base right now. 🐶",
                    "source_documents": [],
                    "confidence": 0.0
                }
        
        try:
            # If we have active web content and this is not a new web query, consider using web context
            if self.web_session_active and not urls:
                # Check if the question might be related to active web content
                web_relevance = self._is_web_related_query(clean_question)
                if web_relevance > 0.5:  # If likely related to web content
                    return self.ask_question_with_web_content(question)
            
            # Check if this is a financial/tuition query and handle specially
            if self._is_financial_query(clean_question):
                return self._handle_financial_query(clean_question)
            
            # Check if this is a grading system query and handle specially
            if self._is_grading_query(clean_question):
                return self._handle_grading_query(clean_question)
            
            # Check university mode setting to determine how to handle the query
            if self.is_university_mode_enabled():
                # In university mode: Use handbook for all questions
                if use_conversation_history and self.conversational_chain:
                    # Use conversational chain for follow-up questions
                    result = self.conversational_chain({
                        "question": clean_question
                    })
                else:
                    # Use simple QA chain
                    result = self.qa_chain({
                        "query": clean_question
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
                    "confidence": self._calculate_confidence(question, source_docs),
                    "mode": "university"
                }
            else:
                # In general mode: Use AI training data for general knowledge
                return self._handle_general_query(clean_question)
            
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
    
    def _keyword_search_fallback(self, question: str, keywords: List[str], k: int = 5) -> List[Document]:
        """Fallback keyword-based search when embedding search fails"""
        try:
            if not self.vectorstore:
                return []
            
            # Get all documents from the database
            collection = self.vectorstore._collection
            results = collection.get()
            
            # Score documents based on keyword matches
            scored_docs = []
            
            for i, doc_content in enumerate(results['documents']):
                score = 0
                doc_lower = doc_content.lower()
                question_lower = question.lower()
                
                # Score based on keyword matches
                for keyword in keywords:
                    if keyword.lower() in doc_lower:
                        score += 1
                
                # Bonus for question terms
                for word in question_lower.split():
                    if len(word) > 3 and word in doc_lower:
                        score += 0.5
                
                # Extra scoring for specific content patterns
                if 'grading' in question_lower:
                    # Prefer documents with correct 4.0 scale over wrong 1.00-1.24 scale
                    if '4.0:' in doc_content and 'excellent' in doc_lower:
                        score += 10  # Strong preference for correct scale
                    elif '1.00-1.24' in doc_content:
                        score -= 5   # Penalize wrong scale
                
                if score > 0:
                    # Create Document object
                    metadata = results['metadatas'][i] if i < len(results['metadatas']) else {}
                    doc = Document(page_content=doc_content, metadata=metadata)
                    scored_docs.append((score, doc))
            
            # Sort by score and return top k
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for score, doc in scored_docs[:k]]
            
        except Exception as e:
            self.logger.error(f"Error in keyword search fallback: {e}")
            return []
    
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
    
    def _is_grading_query(self, question: str) -> bool:
        """Check if question is about grading system"""
        grading_keywords = [
            'grading system', 'grading scale', 'grade scale', 'grading', 'grades',
            'gpa', 'grade point', 'grading policy', '4.0', 'excellent', 'grade meaning',
            'what does 4.0 mean', 'how does grading work', 'grade conversion'
        ]
        return any(keyword in question.lower() for keyword in grading_keywords)
    
    def _handle_grading_query(self, question: str) -> Dict[str, Any]:
        """Handle grading system queries with enhanced search"""
        try:
            # Use keyword search to find the correct grading system documents
            keywords = ['grading', 'grade', '4.0', 'excellent', 'gpa', 'marks', 'scale']
            docs = self._keyword_search_fallback(question, keywords, k=5)
            
            if not docs:
                return {
                    "answer": "I don't have specific information about the grading system in my current knowledge base.",
                    "source_documents": [],
                    "confidence": 0.1
                }
            
            # Create context from the found documents
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Create a grading-specific prompt
            grading_prompt = f"""Use the following pieces of context to answer the question about the grading system. Be specific and accurate.

Context: {context}

Question: {question}

Helpful Answer:"""
            
            # Get response from LLM
            response = self.llm(grading_prompt)
            
            # Calculate confidence based on document relevance
            confidence = min(0.9, len(docs) * 0.15)
            
            # Format source documents
            sources = []
            for doc in docs:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "category": doc.metadata.get("category", "Unknown")
                })
            
            return {
                "answer": response,
                "source_documents": docs,
                "sources": sources,
                "confidence": confidence,
                "query_type": "grading_enhanced"
            }
            
        except Exception as e:
            self.logger.error(f"Error in grading query handler: {e}")
            return {
                "answer": "I encountered an error while looking up grading information.",
                "source_documents": [],
                "confidence": 0.0
            }
    
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
            'admission', 'transfer', 'withdrawal', 'drop', 'schedule',
            
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
                "confidence": 0.8,  # Good confidence for general knowledge
                "mode": "general"
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
    
    def _detect_urls_in_query(self, query: str) -> tuple[str, List[str]]:
        """
        Detect URLs in user query and separate them from the question
        Returns: (clean_question, list_of_urls)
        """
        # URL regex pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        simple_url_pattern = r'(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        
        urls = []
        
        # Find HTTP/HTTPS URLs
        http_urls = re.findall(url_pattern, query)
        urls.extend(http_urls)
        
        # Find simple URLs (www.example.com or example.com)
        simple_urls = re.findall(simple_url_pattern, query)
        for url in simple_urls:
            if not url.startswith('http'):
                # Check if it's a valid domain-like structure
                if validators.url('http://' + url):
                    urls.append(url)
        
        # Remove URLs from query to get clean question
        clean_query = query
        for url in urls:
            clean_query = clean_query.replace(url, '').strip()
        
        # Clean up multiple spaces and conjunctions
        clean_query = re.sub(r'\s+', ' ', clean_query)
        clean_query = re.sub(r'^(and|or|also|plus|additionally)\s+', '', clean_query, flags=re.IGNORECASE)
        clean_query = clean_query.strip()
        
        return clean_query, urls
    
    def _process_web_content(self, urls: List[str]) -> List[Document]:
        """Process web content into documents for vector search"""
        documents = []
        
        for url in urls:
            try:
                # Scrape website
                scraped_data = self.web_scraper.scrape_website(url)
                
                if "error" in scraped_data:
                    self.logger.warning(f"Failed to scrape {url}: {scraped_data['error']}")
                    continue
                
                # Split content into chunks
                content = scraped_data['content']
                title = scraped_data['title']
                
                chunks = self.text_splitter.split_text(content)
                
                # Create documents
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": "web_content",
                            "url": url,
                            "title": title,
                            "chunk_id": f"web_{hash(url)}_{i}",
                            "method": scraped_data.get('method', 'unknown'),
                            "word_count": scraped_data.get('word_count', 0)
                        }
                    )
                    documents.append(doc)
                    
            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {e}")
                continue
        
        return documents
    
    def _create_web_vectorstore(self, documents: List[Document]) -> Optional[Chroma]:
        """Create temporary vector store for web content"""
        if not documents:
            return None
        
        try:
            # Create temporary vector store
            web_vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name=f"web_temp_{int(time.time())}"  # Unique collection name
            )
            return web_vectorstore
        except Exception as e:
            self.logger.error(f"Error creating web vector store: {e}")
            return None
    
    def ask_question_with_web_content(self, query: str) -> Dict[str, Any]:
        """Enhanced question answering with web content support"""
        
        # Check if query contains URLs
        clean_question, urls = self._detect_urls_in_query(query)
        
        if not urls:
            # No URLs found, use regular ask_question method
            return self.ask_question(clean_question)
        
        try:
            # Process web content if new URLs are provided
            if urls:
                web_documents = self._process_web_content(urls)
                
                if not web_documents:
                    return {
                        "answer": f"Woof! I tried to access the website(s) you provided, but couldn't extract readable content. Could you try a different link or ask me something else? 🐶",
                        "sources": [],
                        "confidence": 0.0,
                        "type": "web_error"
                    }
                
                # Add new web content to persistent memory
                success = self.add_web_content_to_memory(urls, web_documents)
                if not success:
                    return {
                        "answer": f"Woof! I had trouble processing the website content. Let me try to help you with the question directly instead! 🐶",
                        "sources": [],
                        "confidence": 0.0,
                        "type": "processing_error"
                    }
            
            # Query both new and existing web content
            if self.web_session_active:
                web_results = self.query_active_web_content(clean_question, k=5)
            else:
                return {
                    "answer": f"Woof! I don't have any website content to analyze right now. Please share a website URL and I'll analyze it for you! 🐶",
                    "sources": [],
                    "confidence": 0.0,
                    "type": "no_web_content"
                }
            
            # Build context from all active web content
            web_context_parts = []
            sources = []
            
            for doc in web_results:
                web_context_parts.append(f"From {doc.metadata['active_title']}: {doc.page_content}")
                sources.append({
                    "title": doc.metadata['active_title'],
                    "url": doc.metadata['active_url'],
                    "content": doc.page_content,
                    "relevance_score": doc.metadata.get('relevance_score', 0.8)  # Use stored score or default
                })
            
            web_context = "\n\n".join(web_context_parts)
            
            # Add context about active web session
            session_summary = self.get_active_web_context_summary()
            
            # Create specialized prompt for web content analysis with session context
            web_analysis_prompt = f"""You are Bulldog Buddy, a friendly AI assistant! 🐶

{session_summary}

The user is asking about the website content. Use the most relevant information from the websites below to answer their question accurately.

Relevant Website Content:
{web_context}

User's Question: {clean_question}

Instructions:
- Answer based on the website content provided above
- You can reference information from previous parts of our conversation about these websites
- Be helpful and accurate with the information from the websites
- Include your bulldog personality with appropriate emojis
- If the current content doesn't fully answer the question, mention what you found and suggest I can help further
- Cite the website source when referencing specific information
- Maintain conversation flow - this might be a follow-up question about the same websites

Bulldog Buddy's Response:"""

            # Get response from LLM
            response = self.llm.invoke(web_analysis_prompt)
            
            return {
                "answer": response,
                "sources": sources,
                "confidence": 0.8,  # High confidence for web-based queries
                "type": "web_analysis",
                "urls_processed": urls if urls else list(self.active_web_content.keys()),
                "documents_found": len(sources),
                "active_session": True
            }
            
        except Exception as e:
            self.logger.error(f"Error in web content analysis: {e}")
            return {
                "answer": f"Woof! I encountered an issue while analyzing the website. Here's what I can tell you about your question anyway... {str(e)} 🐶",
                "sources": [],
                "confidence": 0.0,
                "type": "error"
            }
    
    # ================== PERSISTENT WEB CONTENT METHODS ==================
    
    def add_web_content_to_memory(self, urls: List[str], documents: List[Document]) -> bool:
        """Store web content in persistent memory for conversation continuity"""
        try:
            for url in urls:
                # Filter documents for this URL
                url_docs = [doc for doc in documents if doc.metadata.get('url') == url]
                if not url_docs:
                    continue
                
                # Create individual vectorstore for this URL
                url_vectorstore = Chroma.from_documents(
                    documents=url_docs,
                    embedding=self.embeddings,
                    collection_name=f"web_persistent_{hash(url)}"
                )
                
                # Store in active web content
                self.active_web_content[url] = {
                    'title': url_docs[0].metadata.get('title', 'Web Content'),
                    'vectorstore': url_vectorstore,
                    'document_count': len(url_docs),
                    'timestamp': time.time(),
                    'method': url_docs[0].metadata.get('method', 'unknown')
                }
                
                # Add to current context
                if url not in self.current_web_context:
                    self.current_web_context.append(url)
            
            self.web_session_active = len(self.active_web_content) > 0
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding web content to memory: {e}")
            return False
    
    def query_active_web_content(self, question: str, k: int = 5) -> List[Document]:
        """Query all active web content for relevant information"""
        all_results = []
        
        for url, content_info in self.active_web_content.items():
            try:
                vectorstore = content_info['vectorstore']
                results = vectorstore.similarity_search_with_score(question, k=k)
                
                # Add URL context to results and extract documents assdasd
                for doc, score in results:
                    doc.metadata['active_url'] = url
                    doc.metadata['active_title'] = content_info.get('title', 'Web Content')
                    doc.metadata['relevance_score'] = score
                    all_results.append((doc, score))
                    
            except Exception as e:
                self.logger.error(f"Error querying web content from {url}: {e}")
                continue
        
        # Sort all results by relevance score and return just documents
        all_results.sort(key=lambda x: x[1])  # Lower score = more similar
        return [doc for doc, score in all_results[:k]]
    
    def get_active_web_context_summary(self) -> str:
        """Get a summary of currently active web content for context"""
        if not self.web_session_active:
            return ""
        
        summaries = []
        for url, info in self.active_web_content.items():
            summary = f"- {info['title']} ({url}): {info['document_count']} sections available"
            summaries.append(summary)
        
        return "Currently analyzing these websites:\n" + "\n".join(summaries)
    
    def clear_web_content(self, url: str = None) -> bool:
        """Clear specific URL or all web content from memory"""
        try:
            if url and url in self.active_web_content:
                # Clear specific URL
                del self.active_web_content[url]
                if url in self.current_web_context:
                    self.current_web_context.remove(url)
            else:
                # Clear all web content
                self.active_web_content.clear()
                self.current_web_context.clear()
            
            self.web_session_active = len(self.active_web_content) > 0
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing web content: {e}")
            return False
    
    def get_web_session_info(self) -> Dict[str, Any]:
        """Get information about the current web session"""
        if not self.active_web_content:
            return {
                'active': False,
                'urls': [],
                'total_documents': 0,
                'session_duration': 0
            }
            
        return {
            'active': self.web_session_active,
            'urls': list(self.active_web_content.keys()),
            'total_documents': sum(info['document_count'] for info in self.active_web_content.values()),
            'session_duration': time.time() - min(info['timestamp'] for info in self.active_web_content.values()) if self.active_web_content else 0
        }
    
    def _is_web_related_query(self, question: str) -> float:
        """
        Determine if a question is likely related to active web content
        Returns confidence score between 0-1
        """
        if not self.web_session_active:
            return 0.0
        
        question_lower = question.lower()
        
        # Direct reference keywords (strong indicators)
        strong_references = [
            "this", "that", "it", "the website", "the site", "the page", "the article",
            "mentioned", "said", "according to", "based on", "what does it say",
            "tell me more", "more about", "explain more", "what about",
            "summarize", "summary", "main points", "key points"
        ]
        
        # Contextual keywords (weaker but relevant)
        contextual_keywords = [
            "above", "previous", "earlier", "before", "also", "additionally",
            "regarding", "concerning", "about this", "from what", "how does",
            "what are", "what is", "why does", "where does", "when does"
        ]
        
        # Check for strong references
        strong_score = 0
        for keyword in strong_references:
            if keyword in question_lower:
                strong_score += 0.4
        
        # Check for contextual keywords  
        contextual_score = 0
        for keyword in contextual_keywords:
            if keyword in question_lower:
                contextual_score += 0.2
                
        # Check if question contains terms from active web content titles/content
        content_score = 0
        for content_info in self.active_web_content.values():
            title = content_info.get('title', '').lower()
            # Check if words from title appear in question
            title_words = [word for word in title.split() if len(word) > 3]
            for word in title_words:
                if word in question_lower:
                    content_score += 0.15
        
        # Combine scores
        total_score = min(strong_score + contextual_score + content_score, 1.0)
        
        # Boost score if this is clearly a follow-up (contains "this", "it", "that")
        if any(ref in question_lower for ref in ["this", "it", "that"]):
            total_score = min(total_score + 0.3, 1.0)
            
        return total_score

    # ================== UNIVERSITY MODE CONTROL METHODS ==================
    
    def set_university_mode(self, enabled: bool) -> bool:
        """Enable or disable university mode"""
        try:
            self.university_mode_enabled = enabled
            if enabled:
                self.logger.info("University mode ENABLED - Using student handbook")
            else:
                self.logger.info("University mode DISABLED - Using general knowledge")
            return True
        except Exception as e:
            self.logger.error(f"Error setting university mode: {e}")
            return False

    def is_university_mode_enabled(self) -> bool:
        """Check if university mode is enabled"""
        return getattr(self, 'university_mode_enabled', True)  # Default to True

    def get_mode_info(self) -> Dict[str, Any]:
        """Get current mode information"""
        return {
            "university_mode": self.is_university_mode_enabled(),
            "description": "Student Handbook Mode" if self.is_university_mode_enabled() 
                          else "General Knowledge Mode",
            "data_source": "Student Handbook + Conversation Memory" if self.is_university_mode_enabled()
                          else "AI Training Data + Web Content"
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
