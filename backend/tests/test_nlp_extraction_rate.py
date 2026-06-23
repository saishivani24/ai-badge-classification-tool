"""
test_nlp_extraction_rate.py

READ-ONLY NLP signal extraction rate analysis.

Runs POST /ingest (only) for every badge in test_manifest.json and measures
which signals were successfully extracted.  Does NOT call POST /classify and
does NOT modify any source file, model, route, or existing test file.

Usage:
    pytest tests/test_nlp_extraction_rate.py -v -s
"""

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

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
_CLIENT = TestClient(app)

# ---------------------------------------------------------------------------
# Load manifest + sample data
# ---------------------------------------------------------------------------

_SAMPLE_DATA = Path(__file__).parent.parent.parent / "sample_data"
_MANIFEST: dict = json.loads((_SAMPLE_DATA / "test_manifest.json").read_text())

# Signals whose presence can be attributed to a source layer via the BFS
# signal_source fields returned by the ingest route.
_STRUCTURED_FIELDS = {
    "issuer", "audience_type", "assessment_type", "assessment_evaluator",
    "assessment_required", "canvas_course_code", "canvas_sequence_number",
    "expert_evaluation_required", "has_prerequisite_badges",
}


# ---------------------------------------------------------------------------
# Ingest helper
# ---------------------------------------------------------------------------

def _ingest_badge(badge_id: str, entry: dict) -> dict:
    """POST /ingest for one badge.  Returns the BFS dict or raises."""
    file_key = entry.get("file", f"real_badges/{badge_id}.form.json")
    form_data = json.loads((_SAMPLE_DATA / file_key).read_text())
    payload = {k: v for k, v in form_data.items()
               if not k.startswith("_") and not k.startswith("expected_")}

    resp = _CLIENT.post("/ingest", json={"input_type": "form", "payload": payload})
    if resp.status_code != 200:
        raise RuntimeError(
            f"Ingest failed for {badge_id} [{resp.status_code}]: {resp.text[:200]}"
        )
    return resp.json()


# ---------------------------------------------------------------------------
# Collect ingest results (module-level, run once)
# ---------------------------------------------------------------------------

def _collect_ingest_results() -> list[dict]:
    records = []
    for badge_id, entry in sorted(_MANIFEST.items()):
        rec = {
            "id":              badge_id,
            "error":           None,
            "issuer":          False,
            "audience":        False,
            "assessment_type": False,
            "assessment_eval": False,
            "level":           False,
            "bloom":           False,
            "badge_purpose":   False,
            "canvas":          False,
            "needs_followup":  False,
            "missing_signals": [],
            # Source-layer tallies for this badge
            "structured": 0,
            "keyword":    0,
            "regex":      0,
            "spacy":      0,
        }
        try:
            bfs = _ingest_badge(badge_id, entry)

            rec["issuer"]          = bfs.get("issuer")          is not None
            rec["audience"]        = bfs.get("audience_type")   is not None
            rec["assessment_type"] = bfs.get("assessment_type") is not None
            rec["assessment_eval"] = bfs.get("assessment_evaluator") is not None
            rec["level"]           = bfs.get("self_declared_level")  is not None
            rec["bloom"]           = bfs.get("bloom_level")     is not None
            rec["badge_purpose"]   = bfs.get("badge_purpose")   is not None
            rec["canvas"]          = bfs.get("canvas_course_code") is not None
            rec["needs_followup"]  = bool(bfs.get("needs_followup_questions", False))
            rec["missing_signals"] = bfs.get("missing_signals") or []

            # Count signals by source layer.
            # Form payloads pass structured fields directly; the ingest
            # normaliser preserves them.  NLP layers fill the rest.
            for field in _STRUCTURED_FIELDS:
                if bfs.get(field) is not None:
                    rec["structured"] += 1

            # audience_signal_source is the most reliable layer tag available
            # at ingest time for NLP-filled fields.
            aud_src = bfs.get("audience_signal_source") or ""
            if "keyword" in aud_src or "phrase" in aud_src:
                rec["keyword"] += 1
            elif "regex" in aud_src:
                rec["regex"] += 1

            # level_signal_source tags Layer 1/2 level detection
            lvl_src = bfs.get("level_signal_source") or ""
            if lvl_src == "phrase_match":
                rec["keyword"] += 1
            elif lvl_src == "regex_pattern":
                rec["regex"] += 1

            # bloom_level is always Layer 3 (spaCy)
            if bfs.get("bloom_level") is not None:
                rec["spacy"] += 1

        except Exception as exc:
            rec["error"] = str(exc)

        records.append(rec)
    return records


