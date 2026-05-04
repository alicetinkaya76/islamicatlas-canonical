"""
test_dia_pilot.py — Acceptance suite for Hafta 4 person namespace seed.

Mirrors the 19-test structure of test_yaqut_pilot.py from Hafta 3.

Categories:
  A. Schema validity (5)
  B. PID minting and idempotency (3)
  C. Cross-source resolution (4)
  D. Dynasty rulers dual-write (3)
  E. El-Aʿlām two-track integrity (2)
  F. Yâqūt person→place edge resolution (2)
  G. Counts and acceptance thresholds (4)

Total target: ≥23 tests.

Run:
    pytest tests/integration/test_dia_pilot.py -v
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
DYNASTY_DIR = REPO_ROOT / "data" / "canonical" / "dynasty"
SCHEMAS_DIR = REPO_ROOT / "schemas"
STATE_DIR = REPO_ROOT / "data" / "_state"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def schemas_registry():
    schemas: dict[str, dict] = {}
    for schema_path in SCHEMAS_DIR.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            s = json.load(fh)
        if s.get("$id"):
            schemas[s["$id"]] = s
    registry = Registry()
    for sid, s in schemas.items():
        registry = registry.with_resource(uri=sid, resource=Resource.from_contents(s))
    return registry


@pytest.fixture(scope="module")
def person_validator(schemas_registry):
    with (SCHEMAS_DIR / "person.schema.json").open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=schemas_registry)


@pytest.fixture(scope="module")
def dynasty_validator(schemas_registry):
    with (SCHEMAS_DIR / "dynasty.schema.json").open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=schemas_registry)


@pytest.fixture(scope="module")
def all_person_records():
    out = []
    for p in sorted(PERSON_DIR.glob("iac_person_*.json")):
        with p.open(encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


@pytest.fixture(scope="module")
def all_dynasty_records():
    out = []
    for p in sorted(DYNASTY_DIR.glob("iac_dynasty_*.json")):
        with p.open(encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


# --------------------------------------------------------------------------- #
# A. Schema validity (5 tests)
# --------------------------------------------------------------------------- #


def test_a1_all_person_records_validate(all_person_records, person_validator):
    """A1: Every iac:person-* record must validate against person.schema."""
    failures = []
    for rec in all_person_records:
        errors = list(person_validator.iter_errors(rec))
        if errors:
            top = errors[0]
            failures.append((rec.get("@id"),
                             f"[{'.'.join(str(x) for x in top.absolute_path) or '<root>'}] {top.message[:200]}"))
    assert not failures, f"{len(failures)} schema-invalid persons; first: {failures[:3]}"


def test_a2_all_dynasty_records_validate_with_patched_schema(all_dynasty_records, dynasty_validator):
    """A2: Patched dynasty schema (had_ruler + rulers[].person_pid) — all dynasties valid."""
    failures = []
    for rec in all_dynasty_records:
        errors = list(dynasty_validator.iter_errors(rec))
        if errors:
            top = errors[0]
            failures.append((rec.get("@id"),
                             f"[{'.'.join(str(x) for x in top.absolute_path) or '<root>'}] {top.message[:200]}"))
    assert not failures, f"{len(failures)} schema-invalid dynasties; first: {failures[:3]}"


def test_a3_every_person_has_pid(all_person_records):
    """A3: Every record carries an @id matching iac:person-NNNNNNNN."""
    pid_re = re.compile(r"^iac:person-\d{8}$")
    bad = [r.get("@id") for r in all_person_records if not pid_re.match(r.get("@id") or "")]
    assert not bad, f"{len(bad)} persons with malformed PID; first: {bad[:3]}"


def test_a4_temporal_anyof_satisfied(all_person_records):
    """A4: Every person has at least one of birth_temporal/death_temporal/floruit_temporal."""
    no_temporal = [r["@id"] for r in all_person_records
                   if not (r.get("birth_temporal") or r.get("death_temporal") or r.get("floruit_temporal"))]
    assert not no_temporal, f"{len(no_temporal)} persons without any temporal block; first: {no_temporal[:3]}"


def test_a5_type_array_contains_person(all_person_records):
    """A5: Every person's @type array contains 'iac:Person'."""
    bad = [r["@id"] for r in all_person_records if "iac:Person" not in (r.get("@type") or [])]
    assert not bad, f"{len(bad)} persons missing iac:Person in @type; first: {bad[:3]}"


# --------------------------------------------------------------------------- #
# B. PID minting and idempotency (3 tests)
# --------------------------------------------------------------------------- #


