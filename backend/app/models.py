from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ExtractedData(BaseModel):
    """Data extracted from a document via OCR."""
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    income: Optional[float] = None
    category: Optional[str] = None  # SC/ST/OBC/General
    state: Optional[str] = None
    district: Optional[str] = None
    father_name: Optional[str] = None
    document_type: Optional[str] = None
    raw_text: Optional[str] = None


class UserProfile(BaseModel):
    """Aggregated user profile from multiple documents."""
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    income: Optional[float] = None
    category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    father_name: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    documents: list[ExtractedData] = []


class SchemeInfo(BaseModel):
    """Government scheme information."""
    id: int
    name: str
    name_hi: Optional[str] = None
    description: str
    description_hi: Optional[str] = None
    ministry: str
    category: str  # education, healthcare, agriculture, housing, etc.
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    max_income: Optional[float] = None
    eligible_categories: Optional[str] = None  # comma-separated: SC,ST,OBC,General
    eligible_genders: Optional[str] = None
    eligible_states: Optional[str] = None
    required_documents: Optional[str] = None
    benefits: str
    form_fields: Optional[str] = None  # JSON string of required form fields


class EligibilityResult(BaseModel):
    """Result of checking eligibility for a scheme."""
    scheme: SchemeInfo
    is_eligible: bool
    match_score: float  # 0.0 to 1.0
    reasons: list[str] = []
    missing_info: list[str] = []


class ApplicationForm(BaseModel):
    """Generated application form data."""
    scheme_id: int
    scheme_name: str
    filled_fields: dict
    generated_at: str
    pdf_path: Optional[str] = None


class VoiceRequest(BaseModel):
    """Voice input request."""
    language: str = "hi"


class VoiceResponse(BaseModel):
    """Voice processing response."""
    transcribed_text: str
    language: str
    intent: Optional[str] = None
    entities: dict = {}


class ChatMessage(BaseModel):
    """Chat message for conversation flow."""
    role: str  # "user" or "assistant"
    content: str
    language: str = "hi"
    timestamp: Optional[str] = None


class ConversationState(BaseModel):
    """Tracks the state of a user conversation."""
    session_id: str
    current_step: str = "greeting"  # greeting, query, document_upload, eligibility, confirmation, form_generation
    user_profile: UserProfile = UserProfile()
    eligible_schemes: list[EligibilityResult] = []
    selected_scheme: Optional[int] = None
    messages: list[ChatMessage] = []
    language: str = "hi"
