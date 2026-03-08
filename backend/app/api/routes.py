"""API routes for Setu AI backend."""
import os
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from app.models import UserProfile, ChatMessage
from app.modules.orchestrator import (
    create_session, get_session, process_text_input,
    process_document_upload, generate_form
)
from app.modules.ocr_engine import process_document
from app.modules.eligibility_engine import get_all_schemes, get_scheme_by_id, find_eligible_schemes
from app.modules.form_generator import get_fill_summary
from app.config import settings

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    source: str = "text"  # "text", "voice", "camera"


@router.post("/session/create")
async def api_create_session(language: str = "hi"):
    """Create a new conversation session."""
    state = create_session(language)
    return {
        "session_id": state.session_id,
        "messages": [m.model_dump() for m in state.messages],
        "current_step": state.current_step,
    }


@router.get("/session/{session_id}")
async def api_get_session(session_id: str):
    """Get current session state."""
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": state.session_id,
        "current_step": state.current_step,
        "user_profile": state.user_profile.model_dump(),
        "messages": [m.model_dump() for m in state.messages],
        "eligible_schemes": [
            {
                "scheme": r.scheme.model_dump(),
                "is_eligible": r.is_eligible,
                "match_score": r.match_score,
                "reasons": r.reasons,
                "missing_info": r.missing_info,
            }
            for r in state.eligible_schemes
        ],
    }


@router.post("/chat")
async def api_chat(req: ChatRequest):
    """Send a text or voice-transcribed message to the assistant."""
    state = process_text_input(req.session_id, req.message)
    return {
        "session_id": state.session_id,
        "current_step": state.current_step,
        "messages": [m.model_dump() for m in state.messages],
        "eligible_schemes": [
            {
                "scheme": r.scheme.model_dump(),
                "is_eligible": r.is_eligible,
                "match_score": r.match_score,
            }
            for r in state.eligible_schemes if r.is_eligible
        ],
        "user_profile": state.user_profile.model_dump(),
    }


@router.post("/document/upload")
async def api_upload_document(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload and process a document image."""
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files are allowed (JPEG, PNG, WebP, BMP)")

    # Save the uploaded file
    upload_dir = os.path.join(settings.upload_dir, "documents")
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    safe_filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, safe_filename)

    content = await file.read()
    # Limit file size to 10MB
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # OCR processing
        languages = settings.ocr_languages.split(",")
        extracted = process_document(file_path, languages)

        # Update session with extracted data
        state = process_document_upload(session_id, extracted)

        return {
            "session_id": state.session_id,
            "extracted_data": extracted.model_dump(),
            "current_step": state.current_step,
            "messages": [m.model_dump() for m in state.messages],
            "user_profile": state.user_profile.model_dump(),
            "eligible_schemes": [
                {
                    "scheme": r.scheme.model_dump(),
                    "is_eligible": r.is_eligible,
                    "match_score": r.match_score,
                }
                for r in state.eligible_schemes if r.is_eligible
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.get("/form/preview/{scheme_id}")
async def api_form_preview(scheme_id: int, session_id: str):
    """Preview what fields will be auto-filled for a scheme."""
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    summary = get_fill_summary(state.user_profile, scheme)
    return summary


class FormSubmitRequest(BaseModel):
    session_id: str
    scheme_id: int
    filled_data: dict[str, str]


@router.post("/form/submit")
async def api_submit_filled_form(req: FormSubmitRequest):
    """Accept user-edited form fields and generate a final filled PDF."""
    state = get_session(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    scheme = get_scheme_by_id(req.scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    from app.modules.form_generator import generate_pdf
    pdf_path = generate_pdf(scheme, req.filled_data, state.user_profile)

    return {
        "message": "Form generated successfully",
        "pdf_path": pdf_path,
        "filename": os.path.basename(pdf_path),
    }


@router.post("/form/generate")
async def api_generate_form(session_id: str = Form(...), scheme_id: int = Form(...)):
    """Generate an auto-filled application form PDF."""
    result = generate_form(session_id, scheme_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/form/download/{filename}")
async def api_download_form(filename: str):
    """Download a generated form PDF."""
    # Sanitize filename to prevent path traversal
    safe_name = os.path.basename(filename)
    filepath = os.path.join(settings.upload_dir, "forms", safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Form not found")
    return FileResponse(filepath, media_type="application/pdf", filename=safe_name)


@router.get("/schemes")
async def api_list_schemes():
    """List all available government schemes."""
    schemes = get_all_schemes()
    return {
        "schemes": [s.model_dump() for s in schemes],
        "total": len(schemes),
    }


@router.post("/schemes/check-eligibility")
async def api_check_eligibility(profile: UserProfile, category: str = None):
    """Check eligibility for schemes given a user profile."""
    results = find_eligible_schemes(profile, category)
    return {
        "results": [
            {
                "scheme": r.scheme.model_dump(),
                "is_eligible": r.is_eligible,
                "match_score": r.match_score,
                "reasons": r.reasons,
                "missing_info": r.missing_info,
            }
            for r in results
        ],
        "eligible_count": sum(1 for r in results if r.is_eligible),
        "total_schemes": len(results),
    }


@router.post("/voice/process")
async def api_voice_process(req: ChatRequest):
    """Process voice-transcribed text (transcription done client-side via Web Speech API)."""
    state = process_text_input(req.session_id, req.message)
    return {
        "session_id": state.session_id,
        "current_step": state.current_step,
        "messages": [m.model_dump() for m in state.messages],
        "eligible_schemes": [
            {
                "scheme": r.scheme.model_dump(),
                "is_eligible": r.is_eligible,
                "match_score": r.match_score,
            }
            for r in state.eligible_schemes if r.is_eligible
        ],
        "user_profile": state.user_profile.model_dump(),
    }


@router.get("/schemes/offline-data")
async def api_offline_data():
    """Get all scheme data for offline caching."""
    schemes = get_all_schemes()
    return {
        "schemes": [s.model_dump() for s in schemes],
        "cached_at": datetime.now().isoformat(),
    }