def test_b1_person_pids_unique(all_person_records):
    """B1: All person PIDs are unique."""
    pids = [r["@id"] for r in all_person_records]
    assert len(pids) == len(set(pids)), f"Duplicate PIDs found: {len(pids) - len(set(pids))}"


def test_b2_pid_index_consistent():
    """B2: data/_state/pid_index.json contains an entry for every iac:person-* file."""
    idx_path = STATE_DIR / "pid_index.json"
    if not idx_path.exists():
        pytest.skip("pid_index.json not present (older minter version?)")
    with idx_path.open(encoding="utf-8") as fh:
        idx = json.load(fh)
    indexed_pids = {v for k, v in idx.items() if k.startswith("person:")}
    on_disk = {p.stem.replace("iac_person_", "iac:person-") for p in PERSON_DIR.glob("iac_person_*.json")}
    # Allow a missing prefix style mismatch — convert
    on_disk_normalized = set()
    for p in on_disk:
        # iac:person-00000001 already; some may need padding
        on_disk_normalized.add(p)
    assert indexed_pids.issuperset(on_disk_normalized), (
        f"Index missing {len(on_disk_normalized - indexed_pids)} on-disk PIDs"
    )


def test_b3_pid_counter_consistent():
    """B3: pid_counter.person >= number of person files on disk."""
    counter_path = STATE_DIR / "pid_counter.json"
    with counter_path.open(encoding="utf-8") as fh:
        c = json.load(fh)
    n_files = len(list(PERSON_DIR.glob("iac_person_*.json")))
    assert c.get("person", 0) >= n_files, (
        f"counter.person={c.get('person', 0)} < {n_files} files on disk"
    )


# --------------------------------------------------------------------------- #
# C. Cross-source resolution (4 tests)
# --------------------------------------------------------------------------- #


def test_c1_dia_to_alam_xref_consistency():
    """C1: Every PID in dia_to_alam_xref.json should be a real person on disk."""
    p = STATE_DIR / "dia_to_alam_xref.json"
    if not p.exists():
        pytest.skip("dia_to_alam_xref sidecar missing")
    with p.open(encoding="utf-8") as fh:
        xref = json.load(fh)
    on_disk = {pp.stem.replace("iac_person_", "iac:person-") for pp in PERSON_DIR.glob("iac_person_*.json")}
    on_disk_int = {f"iac:person-{int(p.split('-')[1]):08d}" for p in on_disk}
    missing = [pid for pid in xref if pid not in on_disk_int]
    assert not missing, f"{len(missing)} xref PIDs not found on disk; first: {missing[:3]}"


def test_c2_track_a_augment_records_have_two_derived_from():
    """C2: Persons in el_alam_augment_pending should have provenance.derived_from
    with both DİA and El-Aʿlām entries after pass_augment_alam runs."""
    p = STATE_DIR / "el_alam_augment_pending.json"
    if not p.exists():
        pytest.skip("el_alam_augment_pending sidecar missing")
    with p.open(encoding="utf-8") as fh:
        aug = json.load(fh)
    # Sample first 50 to keep fast
    n_sampled = 0
    n_with_two = 0
    for pid in list(aug.keys())[:50]:
        ppath = PERSON_DIR / f"iac_person_{pid.split('-')[1]}.json"
        if not ppath.exists():
            continue
        with ppath.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        n_sampled += 1
        sids = [d.get("source_id", "") for d in rec.get("provenance", {}).get("derived_from", [])]
        has_dia = any(s.startswith("dia:") for s in sids)
        has_alam = any(s.startswith("el-alam:") for s in sids)
        if has_dia and has_alam:
            n_with_two += 1
    assert n_sampled > 0, "No augment_pending records sampled"
    # Allow some tolerance for race conditions / partial augments
    assert n_with_two >= int(n_sampled * 0.95), (
        f"Only {n_with_two}/{n_sampled} sampled augment records have both DİA + Alam derived_from"
    )


def test_c3_dia_persons_carry_dia_source_id(all_person_records):
    """C3: All persons whose provenance includes a 'dia:slug' source must have
    that source as the FIRST derived_from entry (creator)."""
    bad = []
    for r in all_person_records:
        df = r.get("provenance", {}).get("derived_from", [])
        sids = [d.get("source_id", "") for d in df]
        if any(s.startswith("dia:") for s in sids):
            if not sids[0].startswith("dia:"):
                bad.append((r["@id"], sids))
    assert not bad, f"{len(bad)} DİA persons with dia: not as first derived_from; first: {bad[:2]}"


