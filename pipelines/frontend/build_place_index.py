#!/usr/bin/env python3
"""place_index.json üretici — "bu yeri kitaplarda oku" köprüsünün veri tarafı.

Yer→kitap ters indeksi: mağaza yer pid'inden, o yerin anıldığı Çekirdek
Külliyat kitaplarına (ve bölümlerine) gidilir. Harita popup'ındaki
"kitaplarda oku" bağlantısı bu dosyayı okur.

Girdi:
    web/public/reading/<pidnum>/mentions.json   (extract_book_mentions.py çıktısı)
        {pid, n_places, places:[{pid,name,lat,lon,total,secs:[...]}], ...}
    web/public/reading/core_shelf.json          books[] → pidnum → name_tr

    NOT: Rafta 17 kitap var ama mentions.json yalnız yer-anılma çıkarımı
    yapılmış kitaplarda bulunur (diğerlerinde layer.json: events/entries/
    routes — yer pid'i içermez). Bu script SADECE mevcut mentions.json
    dosyalarını sayar; eksik kitap için sayı uydurulmaz, sonda raporlanır.

Çıktı:
    web/public/books/place_index.json
        {
          "_doc":     "...",
          "n_places": N,                     # tekil yer pid sayısı
          "places": {
            "iac:place-XXXXXXXX": [          # anahtarlar sıralı
              {"pidnum":"00001293",
               "book":"Fütûhu'l-Büldân (Belâzürî)",
               "total":12,
               "secs":[2,5,9]},              # İLK 6 bölüm (kitap başına)
              ...                            # kitaplar total azalan sırada
            ], ...
          },
          "names": {                         # norm(Arapça ad) → pid köprüsü
            "<norm_ar(ad)>": "iac:place-XXXXXXXX", ...
          }
        }

"names" haritası: pid'siz şehir kayıtları (db.json cities .ar alanı)
popup'tan norm_ar ile pid bulup kitap listesine ulaşır. Normalizasyon
extract_book_mentions.norm_ar'ın KENDİSİ (import edilir; kopya tutulmaz):
hareke temizliği + أإآ→ا + ى→ي, ة→ه YAPILMAZ. Belirsizlik-koruması:
aynı norm-ad birden çok pid'e çıkıyorsa haritaya GİRMEZ.

Determinizm: timestamp yok; tüm anahtarlar sıralı, kitap listesi
(total azalan, pidnum artan) tam sıralı → iki koşu bayt-bayt aynıdır.

Boyut kuralı: çıktı 5 MB'ı aşarsa secs kitap başına 4'e indirilir ve
bu durum stdout'ta açıkça raporlanır (sayı uydurma yok).

Çalıştırma:  python3 pipelines/frontend/build_place_index.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
READING = REPO_ROOT / "web/public/reading"
CORE_SHELF = READING / "core_shelf.json"
OUT_PATH = REPO_ROOT / "web/public/books/place_index.json"

SIZE_LIMIT = 5 * 1024 * 1024  # 5 MB
SECS_CAP_DEFAULT = 6
SECS_CAP_FALLBACK = 4


def _load_norm_ar():
    """extract_book_mentions.norm_ar'ı dosya yolundan import et (tek otorite;
    normalizasyon kuralı burada KOPYALANMAZ — sürüklenme olmasın)."""
    src = REPO_ROOT / "pipelines/reading/extract_book_mentions.py"
    spec = importlib.util.spec_from_file_location("extract_book_mentions", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.norm_ar


def main() -> int:
    norm_ar = _load_norm_ar()

    shelf = json.loads(CORE_SHELF.read_text(encoding="utf-8"))
    name_by_pidnum = {b["pidnum"]: b["name_tr"] for b in shelf["books"]}
    n_shelf = len(shelf["books"])

    # --- mentions.json'ları topla (sıralı klasör gezisi → determinizm) ---
    mention_files = sorted(READING.glob("*/mentions.json"))
    missing = sorted(
        d.name for d in READING.iterdir()
        if d.is_dir() and not (d / "mentions.json").exists()
    )

    # place_pid → [(total, pidnum, book_adi, secs_tam_liste)]
    index: dict[str, list[tuple[int, str, str, list[int]]]] = {}
    # norm(ad) → yer pid kümesi (belirsizlik tespiti için)
    norm_pids: dict[str, set[str]] = {}

    n_books = 0
    for mf in mention_files:
        pidnum = mf.parent.name
        book_name = name_by_pidnum.get(pidnum)
        if book_name is None:
            # rafta olmayan klasör: uydurma ad verilmez, atlanır + raporlanır
            print(f"UYARI: {pidnum} core_shelf.json'da yok — atlandı")
            continue
        data = json.loads(mf.read_text(encoding="utf-8"))
        n_books += 1
        for pl in data["places"]:
            pid = pl["pid"]
            index.setdefault(pid, []).append(
                (int(pl["total"]), pidnum, book_name, list(pl["secs"]))
            )
            nm = norm_ar(pl["name"]).strip()
            if nm:
                norm_pids.setdefault(nm, set()).add(pid)

    _PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
    _pv = {}

    def _kaz(pid):
        try:
            n = int(str(pid).rsplit("-", 1)[-1])
        except (ValueError, AttributeError):
            return None
        gor = set()
        while True:
            if n not in _pv:
                f = _PLACE_DIR / f"iac_place_{n:08d}.json"
                try:
                    _pv[n] = (json.loads(f.read_text(encoding="utf-8"))
                              .get("provenance") or {})
                except (OSError, json.JSONDecodeError):
                    _pv[n] = {}
            pr = _pv[n]
            if not pr:
                return None
            if not pr.get("deprecated"):
                return f"iac:place-{n:08d}"
            h = pr.get("deprecated_in_favor_of")
            try:
                h = int(str(h).rsplit("-", 1)[-1])
            except (ValueError, AttributeError):
                return None
            if h in gor:
                return None
            gor.add(n)
            n = h

    # H60: `index` anahtarları pid'dir ve 3'ü ÖLÜYDÜ; bu anahtarlar
    # `places` sözlüğüne aynen geçiyor ve "bu yeri kitaplarda oku" köprüsü
    # oradan gidiyor. Çakışmayan yeniden adlandırılır; kazanan ZATEN
    # anahtarsa DOKUNULMAZ — iki kaydın anılma listelerini (total/secs)
    # birleştirmek bir VERİ kararıdır, otomatik yapılmaz.
    _yeniden, _cakisan = 0, 0
    for _k in list(index):
        _w = _kaz(_k)
        if _w is None or _w == _k:
            continue
        if _w in index:
            _cakisan += 1
            continue
        index[_w] = index.pop(_k)
        _yeniden += 1

    # --- places gövdesini kur (verilen secs sınırıyla) ---
    def build_places(secs_cap: int) -> dict:
        places = {}
        for pid in sorted(index):
            rows = sorted(index[pid], key=lambda r: (-r[0], r[1]))
            places[pid] = [
                {"pidnum": pn, "book": bk, "total": tot, "secs": secs[:secs_cap]}
                for tot, pn, bk, secs in rows
            ]
        return places

    # --- names haritası: yalnız TEKİL norm-ad → pid ---
    # H60: hedef ÖLÜ bir yer olabiliyordu (ölçüldü: 3 ad). Bu köprü ad
    # aramasından yer kaydına gider; emekli pid boş ekran demektir.

    names = {}
    n_olu = 0
    for nm, pids in sorted(norm_pids.items()):
        if len(pids) != 1:
            continue
        kaz = _kaz(next(iter(pids)))
        if kaz is None:
            n_olu += 1          # çözülemeyen ölü hedef: ad hiç yazılmaz
            continue
        names[nm] = kaz
    n_ambiguous = sum(1 for pids in norm_pids.values() if len(pids) > 1)

    def render(secs_cap: int) -> bytes:
        doc = {
            "_doc": (
                "Yer→kitap ters indeksi (build_place_index.py). places: "
                "mağaza yer pid'i → o yeri anan kitaplar, total azalan; "
                f"secs = ilk {secs_cap} bölüm indeksi. names: "
                "norm_ar(Arapça ad) → pid, yalnız tekil eşleşmeler "
                "(belirsiz adlar bilinçli dışarıda). "
                "Kaynak: reading/<pidnum>/mentions.json."
            ),
            "n_places": len(index),
            "places": build_places(secs_cap),
            "names": names,
        }
        return (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")

    secs_cap = SECS_CAP_DEFAULT
    payload = render(secs_cap)
    if len(payload) > SIZE_LIMIT:
        secs_cap = SECS_CAP_FALLBACK
        payload = render(secs_cap)
        print(f"BOYUT: 5 MB aşıldı → secs kitap başına {secs_cap}'e indirildi "
              f"(yeni boyut {len(payload):,} B)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_bytes(payload)

    n_pairs = sum(len(v) for v in index.values())
    print(f"kitap (mentions.json'lu): {n_books} / rafta {n_shelf}")
    if missing:
        print(f"mentions.json OLMAYAN klasörler ({len(missing)}): "
              + ", ".join(missing))
    print(f"tekil yer pid: {len(index)}")
    print(f"yer×kitap çifti: {n_pairs}")
    print(f"names (tekil norm-ad): {len(names)}  |  elenen belirsiz ad: {n_ambiguous}"
          f"  |  ölü hedef yüzünden elenen: {n_olu}")
    print(f"places anahtarı: ölü→kazanan {_yeniden} · ÇAKIŞTI (elle karar) {_cakisan}")
    print(f"secs sınırı: {secs_cap}")
    print(f"çıktı: {OUT_PATH.relative_to(REPO_ROOT)}  ({len(payload):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
