"""
extract.py — scholars kaynağı, TAM EVREN (H11 S4 revizyonu).

H10 S3'te isim otoritesi yalnız scholars.csv'ydi (49 âlim); v1 uygulamasının
db.json'ı gelince (kullanıcı teslimi, 2026-07-12) evren 450 âlime açıldı:
db.json.scholars (id 1..462; tr/en/ar ad + b/d yılları + koordinat + üç-dilli
anlatı + tabaka/râvi bilgisi) ⋈ identity kartları (296) ⋈ meta (67) ⋈
scholars.csv'nin zengin anlatı kolonları (49).

Çıktı sözleşmesi H10 S3 ile aynı (source_record_id scholars:<id>) —
işlenmiş 49'un augment/mint'leri idempotent kalır.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterator

_PLACEHOLDER = "—"


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        if not v or v == _PLACEHOLDER:
            return None
    return v


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    db_path = next(p for p in input_paths if p.name == "db.json")
    conv_path = next(p for p in input_paths if p.name == "scholars_converted.json")
    csv_path = next(p for p in input_paths if p.suffix == ".csv")

    conv = json.loads(conv_path.read_text(encoding="utf-8"))
    identity = conv.get("identity", {})
    meta = conv.get("meta", {})
    csv_rows = {r["scholar_id"]: r for r in
                csv.DictReader(csv_path.open(encoding="utf-8"))}

    scholars = json.loads(db_path.read_text(encoding="utf-8")).get("scholars", [])
    for s in scholars:
        sid = str(s.get("id"))
        row = csv_rows.get(sid) or {}
        yield {
            "source_record_id": f"scholars:{sid}",
            "raw_data": {
                # db.json birincil isim/tarih otoritesi
                "scholar_id": sid,
                "name_tr": _clean(s.get("tr")),
                "name_en": _clean(s.get("en")),
                "name_ar": _clean(s.get("ar")),
                "name_original": _clean(row.get("name_original")),
                "birth_ce": s.get("b"),
                "death_ce": s.get("d"),
                "lat": s.get("lat"), "lon": s.get("lon"),
                "narrative_tr": _clean(s.get("narr_tr")) or _clean(row.get("narrative_tr")),
                "narrative_en": _clean(s.get("narr_en")) or _clean(row.get("narrative_en")),
                "narrative_ar": _clean(s.get("narr_ar")),
                "field": _clean(s.get("disc_tr")) or _clean(row.get("field")),
                "sub_field": _clean(row.get("sub_field")),
                "tabaqa": _clean(s.get("tabaqa_tr")),
                "identity": {k: _clean(v) for k, v in (identity.get(sid) or {}).items()},
                "meta": {k: _clean(v) for k, v in (meta.get(sid) or {}).items()},
            },
            "source_locator": {"file": "db.json", "scholar_id": sid},
        }
