#!/usr/bin/env python3
"""person_bridge.json üretici — Dalga-2 kişi köprüsü (veri tarafı).

Amaç:
    Mağazada (data/_index/lookup.sqlite, source_curie tablosu) aynı iac:person
    pid'ine birden çok kaynak curie'si bağlı (merge'ler): el-alam:<id>,
    dia:<slug>, ei1:<id>... Bu script pid-merge bilgisini frontend'in tek
    fetch'te kullanabileceği iki yönlü hızlı arama haritalarına indirger:
    "bir kişinin kartında tüm kaynak izleri".

Çıktı:
    web/public/books/person_bridge.json
        {
          "_doc": "...",
          "n_persons": N,          # köprüde temsil edilen tekil pid sayısı
          "n_alam": ...,           # alam haritası anahtar sayısı
          "n_dia": ...,            # dia haritası anahtar sayısı
          "skipped_multi": ...,    # dup-sınıfı nedeniyle atlanan pid sayısı
          "alam": { "<alamId>": {"pid": "iac:person-...",
                                  "dia": "<slug|null>", "ei1": "<id|null>"} },
          "dia":  { "<slug>":   {"pid": "iac:person-...",
                                  "alam": "<id|null>", "ei1": "<id|null>"} }
        }
    alam/ei1 id'leri her yerde STRING (curie son-eki oldukları gibi).

Kurallar:
    - YALNIZ person namespace (pid LIKE 'iac:person-%').
    - Kaynak eşlemesi tam-önek iledir: source_id'nin ilk ':' öncesi
      'el-alam' / 'dia' / 'ei1' olmalı. 'dia-chunks' ve 'dia-chunks-v8'
      ailesi dia'ya EŞLENMEZ, tamamen dışarıda (ayrı kimlik evreni;
      İbn Teymiyye 4054/8671 vakası). Diğer namespace'ler (yaqut, openiti,
      science-layer, ...) köprüye girmez.
    - Bir pid'de AYNI kaynaktan (alam/dia/ei1) birden çok curie varsa
      (dup sınıfı) o pid köprüye hiç konmaz; sayısı "skipped_multi"
      alanında raporlanır (belirsizlik-koruması).
    - Determinizm: timestamp yok; alam anahtarları sayısal artan, dia
      anahtarları bayt-sıralı; girdi aynıysa çıktı bayt-bayt aynıdır.
    - Sayı uydurma yok: her sayı bu koşunun sorgu sonuçlarından türetilir.
    - Çıktı 5 MB'ı aşarsa yalnız çift-kaynaklı (≥2 kaynaklı) kişiler
      tutulur ve bu _doc + stdout'ta açıkça belirtilir.

Ayrıca stdout'a data/sources/dia_alam_xref.json ile kesişim analizi basar:
pid-merge köprüsünün xref'e EK kaç yeni alam↔dia çifti getirdiği.

Çalıştırma:  python3 pipelines/frontend/build_person_bridge.py
Commit karari Ali'ye aittir; script commit yapmaz.
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "_index" / "lookup.sqlite"
XREF = REPO / "data" / "sources" / "dia_alam_xref.json"
OUT = REPO / "web" / "public" / "books" / "person_bridge.json"

SIZE_CAP = 5 * 1024 * 1024  # 5 MB

# Köprüye giren kaynaklar: tam önek -> köprü anahtarı.
# 'dia-chunks' / 'dia-chunks-v8' burada YOK ve asla eklenmemeli
# (ayrı kimlik evreni — dia'ya eşlenmez).
BRIDGE_SOURCES = {"el-alam": "alam", "dia": "dia", "ei1": "ei1"}

DOC = (
    "Dalga-2 kişi köprüsü: lookup.sqlite source_curie pid-merge'lerinden "
    "türetilen iki yönlü arama haritaları (alam<->dia/ei1). Yalnız "
    "iac:person namespace; dia-chunks ailesi bilinçli olarak dışarıda "
    "(ayrı kimlik evreni). Aynı kaynaktan birden çok curie'si olan pid'ler "
    "köprüye alınmaz (skipped_multi). alam/ei1 id'leri string. "
    "Üretici: pipelines/frontend/build_person_bridge.py"
)


def load_person_sources(db_path):
    """pid -> {köprü_kaynağı: [id, ...]} — yalnız person + köprü kaynakları."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT source_id, pid FROM source_curie "
        "WHERE pid LIKE 'iac:person-%' ORDER BY source_id"
    ).fetchall()
    con.close()

    persons = {}
    for source_id, pid in rows:
        prefix, sep, local = source_id.partition(":")
        if not sep:
            continue  # önek yoksa köprü dışı
        src = BRIDGE_SOURCES.get(prefix)
        if src is None:
            continue  # dia-chunks dahil tüm diğer namespace'ler dışarıda
        persons.setdefault(pid, {}).setdefault(src, []).append(local)
    return persons


