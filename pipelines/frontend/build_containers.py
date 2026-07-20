#!/usr/bin/env python3
"""Dalga-1+2 "Kitap Kabı" üreticisi — mağaza pid eşlemesini frontend'e yansıtır.

Kapsam — Dalga-1 (künyesi tam 5 kaynak):
    yaqut      Mu'cemü'l-Büldân      12.954 yer     (yaqut_lite.json)
    muqaddasi  Ahsenü't-Tekāsîm       2.049 yer + 21 iklim (muqaddasi_atlas_layer.json)
    khitat     el-Hıtat                 801 yapı    (maqrizi_khitat_atlas_layer.json)
    battles    Savaşlar (küratörlü)     100 olay    (db.json "battles")
    science    İlim Atlası (küratörlü)  182 kişi + eserler (science_layer.json)

Kapsam — Dalga-2 (%80+ pid'li 5 kaynak):
    alam       el-A'lâm (Ziriklî)    13.940 kişi    (alam_lite.json)
    dia        DİA biyografi katmanı  8.528 kişi    (dia_lite.json)
    evliya     Seyahatnâme            5.444 yer+yapı (evliya_atlas_layer.json)
    salibiyyat Haçlı Seferleri          790 olay + 24 kale (salibiyyat_atlas_layer.json)
    cityatlas  Şehir Atlası — Konya     583 yapı    (city-atlas/konya.json;
               Kahire kaba GİRMEZ → khitat kabına işaretçi, çifte temsil önlenir)

Çıktılar (her kaynak için web/public/books/<key>/ altına):
    manifest.json  — künye + SAYILMIŞ kapsam (uydurma sayı YOK)
    pid_map.json   — {yerel_id(string): iac_pid}; SADECE gerçekten eşlenenler
                     (curie'nin yerel kısmı frontend veri dosyasındaki bir
                      kaydın id'sine birebir doğrulanır; doğrulanamayan
                      curie'ler eşlenmemiş sayılır ve manifest'te raporlanır)
    web/public/books/index.json — 10 kabın özeti

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
    el-alam:<int>                    → iac:person-*       yerel id = <int>
    dia:<slug>                       → iac:person-*       yerel id = <slug>
      (İKİNCİ aile: dia-chunks:<slug>, dia-chunks-v8:<slug>, dia-rich:<slug>:title_N,
       tdv_dia:<slug>:title_N — pid_map'e ALINMAZ; manifest'te ayrı raporlanır)
    evliya-celebi:EC_NNNNN           → iac:institution-* / iac:place-* (karışık)
    salibiyyat:SAL_ENNNN             → iac:event-*        yerel id = SAL_ENNNN
    salibiyyat:CST_NNN               → iac:institution-*  yerel id = CST_NNN
      (clusters[].id 'EC_NNNN' Evliyâ'nın EC_ önekiyle ÇAKIŞIR; mağaza curie'si
       yok → kap dışı; kaplar arası anahtar DAİMA kaynak-önekli, çıplak id asla)
    konya-city-atlas:konya_<slug>    → iac:institution-*  yerel id = konya_<slug>

Determinizm: timestamp yok; json.dumps(sort_keys=True); girdi aynıysa çıktı
bayt-bayt aynıdır. Kapsam %100 değilse GERÇEK yüzde yazılır, yuvarlama
iddiası yok.

Çalıştırma:  python3 pipelines/frontend/build_containers.py
"""

import json
import sqlite3
from collections import Counter
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


# ------------------------------------------------------- Dalga-2 kaynakları

UNMATCHED_NOTE = (
    "Eşlenemeyen curie'ler için ayrı kuyruk dosyası üretilmedi; mağaza "
    "kuyrukları zaten mevcut (sayı + örnek ile yetinildi)."
)


def unmatched_fields(unmatched, sample_n=20):
    """Dalga-2 kuralı: eşlenemeyenler SAYI ile raporlanır, kuyruk dosyası yok."""
    return {
        "unmatched_curie_count": len(unmatched),
        "unmatched_curie_sample": sorted(unmatched)[:sample_n],
        "unmatched_note": UNMATCHED_NOTE,
    }


