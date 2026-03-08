"""Conversation orchestrator - manages the multi-step guided workflow with Gemini NLU."""
import uuid
from datetime import datetime
from app.models import (
    UserProfile, ExtractedData, ConversationState, ChatMessage,
    EligibilityResult
)
from app.modules.eligibility_engine import find_eligible_schemes, get_scheme_by_id
from app.modules.form_generator import generate_application
from app.modules.gemini_nlu import process_with_gemini, generate_document_summary

# In-memory session store
_sessions: dict[str, ConversationState] = {}

RESPONSES = {
    "hi": {
        "greeting": "नमस्ते! मैं सेतु AI हूँ — आपका सरकारी योजना सहायक। बोलिए या अपना दस्तावेज़ दिखाइए, मैं आपकी मदद करूँगा।",
        "ask_document": "कृपया अपने दस्तावेज़ की फोटो खींचें — आधार कार्ड, आय प्रमाणपत्र, या जाति प्रमाणपत्र।",
        "document_processed": "आपका {doc_type} सफलतापूर्वक पढ़ लिया गया है।",
        "eligible_schemes": "आपके लिए ये योजनाएं उपलब्ध हैं:",
        "no_eligible": "अभी कोई योजना नहीं मिली। कृपया और दस्तावेज़ दिखाएं।",
        "confirm_apply": "क्या आप '{scheme_name}' के लिए आवेदन करना चाहते हैं? हाँ बोलें।",
        "form_generated": "आपका आवेदन पत्र तैयार है! डाउनलोड करें।",
        "more_docs": "बेहतर मिलान के लिए और दस्तावेज़ दिखाएं। अभी तक: {count} दस्तावेज़",
        "help": "मैं आपकी मदद कर सकता हूँ:\n• योजनाओं की पात्रता जांचें\n• दस्तावेज़ पढ़ें\n• आवेदन पत्र भरें\n\nबस बोलिए या दस्तावेज़ दिखाइए!",
        "welcome_voice": "नमस्ते! मैं सेतु AI हूँ। आप बोलकर या दस्तावेज़ की फोटो खींचकर शुरू कर सकते हैं।",
    },
    "en": {
        "greeting": "Namaste! I am Setu AI — your government scheme assistant. Speak or show your document, I'll help you.",
        "ask_document": "Please take a photo of your document — Aadhaar Card, Income Certificate, or Caste Certificate.",
        "document_processed": "Your {doc_type} has been read successfully.",
        "eligible_schemes": "These schemes are available for you:",
        "no_eligible": "No matching schemes found yet. Please show more documents.",
        "confirm_apply": "Would you like to apply for '{scheme_name}'? Say yes.",
        "form_generated": "Your application form is ready! Download it now.",
        "more_docs": "Show more documents for better matching. So far: {count} documents",
        "help": "I can help you with:\n• Check scheme eligibility\n• Read your documents\n• Fill application forms\n\nJust speak or show a document!",
        "welcome_voice": "Namaste! I am Setu AI. You can start by speaking or taking a photo of your document.",
    }
}


