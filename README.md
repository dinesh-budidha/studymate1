# StudyMate - AI Study Companion

A comprehensive AI-powered study companion similar to NotebookLM, built with Python and Streamlit. StudyMate helps you learn from your documents through intelligent Q&A, content generation, and multi-language support.

## 🌟 Features

### Core Functionality
- **Multi-format Document Processing**: Upload and process PDF, DOCX, and TXT files
- **OCR Support**: Extract text from scanned PDFs using PyMuPDF
- **Intelligent Chunking**: Smart text segmentation with configurable chunk sizes
- **FAISS Vector Search**: Fast similarity search with metadata storage
- **RAG (Retrieval Augmented Generation)**: Context-aware responses with source citations

### AI-Powered Content Generation
- **Interactive Chat**: Ask questions about your documents with citation tracking
- **Document Summaries**: Generate comprehensive summaries of your materials
- **Flashcards**: Automatically create study flashcards from content
- **Quizzes**: Generate multiple-choice quizzes for self-assessment
- **Reports**: Create detailed reports on specific topics

### Advanced Features
- **Multi-language Support**: Translate content to 19+ languages including Indian languages
- **Text-to-Speech**: Convert text to speech in multiple languages and voices
- **Tone Control**: Adjust response style (academic, casual, formal, debate)
- **Debate Mode**: Generate pro/con arguments with different voices
- **User Sessions**: Per-user data isolation and management
- **Data Management**: Easy deletion and cleanup of user data

### Supported Languages
- **Indian Languages**: Hindi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Urdu
- **International**: English, Spanish, French, German, Chinese, Japanese, Korean, Arabic, Russian

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- At least 4GB RAM (8GB recommended for larger documents)
- Internet connection for model downloads

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dinesh-budidha/studymate1.git
   cd studymate1
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration (optional)**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (optional for basic functionality)
   ```

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

5. **Open your browser** to `http://localhost:8501`

## 📖 Usage Guide

### Getting Started
1. **Upload Documents**: Use the file uploader to add PDF, DOCX, or TXT files
2. **Wait for Processing**: Documents are automatically processed and indexed
3. **Start Chatting**: Ask questions about your uploaded content
4. **Generate Content**: Create summaries, flashcards, quizzes, and reports

### Chat Interface
- Ask specific questions about your documents
- Get responses with source citations
- Adjust tone (academic, casual, formal, debate)
- Translate responses to different languages
- Convert responses to speech

### Content Generation
- **Summaries**: Generate overviews of single documents or all materials
- **Flashcards**: Create question-answer pairs for active learning
- **Quizzes**: Test your knowledge with multiple-choice questions
- **Reports**: Generate comprehensive analyses on specific topics

### Language Features
- **Translation**: Automatic or manual translation to 19+ languages
- **Text-to-Speech**: Multi-voice synthesis including debate mode
- **Indian Language Support**: Full support for major Indian languages

### Data Management
- **Per-user Sessions**: Isolated data for multiple users
- **Document Management**: View, search, and delete uploaded documents
- **Data Deletion**: Complete cleanup of user data when needed

## 🛠️ Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Document Processing**: PyMuPDF (PDF processing with OCR)
- **Vector Database**: FAISS (Facebook AI Similarity Search)
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **Language Model**: HuggingFace Transformers (Mistral/GPT family)
- **Translation**: Google Translate API
- **Text-to-Speech**: gTTS + IBM Watson (optional)
- **File Processing**: python-docx, tiktoken

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with the following optional configurations:

```env
# HuggingFace API Key (for advanced models)
HUGGINGFACE_API_KEY=your_api_key_here

# IBM Watson TTS (for advanced voice features)
IBM_WATSON_API_KEY=your_watson_key_here
IBM_WATSON_URL=your_watson_url_here
```

### Model Configuration
Edit `config.py` to customize:
- Chunk sizes and overlap
- Model selections
- Supported file types
- Language mappings
- Voice options

## 📁 Project Structure

```
studymate1/
├── app.py                      # Main Streamlit application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
│
├── document_processor.py      # Document ingestion and chunking
├── vector_store.py           # FAISS vector database management
├── embeddings_handler.py     # Text embedding generation
├── llm_handler.py            # Language model integration
├── rag_engine.py             # RAG implementation
├── tts_handler.py            # Text-to-speech functionality
├── translation_handler.py    # Language translation
├── user_manager.py           # User session management
│
├── uploads/                   # Temporary file storage
├── user_data/                # User session data
├── faiss_indexes/            # FAISS vector indexes
└── temp_files/               # Temporary audio files
```

## 🎯 Use Cases

### Students
- Study lecture notes and textbooks
- Generate flashcards for exam preparation
- Create quizzes for self-assessment
- Get explanations in preferred language

### Researchers
- Analyze research papers and documents
- Generate comprehensive literature reviews
- Extract key insights from multiple sources
- Create structured reports

### Professionals
- Process training materials and manuals
- Generate summaries of technical documents
- Create presentations from source materials
- Multi-language document understanding

### Educators
- Create teaching materials from source texts
- Generate quizzes and assessments
- Translate educational content
- Develop interactive learning experiences

## 🔧 Advanced Features

### Debate Mode
Generate balanced arguments on any topic with different voices:
- Pro arguments with confident tone
- Counter arguments with analytical tone
- Multi-voice audio synthesis for engaging debates

### Tone Control
Adjust AI response style:
- **Academic**: Formal, scholarly responses
- **Casual**: Friendly, conversational tone
- **Formal**: Professional, structured answers
- **Debate Pro/Con**: Argumentative styles for different perspectives

### Data Privacy
- Per-user data isolation
- Complete data deletion capabilities
- No data sharing between users
- Local storage of all processed content

## 🚨 Troubleshooting

### Common Issues

1. **Model Loading Errors**:
   - Ensure stable internet connection for initial model downloads
   - Check available disk space (models can be 1-2GB)
   - Try restarting the application

2. **File Processing Failures**:
   - Verify file format is supported (PDF, DOCX, TXT)
   - Check file size (large files may take longer)
   - Ensure files are not password-protected

3. **Memory Issues**:
   - Close other applications to free up RAM
   - Process smaller documents or fewer files at once
   - Consider using a machine with more memory

4. **Performance Optimization**:
   - Use CPU-only models for better compatibility
   - Adjust chunk sizes in config for better performance
   - Clear old data regularly to save space

### Getting Help
- Check the application logs in the Streamlit interface
- Use the built-in health check in Settings
- Review error messages for specific guidance

## 📊 Performance Notes

- **First Run**: Initial model downloads may take 5-10 minutes
- **Document Processing**: ~1-2 minutes per MB of text content
- **Response Time**: 2-5 seconds for typical queries
- **Memory Usage**: 2-4GB RAM for normal operation
- **Storage**: ~100MB per 1000 document chunks

## 🤝 Contributing

StudyMate is designed to be extensible and customizable. Areas for contribution:
- Additional file format support
- New language models integration
- Enhanced translation capabilities
- UI/UX improvements
- Performance optimizations

## 📄 License

This project is designed for educational and research purposes. Please ensure compliance with all API terms of service and data privacy regulations when deploying.

## 🙏 Acknowledgments

- **HuggingFace**: For transformer models and embeddings
- **Facebook Research**: For FAISS vector search
- **Streamlit**: For the excellent web framework
- **PyMuPDF**: For robust PDF processing
- **Google**: For translation services
- **IBM Watson**: For advanced TTS capabilities

---

Built with ❤️ for learners everywhere. No Google branding - fully independent AI study companion.