# Run once at module load so all tests share the same data
_RESULTS: list[dict] = _collect_ingest_results()


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _build_report(results: list[dict]) -> None:
    total = len(results)

    # Detection counts
    det = {
        "issuer_detected":                sum(1 for r in results if r["issuer"]),
        "audience_detected":              sum(1 for r in results if r["audience"]),
        "assessment_type_detected":       sum(1 for r in results if r["assessment_type"]),
        "assessment_evaluator_detected":  sum(1 for r in results if r["assessment_eval"]),
        "level_detected":                 sum(1 for r in results if r["level"]),
        "bloom_detected":                 sum(1 for r in results if r["bloom"]),
        "badge_purpose_detected":         sum(1 for r in results if r["badge_purpose"]),
        "canvas_code_detected":           sum(1 for r in results if r["canvas"]),
    }
    detection_rates = {k: v / total * 100 for k, v in det.items()}

    # Source-layer totals
    structured_count = sum(r["structured"] for r in results)
    keyword_count    = sum(r["keyword"]    for r in results)
    regex_count      = sum(r["regex"]      for r in results)
    spacy_count      = sum(r["spacy"]      for r in results)

    # Follow-up stats
    followup_count = sum(1 for r in results if r["needs_followup"])
    followup_rate  = followup_count / total * 100
    all_missing: list[str] = []
    for r in results:
        all_missing.extend(r["missing_signals"])
    most_common_missing = (
        Counter(all_missing).most_common(1)[0][0]
        if all_missing else "none"
    )

    # ── Print report ────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("NLP SIGNAL EXTRACTION RATE REPORT")
    print(f"Badges tested: {total}")
    print("=" * 55)

    print("\nSIGNAL DETECTION RATES")
    for signal, rate in detection_rates.items():
        bar = "█" * int(rate / 5)
        print(f"  {signal:<30} {rate:5.1f}%  {bar}")

    print("\nEXTRACTION BY SOURCE LAYER")
    print(f"  Structured field (form input): {structured_count} signals")
    print(f"  Layer 1 keyword rule:          {keyword_count} signals")
    print(f"  Layer 2 regex pattern:         {regex_count} signals")
    print(f"  Layer 3 spaCy Bloom:           {spacy_count} signals")

    print("\nFOLLOW-UP RATE")
    print(f"  Badges needing follow-up: {followup_count}/20 ({followup_rate:.1f}%)")
    print(f"  Most common missing:      {most_common_missing}")

    print("\nPER-BADGE EXTRACTION SUMMARY")
    print(f"{'ID':<6} {'Issuer':^8} {'Audience':^10} {'AssType':^10} "
          f"{'Level':^8} {'Bloom':^7} {'Canvas':^8}")
    print("-" * 60)
    for r in results:
        def mark(val: bool) -> str:
            return "✅" if val else "—"
        if r["error"]:
            print(f"{r['id']:<6}  ERROR: {r['error'][:45]}")
            continue
        print(
            f"{r['id']:<6} {mark(r['issuer']):^8} "
            f"{mark(r['audience']):^10} "
            f"{mark(r['assessment_type']):^10} "
            f"{mark(r['level']):^8} "
            f"{mark(r['bloom']):^7} "
            f"{mark(r['canvas']):^8}"
        )

    print("=" * 55)
    print()


# ---------------------------------------------------------------------------
# FREE TEXT inputs
# ---------------------------------------------------------------------------

_FT_INPUTS = {
    "FT1": (
        "I completed an online course offered by NJIT Learning "
        "and Development Initiative. I had to pass a final assessment "
        "with 80% or higher. This was the first course in the series."
    ),
    "FT2": (
        "After completing the foundational and intermediate "
        "series at NJIT student involvement office, I attended a "
        "two day capstone institute and presented to a panel."
    ),
    "FT3": (
        "I attended a leadership workshop at NJIT organized "
        "by the student involvement office. We had to show up for "
        "three sessions and complete a pre and post assessment."
    ),
    "FT4": (
        "I learned how to use the 3D printer at the NJIT "
        "Makerspace. I completed a safety course and passed a test "
        "with 90% or higher. An instructor watched me operate it."
    ),
    "FT5": (
        "I earned this by launching a startup or competing "
        "in a hackathon or completing an internship at a startup "
        "through the student entrepreneurship center at NJIT."
    ),
}


