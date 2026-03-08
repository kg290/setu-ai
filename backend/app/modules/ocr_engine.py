"""Document OCR and data extraction module using Google Cloud Vision API."""
import os
import re
from typing import Optional
from app.models import ExtractedData

# Set credentials from env if not already set
_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _credentials_path and not os.path.isabs(_credentials_path):
    # Resolve relative to backend directory
    _credentials_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), _credentials_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _credentials_path

_vision_client = None


def _get_vision_client():
    """Get or initialize the Google Cloud Vision client."""
    global _vision_client
    if _vision_client is None:
        from google.cloud import vision
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


def extract_text_from_image(image_path: str, languages: list[str] = None) -> str:
    """Extract raw text from an image using Google Cloud Vision API."""
    from google.cloud import vision

    client = _get_vision_client()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)

    # Use document_text_detection for better structured text
    image_context = vision.ImageContext()
    if languages:
        image_context.language_hints = languages

    response = client.document_text_detection(image=image, image_context=image_context)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    full_text = response.full_text_annotation.text if response.full_text_annotation else ""
    return full_text


def detect_document_type(text: str) -> str:
    """Detect the type of document from extracted text."""
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["aadhaar", "uidai", "unique identification", "आधार"]):
        return "aadhaar"
    elif any(kw in text_lower for kw in ["pan", "permanent account", "income tax", "पैन"]):
        return "pan"
    elif any(kw in text_lower for kw in ["voter", "election", "electors", "निर्वाचन", "मतदाता"]):
        return "voter_id"
    elif any(kw in text_lower for kw in ["ration", "राशन", "bpl", "apl"]):
        return "ration_card"
    elif any(kw in text_lower for kw in ["income certificate", "आय प्रमाण", "annual income"]):
        return "income_certificate"
    elif any(kw in text_lower for kw in ["caste certificate", "जाति प्रमाण", "sc", "st", "obc"]):
        return "caste_certificate"
    elif any(kw in text_lower for kw in ["birth", "जन्म"]):
        return "birth_certificate"
    elif any(kw in text_lower for kw in ["marksheet", "result", "marks", "अंकपत्र"]):
        return "marksheet"
    else:
        return "unknown"


def extract_aadhaar_data(text: str) -> dict:
    """Extract data from Aadhaar card text."""
    data = {}

    # Aadhaar number (12 digits, possibly with spaces)
    aadhaar_match = re.search(r'\b(\d{4}\s?\d{4}\s?\d{4})\b', text)
    if aadhaar_match:
        data["id_number"] = aadhaar_match.group(1).replace(" ", "")

    # Date of birth
    dob_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})', text)
    if dob_match:
        data["date_of_birth"] = dob_match.group(1)

    # Gender
    text_lower = text.lower()
    if "male" in text_lower and "female" not in text_lower:
        data["gender"] = "Male"
    elif "female" in text_lower:
        data["gender"] = "Female"
    elif "पुरुष" in text:
        data["gender"] = "Male"
    elif "महिला" in text or "स्त्री" in text:
        data["gender"] = "Female"

    # Name extraction - usually first capitalized line
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if len(line) > 3 and not any(kw in line.lower() for kw in [
            "government", "india", "aadhaar", "uidai", "male", "female",
            "dob", "year", "address", "vid"
        ]):
            if re.match(r'^[A-Z][a-z]', line) or re.match(r'^[\u0900-\u097F]', line):
                data["name"] = line
                break

    return data


def extract_income_certificate_data(text: str) -> dict:
    """Extract data from income certificate."""
    data = {}

    # Income amount
    income_match = re.search(r'(?:rs\.?|₹|rupees?)\s*([\d,]+)', text.lower())
    if income_match:
        data["income"] = float(income_match.group(1).replace(",", ""))

    # Annual income specific pattern
    annual_match = re.search(r'annual\s+income.*?(\d[\d,]+)', text.lower())
    if annual_match:
        data["income"] = float(annual_match.group(1).replace(",", ""))

    return data


def extract_caste_certificate_data(text: str) -> dict:
    """Extract data from caste certificate."""
    data = {}
    text_lower = text.lower()

    if "scheduled caste" in text_lower or "sc" in text_lower:
        data["category"] = "SC"
    elif "scheduled tribe" in text_lower or "st" in text_lower:
        data["category"] = "ST"
    elif "other backward" in text_lower or "obc" in text_lower:
        data["category"] = "OBC"
    elif "general" in text_lower:
        data["category"] = "General"

    return data


def process_document(image_path: str, languages: list[str] = None) -> ExtractedData:
    """Process a document image and extract structured data."""
    raw_text = extract_text_from_image(image_path, languages)
    doc_type = detect_document_type(raw_text)

    extracted = {"raw_text": raw_text, "document_type": doc_type}

    if doc_type == "aadhaar":
        extracted.update(extract_aadhaar_data(raw_text))
    elif doc_type == "income_certificate":
        extracted.update(extract_income_certificate_data(raw_text))
    elif doc_type == "caste_certificate":
        extracted.update(extract_caste_certificate_data(raw_text))

    # Common extractions for any document
    # Address patterns
    address_match = re.search(
        r'(?:address|पता)[:\s]*(.+?)(?:\n|$)',
        raw_text, re.IGNORECASE
    )
    if address_match and "address" not in extracted:
        extracted["address"] = address_match.group(1).strip()

    # State detection
    indian_states = [
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
        "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
        "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
        "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
        "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
        "west bengal", "delhi"
    ]
    text_lower = raw_text.lower()
    for state in indian_states:
        if state in text_lower:
            extracted["state"] = state.title()
            break

    return ExtractedData(**{k: v for k, v in extracted.items() if k in ExtractedData.model_fields})
