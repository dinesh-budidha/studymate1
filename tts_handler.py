"""Text-to-Speech handler with multi-voice support and Indian languages."""

import os
import io
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import TTS_LANGUAGES, VOICE_OPTIONS, TEMP_DIR

# Try to import optional dependencies
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("Warning: gTTS not available. TTS functionality will be limited.")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available. Audio playback will be limited.")

try:
    from ibm_watson import TextToSpeechV1
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
    from config import IBM_WATSON_API_KEY, IBM_WATSON_URL
    WATSON_AVAILABLE = bool(IBM_WATSON_API_KEY and IBM_WATSON_URL)
except ImportError:
    WATSON_AVAILABLE = False


class TTSHandler:
    """Handles text-to-speech with multiple voices and languages."""
    
    def __init__(self):
        self.watson_tts = None
        self.temp_files = []
        
        # Initialize pygame mixer for audio playback
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.pygame_available = True
            except:
                self.pygame_available = False
                print("Warning: pygame mixer initialization failed")
        else:
            self.pygame_available = False
        
        # Initialize IBM Watson if available
        if WATSON_AVAILABLE:
            self._init_watson()
    
    def _init_watson(self):
        """Initialize IBM Watson Text-to-Speech."""
        try:
            authenticator = IAMAuthenticator(IBM_WATSON_API_KEY)
            self.watson_tts = TextToSpeechV1(authenticator=authenticator)
            self.watson_tts.set_service_url(IBM_WATSON_URL)
            print("IBM Watson TTS initialized successfully")
        except Exception as e:
            print(f"Failed to initialize IBM Watson TTS: {e}")
            self.watson_tts = None
    
    def synthesize_speech(
        self, 
        text: str, 
        language: str = "english",
        voice_style: str = "default",
        use_watson: bool = True
    ) -> Optional[str]:
        """
        Synthesize speech from text and return path to audio file.
        
        Args:
            text: Text to synthesize
            language: Language for TTS
            voice_style: Voice style/tone
            use_watson: Whether to use Watson TTS (if available)
        
        Returns:
            Path to generated audio file or None if failed
        """
        try:
            if not text.strip():
                return None
            
            # Clean text
            clean_text = self._clean_text_for_tts(text)
            
            # Try Watson TTS first if available and requested
            if use_watson and self.watson_tts and language in ["english", "hindi"]:
                return self._watson_synthesize(clean_text, language, voice_style)
            
            # Fallback to Google TTS
            return self._gtts_synthesize(clean_text, language)
            
        except Exception as e:
            print(f"Error synthesizing speech: {e}")
            return None
    
    def _watson_synthesize(self, text: str, language: str, voice_style: str) -> Optional[str]:
        """Synthesize using IBM Watson TTS."""
        try:
            # Map language and voice style to Watson voices
            voice_map = {
                ("english", "default"): "en-US_AllisonV3Voice",
                ("english", "academic"): "en-US_LisaV3Voice", 
                ("english", "casual"): "en-US_AllisonV3Voice",
                ("english", "debate_pro"): "en-US_KevinV3Voice",
                ("english", "debate_con"): "en-US_MichaelV3Voice",
                ("hindi", "default"): "hi-IN_RashiV3Voice"
            }
            
            voice = voice_map.get((language, voice_style), "en-US_AllisonV3Voice")
            
            # Synthesize
            response = self.watson_tts.synthesize(
                text=text,
                voice=voice,
                accept='audio/wav'
            ).get_result()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.wav',
                dir=TEMP_DIR
            )
            temp_file.write(response.content)
            temp_file.close()
            
            self.temp_files.append(temp_file.name)
            return temp_file.name
            
        except Exception as e:
            print(f"Watson TTS error: {e}")
            return None
    
    def _gtts_synthesize(self, text: str, language: str) -> Optional[str]:
        """Synthesize using Google TTS."""
        if not GTTS_AVAILABLE:
            print("gTTS not available")
            return None
            
        try:
            # Map language to gTTS language code
            lang_code = TTS_LANGUAGES.get(language, "en")
            
            # Create gTTS object
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.mp3',
                dir=TEMP_DIR
            )
            tts.save(temp_file.name)
            temp_file.close()
            
            self.temp_files.append(temp_file.name)
            return temp_file.name
            
        except Exception as e:
            print(f"gTTS error: {e}")
            return None
    
    def play_audio(self, audio_file: str) -> bool:
        """Play audio file using pygame."""
        try:
            if not self.pygame_available or not os.path.exists(audio_file):
                return False
            
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False
    
    def create_debate_audio(
        self, 
        topic: str,
        pro_points: List[str], 
        con_points: List[str],
        language: str = "english"
    ) -> List[Dict[str, Any]]:
        """
        Create a debate-style audio with alternating pro/con voices.
        
        Returns:
            List of audio segments with metadata
        """
        segments = []
        
        try:
            # Introduction
            intro_text = f"Debate on the topic: {topic}. Let's hear both sides."
            intro_audio = self.synthesize_speech(
                intro_text, 
                language, 
                "default",
                use_watson=True
            )
            if intro_audio:
                segments.append({
                    "type": "introduction",
                    "text": intro_text,
                    "audio_file": intro_audio,
                    "voice": "default"
                })
            
            # Pro and con arguments
            max_points = max(len(pro_points), len(con_points))
            
            for i in range(max_points):
                # Pro argument
                if i < len(pro_points):
                    pro_text = f"Pro argument {i+1}: {pro_points[i]}"
                    pro_audio = self.synthesize_speech(
                        pro_text,
                        language,
                        "debate_pro",
                        use_watson=True
                    )
                    if pro_audio:
                        segments.append({
                            "type": "pro",
                            "text": pro_text,
                            "audio_file": pro_audio,
                            "voice": "debate_pro"
                        })
                
                # Con argument
                if i < len(con_points):
                    con_text = f"Counter argument {i+1}: {con_points[i]}"
                    con_audio = self.synthesize_speech(
                        con_text,
                        language,
                        "debate_con",
                        use_watson=True
                    )
                    if con_audio:
                        segments.append({
                            "type": "con",
                            "text": con_text,
                            "audio_file": con_audio,
                            "voice": "debate_con"
                        })
            
            # Conclusion
            conclusion_text = "This concludes our debate. Consider both perspectives when forming your opinion."
            conclusion_audio = self.synthesize_speech(
                conclusion_text,
                language,
                "default",
                use_watson=True
            )
            if conclusion_audio:
                segments.append({
                    "type": "conclusion",
                    "text": conclusion_text,
                    "audio_file": conclusion_audio,
                    "voice": "default"
                })
            
            return segments
            
        except Exception as e:
            print(f"Error creating debate audio: {e}")
            return []
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS pronunciation."""
        # Remove markdown and special characters
        import re
        
        # Remove markdown links
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove markdown formatting
        text = re.sub(r'[*_`#]', '', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Limit length (most TTS services have limits)
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        return text.strip()
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for TTS."""
        return TTS_LANGUAGES.copy()
    
    def get_supported_voices(self) -> Dict[str, str]:
        """Get supported voice styles."""
        return VOICE_OPTIONS.copy()
    
    def cleanup_temp_files(self):
        """Clean up temporary audio files."""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error removing temp file {file_path}: {e}")
        
        self.temp_files = []
    
    def health_check(self) -> Dict[str, bool]:
        """Check TTS system health."""
        health = {
            "pygame_available": self.pygame_available,
            "watson_available": self.watson_tts is not None,
            "gtts_available": True  # gTTS should always work if installed
        }
        
        # Test basic synthesis
        try:
            if GTTS_AVAILABLE:
                test_audio = self.synthesize_speech("Test", "english", "default", use_watson=False)
                health["synthesis_working"] = test_audio is not None
                if test_audio:
                    os.remove(test_audio)
            else:
                health["synthesis_working"] = False
        except:
            health["synthesis_working"] = False
        
        return health
    
    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup_temp_files()