def get_response(key: str, language: str = "hi", **kwargs) -> str:
    lang = language if language in RESPONSES else "en"
    template = RESPONSES[lang].get(key, RESPONSES["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def create_session(language: str = "hi") -> ConversationState:
    session_id = str(uuid.uuid4())
    state = ConversationState(
        session_id=session_id,
        current_step="greeting",
        language=language,
    )

    greeting = get_response("welcome_voice", language)
    state.messages.append(ChatMessage(
        role="assistant",
        content=greeting,
        language=language,
        timestamp=datetime.now().isoformat(),
    ))

    _sessions[session_id] = state
    return state


def get_session(session_id: str) -> ConversationState | None:
    return _sessions.get(session_id)


def process_text_input(session_id: str, text: str) -> ConversationState:
    """Process user text/voice input using Gemini NLU."""
    state = _sessions.get(session_id)
    if not state:
        state = create_session()
        session_id = state.session_id

    lang = state.language

    state.messages.append(ChatMessage(
        role="user",
        content=text,
        language=lang,
        timestamp=datetime.now().isoformat(),
    ))

    # Build context for Gemini
    profile_dict = state.user_profile.model_dump()
    schemes_list = [
        {
            "scheme": r.scheme.model_dump(),
            "is_eligible": r.is_eligible,
            "match_score": r.match_score,
        }
        for r in state.eligible_schemes if r.is_eligible
    ]
    history = [{"role": m.role, "content": m.content} for m in state.messages[-6:]]

    # Process through Gemini NLU
    nlu_result = process_with_gemini(
        user_text=text,
        language=lang,
        user_profile=profile_dict,
        eligible_schemes=schemes_list,
        current_step=state.current_step,
        conversation_history=history,
    )

    intent = nlu_result.get("intent", "unknown")
    response_text = nlu_result.get("response_text", "")
    action = nlu_result.get("suggested_action", "none")

    # Handle workflow transitions based on intent
    if intent == "greeting":
        state.current_step = "greeting"
    elif intent in ("upload_document",) or action == "ask_document":
        state.current_step = "document_upload"
    elif intent in ("check_eligibility", "list_schemes") or action == "show_schemes":
        results = find_eligible_schemes(state.user_profile)
        state.eligible_schemes = results
        eligible = [r for r in results if r.is_eligible]
        if eligible and not response_text:
            response_text = get_response("eligible_schemes", lang) + "\n"
            for i, r in enumerate(eligible[:5], 1):
                name = r.scheme.name_hi if lang == "hi" and r.scheme.name_hi else r.scheme.name
                response_text += f"{i}. {name} — {int(r.match_score * 100)}%\n"
        state.current_step = "eligibility"
    elif intent == "apply" or action == "start_application":
        if state.eligible_schemes:
            eligible = [r for r in state.eligible_schemes if r.is_eligible]
            if eligible:
                top = eligible[0]
                name = top.scheme.name_hi if lang == "hi" and top.scheme.name_hi else top.scheme.name
                state.selected_scheme = top.scheme.id
                if not response_text:
                    response_text = get_response("confirm_apply", lang, scheme_name=name)
                state.current_step = "confirmation"
        if not response_text:
            response_text = get_response("ask_document", lang)
            state.current_step = "document_upload"
    elif intent == "confirm_yes" or action == "generate_form":
        if state.selected_scheme:
            result = generate_form(session_id, state.selected_scheme)
            if "error" not in result:
                response_text = get_response("form_generated", lang)
                state.current_step = "form_generation"
            elif not response_text:
                response_text = result.get("error", "Error generating form")

    # Fallback
    if not response_text:
        if state.user_profile.documents:
            results = find_eligible_schemes(state.user_profile)
            state.eligible_schemes = results
            eligible = [r for r in results if r.is_eligible]
            if eligible:
                response_text = get_response("eligible_schemes", lang) + "\n"
                for i, r in enumerate(eligible[:5], 1):
                    name = r.scheme.name_hi if lang == "hi" and r.scheme.name_hi else r.scheme.name
                    response_text += f"{i}. {name} — {int(r.match_score * 100)}%\n"
                state.current_step = "eligibility"
            else:
                response_text = get_response("more_docs", lang, count=len(state.user_profile.documents))
        else:
            response_text = get_response("help", lang)

    state.messages.append(ChatMessage(
        role="assistant",
        content=response_text,
        language=lang,
        timestamp=datetime.now().isoformat(),
    ))

    _sessions[session_id] = state
    return state


def process_document_upload(session_id: str, extracted: ExtractedData) -> ConversationState:
    """Process an uploaded document with OCR results."""
    state = _sessions.get(session_id)
    if not state:
        state = create_session()
        session_id = state.session_id

    lang = state.language
    profile = state.user_profile

    profile.documents.append(extracted)

    if extracted.name and not profile.name:
        profile.name = extracted.name
    if extracted.date_of_birth and not profile.date_of_birth:
        profile.date_of_birth = extracted.date_of_birth
    if extracted.gender and not profile.gender:
        profile.gender = extracted.gender
    if extracted.id_number and not profile.id_number:
        profile.id_number = extracted.id_number
    if extracted.address and not profile.address:
        profile.address = extracted.address
    if extracted.income is not None and profile.income is None:
        profile.income = extracted.income
    if extracted.category and not profile.category:
        profile.category = extracted.category
    if extracted.state and not profile.state:
        profile.state = extracted.state
    if extracted.district and not profile.district:
        profile.district = extracted.district
    if extracted.father_name and not profile.father_name:
        profile.father_name = extracted.father_name

    state.user_profile = profile

    # Use Gemini for friendly document summary
    response_text = generate_document_summary(extracted.model_dump(), lang)

    # Auto-check eligibility
    results = find_eligible_schemes(profile)
    state.eligible_schemes = results
    eligible = [r for r in results if r.is_eligible]

    if eligible:
        response_text += "\n\n" + get_response("eligible_schemes", lang) + "\n"
        for i, r in enumerate(eligible[:5], 1):
            name = r.scheme.name_hi if lang == "hi" and r.scheme.name_hi else r.scheme.name
            response_text += f"{i}. {name} — {int(r.match_score * 100)}%\n"
        state.current_step = "eligibility"
    else:
        response_text += "\n\n" + get_response("more_docs", lang, count=len(profile.documents))
        state.current_step = "document_upload"

    state.messages.append(ChatMessage(
        role="assistant",
        content=response_text,
        language=lang,
        timestamp=datetime.now().isoformat(),
    ))

    _sessions[session_id] = state
    return state


def generate_form(session_id: str, scheme_id: int) -> dict:
    """Generate an application form for a specific scheme."""
    state = _sessions.get(session_id)
    if not state:
        return {"error": "Session not found"}

    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        return {"error": "Scheme not found"}

    application = generate_application(state.user_profile, scheme)

    lang = state.language
    response_text = get_response("form_generated", lang)
    state.messages.append(ChatMessage(
        role="assistant",
        content=response_text,
        language=lang,
        timestamp=datetime.now().isoformat(),
    ))
    state.current_step = "form_generation"
    _sessions[session_id] = state

    return {
        "application": application.model_dump(),
        "message": response_text,
    }
