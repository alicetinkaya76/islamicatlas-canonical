"""
H8 Stage 5 AG conformance tests for dia_person_enrichment_v8.

Pre-pilot (Stage 4 not yet run): all tests skip with "No v8 records yet"
since the canonical store has no records carrying dia-chunks-v8:* provenance.

Post-pilot (Stage 4 run via `python3 pipelines/run_adapter.py --id
dia-person-enrichment-v8 --limit 50`): tests verify the 7 AG criteria.

After bulk run (Stage 6): all 7 tests must remain green.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
SCHEMAS_DIR = REPO_ROOT / "schemas"

ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")


# ----------------------------------------------------------------------
# Fixtures (module-scoped — load once per test session)
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def v8_records():
    """Person records carrying dia-chunks-v8:* in provenance.derived_from.
    (H9 Stage 3: filters conftest's process-cached store instead of re-reading
    21,946 files — this module no longer re-loads the person store.)"""
    from tests.integration import conftest as shared
    out = []
    for rec in shared.load_records("person"):
        derived = rec.get("provenance", {}).get("derived_from", []) or []
        for d in derived:
            if isinstance(d, dict):
                sid = d.get("source_id")
                if isinstance(sid, str) and sid.startswith("dia-chunks-v8:"):
                    pid = rec.get("@id", "")
                    fname = f"iac_person_{pid.rsplit('-', 1)[-1]}.json" if pid else "?"
                    out.append((fname, rec))
                    break
    return out


@pytest.fixture(scope="module")
def person_validator():
    """Schema validator with full $ref resolution registry (process-cached)."""
    from tests.integration import conftest as shared
    return shared.validator_for("person")


# ----------------------------------------------------------------------
# AG tests (7 criteria per H8_MASTER_PLAN_REVISION_PATCH.md v1.1)
# ----------------------------------------------------------------------


def test_ag1_v8_records_validate(v8_records, person_validator):
    """AG.1 — All v8-enriched records validate against person.schema.json."""
    if not v8_records:
        pytest.skip("No v8-enriched records yet — Stage 4 pilot not run")
    failures = []
    for fname, rec in v8_records:
        errors = list(person_validator.iter_errors(rec))
        if errors:
            top = errors[0]
            failures.append(
                f"{fname}: {'.'.join(str(p) for p in top.absolute_path)} "
                f":: {top.message[:200]}"
            )
    assert not failures, (
        f"v8 records failed validation:\n  " + "\n  ".join(failures[:5])
    )


def test_ag2_idempotency(v8_records):
    """AG.2 — No record carries more than one dia-chunks-v8:<slug> entry."""
    if not v8_records:
        pytest.skip()
    for fname, rec in v8_records:
        v8_entries = [
            d for d in rec.get("provenance", {}).get("derived_from", [])
            if isinstance(d, dict)
            and isinstance(d.get("source_id"), str)
            and d["source_id"].startswith("dia-chunks-v8:")
        ]
        assert len(v8_entries) == 1, (
            f"{fname}: {len(v8_entries)} v8 entries (idempotency violated)"
        )


def test_ag3_description_upgrade_meaningful(v8_records):
    """AG.3 — Some v8 records have description.tr > 5,000 chars (proves upgrade
    actually occurred; H4 capped at 5,000)."""
    if not v8_records:
        pytest.skip()
    upgraded = sum(
        1 for _, rec in v8_records
        if len(rec.get("labels", {}).get("description", {}).get("tr", "")) > 5000
    )
    # Expected (per Stage 2b): ~68.8% of Cat A. Even at pilot=50 we should see
    # >= 10 records upgraded.
    assert upgraded > 0, (
        f"No v8 record has description.tr > 5,000 chars — upgrade not firing? "
        f"Total v8 records inspected: {len(v8_records)}"
    )


def test_ag4_preserves_h4_provenance(v8_records):
    """AG.4 — Every v8-enriched record retains its original dia:<slug> H4 entry."""
    if not v8_records:
        pytest.skip()
    failures = []
    for fname, rec in v8_records:
        derived = rec.get("provenance", {}).get("derived_from", [])
        h4_entries = [
            d for d in derived
            if isinstance(d, dict)
            and isinstance(d.get("source_id"), str)
            and d["source_id"].startswith("dia:")
            and not d["source_id"].startswith("dia-chunks-v8:")
        ]
        if not h4_entries:
            failures.append(fname)
    assert not failures, (
        f"Records lost their H4 dia:<slug> entry: {failures[:5]}"
    )


def test_ag5_arabic_preflabel_validity(v8_records):
    """AG.5 — Where prefLabel.ar exists, it contains Arabic-script characters."""
    if not v8_records:
        pytest.skip()
    failures = []
    for fname, rec in v8_records:
        ar = rec.get("labels", {}).get("prefLabel", {}).get("ar")
        if ar and not ARABIC_RE.search(ar):
            failures.append(f"{fname}: prefLabel.ar={ar!r} has no Arabic")
    assert not failures, "\n".join(failures[:5])


def test_ag6_update_history_entry_present(v8_records):
    """AG.6 — Every v8 record has a record_history update entry tagged
    'dia_person_enrichment_v8'."""
    if not v8_records:
        pytest.skip()
    failures = []
    for fname, rec in v8_records:
        history = rec.get("provenance", {}).get("record_history", [])
        v8_updates = [
            h for h in history
            if h.get("change_type") == "update"
            and "dia_person_enrichment_v8" in (h.get("note") or "")
        ]
        if not v8_updates:
            failures.append(fname)
    assert not failures, (
        f"Records missing v8 update history entry: {failures[:5]}"
    )


def test_ag7_description_within_50k(v8_records):
    """AG.7 — No description.<lang> exceeds 50,000 chars (ADR-012 limit)."""
    if not v8_records:
        pytest.skip()
    failures = []
    for fname, rec in v8_records:
        descs = rec.get("labels", {}).get("description", {}) or {}
        for lang, text in descs.items():
            if isinstance(text, str) and len(text) > 50000:
                failures.append(
                    f"{fname}: description.{lang} = {len(text)} chars"
                )
    assert not failures, (
        f"Records exceed 50K limit (ADR-012):\n  " + "\n  ".join(failures[:5])
    )