def build_alam(cur):
    src = DATA / "alam_lite.json"
    records = load_json(src)
    ids = {str(r["id"]) for r in records}  # id alanı int → string anahtar

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "el-alam:%"):
        local = source_id.split(":", 1)[1]
        if local in ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "alam",
        "name_tr": "el-A'lâm (Ziriklî)",
        "name_ar": "الأعلام",
        "work_pid": "iac:work-00000333",
        "work_note": (
            "Label taramasıyla bulundu: pref 'الأعلام' / 'al-Aʿlām', alt başlık "
            "'قاموس تراجم لأشهر الرجال والنساء من العرب والمستعربين والمستشرقين' "
            "(Ziriklî'nin alt başlığı) — mağazada tek kayıt, dublet yok."
        ),
        "record_count": len(records),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "analytics", "network"],
        "pid_coverage": coverage(len(pid_map), len(records)),
        "pid_map_key": "alam_lite.json içindeki id alanı (int) — string olarak",
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/alam_lite.json",
            "data/_index/lookup.sqlite",
        ],
    }
    manifest.update(unmatched_fields(unmatched))
    return manifest, pid_map


def build_dia(cur):
    src = DATA / "dia_lite.json"
    records = load_json(src)
    ids = {str(r["id"]) for r in records}  # id alanı slug (string)

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "dia:%"):
        local = source_id.split(":", 1)[1]
        if local in ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    # İKİNCİ curie ailesi (dia-chunks vd.): pid_map'e ALINMAZ, ayrı raporlanır.
    dia_pids = {pid for _, pid in fetch_curies(cur, "dia:%")}
    related_families = {}
    for fam in ("dia-chunks", "dia-chunks-v8", "dia-rich", "tdv_dia"):
        rows = fetch_curies(cur, fam + ":%")
        if not rows:
            continue
        related_families[fam] = {
            "curie_count": len(rows),
            "entity_kind_counts": kind_counts(dict(rows)),
            "shares_pid_with_dia": sum(1 for _, p in rows if p in dia_pids),
        }

    manifest = {
        "source_key": "dia",
        "name_tr": "TDV İslâm Ansiklopedisi (DİA) Biyografi Katmanı",
        "name_ar": None,
        "work_pid": None,
        "work_note": (
            "work_missing: mağazada DİA'nın kendisine ait work kaydı yok "
            "(label taraması 'İslâm Ansiklopedisi' → 0 sonuç)."
        ),
        "record_count": len(records),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "network", "sankey", "analytics"],
        "pid_coverage": coverage(len(pid_map), len(records)),
        "pid_map_key": "dia_lite.json içindeki id alanı (slug)",
        "related_curie_families": related_families,
        "related_curie_note": (
            "Mağazada 'dia:' dışında dia-chunks / dia-chunks-v8 / dia-rich / "
            "tdv_dia önekli İKİNCİ bir curie ailesi var; sayıları yukarıda "
            "raporlandı, pid_map'e YALNIZ 'dia:' ailesi kondu."
        ),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/dia_lite.json",
            "data/_index/lookup.sqlite",
        ],
    }
    manifest.update(unmatched_fields(unmatched))
    return manifest, pid_map


def build_evliya(cur):
    src = DATA / "evliya_atlas_layer.json"
    layer = load_json(src)
    places = layer["places"]
    ids = {str(p["id"]) for p in places}  # id alanı EC_NNNNN (string)

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "evliya-celebi:%"):
        local = source_id.split(":", 1)[1]  # EC_00001
        if local in ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "evliya",
        "name_tr": "Evliyâ Çelebi Seyahatnâmesi",
        "name_ar": "سياحتنامه",
        "work_pid": "iac:work-00000062",
        "work_note": (
            "Dublet: iac:work-00000062 ve iac:work-00000210 aynı eser "
            "(Seyahatnâme); manifest'e ilki yazıldı."
        ),
        "record_count": len(places),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "voyages"],
        "pid_coverage": coverage(len(pid_map), len(places)),
        "pid_map_key": "evliya_atlas_layer.json places[].id (EC_NNNNN)",
        "coverage_note": (
            "Kayıtlar yer + yapı karışıktır; ayrım entity_kind_counts'ta "
            "(iac:place-* / iac:institution-*) sayılmıştır."
        ),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/evliya_atlas_layer.json",
            "data/_index/lookup.sqlite",
        ],
    }
    manifest.update(unmatched_fields(unmatched))
    return manifest, pid_map


