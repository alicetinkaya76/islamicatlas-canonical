#!/usr/bin/env python3
"""Dalga-1 "Kitap Kabı" üreticisi — mağaza pid eşlemesini frontend'e yansıtır.

Kapsam (künyesi tam 5 kaynak):
    yaqut      Mu'cemü'l-Büldân      12.954 yer     (yaqut_lite.json)
    muqaddasi  Ahsenü't-Tekāsîm       2.049 yer + 21 iklim (muqaddasi_atlas_layer.json)
    khitat     el-Hıtat                 801 yapı    (maqrizi_khitat_atlas_layer.json)
    battles    Savaşlar (küratörlü)     100 olay    (db.json "battles")
    science    İlim Atlası (küratörlü)  182 kişi + eserler (science_layer.json)

Çıktılar (her kaynak için web/public/books/<key>/ altına):
    manifest.json  — künye + SAYILMIŞ kapsam (uydurma sayı YOK)
    pid_map.json   — {yerel_id(string): iac_pid}; SADECE gerçekten eşlenenler
                     (curie'nin yerel kısmı frontend veri dosyasındaki bir
                      kaydın id'sine birebir doğrulanır; doğrulanamayan
                      curie'ler eşlenmemiş sayılır ve manifest'te raporlanır)
    web/public/books/index.json — 5 kabın özeti

Keşfedilen curie biçimleri (data/_index/lookup.sqlite, source_curie):
    yaqut:<int>                      → iac:place-*        yerel id = <int>
    muqaddasi:muq-NNNN               → iac:place-*        yerel id = muq-NNNN
    muqaddasi:muq-iqlim-NNN          → iac:place-*        (frontend aqualim
                                       kayıtlarında id alanı YOK → eşlenemez)
    maqrizi-khitat:cairo_NNNN        → iac:institution-*  yerel id = int(NNNN)
    battles-events:battle:<int>      → iac:event-*        yerel id = <int>
    battles-events:event:<int>       → iac:event-*        (db.json "events"
                                       koleksiyonuna ait; bu kabın kapsamı dışı)
    science-layer:scholar_NNNN       → iac:person-*       yerel id = scholar_NNNN
    science-works:scholar_NNNN:kw_K  → iac:work-*         yerel id = scholar_NNNN:kw_K
                                       (key_works dizisinin K. elemanı)
    science-works:disc_NNNN          → iac:work-*         (discoveries koleksiyonu;
                                       "kişi + eserler" kapsamı dışı → haric)

Determinizm: timestamp yok; json.dumps(sort_keys=True); girdi aynıysa çıktı
bayt-bayt aynıdır. Kapsam %100 değilse GERÇEK yüzde yazılır, yuvarlama
iddiası yok.

Çalıştırma:  python3 pipelines/frontend/build_containers.py
"""

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "web" / "public" / "data"
DB_JSON = REPO / "web" / "src" / "data" / "db.json"
SQLITE = REPO / "data" / "_index" / "lookup.sqlite"
BOOKS = REPO / "web" / "public" / "books"

GENERATED_BY = "pipelines/frontend/build_containers.py"


# ---------------------------------------------------------------- yardımcılar

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_curies(cur, like):
    """source_curie'den (source_id, pid) çiftlerini çek."""
    return cur.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?", (like,)
    ).fetchall()


def pid_namespace(pid):
    """iac:place-00000001 → 'place'"""
    body = pid.split(":", 1)[1]
    return body.rsplit("-", 1)[0]


def kind_counts(pid_map):
    counts = {}
    for pid in pid_map.values():
        ns = pid_namespace(pid)
        counts[ns] = counts.get(ns, 0) + 1
    return counts


def coverage(mapped, total):
    pct = round(100.0 * mapped / total, 2) if total else 0.0
    return {"mapped": mapped, "total": total, "pct": pct}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------- kaynaklar

def build_yaqut(cur):
    src = DATA / "yaqut_lite.json"
    records = load_json(src)
    ids = {str(r["id"]) for r in records}  # id alanı int → string anahtar

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "yaqut:%"):
        local = source_id.split(":", 1)[1]
        if local in ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "yaqut",
        "name_tr": "Mu'cemü'l-Büldân",
        "name_ar": "معجم البلدان",
        "work_pid": "iac:work-00000111",
        "work_note": (
            "Dublet: iac:work-00000111 ve iac:work-00000407 aynı eser "
            "(معجم البلدان); manifest'e ilki yazıldı."
        ),
        "record_count": len(records),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "globe", "analytics", "graph", "idcard"],
        "pid_coverage": coverage(len(pid_map), len(records)),
        "pid_map_key": "yaqut_lite.json içindeki id alanı (int) — string olarak",
        "unmatched_curies": sorted(unmatched),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/yaqut_lite.json",
            "data/_index/lookup.sqlite",
        ],
    }
    return manifest, pid_map


