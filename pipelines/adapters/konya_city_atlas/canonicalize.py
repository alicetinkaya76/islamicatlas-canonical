"""
canonicalize.py — Konya City Atlas (583) → iac:institution- (NAMESPACE
AKTİVASYONU, ADR-015 / H11 Karar 6).

Namespace boş olduğundan two-track yok — hepsi mint. located_in tüm kayıtlar
için tek Tier-2 çözümüyle Konya'ya bağlanır (şehir çapası; eşleşmezse boş).

patron_dynasty AÇIK alias tablosuyla bağlanır (fuzzy DEĞİL): mağazada iki
'Karaman' hanedanı var — dynasty-00000023 Trablusgarp Karamanlıları (Libya!)
ile dynasty-00000124 Konya Karamanoğulları — fuzzy eşleme bunları
karıştırırdı. 'Selçuklu' Konya bağlamında Anadolu Selçuklularıdır (00000107;
editoryal, Konya = Rûm Selçuklu başkenti). 'Bizans'/'Cumhuriyet' katalog
dışı → yalnız note'ta.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from pipelines._lib.entity_resolver import EntityResolver
from pipelines._lib.institution_common import (
    base_provenance, build_type, founded_from, resolve_city, tr_title)

EDITION = ("islamicatlas.org v1 Konya City Atlas (İ.H. Konyalı, Konya Tarihi "
           "2007 dizini + Konyapedia zenginleştirmesi)")

# v1 category → institution_subtype (şema enum'u). Eşleşmeyen → other.
_CAT_TO_SUBTYPE = {
    "cami": "mosque", "mescit": "mosque",
    "medrese": "madrasa", "darulhuffaz": "madrasa", "mektep": "madrasa",
    "turbe": "shrine", "cesme": "fountain", "hamam": "hammam",
    "han": "caravanserai", "zaviye": "tekke", "tekke": "tekke",
    "hankah": "tekke", "kilise": "church", "kopru": "bridge",
    "kutuphane": "library", "saglik": "hospital", "ticaret": "market",
}

# MINT EDİLMEYEN kategoriler (needs_human_review, North Star): 'turizm'
# doğa+modern otel karışımı (Beyşehir GÖLÜ, Alâeddin TEPESİ, Dedeman Oteli);
# 'kultur_varligi' içinde bir KASABA (Ereğli) ve höyük (Çatalhöyük) var.
# Yapı olup olmadığına tarihçi karar verir — sidecar kuyruğuna düşer.
# 'vakif' KALIR: vakıf = endowed institution, şema tanımının açık kapsamı.
_BORDERLINE_CATS = {"turizm", "kultur_varligi"}

# patron.dynasty (kaynak dizgisi) → dynasty PID. Editoryal, birebir anahtar.
_DYNASTY_ALIAS = {
    "Selçuklu": "iac:dynasty-00000107",          # Anadolu Selçukluları
    "Osmanlı": "iac:dynasty-00000130",
    "Osmanlı (genişletme)": "iac:dynasty-00000130",
    "Karamanoğulları": "iac:dynasty-00000124",   # Konya kolu (23 = Trablusgarp!)
}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_institution_konya")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    sidecars = options.get("sidecars") or {}
    side = sidecars.get("konya_institutions")
    if side is None:
        side = {}
    side.setdefault("borderline_review", [])

    repo_root = Path(pid_minter.state_dir).parent.parent
    resolver = EntityResolver(repo_root)
    if resolver._connect() is None:
        raise RuntimeError("lookup.sqlite missing — build it first.")
    konya_pid = resolve_city(resolver, "konya-city-atlas", "Konya",
                             ["Konya", "Iconium"], 37.8746, 32.4932)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "dyn_linked": 0, "coords": 0, "subtype_other": 0,
             "borderline": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]

        if raw.get("category") in _BORDERLINE_CATS:
            stats["borderline"] += 1
            side["borderline_review"].append({
                "source_record_id": rid,
                "name_tr": raw.get("name_tr"),
                "category": raw.get("category"),
                "reason": "yapı/doğa-modern sınırı — tarihçi kararı gerekli",
            })
            continue

        subtype = _CAT_TO_SUBTYPE.get(raw.get("category") or "", "other")
        if subtype == "other":
            stats["subtype_other"] += 1

        labels: dict = {"prefLabel": {"tr": tr_title(raw["name_tr"])}}
        if raw.get("name_en"):
            labels["prefLabel"]["en"] = raw["name_en"]
        if raw.get("name_ar"):
            labels["prefLabel"]["ar"] = raw["name_ar"]
        # TÜMÜ-BÜYÜK dizin biçimi aynen altLabel'da kalır (birebir arama izi).
        if raw["name_tr"] != labels["prefLabel"]["tr"]:
            labels["altLabel"] = {"tr": [raw["name_tr"]]}
        desc = {}
        if raw.get("konyapedia_excerpt_tr"):
            desc["tr"] = raw["konyapedia_excerpt_tr"][:5000]
        if raw.get("konyali_notes_en"):
            desc["en"] = raw["konyali_notes_en"][:5000]
        if raw.get("konyali_notes_ar"):
            desc["ar"] = raw["konyali_notes_ar"][:5000]
        if desc:
            labels["description"] = desc

        pid = pid_minter.mint("institution", rid)
        loc = raw.get("location") or {}
        kp_url = raw.get("konyapedia_url") or ""
        record = {
            "@id": pid,
            "@type": build_type(subtype),
            "institution_subtype": subtype,
            "labels": labels,
            "derived_from_layers": ["konya-city-atlas"],
            "provenance": base_provenance(
                rid,
                f"konya.json id={raw['id']}" + (f"; {kp_url}" if kp_url else ""),
                EDITION, pipeline_name, pipeline_version, now,
                f"Institution namespace activation (H11 S6, ADR-015): initial "
                f"canonicalization by {pipeline_name}."),
        }
        if isinstance(loc.get("lat"), (int, float)) and isinstance(loc.get("lng"), (int, float)):
            record["coords"] = {"lat": loc["lat"], "lon": loc["lng"]}
            stats["coords"] += 1
        if konya_pid:
            record["located_in"] = konya_pid

        dates = raw.get("dates") or {}
        founded = founded_from(dates.get("founding_miladi"),
                               dates.get("founding_hijri"),
                               bool(dates.get("founding_approximate")))
        if founded:
            record["founded_temporal"] = founded

        patron = raw.get("patron") or {}
        dyn_name = patron.get("dynasty")
        note_bits = [f"v1 kategori: {raw.get('category')}"
                     + (f"/{raw['sub_category']}" if raw.get("sub_category") else "")]
        if raw.get("period"):
            note_bits.append(f"Dönem: {raw['period']}")
        if raw.get("current_status"):
            note_bits.append(f"Durum: {raw['current_status']}")
        if loc.get("mahalle"):
            note_bits.append(f"Mahalle: {loc['mahalle']}")
        if dyn_name:
            dyn_pid = _DYNASTY_ALIAS.get(dyn_name)
            if dyn_pid:
                record["patron_dynasty"] = dyn_pid
                stats["dyn_linked"] += 1
            else:
                note_bits.append(f"Hâmi hanedan (katalog dışı): {dyn_name}")
        if patron.get("notes"):
            note_bits.append(str(patron["notes"])[:400])
        record["note"] = " · ".join(note_bits)[:2000]

        stats["minted"] += 1
        yield record

    resolver.close()
    print(f"[canonicalize] konya-city-atlas: minted={stats['minted']} "
          f"coords={stats['coords']} dynasty-linked={stats['dyn_linked']} "
          f"subtype-other={stats['subtype_other']} "
          f"borderline-queued={stats['borderline']} "
          f"located_in={'Konya→' + konya_pid if konya_pid else 'UNRESOLVED'}")
