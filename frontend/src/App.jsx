import { useState, useEffect, useRef, useCallback } from "react";
import "./index.css";
import {
  createSession,
  sendMessage,
  uploadDocument,
  generateForm,
  getFormPreview,
  submitFilledForm,
  getFormDownloadUrl,
} from "./services/api";

const STEPS = [
  { key: "greeting", icon: "🏠", label: "शुरू", labelEn: "Start" },
  { key: "document_upload", icon: "📷", label: "दस्तावेज़", labelEn: "Document" },
  { key: "eligibility", icon: "✅", label: "पात्रता", labelEn: "Eligibility" },
  { key: "confirmation", icon: "🤝", label: "पुष्टि", labelEn: "Confirm" },
  { key: "form_generation", icon: "📝", label: "आवेदन", labelEn: "Form" },
];

// Web Speech API setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState("hi");
  const [profile, setProfile] = useState({});
  const [eligibleSchemes, setEligibleSchemes] = useState([]);
  const [currentStep, setCurrentStep] = useState("greeting");
  const [generatedPdf, setGeneratedPdf] = useState(null);
  const [formPreview, setFormPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [formFiller, setFormFiller] = useState(null); // {schemeId, schemeName, fields: {key: {value, label, label_hi}}}
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Voice state
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // UI state
  const [showChat, setShowChat] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const recognitionRef = useRef(null);

  // Online/offline detection
  useEffect(() => {
    const goOnline = () => setIsOnline(true);
    const goOffline = () => setIsOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  // Initialize session
  useEffect(() => {
    initSession();
  }, []);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Speak new assistant messages
  useEffect(() => {
    if (!ttsEnabled || messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.role === "assistant") {
      speak(lastMsg.content);
    }
  }, [messages, ttsEnabled]);

  async function initSession() {
    try {
      const data = await createSession(language);
      setSessionId(data.session_id);
      setMessages(data.messages || []);
      setCurrentStep(data.current_step || "greeting");
    } catch {
      setMessages([
        {
          role: "assistant",
          content: language === "hi"
            ? "सर्वर से कनेक्ट नहीं हो पा रहा। कृपया बाद में प्रयास करें।"
            : "Cannot connect to server. Please try again later.",
          language,
        },
      ]);
    }
  }

  function handleSessionResponse(data) {
    if (data.messages) setMessages(data.messages);
    if (data.current_step) setCurrentStep(data.current_step);
    if (data.user_profile) setProfile(data.user_profile);
    if (data.eligible_schemes) setEligibleSchemes(data.eligible_schemes);
  }

  // ── Text-to-Speech ──
  function speak(text) {
    if (!ttsEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#_\-|]/g, "").replace(/\n+/g, ". ");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = language === "hi" ? "hi-IN" : "en-IN";
    utterance.rate = 0.9;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }

  function stopSpeaking() {
    window.speechSynthesis?.cancel();
  }

  // ── Speech Recognition (Web Speech API — offline capable) ──
  function startListening() {
    if (!SpeechRecognition) {
      alert(language === "hi"
        ? "आपका ब्राउज़र वॉइस को सपोर्ट नहीं करता"
        : "Your browser doesn't support voice input");
      return;
    }

    stopSpeaking();

    const recognition = new SpeechRecognition();
    recognition.lang = language === "hi" ? "hi-IN" : "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript("");
    };

    recognition.onresult = (event) => {
      let interim = "";
      let final_ = "";
      for (let i = 0; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          final_ += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      setTranscript(final_ || interim);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      if (event.error !== "no-speech") {
        console.error("Speech recognition error:", event.error);
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setIsListening(false);
  }

  // Submit the voice transcript
  useEffect(() => {
    if (!isListening && transcript.trim()) {
      handleSendText(transcript.trim());
      setTranscript("");
    }
  }, [isListening]);

  // ── Send message ──
  async function handleSendText(text) {
    if (!text || !sessionId) return;
    setShowChat(true);
    setLoading(true);
    try {
      const data = await sendMessage(sessionId, text, "voice");
      handleSessionResponse(data);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: language === "hi" ? "त्रुटि हुई" : "Error occurred", language },
      ]);
    }
    setLoading(false);
  }

  async function handleSendInput() {
    if (!input.trim()) return;
    const text = input.trim();
    setInput("");
    await handleSendText(text);
  }

  // ── Document upload (file or camera) ──
  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file || !sessionId) return;
    setShowChat(true);
    setLoading(true);
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: `📷 ${language === "hi" ? "दस्तावेज़ भेजा" : "Document sent"}`,
        language,
      },
    ]);
    try {
      const data = await uploadDocument(sessionId, file);
      handleSessionResponse(data);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: language === "hi"
            ? "दस्तावेज़ पढ़ने में त्रुटि हुई। कृपया दोबारा प्रयास करें।"
            : "Error reading document. Please try again.",
          language,
        },
      ]);
    }
    setLoading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
  }

  // ── Open interactive form filler with pre-filled data ──
  async function handlePreviewForm(schemeId) {
    if (!sessionId) return;
    setPreviewLoading(true);
    try {
      const data = await getFormPreview(sessionId, schemeId);
      // Build editable fields object: every field gets a value (pre-filled or empty)
      const fields = {};
      // Add auto-filled fields
      for (const [key, info] of Object.entries(data.auto_filled || {})) {
        fields[key] = { value: info.value || "", label: info.label, label_hi: info.label_hi };
      }
      // Add missing fields as empty
      for (const f of data.missing_fields || []) {
        fields[f.field] = { value: "", label: f.label, label_hi: f.label_hi };
      }
      setFormFiller({
        schemeId: data.scheme_id,
        schemeName: data.scheme_name,
        schemeNameHi: data.scheme_name_hi,
        fields,
        totalFields: data.total_fields,
      });
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: language === "hi" ? "फॉर्म लोड करने में त्रुटि" : "Error loading form", language },
      ]);
    }
    setPreviewLoading(false);
  }

  // ── Update a single form field value ──
  function handleFormFieldChange(fieldKey, value) {
    setFormFiller((prev) => ({
      ...prev,
      fields: {
        ...prev.fields,
        [fieldKey]: { ...prev.fields[fieldKey], value },
      },
    }));
  }

  // ── Submit the filled form and get PDF ──
  async function handleSubmitForm() {
    if (!formFiller || !sessionId) return;
    setFormSubmitting(true);
    try {
      // Collect all field values
      const filledData = {};
      for (const [key, info] of Object.entries(formFiller.fields)) {
        if (info.value.trim()) filledData[key] = info.value.trim();
      }
      const data = await submitFilledForm(sessionId, formFiller.schemeId, filledData);
      if (data.filename) {
        setGeneratedPdf(data.filename);
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: language === "hi"
            ? "✅ आपका आवेदन पत्र तैयार है! नीचे डाउनलोड करें।"
            : "✅ Your application form is ready! Download it below.",
          language,
        },
      ]);
      setCurrentStep("form_generation");
      setFormFiller(null);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: language === "hi" ? "फॉर्म जमा करने में त्रुटि" : "Error submitting form", language },
      ]);
    }
    setFormSubmitting(false);
  }

  // ── Apply for scheme (generate auto-filled PDF) ──
  async function handleApply(schemeId) {
    if (!sessionId) return;
    setLoading(true);
    try {
      const data = await generateForm(sessionId, schemeId);
      if (data.application?.pdf_path) {
        const filename = data.application.pdf_path.split(/[/\\]/).pop();
        setGeneratedPdf(filename);
      }
      if (data.message) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.message, language },
        ]);
      }
      setCurrentStep("form_generation");
      setFormPreview(null);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: language === "hi" ? "फॉर्म बनाने में त्रुटि" : "Error generating form",
          language,
        },
      ]);
    }
    setLoading(false);
  }

  function toggleLanguage() {
    setLanguage((l) => (l === "hi" ? "en" : "hi"));
  }

  function getStepClass(stepKey) {
    const stepOrder = STEPS.map((s) => s.key);
    const currentIdx = stepOrder.indexOf(currentStep);
    const thisIdx = stepOrder.indexOf(stepKey);
    if (stepKey === currentStep) return "step active";
    if (thisIdx < currentIdx) return "step done";
    return "step";
  }

  const hasDocuments = profile.documents?.length > 0;
  const filledFields = Object.entries(profile)
    .filter(([k, v]) => v && k !== "documents")
    .length;

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <span className="header-logo">🌉</span>
          <div>
            <h1>Setu AI</h1>
            <span className="header-subtitle">सेतु AI — सरकारी योजना सहायक</span>
          </div>
        </div>
        <div className="header-actions">
          <span className={`online-badge ${isOnline ? "online" : "offline"}`}>
            {isOnline ? "●" : "○"} {isOnline ? (language === "hi" ? "ऑनलाइन" : "Online") : (language === "hi" ? "ऑफ़लाइन" : "Offline")}
          </span>
          <button className="lang-btn" onClick={toggleLanguage}>
            {language === "hi" ? "EN" : "हि"}
          </button>
          <button
            className={`tts-btn ${ttsEnabled ? "on" : "off"}`}
            onClick={() => { setTtsEnabled(!ttsEnabled); stopSpeaking(); }}
            title={ttsEnabled ? "Mute TTS" : "Enable TTS"}
          >
            {ttsEnabled ? "🔊" : "🔇"}
          </button>
        </div>
      </header>

      {/* ── Step Progress ── */}
      <div className="step-bar">
        {STEPS.map((s, i) => (
          <div key={s.key} className={getStepClass(s.key)}>
            <span className="step-icon">{s.icon}</span>
            <span className="step-label">{language === "hi" ? s.label : s.labelEn}</span>
          </div>
        ))}
      </div>

      {/* ── Main Content ── */}
      <div className="main">
        {/* ── Voice-First Hero (shown when no deep conversation yet) ── */}
        {!showChat && messages.length <= 1 && (
          <div className="hero">
            <div className="hero-greeting">
              <h2>{language === "hi" ? "नमस्ते! 🙏" : "Namaste! 🙏"}</h2>
              <p className="hero-text">
                {language === "hi"
                  ? "मैं सेतु AI हूँ — आपका सरकारी योजना सहायक। बोलकर या दस्तावेज़ दिखाकर शुरू करें।"
                  : "I am Setu AI — your government scheme assistant. Start by speaking or showing a document."}
              </p>
            </div>

            {/* Big Mic Button */}
            <button
              className={`mic-hero ${isListening ? "listening" : ""}`}
              onClick={isListening ? stopListening : startListening}
              disabled={loading}
            >
              <span className="mic-icon">{isListening ? "⏹" : "🎤"}</span>
              {isListening && <span className="mic-pulse"></span>}
            </button>
            <p className="mic-hint">
              {isListening
                ? (language === "hi" ? "सुन रहा हूँ..." : "Listening...")
                : (language === "hi" ? "बोलने के लिए दबाएं" : "Tap to speak")}
            </p>
            {transcript && (
              <div className="transcript-preview">"{transcript}"</div>
            )}

            {/* Action Buttons */}
            <div className="hero-actions">
              <button className="action-btn camera" onClick={() => cameraInputRef.current?.click()}>
                <span className="action-icon">📷</span>
                <span>{language === "hi" ? "दस्तावेज़ स्कैन करें" : "Scan Document"}</span>
              </button>
              <button className="action-btn upload" onClick={() => fileInputRef.current?.click()}>
                <span className="action-icon">📁</span>
                <span>{language === "hi" ? "फ़ाइल अपलोड करें" : "Upload File"}</span>
              </button>
              <button className="action-btn chat" onClick={() => setShowChat(true)}>
                <span className="action-icon">💬</span>
                <span>{language === "hi" ? "टाइप करें" : "Type Message"}</span>
              </button>
            </div>

            {/* Hidden file inputs */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFileUpload}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/bmp"
              className="hidden"
              onChange={handleFileUpload}
            />
          </div>
        )}

        {/* ── Conversation View ── */}
        {(showChat || messages.length > 1) && (
          <div className="chat-view">
            {/* Message List */}
            <div className="chat-messages">
              {messages.map((msg, i) => (
                <div key={i} className={`msg ${msg.role}`}>
                  {msg.role === "assistant" && <span className="msg-avatar">🌉</span>}
                  <div className="msg-bubble">
                    <p>{msg.content}</p>
                    {msg.role === "assistant" && (
                      <button className="replay-btn" onClick={() => speak(msg.content)} title="Replay">
                        🔊
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {/* Eligible Schemes Cards */}
              {eligibleSchemes.length > 0 && !formFiller && (
                <div className="schemes-section">
                  <h3>{language === "hi" ? "🏛️ उपलब्ध योजनाएं" : "🏛️ Available Schemes"}</h3>
                  {eligibleSchemes.map((r) => (
                    <div key={r.scheme.id} className="scheme-card">
                      <div className="scheme-header">
                        <h4>{language === "hi" && r.scheme.name_hi ? r.scheme.name_hi : r.scheme.name}</h4>
                        <span className={`match ${r.match_score >= 0.7 ? "high" : "med"}`}>
                          {Math.round(r.match_score * 100)}%
                        </span>
                      </div>
                      <p className="scheme-desc">
                        {language === "hi" && r.scheme.description_hi ? r.scheme.description_hi : r.scheme.description}
                      </p>
                      <button
                        className="apply-btn"
                        onClick={() => handlePreviewForm(r.scheme.id)}
                        disabled={previewLoading}
                      >
                        {previewLoading ? "..." : (language === "hi" ? "📝 फॉर्म भरें" : "📝 Fill Application Form")}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* ── Interactive Form Filler ── */}
              {formFiller && (
                <div className="form-filler">
                  <div className="form-filler-header">
                    <button className="form-back-btn" onClick={() => setFormFiller(null)}>← {language === "hi" ? "वापस" : "Back"}</button>
                    <h3>{language === "hi" && formFiller.schemeNameHi ? formFiller.schemeNameHi : formFiller.schemeName}</h3>
                    <p className="form-subtitle">{language === "hi" ? "आवेदन पत्र भरें" : "Fill Application Form"}</p>
                  </div>

                  {/* Progress */}
                  {(() => {
                    const total = Object.keys(formFiller.fields).length;
                    const filled = Object.values(formFiller.fields).filter(f => f.value.trim()).length;
                    const pct = total ? Math.round((filled / total) * 100) : 0;
                    return (
                      <div className="form-progress">
                        <div className="form-progress-text">
                          <span>{filled}/{total} {language === "hi" ? "भरे गए" : "filled"}</span>
                          <span className="form-pct">{pct}%</span>
                        </div>
                        <div className="form-progress-bar">
                          <div className="form-progress-fill" style={{width: `${pct}%`}}></div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Form Fields */}
                  <div className="form-fields">
                    {Object.entries(formFiller.fields).map(([key, info]) => (
                      <div key={key} className={`form-field ${info.value.trim() ? "has-value" : "empty"}`}>
                        <label className="form-label">
                          {language === "hi" ? info.label_hi : info.label}
                          {info.value.trim() && <span className="auto-badge">✅</span>}
                        </label>
                        <input
                          type={key === "date_of_birth" ? "text" : key === "income" || key === "loan_amount" || key === "deposit_amount" ? "text" : key === "mobile_number" ? "tel" : key === "email" ? "email" : "text"}
                          className="form-input"
                          value={info.value}
                          onChange={(e) => handleFormFieldChange(key, e.target.value)}
                          placeholder={language === "hi" ? `${info.label_hi} दर्ज करें` : `Enter ${info.label}`}
                        />
                      </div>
                    ))}
                  </div>

                  {/* Submit */}
                  <div className="form-actions">
                    <button
                      className="form-submit-btn"
                      onClick={handleSubmitForm}
                      disabled={formSubmitting}
                    >
                      {formSubmitting
                        ? (language === "hi" ? "⏳ फॉर्म बना रहे हैं..." : "⏳ Generating...")
                        : (language === "hi" ? "📥 फॉर्म डाउनलोड करें" : "📥 Download Filled Form")}
                    </button>
                    <button className="form-cancel-btn" onClick={() => setFormFiller(null)}>
                      {language === "hi" ? "रद्द करें" : "Cancel"}
                    </button>
                  </div>
                </div>
              )}

              {/* PDF Download */}
              {generatedPdf && (
                <div className="msg assistant">
                  <span className="msg-avatar">🌉</span>
                  <div className="msg-bubble">
                    <a className="download-btn" href={getFormDownloadUrl(generatedPdf)} target="_blank" rel="noopener noreferrer">
                      📥 {language === "hi" ? "आवेदन पत्र डाउनलोड करें" : "Download Application Form"}
                    </a>
                  </div>
                </div>
              )}

              {loading && (
                <div className="loading">
                  <div className="dot"></div><div className="dot"></div><div className="dot"></div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Voice + Input Bar */}
            <div className="input-bar">
              <button
                className={`mic-btn ${isListening ? "listening" : ""}`}
                onClick={isListening ? stopListening : startListening}
                disabled={loading}
              >
                {isListening ? "⏹" : "🎤"}
              </button>
              {isListening && transcript && (
                <div className="live-transcript">{transcript}</div>
              )}
              {!isListening && (
                <>
                  <input
                    className="text-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSendInput()}
                    placeholder={language === "hi" ? "टाइप करें..." : "Type here..."}
                    disabled={loading}
                  />
                  <button className="send-btn" onClick={handleSendInput} disabled={!input.trim() || loading}>
                    ➤
                  </button>
                </>
              )}
              <button className="cam-btn" onClick={() => cameraInputRef.current?.click()} disabled={loading}>
                📷
              </button>
              <button className="file-btn" onClick={() => fileInputRef.current?.click()} disabled={loading}>
                📎
              </button>
            </div>

            {/* Hidden file inputs for chat view */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFileUpload}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/bmp"
              className="hidden"
              onChange={handleFileUpload}
            />
          </div>
        )}

        {/* Profile Summary (toggleable) */}
        {hasDocuments && (
          <button className="profile-toggle" onClick={() => setShowProfile(!showProfile)}>
            👤 {language === "hi" ? `प्रोफ़ाइल (${filledFields} जानकारी)` : `Profile (${filledFields} fields)`}
          </button>
        )}
        {showProfile && (
          <div className="profile-panel">
            <h3>{language === "hi" ? "👤 आपकी जानकारी" : "👤 Your Info"}</h3>
            <div className="profile-grid">
              {[
                ["name", "नाम", "Name"],
                ["date_of_birth", "जन्म तिथि", "DOB"],
                ["gender", "लिंग", "Gender"],
                ["id_number", "आईडी", "ID"],
                ["category", "श्रेणी", "Category"],
                ["income", "आय", "Income"],
                ["state", "राज्य", "State"],
              ].map(([key, hi, en]) => (
                profile[key] ? (
                  <div key={key} className="profile-item">
                    <span className="profile-key">{language === "hi" ? hi : en}</span>
                    <span className="profile-val">{profile[key]}</span>
                  </div>
                ) : null
              ))}
            </div>
            {profile.documents?.length > 0 && (
              <div className="doc-badges">
                {profile.documents.map((d, i) => (
                  <span key={i} className="doc-badge">✅ {d.document_type || `Doc ${i + 1}`}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
