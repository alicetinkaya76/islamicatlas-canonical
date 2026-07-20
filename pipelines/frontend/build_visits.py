#!/usr/bin/env python3
"""Dalga-4 "DURAK (ziyaret) modeli" — seyahatnâmelerin ORTAK rota omurgası.

    python3 pipelines/frontend/build_visits.py

Bu dosya bir kap (container) üreticisi DEĞİL, kap şemasına eklenen YENİ BİR
KAVRAMIN üreticisidir. Kap "bu kitapta hangi kayıtlar var + pid'leri ne"
sorusunu yanıtlar; DURAK "seyyah nereye, hangi SIRAYLA gitti" sorusunu
yanıtlar. İkisi diktir: bir kap duraksız olabilir (Yâkût bir sözlüktür),
bir durak kapsız olamaz (her durak bir kitaba aittir).

Çıktı:
    web/public/books/visits.json       — {seyahatler[], duraklar[]}
    web/public/books/visits_meta.json  — sayımlar + dürüst sınırlar + sözleşme

Gelecekteki HER seyahatnâme bu şemaya bağlanacağı için tasarım gerekçesi
aşağıda açıkça yazılıdır; runbook: docs/h21/DURAK_MODELI.md


TASARIM GEREKÇESİ (neden bu alanlar, neden bu kadarı)
-----------------------------------------------------

(1) visits.json bir "ROTA OMURGASI"dır, kaynak katmanların yerine geçmez.
    Üç kaynağın alan kümeleri taban tabana farklı: İbn Battûta'da 33 alan
    (quote_ar/tr/en, narr, obs, topics, people, xref, country, region...),
    İbn Cübeyr'de 21, Evliyâ'da 16 (ama içlerinde kilobaytlık
    description_tr'ler). Bunların BİRLEŞİMİNİ tek şemaya taşımak iki
    zarar üretir: (a) dosya onlarca MB'a çıkar, (b) kaynağa özgü alanlar
    "ortak şema" kılığına girip aslında ortak olmadıkları hâlde ortakmış
    gibi görünür. Bu yüzden visits.json YALNIZ her seyahatnâmede
    tanımlı olan/olabilecek asgari müştereği taşır:
        kimlik (sid, seq) · ad (ad_ar, ad_tr) · konum (yer_pid, lat, lon)
        zaman (varis_h, varis_metin) · nitelik (is_stay, sec, guven, geo_note)
    Zengin alanlar kaynak katmanında kalır ve (kaynak, sid, seq) üçlüsüyle
    ya da yer_pid ile JOIN edilir. Yeni bir kitap eklerken "ortak şemaya
    alan ekleme" refleksi yerine "kaynak katmanında bırak" refleksi esastır.

(2) SIRA HER KAYNAKTA AYNI ŞEYİ İFADE ETMEZ → `sira_turu` (seyahat düzeyi).
    Bu, bu turun EN ÖNEMLİ bulgusudur ve şemaya alan eklememizin tek
    gerekçesidir. Keşif: Evliyâ katmanının dosya sırası seyahatler arasında
    ÖRÜLÜDÜR — 5.444 kayıt voyage_id'ye göre 343 ayrı bloğa dağılmış
    durumda (V05 4 kayıt → V07 3 kayıt → V05 1 kayıt → ...). Yani EC_ id
    sırası bir GÜZERGÂH sırası değil, Başaran Google Maps dışa aktarımının
    liste sırasıdır. Bunu sessizce `seq: 1..N` diye yazmak, veriye
    olmayan bir güzergâh iddiası eklemek olurdu (North Star ihlali).
    Çözüm: her seyahat kaydı sırasının NE OLDUĞUNU beyan eder —
        "metin_tanikli" : sıra metinden/çıkarımdan gelir, güzergâhtır
                          (rihla: voyage içi seq; ibn-jubayr: sec + bölüm
                           içi sıra üzerinden kurulmuş seq)
        "dosya_sirasi"  : sıra yalnızca kaynak dosyanın sırasıdır,
                          GÜZERGÂH DEĞİLDİR (evliya)
    UI kuralı: `sira_turu != "metin_tanikli"` olan seyahatte duraklar
    çizgiyle BİRLEŞTİRİLMEZ (nokta bulutu olarak gösterilir).

(3) TARİH TAHMİNİ YASAK — iki ayrı korumayla.
    (a) `varis_metin` metindeki İFADEDİR, aynen taşınır, çevrilmez,
        normalleştirilmez (İbn Cübeyr'in arrival_text'i).
    (b) `varis_h` yalnız kaynağın kendisinin tahmin OLARAK İŞARETLEMEDİĞİ
        hicrî tarihlerde yazılır. İbn Battûta katmanında arr_ah dolu olan
        175 durağın 110'u `date_uncertain: true` ile işaretli; bunlar
        milâdî `arr` alanından geri hesaplanmış tahminlerdir → visits.json'a
        ALINMAZ (sayısı meta'da bastirilan_varis_h olarak raporlanır).
        Milâdî `arr` alanı hiç taşınmaz: türetilmiş tarihtir, şemada yeri yok.

(4) `guven` = DURAK çıkarımının güveni. Evliyâ'nın `category_confidence`
    alanı buraya EŞLENMEZ: o alan "bu yer bir cami mi kale mi" sınıflandırma
    güvenidir, durağın kendisinin güveni değildir. Farklı anlamı aynı ada
    koymak sessiz bir yalandır → Evliyâ duraklarında `guven` YOKTUR.

(5) NULL ŞİŞİRME YOK. Alan yoksa anahtar hiç yazılmaz ("lat": null değil,
    "lat" anahtarı hiç yok). Boş string de yazılmaz. False ve 0.0 gerçek
    değerdir, yazılır. Bu kural dosyayı ~%35 küçültür ve "veri var ama
    null" ile "veri yok" ayrımını tüketiciye net verir.

(6) KOORDİNATSIZ DURAK ATILMAZ. İbn Cübeyr'in 83 durağı geocode edilemedi;
    bunlar yer_pid/lat/lon anahtarları OLMADAN girer. Rotanın uzunluğu
    haritanın kapsamına indirgenirse metin çarpıtılır: seyyah oraya gitti,
    biz nokta koyamadık — bu iki ayrı olgudur.

(7) ŞÜPHELİ KOORDİNAT GİZLENİR AMA SİLİNMEZ. postprocess_ibn_jubayr'ın
    süreklilik süpürmesiyle işaretlenmiş 7 durak (`geo_suspect`) veriye
    `geo_note` ön ekiyle girer; UI bunları haritada gizler, kayıt kalır.

(8) ANAHTARLAR DAİMA KAYNAK ÖNEKLİDİR. `sid` asla çıplak "V05" ya da "1"
    değildir; "evliya-V05", "rihla-v1", "ibn-jubayr-v1" biçimindedir.
    Gerekçe H19/build_containers dersi: Salibiyyât'ın clusters[].id'si
    ("EC_NNNN") Evliyâ'nın "EC_NNNNN" önekiyle çakışıyordu. Tek dosyada
    üç kitap birleştiği anda çıplak id çakışma davetidir.

(9) DETERMİNİZM. Timestamp yok, "generated" alanı yok, sıralama sabit
    (seyahatler sid'e göre, duraklar (sid, seq)'e göre), json sort_keys.
    Aynı girdiyle iki koşu bayt-bayt aynıdır; --check-determinism ile
    kanıtlanır.


ÜÇ KAYNAĞIN KEŞFEDİLEN ŞEKLİ (2026-07-20; varsayılmadı, okundu)
----------------------------------------------------------------
web/public/data/ibn_battuta_atlas_layer.json   609 KB
    {metadata, travelers[1], travel_voyages[7], travel_stops[317]}
    stop alanları (33, hepsi 317/317 dolu anahtar olarak):
      id, traveler_id, voyage_id, seq, tr, en, ar, lat, lon, arr, arr_ah,
      dep, stay, region_tr/en, country, type, sig, quote_ar/tr/en,
      narr_tr/en, people, topics, obs_tr/en, xref, confidence,
      date_uncertain, disputed, src_line, src_page
    seq VOYAGE-İÇİDİR (her seyahat 1..N; global tekil değil) → sid şart.
    lat/lon 317/317 dolu. yer_pid dış kaynaktan: source_curie 'ibn-battuta:<id>'
    (120 curie, hepsi iac:place-*, hepsi bir stop id'sine birebir oturuyor).

web/public/reading/00002694/stops_draft.json   262 KB
    {metadata, stops[208]}  — postprocess_ibn_jubayr.py çıktısı
    seq GLOBAL ve 1..208 kesintisiz (tek seyahat). place_pid 125,
    lat/lon 125, geo_note 64, geo_candidates 41, geo_suspect 7,
    arrival_text 167 dolu, arrival_h 66 dolu, is_stay 208/208 (140 true).
    NOT: arrival_h'de yıl basamağı tutarsız ("578-10-26" ve "0578-12-08"
    bir arada) — DÜZELTİLMEDİ, aynen taşındı; meta'da rapor edilir.

web/public/data/evliya_atlas_layer.json   13,3 MB
    {metadata, voyages[10], places[5444]}
    place alanları (16): id, lat, lng(!), voyage_id, volume, year_approx,
      category, description_tr/en/ar, source, cross_refs,
      category_confidence, name_en, name_ar, name_tr
    · lng, lat/lon değil → yeniden adlandırıldı.
    · volume 5444/5444 NULL; year_approx 5444/5444 NULL (anahtar 5431'de
      var ama değer yok) → bu iki alan TAŞINMAZ, ölü alandır.
    · ARRIVAL/IS_STAY/SEC/QUOTE karşılığı YOK → o alanlar yazılmaz.
    · lat/lng 5444/5444 dolu (koordinatsız durak yok).
    · dosya sırası seyahatler arasında örülü (343 blok) → sira_turu
      "dosya_sirasi" (bkz. gerekçe 2).
    · kayıtların çoğu güzergâh durağı değil, ŞEHİR İÇİ YAPIDIR
      (cami 1097, türbe 456, hamam 303...); ayrım category alanındadır ve
      kaynak katmanda kalır — meta'da uyarı olarak yazılıdır.
"""

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "web" / "public" / "data"
READING = REPO / "web" / "public" / "reading"
SQLITE = REPO / "data" / "_index" / "lookup.sqlite"
BOOKS = REPO / "web" / "public" / "books"

