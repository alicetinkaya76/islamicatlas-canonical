"""
extract.py — kitap-katmanlarından şehir YAPILARI (H15).

Girdi: data/sources/book-layers/{00001848,00000261}_structures.json
(Ezrakî Ahbâru Mekke, Hatîb Târîhu Bağdâd — H14 çıkarımları).
type=mountain (coğrafi öğe, yapı değil) ve geo_suspect (uzak-homograf)
kayıtları yield edilmez.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

BOOKS = {
    "00001848": ("azraqi-makka", "Ahbâru Mekke (Ezrakî)", "iac:place-00011505"),
    "00000261": ("tarikh-baghdad", "Târîhu Bağdâd (Hatîb el-Bağdâdî)", "iac:place-00002027"),
    "00000228": ("tarikh-dimashq", "Târîhu Dımaşk (İbn Asâkir)", "iac:place-00004883"),
}


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    skipped = 0
    for path in input_paths:
        pidnum = path.name.split("_")[0]
        prefix, book_name, city_pid = BOOKS[pidnum]
        layer = json.loads(path.read_text(encoding="utf-8"))
        for r in layer["records"]:
            if r.get("type") == "mountain" or r.get("geo_suspect"):
                skipped += 1
                continue
            yield {
                "source_record_id": f"{prefix}:{r['seq']:04d}",
                "raw_data": {**r, "_book": book_name, "_prefix": prefix,
                             "_city_pid": city_pid, "_pidnum": pidnum,
                             "_work_pid": layer["metadata"]["source_work"]},
                "source_locator": {"file": path.name, "id": r["seq"]},
            }
    print(f"[extract] atlanan (dağ/şüpheli): {skipped}")
