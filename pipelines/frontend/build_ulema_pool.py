#!/usr/bin/env python3
"""Ulema Havuzu üreticisi — mağazadaki TÜM kişi kayıtlarının dinamik havuzu.

Sahibin kararı (Ali):
    "Âlimler bölümü statik 450'lik set DEĞİL; mağazadaki TÜM kişi kayıtlarının
     süzülüp toplandığı DİNAMİK havuz olacak; her yeni kitapla kendiliğinden
     büyür. 450'lik set isnâd katmanıyla TOHUM."

Yani havuzun kapsamı = data/canonical/person/*.json'un tamamı. Yeni bir kitap
kabı mağazaya kişi eklediğinde bu script yeniden koşturulur ve havuz kendiliğinden
büyür; hiçbir yerde sabit bir liste tutulmaz.

Çıktılar (H18 dersi: lite/detail ayrımı — endeks küçük, ayrıntı ayrı dosyada):

    web/public/books/ulema_pool.json       LITE endeks, kişi başına MİNİMUM alan
        {
          "_doc": "...",
          "_pid_format": "iac:person-%08d",   # id -> pid geri kurulumu
          "_kaynak_kodlari": {"a": "el-alam", ...},
          "n": <kişi sayısı>,
          "kisiler": [
            {"id": 1,                  # iac:person- öneki DÜŞÜK, yalnız numara (int)
             "ad_tr": "...",           # prefLabel.tr > prefLabel.en (fallback sayılır)
             "ad_ar": "...",           # prefLabel.ar > originalScript.ar (varsa)
             "oh": 13,                 # ölüm hicrî (death_temporal.start_ah) | yoksa alan YOK
             "om": 634,                # ölüm milâdî (death_temporal.start_ce) | yoksa alan YOK
             "k": ["a", "d"],          # kaynak kısa kodları, sıralı
             "m": ["ruler"]}           # meslek/alan (profession), sıralı
          ]
        }
        Boş/eksik alanlar hiç yazılmaz (null yerine yokluk) — boyut için.

    web/public/books/ulema_pool_meta.json  sayımlar (hepsi bu koşuda SAYILDI)

KURALLAR (CLAUDE.md + H18/H19 desenleri):
    - Sayı uydurma YOK: her sayı bu koşunun taramasından türer.
    - Ölüm tarihi YALNIZ death_temporal alanından; yoksa alan hiç yazılmaz.
      Tahmin/çıkarım YASAK (floruit/birth'ten ölüm türetilmez).
    - Etiket sırası: prefLabel.tr > prefLabel.en (tr yoksa); ad_ar için
      prefLabel.ar > originalScript.ar. Uydurma çeviri yok.
    - Determinizm: pid numarası artan; timestamp yok; iki koşu bayt-bayt aynı.
    - Boyut tavanı 6 MB. Aşılırsa sırayla:
        (1) yalnız >=1 kaynak-curie'li kişiler tutulur (curie'siz mint'ler düşer),
        (2) hâlâ büyükse alan kısaltması.
      Hangi karar alındıysa _doc'a ve stdout'a AÇIKÇA yazılır; sessiz kayıt
      atma yok.

KAYNAK KODLARI — source_curie öneki -> kısa kod:
    el-alam        -> "a"   el-A'lâm (Ziriklî)
    dia            -> "d"   TDV DİA biyografi katmanı
    ei1            -> "e"   Encyclopaedia of Islam (1st ed.)
    science-layer  -> "s"   İlim Atlası (küratörlü)
    scholars       -> "sc"  450'lik tohum set (db.json "scholars")
    diğer tüm önekler -> "b" kitap-çıkarımı/diğer
      (openiti, bosworth-nid VE dia-chunks / dia-chunks-v8 buraya düşer.
       dia-chunks ailesi BİLEREK "d"ye eşlenmez: build_person_bridge.py'de
       kayıtlı ders — ayrı kimlik evreni, İbn Teymiyye 4054/8671 vakası.)

Çalıştırma:  python3 pipelines/frontend/build_ulema_pool.py
Commit kararı Ali'ye aittir; script commit yapmaz.
"""

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERSON_DIR = REPO / "data" / "canonical" / "person"
WORK_DIR = REPO / "data" / "canonical" / "work"
SQLITE = REPO / "data" / "_index" / "lookup.sqlite"
SEED_DB = REPO / "data" / "sources" / "scholars" / "db.json"
SEED_ISNAD = REPO / "data" / "sources" / "scholars" / "isnad_chains.js"
BOOKS = REPO / "web" / "public" / "books"
OUT_POOL = BOOKS / "ulema_pool.json"
OUT_META = BOOKS / "ulema_pool_meta.json"

SIZE_CAP = 6 * 1024 * 1024  # 6 MB

GENERATED_BY = "pipelines/frontend/build_ulema_pool.py"
PID_FORMAT = "iac:person-%08d"

# source_curie tam-öneki -> kısa kod. Burada OLMAYAN her önek "b"ye düşer.
SOURCE_CODES = {
    "el-alam": "a",
    "dia": "d",
    "ei1": "e",
    "science-layer": "s",
    "scholars": "sc",
}
OTHER_CODE = "b"

# H46: 'b' (Kitap/diğer) TEK bir kovaydı ve rozeti TIKLANAMIYORDU (href sabit
# null) — 3.105 kişinin tek rozeti buydu. Oysa ham curie öneki hangi kaynağın
# izi olduğunu biliyor. Alt-kodlara ayrıldı ki her biri KENDİ açılabilir
# hedefine gitsin; hedefi OLMAYAN önek de dürüstçe ayrı görünsün.
BOOK_CODES = {
    "dia-chunks": "bc",       # DİA madde-parçası → #dia/<slug>  (pid eşitliği ŞART)
    "dia-chunks-v8": "bc",
    "bosworth-nid": "by",     # Bosworth hükümdar listesi → #dynasty/<id>
    "openiti": "bo",          # OpenITI külliyatı → çoğunda açılabilir sayfa YOK
    "alatli": "ba",           # Alatlı antolojisi → şerit derin link kabul etmiyor
}
CODE_LABELS = {
    "a": "el-alam",
    "d": "dia",
    "e": "ei1",
    "s": "science-layer",
    "sc": "scholars (450 tohum)",
    "bc": "dia-madde-parcasi",
    "by": "bosworth-hanedan",
    "bo": "openiti-kulliyat",
    "ba": "alatli-antoloji",
    "b": "kitap-cikarimi/diger",
}
# Çıktıda kaynak kodlarının deterministik sırası.
CODE_ORDER = ["a", "d", "e", "s", "sc", "bc", "by", "bo", "ba", "b"]

PID_RE = re.compile(r"^iac:person-(\d+)$")


# ---------------------------------------------------------------- yardımcılar

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pid_num(pid):
    """iac:person-00000184 -> 184 ; person olmayan/bozuk pid -> None"""
    m = PID_RE.match(pid)
    return int(m.group(1)) if m else None


def write_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


# ---------------------------------------------------------------- mağaza

def load_persons():
    """canonical/person/*.json -> {pid_no: kayıt} + tarama sayaçları.

    Havuzun kapsamı budur: dosya sistemindeki her kişi kaydı. Filtre yok
    (deprecated kayıt sayısı ayrıca sayılır ve varsa dışarıda bırakılır).
    """
    persons = {}
    stats = Counter()
    ad_tr_fallback = 0
    for path in sorted(PERSON_DIR.glob("*.json")):
        rec = load_json(path)
        num = pid_num(rec.get("@id", ""))
        if num is None:
            stats["bozuk_pid"] += 1
            continue
        if rec.get("provenance", {}).get("deprecated"):
            stats["deprecated_haric"] += 1
            continue

        labels = rec.get("labels") or {}
        pref = labels.get("prefLabel") or {}
        orig = labels.get("originalScript") or {}

        ad_tr = pref.get("tr")
        if not ad_tr:
            ad_tr = pref.get("en")
            if ad_tr:
                ad_tr_fallback += 1
        ad_ar = pref.get("ar") or orig.get("ar")

        death = rec.get("death_temporal") or {}
        oh = death.get("start_ah")
        om = death.get("start_ce")

        meslek = sorted(set(rec.get("profession") or []))

        persons[num] = {
            "ad_tr": ad_tr,
            "ad_ar": ad_ar,
            "oh": oh if isinstance(oh, int) else None,
            "om": om if isinstance(om, int) else None,
            "m": meslek,
        }
        stats["okunan"] += 1
    stats["ad_tr_en_fallback"] = ad_tr_fallback
    return persons, stats


