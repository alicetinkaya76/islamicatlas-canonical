"""
H7 QID quality audit — confirmed-wrong Wikidata target flagger.

Idempotent. For each target person PID + bad QID pair, locate the matching
authority_xref entry and flag it: confidence -> 0.0, reviewed -> false,
note -> 'h7_audit_confirmed_wrong_target:...; do_not_display'. Pre-state is
preserved in provenance.record_history (change_type='update'). Schema-valid
under person.schema.json + _common/authority_xref.schema.json (uses local
$ref registry, no network).

Detects already-flagged records and no-ops them (idempotent). Writes a state
manifest to data/_state/h7_qid_audit_report.json so subsequent sessions can
verify which PIDs have already been triaged.

Usage:
    python3 pipelines/_lib/h7_qid_audit_apply.py [--dry-run]

Source of bad-QID list: KNOWN_ISSUES Sorun 2 (H6 handoff, 2026-05-05),
Wikidata API verified.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PERSON_DIR = REPO_ROOT / "data" / "canonical" / "person"
STATE_DIR = REPO_ROOT / "data" / "_state"
PERSON_SCHEMA = REPO_ROOT / "schemas" / "person.schema.json"
SCHEMAS_DIR = REPO_ROOT / "schemas"
REPORT_PATH = STATE_DIR / "h7_qid_audit_report.json"

ORCID = "https://orcid.org/0000-0002-7747-6854"
RELEASE = "v0.1.0-phase0-h7"
NOTE_PREFIX = "h7_audit_confirmed_wrong_target:"

TARGETS = [
    {
        "pid": "iac:person-00000184",
        "bad_qid": "Q9438",
        "label_for_log": "Harezmî",
        "wrong_target": "Thomas_Aquinas (1225-1274 Italian Dominican)",
    },
    {
        "pid": "iac:person-00000115",
        "bad_qid": "Q9458",
        "label_for_log": "al-Qāsim I (2.)",
        "wrong_target": "Prophet_Muhammad",
    },
    {
        "pid": "iac:person-00020919",
        "bad_qid": "Q36533610",
        "label_for_log": "Badr",
        "wrong_target": "Diana_Badr (modern botanist)",
    },
    {
        "pid": "iac:person-00000182",
        "bad_qid": "Q719449",
        "label_for_log": "'Alī II",
        "wrong_target": "Shah_Alam_II (Mughal Emperor 1760-1806)",
    },
]


def _load_validator():
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as e:
        print(
            "FATAL: jsonschema/referencing not installed. "
            "Run: pip install jsonschema referencing",
            file=sys.stderr,
        )
        raise SystemExit(3) from e

    registry = Registry()
    for sp in SCHEMAS_DIR.rglob("*.schema.json"):
        try:
            s = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            continue
        sid = s.get("$id")
        if sid:
            registry = registry.with_resource(uri=sid, resource=Resource.from_contents(s))

    target = json.loads(PERSON_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(target)
    return Draft202012Validator(target, registry=registry)


def _person_path(pid: str) -> Path:
    stem = pid.replace("iac:", "iac_").replace("-", "_")
    return PERSON_DIR / f"{stem}.json"


def _is_already_flagged(xref_entry: dict) -> bool:
    if not isinstance(xref_entry, dict):
        return False
    if xref_entry.get("confidence") != 0.0:
        return False
    note = xref_entry.get("note") or ""
    return note.startswith(NOTE_PREFIX)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report but do not write any files.",
    )
    args = parser.parse_args()

    validator = _load_validator()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    decisions = []
    write_count = 0
    noop_count = 0
    skip_count = 0
    invalid_count = 0

    for t in TARGETS:
        pid = t["pid"]
        bad_qid = t["bad_qid"]
        fn = _person_path(pid)
        if not fn.exists():
            decisions.append({"pid": pid, "bad_qid": bad_qid, "decision": "missing_file", "path": str(fn)})
            skip_count += 1
            continue

        d = json.loads(fn.read_text(encoding="utf-8"))
        ax = d.get("authority_xref") or []
        target_entry = None
        for e in ax:
            if isinstance(e, dict) and e.get("authority") == "wikidata" and e.get("id") == bad_qid:
                target_entry = e
                break

        if target_entry is None:
            decisions.append({"pid": pid, "bad_qid": bad_qid, "decision": "no_matching_xref"})
            skip_count += 1
            continue

        if _is_already_flagged(target_entry):
            decisions.append({
                "pid": pid,
                "bad_qid": bad_qid,
                "decision": "already_flagged_noop",
                "current_confidence": target_entry.get("confidence"),
                "current_reviewed": target_entry.get("reviewed"),
            })
            noop_count += 1
            continue

        pre_state = {k: target_entry.get(k) for k in ("confidence", "reviewed", "note")}
        note_text = (
            f"{NOTE_PREFIX}{bad_qid}→{t['wrong_target']}; "
            f"do_not_display; verified via Wikidata API 2026-05; "
            f"see KNOWN_ISSUES Sorun 2 (H6 handoff)"
        )
        target_entry["confidence"] = 0.0
        target_entry["reviewed"] = False
        target_entry["note"] = note_text

        prov = d.setdefault("provenance", {})
        history = prov.setdefault("record_history", [])
        history.append({
            "change_type": "update",
            "changed_at": now_iso,
            "changed_by": ORCID,
            "release": RELEASE,
            "note": (
                f"Hafta 7 QID quality audit: confirmed wrong wikidata target "
                f"{bad_qid} → {t['wrong_target']}. authority_xref entry retained "
                f"but flagged: confidence 1.0 → 0.0, reviewed → false, note set. "
                f"Pre-state: {pre_state}. Wikidata API verified 2026-05."
            ),
        })
        prov["modified"] = now_iso

        errs = sorted(validator.iter_errors(d), key=lambda x: list(x.absolute_path))
        if errs:
            decisions.append({
                "pid": pid,
                "bad_qid": bad_qid,
                "decision": "schema_invalid",
                "errors": [{"path": list(e.absolute_path), "msg": e.message[:200]} for e in errs[:3]],
            })
            invalid_count += 1
            continue

        if not args.dry_run:
            fn.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        decisions.append({
            "pid": pid,
            "bad_qid": bad_qid,
            "decision": "wrote" if not args.dry_run else "would_write",
            "label_for_log": t["label_for_log"],
            "pre_state": pre_state,
        })
        write_count += 1

    summary = {
        "wrote": write_count,
        "noop_already_flagged": noop_count,
        "skipped": skip_count,
        "schema_invalid": invalid_count,
        "dry_run": args.dry_run,
    }
    report = {
        "audit_id": "h7_qid_audit_001_confirmed_wrong_targets",
        "audit_version": "1.0.0",
        "executed_at": now_iso,
        "executor_orcid": ORCID,
        "release": RELEASE,
        "source": "KNOWN_ISSUES Sorun 2 (H6 handoff 2026-05-05); Wikidata API verified",
        "schema_target_version": "v0.2.0",
        "summary": summary,
        "decisions": decisions,
    }

    if not args.dry_run:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"=== H7 QID audit summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"  report_path: {REPORT_PATH}{' (dry-run, not written)' if args.dry_run else ''}")
    print()
    print(f"=== Per-target decisions ===")
    for dec in decisions:
        print(f"  {dec['pid']}  bad={dec['bad_qid']}  decision={dec['decision']}")

    return 0 if invalid_count == 0 else 4


if __name__ == "__main__":
    raise SystemExit(main())
