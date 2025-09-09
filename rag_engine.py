"""RAG (Retrieval Augmented Generation) engine for StudyMate."""

from typing import List, Dict, Any, Optional
import numpy as np
from embeddings_handler import EmbeddingsHandler
from vector_store import VectorStore
from llm_handler import LLMHandler
from document_processor import DocumentProcessor


class RAGEngine:
    """Main RAG engine that combines document retrieval and generation."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Initialize components
        self.embeddings_handler = EmbeddingsHandler()
        self.vector_store = VectorStore(
            user_id=user_id,
            embedding_dim=self.embeddings_handler.get_embedding_dimension()
        )
        self.llm_handler = LLMHandler()
        self.document_processor = DocumentProcessor()
        
        # Chat history
        self.chat_history = []
    
    def add_document(self, uploaded_file) -> Dict[str, Any]:
        """Process and add a document to the knowledge base."""
        try:
            # Process the document
            doc_result = self.document_processor.process_uploaded_file(uploaded_file)
            
            if not doc_result["chunks"]:
                return {"success": False, "error": "No text chunks extracted from document"}
            
            # Generate embeddings for chunks
            chunk_texts = [chunk["text"] for chunk in doc_result["chunks"]]
            embeddings = self.embeddings_handler.embed_texts(
                chunk_texts, 
                batch_size=16, 
                show_progress=True
            )
            
            # Add to vector store
            self.vector_store.add_documents(doc_result["chunks"], embeddings)
            
            # Get document stats
            stats = self.document_processor.get_document_stats(doc_result["chunks"])
            
            return {
                "success": True,
                "doc_id": doc_result["metadata"]["doc_id"],
                "filename": doc_result["metadata"]["filename"],
                "stats": stats,
                "message": f"Successfully processed {uploaded_file.name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def chat(
        self, 
        query: str, 
        tone: str = "academic",
        max_results: int = 5,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """Chat with the knowledge base using RAG."""
        try:
            if not query.strip():
                return {
                    "response": "Please enter a question.",
                    "sources": [],
                    "context_used": 0
                }
            
            # Build query with history context if requested
            full_query = query
            if include_history and self.chat_history:
                recent_history = self.chat_history[-3:]  # Last 3 exchanges
                history_context = "\n".join([
                    f"Previous Q: {h['query']}\nPrevious A: {h['response'][:200]}..."
                    for h in recent_history
                ])
                full_query = f"Context from previous conversation:\n{history_context}\n\nCurrent question: {query}"
            
            # Generate query embedding
            query_embedding = self.embeddings_handler.embed_query(full_query)
            
            # Search for relevant chunks
            relevant_chunks = self.vector_store.search(
                query_embedding, 
                k=max_results
            )
            
            if not relevant_chunks:
                response = {
                    "response": "I don't have enough information in the uploaded documents to answer your question. Please upload relevant documents first.",
                    "sources": [],
                    "context_used": 0,
                    "tone": tone
                }
            else:
                # Generate RAG response
                response = self.llm_handler.generate_rag_response(
                    query, 
                    relevant_chunks, 
                    tone
                )
            
            # Add to chat history
            chat_entry = {
                "query": query,
                "response": response["response"],
                "sources": response.get("sources", []),
                "tone": tone,
                "timestamp": np.datetime64('now').isoformat()
            }
            self.chat_history.append(chat_entry)
            
            # Keep only last 50 entries
            if len(self.chat_history) > 50:
                self.chat_history = self.chat_history[-50:]
            
            return response
            
        except Exception as e:
            error_response = {
                "response": f"Error processing your question: {str(e)}",
                "sources": [],
                "context_used": 0,
                "tone": tone
            }
            return error_response
    
    def generate_summary(self, doc_id: Optional[str] = None, max_length: int = 300) -> str:
        """Generate a summary of documents."""
        try:
            if doc_id:
                # Summarize specific document
                chunks = self.vector_store.get_document_chunks(doc_id)
                if not chunks:
                    return "Document not found."
                
                # Combine chunks for summary
                text = "\n".join([chunk["text"] for chunk in chunks[:10]])  # First 10 chunks
            else:
                # Summarize all documents
                all_docs = self.vector_store.get_user_documents()
                if not all_docs:
                    return "No documents available for summary."
                
                # Get text from first few chunks of each document
                text_parts = []
                for doc in all_docs[:5]:  # Limit to 5 documents
                    chunks = self.vector_store.get_document_chunks(doc["doc_id"])
                    if chunks:
                        text_parts.append(f"From {doc['filename']}:\n{chunks[0]['text'][:500]}...")
                
                text = "\n\n".join(text_parts)
            
            # Generate summary
            summary = self.llm_handler.generate_summary(text, max_length)
            return summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def generate_flashcards(self, doc_id: Optional[str] = None, num_cards: int = 10) -> List[Dict[str, str]]:
        """Generate flashcards from documents."""
        try:
            if doc_id:
                chunks = self.vector_store.get_document_chunks(doc_id)
                if not chunks:
                    return [{"question": "Error", "answer": "Document not found"}]
                text = "\n".join([chunk["text"] for chunk in chunks[:5]])
            else:
                # Use all documents
                all_docs = self.vector_store.get_user_documents()
                if not all_docs:
                    return [{"question": "Error", "answer": "No documents available"}]
                
                text_parts = []
                for doc in all_docs[:3]:
                    chunks = self.vector_store.get_document_chunks(doc["doc_id"])
                    if chunks:
                        text_parts.append(chunks[0]["text"][:800])
                text = "\n\n".join(text_parts)
            
            # Generate flashcards
            flashcards = self.llm_handler.generate_flashcards(text, num_cards)
            return flashcards
            
        except Exception as e:
            return [{"question": "Error", "answer": str(e)}]
    
    def generate_quiz(self, doc_id: Optional[str] = None, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate a quiz from documents."""
        try:
            if doc_id:
                chunks = self.vector_store.get_document_chunks(doc_id)
                if not chunks:
                    return [{"question": "Error", "options": ["Document not found"], "correct": 0}]
                text = "\n".join([chunk["text"] for chunk in chunks[:5]])
            else:
                # Use all documents
                all_docs = self.vector_store.get_user_documents()
                if not all_docs:
                    return [{"question": "Error", "options": ["No documents available"], "correct": 0}]
                
                text_parts = []
                for doc in all_docs[:3]:
                    chunks = self.vector_store.get_document_chunks(doc["doc_id"])
                    if chunks:
                        text_parts.append(chunks[0]["text"][:800])
                text = "\n\n".join(text_parts)
            
            # Generate quiz
            quiz = self.llm_handler.generate_quiz(text, num_questions)
            return quiz
            
        except Exception as e:
            return [{"question": "Error", "options": [str(e)], "correct": 0}]
    
    def generate_report(self, topic: str, doc_ids: Optional[List[str]] = None) -> str:
        """Generate a comprehensive report on a topic."""
        try:
            # Search for relevant content
            query_embedding = self.embeddings_handler.embed_query(topic)
            
            # Filter by specific documents if provided
            doc_filter = doc_ids if doc_ids else None
            relevant_chunks = self.vector_store.search(
                query_embedding, 
                k=15,  # Get more chunks for comprehensive report
                doc_filter=doc_filter
            )
            
            if not relevant_chunks:
                return f"No relevant information found for topic: {topic}"
            
            # Organize chunks by source
            sources_content = {}
            for chunk in relevant_chunks:
                filename = chunk.get("filename", "Unknown")
                if filename not in sources_content:
                    sources_content[filename] = []
                sources_content[filename].append(chunk["text"])
            
            # Create comprehensive prompt for report
            context_parts = []
            for filename, texts in sources_content.items():
                combined_text = "\n".join(texts[:3])  # Max 3 chunks per source
                context_parts.append(f"From {filename}:\n{combined_text}")
            
            context = "\n\n".join(context_parts)
            
            prompt = f"""Generate a comprehensive report on the topic "{topic}" based on the following sources. 
Structure the report with clear sections and include insights from multiple sources where applicable.

Sources:
{context}

Topic: {topic}

Report:"""
            
            report = self.llm_handler.generate_response(
                prompt,
                max_new_tokens=800,
                temperature=0.3
            )
            
            return report
            
        except Exception as e:
            return f"Error generating report: {str(e)}"
    
    def get_chat_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent chat history."""
        return self.chat_history[-limit:] if self.chat_history else []
    
    def clear_chat_history(self):
        """Clear chat history."""
        self.chat_history = []
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the knowledge base."""
        return self.vector_store.delete_document(doc_id)
    
    def get_user_documents(self) -> List[Dict[str, Any]]:
        """Get all user documents."""
        return self.vector_store.get_user_documents()
    
    def clear_all_data(self):
        """Clear all user data."""
        self.vector_store.clear_all_data()
        self.chat_history = []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        vector_stats = self.vector_store.get_stats()
        
        return {
            "vector_store": vector_stats,
            "chat_history_length": len(self.chat_history),
            "embeddings_model": self.embeddings_handler.get_model_info(),
            "llm_model": self.llm_handler.get_model_info(),
            "health_check": {
                "embeddings": self.embeddings_handler.health_check(),
                "llm": self.llm_handler.health_check()
            }
        }
    
    def search_documents(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search documents without generating a response."""
        try:
            query_embedding = self.embeddings_handler.embed_query(query)
            results = self.vector_store.search(query_embedding, k=max_results)
            return results
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []