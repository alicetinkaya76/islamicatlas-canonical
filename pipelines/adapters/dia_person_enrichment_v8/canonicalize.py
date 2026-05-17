"""
canonicalize.py — H8 Stage 3 upgrade pass: read existing person record,
apply additive H8 patches, yield merged record.

Patch shape (per ADR-011 v1.1 §Patch shape):
1. description.tr — UPGRADE iff len(new) > len(existing) AND existing is a
   verifying prefix of new (proves same-source). Cap at 50K chars
   (ADR-012). Otherwise: leave H4 value untouched.
2. labels.prefLabel.ar — GAP-FILL iff existing absent AND
   classify_arabic_script(primary_a) == "arabic_primary".
3. death_temporal — GAP-FILL iff existing absent AND chunk.d parseable.
4. provenance.derived_from — APPEND dia-chunks-v8:<slug> (never replace
   H4's dia:<slug> entry).
5. provenance.record_history — APPEND update entry (H8 audit trail).
6. provenance.modified — UPDATE to now() (record was mutated).

Idempotency: skip if record already carries dia-chunks-v8:* in
provenance.derived_from (run_adapter.py supports re-runs gracefully).

Defensive: skip records whose existing description.tr does NOT prefix the
new aggregated narrative (suggests human edit; respect editorial truth).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "_lib"
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib.dia_enrichment_lib import (  # noqa: E402
    build_h8_provenance_entry,
    build_temporal_from_parsed_d,
    classify_arabic_script,
    has_h8_v8_provenance,
    parse_death_paren_extended,
    truncate_at_sentence_boundary,
    DESCRIPTION_MAX_LEN,
)


ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
# Prefix verification length: how many chars of existing description.tr
# must prefix the new aggregated narrative to authorize upgrade. 200 char
# is generous; deterministic same-source aggregation produces identical
# leading bytes between H4 and v8 runs.
PREFIX_VERIFY_LEN = 200


def _read_existing_record(repo_root: Path, pid: str) -> dict | None:
    """Read the existing iac_person_NNNNNNNN.json record from disk."""
    pid_num = pid.split("-")[-1]
    path = repo_root / "data" / "canonical" / "person" / f"iac_person_{pid_num}.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _apply_h8_patches(
    record: dict,
    slug: str,
    primary_a: str,
    primary_d: str,
    t_total: str,
    now: str,
) -> tuple[dict, dict]:
    """Apply H8 patches to a copy of record. Return (new_record, change_log).

    change_log keys: desc_upgrade (bool), arabic_filled (bool),
    temporal_filled (bool), prov_appended (bool, always True for non-skip).
    """
    rec = json.loads(json.dumps(record))  # deep copy
    changes = {
        "desc_upgrade": False,
        "arabic_filled": False,
        "temporal_filled": False,
        "prov_appended": True,
    }

    labels = rec.setdefault("labels", {"prefLabel": {}})

    # 1. description.tr UPGRADE
    descs = labels.setdefault("description", {})
    existing_tr = descs.get("tr", "")
    if t_total and len(t_total) > len(existing_tr):
        existing_prefix = existing_tr[:PREFIX_VERIFY_LEN]
        # Authorize upgrade only if existing was empty OR existing's prefix
        # matches the new narrative (proving same-source truncation, not
        # a divergent editorial edit).
        if not existing_tr or t_total.startswith(existing_prefix):
            new_desc, _ = truncate_at_sentence_boundary(
                t_total, DESCRIPTION_MAX_LEN
            )
            descs["tr"] = new_desc
            changes["desc_upgrade"] = True
        # else: editorial edit detected — silently skip upgrade

    # 2. prefLabel.ar GAP-FILL
    pref = labels.setdefault("prefLabel", {})
    if not pref.get("ar"):
        a_class = classify_arabic_script(primary_a)
        if a_class == "arabic_primary":
            pref["ar"] = primary_a
            changes["arabic_filled"] = True

    # 3. death_temporal GAP-FILL
    if not rec.get("death_temporal"):
        d_parsed = parse_death_paren_extended(primary_d)
        if d_parsed:
            temporal = build_temporal_from_parsed_d(d_parsed)
            if temporal:
                rec["death_temporal"] = temporal
                changes["temporal_filled"] = True

    # 4-6. Provenance augmentation (always)
    prov = rec.setdefault("provenance", {})
    derived = prov.setdefault("derived_from", [])
    derived.append(build_h8_provenance_entry(slug))

    history = prov.setdefault("record_history", [])
    note_parts = ["H8 Stage 3 dia_person_enrichment_v8"]
    if changes["desc_upgrade"]:
        note_parts.append("desc upgrade")
    if changes["arabic_filled"]:
        note_parts.append("prefLabel.ar gap-fill")
    if changes["temporal_filled"]:
        note_parts.append("death_temporal gap-fill")
    history.append({
        "change_type": "update",
        "changed_at": now,
        "changed_by": ATTRIBUTED_TO,
        "release": "v0.1.0",
        "note": ", ".join(note_parts) + f" (slug={slug}).",
    })
    prov["modified"] = now

    return rec, changes


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter=None,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    """Main canonicalize entry point.

    Args:
        extracted_records: from extract.py.
        pid_minter: UNUSED (no new PIDs minted).
        reconciler: UNUSED (reconciliation disabled in manifest).
        options: passed by run_adapter.py (strict_mode, etc.).
    """
    options = options or {}
    strict = options.get("strict_mode", True)

    # Derive repo root from this file's location
    # /Volumes/.../pipelines/adapters/dia_person_enrichment_v8/canonicalize.py
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )

    n_yielded = 0
    n_skip_idempotent = 0
    n_skip_no_record = 0
    n_desc_upgraded = 0
    n_arabic_filled = 0
    n_temporal_filled = 0

    for extracted in extracted_records:
        raw = extracted.get("raw_data", {})
        slug = raw.get("slug")
        pid = raw.get("resolved_pid")
        if not slug or not pid:
            continue

        primary_a = raw.get("primary_a", "")
        primary_d = raw.get("primary_d", "")
        t_total = raw.get("t_total", "")

        existing = _read_existing_record(repo_root, pid)
        if existing is None:
            n_skip_no_record += 1
            print(
                f"[canonicalize] WARN: no existing record at {pid} (slug={slug})",
                file=sys.stderr,
            )
            continue

        if has_h8_v8_provenance(existing):
            n_skip_idempotent += 1
            continue

        try:
            patched, changes = _apply_h8_patches(
                existing, slug, primary_a, primary_d, t_total, now
            )
            n_yielded += 1
            if changes["desc_upgrade"]:
                n_desc_upgraded += 1
            if changes["arabic_filled"]:
                n_arabic_filled += 1
            if changes["temporal_filled"]:
                n_temporal_filled += 1
            yield patched
        except Exception as exc:
            if strict:
                raise
            print(
                f"[canonicalize] ERROR slug={slug}: {exc}", file=sys.stderr
            )

    print(
        f"[canonicalize] yielded={n_yielded} "
        f"(desc_upgraded={n_desc_upgraded} "
        f"arabic_filled={n_arabic_filled} "
        f"temporal_filled={n_temporal_filled}); "
        f"skip_idempotent={n_skip_idempotent} "
        f"skip_no_record={n_skip_no_record}"
    )
