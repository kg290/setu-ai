"""Form auto-fill and PDF generation module — generates fully filled application forms."""
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib import colors
from app.models import UserProfile, SchemeInfo, ApplicationForm
from app.config import settings


# Bilingual labels for every possible form field
FIELD_LABELS = {
    "name": ("Full Name", "पूरा नाम"),
    "father_name": ("Father's/Guardian's Name", "पिता/अभिभावक का नाम"),
    "date_of_birth": ("Date of Birth", "जन्म तिथि"),
    "gender": ("Gender", "लिंग"),
    "id_number": ("Aadhaar Number", "आधार संख्या"),
    "address": ("Residential Address", "आवासीय पता"),
    "state": ("State", "राज्य"),
    "district": ("District", "जिला"),
    "income": ("Annual Family Income", "वार्षिक पारिवारिक आय"),
    "category": ("Social Category (SC/ST/OBC/General)", "सामाजिक श्रेणी"),
    "education": ("Highest Education", "उच्चतम शिक्षा"),
    "occupation": ("Occupation", "व्यवसाय"),
    "bank_account": ("Bank Account Number", "बैंक खाता संख्या"),
    "ifsc_code": ("Bank IFSC Code", "बैंक IFSC कोड"),
    "mobile_number": ("Mobile Number", "मोबाइल नंबर"),
    "land_area": ("Agricultural Land Area (acres)", "कृषि भूमि क्षेत्र (एकड़)"),
    "family_members": ("Number of Family Members", "परिवार के सदस्यों की संख्या"),
    "child_name": ("Child's Name", "बच्चे का नाम"),
    "parent_name": ("Parent/Guardian Name", "अभिभावक का नाम"),
    "institution_name": ("Educational Institution", "शैक्षणिक संस्थान"),
    "course_name": ("Course/Programme", "पाठ्यक्रम"),
    "business_type": ("Type of Business/Enterprise", "व्यवसाय का प्रकार"),
    "loan_amount": ("Loan Amount Required", "आवश्यक ऋण राशि"),
    "deposit_amount": ("Deposit Amount", "जमा राशि"),
    "email": ("Email Address", "ईमेल पता"),
    "age": ("Age", "आयु"),
}

# Extra data we can derive/infer
DERIVED_FIELDS = {
    "age": lambda p: _calc_age(p.date_of_birth) if p.date_of_birth else None,
}


def _calc_age(dob_str: str) -> int | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            dob = datetime.strptime(dob_str, fmt)
            today = datetime.now()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except ValueError:
            continue
    return None


def map_profile_to_form(profile: UserProfile, form_fields: list[str]) -> dict:
    """Map user profile data to form fields, filling in everything possible."""
    profile_dict = profile.model_dump()
    filled = {}

    for field in form_fields:
        # Try direct profile match first
        value = profile_dict.get(field)

        # Try derived fields
        if value is None and field in DERIVED_FIELDS:
            value = DERIVED_FIELDS[field](profile)

        # Map parent_name to father_name or name depending on scheme
        if value is None and field == "parent_name":
            value = profile_dict.get("father_name") or profile_dict.get("name")
        if value is None and field == "child_name":
            value = profile_dict.get("name")

        if value is not None:
            if field == "income":
                filled[field] = f"₹ {value:,.0f}"
            elif field == "age":
                filled[field] = str(value)
            else:
                filled[field] = str(value)
        else:
            filled[field] = None  # Explicitly None = not filled

    return filled


def get_fill_summary(profile: UserProfile, scheme: SchemeInfo) -> dict:
    """Get a summary of what can be auto-filled vs what's missing."""
    form_fields = json.loads(scheme.form_fields) if scheme.form_fields else []
    filled = map_profile_to_form(profile, form_fields)

    auto_filled = {k: v for k, v in filled.items() if v is not None}
    missing = [k for k, v in filled.items() if v is None]

    return {
        "scheme_id": scheme.id,
        "scheme_name": scheme.name,
        "scheme_name_hi": scheme.name_hi,
        "total_fields": len(form_fields),
        "filled_count": len(auto_filled),
        "missing_count": len(missing),
        "fill_percentage": round(len(auto_filled) / len(form_fields) * 100) if form_fields else 0,
        "auto_filled": {
            k: {"value": v, "label": FIELD_LABELS.get(k, (k, k))[0], "label_hi": FIELD_LABELS.get(k, (k, k))[1]}
            for k, v in auto_filled.items()
        },
        "missing_fields": [
            {"field": f, "label": FIELD_LABELS.get(f, (f, f))[0], "label_hi": FIELD_LABELS.get(f, (f, f))[1]}
            for f in missing
        ],
    }