GENERATED_BY = "pipelines/frontend/build_visits.py"
SCHEMA_VERSION = "durak-1.0.0"

# 5 MB tavanı: aşılırsa Evliyâ seyahat-bazlı ayrı dosyalara bölünür.
SIZE_LIMIT_BYTES = 5 * 1024 * 1024

# Sıra türü sözlüğü — seyahat kaydındaki `sira_turu` alanının izinli değerleri.
SIRA_METIN = "metin_tanikli"   # sıra güzergâhtır; UI çizgi çizebilir
SIRA_DOSYA = "dosya_sirasi"    # sıra yalnız dosya sırasıdır; UI çizgi ÇİZMEZ

# Duraklarda izin verilen anahtarlar — sözleşme burada kilitlenir.
STOP_KEYS = ("sid", "seq", "yer_pid", "ad_ar", "ad_tr", "lat", "lon",
             "varis_h", "varis_metin", "is_stay", "sec", "guven", "geo_note")
VOYAGE_KEYS = ("id", "kaynak", "ad_tr", "seyyah_pid", "work_pid", "n_durak",
               "sira_turu")


# ------------------------------------------------------------- yardımcılar

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    """Deterministik yazım: sort_keys, sabit indent, sondaki tek newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def put(rec, key, value):
    """Null şişirme yasağı: None ve "" yazılmaz; False/0/0.0 gerçek değerdir."""
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    rec[key] = value


def check_keys(records, allowed, what):
    """Sözleşme bekçisi: şema dışı alan kaçağı sessizce geçmesin."""
    stray = {k for r in records for k in r} - set(allowed)
    if stray:
        raise SystemExit("ŞEMA İHLALİ ({}): beklenmeyen alan {}".format(
            what, sorted(stray)))


def curie_map(cur, prefix):
    """source_curie'den {yerel_id: pid}."""
    rows = cur.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?",
        (prefix + ":%",)).fetchall()
    return {sid.split(":", 1)[1]: pid for sid, pid in rows}


