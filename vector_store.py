"""Vector store implementation using FAISS for document indexing and retrieval."""

import faiss
import numpy as np
import pickle
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import uuid
from config import FAISS_INDEX_DIR


class VectorStore:
    """FAISS-based vector store for document chunks with metadata."""
    
    def __init__(self, user_id: str, embedding_dim: int = 384):
        self.user_id = user_id
        self.embedding_dim = embedding_dim
        self.index_path = FAISS_INDEX_DIR / f"user_{user_id}"
        self.index_path.mkdir(exist_ok=True)
        
        # FAISS index
        self.index = None
        self.metadata = []  # Store metadata for each vector
        self.doc_mapping = {}  # Map doc_id to chunk indices
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        index_file = self.index_path / "faiss_index.bin"
        metadata_file = self.index_path / "metadata.pkl"
        mapping_file = self.index_path / "doc_mapping.json"
        
        if index_file.exists() and metadata_file.exists():
            try:
                # Load existing index
                self.index = faiss.read_index(str(index_file))
                
                with open(metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                if mapping_file.exists():
                    with open(mapping_file, 'r') as f:
                        self.doc_mapping = json.load(f)
                
                print(f"Loaded existing index with {self.index.ntotal} vectors")
                return
                
            except Exception as e:
                print(f"Error loading index: {e}. Creating new index.")
        
        # Create new index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        self.metadata = []
        self.doc_mapping = {}
        print("Created new FAISS index")
    
    def add_documents(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """Add document chunks and their embeddings to the index."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} doesn't match expected {self.embedding_dim}")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Get starting index for new vectors
        start_idx = self.index.ntotal
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                **chunk,
                "vector_id": start_idx + i,
                "timestamp": np.datetime64('now').isoformat()
            }
            self.metadata.append(chunk_metadata)
            
            # Update document mapping
            doc_id = chunk["doc_id"]
            if doc_id not in self.doc_mapping:
                self.doc_mapping[doc_id] = []
            self.doc_mapping[doc_id].append(start_idx + i)
        
        # Save updated index
        self._save_index()
        
        print(f"Added {len(chunks)} chunks to index. Total vectors: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, k: int = 5, doc_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for similar chunks based on query embedding."""
        if self.index.ntotal == 0:
            return []
        
        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Get more results initially for filtering
        search_k = min(k * 3, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata):
                metadata = self.metadata[idx].copy()
                metadata["similarity_score"] = float(score)
                
                # Apply document filter if specified
                if doc_filter is None or metadata["doc_id"] in doc_filter:
                    results.append(metadata)
                
                if len(results) >= k:
                    break
        
        return results
    
    def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        if doc_id not in self.doc_mapping:
            return []
        
        chunks = []
        for idx in self.doc_mapping[doc_id]:
            if idx < len(self.metadata):
                chunks.append(self.metadata[idx])
        
        return sorted(chunks, key=lambda x: x.get("chunk_index", 0))
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a specific document."""
        if doc_id not in self.doc_mapping:
            return False
        
        # Get indices to remove
        indices_to_remove = set(self.doc_mapping[doc_id])
        
        # Create new index without the deleted vectors
        if indices_to_remove:
            # Get all vectors except the ones to delete
            all_vectors = []
            new_metadata = []
            
            for i in range(self.index.ntotal):
                if i not in indices_to_remove:
                    vector = self.index.reconstruct(i)
                    all_vectors.append(vector)
                    new_metadata.append(self.metadata[i])
            
            # Create new index
            if all_vectors:
                new_index = faiss.IndexFlatIP(self.embedding_dim)
                vectors_array = np.array(all_vectors)
                new_index.add(vectors_array)
                self.index = new_index
            else:
                self.index = faiss.IndexFlatIP(self.embedding_dim)
            
            self.metadata = new_metadata
            
            # Update doc_mapping
            del self.doc_mapping[doc_id]
            
            # Update vector IDs in remaining metadata and doc_mapping
            for i, metadata in enumerate(self.metadata):
                metadata["vector_id"] = i
            
            # Update doc_mapping indices
            new_doc_mapping = {}
            for doc, old_indices in self.doc_mapping.items():
                new_indices = []
                for old_idx in old_indices:
                    # Find new index for this metadata
                    for new_idx, metadata in enumerate(self.metadata):
                        if (metadata.get("chunk_id") == 
                            next((m.get("chunk_id") for m in self.metadata 
                                 if m.get("vector_id") == old_idx), None)):
                            new_indices.append(new_idx)
                            break
                new_doc_mapping[doc] = new_indices
            
            self.doc_mapping = new_doc_mapping
            
            # Save updated index
            self._save_index()
            
            print(f"Deleted document {doc_id}. Remaining vectors: {self.index.ntotal}")
            return True
        
        return False
    
    def get_user_documents(self) -> List[Dict[str, Any]]:
        """Get summary of all documents for the user."""
        doc_summaries = {}
        
        for doc_id, indices in self.doc_mapping.items():
            if indices:
                # Get first chunk for document info
                first_chunk = self.metadata[indices[0]]
                doc_summaries[doc_id] = {
                    "doc_id": doc_id,
                    "filename": first_chunk.get("filename", "Unknown"),
                    "file_type": first_chunk.get("file_type", "Unknown"),
                    "chunk_count": len(indices),
                    "total_tokens": sum(self.metadata[idx].get("token_count", 0) for idx in indices),
                    "created_at": min(self.metadata[idx].get("timestamp", "") for idx in indices)
                }
        
        return list(doc_summaries.values())
    
    def clear_all_data(self):
        """Clear all data for the user."""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = []
        self.doc_mapping = {}
        
        # Remove saved files
        for file_path in self.index_path.glob("*"):
            file_path.unlink()
        
        print(f"Cleared all data for user {self.user_id}")
    
    def _save_index(self):
        """Save the FAISS index and metadata to disk."""
        try:
            # Save FAISS index
            index_file = self.index_path / "faiss_index.bin"
            faiss.write_index(self.index, str(index_file))
            
            # Save metadata
            metadata_file = self.index_path / "metadata.pkl"
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            # Save document mapping
            mapping_file = self.index_path / "doc_mapping.json"
            with open(mapping_file, 'w') as f:
                json.dump(self.doc_mapping, f)
                
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_vectors": self.index.ntotal if self.index else 0,
            "total_documents": len(self.doc_mapping),
            "embedding_dimension": self.embedding_dim,
            "index_size_mb": self._get_index_size_mb(),
            "documents": self.get_user_documents()
        }
    
    def _get_index_size_mb(self) -> float:
        """Get approximate size of index in MB."""
        try:
            total_size = 0
            for file_path in self.index_path.glob("*"):
                total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)
        except:
            return 0.0