def _run_free_text(label: str, text: str) -> dict:
    """
    POST /ingest → POST /classify → GET /logs/{log_id}.

    Returns the fully NLP-populated BFS from normalized_facts in the
    governance log.  All three calls must succeed or RuntimeError is raised.
    """
    # Step 1 — ingest
    r1 = _CLIENT.post("/ingest", json={"input_type": "free_text", "payload": {"text": text}})
    if r1.status_code != 200:
        raise RuntimeError(
            f"Free-text ingest failed for {label} [{r1.status_code}]: {r1.text[:200]}"
        )
    bfs = r1.json()

    # Step 2 — classify (runs extract_all() which populates NLP fields)
    r2 = _CLIENT.post("/classify", json=bfs)
    if r2.status_code != 200:
        raise RuntimeError(
            f"Free-text classify failed for {label} [{r2.status_code}]: {r2.text[:200]}"
        )
    result = r2.json()

    # Step 3 — fetch governance log to get normalized_facts (full BFS post-NLP)
    log_id = result["governance"]["log_id"]
    r3 = _CLIENT.get(f"/logs/{log_id}")
    if r3.status_code != 200:
        raise RuntimeError(
            f"Log fetch failed for {label} log_id={log_id} [{r3.status_code}]: {r3.text[:200]}"
        )
    log = r3.json()
    nf = log.get("normalized_facts") or {}
    if isinstance(nf, str):
        nf = json.loads(nf)

    # Attach classify-level missing_signals and follow-up flag from result
    nf["_missing_signals"] = result.get("missing_signals") or []
    nf["_follow_up_needed"] = bool(result.get("follow_up_needed", False))
    return nf


def _collect_ft_results() -> list[dict]:
    records = []
    for label, text in _FT_INPUTS.items():
        rec = {
            "id":              label,
            "text_preview":    text[:60] + "…",
            "error":           None,
            "issuer":          False,
            "audience":        False,
            "assessment_type": False,
            "assessment_eval": False,
            "level":           False,
            "bloom":           False,
            "badge_purpose":   False,
            "canvas":          False,
            "needs_followup":  False,
            "missing_signals": [],
            # Source-layer tallies
            "l0": 0,   # Layer 0 — keyword issuer detection
            "l1": 0,   # Layer 1 — phrase match
            "l2": 0,   # Layer 2 — regex pattern
            "l3": 0,   # Layer 3 — spaCy Bloom
        }
        try:
            nf = _run_free_text(label, text)

            rec["issuer"]          = nf.get("issuer")               is not None
            rec["audience"]        = nf.get("audience_type")        is not None
            rec["assessment_type"] = nf.get("assessment_type")      is not None
            rec["assessment_eval"] = nf.get("assessment_evaluator") is not None
            rec["level"]           = nf.get("self_declared_level")  is not None
            rec["bloom"]           = nf.get("bloom_level")          is not None
            rec["badge_purpose"]   = nf.get("badge_purpose")        is not None
            rec["canvas"]          = nf.get("canvas_course_code")   is not None
            rec["needs_followup"]  = bool(nf.get("_follow_up_needed", False))
            rec["missing_signals"] = nf.get("_missing_signals") or []

            # Layer 0: issuer resolved via keyword match on free text
            if rec["issuer"]:
                rec["l0"] += 1

            # audience_signal_source reveals layer for audience detection
            aud_src = nf.get("audience_signal_source") or ""
            if "keyword" in aud_src or "phrase" in aud_src:
                rec["l1"] += 1
            elif "regex" in aud_src:
                rec["l2"] += 1

            # level_signal_source tags phrase vs regex level detection
            lvl_src = nf.get("level_signal_source") or ""
            if lvl_src == "phrase_match":
                rec["l1"] += 1
            elif lvl_src == "regex_pattern":
                rec["l2"] += 1

            # assessment_type from NLP keyword/phrase matching (Layer 1)
            if rec["assessment_type"]:
                rec["l1"] += 1

            # assessment_evaluator from NLP phrase matching (Layer 1)
            if rec["assessment_eval"]:
                rec["l1"] += 1

            # bloom_level is always Layer 3 (spaCy)
            if rec["bloom"]:
                rec["l3"] += 1

        except Exception as exc:
            rec["error"] = str(exc)

        records.append(rec)
    return records


_FT_RESULTS: list[dict] = _collect_ft_results()


# ---------------------------------------------------------------------------
# Free-text report builder
# ---------------------------------------------------------------------------