def pid_exists(cur, pid):
    return cur.execute(
        "SELECT 1 FROM entity_bracket WHERE pid = ?", (pid,)).fetchone() is not None


def pid_kind(pid):
    return pid.split(":", 1)[1].rsplit("-", 1)[0]


def geo_report(stops):
    """Koordinatlı / koordinatsız / şüpheli sayımı — hepsi SAYILIR, tahmin yok."""
    return {
        "koordinatli": sum(1 for s in stops if "lat" in s),
        "koordinatsiz": sum(1 for s in stops if "lat" not in s),
        "geo_note_tasiyan": sum(1 for s in stops if "geo_note" in s),
        "geo_suspect": sum(1 for s in stops
                           if str(s.get("geo_note", "")).startswith("geo_suspect")),
        "yer_pid_li": sum(1 for s in stops if "yer_pid" in s),
        "yer_pid_siz": sum(1 for s in stops if "yer_pid" not in s),
        # Ayrık iki olgu: kimlik çözüldü ≠ konum bilindiği. Mağazadaki kayıtta
        # koordinat yoksa durak pid'li ama noktasız kalır (atılmaz).
        "yer_pid_li_ama_koordinatsiz": sum(
            1 for s in stops if "yer_pid" in s and "lat" not in s),
        "koordinatli_ama_yer_pid_siz": sum(
            1 for s in stops if "lat" in s and "yer_pid" not in s),
    }


# ------------------------------------------------------------------ kimlik
# Seyyah/eser pid'leri: mağaza etiket taramasıyla doğrulandı (2026-07-20).
# Mağazada DUBLET olan yerlerde build_containers.py precedent'i uygulanır:
# en küçük pid yazılır, adayların TAMAMI meta'da listelenir, otomatik
# birleştirme YAPILMAZ (dublet temizliği ayrı bir insan kararıdır).

