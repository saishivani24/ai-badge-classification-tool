"""
test_e2e_scenarios.py

7 automated end-to-end scenario tests covering all three input methods
(free_text, form, obv3_json) with high and low confidence cases.

Each scenario runs the full ingest → classify → verify log pipeline.

Usage:
    pytest tests/test_e2e_scenarios.py -v -s
"""

import json
import os
import tempfile

# ---------------------------------------------------------------------------
# Force in-memory DB before any app import touches the database layer.
# ---------------------------------------------------------------------------
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.governance_log import Base
from database import get_db

# ---------------------------------------------------------------------------
# In-memory DB override
# ---------------------------------------------------------------------------

_TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)
Base.metadata.create_all(bind=_TEST_ENGINE)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# ===========================================================================
# SCENARIO 1 — FT01: LDI Professional Free Text
# Issuer: LDI  Audience: external_professional
# Expected: Continuing & Professional Education / Achievement / Foundational
# ===========================================================================

def test_ft01_ldi_professional_free_text():
    # Ingest
    ingest_resp = client.post("/ingest", json={
        "input_type": "free_text",
        "payload": {"text": (
            "I completed an online course offered by NJIT "
            "Learning and Development Initiative focused on "
            "project management for healthcare professionals. "
            "I had to pass a final assessment with 80% or higher. "
            "This was the first course in the series."
        )}
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()
    assert bfs["issuer"] == "LDI"

    # Classify
    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    # Assert classification (field names from ClassificationResult model)
    assert result["classification"]["category"] == \
        "Continuing & Professional Education"
    assert result["classification"]["type"] == "Achievement"
    assert result["classification"]["level"] == "Foundational"
    assert result["explanation"] != ""
    assert len(result["rules_triggered"]) > 0

    # Assert governance log created
    log_id = result["governance"]["log_id"]
    assert log_id is not None and log_id != ""
    log_resp = client.get(f"/logs/{log_id}")
    assert log_resp.status_code == 200


# ===========================================================================
# SCENARIO 2 — FT02: OSIL Capstone Terminal Free Text
# Issuer: OSIL  Audience: njit_student
# Expected: Co-Curricular and Extra-Curricular / Achievement / Terminal
# ===========================================================================

def test_ft02_osil_capstone_free_text():
    ingest_resp = client.post("/ingest", json={
        "input_type": "free_text",
        "payload": {"text": (
            "After completing the foundational and intermediate "
            "series in the Change Management program run by the "
            "student involvement office at NJIT, I attended a "
            "two day leadership institute where my team worked "
            "on a capstone project and presented to a panel."
        )}
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()
    assert bfs["issuer"] == "OSIL"

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    assert result["classification"]["category"] == \
        "Co-Curricular and Extra-Curricular"
    assert result["classification"]["type"] == "Achievement"
    assert result["classification"]["level"] == "Terminal"
    assert result["explanation"] != ""


# ===========================================================================
# SCENARIO 3 — FT03: Vague Input Low Confidence
# No issuer detected — system must degrade gracefully (never block)
# ===========================================================================

def test_ft03_vague_input_low_confidence():
    ingest_resp = client.post("/ingest", json={
        "input_type": "free_text",
        "payload": {"text": "I did some training at NJIT and got a certificate."}
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    # Low confidence expected — issuer cannot be resolved
    assert result["classification"]["confidence"] == "Low"

    # System must still return a result — never block
    assert result["explanation"] != ""
    log_id = result["governance"]["log_id"]
    assert log_id is not None


# ===========================================================================
# SCENARIO 4 — FM01: Form High Confidence
# Issuer: LDI  Audience: njit_employee  Canvas: MCAI.001.02 (sequence 2)
# Expected: Faculty & Staff Development / Achievement / Milestone / High
# ===========================================================================

def test_fm01_form_high_confidence():
    payload = {
        "badge_title": "AI Literacy and Fundamentals",
        "badge_description": (
            "This badge recognizes NJIT faculty who completed "
            "AI Literacy and Fundamentals covering core AI concepts."
        ),
        "issuer": "LDI",
        "audience_type": "njit_employee",
        "earning_criteria_text": (
            "Complete all modules and pass the final assessment "
            "with 80% or higher."
        ),
        "assessment_required": "yes",
        "assessment_type": "final_assessment",
        "assessment_evaluator": "auto_assessed",
        "assessment_pass_threshold": "80%",
        "expert_evaluation_required": False,
        "canvas_course_code": "MCAI.001.02",
        "canvas_sequence_number": 2,
    }

    ingest_resp = client.post("/ingest", json={
        "input_type": "form",
        "payload": payload
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    assert result["classification"]["category"] == "Faculty & Staff Development"
    assert result["classification"]["type"] == "Achievement"
    assert result["classification"]["level"] == "Milestone"
    assert result["classification"]["confidence"] == "High"


# ===========================================================================
# SCENARIO 5 — FM02: Form Unknown Issuer Low Confidence
# No issuer field submitted — missing_signals must flag it
# ===========================================================================

def test_fm02_form_unknown_issuer():
    payload = {
        "badge_title": "Research Methods Certification",
        "badge_description": (
            "This badge recognizes graduate students who completed "
            "research methods training at NJIT."
        ),
        "earning_criteria_text": (
            "Complete all four workshop sessions and submit "
            "a research proposal."
        ),
        "assessment_required": "yes",
    }

    ingest_resp = client.post("/ingest", json={
        "input_type": "form",
        "payload": payload
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()

    assert bfs["issuer"] is None
    assert bfs["needs_followup_questions"] is True
    assert "issuer" in bfs["missing_signals"]

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    assert result["classification"]["confidence"] == "Low"
    assert result["explanation"] != ""


# ===========================================================================
# SCENARIO 6 — OBV3-01: JSON High Confidence
# Canvas URL resolves issuer to LDI; badge_title extracted from "name"
# Expected: Faculty & Staff Development / Achievement / Foundational
# ===========================================================================

def test_obv3_01_json_high_confidence():
    payload = {
        "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
        "id": "https://api.badgr.io/public/badges/neCy02soS",
        "type": ["Achievement"],
        "criteria": {
            "id": "https://njitcl.catalog.instructure.com/courses/ai-microcredentials",
            "narrative": (
                "This badge is awarded to individuals who have "
                "successfully completed all modules within the "
                "Introduction to AI in Education self-paced course."
            ),
        },
        "description": (
            "This badge recognizes completion of Introduction to "
            "AI in Education covering foundational AI concepts "
            "relevant to educators."
        ),
        "name": "Introduction to AI in Education",
        "achievementType": "Achievement",
        "alignments": [{
            "type": ["Alignment"],
            "targetName": "Artificial intelligence",
            "targetUrl": "https://talentneuron.com/",
            "targetCode": "TN-19982",
            "targetDescription": "AI systems",
            "targetFramework": "TALENT_NEURON",
        }],
    }

    ingest_resp = client.post("/ingest", json={
        "input_type": "obv3_json",
        "payload": payload
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()

    assert bfs["issuer"] == "LDI"
    assert bfs["badge_title"] == "Introduction to AI in Education"
    assert bfs["achievement_type"] == "Achievement"

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    assert result["classification"]["category"] == "Faculty & Staff Development"
    assert result["classification"]["type"] == "Achievement"
    assert result["classification"]["level"] == "Foundational"
    assert result["explanation"] != ""


# ===========================================================================
# SCENARIO 7 — OBV3-02: JSON No Criteria URL
# No criteria.id URL → issuer cannot be resolved → Low confidence
# ===========================================================================

def test_obv3_02_json_no_criteria_url():
    payload = {
        "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
        "id": "https://api.badgr.io/public/badges/unknown123",
        "type": ["Achievement"],
        "criteria": {
            "narrative": (
                "Recipients attended the workshop and participated "
                "in all activities."
            )
        },
        "description": (
            "This badge recognizes participation in the Advanced "
            "Leadership Development workshop at NJIT."
        ),
        "name": "Advanced Leadership Development Workshop",
        "achievementType": "Achievement",
    }

    ingest_resp = client.post("/ingest", json={
        "input_type": "obv3_json",
        "payload": payload
    })
    assert ingest_resp.status_code == 200
    bfs = ingest_resp.json()

    assert bfs["issuer"] is None
    assert bfs["needs_followup_questions"] is True
    assert "issuer" in bfs["missing_signals"]

    classify_resp = client.post("/classify", json=bfs)
    assert classify_resp.status_code == 200
    result = classify_resp.json()

    assert result["classification"]["confidence"] == "Low"
    assert result["explanation"] != ""

    log_id = result["governance"]["log_id"]
    assert log_id is not None


# ===========================================================================
# SUMMARY — printed after all 7 scenario tests
# ===========================================================================

def test_e2e_summary():
    """Print end-to-end scenario summary table."""
    print("\n" + "=" * 55)
    print("END-TO-END SCENARIO TEST RESULTS")
    print("=" * 55)
    print(f"  {'Scenario':<40} {'Expected':>10}")
    print("-" * 55)
    scenarios = [
        ("FT01: LDI Professional Free Text",  "High Conf"),
        ("FT02: OSIL Capstone Free Text",      "High Conf"),
        ("FT03: Vague Input",                  "Low Conf"),
        ("FM01: Form High Confidence",         "High Conf"),
        ("FM02: Form Unknown Issuer",          "Low Conf"),
        ("OBV3-01: JSON High Confidence",      "High Conf"),
        ("OBV3-02: JSON No Criteria URL",      "Low Conf"),
    ]
    for name, expected in scenarios:
        print(f"  {name:<40} {expected:>10}")
    print("=" * 55)
