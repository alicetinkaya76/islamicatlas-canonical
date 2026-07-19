"""
extract.py — kitap-katmanlarından TARİHLİ olaylar (H15).

Girdi: data/sources/book-layers/{00001293,00001099,00000809}_events.json
(Fütûh, Meğâzî, Sîre — H14 çıkarımları). Şema temporal İSTER → yalnız
date_h'li kayıtlar yield edilir; tarihsizler kitap-içi katmanda yaşamaya
devam eder (sayaçla raporlanır).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

BOOKS = {
    "00001293": ("futuh-buldan", "Fütûhu'l-Büldân (Belâzürî)"),
    "00001099": ("maghazi", "Kitâbü'l-Meğâzî (Vâkıdî)"),
    "00000809": ("sira", "es-Sîretü'n-Nebeviyye (İbn Hişâm)"),
    # H16 parti-2 kronikleri (yıl-başlıklı → yüksek tarihli-oran)
    "00000331": ("kamil", "el-Kâmil fi't-Târîh (İbn el-Esîr)"),
    "00000508": ("suluk", "es-Sülûk (Makrîzî)"),
    "00000338": ("tabari", "Târîhu't-Taberî"),
    "00000880": ("muruj", "Mürûcü'z-Zeheb (Mes'ûdî)"),
}


def extract(input_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    skipped = 0
    for path in input_paths:
        pidnum = path.name.split("_")[0]
        prefix, book_name = BOOKS[pidnum]
        layer = json.loads(path.read_text(encoding="utf-8"))
        for r in layer["records"]:
            if not r.get("date_h"):
                skipped += 1
                continue
            yield {
                "source_record_id": f"{prefix}:{r['seq']:04d}",
                "raw_data": {**r, "_book": book_name, "_prefix": prefix,
                             "_work_pid": layer["metadata"]["source_work"],
                             "_pidnum": pidnum},
                "source_locator": {"file": path.name, "id": r["seq"]},
            }
    print(f"[extract] tarihsiz atlanan (katmanda kalır): {skipped}")
