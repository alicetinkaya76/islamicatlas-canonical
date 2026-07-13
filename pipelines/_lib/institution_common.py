"""
institution_common.py — institution-namespace adapter'larının ortak parçaları
(H11 S6, ADR-015). Üç adapter (konya-city-atlas, maqrizi-khitat,
evliya-institutions) aynı @type eşlemesini ve provenance iskeletini kullanır;
kopya tablo sürümleri birbirinden kayardı.

Alt-tip eşlemesi EDİTORYALDİR ve bilinçli olarak muhafazakârdır: şema
enum'una oturmayan her kategori "other"a düşer ve v1 kategorisi note'ta
korunur (kale/citadel ≠ palace; kanisa_yahud/sinagog ≠ church; bi'r/kuyu ≠
fountain — anlam esnetmek yerine "other").
"""

from __future__ import annotations

import re

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"

SUBTYPE_TO_TYPE = {
    "mosque": "iac:Mosque", "madrasa": "iac:Madrasa", "shrine": "iac:Shrine",
    "hammam": "iac:Hammam", "caravanserai": "iac:Caravanserai",
    "palace": "iac:Palace", "bridge": "iac:Bridge", "church": "iac:Church",
    "fountain": "iac:Fountain", "market": "iac:Market", "tekke": "iac:Tekke",
    "library": "iac:Library", "hospital": "iac:Hospital",
    "observatory": "iac:Observatory",
}

_ROMAN = re.compile(r"^[IVXLC]+\.?$")
_TR_LOWER = str.maketrans("İIÇĞÖŞÜÂÎÛ", "iıçğöşüâîû")
_TR_UPPER = str.maketrans("iıçğöşüâîû", "İIÇĞÖŞÜÂÎÛ")
_CONNECTORS = {"ve", "ile", "veya"}


def _cap_first_alpha(low: str) -> str:
    """İlk ALFABETİK karakteri büyütür — '(kadı' değil '(Kadı'."""
    for i, ch in enumerate(low):
        if ch.isalpha():
            return low[:i] + ch.translate(_TR_UPPER).upper() + low[i + 1:]
    return low


def tr_title(s: str) -> str:
    """Türkçe-dostu başlık düzeni: TÜMÜ-BÜYÜK v1 dizin adlarını ('ABDÜ'L-AZİZ
    MESCİDİ') okunur hale getirir ('Abdü'l-Aziz Mescidi'). Roma rakamları
    ('II.') korunur; tire sonrası segment de büyütülür; 've/ile/veya'
    bağlaçları küçük kalır. İ/ı dönüşümü locale tablosuyla — str.title()
    'İ'yi 'İ̇' yapar."""
    words = []
    for w in s.split():
        if _ROMAN.match(w):
            words.append(w)
            continue
        low_word = w.translate(_TR_LOWER).lower()
        if low_word in _CONNECTORS:
            words.append(low_word)
            continue
        words.append("-".join(_cap_first_alpha(seg.translate(_TR_LOWER).lower())
                              for seg in w.split("-")))
    return " ".join(words)


def build_type(subtype: str) -> list[str]:
    t = SUBTYPE_TO_TYPE.get(subtype)
    return ["iac:Institution", t] if t else ["iac:Institution"]


def founded_from(miladi, hijri, approximate: bool = False) -> dict | None:
    """dates.founding_miladi/hijri → founded_temporal. İkisi de yoksa None
    (şema anyOf bir çapa ister — boş temporal yield edilmez)."""
    t: dict = {}
    if isinstance(miladi, int):
        t["start_ce"] = miladi
    if isinstance(hijri, int) and 1 <= hijri <= 1700:
        t["start_ah"] = hijri
    if not t:
        return None
    t["approximation"] = "circa" if approximate else "exact"
    return t


def resolve_city(resolver, adapter_id: str, name_tr: str, alt: list[str],
                 lat: float, lon: float) -> str | None:
    """Adapter başına BİR kez çağrılır: tüm kayıtların located_in çapası olan
    şehri Tier-2 ile çözer. Eşleşmezse None — located_in boş kalır, asla
    tahmin edilmez (ADR-008)."""
    d = resolver.resolve(
        entity_type="place", adapter_id=adapter_id,
        extracted_record_id=f"{adapter_id}:_city_anchor",
        labels={"prefLabel": {"tr": name_tr}, "altLabel": {"en": alt}},
        coords={"lat": lat, "lon": lon})
    if d.kind == "match":
        return d.matched_pid
    print(f"  WARN city anchor '{name_tr}' unresolved (kind={d.kind}) — "
          f"located_in boş kalacak")
    return None


def base_provenance(rid: str, locator: str, edition: str, pipeline_name: str,
                    pipeline_version: str, now: str, stage_note: str) -> dict:
    return {
        "derived_from": [{
            "source_id": rid,
            "source_type": "digital_corpus",
            "page_or_locator": locator,
            "extraction_method": "structured_json",
            "edition_or_version": edition,
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
            "note": stage_note,
        }],
        "deprecated": False,
    }