IDENTITY = {
    "rihla": {
        "seyyah_pid": "iac:person-00000198",
        "seyyah_adaylar": ["iac:person-00000198"],
        "seyyah_note": "Tek eşleşme (ابن بطوطة); dublet yok.",
        "work_pid": "iac:work-00000026",
        "work_adaylar": ["iac:work-00000026", "iac:work-00000841"],
        "work_note": ("Dublet: iac:work-00000026 ve iac:work-00000841 aynı eser "
                      "(تحفة النظار في غرائب الأمصار وعجائب الأسفار); en küçük "
                      "pid yazıldı, birleştirme YAPILMADI."),
    },
    "ibn-jubayr": {
        "seyyah_pid": "iac:person-00000300",
        "seyyah_adaylar": ["iac:person-00000300", "iac:person-00000349",
                           "iac:person-00003718"],
        "seyyah_note": ("ÜÇ aday da aynı kişi görünümünde (İbn Cübeyr, ö. 614/1217); "
                        "en küçük pid yazıldı. Mağaza-içi kişi dubleti — insan "
                        "kararı bekler, otomatik birleştirilmedi."),
        # Kaynak katmanın KENDİ beyanı; üzerine yazılmaz.
        "work_pid": "iac:work-00002694",
        "work_adaylar": ["iac:work-00000157", "iac:work-00000208",
                         "iac:work-00002694"],
        "work_note": ("work_pid kaynak katmanın kendi metadata.source_work "
                      "beyanından alındı (iac:work-00002694); mağazada aynı esere "
                      "işaret eden 2 dublet daha var, seçim DEĞİŞTİRİLMEDİ."),
    },
    "evliya": {
        "seyyah_pid": "iac:person-00000223",
        "seyyah_adaylar": ["iac:person-00000223", "iac:person-00000351",
                           "iac:person-00002620"],
        "seyyah_note": ("Dublet: 223 ve 351 aynı kişi (ö. 1682); 2620 ayrı bir "
                        "kayıt (ö. 1684, 'Evli̇ya Çelebi̇' — noktasız-i artefaktı "
                        "şüphesi). En küçük pid yazıldı, birleştirme YAPILMADI."),
        "work_pid": "iac:work-00000062",
        "work_adaylar": ["iac:work-00000062", "iac:work-00000210"],
        "work_note": ("Dublet: iac:work-00000062 ve iac:work-00000210 aynı eser "
                      "(Seyahatnâme); build_containers.py ile aynı seçim."),
    },
}


# ------------------------------------------------------------------ rihla

def build_rihla(cur):
    """İbn Battûta — travel_voyages[7] + travel_stops[317]."""
    layer = load_json(DATA / "ibn_battuta_atlas_layer.json")
    ident = IDENTITY["rihla"]
    pids = curie_map(cur, "ibn-battuta")

    voyages, stops = [], []
    suppressed_h = 0        # date_uncertain yüzünden yazılmayan hicrî tarih
    stay_unknown = 0        # stay alanı None → is_stay çıkarılamaz

    for v in sorted(layer["travel_voyages"], key=lambda x: int(x["id"])):
        sid = "rihla-v{}".format(int(v["id"]))
        vs = [s for s in layer["travel_stops"]
              if str(s["voyage_id"]) == str(v["id"])]
        vs.sort(key=lambda s: int(s["seq"]))

        for s in vs:
            rec = {"sid": sid, "seq": int(s["seq"])}
            put(rec, "yer_pid", pids.get(str(s["id"])))
            put(rec, "ad_ar", s.get("ar"))
            put(rec, "ad_tr", s.get("tr"))
            if s.get("lat") is not None and s.get("lon") is not None:
                rec["lat"], rec["lon"] = s["lat"], s["lon"]
            # Tarih: yalnız kaynağın tahmin İŞARETLEMEDİĞİ hicrî tarih girer.
            if s.get("arr_ah"):
                if s.get("date_uncertain"):
                    suppressed_h += 1
                else:
                    rec["varis_h"] = s["arr_ah"]
            # varis_metin: bu katmanda metindeki varış İFADESİ alanı YOK
            # (quote_ar bir alıntıdır, varış ifadesi değil) → yazılmaz.
            if s.get("stay") is None:
                stay_unknown += 1
            else:
                rec["is_stay"] = int(s["stay"]) > 0
            put(rec, "guven", s.get("confidence"))
            stops.append(rec)

        voyages.append({
            "id": sid,
            "kaynak": "rihla",
            "ad_tr": v["title_tr"],
            "seyyah_pid": ident["seyyah_pid"],
            "work_pid": ident["work_pid"],
            "n_durak": len(vs),
            "sira_turu": SIRA_METIN,
        })

    report = {
        "kaynak_dosya": "web/public/data/ibn_battuta_atlas_layer.json",
        "ham_kayit": len(layer["travel_stops"]),
        "n_seyahat": len(voyages),
        "n_durak": len(stops),
        "sira_turu": SIRA_METIN,
        "sira_gerekce": ("travel_stops[].seq voyage-İÇİ 1..N kesintisiz; "
                         "güzergâh sırasıdır."),
        "yer_pid_kaynagi": "source_curie 'ibn-battuta:<stop id>'",
        "yer_pid_curie_sayisi": len(pids),
        "varis_h_yazilan": sum(1 for s in stops if "varis_h" in s),
        "varis_h_bastirilan_date_uncertain": suppressed_h,
        "varis_metin_yok_gerekce": (
            "Katmanda metindeki varış İFADESİNİ tutan alan yok; milâdî 'arr' "
            "türetilmiş tarihtir ve şemaya alınmaz."),
        "is_stay_kaynagi": "stay (gün sayısı) > 0",
        "is_stay_bilinmeyen": stay_unknown,
        "tasinmayan_alanlar": sorted([
            "arr", "country", "date_uncertain", "dep", "disputed", "en",
            "narr_en", "narr_tr", "obs_en", "obs_tr", "people", "quote_ar",
            "quote_en", "quote_tr", "region_en", "region_tr", "sig",
            "src_line", "src_page", "stay", "topics", "type", "xref"]),
        "tasinmayan_gerekce": (
            "Rota omurgası ilkesi (gerekçe 1): kaynağa özgü zenginlik kaynak "
            "katmanda kalır, (kaynak, sid, seq) ile JOIN edilir. Dikkat: "
            "`disputed: true` işaretli 10 durak visits.json'da AYRICA "
            "işaretlenmez — ihtilaf bilgisi kaynak katmandadır."),
    }
    report.update(geo_report(stops))
    return voyages, stops, report