def build_salibiyyat(cur):
    src = DATA / "salibiyyat_atlas_layer.json"
    layer = load_json(src)
    events = layer["events"]
    castles = layer["castles"]
    event_ids = {str(e["id"]) for e in events}    # SAL_ENNNN
    castle_ids = {str(c["id"]) for c in castles}  # CST_NNN
    total = len(events) + len(castles)

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "salibiyyat:%"):
        local = source_id.split(":", 1)[1]
        if local in event_ids or local in castle_ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    n_clusters = len(layer.get("clusters") or [])
    manifest = {
        "source_key": "salibiyyat",
        "name_tr": "Salibiyyât — Müslüman Gözüyle Haçlı Seferleri",
        "name_ar": None,
        "work_pid": None,
        "work_note": (
            "work_missing: 6 vakayinameden derlenmiş küratörlü katman; "
            "mağazada katmanın kendisine ait tek bir work kaydı yok "
            "(bileşen eserler, ör. el-Kâmil, mağazada ayrıca mevcuttur)."
        ),
        "record_count": total,
        "record_breakdown": {"castles": len(castles), "events": len(events)},
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "compare", "routes", "timeline", "castles"],
        "pid_coverage": coverage(len(pid_map), total),
        "pid_map_key": (
            "salibiyyat_atlas_layer.json events[].id (SAL_ENNNN) ve "
            "castles[].id (CST_NNN)"
        ),
        "id_collision_note": (
            "clusters[].id ({n} adet, 'EC_NNNN') EVLİYÂ kabının 'EC_NNNNN' "
            "önekiyle ÇAKIŞIR; kümelerin mağaza curie'si yoktur ve bu kabın "
            "kapsamı dışıdır. Kaplar arası her birleştirmede anahtar DAİMA "
            "kaynak-önekli kullanılmalıdır (ör. 'salibiyyat:SAL_E0001', "
            "'evliya:EC_00002'); çıplak id asla."
        ).format(n=n_clusters),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/salibiyyat_atlas_layer.json",
            "data/_index/lookup.sqlite",
        ],
    }
    manifest.update(unmatched_fields(unmatched))
    return manifest, pid_map


def build_cityatlas(cur):
    src = DATA / "city-atlas" / "konya.json"
    records = load_json(src)
    ids = {str(r["id"]) for r in records}  # id alanı konya_<slug>
    dup_ids = sorted(
        k for k, v in Counter(str(r["id"]) for r in records).items() if v > 1
    )
    cairo_count = len(load_json(DATA / "city-atlas" / "cairo.json"))

    pid_map, unmatched = {}, []
    for source_id, pid in fetch_curies(cur, "konya-city-atlas:%"):
        local = source_id.split(":", 1)[1]
        if local in ids:
            pid_map[local] = pid
        else:
            unmatched.append(source_id)

    manifest = {
        "source_key": "cityatlas",
        "name_tr": "Şehir Atlası — Konya",
        "name_ar": "أطلس مدينة قونية",
        "work_pid": None,
        "work_note": (
            "work_missing: İbrahim Hakkı Konyalı + Konyapedia'dan derlenmiş "
            "küratörlü katman; mağazada katmana ait work kaydı yok (label "
            "taraması 'Konya Tarihi' / 'Konyalı' → 0 work sonucu)."
        ),
        "record_count": len(records),
        "entity_kind_counts": kind_counts(pid_map),
        "capabilities": ["map", "structures"],
        "pid_coverage": coverage(len(pid_map), len(records)),
        "pid_map_key": "city-atlas/konya.json içindeki id alanı (konya_<slug>)",
        "cities": {
            "cairo": {
                "pointer": "khitat",
                "note": (
                    "cairo.json = maqrizi layer'ın zengin formu, AYNI 801 "
                    "yapı — çifte temsil önlenir (sayıldı: cairo.json {n} "
                    "kayıt)."
                ).format(n=cairo_count),
            },
            "konya": {
                "data_file": "web/public/data/city-atlas/konya.json",
                "record_count": len(records),
            },
        },
        "coverage_note": (
            "Konya dosyasında {t} kayıt, {u} benzersiz id var; yinelenen "
            "id'ler: {d} (mağaza curie'leri 'konya_*' biçimli olduğundan "
            "pid_map bundan etkilenmez)."
        ).format(t=len(records), u=len(ids), d=dup_ids),
        "generated_by": GENERATED_BY,
        "source_files": [
            "web/public/data/city-atlas/konya.json",
            "data/_index/lookup.sqlite",
        ],
    }
    manifest.update(unmatched_fields(unmatched))
    return manifest, pid_map


# ---------------------------------------------------------------- ana akış

BUILDERS = {
    "alam": build_alam,
    "battles": build_battles,
    "cityatlas": build_cityatlas,
    "dia": build_dia,
    "evliya": build_evliya,
    "khitat": build_khitat,
    "muqaddasi": build_muqaddasi,
    "salibiyyat": build_salibiyyat,
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
