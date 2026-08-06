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

from ._store import STORE_SKIP

# H59: bu modül hem canonical/person kayıtlarını hem data/_state karantina
# sidecar'ını okuyor. Kapısı YOKTU; H49 person/'ı depoya alınca CI'da
# koşmaya başladı ve "kanıt kayboldu" diye düştü — oysa kayıp olan
# _state/ dizininin kendisiydi. Ortak kapı hepsini sorar.
pytestmark = STORE_SKIP

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
    """The H7 confirmed-wrong QIDs must remain visibly wrong in ONE of two
    sanctioned forms (H11 Karar 3 doktrin birleşmesi):
      (a) H7 tombstone: in-record xref w/ confidence==0.0 + h7_audit_ note, OR
      (b) H11 quarantine: xref REMOVED from the record and present in
          data/_state/qid_quarantine.json with evidence.
    What must NEVER happen: the bad QID sitting in the record as a normal,
    displayable xref — or vanishing without a quarantine trace."""
    fn = _person_path(pid)
    if not fn.exists():
        pytest.skip(f"canonical person store not present: {fn}")

    xrefs = _load_xref(pid)
    matches = [
        e for e in xrefs
        if isinstance(e, dict)
        and e.get("authority") == "wikidata"
        and e.get("id") == bad_qid
    ]
    if matches:  # form (a): tombstone
        assert len(matches) == 1
        e = matches[0]
        assert e.get("confidence") == 0.0, (
            f"{pid}: tombstone confidence should be 0.0, got "
            f"{e.get('confidence')!r} (was the H7 flag reverted?)")
        assert e.get("reviewed") is False
        assert (e.get("note") or "").startswith(H7_NOTE_PREFIX)
        return
    # form (b): quarantined
    qpath = REPO_ROOT / "data" / "_state" / "qid_quarantine.json"
    assert qpath.exists(), (
        f"{pid}: bad QID {bad_qid} absent from record AND no quarantine "
        f"sidecar — the wrong-target evidence vanished")
    q = json.loads(qpath.read_text(encoding="utf-8"))
    assert any(x.get("pid") == pid and x.get("qid") == bad_qid
               for x in q.get("quarantined", [])), (
        f"{pid}: bad QID {bad_qid} neither tombstoned in-record nor "
        f"quarantined with evidence")


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
