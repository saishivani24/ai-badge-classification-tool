"""
test_accuracy_matrix.py

READ-ONLY validation metric tests — measures system classification accuracy
against all badges in test_manifest.json.  Does NOT modify any source code,
models, routes, or existing test files.

Usage:
    pytest tests/test_accuracy_matrix.py -v -s

Output:
    Printed accuracy matrix with per-badge pass/fail per dimension, then
    aggregate accuracy per dimension and an overall score.

Rules:
    - All assertions are SOFT for individual badges (discrepancies are printed
      but do not stop the report).  One HARD assertion at the end verifies
      overall accuracy >= 75%.
    - S3SK level rules (Bloom NLP-dependent) are checked softly — any of
      S3SK01/02/03/04 is accepted as long as type=Skill and level is correct.
"""

import json
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Force in-memory DB before any app import touches the database layer.
# ---------------------------------------------------------------------------
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.governance_log import Base
from database import get_db

# ---------------------------------------------------------------------------
# In-memory DB override (same pattern as test_real_badges.py)
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

# S3SK rules are NLP/Bloom-sensitive — allow any of them when type=Skill
_SKILL_LEVEL_RULES = {"S3SK01", "S3SK02", "S3SK03", "S3SK04", "S3SK05"}


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def _run_badge(badge_id: str, entry: dict) -> dict:
    """POST /ingest + POST /classify for one badge.  Returns ClassificationResult dict."""
    file_key = entry.get("file", f"real_badges/{badge_id}.form.json")
    form_data = json.loads((_SAMPLE_DATA / file_key).read_text())
    payload = {k: v for k, v in form_data.items()
               if not k.startswith("_") and not k.startswith("expected_")}

    ingest_resp = _CLIENT.post("/ingest", json={"input_type": "form", "payload": payload})
    if ingest_resp.status_code != 200:
        raise RuntimeError(f"Ingest failed [{ingest_resp.status_code}]: {ingest_resp.text[:200]}")

    bfs = ingest_resp.json()
    classify_resp = _CLIENT.post("/classify", json=bfs)
    if classify_resp.status_code != 200:
        raise RuntimeError(f"Classify failed [{classify_resp.status_code}]: {classify_resp.text[:200]}")

    return classify_resp.json()


def _check_badge(badge_id: str, entry: dict) -> dict:
    """
    Run pipeline for one badge and return a result record with pass/fail
    for each dimension.  Never raises — errors are captured as FAIL.
    """
    rec = {
        "badge_id":   badge_id,
        "description": entry.get("description", entry.get("badge_title", badge_id)),
        "error":      None,
        "cat_pass":   False,
        "type_pass":  False,
        "level_pass": False,
        "conf_pass":  False,
        "rules_pass": False,
        "actual_category":    "ERROR",
        "actual_type":        "ERROR",
        "actual_level":       "ERROR",
        "actual_confidence":  "ERROR",
        "missing_rules":      [],
    }

    try:
        r = _run_badge(badge_id, entry)
        cls = r["classification"]
        actual_rules = set(r.get("rules_triggered", []))

        rec["actual_category"]   = cls.get("category")
        rec["actual_type"]       = cls.get("type")
        rec["actual_level"]      = cls.get("level")
        rec["actual_confidence"] = cls.get("confidence")

        rec["cat_pass"]   = cls.get("category")    == entry["expected_category"]
        rec["type_pass"]  = cls.get("type")         == entry["expected_type"]
        rec["level_pass"] = cls.get("level")        == entry["expected_level"]
        rec["conf_pass"]  = cls.get("confidence")   == entry["expected_confidence"]

        # Rule check: each expected rule must appear in actual triggered rules,
        # EXCEPT for S3SK rules when type=Skill — those are NLP-dependent.
        expected_rules = entry.get("expected_rules", [])
        missing = []
        for rule in expected_rules:
            if rule in _SKILL_LEVEL_RULES:
                # Accept any S3SK rule as long as the correct S3SK branch ran
                if not any(r in actual_rules for r in _SKILL_LEVEL_RULES):
                    missing.append(rule)
            else:
                if rule not in actual_rules:
                    missing.append(rule)
        rec["missing_rules"] = missing
        rec["rules_pass"]    = len(missing) == 0

    except Exception as exc:
        rec["error"] = str(exc)

    return rec


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

_W_ID   = 5
_W_DESC = 46
_W_DIM  = 6
_W_OK   = 4

def _pad(s: str, w: int) -> str:
    s = str(s) if s is not None else "None"
    return s[:w].ljust(w)

def _dim(passed: bool) -> str:
    return " PASS " if passed else " FAIL "

