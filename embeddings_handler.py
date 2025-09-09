"""Embeddings handler using sentence-transformers for document and query embeddings."""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union
import torch
from config import DEFAULT_EMBEDDING_MODEL


class EmbeddingsHandler:
    """Handles text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")
            # Fallback to a smaller model
            fallback_model = "all-MiniLM-L6-v2"
            print(f"Trying fallback model: {fallback_model}")
            try:
                self.model = SentenceTransformer(fallback_model)
                self.model_name = fallback_model
                print(f"Fallback model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
            except Exception as e2:
                raise Exception(f"Failed to load both primary and fallback models: {e2}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the model."""
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        return 384  # Default dimension for many sentence transformer models
    
    def embed_texts(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        if not texts:
            return np.array([])
        
        try:
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Generate embeddings
            embeddings = self.model.encode(
                cleaned_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=False  # We'll normalize in the vector store
            )
            
            return embeddings
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            # Return zero embeddings as fallback
            return np.zeros((len(texts), self.get_embedding_dimension()))
    
    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        if not query.strip():
            return np.zeros((1, self.get_embedding_dimension()))
        
        try:
            cleaned_query = self._clean_text(query)
            embedding = self.model.encode([cleaned_query], convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            return np.zeros((1, self.get_embedding_dimension()))
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for embedding."""
        if not text:
            return ""
        
        # Basic cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (most models have token limits)
        max_length = 500  # Conservative limit
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            embedding1_norm = embedding1 / norm1
            embedding2_norm = embedding2 / norm2
            
            # Compute cosine similarity
            similarity = np.dot(embedding1_norm, embedding2_norm)
            return float(similarity)
            
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def batch_similarity(self, query_embedding: np.ndarray, document_embeddings: np.ndarray) -> np.ndarray:
        """Compute similarities between a query and multiple document embeddings."""
        try:
            # Normalize embeddings
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            doc_norms = document_embeddings / np.linalg.norm(document_embeddings, axis=1, keepdims=True)
            
            # Compute similarities
            similarities = np.dot(doc_norms, query_norm.T).flatten()
            return similarities
            
        except Exception as e:
            print(f"Error computing batch similarities: {e}")
            return np.zeros(len(document_embeddings))
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        if not self.model:
            return {"error": "No model loaded"}
        
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.get_embedding_dimension(),
            "max_sequence_length": getattr(self.model, 'max_seq_length', 'Unknown'),
            "device": str(self.model.device) if hasattr(self.model, 'device') else 'Unknown'
        }
    
    def health_check(self) -> bool:
        """Check if the embedding model is working correctly."""
        try:
            test_text = "This is a test sentence for health check."
            embedding = self.embed_query(test_text)
            
            # Check if embedding has correct shape and non-zero values
            expected_dim = self.get_embedding_dimension()
            if embedding.shape != (1, expected_dim):
                return False
            
            if np.allclose(embedding, 0):
                return False
            
            return True
            
        except Exception as e:
            print(f"Health check failed: {e}")
            return False