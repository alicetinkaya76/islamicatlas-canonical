"""canonicalize.py — Alatlı adapter (person edition, ei1 pattern).

Her Alatlı kişisi için Tier-2 resolver çalışır:
  MATCH  → store'da zaten var → augment sidecar (Alatlı tarihi/QID/korpus atfı eklenir)
  REVIEW → sınırda → resolver kuyruğa alır
  NEW    → İslami (bize/both) ise MINT; Batı (batiya) ise scope-b gereği YAN-TABLOda TUTULUR

Resolver'a yalnız ÖLÜM yılı sinyal verilir (ei1 dersi: doğum, ölüm-bracket'lı
store'a karşı yanlış sinyal). Alatlı QID'i Tier-1 deterministik eşleşme sağlar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib import person_canonicalize as pc
from pipelines._lib.entity_resolver import EntityResolver

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = (
    "Alev Alatlı (der.), Tarihe Yön Veren Metinler, 9 cilt "
    "(Kapadokya Üniversitesi Yayınları, 2014/2021)."
)


def _labels(raw: dict, rid: str) -> dict:
    pref: dict = {}
    if raw.get("name_tr"):
        pref["tr"] = raw["name_tr"]
    if raw.get("name_en"):
        pref["en"] = raw["name_en"]
    labels: dict = {"prefLabel": pref or {"tr": raw.get("name_tr") or rid}}
    aliases = [a for a in (raw.get("aliases") or []) if a][:5]
    if aliases:
        labels["altLabel"] = {"tr": aliases}
    return labels


def _canonical_temporal(death_ce, birth_ce):
    """(field_name, temporal_dict) — ölüm önce, yoksa doğum."""
    for val, field, approx in ((death_ce, "death_temporal", "exact"),
                               (birth_ce, "birth_temporal", "exact")):
        try:
            y = int(val) if val is not None else None
        except (TypeError, ValueError):
            y = None
        if y is not None and -3000 <= y <= 3000:
            return field, {"start_ce": y, "approximation": approx}
    return None, None


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_person_alatli")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    augment = sidecars.setdefault("alatli_augment", {})
    western = sidecars.setdefault("alatli_western_held", {})
    audit = sidecars.setdefault("alatli_qid_audit", {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"match": 0, "mint": 0, "western_held": 0, "review": 0, "dateless": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]
        canon = raw.get("canon") or []
        is_western = ("batiya" in canon) and ("bize" not in canon)
        qid = raw.get("qid")
        death_ce = raw.get("death_ce")
        birth_ce = raw.get("birth_ce")

        labels = _labels(raw, rid)
        q_temporal = {"start_ce": int(death_ce)} if death_ce is not None else {}
        axref_in = [{"authority": "wikidata", "id": qid}] if qid else None

        decision = resolver.resolve(
            entity_type="person", adapter_id="alatli",
            extracted_record_id=f"alatli:{rid}",
            authority_xref=axref_in, labels=labels, temporal=q_temporal)

        # ---- MATCH → augment ----
        if decision.kind == "match":
            stats["match"] += 1
            augment.setdefault(decision.matched_pid, []).append({
                "alatli_id": rid, "name_tr": raw.get("name_tr"),
                "qid": qid, "death_ce": death_ce, "birth_ce": birth_ce,
                "tdv_slug": raw.get("tdv_slug"), "canon": canon,
                "place_label": raw.get("place_label"),
                "record_count": raw.get("record_count"),
                "tier": decision.tier, "confidence": decision.confidence,
            })
            # QID-audit: Alatlı tarih-teyitli QID getirdi ama Tier-1 dışı eşleşme
            # → çift-kaynak; store QID'i varsa tarih-çelişkisi ayrı önizlemede.
            continue

        # ---- REVIEW → resolver zaten kuyruğa aldı ----
        if decision.kind == "review":
            stats["review"] += 1
            continue

        # ---- NEW ----
        if is_western:
            # SCOPE-b: Batı kanonu canonical store'a MINT EDİLMEZ.
            stats["western_held"] += 1
            western[rid] = {
                "name_tr": raw.get("name_tr"), "name_en": raw.get("name_en"),
                "qid": qid, "death_ce": death_ce, "birth_ce": birth_ce,
                "canon": canon, "place_label": raw.get("place_label"),
                "record_count": raw.get("record_count"),
            }
            continue

        field, temporal = _canonical_temporal(death_ce, birth_ce)
        if not temporal:
            stats["dateless"] += 1
            continue

        # İslami YENİ figür → MINT
        pid = pid_minter.mint("person", f"alatli:{rid}")
        professions = pc.classify_profession(raw.get("name_tr") or "") or ["scholar"]
        types = pc.build_type_array(professions)

        provenance = pc.build_provenance(
            source_record_id=f"alatli:{rid}",
            source_kind="secondary_scholarly",
            page_locator=f"Tarihe Yön Veren Metinler, kanon={'+'.join(canon)}",
            edition=EDITION,
            pipeline_name=pipeline_name, pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO, license_uri=LICENSE,
            record_history_note=(
                f"Alatlı senkronik atlasından ilk canonicalization (alatli:{rid}); "
                f"kaynak={raw.get('date_source')} güven={raw.get('confidence')}."),
        )

        person: dict = {
            "@id": pid, "@type": types, "labels": labels,
            "profession": professions, "provenance": provenance,
            field: temporal,
        }
        if qid:
            high = raw.get("confidence") == "high"
            person["authority_xref"] = [{
                "authority": "wikidata", "id": qid,
                "confidence": 1.0 if high else 0.7,
                "method": "imported_from_source",
                "reviewed": False,
                "note": ("Alatlı: korpus/TDV tarihi + Wikidata tarih-teyidi (çift kaynak, date-corroborated)"
                         if high else "Alatlı: ad-eşleşmesi (tek kaynak)"),
            }]
        note_bits = [f"Alatlı 'Tarihe Yön Veren Metinler' ({'+'.join(canon)} kanonu)"]
        if raw.get("place_label"):
            note_bits.append(f"doğum yeri: {raw['place_label']}")
        person["note"] = pc.assemble_note(note_bits)
        stats["mint"] += 1
        yield person

    resolver.close()
    print(f"[canonicalize] alatli: match(augment)={stats['match']} "
          f"mint(İslami-yeni)={stats['mint']} western-held={stats['western_held']} "
          f"review={stats['review']} dateless={stats['dateless']}")
