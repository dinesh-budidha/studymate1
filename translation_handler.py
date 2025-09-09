"""Translation handler for Indian languages and other supported languages."""

from typing import Dict, Any, Optional, List
import requests
import time
from config import TTS_LANGUAGES

# Try to import googletrans
try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    print("Warning: googletrans not available. Translation functionality will be limited.")


class TranslationHandler:
    """Handles text translation for multiple Indian languages."""
    
    def __init__(self):
        if GOOGLETRANS_AVAILABLE:
            self.translator = Translator()
        else:
            self.translator = None
        
        self.supported_languages = {
            "english": "en",
            "hindi": "hi",
            "tamil": "ta", 
            "telugu": "te",
            "bengali": "bn",
            "gujarati": "gu",
            "kannada": "kn",
            "malayalam": "ml",
            "marathi": "mr",
            "punjabi": "pa",
            "urdu": "ur",
            "spanish": "es",
            "french": "fr",
            "german": "de",
            "chinese": "zh",
            "japanese": "ja",
            "korean": "ko",
            "arabic": "ar",
            "russian": "ru"
        }
        
        # Cache for translations to avoid repeated API calls
        self.translation_cache = {}
        self.max_cache_size = 1000
    
    def translate_text(
        self, 
        text: str, 
        target_language: str, 
        source_language: str = "auto"
    ) -> Dict[str, Any]:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language name (e.g., 'hindi', 'tamil')
            source_language: Source language ('auto' for auto-detection)
        
        Returns:
            Dictionary with translation result
        """
        try:
            if not text.strip():
                return {
                    "success": False,
                    "error": "Empty text provided"
                }
            
            if not GOOGLETRANS_AVAILABLE:
                return {
                    "success": False,
                    "error": "Translation service not available",
                    "translated_text": text  # Return original text
                }
            
            # Check cache first
            cache_key = f"{text[:100]}_{source_language}_{target_language}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
            
            # Get language codes
            target_code = self.supported_languages.get(target_language.lower())
            source_code = self.supported_languages.get(source_language.lower(), source_language)
            
            if not target_code:
                return {
                    "success": False,
                    "error": f"Unsupported target language: {target_language}"
                }
            
            # Skip translation if source and target are the same
            if source_code == target_code:
                result = {
                    "success": True,
                    "translated_text": text,
                    "source_language": target_language,
                    "target_language": target_language,
                    "confidence": 1.0
                }
                self._cache_translation(cache_key, result)
                return result
            
            # Perform translation
            translation = self.translator.translate(
                text, 
                dest=target_code,
                src=source_code if source_code != "auto" else None
            )
            
            result = {
                "success": True,
                "translated_text": translation.text,
                "source_language": self._get_language_name(translation.src),
                "target_language": target_language,
                "confidence": getattr(translation, 'confidence', 0.9)
            }
            
            # Cache the result
            self._cache_translation(cache_key, result)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Translation failed: {str(e)}",
                "translated_text": text  # Return original text as fallback
            }
    
    def translate_chat_response(
        self,
        response: Dict[str, Any],
        target_language: str
    ) -> Dict[str, Any]:
        """
        Translate a complete chat response including sources.
        
        Args:
            response: RAG response dictionary
            target_language: Target language for translation
        
        Returns:
            Translated response dictionary
        """
        try:
            translated_response = response.copy()
            
            # Translate main response
            if "response" in response:
                translation_result = self.translate_text(
                    response["response"], 
                    target_language
                )
                
                if translation_result["success"]:
                    translated_response["response"] = translation_result["translated_text"]
                    translated_response["translation_info"] = {
                        "target_language": target_language,
                        "source_language": translation_result.get("source_language", "auto"),
                        "confidence": translation_result.get("confidence", 0.9)
                    }
                else:
                    translated_response["translation_error"] = translation_result["error"]
            
            # Optionally translate source information (keeping original for reference)
            if "sources" in response:
                translated_response["original_sources"] = response["sources"]
            
            return translated_response
            
        except Exception as e:
            response["translation_error"] = str(e)
            return response
    
    def translate_content_batch(
        self,
        content_items: List[Dict[str, str]],
        target_language: str,
        content_key: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Translate a batch of content items (e.g., flashcards, quiz questions).
        
        Args:
            content_items: List of content dictionaries
            target_language: Target language
            content_key: Key in each dictionary containing text to translate
        
        Returns:
            List of translated content items
        """
        translated_items = []
        
        for item in content_items:
            try:
                translated_item = item.copy()
                
                # Translate main content
                if content_key in item:
                    translation_result = self.translate_text(
                        item[content_key],
                        target_language
                    )
                    
                    if translation_result["success"]:
                        translated_item[content_key] = translation_result["translated_text"]
                        translated_item["original_" + content_key] = item[content_key]
                    
                # For flashcards, translate both question and answer
                if "question" in item and "answer" in item:
                    q_result = self.translate_text(item["question"], target_language)
                    a_result = self.translate_text(item["answer"], target_language)
                    
                    if q_result["success"] and a_result["success"]:
                        translated_item.update({
                            "question": q_result["translated_text"],
                            "answer": a_result["translated_text"],
                            "original_question": item["question"],
                            "original_answer": item["answer"]
                        })
                
                # For quiz options
                if "options" in item and isinstance(item["options"], list):
                    translated_options = []
                    original_options = item["options"].copy()
                    
                    for option in item["options"]:
                        option_result = self.translate_text(option, target_language)
                        if option_result["success"]:
                            translated_options.append(option_result["translated_text"])
                        else:
                            translated_options.append(option)
                    
                    translated_item["options"] = translated_options
                    translated_item["original_options"] = original_options
                
                translated_item["target_language"] = target_language
                translated_items.append(translated_item)
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                # Keep original item if translation fails
                error_item = item.copy()
                error_item["translation_error"] = str(e)
                translated_items.append(error_item)
        
        return translated_items
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary with detection results
        """
        try:
            if not text.strip():
                return {
                    "success": False,
                    "error": "Empty text provided"
                }
            
            if not GOOGLETRANS_AVAILABLE:
                return {
                    "success": False,
                    "error": "Language detection service not available"
                }
            
            detection = self.translator.detect(text)
            
            return {
                "success": True,
                "language_code": detection.lang,
                "language_name": self._get_language_name(detection.lang),
                "confidence": detection.confidence
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Language detection failed: {str(e)}"
            }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages."""
        return self.supported_languages.copy()
    
    def get_indian_languages(self) -> Dict[str, str]:
        """Get list of supported Indian languages."""
        indian_languages = {}
        indian_lang_codes = ["hi", "ta", "te", "bn", "gu", "kn", "ml", "mr", "pa", "ur"]
        
        for name, code in self.supported_languages.items():
            if code in indian_lang_codes:
                indian_languages[name] = code
        
        return indian_languages
    
    def _get_language_name(self, language_code: str) -> str:
        """Get language name from code."""
        for name, code in self.supported_languages.items():
            if code == language_code:
                return name
        return language_code  # Return code if name not found
    
    def _cache_translation(self, key: str, result: Dict[str, Any]):
        """Cache translation result."""
        if len(self.translation_cache) >= self.max_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self.translation_cache.keys())[:100]
            for old_key in oldest_keys:
                del self.translation_cache[old_key]
        
        self.translation_cache[key] = result
    
    def clear_cache(self):
        """Clear translation cache."""
        self.translation_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.translation_cache),
            "max_cache_size": self.max_cache_size,
            "cache_hit_ratio": getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_attempts', 1), 1)
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check translation system health."""
        try:
            if not GOOGLETRANS_AVAILABLE:
                return {
                    "translation_working": False,
                    "detection_working": False,
                    "error": "googletrans library not available",
                    "supported_languages_count": len(self.supported_languages),
                    "indian_languages_count": len(self.get_indian_languages()),
                    "cache_size": len(self.translation_cache)
                }
            
            # Test basic translation
            test_result = self.translate_text("Hello", "hindi")
            
            # Test language detection
            detect_result = self.detect_language("Hello world")
            
            return {
                "translation_working": test_result["success"],
                "detection_working": detect_result["success"],
                "supported_languages_count": len(self.supported_languages),
                "indian_languages_count": len(self.get_indian_languages()),
                "cache_size": len(self.translation_cache)
            }
            
        except Exception as e:
            return {
                "translation_working": False,
                "detection_working": False,
                "error": str(e)
            }