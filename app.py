"""
StudyMate - A NotebookLM-like AI Study Companion
Main Streamlit Application
"""

import streamlit as st
import time
import uuid
from typing import Dict, Any, List
import traceback

# Import our modules
from config import *
from rag_engine import RAGEngine
from tts_handler import TTSHandler
from translation_handler import TranslationHandler
from user_manager import UserManager

# Page configuration
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 2rem;
        border-radius: 10px;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .source-box {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .flashcard {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .quiz-option {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 5px;
        cursor: pointer;
        border: 1px solid #ddd;
    }
    .quiz-option:hover {
        background-color: #f0f2f6;
    }
    .correct-answer {
        background-color: #d4edda !important;
        border-color: #c3e6cb !important;
    }
    .wrong-answer {
        background-color: #f8d7da !important;
        border-color: #f5c6cb !important;
    }
</style>
""", unsafe_allow_html=True)


class StudyMateApp:
    """Main StudyMate application class."""
    
    def __init__(self):
        self.initialize_session_state()
        self.user_manager = UserManager()
        
        # Initialize user session
        if "user_id" not in st.session_state:
            st.session_state.user_id = self.user_manager.create_user_session()
        
        # Initialize components
        self.rag_engine = RAGEngine(st.session_state.user_id)
        self.tts_handler = TTSHandler()
        self.translation_handler = TranslationHandler()
    
    def initialize_session_state(self):
        """Initialize session state variables."""
        defaults = {
            "chat_history": [],
            "uploaded_documents": [],
            "current_language": "english",
            "current_tone": "academic",
            "show_sources": True,
            "auto_translate": False,
            "current_page": "Chat",
            "quiz_answers": {},
            "quiz_score": None,
            "flashcard_index": 0
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def run(self):
        """Run the main application."""
        # Header
        st.markdown(f"""
        <div class="main-header">
            <h1>{APP_ICON} {APP_TITLE}</h1>
            <p>Upload documents, ask questions, and learn with AI-powered insights</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sidebar navigation
        self.render_sidebar()
        
        # Main content based on selected page
        if st.session_state.current_page == "Chat":
            self.render_chat_page()
        elif st.session_state.current_page == "Documents":
            self.render_documents_page()
        elif st.session_state.current_page == "Content Generation":
            self.render_content_generation_page()
        elif st.session_state.current_page == "Settings":
            self.render_settings_page()
        elif st.session_state.current_page == "Analytics":
            self.render_analytics_page()
    
    def render_sidebar(self):
        """Render the sidebar navigation."""
        with st.sidebar:
            st.title(SIDEBAR_TITLE)
            
            # Page navigation
            pages = ["Chat", "Documents", "Content Generation", "Settings", "Analytics"]
            st.session_state.current_page = st.selectbox(
                "Navigate to:",
                pages,
                index=pages.index(st.session_state.current_page)
            )
            
            st.divider()
            
            # Quick settings
            st.subheader("⚙️ Quick Settings")
            
            # Language selection
            languages = list(self.translation_handler.get_supported_languages().keys())
            st.session_state.current_language = st.selectbox(
                "Language:",
                languages,
                index=languages.index(st.session_state.current_language)
            )
            
            # Tone selection
            tones = list(VOICE_OPTIONS.keys())
            st.session_state.current_tone = st.selectbox(
                "Response Tone:",
                tones,
                index=tones.index(st.session_state.current_tone)
            )
            
            # Translation toggle
            st.session_state.auto_translate = st.checkbox(
                "Auto-translate responses",
                value=st.session_state.auto_translate
            )
            
            # Show sources toggle
            st.session_state.show_sources = st.checkbox(
                "Show source citations",
                value=st.session_state.show_sources
            )
            
            st.divider()
            
            # Document summary
            docs = self.rag_engine.get_user_documents()
            st.subheader("📚 Your Documents")
            if docs:
                for doc in docs[:5]:  # Show first 5
                    st.write(f"📄 {doc['filename']}")
                    st.caption(f"{doc['chunk_count']} chunks")
                
                if len(docs) > 5:
                    st.caption(f"... and {len(docs) - 5} more")
            else:
                st.info("No documents uploaded yet")
            
            # Quick actions
            st.divider()
            st.subheader("🚀 Quick Actions")
            
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                self.rag_engine.clear_chat_history()
                st.rerun()
            
            if st.button("📊 Generate Summary"):
                with st.spinner("Generating summary..."):
                    summary = self.rag_engine.generate_summary()
                    st.session_state.generated_summary = summary
                    st.session_state.current_page = "Content Generation"
                    st.rerun()
    
    def render_chat_page(self):
        """Render the main chat interface."""
        st.header("💬 Chat with Your Documents")
        
        # File uploader
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Upload your study materials to start asking questions"
        )
        
        if uploaded_files:
            self.process_uploaded_files(uploaded_files)
        
        # Chat interface
        st.subheader("Ask me anything about your documents:")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                self.render_chat_message(message, i)
        
        # Chat input
        with st.form("chat_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([6, 1, 1])
            
            with col1:
                user_input = st.text_input(
                    "Your question:",
                    placeholder="Ask about your documents...",
                    label_visibility="collapsed"
                )
            
            with col2:
                submit_button = st.form_submit_button("Send", use_container_width=True)
            
            with col3:
                voice_button = st.form_submit_button("🎤", use_container_width=True)
        
        # Process chat input
        if submit_button and user_input:
            self.process_chat_input(user_input)
        
        if voice_button:
            st.info("Voice input feature coming soon!")
    
    def render_chat_message(self, message: Dict[str, Any], index: int):
        """Render a single chat message."""
        # User message
        st.markdown(f"""
        <div style="text-align: right; margin: 1rem 0;">
            <div style="background-color: #e3f2fd; padding: 1rem; border-radius: 10px; display: inline-block; max-width: 70%;">
                <strong>You:</strong> {message['query']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI response
        st.markdown(f"""
        <div class="chat-message">
            <strong>📚 StudyMate:</strong><br>
            {message['response']}
        </div>
        """, unsafe_allow_html=True)
        
        # Sources
        if st.session_state.show_sources and message.get('sources'):
            with st.expander(f"📖 Sources ({len(message['sources'])} found)"):
                for source in message['sources']:
                    st.markdown(f"""
                    <div class="source-box">
                        <strong>{source['filename']}</strong> (Similarity: {source['similarity_score']:.2f})<br>
                        <em>Chunk ID: {source['chunk_id']}</em>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button(f"🔊 Read Aloud", key=f"tts_{index}"):
                self.text_to_speech(message['response'])
        
        with col2:
            if st.button(f"🌐 Translate", key=f"translate_{index}"):
                self.translate_message(message, index)
        
        with col3:
            if st.button(f"📝 Generate Flashcards", key=f"flashcards_{index}"):
                self.generate_flashcards_from_response(message['response'])
        
        with col4:
            if st.button(f"❓ Create Quiz", key=f"quiz_{index}"):
                self.generate_quiz_from_response(message['response'])
    
    def render_documents_page(self):
        """Render the documents management page."""
        st.header("📚 Document Management")
        
        # Document upload
        st.subheader("Upload New Documents")
        uploaded_files = st.file_uploader(
            "Choose files",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            self.process_uploaded_files(uploaded_files)
        
        # Existing documents
        st.subheader("Your Documents")
        docs = self.rag_engine.get_user_documents()
        
        if docs:
            for doc in docs:
                with st.expander(f"📄 {doc['filename']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Type:** {doc['file_type'].upper()}")
                        st.write(f"**Chunks:** {doc['chunk_count']}")
                        st.write(f"**Tokens:** {doc['total_tokens']:,}")
                    
                    with col2:
                        st.write(f"**Doc ID:** {doc['doc_id']}")
                        if doc.get('created_at'):
                            st.write(f"**Added:** {doc['created_at'][:10]}")
                    
                    # Document actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"📝 Summarize", key=f"sum_{doc['doc_id']}"):
                            with st.spinner("Generating summary..."):
                                summary = self.rag_engine.generate_summary(doc['doc_id'])
                                st.success("Summary generated!")
                                st.write(summary)
                    
                    with col2:
                        if st.button(f"🗃️ Flashcards", key=f"fc_{doc['doc_id']}"):
                            with st.spinner("Creating flashcards..."):
                                flashcards = self.rag_engine.generate_flashcards(doc['doc_id'])
                                st.session_state.current_flashcards = flashcards
                                st.session_state.current_page = "Content Generation"
                                st.rerun()
                    
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"del_{doc['doc_id']}", type="secondary"):
                            if st.session_state.get(f"confirm_delete_{doc['doc_id']}", False):
                                self.rag_engine.delete_document(doc['doc_id'])
                                st.success(f"Deleted {doc['filename']}")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_{doc['doc_id']}"] = True
                                st.warning("Click again to confirm deletion")
        else:
            st.info("No documents uploaded yet. Upload some documents to get started!")
        
        # Bulk actions
        if docs:
            st.divider()
            st.subheader("Bulk Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Delete All Documents", type="secondary"):
                    if st.session_state.get("confirm_delete_all", False):
                        self.rag_engine.clear_all_data()
                        st.success("All documents deleted!")
                        st.rerun()
                    else:
                        st.session_state.confirm_delete_all = True
                        st.warning("Click again to confirm deletion of ALL documents")
            
            with col2:
                if st.button("📊 Generate Report"):
                    topic = st.text_input("Report topic:", placeholder="Enter a topic for the report")
                    if topic:
                        with st.spinner("Generating comprehensive report..."):
                            report = self.rag_engine.generate_report(topic)
                            st.session_state.generated_report = report
                            st.session_state.current_page = "Content Generation"
                            st.rerun()
    
    def render_content_generation_page(self):
        """Render the content generation page."""
        st.header("🎯 Content Generation")
        
        # Content type selection
        content_type = st.selectbox(
            "What would you like to generate?",
            ["Summary", "Flashcards", "Quiz", "Report"]
        )
        
        if content_type == "Summary":
            self.render_summary_generation()
        elif content_type == "Flashcards":
            self.render_flashcard_generation()
        elif content_type == "Quiz":
            self.render_quiz_generation()
        elif content_type == "Report":
            self.render_report_generation()
    
    def render_summary_generation(self):
        """Render summary generation interface."""
        st.subheader("📝 Document Summary")
        
        docs = self.rag_engine.get_user_documents()
        if not docs:
            st.warning("Upload documents first to generate summaries.")
            return
        
        # Document selection
        doc_options = ["All Documents"] + [f"{doc['filename']} ({doc['doc_id']})" for doc in docs]
        selected_doc = st.selectbox("Select document:", doc_options)
        
        # Summary length
        length = st.slider("Summary length (words):", 100, 1000, 300, 50)
        
        if st.button("Generate Summary"):
            with st.spinner("Generating summary..."):
                if selected_doc == "All Documents":
                    summary = self.rag_engine.generate_summary(max_length=length)
                else:
                    doc_id = selected_doc.split("(")[1].split(")")[0]
                    summary = self.rag_engine.generate_summary(doc_id, max_length=length)
                
                st.session_state.generated_summary = summary
        
        # Display generated summary
        if hasattr(st.session_state, 'generated_summary'):
            st.markdown("### Generated Summary")
            st.write(st.session_state.generated_summary)
            
            # Summary actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔊 Read Summary"):
                    self.text_to_speech(st.session_state.generated_summary)
            
            with col2:
                if st.button("🌐 Translate Summary"):
                    if st.session_state.current_language != "english":
                        translated = self.translation_handler.translate_text(
                            st.session_state.generated_summary,
                            st.session_state.current_language
                        )
                        if translated["success"]:
                            st.success("Translation:")
                            st.write(translated["translated_text"])
    
    def render_flashcard_generation(self):
        """Render flashcard generation interface."""
        st.subheader("🗃️ Flashcards")
        
        docs = self.rag_engine.get_user_documents()
        if not docs:
            st.warning("Upload documents first to generate flashcards.")
            return
        
        # Generate new flashcards
        with st.expander("Generate New Flashcards"):
            doc_options = ["All Documents"] + [f"{doc['filename']} ({doc['doc_id']})" for doc in docs]
            selected_doc = st.selectbox("Select document:", doc_options, key="fc_doc_select")
            
            num_cards = st.slider("Number of flashcards:", 3, 20, 10)
            
            if st.button("Generate Flashcards"):
                with st.spinner("Creating flashcards..."):
                    if selected_doc == "All Documents":
                        flashcards = self.rag_engine.generate_flashcards(num_cards=num_cards)
                    else:
                        doc_id = selected_doc.split("(")[1].split(")")[0]
                        flashcards = self.rag_engine.generate_flashcards(doc_id, num_cards=num_cards)
                    
                    st.session_state.current_flashcards = flashcards
                    st.session_state.flashcard_index = 0
        
        # Display flashcards
        if hasattr(st.session_state, 'current_flashcards') and st.session_state.current_flashcards:
            flashcards = st.session_state.current_flashcards
            
            # Navigation
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("⬅️ Previous") and st.session_state.flashcard_index > 0:
                    st.session_state.flashcard_index -= 1
                    st.rerun()
            
            with col2:
                st.write(f"Card {st.session_state.flashcard_index + 1} of {len(flashcards)}")
            
            with col3:
                if st.button("➡️ Next") and st.session_state.flashcard_index < len(flashcards) - 1:
                    st.session_state.flashcard_index += 1
                    st.rerun()
            
            # Current flashcard
            current_card = flashcards[st.session_state.flashcard_index]
            
            # Show/hide answer toggle
            show_answer = st.checkbox("Show Answer", key=f"show_answer_{st.session_state.flashcard_index}")
            
            # Flashcard display
            st.markdown(f"""
            <div class="flashcard">
                <h3>Question:</h3>
                <p>{current_card['question']}</p>
                {'<h3>Answer:</h3><p>' + current_card['answer'] + '</p>' if show_answer else ''}
            </div>
            """, unsafe_allow_html=True)
            
            # Flashcard actions
            if show_answer:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔊 Read Question"):
                        self.text_to_speech(current_card['question'])
                
                with col2:
                    if st.button("🔊 Read Answer"):
                        self.text_to_speech(current_card['answer'])
                
                with col3:
                    if st.button("🌐 Translate Card"):
                        self.translate_flashcard(current_card)
    
    def render_quiz_generation(self):
        """Render quiz generation interface."""
        st.subheader("❓ Interactive Quiz")
        
        docs = self.rag_engine.get_user_documents()
        if not docs:
            st.warning("Upload documents first to generate quizzes.")
            return
        
        # Generate new quiz
        with st.expander("Generate New Quiz"):
            doc_options = ["All Documents"] + [f"{doc['filename']} ({doc['doc_id']})" for doc in docs]
            selected_doc = st.selectbox("Select document:", doc_options, key="quiz_doc_select")
            
            num_questions = st.slider("Number of questions:", 3, 15, 5)
            
            if st.button("Generate Quiz"):
                with st.spinner("Creating quiz..."):
                    if selected_doc == "All Documents":
                        quiz = self.rag_engine.generate_quiz(num_questions=num_questions)
                    else:
                        doc_id = selected_doc.split("(")[1].split(")")[0]
                        quiz = self.rag_engine.generate_quiz(doc_id, num_questions=num_questions)
                    
                    st.session_state.current_quiz = quiz
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_score = None
        
        # Display quiz
        if hasattr(st.session_state, 'current_quiz') and st.session_state.current_quiz:
            quiz = st.session_state.current_quiz
            
            with st.form("quiz_form"):
                for i, question in enumerate(quiz):
                    st.markdown(f"**Question {i+1}:** {question['question']}")
                    
                    # Answer options
                    answer = st.radio(
                        f"Select your answer for question {i+1}:",
                        question['options'],
                        key=f"q_{i}",
                        label_visibility="collapsed"
                    )
                    
                    st.session_state.quiz_answers[i] = question['options'].index(answer) if answer else None
                    st.divider()
                
                if st.form_submit_button("Submit Quiz"):
                    self.grade_quiz(quiz)
            
            # Show results
            if st.session_state.quiz_score is not None:
                score = st.session_state.quiz_score
                total = len(quiz)
                percentage = (score / total) * 100
                
                st.markdown(f"### Quiz Results: {score}/{total} ({percentage:.1f}%)")
                
                if percentage >= 80:
                    st.success("Excellent work! 🎉")
                elif percentage >= 60:
                    st.info("Good job! Keep studying! 📚")
                else:
                    st.warning("Keep practicing! You'll get better! 💪")
                
                # Show detailed results
                with st.expander("Review Answers"):
                    for i, question in enumerate(quiz):
                        user_answer = st.session_state.quiz_answers.get(i)
                        correct_answer = question['correct']
                        
                        if user_answer == correct_answer:
                            st.success(f"Q{i+1}: ✅ Correct")
                        else:
                            st.error(f"Q{i+1}: ❌ Incorrect")
                            st.write(f"Your answer: {question['options'][user_answer] if user_answer is not None else 'No answer'}")
                            st.write(f"Correct answer: {question['options'][correct_answer]}")
    
    def render_report_generation(self):
        """Render report generation interface."""
        st.subheader("📊 Comprehensive Reports")
        
        docs = self.rag_engine.get_user_documents()
        if not docs:
            st.warning("Upload documents first to generate reports.")
            return
        
        # Report topic input
        topic = st.text_input("Report topic:", placeholder="Enter the main topic or theme for your report")
        
        # Document selection
        st.write("Select documents to include:")
        doc_selection = {}
        
        for doc in docs:
            doc_selection[doc['doc_id']] = st.checkbox(
                f"{doc['filename']} ({doc['chunk_count']} chunks)",
                value=True,
                key=f"report_doc_{doc['doc_id']}"
            )
        
        selected_docs = [doc_id for doc_id, selected in doc_selection.items() if selected]
        
        if st.button("Generate Report", disabled=not topic or not selected_docs):
            with st.spinner("Generating comprehensive report..."):
                report = self.rag_engine.generate_report(topic, selected_docs)
                st.session_state.generated_report = report
        
        # Display generated report
        if hasattr(st.session_state, 'generated_report'):
            st.markdown("### Generated Report")
            st.markdown(st.session_state.generated_report)
            
            # Report actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔊 Read Report"):
                    self.text_to_speech(st.session_state.generated_report)
            
            with col2:
                if st.button("🌐 Translate Report"):
                    if st.session_state.current_language != "english":
                        with st.spinner("Translating..."):
                            translated = self.translation_handler.translate_text(
                                st.session_state.generated_report,
                                st.session_state.current_language
                            )
                            if translated["success"]:
                                st.success("Translation:")
                                st.markdown(translated["translated_text"])
            
            with col3:
                # Download report (simplified)
                st.download_button(
                    label="📥 Download Report",
                    data=st.session_state.generated_report,
                    file_name=f"studymate_report_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
    
    def render_settings_page(self):
        """Render the settings page."""
        st.header("⚙️ Settings")
        
        # Language settings
        st.subheader("🌐 Language Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Supported Languages:**")
            languages = self.translation_handler.get_supported_languages()
            for lang_name, lang_code in languages.items():
                st.write(f"• {lang_name.title()} ({lang_code})")
        
        with col2:
            st.write("**Indian Languages:**")
            indian_langs = self.translation_handler.get_indian_languages()
            for lang_name, lang_code in indian_langs.items():
                st.write(f"• {lang_name.title()} ({lang_code})")
        
        # Voice settings
        st.divider()
        st.subheader("🔊 Voice Settings")
        
        voice_options = self.tts_handler.get_supported_voices()
        for voice, description in voice_options.items():
            st.write(f"• **{voice.title()}**: {description}")
        
        # Test voice
        test_text = st.text_input("Test voice with custom text:", value="Hello, this is a test of the text-to-speech system.")
        test_voice = st.selectbox("Voice style:", list(voice_options.keys()))
        test_language = st.selectbox("Language:", list(self.translation_handler.get_supported_languages().keys()))
        
        if st.button("🔊 Test Voice"):
            self.text_to_speech(test_text, test_language, test_voice)
        
        # System settings
        st.divider()
        st.subheader("🔧 System Settings")
        
        # Model information
        with st.expander("Model Information"):
            stats = self.rag_engine.get_system_stats()
            st.json(stats)
        
        # Health check
        if st.button("🏥 Run Health Check"):
            with st.spinner("Running system health check..."):
                health = {
                    "embeddings": self.rag_engine.embeddings_handler.health_check(),
                    "llm": self.rag_engine.llm_handler.health_check(),
                    "tts": self.tts_handler.health_check(),
                    "translation": self.translation_handler.health_check()
                }
                
                st.write("**Health Check Results:**")
                for component, status in health.items():
                    if isinstance(status, bool):
                        st.write(f"• {component.title()}: {'✅' if status else '❌'}")
                    else:
                        st.write(f"• {component.title()}:")
                        for key, value in status.items():
                            st.write(f"  - {key}: {'✅' if value else '❌'}")
        
        # Data management
        st.divider()
        st.subheader("🗄️ Data Management")
        
        user_data = self.user_manager.get_user_data(st.session_state.user_id)
        if user_data:
            st.write(f"**User ID:** {user_data['user_id']}")
            st.write(f"**Documents:** {user_data['total_documents']}")
            st.write(f"**Queries:** {user_data['total_queries']}")
            st.write(f"**Data Size:** {user_data.get('data_size_mb', 0):.2f} MB")
        
        # Danger zone
        with st.expander("🚨 Danger Zone"):
            st.warning("These actions are irreversible!")
            
            if st.button("🗑️ Delete All My Data", type="secondary"):
                if st.session_state.get("confirm_delete_all_data", False):
                    with st.spinner("Deleting all data..."):
                        result = self.user_manager.delete_user_data(
                            st.session_state.user_id, 
                            confirm_deletion=True
                        )
                        if result["success"]:
                            st.success("All data deleted successfully!")
                            # Reset session
                            for key in list(st.session_state.keys()):
                                del st.session_state[key]
                            st.rerun()
                        else:
                            st.error(f"Error: {result['error']}")
                else:
                    st.session_state.confirm_delete_all_data = True
                    st.error("Click again to confirm deletion of ALL your data")
    
    def render_analytics_page(self):
        """Render the analytics page."""
        st.header("📊 Analytics")
        
        # User stats
        st.subheader("👤 Your Activity")
        
        user_data = self.user_manager.get_user_data(st.session_state.user_id)
        if user_data:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Documents", user_data.get('total_documents', 0))
            
            with col2:
                st.metric("Queries", user_data.get('total_queries', 0))
            
            with col3:
                st.metric("Data Size", f"{user_data.get('data_size_mb', 0):.1f} MB")
            
            with col4:
                days_active = 1  # Simplified calculation
                st.metric("Days Active", days_active)
        
        # System stats
        st.divider()
        st.subheader("🖥️ System Statistics")
        
        system_stats = self.user_manager.get_system_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Users", system_stats.get('total_users', 0))
            st.metric("Active Sessions", system_stats.get('active_sessions', 0))
        
        with col2:
            st.metric("Total Data", f"{system_stats.get('total_data_size_mb', 0):.1f} MB")
            st.metric("Avg Documents/User", f"{system_stats.get('avg_documents_per_user', 0):.1f}")
        
        with col3:
            st.metric("Total Sessions", system_stats.get('total_sessions', 0))
            st.metric("Avg Queries/User", f"{system_stats.get('avg_queries_per_user', 0):.1f}")
        
        # Recent activity
        st.divider()
        st.subheader("📈 Recent Activity")
        
        chat_history = self.rag_engine.get_chat_history(10)
        if chat_history:
            for i, chat in enumerate(reversed(chat_history)):
                with st.expander(f"Query {i+1}: {chat['query'][:50]}..."):
                    st.write(f"**Query:** {chat['query']}")
                    st.write(f"**Response Length:** {len(chat['response'])} characters")
                    st.write(f"**Sources Used:** {len(chat.get('sources', []))}")
                    st.write(f"**Tone:** {chat.get('tone', 'N/A')}")
                    if chat.get('timestamp'):
                        st.write(f"**Time:** {chat['timestamp']}")
        else:
            st.info("No recent activity to display.")
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files."""
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in [doc['filename'] for doc in st.session_state.uploaded_documents]:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    result = self.rag_engine.add_document(uploaded_file)
                    
                    if result["success"]:
                        st.success(f"✅ Successfully processed {uploaded_file.name}")
                        st.session_state.uploaded_documents.append({
                            'filename': uploaded_file.name,
                            'doc_id': result['doc_id'],
                            'stats': result['stats']
                        })
                        
                        # Update user stats
                        self.user_manager.increment_user_stats(st.session_state.user_id, "documents")
                        
                        # Show processing stats
                        stats = result['stats']
                        st.info(f"📊 {stats['total_chunks']} chunks, {stats['total_tokens']:,} tokens")
                    else:
                        st.error(f"❌ Error processing {uploaded_file.name}: {result['error']}")
    
    def process_chat_input(self, user_input: str):
        """Process user chat input."""
        with st.spinner("Thinking..."):
            # Update user activity
            self.user_manager.update_user_activity(st.session_state.user_id)
            self.user_manager.increment_user_stats(st.session_state.user_id, "queries")
            
            # Get response from RAG engine
            response = self.rag_engine.chat(
                user_input,
                tone=st.session_state.current_tone,
                include_history=True
            )
            
            # Translate if needed
            if st.session_state.auto_translate and st.session_state.current_language != "english":
                response = self.translation_handler.translate_chat_response(
                    response,
                    st.session_state.current_language
                )
            
            # Add to chat history
            st.session_state.chat_history.append(response)
            
            # Rerun to update display
            st.rerun()
    
    def text_to_speech(self, text: str, language: str = None, voice_style: str = None):
        """Convert text to speech."""
        if language is None:
            language = st.session_state.current_language
        
        if voice_style is None:
            voice_style = st.session_state.current_tone
        
        with st.spinner("Generating speech..."):
            audio_file = self.tts_handler.synthesize_speech(text, language, voice_style)
            
            if audio_file:
                # For web deployment, we'll show a download link instead of playing
                with open(audio_file, "rb") as f:
                    st.download_button(
                        label="🔊 Download Audio",
                        data=f.read(),
                        file_name="studymate_audio.mp3",
                        mime="audio/mpeg"
                    )
                st.success("Audio generated! Click the download button to save it.")
            else:
                st.error("Failed to generate audio. Please try again.")
    
    def translate_message(self, message: Dict[str, Any], index: int):
        """Translate a chat message."""
        if st.session_state.current_language == "english":
            st.info("Already in English!")
            return
        
        with st.spinner("Translating..."):
            translated = self.translation_handler.translate_text(
                message['response'],
                st.session_state.current_language
            )
            
            if translated["success"]:
                st.success(f"Translation to {st.session_state.current_language.title()}:")
                st.write(translated["translated_text"])
            else:
                st.error(f"Translation failed: {translated['error']}")
    
    def translate_flashcard(self, flashcard: Dict[str, str]):
        """Translate a flashcard."""
        if st.session_state.current_language == "english":
            st.info("Already in English!")
            return
        
        with st.spinner("Translating flashcard..."):
            q_result = self.translation_handler.translate_text(
                flashcard['question'],
                st.session_state.current_language
            )
            a_result = self.translation_handler.translate_text(
                flashcard['answer'],
                st.session_state.current_language
            )
            
            if q_result["success"] and a_result["success"]:
                st.success(f"Translation to {st.session_state.current_language.title()}:")
                st.write(f"**Question:** {q_result['translated_text']}")
                st.write(f"**Answer:** {a_result['translated_text']}")
            else:
                st.error("Translation failed")
    
    def generate_flashcards_from_response(self, response_text: str):
        """Generate flashcards from a chat response."""
        with st.spinner("Creating flashcards..."):
            # Create a temporary document-like structure
            flashcards = self.rag_engine.llm_handler.generate_flashcards(response_text)
            st.session_state.current_flashcards = flashcards
            st.session_state.flashcard_index = 0
            st.session_state.current_page = "Content Generation"
            st.rerun()
    
    def generate_quiz_from_response(self, response_text: str):
        """Generate quiz from a chat response."""
        with st.spinner("Creating quiz..."):
            quiz = self.rag_engine.llm_handler.generate_quiz(response_text)
            st.session_state.current_quiz = quiz
            st.session_state.quiz_answers = {}
            st.session_state.quiz_score = None
            st.session_state.current_page = "Content Generation"
            st.rerun()
    
    def grade_quiz(self, quiz: List[Dict[str, Any]]):
        """Grade the quiz answers."""
        score = 0
        for i, question in enumerate(quiz):
            user_answer = st.session_state.quiz_answers.get(i)
            if user_answer == question['correct']:
                score += 1
        
        st.session_state.quiz_score = score


def main():
    """Main application entry point."""
    try:
        app = StudyMateApp()
        app.run()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("Please refresh the page and try again.")
        
        # Show traceback in development
        if st.checkbox("Show technical details"):
            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()