def test_c4_no_orphan_alam_track_b_records(all_person_records):
    """C4: Track-B (mint-new) Alam persons should have el-alam: as the FIRST
    derived_from entry. (And no dia: entries.)"""
    bad = []
    for r in all_person_records:
        df = r.get("provenance", {}).get("derived_from", [])
        sids = [d.get("source_id", "") for d in df]
        if not sids:
            continue
        if sids[0].startswith("el-alam:"):
            # Track B: should not have dia: at all (DİA-known persons go via Track A)
            has_dia = any(s.startswith("dia:") for s in sids)
            if has_dia:
                bad.append((r["@id"], sids))
    assert not bad, f"{len(bad)} Track-B persons that also have dia: derived_from (should not happen): {bad[:2]}"


# --------------------------------------------------------------------------- #
# D. Dynasty rulers dual-write (3 tests)
# --------------------------------------------------------------------------- #


def test_d1_every_dynasty_with_rulers_has_had_ruler(all_dynasty_records):
    """D1: Any dynasty with non-empty rulers[] must have non-empty had_ruler[]
    after the promotion pass."""
    bad = []
    for r in all_dynasty_records:
        rulers = r.get("rulers") or []
        had_ruler = r.get("had_ruler") or []
        if rulers and not had_ruler:
            bad.append(r["@id"])
    assert not bad, f"{len(bad)} dynasties with rulers but no had_ruler[]: {bad[:3]}"


def test_d2_had_ruler_pids_exist(all_dynasty_records):
    """D2: Every PID in had_ruler[] points to an existing person record."""
    on_disk = {pp.stem.replace("iac_person_", "iac:person-") for pp in PERSON_DIR.glob("iac_person_*.json")}
    bad = []
    for r in all_dynasty_records:
        for ppid in (r.get("had_ruler") or []):
            if ppid not in on_disk:
                bad.append((r["@id"], ppid))
    assert not bad, f"{len(bad)} broken PID references in had_ruler[]: {bad[:5]}"


def test_d3_rulers_person_pid_matches_had_ruler(all_dynasty_records):
    """D3: For each ruler index i, dynasty.rulers[i].person_pid == had_ruler[i]
    OR rulers[i].person_pid not set (partial promotion is allowed in dual-write
    phase, but if set must match the parallel array entry by index after dedup)."""
    bad = []
    for r in all_dynasty_records:
        rulers = r.get("rulers") or []
        had_ruler = r.get("had_ruler") or []
        # had_ruler may be deduped; check that every set rulers[i].person_pid
        # is contained in had_ruler[]
        had_set = set(had_ruler)
        for i, ru in enumerate(rulers):
            ppid = ru.get("person_pid")
            if ppid and ppid not in had_set:
                bad.append((r["@id"], i, ppid))
    assert not bad, f"{len(bad)} ruler.person_pid not in had_ruler[]: {bad[:3]}"


# --------------------------------------------------------------------------- #
# E. El-Aʿlām two-track integrity (2 tests)
# --------------------------------------------------------------------------- #


def test_e1_track_a_ratio_sane():
    """E1: Track A (augment) count should match dia_alam_xref bridge size (~1,280)."""
    augp = STATE_DIR / "el_alam_augment_pending.json"
    if not augp.exists():
        pytest.skip("augment sidecar missing")
    with augp.open(encoding="utf-8") as fh:
        aug = json.load(fh)
    # Bridge has 1,400 alam→dia mappings; some collapse (multiple alam_ids → same DİA slug)
    # so augment count is in 1,200..1,400 range.
    assert 1100 <= len(aug) <= 1500, f"Track A count {len(aug)} outside expected band"


def test_e2_track_b_minted_count_within_band():
    """E2: Track-B minted records count is in the expected ~10,000-13,000 range."""
    persp = STATE_DIR / "el_alam_persons_pending.json"
    if not persp.exists():
        pytest.skip("Track B sidecar missing")
    with persp.open(encoding="utf-8") as fh:
        pers = json.load(fh)
    assert 9000 <= len(pers) <= 13000, (
        f"Track B mint count {len(pers)} outside expected band 9000..13000 "
        f"(13,940 alam entries minus ~1,300 Track A and ~1,300 skipped no-temporal)"
    )


# --------------------------------------------------------------------------- #
# F. Yâqūt person→place edge resolution (2 tests)
# --------------------------------------------------------------------------- #


