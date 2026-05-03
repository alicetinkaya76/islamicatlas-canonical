#!/usr/bin/env python3
"""
place_integrity.py — Pass-2 integrity for the place namespace.

Three deferred-resolution passes:

1. PARENT-LOCATION RESOLUTION (Yâqūt parent_locations → located_in[])
   - Read data/_state/yaqut_parent_pending.json
   - For each entry (PID, parent_locations[]), fuzzy-match each parent name
     against the place store's labels (prefLabel.ar / prefLabel.tr / prefLabel.en
     / altLabel.*). Use a heading-normalized dictionary lookup first
     (fastest), fall back to fuzzy match.
   - When a match is found, append the matched PID to the source record's
     located_in[] field; re-validate against place schema.
   - Write a resolution report at data/_state/yaqut_parent_resolution_report.json
     enumerating successes and failures.

2. MUQADDASĪ ↔ YÂQŪT MERGE
   - Read data/_state/muqaddasi_yaqut_xref_pending.json (1,081 entries from
     muqaddasi_xref.json mapping muq-NNNN → yaqut_id).
   - For each entry, the muqaddasi PID and the yaqut PID currently exist
     as TWO separate canonical records. We don't delete or rename PIDs
     (Phase 0 invariant — PIDs are immutable). Instead we apply BIDIRECTIONAL
     attestation:
       muqaddasi record:  derived_from_layers += "yaqut" (already had "makdisi")
                          note += cross-reference to yaqut PID
       yaqut record:      derived_from_layers += "makdisi"
                          note += cross-reference to muqaddasi PID
   - This is the place-layer equivalent of the Bosworth dynasty_relations
     bidirectional invariant. A future Phase 0.5 ResolverV2 pass will
     consolidate these into single PIDs via SAME-AS chains.

3. LE STRANGE AUGMENTATION
   - Read data/_state/le_strange_yaqut_augment_pending.json (218 entries
     keyed by 'yaqut:N').
   - For each, find the corresponding Yâqūt PID via the index, then update:
       derived_from_layers += "le-strange"
       labels.altLabel.en += [le_strange_form, alternate_names...]
       provenance.derived_from += new entry for Le Strange
       note += chapter/page locator + Le Strange description
   - Validate the modified record against place.schema.json.

Usage:
    python3 pipelines/integrity/place_integrity.py --resolve-parents
    python3 pipelines/integrity/place_integrity.py --merge-muqaddasi
    python3 pipelines/integrity/place_integrity.py --augment-lestrange
    python3 pipelines/integrity/place_integrity.py --all       # all three
    python3 pipelines/integrity/place_integrity.py --strict    # exit 1 on errors
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
from typing import Iterator

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.pid_minter import filename_for_pid  # noqa: E402

PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
STATE_DIR = REPO_ROOT / "data" / "_state"
SCHEMAS_DIR = REPO_ROOT / "schemas"
PLACE_SCHEMA = SCHEMAS_DIR / "place.schema.json"


# ============================================================================
# Place index — built on demand; maps multiple keys → PID
# ============================================================================


class PlaceIndex:
    """In-memory index of the place namespace.

    Built keys (per record):
      - pid → record path
      - normalized prefLabel.ar → PID set
      - normalized prefLabel.tr → PID set
      - normalized prefLabel.en → PID set
      - normalized altLabel.* values → PID set
      - source curies: yaqut:N, muqaddasi:muq-NNNN, le-strange:N → PID set

    Normalization:
      - lowercase, strip Arabic diacritics + Latin combining marks
      - drop al-/el-/El-/AL- prefixes
      - drop punctuation (apostrophes, hyphens, etc.) for Latin script
      - Arabic: drop tashkīl (U+064B-U+0652) and shadda
    """

    AR_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u0653\u0654\u0655]")
    AR_PREFIX_AL_RE = re.compile(r"^ال")
    LATIN_PREFIX_AL_RE = re.compile(r"^(?:al|el|aL|eL)[ \-']", re.IGNORECASE)
    LATIN_PUNCT_RE = re.compile(r"[\-'\u02BE\u02BF\u02BC\u2018\u2019\u201C\u201D\.,;:]+")

    def __init__(self):
        self.pid_to_path: dict[str, Path] = {}
        self.label_to_pids: dict[str, set[str]] = defaultdict(set)
        self.curie_to_pid: dict[str, str] = {}

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

        labels = record.get("labels") or {}
        pref = labels.get("prefLabel") or {}

        for lang_key, val in pref.items():
            if not val:
                continue
            if lang_key == "ar" or lang_key == "ar-Latn-x-alalc":
                key = self.normalize_arabic(val) if lang_key == "ar" else self.normalize_latin(val)
            else:
                key = self.normalize_latin(val)
            if key:
                self.label_to_pids[key].add(pid)

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
                if key:
                    self.label_to_pids[key].add(pid)

        # Source CURIE indexing (yaqut_id, plus provenance.derived_from.source_id)
        if record.get("yaqut_id"):
            self.curie_to_pid[record["yaqut_id"]] = pid
        prov = record.get("provenance") or {}
        for d in prov.get("derived_from") or []:
            sid = d.get("source_id")
            if sid:
                self.curie_to_pid[sid] = pid

    @classmethod
    def build(cls) -> "PlaceIndex":
        idx = cls()
        if not PLACE_DIR.exists():
            return idx
        for path in PLACE_DIR.glob("iac_place_*.json"):
            try:
                with path.open(encoding="utf-8") as fh:
                    record = json.load(fh)
            except (OSError, json.JSONDecodeError):
                continue
            idx.add_record(record, path)
        return idx

    def lookup_arabic(self, name: str) -> set[str]:
        return self.label_to_pids.get(self.normalize_arabic(name), set())

    def lookup_latin(self, name: str) -> set[str]:
        return self.label_to_pids.get(self.normalize_latin(name), set())

    def lookup_any(self, name: str) -> set[str]:
        # Try both normalizations
        return self.lookup_arabic(name) | self.lookup_latin(name)

    def lookup_curie(self, curie: str) -> str | None:
        return self.curie_to_pid.get(curie)


# ============================================================================
# Helpers
# ============================================================================


def _now_iso() -> str:
    return (datetime.now(timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _load_validator() -> Draft202012Validator:
    schemas: dict[str, dict] = {}
    for schema_path in SCHEMAS_DIR.rglob("*.schema.json"):
        with schema_path.open(encoding="utf-8") as fh:
            s = json.load(fh)
        if s.get("$id"):
            schemas[s["$id"]] = s
    registry = Registry()
    for sid, s in schemas.items():
        registry = registry.with_resource(uri=sid, resource=Resource.from_contents(s))
    with PLACE_SCHEMA.open(encoding="utf-8") as fh:
        target = json.load(fh)
    return Draft202012Validator(target, registry=registry)


def _load_record(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _save_record(path: Path, record: dict) -> None:
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_record_history(record: dict, change_type: str, note: str,
                            attributed_to: str = "https://orcid.org/0000-0002-7747-6854",
                            release: str = "v0.1.0-phase0") -> None:
    prov = record.setdefault("provenance", {})
    history = prov.setdefault("record_history", [])
    history.append({
        "change_type": change_type,
        "changed_at": _now_iso(),
        "changed_by": attributed_to,
        "release": release,
        "note": note[:1000],
    })
    prov["modified"] = _now_iso()


# ============================================================================
# Pass 1: parent_locations → located_in[]
# ============================================================================


def resolve_parents(strict: bool = False) -> tuple[int, int, int]:
    sidecar_path = STATE_DIR / "yaqut_parent_pending.json"
    if not sidecar_path.exists():
        print(f"  no parent sidecar at {sidecar_path}; skipping")
        return 0, 0, 0

    with sidecar_path.open(encoding="utf-8") as fh:
        pending = json.load(fh)

    if not pending:
        print(f"  parent sidecar empty; nothing to resolve")
        return 0, 0, 0

    print(f"  building place index for parent resolution ...")
    idx = PlaceIndex.build()
    validator = _load_validator()

    n_resolved = 0
    n_partial = 0
    n_failed = 0
    n_errors = 0
    report: dict[str, dict] = {}
    ambiguous_log: list[dict] = []

    for pid, info in pending.items():
        path = idx.pid_to_path.get(pid)
        if not path:
            n_errors += 1
            continue

        parent_names = info.get("parent_locations") or []
        if not parent_names:
            continue

        record = _load_record(path)
        located_in = list(record.get("located_in") or [])
        prior_count = len(located_in)
        resolved_pids = []
        unresolved_names = []
        ambiguous_names = []

        for pname in parent_names:
            candidates = idx.lookup_any(pname)
            # Drop self-reference (a place can't be its own parent)
            candidates.discard(pid)
            if len(candidates) == 1:
                resolved_pids.append(next(iter(candidates)))
            elif len(candidates) > 1:
                # Pick deterministically (lowest PID); record ambiguity
                pick = min(candidates)
                resolved_pids.append(pick)
                ambiguous_names.append({"parent": pname, "candidates": sorted(candidates), "picked": pick})
            else:
                unresolved_names.append(pname)

        # Dedupe + add
        for rp in resolved_pids:
            if rp not in located_in and rp != pid:
                located_in.append(rp)

        if len(located_in) > prior_count:
            record["located_in"] = located_in
            _append_record_history(
                record,
                change_type="update",
                note=(f"located_in[] populated by integrity pass from "
                      f"parent_locations={parent_names!r}; "
                      f"resolved {len(resolved_pids)}/{len(parent_names)}, "
                      f"unresolved={unresolved_names!r}"),
            )
            errs = list(validator.iter_errors(record))
            if errs:
                n_errors += 1
                if strict:
                    raise RuntimeError(
                        f"validation failed after located_in update for {pid}: {errs[0].message}"
                    )
            else:
                _save_record(path, record)
                if unresolved_names:
                    n_partial += 1
                else:
                    n_resolved += 1
        else:
            n_failed += 1

        report[pid] = {
            "parent_locations": parent_names,
            "resolved_count": len(resolved_pids),
            "unresolved": unresolved_names,
            "ambiguous": ambiguous_names,
        }
        if ambiguous_names:
            ambiguous_log.append({"pid": pid, "ambiguous": ambiguous_names})

    # Persist report
    report_path = STATE_DIR / "yaqut_parent_resolution_report.json"
    report_path.write_text(
        json.dumps({
            "summary": {
                "total_pending": len(pending),
                "fully_resolved": n_resolved,
                "partially_resolved": n_partial,
                "failed": n_failed,
                "validation_errors": n_errors,
            },
            "ambiguous": ambiguous_log[:200],
            "details": report,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"  resolved={n_resolved}, partial={n_partial}, failed={n_failed}, errors={n_errors}")
    print(f"  report: {report_path.relative_to(REPO_ROOT)}")
    return n_resolved + n_partial, n_errors, n_failed


# ============================================================================
# Pass 2: Muqaddasī ↔ Yâqūt bidirectional attestation
# ============================================================================


def merge_muqaddasi_yaqut(strict: bool = False) -> tuple[int, int]:
    sidecar_path = STATE_DIR / "muqaddasi_yaqut_xref_pending.json"
    if not sidecar_path.exists():
        print(f"  no muqaddasi sidecar at {sidecar_path}; skipping")
        return 0, 0

    with sidecar_path.open(encoding="utf-8") as fh:
        pending = json.load(fh)

    print(f"  building place index for muqaddasi merge ...")
    idx = PlaceIndex.build()
    validator = _load_validator()

    n_applied = 0
    n_yaqut_missing = 0
    n_errors = 0

    for muqaddasi_pid, info in pending.items():
        muq_path = idx.pid_to_path.get(muqaddasi_pid)
        if not muq_path:
            n_errors += 1
            continue

        yaqut_curie = info.get("yaqut_curie")
        yaqut_pid = idx.lookup_curie(yaqut_curie) if yaqut_curie else None
        if not yaqut_pid:
            n_yaqut_missing += 1
            continue

        # Update muqaddasi record: add 'yaqut' to derived_from_layers,
        # add a cross-ref note
        muq_rec = _load_record(muq_path)
        layers = list(muq_rec.get("derived_from_layers") or [])
        if "yaqut" not in layers:
            layers.append("yaqut")
            muq_rec["derived_from_layers"] = layers
        existing_note = muq_rec.get("note") or ""
        cross_ref_note = (
            f"Yâqūt cross-attestation: same place is canonicalized at {yaqut_pid} "
            f"under Yâqūt's id={info.get('yaqut_id')}. "
            f"Phase 0 keeps both PIDs; ResolverV2 in Phase 0.5 will consolidate."
        )
        if cross_ref_note not in existing_note:
            new_note = cross_ref_note + (" || " + existing_note if existing_note else "")
            muq_rec["note"] = new_note[:5000]
        _append_record_history(
            muq_rec, "update",
            f"Bidirectional attestation: linked to Yâqūt PID {yaqut_pid}.",
        )
        errs = list(validator.iter_errors(muq_rec))
        if errs:
            n_errors += 1
            if strict:
                raise RuntimeError(f"validation failed for {muqaddasi_pid}: {errs[0].message}")
            continue
        _save_record(muq_path, muq_rec)

        # Update yaqut record: add 'makdisi' to derived_from_layers
        yaqut_path = idx.pid_to_path.get(yaqut_pid)
        if yaqut_path:
            yaqut_rec = _load_record(yaqut_path)
            ylayers = list(yaqut_rec.get("derived_from_layers") or [])
            if "makdisi" not in ylayers:
                ylayers.append("makdisi")
                yaqut_rec["derived_from_layers"] = ylayers
            existing_note = yaqut_rec.get("note") or ""
            cross_ref_note = (
                f"Muqaddasī cross-attestation: same place is also canonicalized "
                f"at {muqaddasi_pid} under Muqaddasī's id={info.get('muqaddasi_id')}, "
                f"iqlim={info.get('iqlim_ar', '?')}."
            )
            if cross_ref_note not in existing_note:
                new_note = (existing_note + " || " + cross_ref_note) if existing_note else cross_ref_note
                yaqut_rec["note"] = new_note[:5000]
            _append_record_history(
                yaqut_rec, "update",
                f"Bidirectional attestation: linked to Muqaddasī PID {muqaddasi_pid}.",
            )
            errs = list(validator.iter_errors(yaqut_rec))
            if not errs:
                _save_record(yaqut_path, yaqut_rec)
            else:
                n_errors += 1

        n_applied += 1

    print(f"  applied={n_applied}, yaqut_pid_missing={n_yaqut_missing}, errors={n_errors}")
    return n_applied, n_errors


# ============================================================================
# Pass 3: Le Strange augmentation
# ============================================================================


def augment_le_strange(strict: bool = False) -> tuple[int, int]:
    sidecar_path = STATE_DIR / "le_strange_yaqut_augment_pending.json"
    if not sidecar_path.exists():
        print(f"  no le-strange sidecar at {sidecar_path}; skipping")
        return 0, 0

    with sidecar_path.open(encoding="utf-8") as fh:
        pending = json.load(fh)

    print(f"  building place index for le-strange augmentation ...")
    idx = PlaceIndex.build()
    validator = _load_validator()

    n_applied = 0
    n_yaqut_missing = 0
    n_errors = 0

    for yaqut_curie, info_or_list in pending.items():
        # Could be single dict or list
        infos = info_or_list if isinstance(info_or_list, list) else [info_or_list]
        yaqut_pid = idx.lookup_curie(yaqut_curie)
        if not yaqut_pid:
            n_yaqut_missing += 1
            continue
        path = idx.pid_to_path.get(yaqut_pid)
        if not path:
            continue

        record = _load_record(path)
        layers = list(record.get("derived_from_layers") or [])
        if "le-strange" not in layers:
            layers.append("le-strange")
            record["derived_from_layers"] = layers

        # Append le-strange forms as alternate names
        labels = record.setdefault("labels", {})
        alt = labels.setdefault("altLabel", {})
        alt_en = list(alt.get("en") or [])
        alt_tr = list(alt.get("tr") or [])
        new_note_parts = []

        for info in infos:
            ls_form = info.get("le_strange_form")
            if ls_form and ls_form not in alt_en:
                alt_en.append(ls_form[:200])
            for an in info.get("alternate_names") or []:
                if an and an not in alt_en:
                    alt_en.append(an[:200])
            page = info.get("page_range")
            chap = info.get("chapter")
            new_note_parts.append(
                f"Le Strange (1905) attestation: id={info.get('le_strange_id')}, "
                f"ch.{chap}, pp.{page}"
                + (f", province='{info['province']}'" if info.get("province") else "")
                + (f", description: {info['description'][:300]}"
                   if info.get("description") else "")
            )

        if alt_en:
            alt["en"] = alt_en[:30]
        if alt_tr:
            alt["tr"] = alt_tr[:30]

        # Append to provenance.derived_from with le-strange entries
        prov = record.setdefault("provenance", {})
        derived = prov.setdefault("derived_from", [])
        for info in infos:
            derived.append({
                "source_id": f"le-strange:{info.get('le_strange_id')}",
                "source_type": "secondary_scholarly",
                "page_or_locator": (
                    f"Le Strange, Lands of the Eastern Caliphate, "
                    f"ch.{info.get('chapter')}, pp.{info.get('page_range')}"
                ),
                "extraction_method": "structured_json",
                "edition_or_version": "Cambridge: Cambridge University Press, 1905.",
            })

        # Note assembly
        existing = record.get("note") or ""
        full_note = existing + (" || " if existing else "") + " || ".join(new_note_parts)
        record["note"] = full_note[:5000]

        _append_record_history(
            record, "update",
            f"Le Strange augmentation applied: {len(infos)} attestation(s) merged.",
        )

        errs = list(validator.iter_errors(record))
        if errs:
            n_errors += 1
            if strict:
                raise RuntimeError(f"validation failed for {yaqut_pid}: {errs[0].message}")
            continue
        _save_record(path, record)
        n_applied += 1

    print(f"  applied={n_applied}, yaqut_pid_missing={n_yaqut_missing}, errors={n_errors}")
    return n_applied, n_errors


# ============================================================================
# Main
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Place namespace integrity pass.")
    parser.add_argument("--resolve-parents", action="store_true",
                        help="Resolve Yâqūt parent_locations → located_in[]")
    parser.add_argument("--merge-muqaddasi", action="store_true",
                        help="Apply Muqaddasī ↔ Yâqūt bidirectional attestation")
    parser.add_argument("--augment-lestrange", action="store_true",
                        help="Apply Le Strange augmentation to existing Yâqūt PIDs")
    parser.add_argument("--all", action="store_true",
                        help="Run all three passes in order")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on validation errors")
    args = parser.parse_args()

    if args.all:
        args.resolve_parents = True
        args.merge_muqaddasi = True
        args.augment_lestrange = True

    if not (args.resolve_parents or args.merge_muqaddasi or args.augment_lestrange):
        parser.print_help()
        return 1

    n_total_errors = 0

    if args.resolve_parents:
        print("\n=== Pass 1: Yâqūt parent_locations → located_in[]")
        _, errs, _ = resolve_parents(strict=args.strict)
        n_total_errors += errs

    if args.merge_muqaddasi:
        print("\n=== Pass 2: Muqaddasī ↔ Yâqūt cross-attestation")
        _, errs = merge_muqaddasi_yaqut(strict=args.strict)
        n_total_errors += errs

    if args.augment_lestrange:
        print("\n=== Pass 3: Le Strange augmentation of Yâqūt PIDs")
        _, errs = augment_le_strange(strict=args.strict)
        n_total_errors += errs

    print(f"\n=== Total errors: {n_total_errors}")
    return 1 if args.strict and n_total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