def build_maps(persons, only_multi_source=False):
    """(alam_map, dia_map, n_persons, skipped_multi) üret."""
    skipped_multi = 0
    kept = {}
    for pid, srcs in persons.items():
        if any(len(ids) > 1 for ids in srcs.values()):
            skipped_multi += 1  # dup sınıfı: belirsizlik-koruması
            continue
        if only_multi_source and len(srcs) < 2:
            continue
        kept[pid] = {src: ids[0] for src, ids in srcs.items()}

    alam_map = {}
    dia_map = {}
    for pid, ids in kept.items():
        if "alam" in ids:
            alam_map[ids["alam"]] = {
                "pid": pid,
                "dia": ids.get("dia"),
                "ei1": ids.get("ei1"),
            }
        if "dia" in ids:
            dia_map[ids["dia"]] = {
                "pid": pid,
                "alam": ids.get("alam"),
                "ei1": ids.get("ei1"),
            }

    # Deterministik sıralama: alam sayısal artan, dia bayt-sıralı.
    alam_sorted = {k: alam_map[k] for k in sorted(alam_map, key=lambda s: (len(s), s))}
    dia_sorted = {k: dia_map[k] for k in sorted(dia_map)}
    return alam_sorted, dia_sorted, len(kept), skipped_multi


def serialize(alam_map, dia_map, n_persons, skipped_multi, reduced):
    doc = DOC
    if reduced:
        doc += (
            " NOT: tam çıktı 5MB sınırını aştığı için yalnız çift-kaynaklı "
            "(>=2 kaynaklı) kişiler tutuldu; tek-kaynaklılar atıldı."
        )
    out = {
        "_doc": doc,
        "n_persons": n_persons,
        "n_alam": len(alam_map),
        "n_dia": len(dia_map),
        "skipped_multi": skipped_multi,
        "alam": alam_map,
        "dia": dia_map,
    }
    return (json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def xref_analysis(alam_map):
    """Köprünün alam<->dia çiftlerini mevcut xref ile karşılaştır."""
    with open(XREF, encoding="utf-8") as f:
        xref = json.load(f)
    xref_pairs = set()
    for alam_id, dia_slug in xref.get("alam_to_dia", {}).items():
        xref_pairs.add((str(alam_id), dia_slug))
    for dia_slug, alam_ids in xref.get("dia_to_alam", {}).items():
        for alam_id in alam_ids:
            xref_pairs.add((str(alam_id), dia_slug))

    bridge_pairs = {
        (alam_id, entry["dia"])
        for alam_id, entry in alam_map.items()
        if entry["dia"] is not None
    }
    new_pairs = sorted(bridge_pairs - xref_pairs, key=lambda p: (len(p[0]), p[0]))
    overlap = bridge_pairs & xref_pairs
    # Çelişki: aynı alam id'si için xref farklı bir dia slug'ı veriyor mu?
    xref_by_alam = {}
    for a, d in xref_pairs:
        xref_by_alam.setdefault(a, set()).add(d)
    conflicts = sorted(
        (a, d, sorted(xref_by_alam[a]))
        for a, d in bridge_pairs
        if a in xref_by_alam and d not in xref_by_alam[a]
    )
    return {
        "xref_pairs": len(xref_pairs),
        "bridge_pairs": len(bridge_pairs),
        "overlap": len(overlap),
        "new_pairs": new_pairs,
        "conflicts": conflicts,
    }


def labels_for(pids):
    """Rapor örnekleri için tr>en pref etiketi (yalnız stdout, JSON'a girmez)."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out = {}
    for pid in pids:
        row = con.execute(
            "SELECT text FROM label WHERE pid=? AND kind='pref' "
            "ORDER BY CASE lang WHEN 'tr' THEN 0 WHEN 'en' THEN 1 ELSE 2 END "
            "LIMIT 1",
            (pid,),
        ).fetchone()
        out[pid] = row[0] if row else "(etiket yok)"
    con.close()
    return out


def main():
    persons = load_person_sources(DB)
    alam_map, dia_map, n_persons, skipped_multi = build_maps(persons)
    payload = serialize(alam_map, dia_map, n_persons, skipped_multi, reduced=False)
    reduced = False
    if len(payload) > SIZE_CAP:
        reduced = True
        alam_map, dia_map, n_persons, skipped_multi = build_maps(
            persons, only_multi_source=True
        )
        payload = serialize(alam_map, dia_map, n_persons, skipped_multi, reduced=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(payload)

    print(f"person_bridge.json yazildi: {OUT}")
    print(f"  n_persons={n_persons}  n_alam={len(alam_map)}  n_dia={len(dia_map)}")
    print(f"  skipped_multi={skipped_multi}  boyut={len(payload)} bayt  reduced={reduced}")

    ana = xref_analysis(alam_map)
    print("xref kesisimi (data/sources/dia_alam_xref.json):")
    print(f"  xref cift sayisi   : {ana['xref_pairs']}")
    print(f"  kopru cift sayisi  : {ana['bridge_pairs']}")
    print(f"  ortak (overlap)    : {ana['overlap']}")
    print(f"  YENI cift (kopru\\xref): {len(ana['new_pairs'])}")
    if ana["new_pairs"]:
        ex = ana["new_pairs"][:3]
        lbl = labels_for([alam_map[a]["pid"] for a, _ in ex])
        for a, d in ex:
            pid = alam_map[a]["pid"]
            print(f"    ornek: alam:{a} <-> dia:{d}  ({pid} = {lbl[pid]})")
    if ana["conflicts"]:
        print(f"  CELISKI (ayni alam, farkli dia): {len(ana['conflicts'])}")
        for a, d, xd in ana["conflicts"][:5]:
            print(f"    alam:{a} kopru->dia:{d}  xref->dia:{xd}")
    else:
        print("  celiski yok (ayni alam id'sinde kopru ile xref ayni dia'yi veriyor)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