def load_source_codes():
    """pid_no -> set(kısa kod) ; ayrıca ham önek sayımı."""
    con = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT source_id, pid FROM source_curie WHERE pid LIKE 'iac:person-%' "
        "ORDER BY source_id"
    ).fetchall()
    con.close()

    codes = {}
    prefix_counts = Counter()
    # H46: locator (curie'nin ':' sonrası) artık SAKLANIYOR — hedef id'si oradan
    # geliyor. Bugüne dek atılıyordu, bu yüzden 'b' rozeti hedefsizdi.
    locators = {}
    for source_id, pid in rows:
        num = pid_num(pid)
        if num is None:
            continue
        prefix, sep, loc = source_id.partition(":")
        prefix_counts[prefix if sep else "(oneksiz)"] += 1
        if not sep:
            code = OTHER_CODE
        elif prefix in SOURCE_CODES:
            code = SOURCE_CODES[prefix]
        else:
            code = BOOK_CODES.get(prefix, OTHER_CODE)
            if code != OTHER_CODE:
                locators.setdefault(num, {})[prefix] = loc
        codes.setdefault(num, set()).add(code)
    return codes, prefix_counts, locators


def openiti_authors():
    """OpenITI külliyatında eseri olan kişiler (pid no kümesi) — H55.

    NEDEN CURIE YETMİYOR: 'bo' rozeti `source_curie`'deki `openiti:` önekinden
    geliyordu, yani YALNIZ OpenITI'den mint edilmiş kişiye düşüyordu. Oysa DİA
    ya da el-Aʿlâm'dan mint edilmiş bir kişinin de OpenITI'de eseri olabilir —
    ve rozet ona çıkmıyordu. Ölçüldü: rozet 2.246 kişide, oysa OpenITI eseri
    olan 3.553 kişi var; 1.307'si rozetsiz, FAZLADAN rozet alan 0. Yani rozet
    gerçeğin öz alt kümesiydi ve kaynağı yanlıştı: kişinin mint kaynağı değil,
    ESERİNİN varlığı sorulmalı.

    Yumuşak-silinmiş müellif pid'leri kazanana çevrilir (H49/H50 birleştirmesi
    eser kayıtlarının `authors` alanına hiç uğramamıştı; ölçüldü: 1.177 bağ).
    """
    if not WORK_DIR.is_dir():
        return set()

    prov_cache = {}

    def prov(num):
        if num not in prov_cache:
            p = PERSON_DIR / f"iac_person_{num:08d}.json"
            try:
                prov_cache[num] = (json.loads(p.read_text(encoding="utf-8"))
                                   .get("provenance") or {})
            except (OSError, json.JSONDecodeError):
                prov_cache[num] = {}
        return prov_cache[num]

    def kazanan(num):
        gorulen = set()
        while True:
            pr = prov(num)
            if not pr:
                return None
            if not pr.get("deprecated"):
                return num
            hedef = pid_num(pr.get("deprecated_in_favor_of") or "")
            if hedef is None or hedef in gorulen:
                return None
            gorulen.add(num)
            num = hedef

    out = set()
    for f in sorted(WORK_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (r.get("provenance") or {}).get("deprecated"):
            continue
        # Rozetin etiketi "OpenITI külliyatı" — o yüzden yalnız OpenITI izi
        # taşıyan eser sayılır. Bilim katmanından gelen eserler 's' rozetinde.
        if not r.get("openiti_uri"):
            continue
        for x in (r.get("authors") or []):
            pid = x.get("person") if isinstance(x, dict) else x
            n = pid_num(pid or "")
            if n is None:
                continue
            k = kazanan(n)
            if k is not None:
                out.add(k)
    return out


def resolve_targets(locators):
    """pid_no -> {alt_kod: hedef} — YALNIZ GERÇEKTEN AÇILAN hedefler.

    H46 doktrini: hedef çözülmüyorsa alan YAZILMAZ. Sahte tıklanabilirlik,
    dürüst boşluktan kötüdür.

    EN BÜYÜK TUZAK (ölçüldü): dia-chunks slug'ının 267'si BAŞKA bir pid'e bağlı.
    Slug'a bakıp link üretmek o kişilerde KESİNLİKLE yanlış DİA maddesini
    açardı. Bu yüzden pid EŞİTLİK kontrolü pazarlık konusu değildir.
    """
    out = {}
    # DİA kataloğu: slug -> pid
    slug2pid = {}
    for rel in ("web/public/view-data/dia_lite.json", "web/public/data/dia_lite.json"):
        f = REPO / rel
        if f.is_file():
            d = json.loads(f.read_text(encoding="utf-8"))
            arr = d if isinstance(d, list) else (d.get("records") or d.get("items") or [])
            slug2pid = {str(x.get("id")): x.get("pid") for x in arr if x.get("id")}
            break
    # v1 hanedan kataloğu: id kümesi
    dyn_ids = set()
    f = REPO / "web" / "src" / "data" / "db.json"
    if f.is_file():
        dyn_ids = {str(x.get("id")) for x in json.loads(f.read_text(encoding="utf-8")).get("dynasties", [])}

    sayac = Counter()
    for num, per_prefix in locators.items():
        pid = f"iac:person-{num:08d}"
        hedef = {}
        for prefix, loc in per_prefix.items():
            if prefix.startswith("dia-chunks"):
                # PID EŞİTLİĞİ: slug bu kişiye mi ait?
                if slug2pid.get(loc) == pid:
                    hedef["bc"] = loc
                    sayac["bc"] += 1
                else:
                    sayac["bc_reddedildi"] += 1
            elif prefix == "bosworth-nid":
                nid = loc.split(":")[0]
                if nid in dyn_ids:
                    hedef["by"] = nid
                    sayac["by"] += 1
        if hedef:
            out[num] = hedef
    return out, sayac


def store_person_total():
    """entity_bracket'teki person sayısı — dosya sayımıyla çapraz kontrol."""
    con = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    (n,) = con.execute(
        "SELECT COUNT(*) FROM entity_bracket WHERE entity_type='person'"
    ).fetchone()
    con.close()
    return n


# ---------------------------------------------------------------- 450 tohum

def load_seed():
    """450'lik tohum set + isnâd kenarları (db.json scholars / isnad_chains.js)."""
    seed_ids = []
    if SEED_DB.exists():
        seed_ids = [s["id"] for s in load_json(SEED_DB).get("scholars", []) if "id" in s]

    edges = []
    if SEED_ISNAD.exists():
        text = SEED_ISNAD.read_text(encoding="utf-8")
        edges = [
            (int(a), int(b))
            for a, b in re.findall(r"\{\s*from:\s*(\d+)\s*,\s*to:\s*(\d+)\s*\}", text)
        ]
    return seed_ids, edges


def seed_pid_map():
    """scholars:<yerel id> curie'lerinden {yerel id (int): pid_no}."""
    con = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE 'scholars:%' "
        "ORDER BY source_id"
    ).fetchall()
    con.close()
    out = {}
    for source_id, pid in rows:
        local = source_id.split(":", 1)[1]
        num = pid_num(pid)
        if num is None or not local.isdigit():
            continue
        out[int(local)] = num
    return out


