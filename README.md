# CrimeVision AI — Intelligent Multimodal Forensic Analysis Platform

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.14-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/ASGI-Uvicorn-2ca5e0.svg)](https://www.uvicorn.org/)
[![RT-DETR](https://img.shields.io/badge/RT--DETR-Object%20Detection-cyan.svg)](https://github.com/ultralytics/ultralytics)
[![Whisper](https://img.shields.io/badge/OpenAI%20Whisper-Speech%20Acoustics-purple.svg)](https://github.com/openai/whisper)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20Visualization-orange.svg)](https://threejs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**CrimeVision AI** is an advanced, production-grade multimodal forensic evidence analysis and decision-support web platform powered by **FastAPI** and **Uvicorn**. It ingests **image, video, and audio evidence**, extracts structured intelligence using state-of-the-art vision and speech models (**RT-DETR**, **CLIP**, **BLIP**, **OpenAI Whisper**), fuses findings into a **Unified Chronological Timeline**, provides an **AI Evidence Chat** interface with forensic RAG retrieval, renders an interactive **3D conceptual scene**, and generates **court-ready forensic PDF reports**.

---

## ⚖️ Forensic Decision-Support Disclaimer

> **IMPORTANT FORENSIC BOUNDARY NOTICE**  
> CrimeVision AI is an **investigator decision-support and analytical tool**, NOT an autonomous system that determines guilt or innocence. It does not infer personal identities without verified biometric models, nor does it deduce criminal intent solely from visual appearance or spatial proximity. Detected entities represent statistical probabilities and must be independently corroborated by qualified forensic examiners and legal authorities.

---

## 🌟 Key Features

- **High-Performance FastAPI Architecture**:
  - Fully asynchronous REST API powered by **FastAPI** & **Uvicorn**.
  - Interactive OpenAPI documentation automatically generated at `/docs` (Swagger UI) and `/redoc` (ReDoc).
  - Pure SQLAlchemy 2.0 ORM with thread-safe `SessionLocal` and dependency injection (`Depends(get_db)`).
  - Pydantic v2 validation for all API inputs and structured outputs.

- **Multimodal Analysis Hub (3-Column Investigator Layout)**:
  - **Left Column — Image Intelligence**:
    - **RT-DETR (Real-Time DEtection TRansformer)**: Detects persons, vehicles, bags, and physical entities. Draws high-visibility forensic bounding boxes, confidence tags, and chain-of-custody watermarks.
    - **OpenAI CLIP (ViT-B/32)**: Visual-semantic scene classification (street, warehouse, office, vehicle area, outdoor, commercial) with normalized confidence scores.
    - **Salesforce BLIP**: Neutral, clinical image captioning and scene description.
    - **Scenario Analysis & Multilingual Translations**: Extracted forensic facts, investigator action checklists, and multilingual translation toggles (Hindi, Telugu, French, English).
  - **Center Column — Audio Acoustics**:
    - **OpenAI Whisper**: Multilingual audio transcription with timestamped speech segments and language identification.
    - Interactive audio playback, acoustic waveform visualizer, and chronological speech transcript cards.
    - Pure-Python WAV reader fallback ensuring transcription operates seamlessly even on systems without system-wide `ffmpeg`.
  - **Right Column — Video Analysis & 3D Spatial Scene**:
    - Intelligent keyframe sampling rate (e.g. 1 FPS) and inter-frame differencing for visual transition/motion detection.
    - Temporal event generation (`person_detected`, `vehicle_detected`, `multiple_people`, `scene_change`).
    - **Interactive Three.js 3D Conceptual Scene**: Spatial rendering of crime scene entity nodes (Persons, Vehicles, Objects, Evidence Beacons) with OrbitControls and real-time inspector telemetry.

- **Comprehensive Platform Features**:
  - **Main Dashboard**: Real-time analytical statistics, status distributions, and visual charts powered by **Chart.js**.
  - **Case Management**: Full case lifecycle tracking (`Open`, `Under Analysis`, `Review`, `Closed`) with evidence isolation.
  - **Evidence Ingestion & Chain of Custody**: Cryptographic streaming SHA-256 integrity verification, secure filename isolation, and metadata cataloging.
  - **Evidence Fusion Engine**: Chronological alignment of frame events, speech events, and visual observations with cross-modal correlation.
  - **AI Evidence Chat (Forensic RAG)**: Powered by **Groq LLM** (`llama-3.3-70b-versatile` or configured model) with strict evidence-grounded retrieval. Graceful analytical rule-based fallback when Groq API key is unconfigured.
  - **Automated Forensic PDF Reports**: Professional ReportLab generator compiling cryptographic evidence inventory, SHA-256 hashes, vision findings, audio transcripts, and unified timeline.
  - **One-Click Demo Mode**: Instant seeding of `CV-DEMO-001 Multimodal Crime Scene & Witness Reconstruction` with sample imagery, CCTV footage, and acoustic witness audio.

---

## 🏛️ System Architecture

```text
IMAGE ─────────► RT-DETR + CLIP + BLIP ───────────┐
                                                  │
VIDEO ─────────► Keyframe Sampling + RT-DETR ─────┼──► EvidenceFusionEngine ──► Unified Timeline
                                                  │                                │
AUDIO ─────────► OpenAI Whisper (Multilingual) ───┘                                │
                                                                                   ▼
                                                                     Forensic RAG + Groq LLM
                                                                                   │
                                                      ┌────────────────────────────┴───────────────────────────┐
                                                      ▼                                                        ▼
                                             AI Evidence Chat                                         Forensic PDF Report
                                             (Interactive Q&A)                                        (Signed Document)
```

---

## 📂 Project Structure

```text
crimevision-ai/
├── app.py                     # FastAPI application factory, lifespan hooks & entry point
├── config.py                  # Central configuration, storage paths & model params
├── requirements.txt           # Python dependency specifications
├── .env.example               # Example environment variables
├── README.md                  # Comprehensive platform documentation
│
├── backend/
│   ├── models/
│   │   ├── database.py        # SQLAlchemy engine, SessionLocal & get_db dependency
│   │   ├── case.py            # Case data model & relationship mappings
│   │   ├── evidence.py        # Evidence, Detection, Transcript models
│   │   └── timeline.py        # TimelineEvent, ChatMessage, Report models
│   │
│   ├── routes/
│   │   ├── cases.py           # Case management CRUD REST endpoints (APIRouter)
│   │   ├── evidence.py        # Evidence ingestion, async upload & file streaming
│   │   ├── analysis.py        # AI analysis execution & timeline fusion
│   │   ├── chat.py            # Forensic investigator AI chat endpoints
│   │   ├── reports.py         # Forensic PDF generation & download
│   │   └── system.py          # Diagnostics, system health & demo seeding
│   │
│   ├── services/
│   │   ├── object_detection.py # RT-DETR adapter & fallback CV detector
│   │   ├── clip_service.py     # CLIP visual-semantic scene classifier
│   │   ├── blip_service.py     # BLIP neutral image captioning
│   │   ├── image_analysis.py   # Image CV pipeline coordinator
│   │   ├── video_analysis.py   # Video frame sampler & event detector
│   │   ├── whisper_service.py  # Whisper multilingual speech transcription
│   │   ├── audio_analysis.py   # Audio analysis & speech event extractor
│   │   ├── evidence_fusion.py  # Multimodal chronological fusion engine
│   │   ├── llm_service.py      # Groq LLM integration & forensic RAG
│   │   ├── report_service.py   # ReportLab forensic PDF report generator
│   │   └── demo_service.py     # CV-DEMO-001 dataset generator & seeder
│   │
│   └── utils/
│       ├── file_security.py   # Path traversal defense & safe naming
│       ├── hashing.py         # Streaming SHA-256 integrity calculator
│       └── validators.py      # Pydantic schemas & standardized JSON responses
│
├── frontend/
│   ├── templates/
│   │   └── index.html         # Multimodal forensic intelligence dashboard UI
│   └── static/
│       ├── css/
│       │   └── style.css      # Cyber-forensic dark theme stylesheet
│       └── js/
│           ├── main.js        # REST client, 3-column controller & Chart.js
│           └── scene3d.js     # Three.js 3D conceptual scene renderer
│
├── storage/
│   ├── originals/             # Immutable uploaded evidence
│   ├── processed/             # Annotated images & keyframe snapshots
│   ├── reports/               # Generated forensic PDF documents
│   └── demo/                  # Generated demo media assets
│
└── tests/
    ├── test_hashing.py        # SHA-256 cryptographic integrity tests
    ├── test_fusion.py         # Chronological sorting & correlation tests
    ├── test_api.py            # FastAPI TestClient API tests
    └── verify_flow.py         # End-to-end acceptance verification script
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | Python 3.10–3.14, **FastAPI 0.115+**, **Uvicorn (ASGI)**, Pydantic v2, SQLAlchemy 2.0 |
| **Object Detection** | Ultralytics RT-DETR-l (`rtdetr-l.pt`), YOLOv8 fallback, OpenCV HOG |
| **Semantic & Captioning** | OpenAI CLIP (`openai/clip-vit-base-patch32`), Salesforce BLIP |
| **Speech & Acoustics** | OpenAI Whisper (multilingual base/tiny), pure-Python WAV reader |
| **LLM Reasoning** | Groq Cloud SDK (`llama-3.3-70b-versatile`), Custom Forensic RAG |
| **Document Generation** | ReportLab 4.4 (cryptographic integrity, table styles, flowables) |
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6+), Bootstrap 5, FontAwesome 6 |
| **Visualization** | Chart.js 4.4, Three.js (r128) + OrbitControls |
| **Database** | SQLite (default zero-config), PostgreSQL compatible architecture |

---

## 🚀 Quickstart Installation & Execution

### 1. Set Up Virtual Environment (Recommended)

**Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create or edit `.env`:

```env
PORT=5000
DATABASE_URL=sqlite:///crimevision.db

# Optional: Add Groq API key for LLM reasoning (https://console.groq.com)
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# AI Models & Sampling
RT_DETR_MODEL_PATH=rtdetr-l.pt
WHISPER_MODEL_NAME=base
ENABLE_DEMO_MODE=true
```

*(Note: If `GROQ_API_KEY` is not provided, CrimeVision AI automatically uses its built-in rule-based forensic analytical reasoning engine so chat never crashes).*

### 4. Run the Application

You can start the server using either method:

**Method A (Direct Python Entry)**:
```bash
python app.py
```

**Method B (Direct Uvicorn Command)**:
```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

Open your browser to:
- **Web Application**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Interactive Swagger Docs**: [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:5000/redoc](http://127.0.0.1:5000/redoc)

---

## ⚠️ Troubleshooting Port Conflicts (`[Errno 10048]`)

If you encounter:
```text
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 5000):
[winerror 10048] only one usage of each socket address is normally permitted
```
This means an instance of python or another process is already listening on port 5000.

**Fix on Windows (PowerShell)**:
```powershell
# 1. Identify the process ID holding port 5000
Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object OwningProcess

# 2. Stop the process (replace <PID> with the ID from step 1)
Stop-Process -Id <PID> -Force

# 3. Alternatively, run CrimeVision AI on another port
$env:PORT="5001"; python app.py
```

---

## 🧪 Verification & Automated Testing

The platform includes full pytest coverage and live end-to-end verification:

### Unit & API Test Suite:
```bash
python -m pytest tests/test_api.py -v
```

### End-to-End Acceptance Verification:
With the server running on port 5000, execute:
```bash
python tests/verify_flow.py
```

Sample output:
```text
============================================================
CRIMEVISION AI - END-TO-END ACCEPTANCE TEST SUITE
============================================================
[OK] System Status: Platform: CrimeVision AI v2.4 | Device: NVIDIA GeForce RTX GPU / CPU
[OK] Dashboard Stats: Ingested Evidence Verified
[OK] Demo Case Ingested: Case #CV-DEMO-001 (Office Incident & Jewelry Robbery Reconstruction)
[OK] Case Evidence Count: 3 items (Video, Audio, Image)
[OK] Unified Timeline: 6 events synthesized
[OK] Chat Query: AI Response with cited references [EV-1], [TL-1], [TR-1]
[OK] Forensic PDF Report Generated: Document SHA-256 verified
[OK] Web Frontend UI successfully rendered at http://127.0.0.1:5000/
============================================================
ALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!
============================================================
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web frontend dashboard UI |
| `GET` | `/docs` | Interactive Swagger OpenAPI documentation |
| `GET` | `/redoc` | Interactive ReDoc API documentation |
| `GET` | `/api/system/status` | Runtime hardware, AI model status, and weapon disclosures |
| `GET` | `/api/dashboard/stats` | Aggregated metrics for cases, evidence, and detections |
| `POST` | `/api/demo/seed` | Seed `CV-DEMO-001` multimodal incident demo case |
| `GET` | `/api/cases` | List all investigation cases |
| `POST` | `/api/cases` | Create a new investigation case |
| `GET` | `/api/cases/{id}` | Get case details and evidence modality breakdown |
| `PUT` | `/api/cases/{id}` | Update case title, investigator, or status |
| `DELETE` | `/api/cases/{id}` | Delete case and all associated evidence files |
| `GET` | `/api/cases/{id}/evidence` | List all evidence items for a case |
| `POST` | `/api/cases/{id}/evidence` | Upload new evidence file (`multipart/form-data`) |
| `GET` | `/api/evidence/{id}` | Get evidence detail including detections and transcripts |
| `POST` | `/api/evidence/{id}/analyze` | Execute AI analysis pipeline on single evidence file |
| `POST` | `/api/cases/{id}/analyze-all` | Batch-analyze all pending evidence in a case |
| `GET` | `/api/cases/{id}/timeline` | Retrieve fused chronological timeline |
| `POST` | `/api/cases/{id}/chat` | Post forensic question to AI evidence assistant |
| `GET` | `/api/cases/{id}/chat/history` | Retrieve chat message history for case |
| `POST` | `/api/cases/{id}/report` | Generate forensic PDF report |
| `GET` | `/api/reports/{id}/download` | Download or preview generated PDF report |
| `GET` | `/storage/originals/{filename}`| Serve original evidence file securely |
| `GET` | `/storage/processed/{filename}`| Serve processed derivative (annotated keyframes) |

---

## 🔒 Security & Forensic Chain of Custody

1. **Immutable Storage**: Original evidence files are stored with random UUID identifiers in `storage/originals/` and are never modified after ingestion.
2. **Cryptographic Hashing**: Streaming SHA-256 hashes are calculated on upload with 64KB chunking to prevent memory exhaustion on large video files.
3. **Path Traversal Protection**: Uploaded filenames are sanitized and validated against safe directory roots.
4. **Isolated Cases**: RAG chat context and evidence retrievals are strictly partitioned by `case_id`.

---

## 📄 License

This software is released under the **MIT License**.
CrimeVision AI is designed for forensic research, education, and investigation decision-support.
