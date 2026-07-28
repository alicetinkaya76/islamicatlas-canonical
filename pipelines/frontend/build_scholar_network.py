#!/usr/bin/env python3
"""Canonical isnâd ağı üreticisi (H34) — hoca–talebe zinciri.

SORUN: Âlimler görünümündeki "ağ" modu v1 `db.json`'dan besleniyor: **450 âlim,
155 kenar** (H24'te 8 hayalet-uçlu kenar elenmişti). Oysa canonical mağazada
DİA ilişkilerinden gelen **3.399 kişilik, ~7.900 kenarlık** gerçek hoca–talebe
ağı var (H11 S11; yön H11 S11 doğrulamasında düzeltildi: pozisyon-0 TALEBE).

Bu üretici o ağı UI'ın okuyabileceği tek dosyaya indirger. v1 ağı DEĞİŞMEZ;
canonical ağ AYRI bir mod olarak eklenir (H26/H28 "ek katman" deseni).

DÜRÜSTLÜK
    - Kenar TEKİLLEŞTİRİLİR: A.teachers=[B] ile B.students=[A] aynı kenardır;
      yön hep hoca→talebe olarak normalize edilir.
    - Emekli (deprecated) kayıt ve emekliye giden kenar ATILIR.
    - Mağazada karşılığı olmayan pid'e giden kenar ATILIR (hayalet uç yok —
      H24'te v1 ağında yaşanan hatanın tekrarı önlenir); atılan sayı raporlanır.
    - Derece (degree) her düğüme yazılır; UI eşik süzgeci uygular, sayı ekranda.

Çıktı: web/public/view-data/scholar_network.json (gitignored; build'de üretilir)
Determinizm: düğümler pid'e, kenarlar (hoca,talebe) çiftine göre sıralı.
"""

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERSON = REPO / "data" / "canonical" / "person"
OUT = REPO / "web" / "public" / "view-data" / "scholar_network.json"


def load_people():
    """pid → kayıt (yalnız aktif)."""
    people = {}
    for f in glob.glob(str(PERSON / "*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if d.get("provenance", {}).get("deprecated"):
            continue
        people[d["@id"]] = d
    return people


def death_ce(rec):
    t = rec.get("death_temporal") or rec.get("floruit_temporal") or {}
    for k in ("start_ce", "end_ce"):
        if isinstance(t.get(k), int):
            return t[k]
    for k in ("start_ah", "end_ah"):
        if isinstance(t.get(k), int):
            return round(t[k] * 0.970229 + 621.567)
    return None


def build():
    people = load_people()
    edges = set()          # (hoca_pid, talebe_pid) — tekilleştirilmiş
    dropped_ghost = 0

    for pid, rec in people.items():
        for teacher in (rec.get("teachers") or []):
            if teacher in people:
                edges.add((teacher, pid))          # hoca → talebe
            else:
                dropped_ghost += 1
        for student in (rec.get("students") or []):
            if student in people:
                edges.add((pid, student))
            else:
                dropped_ghost += 1

    deg = {}
    for a, b in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1

    nodes = []
    for pid in sorted(deg):
        rec = people[pid]
        pref = (rec.get("labels", {}) or {}).get("prefLabel", {}) or {}
        name = pref.get("tr") or pref.get("en") or pref.get("ar") or ""
        nodes.append({
            "pid": pid,
            "name": name.replace("i̇", "i"),
            "death_ce": death_ce(rec),
            "deg": deg[pid],
            "layers": rec.get("derived_from_layers") or [],
        })

    edge_list = [{"s": a, "t": b} for a, b in sorted(edges)]
    hist = {}
    for n in nodes:
        b = min(n["deg"], 10)
        hist[str(b)] = hist.get(str(b), 0) + 1

    return {
        "generated_by": "pipelines/frontend/build_scholar_network.py",
        "note": ("Canonical hoca–talebe (isnâd) ağı. Kenar yönü hoca→talebe. "
                 "Emekli kayıtlar ve mağazada karşılığı olmayan uçlar atıldı."),
        "counts": {
            "nodes": len(nodes),
            "edges": len(edge_list),
            "dropped_ghost_ends": dropped_ghost,
            "degree_hist": hist,
        },
        "nodes": nodes,
        "edges": edge_list,
    }


def main():
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    c = doc["counts"]
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()}")
    print(f"  düğüm: {c['nodes']} · kenar: {c['edges']}")
    print(f"  atılan hayalet uç: {c['dropped_ghost_ends']}")
    top = sorted(doc["nodes"], key=lambda n: -n["deg"])[:5]
    print("  en bağlantılı: " + ", ".join(f"{n['name'][:24]}({n['deg']})" for n in top))


if __name__ == "__main__":
    main()