def _build_ft_report(ft_results: list[dict]) -> None:
    n = len(ft_results)

    det = {
        "issuer_detected":               sum(1 for r in ft_results if r["issuer"]),
        "audience_detected":             sum(1 for r in ft_results if r["audience"]),
        "assessment_type_detected":      sum(1 for r in ft_results if r["assessment_type"]),
        "assessment_evaluator_detected": sum(1 for r in ft_results if r["assessment_eval"]),
        "level_detected":                sum(1 for r in ft_results if r["level"]),
        "bloom_detected":                sum(1 for r in ft_results if r["bloom"]),
        "badge_purpose_detected":        sum(1 for r in ft_results if r["badge_purpose"]),
        "canvas_code_detected":          sum(1 for r in ft_results if r["canvas"]),
    }
    ft_detection_rates = {k: v / n * 100 for k, v in det.items()}

    l0_count = sum(r["l0"] for r in ft_results)
    l1_count = sum(r["l1"] for r in ft_results)
    l2_count = sum(r["l2"] for r in ft_results)
    l3_count = sum(r["l3"] for r in ft_results)

    followup_count = sum(1 for r in ft_results if r["needs_followup"])
    followup_rate  = followup_count / n * 100
    all_missing: list[str] = []
    for r in ft_results:
        all_missing.extend(r["missing_signals"])
    most_common_missing = (
        Counter(all_missing).most_common(1)[0][0]
        if all_missing else "none"
    )

    print("\nFREE TEXT EXTRACTION RATES (N=5)")
    print(f"{'Signal':<30} {'Rate':>6}")
    print("-" * 40)
    for signal, rate in ft_detection_rates.items():
        bar = "█" * int(rate / 10)
        print(f"  {signal:<28} {rate:5.1f}%  {bar}")

    print("\nFREE TEXT SOURCE LAYER BREAKDOWN")
    print(f"  Layer 0 (keyword issuer):  {l0_count} signals")
    print(f"  Layer 1 (phrase match):    {l1_count} signals")
    print(f"  Layer 2 (regex pattern):   {l2_count} signals")
    print(f"  Layer 3 (spaCy Bloom):     {l3_count} signals")

    print("\nFREE TEXT FOLLOW-UP RATE")
    print(f"  Inputs needing follow-up: {followup_count}/5 ({followup_rate:.1f}%)")
    print(f"  Most common missing:      {most_common_missing}")

    print("\nFREE TEXT PER-INPUT EXTRACTION SUMMARY")
    print(f"{'ID':<5} {'Issuer':^8} {'Audience':^10} {'AssType':^10} "
          f"{'Level':^8} {'Bloom':^7} {'Followup':^9}")
    print("-" * 60)
    for r in ft_results:
        def mark(val: bool) -> str:
            return "✅" if val else "—"
        if r["error"]:
            print(f"{r['id']:<5}  ERROR: {r['error'][:45]}")
            continue
        fu = "yes" if r["needs_followup"] else "no"
        print(
            f"{r['id']:<5} {mark(r['issuer']):^8} "
            f"{mark(r['audience']):^10} "
            f"{mark(r['assessment_type']):^10} "
            f"{mark(r['level']):^8} "
            f"{mark(r['bloom']):^7} "
            f"{fu:^9}"
        )
        # Print what was detected for context
        details = []
        if r["issuer"]:    details.append(f"issuer detected")
        if r["level"]:     details.append(f"level detected")
        if r["bloom"]:     details.append(f"bloom detected")
        if r["missing_signals"]:
            details.append(f"missing={r['missing_signals']}")
        if details:
            print(f"       ↳ {', '.join(details)}")

    print("=" * 55)
    print()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def results():
    return _RESULTS


@pytest.fixture(scope="module")
def ft_results():
    return _FT_RESULTS


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extraction_rate_report(results, ft_results):
    """
    Print the full NLP extraction rate report (form + free text).

    READ-ONLY — no source modifications.
    """
    _build_report(results)
    _build_ft_report(ft_results)


def test_issuer_detection_rate(results):
    """Issuer must be detected in >= 90% of form badges at ingest time."""
    total = len(results)
    n = sum(1 for r in results if r["issuer"])
    rate = n / total * 100
    assert rate >= 90.0, (
        f"Issuer detection rate {n}/{total} ({rate:.1f}%) is below 90%."
    )


def test_assessment_type_detection_rate(results):
    """Assessment type must be detected in >= 80% of form badges at ingest time."""
    total = len(results)
    n = sum(1 for r in results if r["assessment_type"])
    rate = n / total * 100
    assert rate >= 80.0, (
        f"Assessment type detection rate {n}/{total} ({rate:.1f}%) is below 80%."
    )


def test_no_ingest_errors(results):
    """Every form badge must complete POST /ingest without an exception."""
    errors = [(r["id"], r["error"]) for r in results if r["error"]]
    assert not errors, f"Ingest errors for badges: {errors}"


def test_ft_no_ingest_errors(ft_results):
    """Every free-text input must complete ingest + classify + log fetch without an exception."""
    errors = [(r["id"], r["error"]) for r in ft_results if r["error"]]
    assert not errors, f"Free-text pipeline errors: {errors}"


def test_ft_issuer_detection_rate(ft_results):
    """Issuer keyword extraction must fire for >= 60% of free-text inputs."""
    n = sum(1 for r in ft_results if r["issuer"])
    total = len(ft_results)
    rate = n / total * 100
    assert rate >= 60.0, (
        f"Free-text issuer detection rate {n}/{total} ({rate:.1f}%) is below 60%."
    )