# ------------------------------------------------------------- ibn-jubayr

def build_ibn_jubayr(cur):
    """İbn Cübeyr — tek seyahat, postprocess_ibn_jubayr.py çıktısı."""
    src = READING / "00002694" / "stops_draft.json"
    layer = load_json(src)
    ident = IDENTITY["ibn-jubayr"]
    sid = "ibn-jubayr-v1"

    stops, bad_pid = [], []
    h_formats = Counter()
    for s in sorted(layer["stops"], key=lambda x: int(x["seq"])):
        rec = {"sid": sid, "seq": int(s["seq"])}
        pid = s.get("place_pid")
        if pid:
            if pid_exists(cur, pid):
                rec["yer_pid"] = pid
            else:
                bad_pid.append(pid)
        put(rec, "ad_ar", s.get("name_ar"))
        put(rec, "ad_tr", s.get("name_tr"))
        if s.get("lat") is not None and s.get("lon") is not None:
            rec["lat"], rec["lon"] = s["lat"], s["lon"]
        if s.get("arrival_h"):
            rec["varis_h"] = s["arrival_h"]           # AYNEN; normalize edilmez
            h_formats[len(str(s["arrival_h"]).split("-")[0])] += 1
        put(rec, "varis_metin", s.get("arrival_text"))  # metindeki İFADE, aynen
        if s.get("is_stay") is not None:
            rec["is_stay"] = bool(s["is_stay"])
        if s.get("sec") is not None:
            rec["sec"] = int(s["sec"])
        put(rec, "guven", s.get("confidence"))
        # geo_suspect: veriye GİRER, notla işaretlenir; UI gizler.
        note = s.get("geo_note")
        if s.get("geo_suspect"):
            mark = ("geo_suspect: süreklilik süpürmesi — komşu duraklara >800 km; "
                    "haritada gizlenir, kayıt korunur")
            note = mark + (" | " + note if note else "")
        put(rec, "geo_note", note)
        stops.append(rec)

    voyages = [{
        "id": sid,
        "kaynak": "ibn-jubayr",
        "ad_tr": "Rihle — Gırnata'dan Hicaz'a ve dönüş",
        "seyyah_pid": ident["seyyah_pid"],
        "work_pid": ident["work_pid"],
        "n_durak": len(stops),
        "sira_turu": SIRA_METIN,
    }]

    report = {
        "kaynak_dosya": "web/public/reading/00002694/stops_draft.json",
        "ham_kayit": len(layer["stops"]),
        "n_seyahat": 1,
        "n_durak": len(stops),
        "sira_turu": SIRA_METIN,
        "sira_gerekce": ("stops[].seq global 1..N kesintisiz; "
                         "postprocess_ibn_jubayr.py'de sec + bölüm-içi sıradan "
                         "kurulmuş güzergâh sırasıdır."),
        "yer_pid_kaynagi": "stops[].place_pid (entity_bracket'te doğrulandı)",
        "yer_pid_dogrulanamayan": sorted(set(bad_pid)),
        "pid_li_koordinatsiz_ornek": (
            "seq 26 سبك/Sebk → iac:place-00006269: pid mağazada VAR ama "
            "entity_bracket'te lat/lon boş. Kaynak dosyada 'lat': null olarak "
            "duruyordu; null şişirme kuralıyla anahtar yazılmadı. Kimlik "
            "çözümü ile konum bilgisi ayrı olgulardır."),
        "varis_h_yazilan": sum(1 for s in stops if "varis_h" in s),
        "varis_h_yil_basamak_dagilimi": dict(sorted(h_formats.items())),
        "varis_h_format_uyarisi": (
            "Kaynakta hicrî yıl basamağı TUTARSIZ ('578-10-26' ile "
            "'0578-12-08' bir arada). DÜZELTİLMEDİ — değer aynen taşındı; "
            "sıralama/karşılaştırma yapan tüketici yılı int'e çevirmelidir. "
            "Onarım kaynak boru hattının (postprocess_ibn_jubayr.py) işidir."),
        "varis_metin_yazilan": sum(1 for s in stops if "varis_metin" in s),
        "tasinmayan_alanlar": sorted([
            "departure_text", "geo_candidates", "name_en", "notes", "page",
            "people", "quote_ar", "secs", "stay_summary_tr", "type"]),
        "tasinmayan_gerekce": (
            "Rota omurgası ilkesi (gerekçe 1). `geo_candidates` (41 durak) "
            "bilerek dışarıda: belirsizlik çözümü inceleme kuyruğunun konusudur "
            "(data/review_queue/ibn-jubayr-stops.jsonl), rota omurgasının değil."),
        "kaynak_statu": layer["metadata"].get("status"),
    }
    report.update(geo_report(stops))
    return voyages, stops, report


