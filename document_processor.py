"""Document processing module for handling PDF, DOCX, and TXT files."""

import os
import fitz  # PyMuPDF
from docx import Document
import tiktoken
from typing import List, Dict, Any
from pathlib import Path
import hashlib
import json
from config import CHUNK_SIZE, CHUNK_OVERLAP, UPLOAD_DIR


class DocumentProcessor:
    """Handles document ingestion, processing, and chunking."""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def process_uploaded_file(self, uploaded_file) -> Dict[str, Any]:
        """Process an uploaded file and return document metadata and content."""
        try:
            # Save uploaded file temporarily
            file_path = UPLOAD_DIR / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Extract text based on file type
            file_extension = uploaded_file.name.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                text = self._extract_pdf_text(file_path)
            elif file_extension == 'docx':
                text = self._extract_docx_text(file_path)
            elif file_extension == 'txt':
                text = self._extract_txt_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Generate document metadata
            doc_id = self._generate_doc_id(uploaded_file.name, text)
            metadata = {
                "doc_id": doc_id,
                "filename": uploaded_file.name,
                "file_type": file_extension,
                "file_size": len(uploaded_file.getbuffer()),
                "text_length": len(text),
                "num_tokens": len(self.encoding.encode(text))
            }
            
            # Create chunks
            chunks = self._create_chunks(text, metadata)
            
            # Clean up temporary file
            os.remove(file_path)
            
            return {
                "metadata": metadata,
                "text": text,
                "chunks": chunks
            }
            
        except Exception as e:
            # Clean up on error
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise Exception(f"Error processing file {uploaded_file.name}: {str(e)}")
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF with OCR fallback."""
        text = ""
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Try text extraction first
                page_text = page.get_text()
                
                # If no text found, try OCR
                if not page_text.strip():
                    pix = page.get_pixmap()
                    # For now, we'll just note that OCR would be needed
                    # In a full implementation, you'd integrate pytesseract here
                    page_text = f"[OCR needed for page {page_num + 1}]"
                
                text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {str(e)}")
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            doc = Document(file_path)
            text = ""
            
            # Extract paragraphs
            for para in doc.paragraphs:
                text += para.text + "\n"
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + " "
                    text += "\n"
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Error extracting DOCX text: {str(e)}")
    
    def _extract_txt_text(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read().strip()
            except Exception as e:
                raise Exception(f"Error reading text file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error extracting TXT text: {str(e)}")
    
    def _generate_doc_id(self, filename: str, content: str) -> str:
        """Generate unique document ID based on filename and content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"{filename_hash}_{content_hash}"
    
    def _create_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create chunks from text with metadata."""
        chunks = []
        
        # Split text into sentences first
        sentences = text.split('.')
        
        current_chunk = ""
        current_tokens = 0
        chunk_id = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_tokens = len(self.encoding.encode(sentence))
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk_metadata(
                    current_chunk, chunk_id, metadata
                ))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + sentence + "."
                current_tokens = len(self.encoding.encode(current_chunk))
                chunk_id += 1
            else:
                current_chunk += sentence + "."
                current_tokens += sentence_tokens
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(self._create_chunk_metadata(
                current_chunk, chunk_id, metadata
            ))
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of current chunk."""
        words = text.split()
        overlap_words = min(self.chunk_overlap // 5, len(words))  # Approximate word count
        return " ".join(words[-overlap_words:]) + " " if overlap_words > 0 else ""
    
    def _create_chunk_metadata(self, text: str, chunk_id: int, doc_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for a text chunk."""
        return {
            "chunk_id": f"{doc_metadata['doc_id']}_chunk_{chunk_id}",
            "doc_id": doc_metadata["doc_id"],
            "filename": doc_metadata["filename"],
            "file_type": doc_metadata["file_type"],
            "chunk_index": chunk_id,
            "text": text.strip(),
            "token_count": len(self.encoding.encode(text)),
            "char_count": len(text)
        }
    
    def get_document_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about processed document."""
        if not chunks:
            return {}
        
        total_tokens = sum(chunk["token_count"] for chunk in chunks)
        total_chars = sum(chunk["char_count"] for chunk in chunks)
        
        return {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "total_characters": total_chars,
            "avg_tokens_per_chunk": total_tokens // len(chunks),
            "avg_chars_per_chunk": total_chars // len(chunks)
        }