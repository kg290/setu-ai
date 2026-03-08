# 🌉 Setu AI — सेतु AI

**AI Voice-Based Government Scheme Assistant**

> **Live Demo:** [https://setu-ai-one.vercel.app](https://setu-ai-one.vercel.app)

Setu AI is a voice-driven, multilingual assistant that helps Indian citizens discover and apply for government welfare schemes. It bridges the gap between complex government forms and the people who need them most — by speaking their language, reading their documents, and filling forms on their behalf.

> **"Setu"** (सेतु) means **"Bridge"** — bridging people to government benefits.

---

## 🎯 Problem Statement

Millions of eligible Indians miss out on government schemes due to:
- Complex application forms they can't read
- Language barriers and low digital literacy
- Dependence on expensive middlemen
- Lack of awareness about available schemes

## 💡 Solution

Setu AI provides a **voice-first, mobile-friendly** interface where users can:
1. **Speak** in Hindi or English to interact with the assistant
2. **Scan documents** (Aadhaar, PAN, income/caste certificates) using their phone camera
3. **Auto-extract information** via OCR — no manual data entry needed
4. **Check eligibility** across 8+ government schemes instantly
5. **Fill application forms** with pre-populated data and download completed PDFs

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎤 **Voice-First Interface** | Large mic button — tap and speak in Hindi/English |
| 📷 **Document OCR** | Google Cloud Vision extracts data from Aadhaar, PAN, certificates |
| 🤖 **Gemini AI NLU** | Natural language understanding via Google Gemini 2.0 Flash |
| ✅ **Smart Eligibility** | Automatic matching against 8 government schemes |
| 📝 **Interactive Form Filling** | Pre-filled editable forms with progress tracking |
| 📥 **PDF Generation** | Professional bilingual application forms with ReportLab |
| 🔊 **Text-to-Speech** | Browser-native TTS reads responses aloud |
| 🌐 **Offline Support** | Web Speech API works without internet for voice input |
| 📱 **Mobile-First** | Designed for smartphones, touch-friendly UI |

## 🏛️ Supported Government Schemes

1. **PM Kisan Samman Nidhi** — Agriculture support
2. **PM Awas Yojana** — Housing for all
3. **National Scholarship Portal** — Education scholarships
4. **Ayushman Bharat (PMJAY)** — Healthcare coverage
5. **Sukanya Samriddhi Yojana** — Girl child savings
6. **MGNREGA** — Rural employment guarantee
7. **PM Ujjwala Yojana** — LPG gas connections
8. **PM Mudra Yojana** — Small business loans

---

## 🏗️ Tech Stack

### Backend
- **Python 3.10+** with **FastAPI**
- **Google Cloud Vision API** — OCR document extraction
- **Google Gemini 2.0 Flash** — Conversational AI / NLU
- **ReportLab** — PDF form generation
- **SQLite** — Scheme database
- **Pydantic** — Data validation

### Frontend
- **React 19** with **Vite**
- **Web Speech API** — Browser-native speech recognition
- **SpeechSynthesis API** — Text-to-speech
- **Vanilla CSS** — Mobile-first, voice-first design

---

## 📁 Project Structure

```
AIFORBHARAT/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment variables
│   ├── app/
│   │   ├── config.py              # Settings management
│   │   ├── database.py            # SQLite + scheme seeding
│   │   ├── models.py              # Pydantic data models
│   │   ├── api/
│   │   │   └── routes.py          # REST API endpoints
│   │   └── modules/
│   │       ├── orchestrator.py    # Conversation workflow
│   │       ├── gemini_nlu.py      # Gemini AI integration
│   │       ├── ocr_engine.py      # Document OCR processing
│   │       ├── eligibility_engine.py  # Scheme matching
│   │       ├── form_generator.py  # PDF form generation
│   │       └── voice_engine.py    # Whisper STT (fallback)
│   └── uploads/                   # Generated forms & docs
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                # Main React component
│       ├── index.css              # Voice-first CSS
│       └── services/
│           └── api.js             # API client
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Cloud API credentials (Vision API)
- Gemini API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The app will be available at `http://localhost:5173`

---

## 🔑 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_service_account.json
OCR_LANGUAGES=en,hi
DEFAULT_LANGUAGE=hi
DATABASE_PATH=app/data/setu.db
UPLOAD_DIR=uploads
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/session/create` | Create new conversation session |
| POST | `/api/chat` | Send text/voice message |
| POST | `/api/document/upload` | Upload document for OCR |
| GET | `/api/form/preview/{scheme_id}` | Get form fields with auto-fill data |
| POST | `/api/form/submit` | Submit filled form, generate PDF |
| GET | `/api/form/download/{filename}` | Download generated PDF |
| GET | `/api/schemes` | List all government schemes |
| POST | `/api/schemes/check-eligibility` | Check scheme eligibility |

---

## 🔄 User Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Voice Input │────▸│  Gemini NLU  │────▸│  Intent + Reply │
│  (Hindi/En)  │     │  Processing  │     │  (Bilingual)    │
└─────────────┘     └──────────────┘     └─────────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Document   │────▸│  Google OCR  │────▸│  Auto-Extract   │
│  Photo/Scan │     │  Vision API  │     │  Name, DOB, ID  │
└─────────────┘     └──────────────┘     └─────────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  User       │────▸│  Eligibility │────▸│  Matched Schemes│
│  Profile    │     │  Engine      │     │  with % Score   │
└─────────────┘     └──────────────┘     └─────────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Fill Form  │────▸│  Interactive │────▸│  Download PDF   │
│  (Auto+Edit)│     │  Form Filler │     │  Application    │
└─────────────┘     └──────────────┘     └─────────────────┘
```

---

## 🛡️ Security

- File uploads validated (type + size limits)
- Path traversal prevention on downloads
- CORS configured for frontend origin only
- API keys loaded from environment variables
- Session-based state management

---

## 👥 Team

Built for **AI for Bharat Hackathon**

---

## 📜 License

This project is built for the AI for Bharat Hackathon.
