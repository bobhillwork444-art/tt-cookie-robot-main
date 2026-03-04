"""
Simple translation loader from Qt .ts files
"""
import os
import xml.etree.ElementTree as ET


class SimpleTranslator:
    """Load translations from Qt .ts files without lrelease"""
    
    def __init__(self):
        self.translations = {}
        self.current_language = "English"
    
    def load(self, filepath: str) -> bool:
        """Load translations from .ts file"""
        if not os.path.exists(filepath):
            return False
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            for context in root.findall('context'):
                for message in context.findall('message'):
                    source = message.find('source')
                    translation = message.find('translation')
                    
                    if source is not None and translation is not None:
                        src_text = source.text or ""
                        trans_text = translation.text or src_text
                        
                        # Skip empty or unfinished translations
                        if trans_text and translation.get('type') != 'unfinished':
                            self.translations[src_text] = trans_text
            
            return True
        except Exception as e:
            print(f"Translation load error: {e}")
            return False
    
    def translate(self, text: str) -> str:
        """Get translated text"""
        return self.translations.get(text, text)
    
    def clear(self):
        """Clear loaded translations"""
        self.translations = {}


# Global translator instance
_translator = SimpleTranslator()


def load_translation(language: str, app_dir: str = None) -> bool:
    """Load translation for specified language"""
    _translator.clear()
    
    if language == "English":
        return True  # No translation needed
    
    # Map language name to file
    lang_map = {
        "Русский": "ru_RU",
        "Russian": "ru_RU",
    }
    
    lang_code = lang_map.get(language)
    if not lang_code:
        return False
    
    # Find translations directory
    if app_dir is None:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    ts_path = os.path.join(app_dir, "translations", f"{lang_code}.ts")
    
    return _translator.load(ts_path)


def tr(text: str) -> str:
    """Translate text using loaded translations"""
    return _translator.translate(text)
