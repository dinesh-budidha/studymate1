#!/usr/bin/env python3
"""
StudyMate Demo Script
Demonstrates core functionality without requiring the full Streamlit UI
"""

import os
import sys
from pathlib import Path

def create_sample_document():
    """Create a sample text document for testing."""
    sample_content = """
# Artificial Intelligence and Machine Learning

## Introduction
Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines capable of performing tasks that typically require human intelligence. Machine Learning (ML) is a subset of AI that focuses on the ability of machines to receive data and learn for themselves without being explicitly programmed.

## Key Concepts

### Machine Learning Types
1. **Supervised Learning**: Uses labeled training data to learn a mapping function from inputs to outputs.
2. **Unsupervised Learning**: Finds hidden patterns in data without labeled examples.
3. **Reinforcement Learning**: Learns through interaction with an environment using rewards and penalties.

### Applications
- Natural Language Processing (NLP)
- Computer Vision
- Robotics
- Autonomous Vehicles
- Healthcare Diagnostics
- Financial Trading

## Benefits
- Automation of repetitive tasks
- Improved decision making
- Pattern recognition in large datasets
- Personalized user experiences
- Predictive analytics

## Challenges
- Data privacy and security
- Algorithmic bias
- Job displacement concerns
- Interpretability of AI models
- Computational resource requirements

## Future Outlook
AI and ML continue to evolve rapidly, with emerging trends including:
- Large Language Models (LLMs)
- Generative AI
- Edge Computing
- Quantum Machine Learning
- Ethical AI frameworks
"""
    
    sample_file = Path("sample_document.txt")
    with open(sample_file, "w") as f:
        f.write(sample_content)
    
    return sample_file

def run_demo():
    """Run a demonstration of StudyMate core features."""
    print("🚀 StudyMate Core Functionality Demo")
    print("=" * 50)
    
    try:
        # Import core modules
        print("\n📦 Loading core modules...")
        from rag_engine import RAGEngine
        from user_manager import UserManager
        
        # Initialize user session
        print("👤 Creating user session...")
        user_manager = UserManager()
        user_id = user_manager.create_user_session("demo_user")
        print(f"✅ User session created: {user_id}")
        
        # Initialize RAG engine
        print("🧠 Initializing RAG engine...")
        rag_engine = RAGEngine(user_id)
        print("✅ RAG engine initialized")
        
        # Create and process sample document
        print("\n📄 Creating sample document...")
        sample_file = create_sample_document()
        
        # Simulate file upload object
        class FileUpload:
            def __init__(self, file_path):
                self.file_path = Path(file_path)
                self.name = self.file_path.name
                
            def getbuffer(self):
                return self.file_path.read_bytes()
        
        uploaded_file = FileUpload(sample_file)
        
        print("🔄 Processing document...")
        result = rag_engine.add_document(uploaded_file)
        
        if result["success"]:
            print(f"✅ Document processed successfully!")
            print(f"   📊 Stats: {result['stats']}")
        else:
            print(f"❌ Document processing failed: {result['error']}")
            return
        
        # Test chat functionality
        print("\n💬 Testing chat functionality...")
        questions = [
            "What is machine learning?",
            "What are the types of machine learning?",
            "What are the applications of AI?",
            "What challenges does AI face?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n🤔 Question {i}: {question}")
            response = rag_engine.chat(question, tone="academic")
            print(f"🤖 Response: {response['response'][:200]}...")
            if response.get('sources'):
                print(f"📚 Sources found: {len(response['sources'])}")
        
        # Test content generation
        print("\n📝 Testing content generation...")
        
        # Generate summary
        print("\n📊 Generating summary...")
        summary = rag_engine.generate_summary()
        print(f"Summary: {summary[:300]}...")
        
        # Generate flashcards
        print("\n🗃️ Generating flashcards...")
        flashcards = rag_engine.generate_flashcards(num_cards=3)
        for i, card in enumerate(flashcards, 1):
            print(f"Flashcard {i}:")
            print(f"  Q: {card['question']}")
            print(f"  A: {card['answer'][:100]}...")
        
        # Generate quiz
        print("\n❓ Generating quiz...")
        quiz = rag_engine.generate_quiz(num_questions=2)
        for i, question in enumerate(quiz, 1):
            print(f"Quiz Question {i}: {question['question']}")
            for j, option in enumerate(question['options']):
                print(f"  {chr(65+j)}) {option}")
            print(f"  Correct: {chr(65+question['correct'])}")
        
        # System statistics
        print("\n📈 System Statistics:")
        stats = rag_engine.get_system_stats()
        print(f"  📚 Total vectors: {stats['vector_store']['total_vectors']}")
        print(f"  📄 Total documents: {stats['vector_store']['total_documents']}")
        print(f"  💬 Chat history: {stats['chat_history_length']} messages")
        
        # Health check
        print("\n🏥 Health Check:")
        health = stats['health_check']
        for component, status in health.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {component}: {status}")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        os.remove(sample_file)
        print("✅ Demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_demo()