# ---------------------------------------------------------------- serileştirme

def build_records(persons, codes, only_with_curie=False, short_names=False, targets=None):
    """LITE kayıt listesi — pid numarası artan (determinizm)."""
    records = []
    for num in sorted(persons):
        p = persons[num]
        srcs = codes.get(num)
        if only_with_curie and not srcs:
            continue
        rec = {"id": num}
        if p["ad_tr"]:
            rec["ad_tr"] = p["ad_tr"]
        if p["ad_ar"] and not short_names:
            rec["ad_ar"] = p["ad_ar"]
        if p["oh"] is not None:
            rec["oh"] = p["oh"]
        if p["om"] is not None:
            rec["om"] = p["om"]
        if srcs:
            rec["k"] = [c for c in CODE_ORDER if c in srcs]
        # H46: çözülmüş hedefler (alt-kod -> locator). YALNIZ gerçekten açılan
        # hedefler yazılır; alan yoksa rozet tıklanamaz ve öyle görünür.
        t = (targets or {}).get(num)
        if t:
            rec["t"] = t
        if p["m"] and not short_names:
            rec["m"] = p["m"]
        records.append(rec)
    return records


def serialize_pool(records, notes):
    doc = (
        "Ulema Havuzu — LITE endeks. Kapsam: magazadaki TUM kisi kayitlari "
        "(data/canonical/person/*.json); statik liste degil, her yeni kitapla "
        "yeniden uretilerek buyur. 'id' alani iac:person- onekisiz numaradir; "
        "pid = _pid_format % id. Olum tarihleri YALNIZ death_temporal'dan gelir, "
        "yoksa alan hic yazilmaz (tahmin yok). Uretici: " + GENERATED_BY
    )
    if notes:
        doc += " NOT: " + " ".join(notes)
    out = {
        "_doc": doc,
        "_pid_format": PID_FORMAT,
        "_kaynak_kodlari": {c: CODE_LABELS[c] for c in CODE_ORDER},
        "n": len(records),
        "kisiler": records,
    }
    return (
        json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def serialize_meta(meta):
    return (
        json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


# ---------------------------------------------------------------- meta

def build_meta(records, persons, codes, prefix_counts, scan_stats,
               bracket_total, notes):
    """Tüm sayımlar HAVUZA GİREN kayıtlar üzerinden yapılır."""
    in_pool = {r["id"] for r in records}

    per_source = Counter()
    for r in records:
        for c in r.get("k", []):
            per_source[c] += 1
    curiesiz = sum(1 for r in records if not r.get("k"))

    sets = {c: {r["id"] for r in records if c in r.get("k", [])} for c in CODE_ORDER}
    a, d, e = sets["a"], sets["d"], sets["e"]
    overlap = {
        "a_kesisim_d": len(a & d),
        "a_kesisim_e": len(a & e),
        "d_kesisim_e": len(d & e),
        "a_kesisim_d_kesisim_e": len(a & d & e),
        "yalniz_a": len(a - d - e),
        "yalniz_d": len(d - a - e),
        "yalniz_e": len(e - a - d),
    }

    n_ah = sum(1 for r in records if "oh" in r)
    n_ce = sum(1 for r in records if "om" in r)
    n_any = sum(1 for r in records if "oh" in r or "om" in r)

    seed_ids, edges = load_seed()
    smap = seed_pid_map()
    seed_set = set(seed_ids)
    seed_mapped = {sid: smap[sid] for sid in seed_ids if sid in smap}
    seed_in_pool = {sid: p for sid, p in seed_mapped.items() if p in in_pool}
    # Mağazada scholars: curie'si olup db.json'un guncel 450'sinde KARSILIGI
    # OLMAYAN yerel id'ler (yetim curie) — seed listesinden cikarilmis kayitlar.
    orphan = sorted(set(smap) - seed_set)
    edge_nodes = {n for edge in edges for n in edge}
    uniq_edges = set(edges)
    edges_resolvable = [
        edge for edge in uniq_edges
        if edge[0] in seed_in_pool and edge[1] in seed_in_pool
    ]

    meta = {
        "_doc": (
            "Ulema Havuzu sayimlari. Her sayi bu kosunun taramasindan uretildi; "
            "tahmin/yuvarlama yok. Uretici: " + GENERATED_BY
        ),
        "_notlar": notes,
        "toplam_kisi": len(records),
        "tarama": {
            "canonical_dosya_okunan": scan_stats["okunan"],
            "deprecated_haric": scan_stats["deprecated_haric"],
            "bozuk_pid": scan_stats["bozuk_pid"],
            "entity_bracket_person": bracket_total,
            "dosya_bracket_uyumlu": scan_stats["okunan"] == bracket_total,
            "ad_tr_prefLabel_en_fallback": scan_stats["ad_tr_en_fallback"],
            "havuz_disi_birakilan": scan_stats["okunan"] - len(records),
        },
        "kaynak_basina_kisi": {c: per_source.get(c, 0) for c in CODE_ORDER},
        "kaynak_curiesiz_kisi": curiesiz,
        "ham_curie_onek_sayimi": dict(sorted(prefix_counts.items())),
        "cakisma_matrisi": overlap,
        "olum_tarihi": {
            "hicri_var": n_ah,
            "miladi_var": n_ce,
            "en_az_biri_var": n_any,
            "tarihsiz": len(records) - n_any,
        },
        "tohum_450": {
            "_doc": (
                "'havuzda' = scholars:<id> curie'si uzerinden havuzdaki bir pid'e "
                "IZLENEBILEN tohum sayisi. Curie'si olmayan tohumlar icin havuz "
                "uyeligi BILINMIYOR: ayni kisi baska bir kaynak curie'siyle (el-alam, "
                "dia, ...) havuzda olabilir; isim eslestirmesi Faz-2 isi, burada "
                "tahmin YAPILMADI."
            ),
            "db_json_scholar_sayisi": len(seed_ids),
            "tekil_id": len(seed_set),
            "id_araligi": [min(seed_ids), max(seed_ids)] if seed_ids else [],
            "scholars_curie_ile_pid_almis": len(seed_mapped),
            "havuzda_izlenebilir": len(seed_in_pool),
            "scholars_curie_yok_havuz_durumu_bilinmiyor": (
                len(seed_set) - len(seed_mapped)
            ),
            "yetim_scholars_curie": orphan,
            "yetim_scholars_curie_sayisi": len(orphan),
            "isnad_zincir_sayisi_kenar_toplam": len(edges),
            "isnad_kenar_tekil": len(uniq_edges),
            "isnad_dugum_tekil": len(edge_nodes),
            "isnad_dugum_havuzda_izlenebilir": len(edge_nodes & set(seed_in_pool)),
            "isnad_tekil_kenar_iki_ucu_havuzda": len(edges_resolvable),
        },
        "meslek_dagilimi": dict(
            sorted(
                Counter(m for r in records for m in r.get("m", [])).items(),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
    }
    return meta


# ---------------------------------------------------------------- main

def main():
    if not PERSON_DIR.is_dir():
        print(f"HATA: {PERSON_DIR} yok", file=sys.stderr)
        return 1

    persons, scan_stats = load_persons()
    codes, prefix_counts, locators = load_source_codes()

    # H55: 'bo' rozetini kişinin MİNT KAYNAĞINDAN değil, ESERİNİN varlığından
    # türet. Ekleme yapar, silme yapmaz (ölçüldü: fazladan rozet 0).
    oi = openiti_authors()
    bo_eklenen = 0
    for num in oi:
        if num not in persons:
            continue                        # havuzda olmayan kişiye rozet basılmaz
        s = codes.setdefault(num, set())
        if "bo" not in s:
            s.add("bo")
            bo_eklenen += 1
    print(f"  'bo' rozeti eser bagindan eklendi: +{bo_eklenen} "
          f"(OpenITI eseri olan kisi {len(oi)})")

    targets, target_counts = resolve_targets(locators)
    print(f"  hedefi cozulen: {dict(target_counts)}")
    bracket_total = store_person_total()

    notes = []
    records = build_records(persons, codes, targets=targets)
    payload = serialize_pool(records, notes)

    if len(payload) > SIZE_CAP:
        dropped = sum(1 for n in persons if not codes.get(n))
        notes.append(
            f"Tam cikti {SIZE_CAP} bayt sinirini asti; yalnız >=1 kaynak-curie'li "
            f"kisiler tutuldu, kaynak-curie'siz {dropped} mint kayit HAVUZ DISI "
            f"birakildi."
        )
        records = build_records(persons, codes, only_with_curie=True, targets=targets)
        payload = serialize_pool(records, notes)

    if len(payload) > SIZE_CAP:
        notes.append(
            "Ikinci asamada da sinir asildi; alan kisaltmasina gidildi: "
            "ad_ar ve meslek alanlari LITE endeksten cikarildi "
            "(detay katmanindan alinmali)."
        )
        records = build_records(
            persons, codes, only_with_curie=True, short_names=True
        , targets=targets)
        payload = serialize_pool(records, notes)

    meta = build_meta(
        records, persons, codes, prefix_counts, scan_stats, bracket_total, notes
    )
    meta_payload = serialize_meta(meta)

    write_bytes(OUT_POOL, payload)
    write_bytes(OUT_META, meta_payload)

    print(f"ulema_pool.json      : {OUT_POOL}  ({len(payload)} bayt)")
    print(f"ulema_pool_meta.json : {OUT_META}  ({len(meta_payload)} bayt)")
    print(f"toplam kisi          : {meta['toplam_kisi']}")
    print(f"kaynak basina        : {meta['kaynak_basina_kisi']}")
    print(f"kaynak-curie'siz     : {meta['kaynak_curiesiz_kisi']}")
    print(f"cakisma              : {meta['cakisma_matrisi']}")
    print(f"olum tarihi          : {meta['olum_tarihi']}")
    print(f"450 tohum            : {meta['tohum_450']}")
    if notes:
        print("BOYUT KARARLARI:")
        for n in notes:
            print("  - " + n)
    else:
        print("boyut karari         : gerekmedi (sinir altinda, kayit atilmadi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