def _bar(n: int, total: int, width: int = 20) -> str:
    filled = round(n / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def _print_report(results: list[dict]) -> None:
    total = len(results)
    header = (
        f"\n{'═' * 95}\n"
        f"  BADGE CLASSIFICATION ACCURACY MATRIX  —  {total} badges\n"
        f"{'═' * 95}\n"
    )
    print(header)

    col_hdr = (
        f"  {'ID':<{_W_ID}}  {'Description':<{_W_DESC}}"
        f"  {'Cat':^{_W_DIM}}  {'Type':^{_W_DIM}}  {'Level':^{_W_DIM}}"
        f"  {'Conf':^{_W_DIM}}  {'Rules':^{_W_DIM}}  {'':^{_W_OK}}"
    )
    print(col_hdr)
    print("  " + "─" * 93)

    for rec in results:
        if rec["error"]:
            line = (
                f"  {_pad(rec['badge_id'], _W_ID)}"
                f"  {_pad(rec['description'], _W_DESC)}"
                f"  {'ERROR':^{_W_DIM * 5 + 16}}"
            )
            print(line)
            print(f"      ↳ {rec['error'][:90]}")
            continue

        all_pass = all([
            rec["cat_pass"], rec["type_pass"],
            rec["level_pass"], rec["conf_pass"], rec["rules_pass"],
        ])
        ok_symbol = " ✓  " if all_pass else " ✗  "

        line = (
            f"  {_pad(rec['badge_id'], _W_ID)}"
            f"  {_pad(rec['description'], _W_DESC)}"
            f"  {_dim(rec['cat_pass'])}"
            f"  {_dim(rec['type_pass'])}"
            f"  {_dim(rec['level_pass'])}"
            f"  {_dim(rec['conf_pass'])}"
            f"  {_dim(rec['rules_pass'])}"
            f"  {ok_symbol}"
        )
        print(line)

        # Print detail rows for any FAIL dimension
        if not rec["cat_pass"]:
            print(f"      ↳ category  expected={rec['actual_category']!r}  "
                  f"← expected {_MANIFEST[rec['badge_id']]['expected_category']!r}")
        if not rec["type_pass"]:
            print(f"      ↳ type      got={rec['actual_type']!r}  "
                  f"expected={_MANIFEST[rec['badge_id']]['expected_type']!r}")
        if not rec["level_pass"]:
            print(f"      ↳ level     got={rec['actual_level']!r}  "
                  f"expected={_MANIFEST[rec['badge_id']]['expected_level']!r}")
        if not rec["conf_pass"]:
            print(f"      ↳ conf      got={rec['actual_confidence']!r}  "
                  f"expected={_MANIFEST[rec['badge_id']]['expected_confidence']!r}")
        if not rec["rules_pass"]:
            print(f"      ↳ rules     missing={rec['missing_rules']}")

    # Aggregate
    n_cat   = sum(1 for r in results if r["cat_pass"])
    n_type  = sum(1 for r in results if r["type_pass"])
    n_level = sum(1 for r in results if r["level_pass"])
    n_conf  = sum(1 for r in results if r["conf_pass"])
    n_rules = sum(1 for r in results if r["rules_pass"])
    n_all   = sum(1 for r in results if all([
        r["cat_pass"], r["type_pass"], r["level_pass"], r["conf_pass"], r["rules_pass"]
    ]))

    print("\n  " + "─" * 93)
    print("\n  DIMENSION ACCURACY\n")
    dims = [
        ("Category",   n_cat),
        ("Type",       n_type),
        ("Level",      n_level),
        ("Confidence", n_conf),
        ("Rules",      n_rules),
    ]
    for label, n in dims:
        pct = n / total * 100
        bar = _bar(n, total)
        print(f"  {label:<12}  {n:>2}/{total}  {pct:5.1f}%  {bar}")

    overall_pct = n_all / total * 100
    print(f"\n  {'OVERALL':<12}  {n_all:>2}/{total}  {overall_pct:5.1f}%  "
          f"(all 5 dimensions passing)")
    print(f"\n{'═' * 95}\n")

    return n_all, total


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def all_results():
    """Run the full pipeline for every manifest badge once per module."""
    return [_check_badge(bid, entry) for bid, entry in sorted(_MANIFEST.items())]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_accuracy_matrix(all_results):
    """
    Print a full accuracy matrix and assert overall accuracy >= 75%.

    This is a READ-ONLY metric test.  It measures system performance without
    modifying any source code, routes, or models.
    """
    n_all, total = _print_report(all_results)
    min_passing = int(total * 0.75)
    assert n_all >= min_passing, (
        f"Overall accuracy {n_all}/{total} ({n_all/total*100:.1f}%) "
        f"is below the 75% threshold ({min_passing}/{total})."
    )


def test_category_accuracy(all_results):
    """Category must be correct for >= 90% of badges."""
    n = sum(1 for r in all_results if r["cat_pass"])
    total = len(all_results)
    assert n / total >= 0.90, (
        f"Category accuracy {n}/{total} ({n/total*100:.1f}%) is below 90%."
    )


def test_type_accuracy(all_results):
    """Type must be correct for >= 90% of badges."""
    n = sum(1 for r in all_results if r["type_pass"])
    total = len(all_results)
    assert n / total >= 0.90, (
        f"Type accuracy {n}/{total} ({n/total*100:.1f}%) is below 90%."
    )


def test_no_pipeline_errors(all_results):
    """Every badge must complete ingest + classify without an exception."""
    errors = [(r["badge_id"], r["error"]) for r in all_results if r["error"]]
    assert not errors, f"Pipeline errors for badges: {errors}"
