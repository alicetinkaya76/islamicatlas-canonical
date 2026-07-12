"""
canonicalize.py — EI1 → person mints + person/place/dynasty AUGMENTS.

Single-yield-namespace design (run_adapter validates yields against ONE
schema): only PERSON records are minted. The unique value of EI1 for the
other classes is its ENGLISH summaries on entities the store already has —
so geography/dynasty run match-or-review only (augment sidecar / queue);
their "new" cases are recorded, never minted (Yâqūt already covers the
gazetteer; a coordinate-less OCR place adds noise, not map value).

Person track:
    match  → augment sidecar (description.en/ar gap-fill, altLabel.en,
             ei1 provenance) — applied by apply_ei1_augments.py
    new    → mint IFF a death/birth year parsed (dia precedent: the P0.2
             temporal rule); date-less new → sidecar `person_new_dateless`
    review → resolver queue (never minted)

Work titles (ei1_works, 306 lists): NOT minted — title-string-only works are
exactly ADR-009's forbidden sig-mint. Kept in the augment payloads as
evidence for AP-style future validation.

OCR caveat: titles carry noise ("BA GH DAD") — such records naturally land
in review/new-dateless rather than corrupting matches (score too low).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = ("Encyclopaedia of Islam, 1st ed. (Brill, 1913-1936), digitized/"
           "structured ei1_lite v-repo; OCR-derived — noise possible")

_CLASS_TO_NS = {"biography": "person", "geography": "place", "dynasty": "dynasty"}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_person_ei1")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("ei1_augment")
    if side is None:
        side = {}
    for k in ("person", "place", "dynasty", "person_new_dateless",
              "skipped_classes", "_review_skipped"):
        side.setdefault(k, {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"match": 0, "new_minted": 0, "new_dateless": 0, "new_place_dyn": 0,
             "review": 0, "skipped_class": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        at = raw.get("at") or "unknown"
        ns = _CLASS_TO_NS.get(at)
        if ns is None:
            stats["skipped_class"] += 1
            sc = side["skipped_classes"]
            sc[at] = sc.get(at, 0) + 1
            continue

        labels = _build_labels(raw)
        temporal = _temporal(raw)
        # Resolver'a yalnız ÖLÜM yılı verilir (bc doğumdur; ölüm-bracket'lı
        # store'a karşı yanlış sinyal olur — H10 final-review).
        q_temporal = ({"start_ce": temporal["start_ce"]}
                      if temporal.get("_from") == "dc" else {})
        decision = resolver.resolve(
            entity_type=ns, adapter_id="ei1", extracted_record_id=rid,
            labels=labels, temporal=q_temporal)

        if decision.kind == "match":
            stats["match"] += 1
            side[ns].setdefault(decision.matched_pid, []).append(
                _augment_payload(raw, decision))
            continue
        if decision.kind == "review":
            stats["review"] += 1
            side["_review_skipped"][rid] = {
                "queue_id": decision.queue_id, "ns": ns,
                "confidence": decision.confidence, "title": raw.get("t")}
            continue

        # kind == "new"
        if ns != "person":
            stats["new_place_dyn"] += 1
            sc = side["skipped_classes"]
            key = f"{ns}_new_not_minted"
            sc[key] = sc.get(key, 0) + 1
            continue
        if not temporal:
            stats["new_dateless"] += 1
            side["person_new_dateless"][rid] = {"title": raw.get("t")}
            continue

        stats["new_minted"] += 1
        yield _build_person(raw, labels, temporal, rid, pid_minter,
                            pipeline_name, pipeline_version, now)

    resolver.close()
    print(f"[canonicalize] ei1: match(augment)={stats['match']} "
          f"person-mint={stats['new_minted']} "
          f"person-new-dateless={stats['new_dateless']} "
          f"place/dyn-new(not-minted)={stats['new_place_dyn']} "
          f"review={stats['review']} skipped-class={stats['skipped_class']}")


def _build_labels(raw: dict) -> dict:
    pref: dict = {}
    t = (raw.get("t") or "").strip()
    tn = (raw.get("tn") or "").strip()
    if t:
        pref["en"] = t.title() if t.isupper() else t
    labels: dict = {"prefLabel": pref or {"en": f"EI1 {raw.get('id')}"}}
    alts = [v for v in (tn,) if v and v.lower() != t.lower()]
    if alts:
        labels["altLabel"] = {"en": alts}
    return labels


def _temporal(raw: dict) -> dict:
    """H10 final-review düzeltmesi: hangi anahtardan geldiği taşınır — bc
    (doğum) death_temporal'a yazılıp 58 kayda yanlış ölüm yılı basmıştı.
    Ayrıca doğum yılı resolver'a ölüm-yılıymış gibi verilmez (yanlış tarih,
    tarihsizden kötü skorlar ve review bandını atlatır)."""
    out: dict = {}
    for k in ("dc", "bc"):
        v = raw.get(k)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            v = int(v.strip())
        if isinstance(v, int) and -600 <= v <= 2000:
            out["start_ce"] = v
            out["_from"] = k
            break
    return out


def _augment_payload(raw: dict, decision) -> dict:
    return {
        "ei1_id": raw.get("id"),
        "matched_via": f"tier{decision.tier}",
        "confidence": decision.confidence,
        "title": raw.get("t"),
        "summary_en": (raw.get("ds") or "")[:5000] or None,
        "summary_tr": (raw.get("dt") or "")[:5000] or None,
        "summary_ar": (raw.get("da") or "")[:5000] or None,
        "author": raw.get("au"),
        "vol": raw.get("vol"), "page": raw.get("is"),
        "work_titles": (raw.get("work_titles") or [])[:20],
    }


def _build_person(raw, labels, temporal, rid, pid_minter,
                  pipeline_name, pipeline_version, now) -> dict:
    pid = pid_minter.mint("person", rid)
    # dc → death_temporal; bc → birth_temporal (P0.2 "en az bir temporal"
    # kuralını doğum da sağlar; doğumu ölüm diye yazmak 58 kaydı bozmuştu).
    t_field = "death_temporal" if temporal.get("_from") == "dc" else "birth_temporal"
    record = {
        "@id": pid,
        "@type": ["iac:Person"],
        "labels": labels,
        "profession": ["scholar"],
        t_field: {"start_ce": temporal["start_ce"], "approximation": "exact"},
        "provenance": {
            "derived_from": [{
                "source_id": rid,
                "source_type": "tertiary_reference",
                "page_or_locator": f"EI1 vol. {raw.get('vol')}, p. {raw.get('is')}",
                "extraction_method": "ocr",
                "edition_or_version": EDITION,
            }],
            "generated_by": {"pipeline_name": pipeline_name,
                             "pipeline_version": pipeline_version},
            "generated_at": now,
            "attributed_to": ATTRIBUTED_TO,
            "created": now, "modified": now,
            "license": LICENSE,
            "record_history": [{
                "change_type": "create", "changed_at": now,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": f"Initial canonicalization by {pipeline_name} "
                        f"{pipeline_version} (H10 Stage 4; Tier-2 kind=new, "
                        f"dated).",
            }],
            "deprecated": False,
        },
    }
    desc = {}
    if raw.get("ds"):
        desc["en"] = raw["ds"][:5000]
    if raw.get("dt"):
        desc["tr"] = raw["dt"][:5000]
    if desc:
        record["labels"]["description"] = desc
    return record