# ---------------------------------------------------------------- evliya

def build_evliya(cur):
    """Evliyâ Çelebi — 10 seyahat, 5.444 yer/yapı.

    DİKKAT: sıra DOSYA SIRASIDIR, güzergâh değildir (bkz. gerekçe 2)."""
    layer = load_json(DATA / "evliya_atlas_layer.json")
    ident = IDENTITY["evliya"]
    pids = curie_map(cur, "evliya-celebi")

    by_voyage = {}
    for p in layer["places"]:
        by_voyage.setdefault(p["voyage_id"], []).append(p)

    names = {v["id"]: v["name_tr"] for v in layer["voyages"]}
    voyages, stops = [], []
    kind_counts = Counter()

    for vid in sorted(by_voyage):
        sid = "evliya-{}".format(vid)
        # Sabit sıralama: EC_ id'ye göre artan (dosya sırasının deterministik hâli)
        vp = sorted(by_voyage[vid], key=lambda x: x["id"])
        for i, p in enumerate(vp, start=1):
            rec = {"sid": sid, "seq": i}
            pid = pids.get(p["id"])
            if pid:
                rec["yer_pid"] = pid
                kind_counts[pid_kind(pid)] += 1
            put(rec, "ad_ar", p.get("name_ar"))
            put(rec, "ad_tr", p.get("name_tr"))
            # kaynak alan adı 'lng' → şemada 'lon'
            if p.get("lat") is not None and p.get("lng") is not None:
                rec["lat"], rec["lon"] = p["lat"], p["lng"]
            # varis_h / varis_metin / is_stay / sec / guven: KARŞILIĞI YOK.
            stops.append(rec)

        voyages.append({
            "id": sid,
            "kaynak": "evliya",
            "ad_tr": names.get(vid, vid),
            "seyyah_pid": ident["seyyah_pid"],
            "work_pid": ident["work_pid"],
            "n_durak": len(vp),
            "sira_turu": SIRA_DOSYA,
        })

    # Dosya sırasının örülülüğünü SAY: kaç blok var (iddianın kanıtı)
    blocks = 1
    prev = layer["places"][0]["voyage_id"]
    for p in layer["places"][1:]:
        if p["voyage_id"] != prev:
            blocks += 1
            prev = p["voyage_id"]

    report = {
        "kaynak_dosya": "web/public/data/evliya_atlas_layer.json",
        "ham_kayit": len(layer["places"]),
        "n_seyahat": len(voyages),
        "n_durak": len(stops),
        "sira_turu": SIRA_DOSYA,
        "sira_gerekce": (
            "Katmanda seq/sıra alanı YOK. Dosya sırası seyahatler arasında "
            "ÖRÜLÜ: 5.444 kayıt voyage_id'ye göre {} ayrı bloğa dağılmış "
            "(ör. V05×4 → V07×3 → V05×1 → ...). Bu bir güzergâh değil, "
            "Başaran Google Maps dışa aktarım sırasıdır. seq yalnızca "
            "seyahat içinde EC_ id'ye göre artan, DETERMİNİSTİK bir "
            "konumlandırmadır; güzergâh İDDİASI DEĞİLDİR."
        ).format(blocks),
        "dosya_sirasi_blok_sayisi": blocks,
        "ui_kurali": ("sira_turu='dosya_sirasi' → duraklar çizgiyle "
                      "BİRLEŞTİRİLMEZ, nokta bulutu olarak gösterilir."),
        "yer_pid_kaynagi": "source_curie 'evliya-celebi:EC_NNNNN'",
        "yer_pid_curie_sayisi": len(pids),
        "yer_pid_tur_dagilimi": dict(sorted(kind_counts.items())),
        "kapsam_uyarisi": (
            "Kayıtların çoğu GÜZERGÂH DURAĞI değil ŞEHİR İÇİ YAPIDIR "
            "(cami 1097, türbe 456, hamam 303, medrese 99...); ayrım kaynak "
            "katmanın `category` alanındadır ve oraya bakılmalıdır. Bu dosya "
            "onları 'ziyaret edilen nokta' olarak taşır, 'durak' olarak "
            "yorumlanmalarını İDDİA ETMEZ."),
        "guven_yok_gerekce": (
            "Katmandaki `category_confidence` bir SINIFLANDIRMA güvenidir "
            "(bu yer cami mi kale mi), durak çıkarımının güveni değildir → "
            "`guven` alanına eşlenmedi (gerekçe 4)."),
        "olu_alanlar": {
            "volume": "5444/5444 null",
            "year_approx": "5444/5444 null (anahtar 5431 kayıtta var, değer yok)",
        },
        "tasinmayan_alanlar": sorted([
            "category", "category_confidence", "cross_refs", "description_ar",
            "description_en", "description_tr", "name_en", "source", "volume",
            "year_approx"]),
        "tasinmayan_gerekce": (
            "description_* alanları kilobaytlıktır; taşınsa dosya ~13 MB olur "
            "ve 5 MB tavanı aşılırdı. cross_refs (2.846 kayıtta dolu) bir "
            "çapraz-referans katmanıdır, rota omurgası değil."),
    }
    report.update(geo_report(stops))
    return voyages, stops, report