def test_f1_yaqut_resolution_report_exists_and_sane():
    """F1: yaqut_persons_resolution_report.json exists and reports >=70% resolution
    via alam_id-tier-1 alone (the dominant strategy in Hafta 4 with the
    Alam-anchored sidecar)."""
    p = STATE_DIR / "yaqut_persons_resolution_report.json"
    assert p.exists(), "Resolution report not produced — pass_resolve_yaqut_persons not run?"
    with p.open(encoding="utf-8") as fh:
        rep = json.load(fh)
    total = rep.get("attestations_total", 0)
    if total == 0:
        pytest.skip("No attestations in sandbox (place namespace incomplete)")
    # Resolution rate must be >=70% — allow lower bound for sandbox where
    # only a few places exist.
    pct = rep.get("resolution_pct", 0)
    assert pct >= 70, f"Yâqūt resolution rate {pct}% below 70% threshold"


def test_f2_active_in_places_pids_valid(all_person_records):
    """F2: Every PID in person.active_in_places[] points to a real place file
    OR to one of the 7 sandbox samples (sandbox-tolerant)."""
    place_dir = REPO_ROOT / "data" / "canonical" / "place"
    on_disk = {pp.stem.replace("iac_place_", "iac:place-") for pp in place_dir.glob("iac_place_*.json")}
    bad = []
    for r in all_person_records:
        for ppid in (r.get("active_in_places") or []):
            if ppid not in on_disk:
                bad.append((r["@id"], ppid))
    assert not bad, f"{len(bad)} broken PID references in active_in_places[]: {bad[:5]}"


# --------------------------------------------------------------------------- #
# G. Counts and acceptance thresholds (4 tests)
# --------------------------------------------------------------------------- #


def test_g1_total_person_count_above_acceptance(all_person_records):
    """G1 (Acceptance K): ≥10,000 person records."""
    n = len(all_person_records)
    assert n >= 10_000, f"Only {n:,} person records — below K acceptance ({10_000:,})"


def test_g2_dia_derived_count_revised(all_person_records):
    """G2 (revised Acceptance N): ≥7,000 DİA-derived person records.

    NEXT_SESSION_PROMPT estimated 12,000-14,000; reality is 8,093 distinct DİA slugs of
    which ~7,400 carry biographical signal. We revised the threshold downward at
    Hafta 4 kickoff after the data inventory."""
    dia_count = 0
    for r in all_person_records:
        df = r.get("provenance", {}).get("derived_from", [])
        if any(d.get("source_id", "").startswith("dia:") for d in df):
            dia_count += 1
    assert dia_count >= 7_000, f"Only {dia_count:,} DİA-derived persons; below revised target 7,000"


def test_g3_bosworth_ruler_count_in_band(all_person_records):
    """G3 (Acceptance L proxy): Bosworth-derived ruler PIDs should be ~830 across
    all 186 dynasties when fully populated. In sandbox we have 7 dynasties so
    expect ~94 (the actual count of inline rulers across the 7 samples)."""
    bosworth_count = 0
    for r in all_person_records:
        df = r.get("provenance", {}).get("derived_from", [])
        if any(d.get("source_id", "").startswith("bosworth-nid:") for d in df):
            bosworth_count += 1
    n_dyn = len(list(DYNASTY_DIR.glob("*.json")))
    if n_dyn == 7:
        # Sandbox: 94 rulers across 7 sample dynasties
        assert 80 <= bosworth_count <= 110, f"Sandbox: expected ~94 Bosworth rulers, got {bosworth_count}"
    else:
        # Full: 830 across 186
        assert 700 <= bosworth_count <= 900, f"Full Mac: expected ~830 Bosworth rulers, got {bosworth_count}"


def test_g4_science_layer_full_seed(all_person_records):
    """G4 (Acceptance M proxy): All 182 science_layer scholars seeded as person records.
    (Wikidata reconciliation count is recon-mode dependent and only verifiable in
    --recon-mode auto on user's Mac.)"""
    sci_count = 0
    for r in all_person_records:
        df = r.get("provenance", {}).get("derived_from", [])
        if any(d.get("source_id", "").startswith("science-layer:") for d in df):
            sci_count += 1
    assert sci_count == 182, f"Expected 182 science_layer scholars, got {sci_count}"


# --------------------------------------------------------------------------- #
# Bonus: data quality spot checks (2 extra)
# --------------------------------------------------------------------------- #


