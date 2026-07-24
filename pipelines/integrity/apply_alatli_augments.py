#!/usr/bin/env python3
"""apply_alatli_augments.py — Alatlı Track-A augment'lerini mevcut kişilere uygula (H25).

Alatlı adapter'ının match(augment) sonuçları (data/sources/alatli/
_alatli_augment_pending.json) mevcut store kişilerine gap-fill + provenance
append olarak işlenir. Idempotency probe = derived_from'da `alatli:` var mı.

Her matched PID için:
  authority_xref  ← Alatlı QID  (store'da QID YOKSA ekle; FARKLI QID varsa
                    ÇATIŞMA kuyruğuna — ÜZERİNE YAZMA; AYNIYSA no-op)
  altLabel.tr     += Alatlı adı (yoksa)
  derived_from_layers += "alatli"
  derived_from    += alatli:<id> + record_history + modified

Çoklu-olay (aynı PID'e ≥2 Alatlı kişisi) = adaş-merge şüphesi → collisions
kuyruğu, OTOMATİK UYGULANMAZ (ei1 deseni). Alatlı QID'i tarih-teyitli olduğu
için store'un %33,7 FP QID'lerini de yakalar → alatli-qid-conflicts kuyruğu.

Kullanım: python3 pipelines/integrity/apply_alatli_augments.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIDECAR = REPO_ROOT / "data" / "sources" / "alatli" / "_alatli_augment_pending.json"
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
EDITION = ("Alev Alatlı (der.), Tarihe Yön Veren Metinler, 9 cilt "
           "(Kapadokya Üniversitesi Yayınları, 2014/2021).")


def _all_label_strings(labels: dict) -> set[str]:
    out = set()
    for v in (labels.get("prefLabel") or {}).values():
        if isinstance(v, str):
            out.add(v.casefold())
    for arr in (labels.get("altLabel") or {}).values():
        if isinstance(arr, list):
            out.update(x.casefold() for x in arr if isinstance(x, str))
    return out


def _queue(path: Path, obj: dict, dry: bool):
    if dry:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    side = json.loads(SIDECAR.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    coll_q = REPO_ROOT / "data" / "review_queue" / "alatli-collisions.jsonl"
    conf_q = REPO_ROOT / "data" / "review_queue" / "alatli-qid-conflicts.jsonl"

    n_applied = n_noop = n_missing = n_coll = 0
    qid_added = qid_conflict = qid_same = 0

    for pid, events in sorted(side.items()):
        path = (REPO_ROOT / "data" / "canonical" / "person" /
                f"iac_person_{pid.rsplit('-', 1)[1]}.json")
        if not path.exists():
            n_missing += 1
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        derived = rec.setdefault("provenance", {}).setdefault("derived_from", [])
        if any(str(d.get("source_id", "")).startswith("alatli:") for d in derived):
            n_noop += 1
            continue

        # adaş-merge guard
        if len(events) > 1:
            _queue(coll_q, {"pid": pid, "events": events}, args.dry_run)
            n_coll += 1
            continue

        ev = events[0]
        changed = []
        labels = rec.setdefault("labels", {})

        # --- QID (asıl değer + FP-audit) ---
        qid = ev.get("qid")
        if qid:
            xref = rec.setdefault("authority_xref", [])
            store_qids = {x.get("id") for x in xref if x.get("authority") == "wikidata"}
            if qid in store_qids:
                qid_same += 1
            elif store_qids:
                # FARKLI QID — üzerine yazma; çatışmayı kuyruğa (FP-audit)
                _queue(conf_q, {
                    "pid": pid, "store_qid": sorted(store_qids), "alatli_qid": qid,
                    "alatli_name": ev.get("name_tr"),
                    "alatli_death_ce": ev.get("death_ce"),
                    "alatli_birth_ce": ev.get("birth_ce"),
                    "match_tier": ev.get("tier"),
                }, args.dry_run)
                qid_conflict += 1
            else:
                # store'da QID yok → Alatlı tarih-teyitli QID'i ekle (display-gate arkası)
                xref.append({
                    "authority": "wikidata", "id": qid,
                    "confidence": round(max(0.7, ev.get("confidence") or 0.9), 3),
                    "method": "imported_from_source", "reviewed": False,
                    "note": "Alatlı (Tarihe Yön Veren Metinler): Tier-2 ad+ölüm eşleşmesi; "
                            "QID Wikidata tarih-teyitli.",
                })
                qid_added += 1
                changed.append("authority_xref")

        # --- altLabel.tr (Alatlı ad biçimi) ---
        name_tr = (ev.get("name_tr") or "").strip()
        if name_tr and name_tr.casefold() not in _all_label_strings(labels):
            labels.setdefault("altLabel", {}).setdefault("tr", []).append(name_tr)
            changed.append("altLabel.tr")

        # --- source_layer tag ---
        layers = list(rec.get("derived_from_layers") or [])
        if "alatli" not in layers:
            layers.append("alatli")
            rec["derived_from_layers"] = layers
            changed.append("derived_from_layers")

        # --- provenance ---
        derived.append({
            "source_id": f"alatli:{ev['alatli_id']}",
            "source_type": "secondary_scholarly",
            "page_or_locator": f"Tarihe Yön Veren Metinler, kanon={'+'.join(ev.get('canon') or [])}",
            "extraction_method": "structured_json",
            "edition_or_version": EDITION,
        })
        rec["provenance"].setdefault("record_history", []).append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": (f"alatli augment (H25, Tier-{ev.get('tier')} conf "
                     f"{round(ev.get('confidence', 0), 2)}): {changed or 'provenance-only'}."),
        })
        rec["provenance"]["modified"] = now
        if not args.dry_run:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        n_applied += 1

    print(f"[apply_alatli_augments] applied={n_applied} already-done={n_noop} "
          f"collision={n_coll} missing={n_missing}"
          f"{' (dry-run)' if args.dry_run else ''}")
    print(f"  QID: added={qid_added} conflict(FP-audit)={qid_conflict} same={qid_same}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