def build_muqaddasi(cur):
    src = DATA / "muqaddasi_atlas_layer.json"
    layer = load_json(src)
    places = layer["places"]
    aqualim = layer["aqualim"]
    place_ids = {str(p["id"]) for p in places}
    total = len(places) + len(aqualim)

    pid_map, iqlim_curies, unmatched = {}, [], []
    for source_id, pid in fetch_curies(cur, "muqaddasi:%"):
        local = source_id.split(":", 1)[1]
        if local in place_ids:
            pid_map[local] = pid
        elif local.startswith("muq-iqlim-"):
            iqlim_curies.append(source_id)
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "muqaddasi",
        "name_tr": "Ahsenü't-Tekâsîm fî Ma'rifeti'l-Ekâlîm",
        "name_ar": "أحسن التقاسيم في معرفة الأقاليم",
        "work_pid": "iac:work-00000154",
        "work_note": (
            "Dublet: iac:work-00000154 ve iac:work-00001533 aynı eser "
            "(أحسن التقاسيم في معرفة الأقاليم); manifest'e ilki yazıldı."
        ),
        "record_count": total,
        "record_breakdown": {"aqualim": len(aqualim), "places": len(places)},
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "routes"],
        "pid_coverage": coverage(len(pid_map), total),
        "pid_map_key": "muqaddasi_atlas_layer.json places[].id (ör. muq-0001)",
        "coverage_note": (
            "Mağazada {n} iklim curie'si var (muqaddasi:muq-iqlim-*), ancak "
            "frontend aqualim kayıtlarında id alanı bulunmadığından bunlar "
            "pid_map'e alınmadı; eşleme sıra varsayımıyla YAPILMADI."
        ).format(n=len(iqlim_curies)),
        "unmatched_curies": sorted(unmatched),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/muqaddasi_atlas_layer.json",
            "data/_index/lookup.sqlite",
        ],
    }
    return manifest, pid_map


def build_khitat(cur):
    src = DATA / "maqrizi_khitat_atlas_layer.json"
    layer = load_json(src)
    structures = layer["structures"]
    ids = {str(s["id"]) for s in structures}  # id alanı int

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "maqrizi-khitat:%"):
        local = source_id.split(":", 1)[1]  # cairo_0001
        if local.startswith("cairo_") and local[6:].isdigit():
            key = str(int(local[6:]))  # cairo_0001 → "1"
            if key in ids:
                pid_map[key] = pid
                continue
        unmatched.append(source_id)

    manifest = {
        "source_key": "khitat",
        "name_tr": "el-Hıtat",
        "name_ar": "الخطط",
        "work_pid": "iac:work-00000059",
        "work_note": None,
        "record_count": len(structures),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "structures"],
        "pid_coverage": coverage(len(pid_map), len(structures)),
        "pid_map_key": (
            "maqrizi_khitat_atlas_layer.json structures[].id (int) — string "
            "olarak; curie yerel kısmı cairo_NNNN biçiminden çözüldü"
        ),
        "unmatched_curies": sorted(unmatched),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/maqrizi_khitat_atlas_layer.json",
            "data/_index/lookup.sqlite",
        ],
    }
    return manifest, pid_map


def build_battles(cur):
    battles = load_json(DB_JSON)["battles"]
    ids = {str(b["id"]) for b in battles}  # id alanı int

    pid_map, event_curies, unmatched = {}, [], []
    for source_id, pid in fetch_curies(cur, "battles-events:%"):
        local = source_id.split(":", 1)[1]  # battle:1 | event:1
        if local.startswith("battle:"):
            key = local.split(":", 1)[1]
            if key in ids:
                pid_map[key] = pid
            else:
                unmatched.append(source_id)
        elif local.startswith("event:"):
            # db.json "events" koleksiyonuna ait; bu kabın kapsamı dışında.
            event_curies.append(source_id)
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "battles",
        "name_tr": "İslam Tarihinde Savaşlar",
        "name_ar": None,
        "work_pid": None,
        "work_note": (
            "work_missing: küratörlü modern veri seti; mağazada tek bir "
            "klasik esere bağlı work kaydı yok."
        ),
        "record_count": len(battles),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "events"],
        "pid_coverage": coverage(len(pid_map), len(battles)),
        "pid_map_key": "db.json battles[].id (int) — string olarak",
        "coverage_note": (
            "Mağazada yalnız battle:1..{m} curie'si var; db.json battles "
            "{t} kayıt içeriyor → kapsam {m}/{t}. Ayrıca {e} adet "
            "battles-events:event:* curie'si db.json 'events' koleksiyonuna "
            "aittir ve bu kabın kapsamı dışıdır."
        ).format(m=len(pid_map), t=len(battles), e=len(event_curies)),
        "unmatched_curies": sorted(unmatched),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/src/data/db.json",
            "data/_index/lookup.sqlite",
        ],
    }
    return manifest, pid_map


