"""Gemini NLU module - Natural Language Understanding using Google Gemini API."""
import os
import json
import google.generativeai as genai
from app.config import settings

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


SYSTEM_PROMPT = """You are Setu AI (सेतु AI), a friendly, empathetic government scheme assistant for Indian citizens.
You help low-literacy, rural users navigate government welfare schemes in simple Hindi or English.

Your personality:
- Warm, patient, respectful - like a helpful village elder
- Use simple, everyday language (avoid bureaucratic jargon)
- Always be encouraging and supportive
- Address the user respectfully

Your capabilities:
1. Guide users to upload documents (Aadhaar, income certificate, caste certificate, etc.)
2. Explain which government schemes they qualify for
3. Help them understand scheme benefits in simple terms
4. Guide them through the application process step by step

IMPORTANT RULES:
- Respond in the SAME LANGUAGE the user speaks (Hindi or English)
- Keep responses SHORT (2-3 sentences max) - they will be read aloud via TTS
- Use simple words a person with basic education can understand
- Be culturally sensitive and respectful
- If the user's intent is unclear, gently ask for clarification
- Never fabricate scheme information - only reference the schemes provided

You must respond with valid JSON in this exact format:
{
  "response_text": "Your response to the user in their language",
  "intent": "one of: greeting, check_eligibility, apply, upload_document, list_schemes, help, confirm_yes, confirm_no, provide_info, unknown",
  "entities": {"category": "optional scheme category if mentioned"},
  "suggested_action": "one of: none, ask_document, show_schemes, start_application, generate_form, ask_confirmation"
}"""


def process_with_gemini(
    user_text: str,
    language: str = "hi",
    user_profile: dict = None,
    eligible_schemes: list = None,
    current_step: str = "greeting",
    conversation_history: list = None,
) -> dict:
    """Process user input through Gemini for intelligent NLU and response generation."""
    model = _get_model()

    # Build context
    context_parts = [f"Current language: {'Hindi' if language == 'hi' else 'English'}"]
    context_parts.append(f"Current workflow step: {current_step}")

    if user_profile:
        filled = {k: v for k, v in user_profile.items() if v and k != "documents"}
        if filled:
            context_parts.append(f"User profile so far: {json.dumps(filled, ensure_ascii=False)}")
        docs = user_profile.get("documents", [])
        if docs:
            doc_types = [d.get("document_type", "unknown") for d in docs]
            context_parts.append(f"Documents uploaded: {', '.join(doc_types)}")

    if eligible_schemes:
        scheme_list = []
        for s in eligible_schemes[:5]:
            scheme = s.get("scheme", s)
            name = scheme.get("name_hi", scheme.get("name", ""))
            score = s.get("match_score", 0)
            scheme_list.append(f"- {name} (match: {int(score*100)}%)")
        context_parts.append("Eligible schemes:\n" + "\n".join(scheme_list))

    # Recent conversation for context (last 4 messages)
    if conversation_history:
        recent = conversation_history[-4:]
        history_text = "\n".join(
            f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
            for m in recent
        )
        context_parts.append(f"Recent conversation:\n{history_text}")

    context = "\n".join(context_parts)

    prompt = f"""{SYSTEM_PROMPT}

Context:
{context}

User says: "{user_text}"

Respond with JSON only:"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        return {
            "response_text": result.get("response_text", ""),
            "intent": result.get("intent", "unknown"),
            "entities": result.get("entities", {}),
            "suggested_action": result.get("suggested_action", "none"),
            "source": "gemini",
        }
    except Exception as e:
        # Fallback to basic response
        return {
            "response_text": _fallback_response(user_text, language),
            "intent": "unknown",
            "entities": {},
            "suggested_action": "none",
            "source": "fallback",
            "error": str(e),
        }


def _fallback_response(text: str, language: str) -> str:
    """Provide a basic fallback when Gemini is unavailable."""
    if language == "hi":
        return "मैं सेतु AI हूँ। कृपया अपना दस्तावेज़ अपलोड करें या बताएं कि आपको किस योजना के बारे में जानना है।"
    return "I am Setu AI. Please upload your document or tell me which scheme you'd like to know about."


def generate_document_summary(extracted_data: dict, language: str = "hi") -> str:
    """Generate a simple, voice-friendly summary of extracted document data."""
    model = _get_model()

    prompt = f"""You are Setu AI. A user just uploaded a document and we extracted this data:
{json.dumps(extracted_data, ensure_ascii=False, indent=2)}

Generate a brief, friendly summary in {'Hindi' if language == 'hi' else 'English'} telling the user what information was found.
Keep it under 3 sentences. Use simple language suitable for text-to-speech.
Return ONLY the summary text, no JSON."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        if language == "hi":
            doc_type = extracted_data.get("document_type", "दस्तावेज़")
            return f"आपका {doc_type} सफलतापूर्वक प्रोसेस हो गया है।"
        doc_type = extracted_data.get("document_type", "document")
        return f"Your {doc_type} has been processed successfully."
