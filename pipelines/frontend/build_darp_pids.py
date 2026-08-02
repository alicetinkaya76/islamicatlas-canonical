#!/usr/bin/env python3
"""Darphane katmanına pid köprüsü (H53).

SORUN (H51 yer denetimi): `darpislam_lite.json` 3.381 darphane taşıyor ama
**pid alanı olan kayıt sayısı 0**. Oysa `lookup.sqlite`'ta 2.338 `darp-islam:*`
curie'si zaten var ve hepsi `iac:place-*`'e bağlı. Sonuç: darphaneler merkezî
deftere hiç bağlanamıyordu; denetimin ölçtüğü "2.481 aktif yer hiçbir görünümde
yok" kümesinin en büyük parçası (2.226) buydu.

NE YAPAR: v1'in `darpislam_lite.json` dosyasına DOKUNMADAN yanına bir
pid haritası çıkarır. Kart, pid'i olan darphaneden Yâkût kaydına
(`#yaqut?pid=`) ve merkezî deftere geçebilir.

NE YAPMAZ:
  • v1 dosyasını değiştirmez (o dosya v1'e SYMLINK olan dizinde; yazılmaz).
  • Curie'si olmayan 1.043 darphane için pid UYDURMAZ. Ad benzerliğiyle
    eşleştirme YAPILMAZ — aynı adı taşıyan farklı darphaneler olağandır ve
    yanlış eşleşme, kullanıcıyı başka bir şehre götürür. Onlar dürüstçe
    pid'siz kalır.

Çıktı: web/public/view-data/darp_pids.json
Determinizm: id sıralı, timestamp yok.
"""

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SQLITE = REPO / "data" / "_index" / "lookup.sqlite"
LITE = REPO / "web" / "public" / "data" / "darpislam_lite.json"
PLACE_DIR = REPO / "data" / "canonical" / "place"
OUT = REPO / "web" / "public" / "view-data" / "darp_pids.json"


def main() -> None:
    if not (SQLITE.is_file() and LITE.is_file()):
        print("atlandı: lookup.sqlite ya da darpislam_lite yok")
        return

    d = json.loads(LITE.read_text(encoding="utf-8"))
    mints = d if isinstance(d, list) else (d.get("mints") or [])
    lite_ids = {str(m.get("id")) for m in mints if m.get("id") is not None}

    con = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE 'darp-islam:%'"
    ).fetchall()
    con.close()

    # YUMUŞAK-SİLİNMİŞ yere bağ verilmez: kayıt canonical'da yaşıyor ama
    # yayınlanan katmanlarda görünmüyor; bağ boş ekrana götürürdü.
    # (Kişi tarafında aynı ders H49'da alındı: "pid yaşar" ≠ "UI bulur".)
    def deprecated(pid: str) -> bool:
        try:
            num = int(str(pid).rsplit("-", 1)[-1])
        except ValueError:
            return True
        p = PLACE_DIR / f"iac_place_{num:08d}.json"
        if not p.is_file():
            return True
        prov = (json.loads(p.read_text(encoding="utf-8")).get("provenance") or {})
        return bool(prov.get("deprecated"))

    esleme, atlanan_dep, atlanan_yok = {}, 0, 0
    for source_id, pid in rows:
        darp_id = source_id.split(":", 1)[1]
        if darp_id not in lite_ids:
            atlanan_yok += 1
            continue
        if deprecated(pid):
            atlanan_dep += 1
            continue
        esleme[darp_id] = pid

    doc = {
        "_doc": ("Darphane (darp-islam) → canonical yer pid haritası. v1'in "
                 "darpislam_lite.json dosyası DEĞİŞTİRİLMEZ; bu yan dosya kartın "
                 "merkezî deftere geçmesini sağlar. Curie'si olmayan darphaneye "
                 "pid UYDURULMAZ — ad benzerliğiyle eşleştirme yapılmaz. "
                 "Üretici: build_darp_pids.py"),
        "counts": {
            "darphane": len(mints),
            "pid_bulunan": len(esleme),
            "pid_yok": len(mints) - len(esleme),
            "atlanan_yumusak_silinmis": atlanan_dep,
            "atlanan_lite_disi": atlanan_yok,
        },
        "pids": {k: esleme[k] for k in sorted(esleme, key=lambda x: int(x) if x.isdigit() else 0)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    c = doc["counts"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  darphane        : {c['darphane']}")
    print(f"  pid bulunan     : {c['pid_bulunan']} (%{c['pid_bulunan']*100//max(c['darphane'],1)})")
    print(f"  pid YOK (dürüst): {c['pid_yok']}")
    if atlanan_dep:
        print(f"  yumuşak-silinmiş yere bağ verilmedi: {atlanan_dep}")


if __name__ == "__main__":
    main()