def build_science(cur):
    src = DATA / "science_layer.json"
    layer = load_json(src)
    scholars = layer["scholars"]
    scholar_ids = {str(s["id"]) for s in scholars}

    # key_works'ün yerel kimliği: scholar_NNNN:kw_K (K = dizideki sıra)
    work_keys = set()
    for s in scholars:
        for i in range(len(s.get("key_works") or [])):
            work_keys.add("{}:kw_{}".format(s["id"], i))

    pid_map, disc_curies, unmatched = {}, [], []
    for source_id, pid in fetch_curies(cur, "science-layer:%"):
        local = source_id.split(":", 1)[1]
        if local in scholar_ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)
    for source_id, pid in fetch_curies(cur, "science-works:%"):
        local = source_id.split(":", 1)[1]
        if local in work_keys:
            pid_map[local] = pid
        elif local.startswith("disc_"):
            # discoveries koleksiyonuna ait; "kişi + eserler" kapsamı dışı.
            disc_curies.append(source_id)
        else:
            unmatched.append(source_id)

    total = len(scholars) + len(work_keys)
    n_works = sum(1 for k in pid_map if ":kw_" in k)
    manifest = {
        "source_key": "science",
        "name_tr": "İslam Bilim Tarihi Atlası",
        "name_ar": None,
        "work_pid": None,
        "work_note": (
            "work_missing: küratörlü modern katman; mağazada tek bir klasik "
            "esere bağlı work kaydı yok."
        ),
        "record_count": total,
        "record_breakdown": {"key_works": len(work_keys), "scholars": len(scholars)},
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "network", "routes"],
        "pid_coverage": coverage(len(pid_map), total),
        "pid_map_key": (
            "science_layer.json scholars[].id (scholar_NNNN) ve eserler için "
            "scholar_NNNN:kw_K (K = key_works dizisindeki sıra)"
        ),
        "coverage_note": (
            "{w} eser + {s} kişi eşlendi. Mağazadaki {d} adet "
            "science-works:disc_* curie'si discoveries koleksiyonuna aittir "
            "ve 'kişi + eserler' kapsamı dışında bırakıldı."
        ).format(w=n_works, s=len(pid_map) - n_works, d=len(disc_curies)),
        "unmatched_curies": sorted(unmatched),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/science_layer.json",
            "data/_index/lookup.sqlite",
        ],
    }
    return manifest, pid_map


# ---------------------------------------------------------------- ana akış

BUILDERS = {
    "battles": build_battles,
    "khitat": build_khitat,
    "muqaddasi": build_muqaddasi,
    "science": build_science,
    "yaqut": build_yaqut,
}


def main():
    con = sqlite3.connect("file:{}?mode=ro".format(SQLITE), uri=True)
    cur = con.cursor()

    index_entries = []
    for key in sorted(BUILDERS):
        manifest, pid_map = BUILDERS[key](cur)
        out_dir = BOOKS / key
        write_json(out_dir / "manifest.json", manifest)
        write_json(out_dir / "pid_map.json", pid_map)
        index_entries.append({
            "key": key,
            "record_count": manifest["record_count"],
            "pid_coverage": manifest["pid_coverage"],
            "capabilities": manifest["capabilities"],
        })
        cov = manifest["pid_coverage"]
        print("{:10s} kayıt={:6d} eşlenen={:6d} kapsam=%{}".format(
            key, manifest["record_count"], cov["mapped"], cov["pct"]))

    write_json(BOOKS / "index.json", {
        "containers": index_entries,
        "generated_by": GENERATED_BY,
    })
    con.close()
    print("OK →", BOOKS.relative_to(REPO))


if __name__ == "__main__":
    main()
