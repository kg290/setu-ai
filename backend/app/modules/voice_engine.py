"""Voice processing module - Speech-to-Text and Text-to-Speech."""
import os
import tempfile
from typing import Optional

# Lazy-load whisper model
_whisper_model = None


def _get_whisper_model(model_name: str = "base"):
    """Load whisper model lazily."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model


def transcribe_audio(audio_path: str, language: str = "hi", model_name: str = "base") -> dict:
    """
    Transcribe audio file to text using Whisper.
    Supports Hindi, English, Tamil, Telugu, Bengali, etc.
    """
    model = _get_whisper_model(model_name)

    # Map language codes to Whisper language names
    lang_map = {
        "hi": "Hindi",
        "en": "English",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "or": "Odia",
    }

    result = model.transcribe(
        audio_path,
        language=language if language != "auto" else None,
    )

    return {
        "text": result["text"].strip(),
        "language": result.get("language", language),
        "segments": [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in result.get("segments", [])
        ]
    }


def detect_intent(text: str) -> dict:
    """
    Simple rule-based intent detection for government scheme queries.
    """
    text_lower = text.lower()

    # Intent patterns
    intents = {
        "check_eligibility": [
            "eligible", "eligib", "योग्य", "पात्र", "qualify", "can i get",
            "am i eligible", "kya mujhe mil sakta", "क्या मुझे मिल सकता",
            "scheme", "yojana", "योजना", "scholarship", "छात्रवृत्ति"
        ],
        "apply": [
            "apply", "application", "form", "register", "आवेदन", "फॉर्म",
            "bharein", "भरें", "submit", "जमा"
        ],
        "upload_document": [
            "document", "upload", "photo", "दस्तावेज़", "अपलोड", "फोटो",
            "aadhaar", "आधार", "card", "कार्ड", "certificate", "प्रमाणपत्र"
        ],
        "list_schemes": [
            "list", "show", "all schemes", "what schemes", "सभी योजनाएं",
            "कौन कौन सी", "bataiye", "बताइये", "dikhao", "दिखाओ"
        ],
        "help": [
            "help", "मदद", "sahayata", "सहायता", "kaise", "कैसे", "how"
        ],
        "greeting": [
            "hello", "hi", "namaste", "नमस्ते", "namaskar", "नमस्कार"
        ]
    }

    detected_intent = "unknown"
    max_matches = 0

    for intent, keywords in intents.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_matches:
            max_matches = matches
            detected_intent = intent

    # Extract entities
    entities = {}
    category_keywords = {
        "education": ["education", "scholarship", "शिक्षा", "छात्रवृत्ति", "padhai", "पढ़ाई"],
        "agriculture": ["farmer", "kisan", "किसान", "agriculture", "कृषि", "kheti", "खेती"],
        "housing": ["house", "ghar", "घर", "awas", "आवास", "housing", "मकान"],
        "healthcare": ["health", "hospital", "स्वास्थ्य", "इलाज", "bimari", "बीमारी"],
        "employment": ["job", "employment", "naukri", "नौकरी", "rozgar", "रोज़गार"],
        "women_child": ["women", "girl", "महिला", "लड़की", "beti", "बेटी"],
    }

    for cat, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            entities["category"] = cat
            break

    return {
        "intent": detected_intent,
        "entities": entities,
        "confidence": min(max_matches / 3, 1.0) if max_matches > 0 else 0.0
    }


def text_to_speech(text: str, language: str = "hi", output_path: str = None) -> str:
    """Convert text to speech audio file."""
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "setu_tts_output.mp3")

    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Try to set voice for the language
        voices = engine.getProperty("voices")
        for voice in voices:
            if language in voice.id.lower():
                engine.setProperty("voice", voice.id)
                break
        engine.save_to_file(text, output_path)
        engine.runAndWait()
    except Exception:
        # Fallback: generate a simple response marker
        with open(output_path, "w") as f:
            f.write(f"[TTS:{language}] {text}")

    return output_path
