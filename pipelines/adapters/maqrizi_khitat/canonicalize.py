"""
canonicalize.py — Makrîzî Hıtat Kahire yapıları (801) → iac:institution-
(ADR-015 / H11 Karar 6, konya-city-atlas ile aynı koşuda).

Hepsi mint (namespace bu koşuda dolduruluyor); located_in tek Tier-2
çözümüyle Kahire'ye bağlanır. Alt-tip eşlemesi muhafazakâr: qal'a (kale),
kanisa_yahud (sinagog), bi'r (kuyu), dar (konak), hikr (arsa tahsisi),
birka/maydan/jazira/sijn/sina'a → "other" + v1 kategorisi note'ta —
anlam esnetilmez. dayr (manastır) ve kanisa → church (Hristiyan kurumu).

patron_dynasty AÇIK alias tablosu (fuzzy değil): kaynaktaki 12 ayrık hanedan
dizgisinin tamamı sayımla çıkarıldı; Bahrî/Burcî Memlük ayrımı mağazada tek
kayıt (dynasty-00000031) olduğundan taban kayda bağlanır, kol adı note'ta
zaten (dönem alanı) korunur.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from pipelines._lib.institution_common import (
    base_provenance, build_type, founded_from)

EDITION = ("islamicatlas.org v1 Maqrīzī Khiṭaṭ atlas layer (el-Mevâʿiz "
           "ve'l-iʿtibâr; Kahire/Fustat yapıları, üç-dilli adlarla "
           "zenginleştirilmiş cairo.json formu)")

_CAT_TO_SUBTYPE = {
    "mosque": "mosque", "masjid": "mosque", "masjid_qarafa": "mosque",
    "masjid_jabal": "mosque", "musalla": "mosque",
    "madrasa": "madrasa",
    "dayr": "church", "kanisa": "church",
    "suq": "market", "qaysariyya": "market",
    "hammam": "hammam",
    "jawsaq": "palace",
    "zawiya": "tekke", "khanqah": "tekke", "ribat": "tekke",
    "ribat_qarafa": "tekke",
    "qantara": "bridge", "jisr": "bridge",
    "khan": "caravanserai",
    "maristan": "hospital",
    "mashhad": "shrine", "shrine": "shrine", "maqbara": "shrine",
}

_DYNASTY_ALIAS = {
    "Memlükler": "iac:dynasty-00000031",
    "Memlükler (Bahrî)": "iac:dynasty-00000031",
    "Memlükler (Burcî)": "iac:dynasty-00000031",
    "Eyyûbîler": "iac:dynasty-00000030",
    "Fâtımîler": "iac:dynasty-00000027",
    "Hulefâ-i Râşidîn": "iac:dynasty-00000001",
    "Râşidîn": "iac:dynasty-00000001",
    "Emevîler": "iac:dynasty-00000002",
    "Tûlûnîler": "iac:dynasty-00000025",
    "Abbâsîler (Tolunoğulları öncesi)": "iac:dynasty-00000003",
    "İhşîdîler": "iac:dynasty-00000026",
}


def canonicalize(extracted_records: Iterator[dict], pid_minter, reconciler=None,
                 options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    pipeline_name = options.get("pipeline_name", "canonicalize_institution_maqrizi")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    # Şehir çapası: EDİTORYAL SABİT (H11 Karar 6). Tier-2 koşusu kind=review
    # verdi (conf 0.8615: label 1.0 + spatial 1.0, ama sorgu alt-etiket
    # tahminleri adayın 'Medinetü'l-Mu'izz' alt'ıyla örtüşmeyince alt=0.31
    # ortalamayı 0.9 eşiğinin altına çekti — ağırlık artefaktı). Tek aday
    # iac:place-00009399 (Yâkût El-Kâhire, koordinat birebir 30.0444/31.2357,
    # tasviri 969 Fâtımî kuruluşunu verir) — kimlik şüphesiz; hanedan alias
    # tablosuyla aynı sınıfta belgeli editoryal bağ, resolver oyunlanmaz.
    cairo_pid = "iac:place-00009399"

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"minted": 0, "dyn_linked": 0, "coords": 0, "subtype_other": 0}

    for extracted in extracted_records:
        raw = extracted["raw_data"]
        rid = extracted["source_record_id"]

        subtype = _CAT_TO_SUBTYPE.get(raw.get("category") or "", "other")
        if subtype == "other":
            stats["subtype_other"] += 1

        labels: dict = {"prefLabel": {}}
        for lang, field in (("tr", "name_tr"), ("en", "name_en"), ("ar", "name_ar")):
            if raw.get(field):
                labels["prefLabel"][lang] = raw[field]
        if raw.get("source_excerpt_ar"):
            labels["description"] = {"ar": raw["source_excerpt_ar"][:5000]}

        pid = pid_minter.mint("institution", rid)
        record = {
            "@id": pid,
            "@type": build_type(subtype),
            "institution_subtype": subtype,
            "labels": labels,
            "derived_from_layers": ["maqrizi-khitat"],
            "provenance": base_provenance(
                rid,
                f"cairo.json id={raw['id']}; Hıtat satır {raw.get('source_line')}",
                EDITION, pipeline_name, pipeline_version, now,
                f"Institution namespace activation (H11 S6, ADR-015): initial "
                f"canonicalization by {pipeline_name}."),
        }
        loc = raw.get("location") or {}
        if isinstance(loc.get("lat"), (int, float)) and isinstance(loc.get("lng"), (int, float)):
            record["coords"] = {"lat": loc["lat"], "lon": loc["lng"]}
            stats["coords"] += 1
        if cairo_pid:
            record["located_in"] = cairo_pid

        dates = raw.get("dates") or {}
        founded = founded_from(dates.get("founding_miladi"), dates.get("founding_hijri"))
        if founded:
            record["founded_temporal"] = founded

        note_bits = [f"v1 kategori: {raw.get('category')}"
                     + (f"/{raw['subcategory']}" if raw.get("subcategory") else "")]
        if raw.get("period"):
            note_bits.append(f"Dönem: {raw['period']}")
        if raw.get("current_status"):
            note_bits.append(f"Durum: {raw['current_status']}")
        if loc.get("geocoding_confidence") == "low":
            note_bits.append("Koordinat düşük güvenilirlikli (v1 geocoding)")
        dyn = raw.get("dynasty") or {}
        dyn_name = dyn.get("tr") if isinstance(dyn, dict) else dyn
        if dyn_name:
            dyn_pid = _DYNASTY_ALIAS.get(dyn_name)
            if dyn_pid:
                record["patron_dynasty"] = dyn_pid
                stats["dyn_linked"] += 1
            else:
                note_bits.append(f"Hâmi hanedan (katalog dışı): {dyn_name}")
        patron = raw.get("patron") or {}
        if patron.get("name"):
            note_bits.append(f"Bâni: {patron['name']}")
        record["note"] = " · ".join(note_bits)[:2000]

        stats["minted"] += 1
        yield record

    print(f"[canonicalize] maqrizi-khitat: minted={stats['minted']} "
          f"coords={stats['coords']} dynasty-linked={stats['dyn_linked']} "
          f"subtype-other={stats['subtype_other']} "
          f"located_in={'Kahire→' + cairo_pid if cairo_pid else 'UNRESOLVED'}")
