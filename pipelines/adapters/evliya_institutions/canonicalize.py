"""
canonicalize.py — Evliyâ yapıları (2,608) → iac:institution-, Tier-2
TWO-TRACK (darp-islam deseni, institution sürümü).

konya-city-atlas + maqrizi-khitat mint'lerinden SONRA, lookup yeniden
kurulmuşken koşar: Evliyâ Konya'yı ve Kahire'yi gezdi — Alâeddin Camii gibi
yapılar iki kaynakta birden var.

  TRACK A (match): yapı zaten mint'li → sidecar augment olayı
    (derived_from_layers += evliya-celebi + history kanıtı; jenerik
    apply_layer_augments.py uygular). Kayıt İÇERİĞİNE dokunulmaz.
  TRACK B (new): tam mint — üç-dilli ad + Seyahatnâme tasvirleri + koordinat.
  REVIEW: resolver kuyruğuna düşer, mint EDİLMEZ (sidecar'da sayılır).

located_in HİÇ doldurulmaz: Evliyâ kayıtlarında şehir adı alanı yok, yalnız
koordinat var; koordinattan şehre çıkarım = tahmin (ADR-008'e aykırı).
Harita coords'tan çalışır; place bağlama Faz 2 zenginleştirmesi.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver
from pipelines._lib.institution_common import base_provenance, build_type

EDITION = ("islamicatlas.org v1 Evliyâ Çelebi Seyahatnâme atlas layer "
           "(evliya_atlas_layer.json; 10 voyage, tasvirler tr/en/ar)")

_CAT_TO_SUBTYPE = {
    "cami": "mosque", "mescit": "mosque", "türbe": "shrine",
    "hamam": "hammam", "tekke": "tekke", "han": "caravanserai",
    "saray": "palace", "medrese": "madrasa", "köprü": "bridge",
    "kilise": "church", "çeşme": "fountain", "bedesten": "market",
}

_HTML_TAG = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    out = _HTML_TAG.sub("", text).strip()
    return out[:5000] if out else None


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_institution_evliya")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("evliya_institutions")
    if side is None:
        side = {}
    side.setdefault("augments", {})
    side.setdefault("_review_skipped", {})

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — rebuild it AFTER the "
                           "konya/maqrizi runs (two-track needs the fresh "
                           "institution namespace in the index).")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "match": 0, "review": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]

        labels: dict = {"prefLabel": {}}
        for lang, field in (("tr", "name_tr"), ("en", "name_en"), ("ar", "name_ar")):
            if raw.get(field):
                labels["prefLabel"][lang] = raw[field]

        decision = resolver.resolve(
            entity_type="institution", adapter_id="evliya-institutions",
            extracted_record_id=rid, labels=labels,
            coords={"lat": raw["lat"], "lon": raw["lng"]})

        if decision.kind == "match":
            stats["match"] += 1
            side["augments"].setdefault(decision.matched_pid, []).append({
                "evliya_id": raw["id"],
                "voyage_id": raw.get("voyage_id"),
                "confidence": decision.confidence,
                "name_tr": raw.get("name_tr"),
            })
            continue
        if decision.kind == "review":
            stats["review"] += 1
            side["_review_skipped"][rid] = {
                "queue_id": decision.queue_id,
                "confidence": decision.confidence,
                "name_tr": raw.get("name_tr"),
            }
            continue

        subtype = _CAT_TO_SUBTYPE[raw["category"]]  # 12 kategori — tamamı eşleşik
        desc = {}
        for lang, field in (("tr", "description_tr"), ("en", "description_en"),
                            ("ar", "description_ar")):
            v = _clean(raw.get(field))
            if v:
                desc[lang] = v
        if desc:
            labels["description"] = desc

        pid = pid_minter.mint("institution", rid)
        record = {
            "@id": pid,
            "@type": build_type(subtype),
            "institution_subtype": subtype,
            "labels": labels,
            "coords": {"lat": raw["lat"], "lon": raw["lng"]},
            "derived_from_layers": ["evliya-celebi"],
            "note": (f"v1 kategori: {raw['category']} · Evliyâ Çelebi "
                     f"Seyahatnâmesi, voyage {raw.get('voyage_id')}")[:2000],
            "provenance": base_provenance(
                rid,
                f"evliya_atlas_layer.json id={raw['id']} "
                f"voyage={raw.get('voyage_id')}",
                EDITION, pipeline_name, pipeline_version, now,
                f"Institution namespace (H11 S6, ADR-015): initial "
                f"canonicalization by {pipeline_name} (Tier-2 kind=new)."),
        }
        stats["minted"] += 1
        yield record

    resolver.close()
    print(f"[canonicalize] evliya-institutions: minted={stats['minted']} "
          f"match(augment)={stats['match']} review(skipped)={stats['review']}")
