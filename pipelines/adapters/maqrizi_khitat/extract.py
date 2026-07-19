"""
extract.py — cairo.json (Makrîzî Hıtat atlas katmanı, 801 yapı) → intermediate.

Kaynak: islamicatlas.org v1'in Makrîzî *el-Mevâʿiz ve'l-iʿtibâr bi-zikri'l-
hıtat ve'l-âsâr* çıkarımı (Kahire/Fustat yapıları; source_excerpt_ar Makrîzî
metninden). data/sources/maqrizi-khitat/maqrizi_khitat_atlas_layer.json aynı
801 kaydın yalın formudur — zengin form (üç-dilli adlar, dates, dynasty,
patron) bu dosyadır; ikisi ayrı kaynak DEĞİLDİR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    for path in input_paths:
        with path.open(encoding="utf-8") as fh:
            for row in json.load(fh):
                yield {
                    "source_record_id": f"maqrizi-khitat:{row['id']}",
                    "raw_data": row,
                    "source_locator": {"file": path.name, "id": row["id"]},
                }
