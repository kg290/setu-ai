"""Database module for storing scheme information and user data."""
import sqlite3
import json
import os
from app.config import settings


def get_db_connection():
    """Get a database connection."""
    os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_hi TEXT,
            description TEXT NOT NULL,
            description_hi TEXT,
            ministry TEXT NOT NULL,
            category TEXT NOT NULL,
            min_age INTEGER,
            max_age INTEGER,
            max_income REAL,
            eligible_categories TEXT,
            eligible_genders TEXT,
            eligible_states TEXT,
            required_documents TEXT,
            benefits TEXT NOT NULL,
            form_fields TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_profile TEXT,
            conversation_state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            scheme_id INTEGER,
            filled_data TEXT,
            pdf_path TEXT,
            status TEXT DEFAULT 'generated',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheme_id) REFERENCES schemes(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_schemes():
    """Seed the database with Indian government schemes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM schemes")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    schemes = [
        {
            "name": "PM Kisan Samman Nidhi",
            "name_hi": "प्रधानमंत्री किसान सम्मान निधि",
            "description": "Financial assistance of Rs 6000 per year to small and marginal farmers",
            "description_hi": "छोटे और सीमांत किसानों को प्रति वर्ष 6000 रुपये की वित्तीय सहायता",
            "ministry": "Ministry of Agriculture",
            "category": "agriculture",
            "min_age": 18,
            "max_age": None,
            "max_income": None,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,Land Records,Bank Passbook",
            "benefits": "Rs 6000 per year in 3 installments of Rs 2000",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "bank_account", "ifsc_code",
                "land_area", "mobile_number"
            ])
        },
        {
            "name": "PM Awas Yojana (Gramin)",
            "name_hi": "प्रधानमंत्री आवास योजना (ग्रामीण)",
            "description": "Housing assistance for rural poor to build pucca houses",
            "description_hi": "ग्रामीण गरीबों को पक्के मकान बनाने के लिए आवास सहायता",
            "ministry": "Ministry of Rural Development",
            "category": "housing",
            "min_age": 18,
            "max_age": None,
            "max_income": 300000,
            "eligible_categories": "SC,ST,OBC",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,Income Certificate,BPL Card",
            "benefits": "Rs 1.20 Lakh in plain areas, Rs 1.30 Lakh in hilly areas",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "income", "category",
                "bank_account", "mobile_number"
            ])
        },
        {
            "name": "National Scholarship Portal - Post Matric",
            "name_hi": "राष्ट्रीय छात्रवृत्ति पोर्टल - पोस्ट मैट्रिक",
            "description": "Scholarship for SC/ST/OBC students pursuing post-matriculation education",
            "description_hi": "पोस्ट-मैट्रिक शिक्षा प्राप्त करने वाले SC/ST/OBC छात्रों के लिए छात्रवृत्ति",
            "ministry": "Ministry of Social Justice",
            "category": "education",
            "min_age": 15,
            "max_age": 35,
            "max_income": 250000,
            "eligible_categories": "SC,ST,OBC",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,Income Certificate,Caste Certificate,Marksheet",
            "benefits": "Tuition fee reimbursement and maintenance allowance",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "income", "category",
                "education", "institution_name", "course_name",
                "bank_account", "mobile_number"
            ])
        },
        {
            "name": "Ayushman Bharat - PMJAY",
            "name_hi": "आयुष्मान भारत - पीएमजेएवाई",
            "description": "Health insurance cover of Rs 5 lakh per family per year for secondary and tertiary care",
            "description_hi": "माध्यमिक और तृतीयक देखभाल के लिए प्रति परिवार प्रति वर्ष 5 लाख रुपये का स्वास्थ्य बीमा",
            "ministry": "Ministry of Health",
            "category": "healthcare",
            "min_age": None,
            "max_age": None,
            "max_income": 200000,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,Ration Card,Income Certificate",
            "benefits": "Rs 5 Lakh health insurance coverage per family per year",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "income",
                "family_members", "mobile_number"
            ])
        },
        {
            "name": "Sukanya Samriddhi Yojana",
            "name_hi": "सुकन्या समृद्धि योजना",
            "description": "Savings scheme for girl child with high interest rate and tax benefits",
            "description_hi": "उच्च ब्याज दर और कर लाभ के साथ बालिका के लिए बचत योजना",
            "ministry": "Ministry of Finance",
            "category": "women_child",
            "min_age": 0,
            "max_age": 10,
            "max_income": None,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Female",
            "eligible_states": None,
            "required_documents": "Birth Certificate,Aadhaar Card (Parent),Address Proof",
            "benefits": "High interest savings account with tax benefits under 80C",
            "form_fields": json.dumps([
                "child_name", "parent_name", "date_of_birth", "gender",
                "id_number", "address", "state", "district",
                "bank_account", "deposit_amount", "mobile_number"
            ])
        },
        {
            "name": "MGNREGA",
            "name_hi": "मनरेगा",
            "description": "Guaranteed 100 days of wage employment per year to rural households",
            "description_hi": "ग्रामीण परिवारों को प्रति वर्ष 100 दिनों के वेतन रोजगार की गारंटी",
            "ministry": "Ministry of Rural Development",
            "category": "employment",
            "min_age": 18,
            "max_age": 65,
            "max_income": None,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,Address Proof,Bank Passbook",
            "benefits": "100 days guaranteed employment with minimum wage",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "category",
                "bank_account", "mobile_number"
            ])
        },
        {
            "name": "PM Ujjwala Yojana",
            "name_hi": "प्रधानमंत्री उज्ज्वला योजना",
            "description": "Free LPG connections to women from BPL households",
            "description_hi": "बीपीएल परिवारों की महिलाओं को मुफ्त एलपीजी कनेक्शन",
            "ministry": "Ministry of Petroleum",
            "category": "welfare",
            "min_age": 18,
            "max_age": None,
            "max_income": 200000,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,BPL Card,Address Proof,Bank Passbook",
            "benefits": "Free LPG connection with first refill and stove",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "income",
                "bank_account", "mobile_number"
            ])
        },
        {
            "name": "Pradhan Mantri Mudra Yojana",
            "name_hi": "प्रधानमंत्री मुद्रा योजना",
            "description": "Loans up to Rs 10 lakh for non-corporate small business",
            "description_hi": "गैर-कॉर्पोरेट छोटे व्यवसाय के लिए 10 लाख रुपये तक का ऋण",
            "ministry": "Ministry of Finance",
            "category": "business",
            "min_age": 18,
            "max_age": 65,
            "max_income": None,
            "eligible_categories": "SC,ST,OBC,General",
            "eligible_genders": "Male,Female",
            "eligible_states": None,
            "required_documents": "Aadhaar Card,PAN Card,Business Plan,Address Proof",
            "benefits": "Collateral-free loans: Shishu (up to 50K), Kishore (50K-5L), Tarun (5L-10L)",
            "form_fields": json.dumps([
                "name", "father_name", "date_of_birth", "gender", "id_number",
                "address", "state", "district", "business_type",
                "loan_amount", "bank_account", "mobile_number"
            ])
        },
    ]

    for scheme in schemes:
        cursor.execute("""
            INSERT INTO schemes (name, name_hi, description, description_hi, ministry,
                category, min_age, max_age, max_income, eligible_categories,
                eligible_genders, eligible_states, required_documents, benefits, form_fields)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scheme["name"], scheme["name_hi"], scheme["description"],
            scheme["description_hi"], scheme["ministry"], scheme["category"],
            scheme["min_age"], scheme["max_age"], scheme["max_income"],
            scheme["eligible_categories"], scheme["eligible_genders"],
            scheme["eligible_states"], scheme["required_documents"],
            scheme["benefits"], scheme["form_fields"]
        ))

    conn.commit()
    conn.close()
