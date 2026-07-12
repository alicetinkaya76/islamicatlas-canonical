"""
canonicalize.py — DarpIslam mints → place namespace, Tier-2-resolved two-track.

FIRST real consumer of the H10 Tier-2 resolver (ADR-008 §8.2). Per mint:

  TRACK A (resolver kind="match", tier 1 or 2):
    The mint's town already exists in the place store (usually Yâqūt-seeded).
    NO new record — an augmentation entry goes to the
    darp_islam_augment_pending sidecar (applied by
    pipelines/integrity/apply_darp_augments.py: derived_from_layers +=
    "darp-islam" + record_history update). Mirrors le-strange's pattern.

  TRACK B (kind="new"):
    Mint a new iac:place record: @type [iac:Place, iac:Settlement],
    coords, temporal_coverage from emission years (CE), trilingual labels,
    provenance source_type=digital_corpus (ADR-010), derived_from_layers
    ["darp-islam"]. nomisma_uri goes into provenance.page_or_locator + note —
    the frozen v0.3.0 authority enum has no 'nomisma' (candidate for v0.4.x).

  REVIEW (0.70 ≤ score < auto threshold, or single-signal high score):
    NOTHING is written — the resolver has already queued the case with its
    candidate list (data/review_queue/darp-islam.jsonl); the sidecar records
    it under review_skipped for the historian pass. North Star: a probable
    duplicate is never minted.

Refuses to run if the lookup index is missing: resolving 3,381 mints against
an absent index would silently mint duplicates for every known town.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = ("DarpIslam v1.1 (2026-03-27) — Digital Corpus of Islamic Mints; "
           "aggregates Ö. Diler, Islamic Mints (2009) via Hamburg ERC "
           "digitization (MIT) + nomisma.org mint records")

_METAL_TR = {"AV": "altın/dinar", "AR": "gümüş/dirhem", "AE": "bakır/fels"}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    namespace = options.get("namespace", "place")
    pipeline_name = options.get("pipeline_name", "canonicalize_place_darp_islam")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    augment = sidecars.get("darp_augment")
    if augment is None:
        augment = {}

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError(
            "lookup.sqlite missing — build it first (python3 "
            "pipelines/_index/build_lookup.py); resolving without the index "
            "would mint a duplicate for every known town.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    n_match = n_new = n_review = 0

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        detail = raw.get("detail") or {}

        labels = _build_labels(raw, detail)
        temporal = {}
        if isinstance(raw.get("year_min_ce"), int):
            temporal["start_ce"] = raw["year_min_ce"]
        if isinstance(raw.get("year_max_ce"), int):
            temporal["end_ce"] = raw["year_max_ce"]
        coords = {"lat": raw.get("lat"), "lon": raw.get("lng")}

        decision = resolver.resolve(
            entity_type="place", adapter_id="darp-islam",
            extracted_record_id=rid,
            labels=labels, temporal=temporal, coords=coords)

        if decision.kind == "match":
            n_match += 1
            # LIST per pid — multiple mint records can legitimately land on
            # the same town (e.g. name variants of Damascus); a dict-overwrite
            # here silently dropped 85/706 matches in the first bulk run.
            augment.setdefault(decision.matched_pid, []).append({
                "darp_id": raw["id"],
                "matched_via": f"tier{decision.tier}",
                "confidence": decision.confidence,
                "mint_name_tr": raw.get("name_tr"),
                "nomisma_uri": detail.get("nomisma_uri") or None,
                "mint_years_ce": [raw.get("year_min_ce"), raw.get("year_max_ce")],
                "metals": raw.get("metals") or [],
                "emission_count": raw.get("emission_count", 0),
                "dynasties": raw.get("dynasties") or [],
            })
            continue

        if decision.kind == "review":
            n_review += 1
            skipped = augment.setdefault("_review_skipped", {})
            skipped[rid] = {"queue_id": decision.queue_id,
                            "confidence": decision.confidence,
                            "name_tr": raw.get("name_tr")}
            continue

        # Hinted-new demotion (pilot finding): the source curator marked this
        # mint as a Yâqūt town (yakut_tr description present) but Tier-2
        # scored below the review band — minting would very likely duplicate
        # an existing place under a distant transliteration. North Star:
        # curator-signal + resolver-miss = borderline → human review, no mint.
        if detail.get("yakut_tr") or detail.get("yakut_en"):
            n_review += 1
            skipped = augment.setdefault("_review_skipped", {})
            skipped[rid] = {"queue_id": None,
                            "reason": "yakut_hint_unresolved",
                            "confidence": decision.confidence,
                            "name_tr": raw.get("name_tr"),
                            "yakut_hint_tr": (detail.get("yakut_tr") or "")[:200]}
            continue

        n_new += 1
        yield _build_place(raw, detail, labels, temporal, rid,
                           pid_minter, namespace, pipeline_name,
                           pipeline_version, now)

    resolver.close()
    print(f"[canonicalize] darp-islam: match(augment)={n_match} "
          f"new(mint)={n_new} review(skipped)={n_review}")


def _build_labels(raw: dict, detail: dict) -> dict:
    # NOTE: detail.yakut_tr/en are DESCRIPTION texts ("Kazvin ve Zanjan
    # arası..."), not name forms — pilot validation showed feeding them to
    # the resolver as altLabel pollutes the FTS query. They are used only as
    # a curator SIGNAL (see the hinted-new demotion in canonicalize()).
    pref: dict = {}
    if raw.get("name_tr"):
        pref["tr"] = raw["name_tr"]
    if raw.get("name_en") and raw.get("name_en") != raw.get("name_tr"):
        pref["en"] = raw["name_en"]
    if raw.get("name_ar"):
        pref["ar"] = raw["name_ar"]
    if not pref:
        pref["en"] = raw.get("name_en") or f"Mint {raw.get('id')}"
    labels: dict = {"prefLabel": pref}
    if raw.get("name_ar"):
        labels["originalScript"] = {"ar": raw["name_ar"]}
    return labels


def _build_place(raw, detail, labels, temporal, rid, pid_minter, namespace,
                 pipeline_name, pipeline_version, now) -> dict:
    pid = pid_minter.mint(namespace, rid)
    metals = ", ".join(_METAL_TR.get(m, m) for m in (raw.get("metals") or []))
    dynasties = ", ".join(raw.get("dynasties") or [])
    note_bits = [f"İslam darphanesi ({raw.get('type', 'mint')})."]
    if raw.get("emission_count"):
        note_bits.append(f"{raw['emission_count']} emisyon kaydı.")
    if metals:
        note_bits.append(f"Metaller: {metals}.")
    if dynasties:
        note_bits.append(f"Hanedanlar: {dynasties}.")
    if detail.get("nomisma_uri"):
        note_bits.append(f"Nomisma: {detail['nomisma_uri']} (authority enum'unda "
                         f"'nomisma' yok — v0.4.x adayı; ADR-013).")

    record = {
        "@id": pid,
        "@type": ["iac:Place", "iac:Settlement"],
        "place_subtype": "settlement",
        "labels": labels,
        "coords": {"lat": raw["lat"], "lon": raw["lng"],
                   "uncertainty": {"type": "centroid"},
                   "precision_meters": 10000,
                   "derived_from_source": rid},
        "derived_from_layers": ["darp-islam"],
        "note": " ".join(note_bits)[:2000],
        "provenance": {
            "derived_from": [{
                "source_id": rid,
                "source_type": "digital_corpus",
                "page_or_locator": (detail.get("nomisma_uri")
                                    or f"DarpIslam mint id={raw['id']}"),
                "extraction_method": "structured_json",
                "edition_or_version": EDITION,
            }],
            "generated_by": {"pipeline_name": pipeline_name,
                             "pipeline_version": pipeline_version},
            "generated_at": now,
            "attributed_to": ATTRIBUTED_TO,
            "created": now,
            "modified": now,
            "license": LICENSE,
            "record_history": [{
                "change_type": "create",
                "changed_at": now,
                "changed_by": ATTRIBUTED_TO,
                "release": "v0.1.0-phase0",
                "note": f"Initial canonicalization by {pipeline_name} "
                        f"{pipeline_version} (H10 Stage 2; Tier-2 resolved "
                        f"kind=new).",
            }],
            "deprecated": False,
        },
    }
    if temporal:
        record["temporal_coverage"] = temporal
    return record