def generate_pdf(
    scheme: SchemeInfo,
    filled_fields: dict,
    profile: UserProfile,
    output_dir: str = None,
) -> str:
    """Generate a properly auto-filled PDF application form."""
    if output_dir is None:
        output_dir = os.path.join(settings.upload_dir, "forms")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"application_{scheme.id}_{timestamp}.pdf"
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_s = ParagraphStyle("Title2", parent=styles["Title"], fontSize=15,
                             textColor=HexColor("#0d47a1"), alignment=TA_CENTER, spaceAfter=2)
    subtitle_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10,
                                textColor=HexColor("#555"), alignment=TA_CENTER, spaceAfter=4)
    ministry_s = ParagraphStyle("Ministry", parent=styles["Normal"], fontSize=9,
                                textColor=HexColor("#1565c0"), alignment=TA_CENTER, spaceAfter=8)
    heading_s = ParagraphStyle("Head", parent=styles["Heading2"], fontSize=11,
                               textColor=HexColor("#0d47a1"), spaceBefore=12, spaceAfter=6)
    label_s = ParagraphStyle("Label", parent=styles["Normal"], fontSize=8.5,
                              textColor=HexColor("#666"))
    value_s = ParagraphStyle("Value", parent=styles["Normal"], fontSize=10,
                              textColor=HexColor("#111"), leading=13)
    filled_s = ParagraphStyle("Filled", parent=styles["Normal"], fontSize=10,
                               textColor=HexColor("#1b5e20"), leading=13)
    empty_s = ParagraphStyle("Empty", parent=styles["Normal"], fontSize=9,
                              textColor=HexColor("#c62828"), leading=13)
    footer_s = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7,
                               textColor=colors.grey, alignment=TA_CENTER)
    note_s = ParagraphStyle("Note", parent=styles["Normal"], fontSize=8,
                             textColor=HexColor("#e65100"), leading=11)

    elements = []

    # ─── Header ───
    elements.append(Paragraph("भारत सरकार / Government of India", subtitle_s))
    elements.append(Paragraph(scheme.ministry, ministry_s))
    elements.append(HRFlowable(width="100%", color=HexColor("#1565c0"), thickness=2))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"{scheme.name_hi or scheme.name}<br/><font size='9'>{scheme.name}</font>",
        title_s
    ))
    elements.append(Paragraph("Application Form / आवेदन पत्र", subtitle_s))
    elements.append(HRFlowable(width="100%", color=HexColor("#e0e0e0"), thickness=1))
    elements.append(Spacer(1, 4))

    # ─── Application Reference ───
    ref_no = f"SETU-{scheme.id}-{timestamp}"
    ref_data = [
        [f"Application Ref No: {ref_no}", f"Date: {datetime.now().strftime('%d/%m/%Y')}"],
    ]
    ref_table = Table(ref_data, colWidths=[10 * cm, 7 * cm])
    ref_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#666")),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elements.append(ref_table)
    elements.append(Spacer(1, 6))

    # ─── Scheme Benefits ───
    elements.append(Paragraph("Scheme Benefits / योजना लाभ", heading_s))
    benefits_hi = scheme.description_hi or scheme.description
    elements.append(Paragraph(f"<b>{benefits_hi}</b>", value_s))
    elements.append(Paragraph(f"<i>{scheme.benefits}</i>", label_s))
    elements.append(Spacer(1, 6))

    # ─── Auto-Filled Applicant Details ───
    elements.append(Paragraph("Applicant Details / आवेदक का विवरण (Auto-Filled / स्वतः भरा गया)", heading_s))

    filled_count = sum(1 for v in filled_fields.values() if v is not None)
    total_count = len(filled_fields)
    fill_pct = round(filled_count / total_count * 100) if total_count else 0
    elements.append(Paragraph(
        f"<b>{filled_count}/{total_count} fields auto-filled ({fill_pct}%)</b> — "
        f"<font color='#1b5e20'>■ Filled</font> | <font color='#c62828'>□ Needs manual entry</font>",
        note_s
    ))
    elements.append(Spacer(1, 4))

    # Build form table
    form_rows = []
    row_colors = []
    sno = 0
    for field, value in filled_fields.items():
        sno += 1
        labels = FIELD_LABELS.get(field, (field.replace("_", " ").title(), field))
        label_text = f"{sno}. {labels[0]}\n    {labels[1]}"

        if value is not None:
            val_text = f"✅  {value}"
            is_filled = True
        else:
            val_text = "☐  (To be filled manually / मैन्युअल भरें)"
            is_filled = False

        form_rows.append([label_text, val_text])
        row_colors.append(is_filled)

    if form_rows:
        form_table = Table(form_rows, colWidths=[7.5 * cm, 9.5 * cm])
        style_cmds = [
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#ccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]
        # Color rows based on fill status
        for i, is_filled in enumerate(row_colors):
            if is_filled:
                style_cmds.append(("BACKGROUND", (1, i), (1, i), HexColor("#e8f5e9")))
                style_cmds.append(("TEXTCOLOR", (1, i), (1, i), HexColor("#1b5e20")))
            else:
                style_cmds.append(("BACKGROUND", (1, i), (1, i), HexColor("#fff3e0")))
                style_cmds.append(("TEXTCOLOR", (1, i), (1, i), HexColor("#c62828")))
            style_cmds.append(("BACKGROUND", (0, i), (0, i), HexColor("#e3f2fd")))

        form_table.setStyle(TableStyle(style_cmds))
        elements.append(form_table)

    elements.append(Spacer(1, 8))

    # ─── Required Documents Checklist ───
    if scheme.required_documents:
        elements.append(Paragraph("Required Documents / आवश्यक दस्तावेज़", heading_s))
        docs_list = [d.strip() for d in scheme.required_documents.split(",")]
        uploaded_types = []
        if profile.documents:
            uploaded_types = [d.document_type or "" for d in profile.documents]

        for doc_name in docs_list:
            is_uploaded = any(doc_name.lower() in ut.lower() for ut in uploaded_types if ut)
            mark = "✅" if is_uploaded else "☐"
            status = "(Uploaded)" if is_uploaded else "(Not uploaded / अपलोड नहीं हुआ)"
            elements.append(Paragraph(f"  {mark}  {doc_name} {status}", value_s))
        elements.append(Spacer(1, 8))

    # ─── Declaration ───
    elements.append(Paragraph("Declaration / घोषणा", heading_s))
    elements.append(Paragraph(
        "I, <b>{name}</b>, hereby declare that all the information provided in this application form "
        "is true, correct and complete to the best of my knowledge and belief. I understand that any "
        "false information may lead to rejection of my application.".format(
            name=filled_fields.get("name") or "_______________"
        ),
        value_s,
    ))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "मैं, <b>{name}</b>, घोषणा करता/करती हूँ कि इस आवेदन पत्र में दी गई सभी जानकारी मेरी "
        "जानकारी और विश्वास के अनुसार सत्य, सही और पूर्ण है।".format(
            name=filled_fields.get("name") or "_______________"
        ),
        value_s,
    ))
    elements.append(Spacer(1, 24))

    # ─── Signature ───
    sig_data = [
        [
            f"Place / स्थान: {filled_fields.get('district') or filled_fields.get('state') or '___________'}",
            "",
            "Applicant's Signature / आवेदक के हस्ताक्षर"
        ],
        [
            f"Date / दिनांक: {datetime.now().strftime('%d/%m/%Y')}",
            "",
            f"\n({filled_fields.get('name') or '_______________'})"
        ],
    ]
    sig_table = Table(sig_data, colWidths=[7 * cm, 3 * cm, 7 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("LINEABOVE", (2, 0), (2, 0), 1, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)

    # ─── Footer ───
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", color=HexColor("#e0e0e0"), thickness=0.5))
    elements.append(Paragraph(
        f"<i>Auto-generated by Setu AI (सेतु AI) | Ref: {ref_no} | "
        f"This is a pre-filled draft. Please verify all details before submission.</i>",
        footer_s,
    ))

    doc.build(elements)
    return filepath


def generate_application(profile: UserProfile, scheme: SchemeInfo) -> ApplicationForm:
    """Generate a complete auto-filled application for a scheme."""
    form_fields = json.loads(scheme.form_fields) if scheme.form_fields else []
    filled_fields = map_profile_to_form(profile, form_fields)
    pdf_path = generate_pdf(scheme, filled_fields, profile)

    return ApplicationForm(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        filled_fields=filled_fields,
        generated_at=datetime.now().isoformat(),
        pdf_path=pdf_path,
    )