# ---------------------------------------------------------------- ana akış

BUILDERS = [
    ("evliya", build_evliya),
    ("ibn-jubayr", build_ibn_jubayr),
    ("rihla", build_rihla),
]


def build():
    con = sqlite3.connect("file:{}?mode=ro".format(SQLITE), uri=True)
    cur = con.cursor()

    all_voyages, all_stops, reports = [], [], {}
    for key, fn in BUILDERS:
        v, s, r = fn(cur)
        all_voyages += v
        all_stops += s
        reports[key] = r

    # kimlik pid'lerinin mağazada GERÇEKTEN var olduğunu doğrula
    for key, ident in IDENTITY.items():
        for field in ("seyyah_pid", "work_pid"):
            pid = ident[field]
            if not pid_exists(cur, pid):
                raise SystemExit("{}: {} mağazada yok → {}".format(key, field, pid))
    con.close()

    # sabit sıralama (determinizm)
    all_voyages.sort(key=lambda v: v["id"])
    all_stops.sort(key=lambda s: (s["sid"], s["seq"]))

    check_keys(all_stops, STOP_KEYS, "duraklar")
    check_keys(all_voyages, VOYAGE_KEYS, "seyahatler")

    # sid bütünlüğü: her durağın sid'i bir seyahatte var; n_durak tutuyor
    vids = {v["id"] for v in all_voyages}
    orphan = sorted({s["sid"] for s in all_stops} - vids)
    if orphan:
        raise SystemExit("yetim sid: {}".format(orphan))
    counted = Counter(s["sid"] for s in all_stops)
    for v in all_voyages:
        if counted[v["id"]] != v["n_durak"]:
            raise SystemExit("n_durak tutmuyor: {} ({} != {})".format(
                v["id"], counted[v["id"]], v["n_durak"]))
    # seq bütünlüğü: her seyahatte 1..n kesintisiz
    for v in all_voyages:
        seqs = sorted(s["seq"] for s in all_stops if s["sid"] == v["id"])
        if seqs != list(range(1, v["n_durak"] + 1)):
            raise SystemExit("seq kesintili: {}".format(v["id"]))

    visits = {"seyahatler": all_voyages, "duraklar": all_stops}
    return visits, reports


