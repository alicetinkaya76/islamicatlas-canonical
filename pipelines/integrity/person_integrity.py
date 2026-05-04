#!/usr/bin/env python3
"""
person_integrity.py — Pass-2 integrity for the person namespace (Hafta 4).

Five deferred-resolution passes:

1. EL-AʿLĀM AUGMENTATION (Track A merge)
   - Read data/_state/el_alam_augment_pending.json (1,280 entries keyed by DİA-derived person PID).
   - For each, append a derived_from entry to the existing person's provenance,
     add Ziriklī's Arabic heading to altLabel.ar (deduped), and append a
     record_history entry. Re-validate against person.schema.

2. BOSWORTH RULER PROMOTION (dual-write)
   - Read data/_state/bosworth_rulers_pending.json (entries keyed by dynasty PID).
   - For each dynasty, populate had_ruler[] (PID array, ordered by ruler_index)
     and write rulers[i].person_pid for each i.
   - Re-validate dynasty record against the patched dynasty.schema.

3. YÂQŪT NOTABLE_PERSONS RESOLUTION
   - Read data/_state/yaqut_persons_pending.json (606 places × 7,093 person attestations).
   - Build PersonIndex; resolve each Yâqūt person attestation to a person PID
     using:
        Tier-1: alam_id → DİA slug → existing person PID (via dia_to_alam_xref +
                el_alam_persons_pending sidecars)
        Tier-2: DİA URL match (dia_persons_pending sidecar)
        Tier-3: name (he/ht) + death_year ±2y match against PersonIndex
   - For each (person, place) edge resolved: append place_pid to
     person.active_in_places[]. Forward-only (Y4.4 decision).
   - Write resolution report.

4. SCIENCE-LAYER PLACE LINKING
   - Read data/_state/science_layer_active_places_pending.json (182 entries).
   - For each scholar, fuzzy-match birth_place.name and active_places[].name
     against the place namespace. Populate person.birth_place and
     person.active_in_places[].

5. DİA BIRTH/DEATH PLACE RESOLUTION
   - Read data/_state/dia_birth_death_places_pending.json (5,525 entries).
   - For each person with bp/dp string, fuzzy-match against the place namespace.
     Populate person.birth_place / person.death_place where match confidence is
     high; otherwise leave note hint.

Usage:
    python3 pipelines/integrity/person_integrity.py --augment-alam
    python3 pipelines/integrity/person_integrity.py --promote-rulers
    python3 pipelines/integrity/person_integrity.py --resolve-yaqut-persons
    python3 pipelines/integrity/person_integrity.py --link-science-places
    python3 pipelines/integrity/person_integrity.py --resolve-dia-places
    python3 pipelines/integrity/person_integrity.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import filename_for_pid  # noqa: E402

PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
DYNASTY_DIR = REPO_ROOT / "data" / "canonical" / "dynasty"
STATE_DIR = REPO_ROOT / "data" / "_state"
SCHEMAS_DIR = REPO_ROOT / "schemas"


# ============================================================================ #
# Helpers
# ============================================================================ #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_validator(schema_filename: str) -> Draft202012Validator:
    schemas: dict[str, dict] = {}
    for schema_path in SCHEMAS_DIR.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            s = json.load(fh)
        if s.get("$id"):
            schemas[s["$id"]] = s
    registry = Registry()
    for sid, s in schemas.items():
        registry = registry.with_resource(uri=sid, resource=Resource.from_contents(s))
    target_path = SCHEMAS_DIR / schema_filename
    with target_path.open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=registry)


def _load_record(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _save_record(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_state(name: str) -> dict:
    p = STATE_DIR / name
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def _write_report(name: str, payload: dict) -> None:
    p = STATE_DIR / name
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


# ============================================================================ #
# Person index — built on demand
# ============================================================================ #


class PersonIndex:
    """In-memory index of the person namespace.

    Multiple lookup keys per record:
      - dia_slug (from provenance.derived_from.source_id == "dia:<slug>")
      - alam_id (from provenance.derived_from.source_id == "el-alam:<id>"
        OR from note "alam_id=NNN")
      - normalised label (Arabic + Latin) → set of PIDs
      - normalised label + death_year_ce → set of PIDs (tighter Tier-3)
    """

    AR_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]")
    AR_PREFIX_AL_RE = re.compile(r"^ال")
    LATIN_PREFIX_AL_RE = re.compile(r"^(?:al|el|aL|eL)[ \-']", re.IGNORECASE)
    LATIN_PUNCT_RE = re.compile(r"[\-'\u02BE\u02BF\u02BC\u2018\u2019\u201C\u201D\.,;:]+")
    ALAM_ID_NOTE_RE = re.compile(r"alam_id=(\d+)")

    def __init__(self):
        self.pid_to_path: dict[str, Path] = {}
        self.pid_to_record: dict[str, dict] = {}
        self.dia_slug_to_pid: dict[str, str] = {}
        self.alam_id_to_pid: dict[int, str] = {}
        self.bosworth_id_to_pids: dict[str, list[str]] = defaultdict(list)
        # Multi-language label index
        self.label_to_pids: dict[str, set[str]] = defaultdict(set)
        # Tighter index: (label_norm, death_year_ce) → PIDs
        self.label_year_to_pids: dict[tuple[str, int], set[str]] = defaultdict(set)

    @classmethod
    def normalize_arabic(cls, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFKC", s)
        s = cls.AR_DIACRITICS_RE.sub("", s)
        s = cls.AR_PREFIX_AL_RE.sub("", s)
        return s.strip()

    @classmethod
    def normalize_latin(cls, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        s = cls.LATIN_PREFIX_AL_RE.sub("", s)
        s = cls.LATIN_PUNCT_RE.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _add_label(self, key: str, pid: str, death_year: int | None):
        if not key:
            return
        self.label_to_pids[key].add(pid)
        if death_year is not None:
            # Add with ±2y tolerance fanout
            for delta in (-2, -1, 0, 1, 2):
                self.label_year_to_pids[(key, death_year + delta)].add(pid)

    def add_record(self, record: dict, path: Path) -> None:
        pid = record.get("@id")
        if not pid:
            return
        self.pid_to_path[pid] = path
        self.pid_to_record[pid] = record

        # Source-id indexing
        prov = record.get("provenance") or {}
        for d in prov.get("derived_from") or []:
            sid = d.get("source_id") or ""
            if sid.startswith("dia:"):
                self.dia_slug_to_pid[sid[len("dia:"):]] = pid
            elif sid.startswith("el-alam:"):
                try:
                    aid = int(sid[len("el-alam:"):])
                    self.alam_id_to_pid[aid] = pid
                except ValueError:
                    pass
            elif sid.startswith("bosworth-nid:"):
                # e.g. "bosworth-nid:1:ruler:0"
                m = re.match(r"bosworth-nid:(\d+):ruler:(\d+)", sid)
                if m:
                    self.bosworth_id_to_pids[f"NID-{int(m.group(1)):03d}"].append(pid)

        # Note-mining for alam_id (Track A augment-only records do NOT carry
        # an "el-alam:NNN" source_id in provenance; instead the aid is set on
        # the augment_pending sidecar. Best-effort: if alam_id is in note, capture.)
        note = record.get("note") or ""
        for m in self.ALAM_ID_NOTE_RE.finditer(note):
            try:
                aid = int(m.group(1))
                # Only add if no entry yet (don't shadow el-alam:N source-id)
                if aid not in self.alam_id_to_pid:
                    self.alam_id_to_pid[aid] = pid
            except ValueError:
                pass

        # Death year (for tighter Tier-3 matching)
        death_year = (record.get("death_temporal") or {}).get("start_ce")

        # Label indexing
        labels = record.get("labels") or {}
        pref = labels.get("prefLabel") or {}
        for lang_key, val in pref.items():
            if not val:
                continue
            if lang_key == "ar":
                key = self.normalize_arabic(val)
            else:
                key = self.normalize_latin(val)
            self._add_label(key, pid, death_year)

        alt = labels.get("altLabel") or {}
        for lang_key, vals in alt.items():
            if not isinstance(vals, list):
                continue
            for v in vals:
                if not v:
                    continue
                if lang_key == "ar":
                    key = self.normalize_arabic(v)
                else:
                    key = self.normalize_latin(v)
                self._add_label(key, pid, death_year)

    @classmethod
    def build(cls) -> "PersonIndex":
        idx = cls()
        if not PERSON_DIR.exists():
            return idx
        for path in sorted(PERSON_DIR.glob("iac_person_*.json")):
            try:
                rec = _load_record(path)
            except (OSError, json.JSONDecodeError):
                continue
            idx.add_record(rec, path)
        return idx

    def resolve_alam_id(self, alam_id: int) -> str | None:
        return self.alam_id_to_pid.get(alam_id)

    def resolve_dia_slug(self, slug: str) -> str | None:
        return self.dia_slug_to_pid.get(slug)

    def resolve_by_label_year(self, name: str, death_year_ce: int | None) -> str | None:
        """Tier-3: name + death_year ±2y. Returns PID only if unique match."""
        for normalizer in (self.normalize_arabic, self.normalize_latin):
            key = normalizer(name)
            if not key:
                continue
            if death_year_ce is not None:
                pids = self.label_year_to_pids.get((key, death_year_ce), set())
                if len(pids) == 1:
                    return next(iter(pids))
                elif len(pids) > 1:
                    # Ambiguous; reject
                    return None
            # Fallback: name-only (lower confidence)
            pids = self.label_to_pids.get(key, set())
            if len(pids) == 1:
                return next(iter(pids))
        return None


# ============================================================================ #
# Place index — light version for person→place resolution
# ============================================================================ #


class PlaceIndex:
    AR_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]")
    AR_PREFIX_AL_RE = re.compile(r"^ال")
    LATIN_PREFIX_AL_RE = re.compile(r"^(?:al|el|aL|eL)[ \-']", re.IGNORECASE)
    LATIN_PUNCT_RE = re.compile(r"[\-'\u02BE\u02BF\u02BC\u2018\u2019\u201C\u201D\.,;:]+")

    def __init__(self):
        self.pid_to_path: dict[str, Path] = {}
        self.label_to_pids: dict[str, set[str]] = defaultdict(set)
        self.yaqut_id_to_pid: dict[int, str] = {}

    @classmethod
    def normalize_arabic(cls, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFKC", s)
        s = cls.AR_DIACRITICS_RE.sub("", s)
        s = cls.AR_PREFIX_AL_RE.sub("", s)
        return s.strip()

    @classmethod
    def normalize_latin(cls, s: str) -> str:
        if not s:
            return ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.lower()
        s = cls.LATIN_PREFIX_AL_RE.sub("", s)
        s = cls.LATIN_PUNCT_RE.sub("", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def add_record(self, record: dict, path: Path) -> None:
        pid = record.get("@id")
        if not pid:
            return
        self.pid_to_path[pid] = path

        # Yâqūt id index
        ycurie = record.get("yaqut_id")
        if ycurie and isinstance(ycurie, str) and ycurie.startswith("yaqut:"):
            try:
                yid = int(ycurie[len("yaqut:"):])
                self.yaqut_id_to_pid[yid] = pid
            except ValueError:
                pass
        prov = record.get("provenance") or {}
        for d in prov.get("derived_from") or []:
            sid = d.get("source_id") or ""
            if sid.startswith("yaqut:"):
                try:
                    yid = int(sid[len("yaqut:"):])
                    self.yaqut_id_to_pid[yid] = pid
                except ValueError:
                    pass

        labels = record.get("labels") or {}
        for bucket_name in ("prefLabel", "altLabel"):
            bucket = labels.get(bucket_name) or {}
            for lang_key, val in bucket.items():
                if val is None:
                    continue
                vals = val if isinstance(val, list) else [val]
                for v in vals:
                    if not v:
                        continue
                    if lang_key == "ar":
                        key = self.normalize_arabic(str(v))
                    else:
                        key = self.normalize_latin(str(v))
                    if key:
                        self.label_to_pids[key].add(pid)

    @classmethod
    def build(cls) -> "PlaceIndex":
        idx = cls()
        if not PLACE_DIR.exists():
            return idx
        for path in sorted(PLACE_DIR.glob("iac_place_*.json")):
            try:
                rec = _load_record(path)
            except (OSError, json.JSONDecodeError):
                continue
            idx.add_record(rec, path)
        return idx

    def lookup(self, name: str) -> str | None:
        """Lookup by label across both normalizations. Returns PID iff unique."""
        if not name:
            return None
        for normalizer in (self.normalize_arabic, self.normalize_latin):
            key = normalizer(name)
            if not key:
                continue
            pids = self.label_to_pids.get(key, set())
            if len(pids) == 1:
                return next(iter(pids))
        return None

    def lookup_yaqut(self, yaqut_id: int) -> str | None:
        return self.yaqut_id_to_pid.get(yaqut_id)


# ============================================================================ #
# Pass 1 — El-Aʿlām augmentation (Track A merge)
# ============================================================================ #


def pass_augment_alam(strict: bool = False) -> dict:
    pending = _load_state("el_alam_augment_pending.json")
    if not pending:
        return {"applied": 0, "skipped_missing_record": 0, "validation_failures": 0}

    validator = _load_validator("person.schema.json")
    applied = 0
    skipped = 0
    failures: list[tuple[str, str]] = []

    for pid, alam in pending.items():
        path = PERSON_DIR / filename_for_pid(pid)
        if not path.exists():
            skipped += 1
            continue
        record = _load_record(path)

        # Append derived_from entry for el-alam
        prov = record.get("provenance") or {}
        df = prov.get("derived_from") or []
        # Skip if already has an el-alam derived_from
        if any(d.get("source_id", "").startswith("el-alam:") for d in df):
            continue
        df.append({
            "source_id": f"el-alam:{alam.get('alam_id')}",
            "source_type": "tertiary_reference",
            "page_or_locator": (
                f"al-Ziriklī, al-Aʿlām, alam_id={alam.get('alam_id')}, "
                f"heading_ar={alam.get('heading_ar')}"
            ),
            "extraction_method": "structured_json",
            "edition_or_version": (
                "Khayr al-Dīn al-Ziriklī, al-Aʿlām (Beirut: Dār al-ʿIlm li’l-Malāyīn, "
                "8th ed. 2002), 8 vols."
            ),
        })
        prov["derived_from"] = df
        prov["modified"] = _now_iso()
        rh = prov.get("record_history") or []
        rh.append({
            "change_type": "update",
            "changed_at": _now_iso(),
            "changed_by": "https://orcid.org/0000-0002-7747-6854",
            "release": "v0.1.0-phase0",
            "note": (
                f"El-Aʿlām augmentation: linked alam_id={alam.get('alam_id')} "
                f"(heading_ar={alam.get('heading_ar')}) via Track A "
                f"(DİA→Alam xref bridge). dt={(alam.get('description_tr') or '')[:80]}"
            ),
        })
        prov["record_history"] = rh
        record["provenance"] = prov

        # altLabel.ar — add Ziriklī's heading_ar if not duplicate
        labels = record.get("labels") or {}
        alt = labels.get("altLabel") or {}
        ar_alts = alt.get("ar") or []
        h_ar = alam.get("heading_ar")
        if h_ar and h_ar.strip():
            existing_norm = {PersonIndex.normalize_arabic(x) for x in ar_alts}
            existing_norm.add(PersonIndex.normalize_arabic(
                (record.get("labels", {}).get("prefLabel", {}).get("ar") or "")
            ))
            if PersonIndex.normalize_arabic(h_ar) not in existing_norm:
                ar_alts.append(h_ar.strip())
                alt["ar"] = ar_alts[:20]
                labels["altLabel"] = alt
                record["labels"] = labels

        # Note: append Alam reference text
        note_old = record.get("note") or ""
        alam_note = (
            f"El-Aʿlām (Track A) augmentation: alam_id={alam.get('alam_id')}, "
            f"heading_ar={h_ar}, dt={(alam.get('description_tr') or '')[:200]}"
        )
        # Avoid duplicate appends on re-run
        if alam_note not in note_old:
            new_note = (note_old + " || " + alam_note).strip(" |") if note_old else alam_note
            record["note"] = new_note[:5000]

        errors = list(validator.iter_errors(record))
        if errors:
            top = errors[0]
            failures.append((pid, f"[{'.'.join(str(x) for x in top.absolute_path) or '<root>'}] {top.message[:200]}"))
            if strict:
                break
            continue

        _save_record(path, record)
        applied += 1

    report = {
        "pass": "augment_alam",
        "applied": applied,
        "skipped_missing_record": skipped,
        "validation_failures": len(failures),
        "failure_examples": failures[:10],
    }
    _write_report("el_alam_augment_report.json", report)
    return report


# ============================================================================ #
# Pass 2 — Bosworth ruler dual-write (rulers[].person_pid + had_ruler[])
# ============================================================================ #


def pass_promote_rulers(strict: bool = False) -> dict:
    pending = _load_state("bosworth_rulers_pending.json")
    if not pending:
        return {"applied": 0, "validation_failures": 0}

    validator = _load_validator("dynasty.schema.json")
    applied = 0
    failures: list[tuple[str, str]] = []

    for dynasty_pid, ruler_entries in pending.items():
        dpath = DYNASTY_DIR / filename_for_pid(dynasty_pid)
        if not dpath.exists():
            continue
        record = _load_record(dpath)

        rulers = record.get("rulers") or []
        # Sort entries by ruler_index for deterministic ordering
        entries_sorted = sorted(ruler_entries, key=lambda e: e.get("ruler_index", 0))

        # Build had_ruler[] from entries (skip duplicates while preserving order)
        had = []
        seen = set()
        for e in entries_sorted:
            ppid = e.get("person_pid")
            if ppid and ppid not in seen:
                had.append(ppid)
                seen.add(ppid)

        record["had_ruler"] = had

        # Dual-write: write rulers[i].person_pid for each promoted ruler
        for e in entries_sorted:
            i = e.get("ruler_index")
            if i is None or i >= len(rulers):
                continue
            ppid = e.get("person_pid")
            if ppid:
                rulers[i]["person_pid"] = ppid
        record["rulers"] = rulers

        # Append record_history entry
        prov = record.get("provenance") or {}
        prov["modified"] = _now_iso()
        rh = prov.get("record_history") or []
        rh.append({
            "change_type": "update",
            "changed_at": _now_iso(),
            "changed_by": "https://orcid.org/0000-0002-7747-6854",
            "release": "v0.1.0-phase0",
            "note": (
                f"Hafta 4 ruler promotion: had_ruler[] populated with {len(had)} PID(s); "
                f"rulers[i].person_pid dual-write applied. Inline rulers[] retained "
                f"for UI continuity per Y4.2(c) decision; P0.2 cutover removes inline."
            ),
        })
        prov["record_history"] = rh
        record["provenance"] = prov

        errors = list(validator.iter_errors(record))
        if errors:
            top = errors[0]
            failures.append((dynasty_pid, f"[{'.'.join(str(x) for x in top.absolute_path) or '<root>'}] {top.message[:200]}"))
            if strict:
                break
            continue

        _save_record(dpath, record)
        applied += 1

    report = {
        "pass": "promote_rulers",
        "applied": applied,
        "validation_failures": len(failures),
        "failure_examples": failures[:10],
    }
    _write_report("bosworth_rulers_promotion_report.json", report)
    return report


# ============================================================================ #
# Pass 3 — Yâqūt notable_persons resolution (place ↔ person edge)
# ============================================================================ #


def pass_resolve_yaqut_persons(strict: bool = False) -> dict:
    pending = _load_state("yaqut_persons_pending.json")
    if not pending:
        return {"applied": 0}

    person_idx = PersonIndex.build()
    place_idx = PlaceIndex.build()
    validator = _load_validator("person.schema.json")

    # Build dia_to_alam_xref reverse map: alam_id → DİA-derived person PID.
    # The DİA adapter already populated dia_to_alam_xref.json (PID → {alam_id, slug}).
    dia_xref = _load_state("dia_to_alam_xref.json")
    alam_to_dia_pid: dict[int, str] = {}
    for pid, info in dia_xref.items():
        aid = info.get("alam_id")
        if aid is not None:
            try:
                alam_to_dia_pid[int(aid)] = pid
            except (TypeError, ValueError):
                pass

    # Load xref_alam blacklist (Hafta 4 patch): science_layer's xref_alam field
    # was found to be ~35% wrong on inspection (homonym confusions, batch-processing
    # errors). The blacklist enumerates alam_id values that should NOT be trusted
    # as a Tier-1 routing key, even though they appear in dia_to_alam_xref.json.
    # See data/_state/science_layer_xref_alam_verified.json for the audit trail.
    blacklist_data = _load_state("xref_alam_blacklist.json")
    blacklist_alam_ids: set[int] = set(blacklist_data.get("blacklist_alam_ids", []))

    # Resolution counters
    n_attestations_total = 0
    n_resolved_alam = 0
    n_resolved_dia_slug = 0
    n_resolved_label_year = 0
    n_unresolved = 0
    n_blacklisted = 0

    # Collect updates per person: PID → set of place PIDs
    person_updates: dict[str, set[str]] = defaultdict(set)
    sample_unresolved: list[dict] = []

    for place_pid, block in pending.items():
        # place_pid in pending sidecar is the iac:place-NNNNNNNN; sometimes the
        # sidecar key was stored as a yaqut numeric id — handle both shapes.
        if not place_pid.startswith("iac:place-"):
            # Try yaqut_id-based lookup
            yid_str = block.get("yaqut_id")
            if yid_str is not None:
                resolved = place_idx.lookup_yaqut(int(yid_str))
                if resolved:
                    place_pid = resolved
                else:
                    continue
            else:
                continue

        if place_pid not in place_idx.pid_to_path:
            # The sandbox build only contains 7 sample places; real Mac run will
            # have all 15,239. Skip silently.
            continue

        for p in block.get("persons") or []:
            n_attestations_total += 1
            aid = p.get("id")
            try:
                aid_int = int(aid) if aid is not None else None
            except (TypeError, ValueError):
                aid_int = None

            person_pid = None
            tier = None

            # Tier-1: alam_id direct (with blacklist guard)
            if aid_int is not None:
                if aid_int in blacklist_alam_ids:
                    # This alam_id was found unreliable in the science_layer
                    # xref audit (Hafta 4 patch). Fall through to Tier-2/3.
                    n_blacklisted += 1
                else:
                    person_pid = (
                        person_idx.resolve_alam_id(aid_int)
                        or alam_to_dia_pid.get(aid_int)
                    )
                    if person_pid:
                        tier = "alam_id"
                        n_resolved_alam += 1

            # Tier-2: DİA URL embedded slug
            if not person_pid:
                dia_url = p.get("dia") or ""
                m = re.search(r"islamansiklopedisi\.org\.tr/([\w\-]+)", dia_url)
                if m:
                    slug = m.group(1)
                    person_pid = person_idx.resolve_dia_slug(slug)
                    if person_pid:
                        tier = "dia_slug"
                        n_resolved_dia_slug += 1

            # Tier-3: name + death_year ±2y
            if not person_pid:
                death_y = p.get("dm")
                # he is ALA-LC (Latin); ht is Turkish transliteration
                for nm in (p.get("he"), p.get("ht")):
                    if not nm:
                        continue
                    cand = person_idx.resolve_by_label_year(nm, death_y)
                    if cand:
                        person_pid = cand
                        tier = "label_year"
                        n_resolved_label_year += 1
                        break

            if person_pid:
                person_updates[person_pid].add(place_pid)
            else:
                n_unresolved += 1
                if len(sample_unresolved) < 30:
                    sample_unresolved.append({
                        "alam_id": aid_int,
                        "he": p.get("he"),
                        "ht": p.get("ht"),
                        "dm": p.get("dm"),
                        "place_pid": place_pid,
                    })

    # Apply person.active_in_places[] updates
    n_persons_updated = 0
    n_validation_failures = 0
    for ppid, place_pids in person_updates.items():
        ppath = PERSON_DIR / filename_for_pid(ppid)
        if not ppath.exists():
            continue
        record = _load_record(ppath)
        existing = set(record.get("active_in_places") or [])
        new_set = existing | place_pids
        if new_set == existing:
            continue
        record["active_in_places"] = sorted(new_set)
        prov = record.get("provenance") or {}
        prov["modified"] = _now_iso()
        rh = prov.get("record_history") or []
        rh.append({
            "change_type": "update",
            "changed_at": _now_iso(),
            "changed_by": "https://orcid.org/0000-0002-7747-6854",
            "release": "v0.1.0-phase0",
            "note": (
                f"Hafta 4 person→place resolution: {len(new_set - existing)} new active_in_places "
                f"PID(s) added from Yâqūt notable_persons sidecar."
            ),
        })
        prov["record_history"] = rh
        record["provenance"] = prov
        errors = list(validator.iter_errors(record))
        if errors:
            n_validation_failures += 1
            if strict:
                break
            continue
        _save_record(ppath, record)
        n_persons_updated += 1

    report = {
        "pass": "resolve_yaqut_persons",
        "attestations_total": n_attestations_total,
        "resolved_via_alam_id": n_resolved_alam,
        "resolved_via_dia_slug": n_resolved_dia_slug,
        "resolved_via_label_year": n_resolved_label_year,
        "blacklisted_alam_id_skipped": n_blacklisted,
        "unresolved": n_unresolved,
        "resolution_pct": round(
            100 * (n_resolved_alam + n_resolved_dia_slug + n_resolved_label_year)
            / max(1, n_attestations_total), 1
        ),
        "persons_updated": n_persons_updated,
        "validation_failures": n_validation_failures,
        "sample_unresolved": sample_unresolved,
    }
    _write_report("yaqut_persons_resolution_report.json", report)
    return report


# ============================================================================ #
# Pass 4 — Science layer place linking (birth_place + active_places strings)
# ============================================================================ #


def pass_link_science_places(strict: bool = False) -> dict:
    pending = _load_state("science_layer_active_places_pending.json")
    if not pending:
        return {"applied": 0}

    place_idx = PlaceIndex.build()
    validator = _load_validator("person.schema.json")

    n_birth_resolved = 0
    n_active_resolved = 0
    n_birth_unresolved = 0
    n_active_unresolved = 0
    n_persons_updated = 0
    n_validation_failures = 0

    for ppid, block in pending.items():
        ppath = PERSON_DIR / filename_for_pid(ppid)
        if not ppath.exists():
            continue
        record = _load_record(ppath)
        changed = False

        # birth_place
        bp = block.get("birth_place") or {}
        bp_name = (bp.get("name") or {}).get("en") if isinstance(bp.get("name"), dict) else bp.get("name")
        if bp_name and "birth_place" not in record:
            cand = place_idx.lookup(bp_name)
            if cand:
                record["birth_place"] = cand
                n_birth_resolved += 1
                changed = True
            else:
                # Also try TR / AR
                tr = (bp.get("name") or {}).get("tr") if isinstance(bp.get("name"), dict) else None
                ar = (bp.get("name") or {}).get("ar") if isinstance(bp.get("name"), dict) else None
                cand = (tr and place_idx.lookup(tr)) or (ar and place_idx.lookup(ar))
                if cand:
                    record["birth_place"] = cand
                    n_birth_resolved += 1
                    changed = True
                else:
                    n_birth_unresolved += 1

        # active_in_places
        new_active = set(record.get("active_in_places") or [])
        before = len(new_active)
        for ap in (block.get("active_places") or []):
            ap_name = ap.get("name") or {}
            for lang in ("en", "tr", "ar"):
                nm = ap_name.get(lang) if isinstance(ap_name, dict) else (ap_name if isinstance(ap_name, str) else None)
                if nm:
                    cand = place_idx.lookup(nm)
                    if cand:
                        new_active.add(cand)
                        n_active_resolved += 1
                        break
            else:
                n_active_unresolved += 1
        if len(new_active) > before:
            record["active_in_places"] = sorted(new_active)
            changed = True

        if not changed:
            continue

        prov = record.get("provenance") or {}
        prov["modified"] = _now_iso()
        rh = prov.get("record_history") or []
        rh.append({
            "change_type": "update",
            "changed_at": _now_iso(),
            "changed_by": "https://orcid.org/0000-0002-7747-6854",
            "release": "v0.1.0-phase0",
            "note": "Hafta 4 science_layer place linking: birth_place / active_in_places resolved against Yâqūt-derived place namespace.",
        })
        prov["record_history"] = rh
        record["provenance"] = prov

        errors = list(validator.iter_errors(record))
        if errors:
            n_validation_failures += 1
            if strict:
                break
            continue
        _save_record(ppath, record)
        n_persons_updated += 1

    report = {
        "pass": "link_science_places",
        "birth_resolved": n_birth_resolved,
        "active_resolved": n_active_resolved,
        "birth_unresolved": n_birth_unresolved,
        "active_unresolved": n_active_unresolved,
        "persons_updated": n_persons_updated,
        "validation_failures": n_validation_failures,
    }
    _write_report("science_layer_place_linking_report.json", report)
    return report


# ============================================================================ #
# Pass 5 — DİA bp/dp string → place PID resolution
# ============================================================================ #


def pass_resolve_dia_places(strict: bool = False) -> dict:
    pending = _load_state("dia_birth_death_places_pending.json")
    if not pending:
        return {"applied": 0}

    place_idx = PlaceIndex.build()
    validator = _load_validator("person.schema.json")

    n_birth_resolved = 0
    n_death_resolved = 0
    n_unresolved = 0
    n_persons_updated = 0
    n_validation_failures = 0

    for ppid, block in pending.items():
        ppath = PERSON_DIR / filename_for_pid(ppid)
        if not ppath.exists():
            continue
        record = _load_record(ppath)
        changed = False

        bp_str = block.get("birth_place_string") or ""
        dp_str = block.get("death_place_string") or ""

        if bp_str and "birth_place" not in record:
            cand = place_idx.lookup(bp_str)
            if cand:
                record["birth_place"] = cand
                n_birth_resolved += 1
                changed = True
            else:
                n_unresolved += 1

        if dp_str and "death_place" not in record:
            cand = place_idx.lookup(dp_str)
            if cand:
                record["death_place"] = cand
                n_death_resolved += 1
                changed = True
            else:
                n_unresolved += 1

        if not changed:
            continue

        prov = record.get("provenance") or {}
        prov["modified"] = _now_iso()
        rh = prov.get("record_history") or []
        rh.append({
            "change_type": "update",
            "changed_at": _now_iso(),
            "changed_by": "https://orcid.org/0000-0002-7747-6854",
            "release": "v0.1.0-phase0",
            "note": "Hafta 4 DİA place resolution: birth_place / death_place string matched to place namespace.",
        })
        prov["record_history"] = rh
        record["provenance"] = prov

        errors = list(validator.iter_errors(record))
        if errors:
            n_validation_failures += 1
            if strict:
                break
            continue
        _save_record(ppath, record)
        n_persons_updated += 1

    report = {
        "pass": "resolve_dia_places",
        "birth_resolved": n_birth_resolved,
        "death_resolved": n_death_resolved,
        "unresolved": n_unresolved,
        "persons_updated": n_persons_updated,
        "validation_failures": n_validation_failures,
    }
    _write_report("dia_places_resolution_report.json", report)
    return report


# ============================================================================ #
# CLI
# ============================================================================ #


def main() -> int:
    parser = argparse.ArgumentParser(description="Person namespace integrity passes (Hafta 4).")
    parser.add_argument("--augment-alam", action="store_true")
    parser.add_argument("--promote-rulers", action="store_true")
    parser.add_argument("--resolve-yaqut-persons", action="store_true")
    parser.add_argument("--link-science-places", action="store_true")
    parser.add_argument("--resolve-dia-places", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.all:
        args.augment_alam = True
        args.promote_rulers = True
        args.resolve_yaqut_persons = True
        args.link_science_places = True
        args.resolve_dia_places = True

    rc = 0
    if args.augment_alam:
        r = pass_augment_alam(strict=args.strict)
        print(f"[augment_alam] applied={r['applied']} skipped={r.get('skipped_missing_record', 0)} fail={r['validation_failures']}")
        if r["validation_failures"] and args.strict:
            rc = 1
    if args.promote_rulers:
        r = pass_promote_rulers(strict=args.strict)
        print(f"[promote_rulers] applied={r['applied']} fail={r['validation_failures']}")
        if r["validation_failures"] and args.strict:
            rc = 1
    if args.resolve_yaqut_persons:
        r = pass_resolve_yaqut_persons(strict=args.strict)
        print(f"[resolve_yaqut_persons] attestations={r['attestations_total']} "
              f"alam_id={r['resolved_via_alam_id']} dia_slug={r['resolved_via_dia_slug']} "
              f"label_year={r['resolved_via_label_year']} unresolved={r['unresolved']} "
              f"resolution={r['resolution_pct']}% persons_updated={r['persons_updated']} "
              f"fail={r['validation_failures']}")
    if args.link_science_places:
        r = pass_link_science_places(strict=args.strict)
        print(f"[link_science_places] birth={r['birth_resolved']} active={r['active_resolved']} "
              f"persons={r['persons_updated']} fail={r['validation_failures']}")
    if args.resolve_dia_places:
        r = pass_resolve_dia_places(strict=args.strict)
        print(f"[resolve_dia_places] birth={r['birth_resolved']} death={r['death_resolved']} "
              f"persons={r['persons_updated']} fail={r['validation_failures']}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
