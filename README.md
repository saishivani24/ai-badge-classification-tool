# NJIT AI-Assisted Digital Badge Classification Tool

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![React](https://img.shields.io/badge/React-18%2B-61DAFB)
![Tests](https://img.shields.io/badge/Tests-308%20Passing-brightgreen)
![Accuracy](https://img.shields.io/badge/Accuracy-100%25%2020%2F20-brightgreen)
![License](https://img.shields.io/badge/License-NJIT%20Capstone%202026-CC0033)

> A rule-based, explainable, and auditable web prototype that operationalizes NJIT's digital badge taxonomy into a structured, human-in-the-loop classification workflow.

**Capstone Project:** Spring 2026

**Institution:** New Jersey Institute of Technology

**Faculty Advisor:** Prabhat Vaish

**Supervisor:** Kerry Eberhardt

**Team Members:**

1. Rajat Pednekar
2. Prabhath Vinay Vipparthi
3. Tanay Yadav
4. Sai Shivani Kushanapalli

---

**Navigation:**
[Overview](#overview) &nbsp;·&nbsp;
[Architecture](#architecture) &nbsp;·&nbsp;
[Tech Stack](#tech-stack) &nbsp;·&nbsp;
[Repository Structure](#repository-structure) &nbsp;·&nbsp;
[Setup](#setup-and-installation) &nbsp;·&nbsp;
[Running the System](#running-the-system) &nbsp;·&nbsp;
[How to Use](#how-to-use) &nbsp;·&nbsp;
[API Reference](#api-reference) &nbsp;·&nbsp;
[Classification Taxonomy](#classification-taxonomy) &nbsp;·&nbsp;
[Testing](#testing) &nbsp;·&nbsp;
[Known Limitations](#known-limitations) &nbsp;·&nbsp;
[Team](#team)

---

## Overview

### The Problem

NJIT issues digital badges across five institutional units — the Learning and Development Initiative (LDI), the Office of Student Involvement and Leadership (OSIL), the Makerspace, the Newark College of Engineering (NCE), and the Office of Global Initiatives (OGI). Each badge must be formally classified against a three-stage hierarchical taxonomy: **Category**, **Type**, and **Level**, before it is published. Prior to this system, classification was done manually — slowly, inconsistently, and without a structured audit trail.

### The Solution

This prototype automates classification while keeping humans in control of every final decision. It accepts badge metadata in three formats (OBv3 JSON, guided proposal form, or free text), normalizes it into a **Badge Fact Sheet**, extracts classification signals using a four-layer NLP pipeline, applies NJIT's locked institutional taxonomy through a deterministic rule engine, and returns a fully explainable, auditable result that a human reviewer can accept or override.

### Core Principles

| Principle | Implementation |
|---|---|
| **Deterministic** | Rule engine uses explicit `if/elif` chains — no ML model ever makes a classification decision |
| **Explainable** | Every classification produces a structured plain-English explanation citing rule IDs and signal sources |
| **Auditable** | A full governance log entry is created for every classification and stored permanently |
| **Human-in-the-loop** | Reviewers accept or override with a mandatory reason; final decision always belongs to a human |
| **Non-blocking** | Missing signals trigger follow-up questions — they never prevent classification from completing |

---

## Architecture

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                             │
│         OBv3 JSON  ·  Proposal Form  ·  Free Text               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST /ingest                                  │
│                                                                  │
│  Ingestion     → parser.py / form_mapper.py                     │
│  Normalization → normalizer.py · issuer_resolver.py             │
│  Validation    → EC01–EC03 · EC24 (whitespace, duplicates,      │
│                  short content, implied series detection)        │
│                                                                  │
│  OUTPUT: Badge Fact Sheet (60+ structured fields)               │
└────────────────────────────┬────────────────────────────────────┘
                             │  BadgeFactSheet
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST /classify                                │
│                                                                  │
│  NLP Pipeline  → Layer 1: Phrase matching (phrase_dictionary.py)│
│                  Layer 2: Regex patterns  (pattern_rules.py)    │
│                  Layer 3: spaCy Bloom     (bloom_extractor.py)  │
│                  Layer 4: LLM stub        (llm_extractor.py)    │
│                                                                  │
│  Rule Engine   → Stage 1: Category (S1R01–S1R08)               │
│                  Stage 2: Type     (S2R01–S2R11)                │
│                  Stage 3: Level    (4 type-specific branches)   │
│                                                                  │
│  Explainability → explainer.py (8-element plain-English output) │
│  Governance     → governance_logger.py (full audit entry)       │
│                                                                  │
│  OUTPUT: ClassificationResult with log_id                       │
└────────────────────────────┬────────────────────────────────────┘
                             │  log_id + recommendation
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POST /review                                  │
│                                                                  │
│  Reviewer accepts or overrides any of the three stages          │
│  Override reason enforced (≥20 chars · valid taxonomy pair)     │
│  Final decision locked in governance log                        │
└─────────────────────────────────────────────────────────────────┘
```

### Layer-by-Layer Breakdown

| Layer | Purpose | Key Files |
|---|---|---|
| **Ingestion** | Parse OBv3 JSON, map form fields, detect issuer via keyword matching | `parser.py`, `form_mapper.py` |
| **Normalization** | Convert any input to a standardized Badge Fact Sheet | `normalizer.py`, `issuer_resolver.py` |
| **NLP Pipeline** | Extract classification signals from badge text | `phrase_dictionary.py`, `pattern_rules.py`, `bloom_extractor.py`, `signal_extractor.py` |
| **Rule Engine** | Deterministic three-stage classification | `stage1.py`, `stage2.py`, `stage3.py`, `engine.py` |
| **Explainability** | Generate structured plain-English explanation | `explainer.py` |
| **Governance** | Permanent audit trail for every classification | `governance_logger.py` |

---

## Tech Stack

### Backend

| Technology | Purpose | Version |
|---|---|---|
| Python | Core language | 3.11+ |
| FastAPI | REST API framework | 0.100+ |
| SQLite | Embedded database | Built-in |
| SQLAlchemy | ORM and schema management | 2.0+ |
| spaCy | NLP — Bloom's Taxonomy verb extraction | 3.x (`en_core_web_sm`) |
| Pydantic | Data validation and serialization | 2.0+ |
| pytest | Test framework | 7.x+ |

### Frontend

| Technology | Purpose |
|---|---|
| React | UI framework |
| Vite | Build tool and dev server |
| Tailwind CSS | Utility-first styling |
| Axios | HTTP client for API calls |

---

## Repository Structure

```
ai-badge-classification-tool/
├── README.md                          # This file
├── CLAUDE.md                          # Project context for Claude Code
├── LICENSE.txt                        # Author license
├── .env.example                       # Environment variables template
│
├── backend/
│   ├── database.py                    # SQLite setup, session, auto-migration
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI entry point, CORS, router registration
│       ├── routes/
│       │   ├── ingestion.py           # POST /ingest
│       │   ├── classification.py      # POST /classify
│       │   ├── review.py              # POST /review
│       │   ├── logs.py                # GET /logs, GET /logs/{id}
│       │   └── reviewer.py            # POST /reviewer/auth, GET /reviewer/queue
│       ├── models/
│       │   ├── badge_fact_sheet.py    # Core Pydantic BFS model (60+ fields)
│       │   ├── classification_result.py
│       │   └── governance_log.py      # SQLAlchemy ORM model
│       ├── services/
│       │   ├── ingestion/
│       │   │   ├── parser.py          # OBv3 JSON parser
│       │   │   └── form_mapper.py     # Form fields + free-text → BadgeFactSheet
│       │   ├── normalization/
│       │   │   ├── normalizer.py      # Orchestrates full 7-step ingestion pipeline
│       │   │   └── issuer_resolver.py # Criteria URL → issuer (IR01–IR07)
│       │   ├── nlp/
│       │   │   ├── phrase_dictionary.py  # Layer 1 — exact phrase matching
│       │   │   ├── pattern_rules.py      # Layer 2 — regex patterns
│       │   │   ├── bloom_extractor.py    # Layer 3 — spaCy Bloom verb extraction
│       │   │   ├── llm_extractor.py      # Layer 4 — LLM stub (USE_LLM=false)
│       │   │   └── signal_extractor.py   # Orchestrates all 4 NLP layers
│       │   ├── classification/
│       │   │   ├── stage1.py          # Category rules S1R01–S1R08
│       │   │   ├── stage2.py          # Type rules S2R01–S2R11
│       │   │   ├── stage3.py          # Level rules — 4 type-specific branches
│       │   │   └── engine.py          # Orchestrates Stages 1 → 2 → 3
│       │   ├── explainability/
│       │   │   └── explainer.py       # 8-element plain-English explanation generator
│       │   └── logging/
│       │       └── governance_logger.py
│       └── utils/
│           ├── canvas_code_parser.py  # MCAI.002.03 → pathway + sequence number
│           └── obv_version_detector.py
│
├── backend/tests/                     # 308 automated tests — 16 test files
│   ├── test_accuracy_matrix.py        # 20 real badges — 100% accuracy
│   ├── test_e2e_scenarios.py          # 7 end-to-end scenarios (all 3 input types)
│   ├── test_nlp_extraction_rate.py    # NLP signal extraction rate measurement
│   ├── test_real_badges.py            # Real NJIT badge fixture tests
│   ├── test_synthetic_badges.py       # Happy-path + edge cases
│   ├── test_classification.py         # Rule engine unit tests
│   ├── test_edge_cases.py             # EC01–EC30 edge case coverage
│   ├── test_explainability.py         # Explanation content and completeness
│   ├── test_logging.py                # Governance log creation and review
│   ├── test_api_integration.py        # Full round-trip API tests
│   └── test_verification_checklist.py # T01–T08 scenario regression tests
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── SubmitBadge.jsx            # Three-tab submission (Form / JSON / Free Text)
│       │   ├── ReviewResult.jsx           # Classification result display
│       │   ├── GovernanceLogs.jsx         # Audit trail table with search
│       │   ├── SubmissionConfirmation.jsx # Post-submit confirmation
│       │   └── reviewer/
│       │       ├── ReviewerLogin.jsx
│       │       ├── ReviewerDashboard.jsx
│       │       └── ReviewerReview.jsx
│       ├── components/
│       │   ├── BadgeForm.jsx          # Multi-step guided form
│       │   ├── ClassificationResult.jsx
│       │   ├── ExplanationPanel.jsx
│       │   ├── SignalPanel.jsx
│       │   ├── OverrideForm.jsx
│       │   ├── JsonPaste.jsx
│       │   ├── FreeTextInput.jsx
│       │   └── ProtectedRoute.jsx
│       ├── context/ReviewerContext.jsx
│       ├── services/api.js            # Centralized Axios API client
│       └── utils/formTranslator.js    # Plain-language form → BFS field mapping
│
├── sample_data/
│   ├── real_badges/                   # 20 real NJIT badge JSON payloads (B001–B026)
│   └── test_manifest.json             # Expected classification results for all 20 badges
│
├── scripts/
│   ├── load_sample_data.py            # Populates demo database from sample_data/
│   ├── reset_database.py              # Clears badges.db for a fresh start
│   └── validate_taxonomy.py           # Standalone taxonomy rule validator
│
└── docs/
    ├── architecture.md
    ├── taxonomy-rules.md
    ├── badge-fact-sheet-schema.md
    ├── decision-tables.md
    ├── nlp-phrase-dictionary.md
    ├── governance-logging.md
    ├── testing-plan.md
    └── demo-script.md
```

---

## Setup and Installation

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Git

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Rajat-Projects/ai-badge-classification-tool
cd ai-badge-classification-tool/ai-badge-classification-tool
```

### Step 2 — Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### Step 3 — Environment Variables

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
REVIEWER_PASSWORD=xxxx-xxxxxxxx-xxxx
USE_LLM=false
DATABASE_URL=sqlite:///./badges.db
ALLOWED_ORIGINS=http://localhost:5173
APP_VERSION=1.0.0
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./badges.db` | SQLAlchemy connection string |
| `USE_LLM` | `false` | Enable LLM gap-filling (requires Anthropic API key) |
| `ANTHROPIC_API_KEY` | *(empty)* | Required only if `USE_LLM=true` |
| `REVIEWER_PASSWORD` | `xxxx-xxxxxxxx-xxxx` | Reviewer dashboard access code |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowed origins |
| `APP_VERSION` | `1.0.0` | Reported by `/health` endpoint |

### Step 4 — Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Running the System

### Start the Backend

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`

> The SQLite database and all tables are created automatically on first startup.

### Start the Frontend

```bash
cd frontend
npm run dev
```

- Application: `http://localhost:5173`

### Verify System Health

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "1.0.0", "nlp": {"spacy_available": true}}
```

### Load Demo Data (Optional)

Pre-populate the database with all 20 real NJIT badge fixtures:

```bash
# Run from the project root with the backend server running
python scripts/load_sample_data.py
```

---

## How to Use

### Submitting a Badge — User A (Submitter)

Navigate to `http://localhost:5173` and choose one of three input methods:

#### 1. Proposal Form
A six-step guided form written in plain language. No taxonomy knowledge is required from the submitter. A translation layer (`formTranslator.js`) converts answers to structured Badge Fact Sheet fields automatically.

#### 2. OBv3 JSON Paste
Paste any valid Open Badges v3 JSON object. The issuer is auto-detected from the `criteria.id` URL domain. Follow-up questions appear for any signals that could not be resolved automatically.

#### 3. Free Text
Describe the badge in plain everyday language. The NLP pipeline extracts signals automatically across four layers. Plain-language follow-up questions prompt for any remaining missing fields. Designed for students evaluating badge equivalents from outside NJIT.

**After submission:**
1. Badge Fact Sheet is displayed with all extracted signals highlighted
2. Follow-up questions appear for any missing critical fields
3. Click **Submit for Review** → confirmation page with status shown
4. Reviewer sees badge appear in the pending queue

---

### Reviewing a Classification — User B (Reviewer)

1. Click **Reviewer Login** in the navigation bar
2. Enter the reviewer access code (`REVIEWER_PASSWORD` from `.env`)
3. View the **Pending Review** queue on the dashboard
4. Click **View →** to open any pending badge
5. Review the full classification:
   - All extracted signals with their source layer labeled
   - Three-stage classification result with confidence level
   - Complete plain-English explanation with rule IDs cited
6. Choose an action:
   - **Accept** — confirms the system recommendation
   - **Override** — changes any stage with a mandatory reason (≥ 20 characters)

---

### Viewing Governance Logs

All classifications are permanently stored and accessible to all users at `/logs`. Click any record to expand the full detail view:

- System-recommended result vs. final human decision
- Override reason and what changed
- Complete explanation text
- All signals used with source layer attribution

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Convert any input format to a Badge Fact Sheet |
| `POST` | `/classify` | Run the rule engine; creates a governance log entry |
| `POST` | `/review` | Accept or override a classification |
| `GET` | `/logs` | Paginated list of all governance log entries |
| `GET` | `/logs/{id}` | Full detail for a single governance log entry |
| `GET` | `/health` | System status and spaCy availability |
| `POST` | `/reviewer/auth` | Authenticate reviewer and receive access token |
| `GET` | `/reviewer/queue` | Pending queue, recent reviews, and stats |
| `GET` | `/reviewer/review/{token}` | Load a badge for review via email link token |

### POST /ingest

**Request body:**

```json
{
  "input_type": "form",
  "payload": {
    "badge_title": "AI Literacy and Fundamentals",
    "badge_description": "Recognizes NJIT faculty who completed the AI Literacy course.",
    "issuer": "LDI",
    "audience_type": "njit_employee",
    "earning_criteria_text": "Complete all modules and pass the final assessment.",
    "assessment_required": "yes",
    "assessment_type": "final_assessment",
    "assessment_evaluator": "auto_assessed",
    "expert_evaluation_required": false
  }
}
```

`input_type` accepts: `form` | `obv3_json` | `free_text`

**Response:** Complete Badge Fact Sheet (BadgeFactSheet model, 60+ fields)

---

### POST /classify

**Request body:** The `BadgeFactSheet` object returned by `POST /ingest`

**Response:**

```json
{
  "badge_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "badge_title": "AI Literacy and Fundamentals",
  "issuer": "LDI",
  "classification": {
    "category": "Faculty & Staff Development",
    "type": "Achievement",
    "level": "Foundational",
    "confidence": "High",
    "level_branch_used": "achievement"
  },
  "rules_triggered": ["S1R01", "S2R09", "S3A05"],
  "signals_used": {
    "issuer":           { "value": "LDI",              "source": "structured_field" },
    "audience_type":    { "value": "njit_employee",     "source": "structured_field" },
    "assessment_type":  { "value": "final_assessment",  "source": "structured_field" },
    "bloom_level":      { "value": "understanding",     "source": "spacy_verb" }
  },
  "explanation": "CATEGORY: Classified as 'Faculty & Staff Development'...",
  "follow_up_needed": false,
  "missing_signals": [],
  "governance": {
    "log_id": "7e0b1234-...",
    "classified_at": "2026-04-28T10:00:00Z",
    "reviewer_status": "pending"
  }
}
```

---

### POST /ingest — OBv3 JSON Example

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "obv3_json",
    "payload": {
      "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
      "name": "Introduction to AI in Education",
      "criteria": {
        "id": "https://njitcl.catalog.instructure.com/courses/ai-microcredentials",
        "narrative": "Complete all modules within the self-paced course."
      },
      "description": "Recognizes completion of Introduction to AI in Education.",
      "achievementType": "Achievement"
    }
  }'
```

---

### POST /review — Override Example

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "7e0b1234-...",
    "reviewer_id": "k.eberhardt",
    "reviewer_status": "overridden",
    "override_reason": "Badge includes a reflection component requiring expert evaluation.",
    "override_category": "Faculty & Staff Development",
    "override_type": "Skill",
    "override_level": "Application"
  }'
```

**Validation rules enforced:**
- `override_reason` must be ≥ 20 characters (EC29)
- `override_type` + `override_level` must be a valid taxonomy combination (EC30)
- If all override values match the recommendation, status silently resolves to `accepted` (EC26)

---

## Classification Taxonomy

### Stage 1 — Badge Category

Determined by **issuer identity** and **audience type**.

| Category | Issuer | Audience |
|---|---|---|
| Faculty & Staff Development | LDI | NJIT employees / faculty |
| Continuing & Professional Education | LDI | External professionals |
| Co-Curricular and Extra-Curricular | OSIL | NJIT students |
| Academic | Makerspace, NCE | NJIT students |

### Stage 2 — Badge Type

Determined by **earning criteria** and **assessment method**. Rules run in strict priority order — first match wins.

| Type | Key Signal | Assessment |
|---|---|---|
| **Souvenir** | Attendance only — no assessment required | None |
| **Achievement** | Auto-assessed or platform-tracked completion | Auto-assessed |
| **Skill** | Expert-scored demonstration of a specific skill | Expert-scored |
| **Competency** | Expert evaluation of KSAs in real-world context | Expert-scored |

### Stage 3 — Badge Level

Level names are **type-specific** and cannot be used across types.

| Type | Valid Levels (low → high) |
|---|---|
| Souvenir | Souvenir |
| Achievement | Foundational → Milestone → Terminal |
| Skill | Awareness → Application → Mastery |
| Competency | Demonstrated → Integrated → Exemplary |

**Level determination per type:**

| Type | Primary Signal | Secondary Signal | Fallback |
|---|---|---|---|
| Achievement | Canvas sequence number | Prerequisite badges / self-declared phrase | NLP Bloom level |
| Skill | Bloom's Taxonomy level from text | Expert-scored flag | Unknown |
| Competency | Leadership evidence | Multi-context evidence | Real-world context |

### Issuer Resolution Rules

When a badge is submitted via OBv3 JSON, the issuer is resolved from the `criteria.id` URL:

| Criteria URL Domain / Pattern | Resolved Issuer |
|---|---|
| `ldi.njit.edu` | LDI |
| `njitcl.catalog.instructure.com` | LDI |
| `njit.edu/development` | LDI |
| `njitmakerspace.com` | Makerspace |
| `engineering.njit.edu` | NCE |
| `njit.edu/global` | OGI |

For form and free text inputs, issuer is provided directly or detected via keyword matching in the badge description.

---

## Testing

### Running the Full Test Suite

```bash
cd backend
source ../venv/bin/activate
pytest tests/ -v
```

### Test Results

```
308 tests collected
308 passed, 0 failed
Pass rate: 100%
Runtime: ~3.2 seconds
```

### Coverage by Test File

| Test File | Scope | Tests |
|---|---|---|
| `test_accuracy_matrix.py` | 20 real NJIT badges — all 5 dimensions | 4 |
| `test_e2e_scenarios.py` | 7 end-to-end scenarios (all 3 input types) | 8 |
| `test_nlp_extraction_rate.py` | NLP signal extraction measurement | 6 |
| `test_real_badges.py` | Real badge fixtures classified correctly | ~20 |
| `test_synthetic_badges.py` | Happy-path taxonomy combinations + edge cases | ~26 |
| `test_classification.py` | Rule engine unit tests per stage | ~43 |
| `test_explainability.py` | Explanation content and completeness | ~30 |
| `test_logging.py` | Governance log creation, update, retrieval | ~8 |
| `test_api_integration.py` | Full round-trip API endpoint tests | ~32 |
| `test_edge_cases.py` | EC01–EC30 edge case coverage | ~20 |
| `test_verification_checklist.py` | T01–T08 regression scenarios | ~8 |
| `test_ingestion.py` | Parser, form mapper, free-text normalizer | ~20 |
| `test_api.py` | Route availability and response shape | ~20 |

### Classification Accuracy Matrix — 20 Real NJIT Badges

All 20 real NJIT badges tested across all five classification dimensions:

| Dimension | Score |
|---|---|
| Stage 1 — Category | 20 / 20 (100%) |
| Stage 2 — Type | 20 / 20 (100%) |
| Stage 3 — Level | 20 / 20 (100%) |
| Confidence Level | 20 / 20 (100%) |
| Rules Triggered | 20 / 20 (100%) |
| **Overall (all 5 passing)** | **20 / 20 (100%)** |

### Accuracy by Issuer

| Issuer | Badges Tested | Result |
|---|---|---|
| LDI | 7 | 7 / 7 — 100% |
| OSIL | 6 | 6 / 6 — 100% |
| Makerspace | 4 | 4 / 4 — 100% |
| NCE | 1 | 1 / 1 — 100% |
| OGI | 1 | 1 / 1 — 100% |

### NLP Signal Extraction Rates

Measured across 20 structured form badges (ingest-time) and 5 free-text inputs (post-classify):

| Signal | Structured Input | Free Text (post-classify) |
|---|---|---|
| Issuer | 100% | 100% |
| Audience Type | 100% | 80% |
| Assessment Type | 100% | 60% |
| Assessment Evaluator | 85% | 20% |
| Badge Purpose | 100% | 100% |
| Bloom Level | N/A (at classify time) | 100% |
| Level Signal | 35% (canvas) | 40% (NLP phrase) |

### End-to-End Scenario Coverage

| Scenario | Input Type | Expected Confidence | Result |
|---|---|---|---|
| FT01 — LDI Professional | Free Text | High Conf | PASS |
| FT02 — OSIL Capstone | Free Text | High Conf | PASS |
| FT03 — Vague Input | Free Text | Low Conf | PASS |
| FM01 — Form High Confidence | Form | High Conf | PASS |
| FM02 — Unknown Issuer | Form | Low Conf | PASS |
| OBV3-01 — JSON High Confidence | OBv3 JSON | High Conf | PASS |
| OBV3-02 — No Criteria URL | OBv3 JSON | Low Conf | PASS |

---

## Known Limitations

| Limitation | Status | Impact |
|---|---|---|
| OGI badge category not confirmed | Open — awaiting supervisor input | B026 Stage 1 returns `null`; confidence forced to Low |
| Makerspace Skill vs. Achievement boundary | Open — pending taxonomy clarification | B013–B015 type may need revision after decision |
| LLM extractor is a stub | `USE_LLM=false` by default | Free-text classification relies on rule-based NLP + follow-up questions |
| Free-text submissions always require follow-up | By design — natural language lacks structured fields | Handled gracefully by plain-language Q&A interface |
| OBv2 badges rejected | 422 response with clear error message | All current NJIT badges are OBv3 format |
| Canvas course codes not extracted from free text | Students do not know internal course codes | Level classification falls back to NLP phrase matching |

---

## Non-Negotiable System Rules

These rules govern every design decision and every line of code in this system:

1. **Taxonomy rules are locked** — No new policy logic invented; all rules derived from NJIT's official taxonomy documentation
2. **Classification is always deterministic** — Rule engine only; no ML model ever makes a classification decision
3. **NLP extracts signals, never decides** — The NLP pipeline populates Badge Fact Sheet fields; the rule engine reads them
4. **Every output is explainable** — Rules triggered, signals used, and plain-English reasoning always returned
5. **Every decision is auditable** — A governance log entry is created for every single classification
6. **Human override is always supported** — A reviewer can change any stage of any classification at any time
7. **Classify from Badge Fact Sheet only** — The rule engine never reads raw input directly
8. **No scope creep** — No badge issuance, no wallet, no admin rule management UI

---

## Team

| Name | Role | Contact |
|---|---|---|
| **Rajat Ravindra Pednekar** | System Architecture, NLP Pipeline Development, Schema Design| rp2348@njit.edu |
| **Sai Shivani K** | Taxonomy Documentation, Frontend Implementation | sk3764@njit.edu |
| **Prabhath Vinay Vipparthi** | Data Engineering, NLP Phrase Dictionary, Pattern Rules, Classification Engine, AI/NLP Pipeline, Testing & Validation | pv342@njit.edu |
| **Tanay** | Backend Design, Governance Design, Feedback Loop | ty233@njit.edu |

**Faculty Advisor:** Prabhat Vaish
**Supervisor:** Kerry Eberhardt
**Institution:** New Jersey Institute of Technology
**Semester:** Spring 2026

---

## License

```
Copyright (c) 2026 Rajat Ravindra Pednekar

Developed as a capstone project at
New Jersey Institute of Technology — Spring 2026

Permission is hereby granted to NJIT and its authorized representatives
to use, modify, and distribute this software for institutional badge
classification purposes.

This software may not be used for commercial purposes without explicit
written permission from the author.
```

---

*NJIT AI-Assisted Digital Badge Classification Tool — Capstone Spring 2026*