def build_meta(visits, reports, size_bytes):
    stops = visits["duraklar"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "sozlesme": {
            "seyahat_alanlari": list(VOYAGE_KEYS),
            "durak_alanlari": list(STOP_KEYS),
            "kaynak_enum": ["evliya", "ibn-jubayr", "rihla"],
            "sira_turu_enum": {
                SIRA_METIN: "sıra metinden/çıkarımdan gelir; GÜZERGÂHTIR",
                SIRA_DOSYA: ("sıra yalnız kaynak dosyanın sırasıdır; "
                             "GÜZERGÂH DEĞİLDİR — UI çizgi çizmez"),
            },
            "null_kurali": ("Alan yoksa anahtar YAZILMAZ. 'lat': null diye bir "
                            "şey yoktur; 'lat' anahtarı ya vardır ya yoktur. "
                            "False ve 0.0 gerçek değerdir."),
            "sid_kurali": ("sid DAİMA kaynak öneklidir (rihla-vN / "
                           "ibn-jubayr-v1 / evliya-VNN); çıplak id yasak."),
            "join_kurali": ("Zengin alanlar kaynak katmanda kalır; visits.json "
                            "(kaynak, sid, seq) ve yer_pid üzerinden JOIN edilir."),
            "determinizm": ("timestamp/generated alanı YOK; seyahatler sid'e, "
                            "duraklar (sid, seq)'e göre sıralı; json sort_keys. "
                            "İki koşu bayt-bayt aynıdır."),
        },
        "toplam": {
            "n_seyahat": len(visits["seyahatler"]),
            "n_durak": len(stops),
            "dosya_bayt": size_bytes,
            "dosya_mb": round(size_bytes / 1024 / 1024, 3),
            "boyut_tavani_mb": 5,
            "bolme_gerekti_mi": size_bytes > SIZE_LIMIT_BYTES,
            **geo_report(stops),
        },
        "kaynak_basina": reports,
        "kimlik": IDENTITY,
        "kimlik_notu": (
            "Seyyah/eser pid'lerinde mağaza dubletleri var. build_containers.py "
            "precedent'i uygulandı: en küçük pid yazıldı, adayların TAMAMI "
            "burada listelendi, hiçbir birleştirme otomatik YAPILMADI — dublet "
            "temizliği ayrı bir insan kararıdır."),
        "durust_sinirlar": [
            "Evliyâ'nın sırası GÜZERGÂH DEĞİLDİR (dosya sırası, 343 blok "
            "hâlinde örülü); sira_turu ile beyan edilir, UI çizgi çizmemelidir.",
            "Evliyâ kayıtlarının çoğu şehir içi yapıdır (cami/türbe/hamam), "
            "güzergâh durağı değil; ayrım kaynak katmanın `category` alanında.",
            "İbn Battûta'da metindeki varış İFADESİ alanı yok → varis_metin "
            "hiçbir rihla durağında yazılmadı.",
            "İbn Battûta'da date_uncertain işaretli 110 hicrî tarih "
            "BASTIRILDI (tahmin yayınlanmaz).",
            "İbn Cübeyr'in hicrî tarihlerinde yıl basamağı tutarsız; "
            "DÜZELTİLMEDİ, aynen taşındı.",
            "İbn Cübeyr katmanı bir ÇIKARIM taslağıdır (sahip kararıyla "
            "yayımlanmış); confidence ve geo_note alanları korunmuştur.",
            "Koordinatsız duraklar ATILMADI; yer_pid/lat/lon anahtarları "
            "olmadan girerler.",
            "geo_suspect duraklar SİLİNMEDİ; geo_note ön ekiyle işaretlenip "
            "veride bırakıldı, gizleme UI'ın işidir.",
        ],
    }


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_determinism():
    """İki koşuyu ayrı dizinlere yazıp bayt-bayt karşılaştırır."""
    hashes = []
    for _ in range(2):
        tmp = Path(tempfile.mkdtemp())
        visits, reports = build()
        p = tmp / "visits.json"
        write_json(p, visits)
        write_json(tmp / "visits_meta.json",
                   build_meta(visits, reports, p.stat().st_size))
        hashes.append((sha256(p), sha256(tmp / "visits_meta.json")))
        shutil.rmtree(tmp)
    ok = hashes[0] == hashes[1]
    print("determinizm: visits.json      sha256={}".format(hashes[0][0]))
    print("             visits_meta.json sha256={}".format(hashes[0][1]))
    print("             iki koşu ayni mi: {}".format("EVET" if ok else "HAYIR"))
    return 0 if ok else 1


def main():
    if "--check-determinism" in sys.argv:
        return check_determinism()

    visits, reports = build()
    out = BOOKS / "visits.json"
    write_json(out, visits)
    size = out.stat().st_size

    if size > SIZE_LIMIT_BYTES:
        raise SystemExit(
            "visits.json {} bayt > 5 MB tavanı — Evliyâ seyahat-bazlı "
            "bölünmeli (docs/h21/DURAK_MODELI.md §bölme).".format(size))

    write_json(BOOKS / "visits_meta.json", build_meta(visits, reports, size))

    for key, r in sorted(reports.items()):
        print("{:11s} seyahat={:2d} durak={:5d} koord={:5d} koordsuz={:4d} "
              "supheli={:d} pid={:5d} sira={}".format(
                  key, r["n_seyahat"], r["n_durak"], r["koordinatli"],
                  r["koordinatsiz"], r["geo_suspect"], r["yer_pid_li"],
                  r["sira_turu"]))
    print("TOPLAM      seyahat={:2d} durak={:5d}  ·  visits.json {} bayt "
          "({:.2f} MB, tavan 5 MB → bölme GEREKMEDİ)".format(
              len(visits["seyahatler"]), len(visits["duraklar"]), size,
              size / 1024 / 1024))
    print("OK →", out.relative_to(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
