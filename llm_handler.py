"""LLM handler for HuggingFace models, primarily Mistral."""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from typing import List, Dict, Any, Optional
import warnings
from config import DEFAULT_LLM_MODEL, HUGGINGFACE_API_KEY

# Suppress some warnings
warnings.filterwarnings("ignore", category=UserWarning)


class LLMHandler:
    """Handles language model operations using HuggingFace transformers."""
    
    def __init__(self, model_name: str = DEFAULT_LLM_MODEL):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_length = 2048
        self._load_model()
    
    def _load_model(self):
        """Load the language model and tokenizer."""
        try:
            print(f"Loading LLM model: {self.model_name}")
            print(f"Using device: {self.device}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                token=HUGGINGFACE_API_KEY if HUGGINGFACE_API_KEY else None,
                trust_remote_code=True
            )
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # For lighter deployment, we'll use a pipeline instead of loading the full model
            self.pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                token=HUGGINGFACE_API_KEY if HUGGINGFACE_API_KEY else None,
                trust_remote_code=True
            )
            
            print("Model loaded successfully")
            
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")
            # Fallback to a smaller, more accessible model
            fallback_model = "microsoft/DialoGPT-medium"
            try:
                print(f"Trying fallback model: {fallback_model}")
                self.model_name = fallback_model
                self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.pipeline = pipeline(
                    "text-generation",
                    model=fallback_model,
                    tokenizer=self.tokenizer,
                    device=0 if self.device == "cuda" else -1
                )
                print("Fallback model loaded successfully")
                
            except Exception as e2:
                print(f"Failed to load fallback model: {e2}")
                # Use a very basic model as last resort
                try:
                    self.model_name = "gpt2"
                    self.pipeline = pipeline("text-generation", model="gpt2")
                    self.tokenizer = self.pipeline.tokenizer
                    print("Using GPT-2 as emergency fallback")
                except Exception as e3:
                    raise Exception(f"Failed to load any model: {e3}")
    
    def generate_response(
        self, 
        prompt: str, 
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ) -> str:
        """Generate a response to the given prompt."""
        try:
            if not self.pipeline:
                return "Error: Model not loaded"
            
            # Truncate prompt if too long
            max_prompt_length = self.max_length - max_new_tokens - 50  # Buffer
            if len(prompt) > max_prompt_length:
                prompt = prompt[:max_prompt_length] + "..."
            
            # Generate response
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                return_full_text=False,
                truncation=True
            )
            
            if outputs and len(outputs) > 0:
                response = outputs[0]['generated_text'].strip()
                return self._clean_response(response, prompt)
            else:
                return "Sorry, I couldn't generate a response."
                
        except Exception as e:
            print(f"Error generating response: {e}")
            return f"Error generating response: {str(e)}"
    
    def generate_rag_response(
        self, 
        query: str, 
        context_chunks: List[Dict[str, Any]],
        tone: str = "academic"
    ) -> Dict[str, Any]:
        """Generate a RAG response with context and citations."""
        try:
            # Build context from chunks
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(context_chunks[:5]):  # Limit to top 5 chunks
                context_parts.append(f"[Source {i+1}]: {chunk['text'][:500]}...")
                sources.append({
                    "source_id": i + 1,
                    "filename": chunk.get("filename", "Unknown"),
                    "chunk_id": chunk.get("chunk_id", ""),
                    "similarity_score": chunk.get("similarity_score", 0.0)
                })
            
            context = "\n\n".join(context_parts)
            
            # Create prompt based on tone
            prompt = self._create_rag_prompt(query, context, tone)
            
            # Generate response
            response = self.generate_response(
                prompt, 
                max_new_tokens=512,
                temperature=0.3 if tone == "academic" else 0.7
            )
            
            return {
                "response": response,
                "sources": sources,
                "context_used": len(context_chunks),
                "tone": tone
            }
            
        except Exception as e:
            print(f"Error generating RAG response: {e}")
            return {
                "response": f"Error: {str(e)}",
                "sources": [],
                "context_used": 0,
                "tone": tone
            }
    
    def _create_rag_prompt(self, query: str, context: str, tone: str) -> str:
        """Create a RAG prompt based on tone."""
        tone_instructions = {
            "academic": "Provide a scholarly, well-structured response with clear explanations.",
            "casual": "Respond in a friendly, conversational manner.",
            "formal": "Provide a professional, formal response.",
            "debate_pro": "Present arguments in favor of the topic with confidence.",
            "debate_con": "Present counter-arguments or opposing viewpoints analytically."
        }
        
        instruction = tone_instructions.get(tone, tone_instructions["academic"])
        
        prompt = f"""Based on the following context documents, answer the user's question. {instruction}

Context:
{context}

Question: {query}

Answer: """
        
        return prompt
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate a summary of the given text."""
        try:
            prompt = f"""Summarize the following text in about {max_length} words:

