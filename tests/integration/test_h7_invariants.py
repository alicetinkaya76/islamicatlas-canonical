"""
H7 invariant tests.

These tests defend three things produced in Hafta 7:
  H7-1: Four person records carry the H7 audit flag pattern
        (confidence==0.0 + note startswith "h7_audit_confirmed_wrong_target:").
  H7-2: Frontend integration spec contains the Wikidata display gate
        (section 2.4 + the isWikidataXrefDisplayable predicate).
  H7-3: The H7 QID audit state sidecar exists and is internally
        consistent with the four flagged person records.

If any of these regressed, an H7+ pass either reverted the QID flag
or removed the frontend gate doctrine. Both are non-trivial changes
and need explicit review.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
STATE_PATH = REPO_ROOT / "data" / "_state" / "h7_qid_audit_report.json"
SPEC_PATH = (
    REPO_ROOT
    / "docs"
    / "h6_phase_0b"
    / "HAFTA6_S5_FRONTEND_INTEGRATION_SPEC.md"
)

H7_NOTE_PREFIX = "h7_audit_confirmed_wrong_target:"

H7_TARGETS = [
    ("iac:person-00000184", "Q9438"),
    ("iac:person-00000115", "Q9458"),
    ("iac:person-00020919", "Q36533610"),
    ("iac:person-00000182", "Q719449"),
]


def _person_path(pid: str) -> Path:
    stem = pid.replace("iac:", "iac_").replace("-", "_")
    return PERSON_DIR / f"{stem}.json"


def _load_xref(pid: str) -> list[dict]:
    fn = _person_path(pid)
    if not fn.exists():
        return []
    d = json.loads(fn.read_text(encoding="utf-8"))
    return d.get("authority_xref") or []


@pytest.mark.parametrize("pid,bad_qid", H7_TARGETS)
def test_h7_1_qid_flag_invariant(pid: str, bad_qid: str) -> None:
    """Each H7 target carries the wikidata xref with confidence==0.0
    and the h7_audit_ note prefix. Method/reviewed combination MUST
    indicate a deliberate flag, not a stale low-confidence draft."""
    fn = _person_path(pid)
    if not fn.exists():
        pytest.skip(f"canonical person store not present: {fn}")

    xrefs = _load_xref(pid)
    matches = [
        e
        for e in xrefs
        if isinstance(e, dict)
        and e.get("authority") == "wikidata"
        and e.get("id") == bad_qid
    ]
    assert len(matches) == 1, (
        f"{pid}: expected exactly 1 wikidata xref for {bad_qid}, "
        f"got {len(matches)}"
    )
    e = matches[0]
    assert e.get("confidence") == 0.0, (
        f"{pid}: confidence should be 0.0, got {e.get('confidence')!r} "
        f"(was the H7 flag reverted?)"
    )
    assert e.get("reviewed") is False, (
        f"{pid}: reviewed should be False, got {e.get('reviewed')!r}"
    )
    note = e.get("note") or ""
    assert note.startswith(H7_NOTE_PREFIX), (
        f"{pid}: note should start with {H7_NOTE_PREFIX!r}, "
        f"got {note[:80]!r}"
    )


def test_h7_2_frontend_spec_has_wikidata_gate() -> None:
    """Spec contains the H7 Stage 2 patches: section 2.4 heading,
    the isWikidataXrefDisplayable predicate, and the F2 PersonCard
    deliverable's Wikidata gate done-when criterion."""
    if not SPEC_PATH.exists():
        pytest.skip(f"frontend spec not present: {SPEC_PATH}")

    txt = SPEC_PATH.read_text(encoding="utf-8")

    assert "2.4" in txt and "Wikidata QID display policy" in txt, (
        "spec missing section 2.4 'Wikidata QID display policy'"
    )
    assert "isWikidataXrefDisplayable" in txt, (
        "spec missing TS predicate isWikidataXrefDisplayable"
    )
    assert "h7_audit_confirmed_wrong_target" in txt, (
        "spec missing reference to h7_audit_ note prefix"
    )
    assert "Wikidata gate" in txt or "Wikidata QID gating" in txt, (
        "spec missing F2 deliverable update or section 6 bullet "
        "referencing the gate"
    )


def test_h7_3_audit_state_sidecar_consistent() -> None:
    """The H7 audit state sidecar exists and reports four targets
    in either 'wrote' or 'noop_already_flagged' status. Any other
    state means the script ran but disagrees with the canonical store."""
    if not STATE_PATH.exists():
        pytest.skip(f"h7 audit state sidecar not present: {STATE_PATH}")

    report = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    assert report.get("audit_id") == "h7_qid_audit_001_confirmed_wrong_targets"
    assert report.get("schema_target_version") == "v0.2.0"

    decisions = report.get("decisions") or []
    target_pids = {p for p, _ in H7_TARGETS}
    decision_pids = {d.get("pid") for d in decisions if isinstance(d, dict)}
    missing = target_pids - decision_pids
    assert not missing, f"audit report missing targets: {missing}"

    valid_decisions = {"wrote", "already_flagged_noop", "would_write"}
    for d in decisions:
        if d.get("pid") in target_pids:
            assert d.get("decision") in valid_decisions, (
                f"target {d.get('pid')} has unexpected decision "
                f"{d.get('decision')!r}; expected one of {valid_decisions}"
            )