def test_h1_alkhwarizmi_canonicalized():
    """H1 spot-check: Al-Khwarizmi (science_layer scholar_0001) seeded as person
    with mathematician+astronomer+geographer profession."""
    # The science_layer adapter's PID for scholar_0001 is the first PID minted
    # by science-layer (which runs after bosworth-rulers-fixup so 94 + 1 = 95)
    # but exact ordinal depends on run order. Simpler: scan for source_id 'science-layer:scholar_0001'.
    found = None
    for pp in PERSON_DIR.glob("iac_person_*.json"):
        with pp.open(encoding="utf-8") as fh:
            r = json.load(fh)
        sids = [d.get("source_id", "") for d in r.get("provenance", {}).get("derived_from", [])]
        if "science-layer:scholar_0001" in sids:
            found = r
            break
    assert found, "Al-Khwarizmi (scholar_0001) not found in person namespace"
    profs = set(found.get("profession") or [])
    assert "mathematician" in profs, f"Al-Khwarizmi profession missing 'mathematician': {profs}"
    assert "astronomer" in profs, f"Al-Khwarizmi profession missing 'astronomer': {profs}"
    death = (found.get("death_temporal") or {}).get("start_ce")
    assert death == 850, f"Al-Khwarizmi death year expected 850 CE, got {death}"


def test_h2_abubakr_promoted():
    """H2 spot-check: Abū Bakr (Râşidîn[0]) promoted to person and linked back
    to dynasty via had_ruler[]."""
    rashidun_path = DYNASTY_DIR / "iac_dynasty_00000001.json"
    if not rashidun_path.exists():
        pytest.skip("Rashidun dynasty not in sandbox")
    with rashidun_path.open(encoding="utf-8") as fh:
        rashidun = json.load(fh)
    had = rashidun.get("had_ruler") or []
    assert len(had) >= 4, f"Rashidun had_ruler should have ≥4 entries (Abu Bakr+Umar+Uthman+Ali); got {len(had)}"
    abubakr_pid = had[0]
    abubakr_path = PERSON_DIR / f"iac_person_{abubakr_pid.split('-')[1]}.json"
    assert abubakr_path.exists(), f"Abū Bakr person record not on disk at {abubakr_path}"
    with abubakr_path.open(encoding="utf-8") as fh:
        ab = json.load(fh)
    assert "iac:Ruler" in (ab.get("@type") or []), f"Abū Bakr @type missing iac:Ruler: {ab.get('@type')}"
    assert "iac:dynasty-00000001" in (ab.get("affiliated_dynasties") or []), (
        f"Abū Bakr not linked back to Rashidun dynasty: {ab.get('affiliated_dynasties')}"
    )


# --------------------------------------------------------------------------- #
# I. Hafta 4 patch — xref_alam audit + blacklist regression (1 extra)
# --------------------------------------------------------------------------- #


def test_i1_xref_alam_blacklist_present_and_used():
    """I1 (Hafta 4 patch): the science_layer xref_alam audit identified ~62
    alam_id values as unreliable (LOW_BAD or homonym-MEDIUM_name_only). The
    blacklist sidecar must exist and be honored by pass_resolve_yaqut_persons.

    Regression guard: prevents future code changes from silently restoring
    Tier-1 routing through known-bad bridges.
    """
    blacklist_path = STATE_DIR / "xref_alam_blacklist.json"
    assert blacklist_path.exists(), "xref_alam_blacklist.json missing — Hafta 4 patch regression"
    with blacklist_path.open(encoding="utf-8") as fh:
        bl = json.load(fh)
    blacklisted_ids = bl.get("blacklist_alam_ids", [])
    assert len(blacklisted_ids) >= 40, (
        f"Blacklist has only {len(blacklisted_ids)} entries; expected ≥40 (LOW_BAD ≥41 alone)"
    )

    # The verified.json sidecar should carry the audit detail
    verified_path = STATE_DIR / "science_layer_xref_alam_verified.json"
    assert verified_path.exists(), "science_layer_xref_alam_verified.json missing"
    with verified_path.open(encoding="utf-8") as fh:
        ver = json.load(fh)
    assert "LOW_BAD" in ver, "verified.json missing LOW_BAD bucket"
    # Spot-check: known LOW_BAD case (Mimar Sinan → 'Ammâr' which is a different person)
    sinan_low = any(e.get("scholar_id") == "scholar_0026" for e in ver.get("LOW_BAD", []))
    assert sinan_low, "scholar_0026 (Mimar Sinân) should be in LOW_BAD; audit may have regressed"
