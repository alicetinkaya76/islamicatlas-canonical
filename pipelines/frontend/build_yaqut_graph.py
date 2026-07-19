#!/usr/bin/env python3
"""yaqut_graph.json üretici — Yâkût "Yer Grafı" (PlaceGraph) sekmesinin verisi.

Ne üretir:
    web/public/yaqut_graph.json          (PlaceGraph'ın fetch ettiği asıl yol:
                                          `${BASE_URL}yaqut_graph.json` → public kökü)
    web/public/data/yaqut_graph.json     (diğer yaqut_* veri dosyalarıyla aynı
                                          klasörde tutulan eş kopya)

Kaynak:
    web/public/data/yaqut_lite.json      12.954 yer (id, ht Türkçe ad, h Arapça ad,
                                          gt tip, pc Ziriklî kişi sayısı)
    web/public/data/yaqut_crossref.json  yerId → Ziriklî kişi listesi (kişi alanı: id)

Graf mantığı:
    Düğüm  = crossref kaydı olan yer (606 yer; yalnızca bunlar düğüm olur).
    Kenar  = iki yerin AYNI Ziriklî kişisini paylaşması (crossref kesişimi).
    Ağırlık (w) = ortak kişi sayısı.
    Min ağırlık eşiği 1'dir; kenar sayısı EDGE_CAP'i (50.000) aşarsa eşik 2'ye
    çekilir ve bu, çıktının `meta.min_weight` alanına yazılır. (Bu veriyle
    w>=1 toplam 1.338 kenar üretir; eşik 1'de kalır.)

Şema (YaqutAdvanced.jsx → PlaceGraph'ın okuduğu alanlar):
    nodes: [{id, n, ht, gt, pc}]   # id: sayısal yer id'si; n: görünen ad
                                   # (Arapça `h`, dir="rtl" ile gösteriliyor)
    edges: [{s, t, w}]             # s/t: kaynak/hedef düğüm id'si; w: ağırlık
    meta:  {...}                   # bileşen okumaz; provenans + sayılar

Determinizm: düğümler pc azalan + id artan; kenarlar (s, t) artan; s < t;
timestamp yok. Aynı girdiden her çalıştırmada bayt-bayt aynı çıktı üretilir.
"""

import itertools
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "web" / "public" / "data"
OUT_ROOT = REPO / "web" / "public" / "yaqut_graph.json"   # PlaceGraph'ın fetch yolu
OUT_DATA = DATA / "yaqut_graph.json"                       # veri klasörü kopyası

EDGE_CAP = 50_000  # bu sayı aşılırsa min ağırlık eşiği 2'ye çekilir


def main():
    lite = json.loads((DATA / "yaqut_lite.json").read_text(encoding="utf-8"))
    crossref = json.loads((DATA / "yaqut_crossref.json").read_text(encoding="utf-8"))

    lite_by_id = {e["id"]: e for e in lite}

    # --- Düğümler: yalnızca crossref'i olan yerler -------------------------
    place_ids = sorted(int(k) for k in crossref.keys())
    missing = [pid for pid in place_ids if pid not in lite_by_id]
    if missing:
        raise SystemExit(f"HATA: crossref'teki {len(missing)} yer lite'ta yok: {missing[:5]}")

    nodes = []
    for pid in place_ids:
        e = lite_by_id[pid]
        nodes.append({
            "id": pid,
            "n": e.get("h") or e.get("ht") or str(pid),  # PlaceGraph tooltip/etiket (RTL)
            "ht": e.get("ht"),
            "gt": e.get("gt"),
            "pc": e.get("pc") or 0,
        })
    # Önem sırası: pc azalan, id artan (deterministik tiebreak)
    nodes.sort(key=lambda n: (-n["pc"], n["id"]))

    # --- Kenarlar: kişi -> yerler ters indeksinden ikili kesişimler --------
    person_places = defaultdict(set)
    for place_id, persons in crossref.items():
        pid = int(place_id)
        for person in persons:
            person_places[person["id"]].add(pid)

    pair_weight = defaultdict(int)
    for places in person_places.values():
        if len(places) > 1:
            for a, b in itertools.combinations(sorted(places), 2):
                pair_weight[(a, b)] += 1

    min_weight = 1
    if len(pair_weight) > EDGE_CAP:
        min_weight = 2  # docstring'de belirtilen boyut korumasi

    edges = [
        {"s": a, "t": b, "w": w}
        for (a, b), w in sorted(pair_weight.items())
        if w >= min_weight
    ]

    out = {
        "meta": {
            "source": ["yaqut_lite.json", "yaqut_crossref.json"],
            "node_rule": "crossref kaydı olan yerler",
            "edge_rule": "iki yerin aynı Ziriklî kişisini paylaşması; w = ortak kişi sayısı",
            "min_weight": min_weight,
            "n_nodes": len(nodes),
            "n_edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }

    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    for path in (OUT_ROOT, OUT_DATA):
        path.write_text(payload, encoding="utf-8")

    print(f"düğüm: {len(nodes)}")
    print(f"kenar: {len(edges)} (min_weight={min_weight}; w>=1 ham: {len(pair_weight)})")
    for path in (OUT_ROOT, OUT_DATA):
        print(f"yazıldı: {path} ({path.stat().st_size:,} bayt)")


if __name__ == "__main__":
    main()