{text[:2000]}

Summary:"""
            
            return self.generate_response(
                prompt, 
                max_new_tokens=max_length,
                temperature=0.3
            )
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"
    
    def generate_flashcards(self, text: str, num_cards: int = 5) -> List[Dict[str, str]]:
        """Generate flashcards from the given text."""
        try:
            prompt = f"""Create {num_cards} flashcards from the following text. Format each flashcard as:
Q: [Question]
A: [Answer]

Text:
{text[:1500]}

Flashcards:"""
            
            response = self.generate_response(
                prompt, 
                max_new_tokens=400,
                temperature=0.5
            )
            
            # Parse flashcards from response
            flashcards = self._parse_flashcards(response)
            return flashcards
            
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            return [{"question": "Error", "answer": str(e)}]
    
    def generate_quiz(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate a multiple choice quiz from the given text."""
        try:
            prompt = f"""Create {num_questions} multiple choice questions from the following text. Format each question as:
Q: [Question]
A) [Option A]
B) [Option B] 
C) [Option C]
D) [Option D]
Correct: [Letter]

Text:
{text[:1500]}

Quiz:"""
            
            response = self.generate_response(
                prompt, 
                max_new_tokens=600,
                temperature=0.4
            )
            
            # Parse quiz from response
            quiz = self._parse_quiz(response)
            return quiz
            
        except Exception as e:
            print(f"Error generating quiz: {e}")
            return [{"question": "Error", "options": ["Error"], "correct": 0}]
    
    def _clean_response(self, response: str, prompt: str) -> str:
        """Clean up the generated response."""
        # Remove the prompt if it appears in the response
        if prompt and response.startswith(prompt):
            response = response[len(prompt):].strip()
        
        # Clean up common artifacts
        response = response.replace("<|endoftext|>", "")
        response = response.replace("[/INST]", "")
        
        # Take only the first complete sentence/paragraph
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Q:', 'A:', 'Question:', 'Answer:')):
                cleaned_lines.append(line)
            elif cleaned_lines:  # Stop at first Q/A pattern if we have content
                break
        
        return '\n'.join(cleaned_lines).strip() if cleaned_lines else response.strip()
    
    def _parse_flashcards(self, text: str) -> List[Dict[str, str]]:
        """Parse flashcards from generated text."""
        flashcards = []
        lines = text.split('\n')
        
        current_q = ""
        current_a = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                if current_q and current_a:
                    flashcards.append({"question": current_q, "answer": current_a})
                current_q = line[2:].strip()
                current_a = ""
            elif line.startswith('A:'):
                current_a = line[2:].strip()
        
        # Add the last card
        if current_q and current_a:
            flashcards.append({"question": current_q, "answer": current_a})
        
        return flashcards if flashcards else [{"question": "No flashcards generated", "answer": "Try with different content"}]
    
    def _parse_quiz(self, text: str) -> List[Dict[str, Any]]:
        """Parse quiz questions from generated text."""
        quiz = []
        lines = text.split('\n')
        
        current_q = ""
        current_options = []
        current_correct = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                if current_q and current_options:
                    quiz.append({
                        "question": current_q,
                        "options": current_options,
                        "correct": current_correct
                    })
                current_q = line[2:].strip()
                current_options = []
                current_correct = 0
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                current_options.append(line[2:].strip())
            elif line.startswith('Correct:'):
                correct_letter = line[8:].strip().upper()
                if correct_letter in 'ABCD':
                    current_correct = ord(correct_letter) - ord('A')
        
        # Add the last question
        if current_q and current_options:
            quiz.append({
                "question": current_q,
                "options": current_options,
                "correct": current_correct
            })
        
        return quiz if quiz else [{"question": "No quiz generated", "options": ["Try again"], "correct": 0}]
    
    def health_check(self) -> bool:
        """Check if the LLM is working correctly."""
        try:
            test_prompt = "Hello, how are you?"
            response = self.generate_response(test_prompt, max_new_tokens=10)
            return len(response) > 0 and "Error" not in response
        except:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "max_length": self.max_length,
            "tokenizer_vocab_size": self.tokenizer.vocab_size if self.tokenizer else "Unknown"
        }