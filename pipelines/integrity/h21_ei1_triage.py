#!/usr/bin/env python3
"""
h21_ei1_triage.py — Dalga-4: EI-1 (ei1_lite.json) GÜRÜLTÜ TRİYAJI + tip-bazlı
Tier-2 eşleştirme.

EI-1, mağazadaki en riskli kaynak: 7.568 maddenin tamamı OCR türevi ve içinde
madde OLMAYAN kayıtlar var — yazar imzaları ("R BASSET and R HARTMANN"),
yayıncı künyeleri ("E. J. BRILL"), sayfa üstbilgileri ("al-'AINI  AIR" =
"al-'AINI — AIR" iki-maddebaşlı running head), dergi kısaltmaları ("Z D M G"),
editoryal aparat ("ADDITIONS AND CORRECTIONS") ve saf OCR hurdası.

TRİYAJ SİLMEZ. Her kayıt üç kovadan birine yazılır:
    saglam    → gerçek ansiklopedi maddesi gibi davranan kayıt (eşleştirmeye girer)
    artifact  → yüksek-kesinlikli kural yakaladı (İŞARETLENİR, v1 verisi bozulmaz)
    belirsiz  → kural emin değil → İNSAN kuyruğu (otomatik atma YOK, eşleştirmeye
                de girmez)

Kurallar VERİDEN çıkarıldı (her kuralın yakalama sayısı + 3 örneği çıktı
dosyasındaki `_meta.kurallar` altında raporlanır). Kural mantığı değişirse
sayılar da değişir — rapor edilen her sayı bu koştan üretilir, elle yazılmaz.

İkinci aşama (--resolve): saglam alt kümede tip-bazlı Tier-2 eşleştirme
    at=biography → person namespace
    at=geography → place  namespace
H20 KARAR H20-1 (docs/h20/HAFTA20_DALGA3.md) ZORUNLU ÖN-ADIM: alt-küme
benzerliği kullanan her eşleştirmede "kapsayıcı/idari ek" temizliği. EI-1'de
bunun karşılığı virgüllü ülke eki DEĞİL (EI-1 başlıklarında hiç virgül yok),
iki-maddebaşlı sayfa üstbilgisidir: "al-AHSA  AIBEG" gibi bir başlık
token_set_ratio'da HEM "al-Ahsa" HEM "Aibeg" kaydının alt-kümesi sayılır ve
tek pid'i mıknatısa çevirir. Bu başlıklar zaten `A7_sayfa_ustbilgisi` ile
artifact'e düşer; ayrıca `clean_title()` OCR noktalama gürültüsünü ve tek-harf
artıklarını temizler. Mıknatıs kontrolü koşu sonunda RAPORLANIR (en yoğun
hedef pid kaç kayıt çekiyor).

MİNT YOK. Otomatik borderline kararı YOK. Eşik altı → review kuyruğu.

Usage:
  python3 pipelines/integrity/h21_ei1_triage.py                 # yalnız triyaj
  python3 pipelines/integrity/h21_ei1_triage.py --resolve       # + eşleştirme
  python3 pipelines/integrity/h21_ei1_triage.py --resolve --reset
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from pipelines._lib.institution_common import tr_title  # H31: Türkçe-güvenli başlık

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

SOURCE = REPO_ROOT / "data" / "sources" / "ei1" / "ei1_lite.json"
TRIAGE_OUT = REPO_ROOT / "data" / "_state" / "ei1_triage.json"
AUGMENT_OUT = REPO_ROOT / "data" / "_state" / "h21_ei1_augment_pending.json"
ADAPTER = "h21-ei1"
QUEUE = REPO_ROOT / "data" / "review_queue" / f"{ADAPTER}.jsonl"

# at → resolver namespace (yalnız bu ikisi; concept/dynasty/cross_reference/
# unknown tip-bazlı eşleştirmeye SOKULMAZ — dynasty n=31 ve store'da dynasty
# bracket'ı 186 kayıt, ayrı bir kalibrasyon işi; kapsam dışı bırakıldı)
AT_TO_NS = {"biography": "person", "geography": "place"}


# ---------------------------------------------------------------------------
# yardımcılar
# ---------------------------------------------------------------------------

def nrm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def alpha_tokens(t: str) -> list[str]:
    return [x for x in re.split(r"[^A-Za-z]+", t) if x]


VOWELS = re.compile(r"[AEIOUYaeiouy]")
ROMAN = re.compile(r"^[IVXLCM]+$")

# b. = ibn, l- = al- : Arapça nesep/artikel işaretleri; "initial" sayılmazlar
_FILIATION = {"B", "L"}


# ---------------------------------------------------------------------------
# ARTIFACT kuralları (yüksek kesinlik) — sıra önemlidir, ilk yakalayan kazanır
# ---------------------------------------------------------------------------

def _degenerate_ds(r: dict) -> bool:
    """ds gövde değil, kırpılmış bir imza/atıf kalıntısı: <=14 karakter ve
    başlığı İÇERMİYOR ('R.', 'Z.', '624 ; H.')."""
    ds = (r.get("ds") or "").strip()
    return len(ds) <= 14 and nrm(r["t"]) not in nrm(ds)


def a1_yazar_imza(r: dict) -> bool:
    """Yazar imzası / atıf künyesi: başlıkta >=2 tek-harf BÜYÜK initial
    (B ve L hariç — Arapça 'b.' ve 'l-') VE gövde dejenere.
    Kanıt: id 0 'R BASSET and R HARTMANN' ds='R.'."""
    inits = sum(1 for x in alpha_tokens(r["t"])
                if len(x) == 1 and x.isupper() and x not in _FILIATION)
    return inits >= 2 and _degenerate_ds(r)


_PUBLISHER = re.compile(r"\b(BRILL|LUZAC|ORIENTAL PUBLISHER|ORTENTAT PUBLISHER)\b",
                        re.IGNORECASE)


def a2_yayinci_kunye(r: dict) -> bool:
    """Yayıncı/ilan künyesi: Brill, Luzac, 'ORIENTAL PUBLISHER' — ansiklopedi
    maddesi değil, cilt önü/arkası reklam ve imprint satırı."""
    return bool(_PUBLISHER.search(r["t"]))


_EDITORIAL = re.compile(
    r"\b(ADDITIONS?|CORRECTIONS?|ERRATA|EXPLICATION OF PLATES|"
    r"TABLE OF CONTENTS|LIST OF ABBREVIATIONS)\b", re.IGNORECASE)


def a3_editoryal_aparat(r: dict) -> bool:
    """Editoryal aparat: 'ADDITIONS AND CORRECTIONS', 'EXPLICATION OF PLATES' —
    cilt aparatı, madde değil."""
    return bool(_EDITORIAL.search(r["t"]))


def a7_sayfa_ustbilgisi(r: dict) -> bool:
    """Sayfa üstbilgisi (running head): EI-1 sayfa başlığı o sayfanın İLK ve SON
    maddebaşını 'X — Y' biçiminde taşır; OCR bunu başlıkta ÇİFT BOŞLUKLA
    ("al-'AINI  AIR"), gövdede em-dash'le bırakmış. İKİ maddebaşlı bir başlık
    alt-küme benzerliğinde iki ayrı kaydın da alt-kümesi sayılır → H20-1
    mıknatıs riski. Bu yüzden ayrı ve erken bir kural."""
    if not re.search(r"  +", r["t"]):
        return False
    ds = r.get("ds") or ""
    return ("—" in ds) or ("–" in ds)


def a8_atif_parcasi(r: dict) -> bool:
    """Atıf/dizgi parçası: başlıkta >=2 boşluklu bir kopukluk VAR ve gövde
    dejenere ('p  BIFAO' ds='p.', 'in TBGK  V' ds='in T.B.G.K.'). A7 ile aynı
    çift-boşluk sinyali, ama gövdede em-dash yok — running head değil, dipnot/
    atıf satırından kopmuş parça. Tek başına çift boşluk YETMEZ (OCR meşru
    başlıkları da böler: 'al-KAZV  NI' gövdesi dolu, yakalanmaz)."""
    return bool(re.search(r"  +", r["t"])) and _degenerate_ds(r)


def a4_roma_rakami_baslik(r: dict) -> bool:
    """Başlık saf Roma rakamı ('XVII', 'LXXXIX'): cilt/bölüm numarası ya da
    atıf içindeki cilt sayısı — maddebaşı değil."""
    a = re.sub(r"[^A-Za-z]", "", r["t"])
    return len(a) >= 2 and bool(ROMAN.match(a))


_CITATION_DS = re.compile(r"([A-Z]\.){2,}|\bp\.\s*\d|\bser\.|\bvol\.")


def a5_kaynakca_kisaltmasi(r: dict) -> bool:
    """Süreli yayın kısaltması: başlığın harfleri tümü BÜYÜK ve SESLİ HARF YOK
    (ZDMG, JRAS, SBPMS, WZKM) VE gövde atıf kalıbı taşıyor ('Z.D.M.G., 1898,
    lii.'). İki koşul birlikte istenir — sesli-harfsiz her başlık kısaltma
    değildir (OCR bozuğu 'GRDS'=Gördes gibi vakalar tek başına yakalanmaz)."""
    a = re.sub(r"[^A-Za-z]", "", r["t"])
    if len(a) < 3 or not a.isupper() or VOWELS.search(a):
        return False
    return bool(_CITATION_DS.search(r.get("ds") or ""))


def a6_alfabetik_olmayan_hurda(r: dict) -> bool:
    """Saf OCR hurdası: başlıktaki harf oranı %50'nin altında ya da toplam harf
    sayısı 2'den az ("O - JJ", "C A'- J", "P- SS b")."""
    t = r["t"]
    letters = sum(c.isalpha() for c in t)
    return letters < 2 or (len(t) > 0 and letters / len(t) < 0.5)


ARTIFACT_RULES: list[tuple[str, callable, str]] = [
    ("A7_sayfa_ustbilgisi", a7_sayfa_ustbilgisi,
     "çift boşluklu iki-maddebaşlı başlık + gövdede em-dash (running head)"),
    ("A1_yazar_imza", a1_yazar_imza,
     ">=2 tek-harf initial (B/L hariç) + dejenere gövde (<=14 krk)"),
    ("A2_yayinci_kunye", a2_yayinci_kunye,
     "Brill/Luzac/Oriental Publisher imprint-reklam satırı"),
    ("A3_editoryal_aparat", a3_editoryal_aparat,
     "Additions/Corrections/Errata/Plates cilt aparatı"),
    ("A8_atif_parcasi", a8_atif_parcasi,
     "başlıkta çift boşluk + dejenere gövde (em-dash yok → atıf parçası)"),
    ("A5_kaynakca_kisaltmasi", a5_kaynakca_kisaltmasi,
     "sesli-harfsiz tümü-büyük başlık + gövdede atıf kalıbı"),
    ("A4_roma_rakami_baslik", a4_roma_rakami_baslik,
     "başlık saf Roma rakamı"),
    ("A6_alfabetik_olmayan_hurda", a6_alfabetik_olmayan_hurda,
     "harf oranı <%50 veya <2 harf — saf OCR hurdası"),
]


# ---------------------------------------------------------------------------
# BELİRSİZ kuralları — otomatik atılmaz, insana gider, eşleştirmeye girmez
# ---------------------------------------------------------------------------

def b1_devam_sayfasi_parcasi(r: dict) -> bool:
    """Devam-sayfası parçası: gövdenin ilk satırı BİREBİR başlık, kalanı küçük
    harf/rakamla başlıyor ('ADAMAUA \\n\\n same year.'). Gerçek maddenin sonraki
    sayfasından kopmuş bir parça olabilir — başlık doğru ama kayıt madde
    değil. Kesin diyemeyiz: bazı maddelerde gövde meşru olarak paragraf
    atlıyor. BELİRSİZ."""
    ds = r.get("ds") or ""
    if "\n\n" not in ds:
        return False
    head, rest = ds.split("\n\n", 1)
    if not nrm(head) or nrm(head) != nrm(r["t"]):
        return False
    rest = rest.lstrip()
    return bool(rest) and (rest[0].islower() or rest[0].isdigit())


def b3_govdesiz_madde(r: dict) -> bool:
    """Gövdesiz madde: gövde yalnızca başlığın yankısı ('AARON.'). Çapraz
    gönderme maddesi (meşru) ile OCR'ın gövdesini kaybettiği madde (artifact)
    aynı görünür → ayırt edemeyiz. BELİRSİZ."""
    return nrm(r.get("ds")) == nrm(r["t"]) and bool(nrm(r["t"]))


BELIRSIZ_RULES: list[tuple[str, callable, str]] = [
    ("B1_devam_sayfasi_parcasi", b1_devam_sayfasi_parcasi,
     "gövde ilk satırı = başlık, kalan küçük harf/rakamla başlıyor"),
    ("B3_govdesiz_madde", b3_govdesiz_madde,
     "gövde yalnızca başlığın yankısı (çapraz-gönderme mi kayıp gövde mi?)"),
]


# ---------------------------------------------------------------------------
# triyaj
# ---------------------------------------------------------------------------

def triage(records: list[dict]) -> dict:
    saglam: list[int] = []
    artifact: list[dict] = []
    belirsiz: list[dict] = []
    rule_hits: dict[str, list[dict]] = defaultdict(list)
    # B2: aynı (tn, ds, at) üçlüsünün 2. ve sonraki kopyaları — birebir tekrar
    seen: set[tuple] = set()

    for r in records:
        fired = None
        for rid, fn, _ in ARTIFACT_RULES:
            if fn(r):
                fired = rid
                break
        if fired:
            row = {"id": r["id"], "kural": fired, "baslik": r["t"]}
            artifact.append(row)
            rule_hits[fired].append(row)
            continue

        key = (r.get("tn"), r.get("ds"), r.get("at"))
        if key in seen:
            row = {"id": r["id"], "kural": "B2_birebir_tekrar", "baslik": r["t"]}
            belirsiz.append(row)
            rule_hits["B2_birebir_tekrar"].append(row)
            continue
        seen.add(key)

        fired_b = None
        for rid, fn, _ in BELIRSIZ_RULES:
            if fn(r):
                fired_b = rid
                break
        if fired_b:
            row = {"id": r["id"], "kural": fired_b, "baslik": r["t"]}
            belirsiz.append(row)
            rule_hits[fired_b].append(row)
            continue

        saglam.append(r["id"])

    descs = {rid: d for rid, _, d in ARTIFACT_RULES}
    descs.update({rid: d for rid, _, d in BELIRSIZ_RULES})
    descs["B2_birebir_tekrar"] = ("aynı (tn, ds, at) üçlüsünün 2.+ kopyası — "
                                  "aynı maddenin mükerrer çıkarımı mı, iki ayrı "
                                  "madde mi belli değil")
    kurallar = {
        rid: {
            "kova": "artifact" if rid.startswith("A") else "belirsiz",
            "aciklama": descs[rid],
            "yakalanan": len(rows),
            "ornekler": [x["baslik"] for x in rows[:3]],
        }
        for rid, rows in sorted(rule_hits.items())
    }
    return {"saglam": saglam, "artifact": artifact, "belirsiz": belirsiz,
            "kurallar": kurallar}


# ---------------------------------------------------------------------------
# eşleştirme (sağlam alt küme)
# ---------------------------------------------------------------------------

_OCR_EDGE = re.compile(r"^[^A-Za-z0-9']+|[^A-Za-z0-9']+$")


def clean_title(t: str) -> str:
    """H20-1 ön-adımı. EI-1'de 'kapsayıcı ek' virgüllü ülke eki DEĞİL (bu
    kaynakta virgüllü başlık yok, ölçüldü: 0/7568); karşılığı iki-maddebaşlı
    sayfa üstbilgisidir ve o kayıtlar A7 ile zaten artifact'e düşer. Burada
    kalan iş OCR kenar gürültüsünü kesmek: baştaki/sondaki noktalama ve
    ayraçlar ('■ALi' → 'ALi', "al-'ADIL," → "al-'ADIL"), çoklu boşluk
    daraltma. Harf içeriğine DOKUNULMAZ — OCR düzeltmesi yapılmaz."""
    t = _OCR_EDGE.sub("", t or "")
    return re.sub(r"\s+", " ", t).strip()


def _labels(r: dict) -> dict:
    t = clean_title(r["t"])
    if not t:
        return {}
    pref = {"en": tr_title(t) if t.isupper() else t}   # H31: .title() → tr_title
    alts = [x for x in (clean_title(r.get("tn") or ""),)
            if x and x.lower() != t.lower()]
    labels: dict = {"prefLabel": pref}
    if alts:
        labels["altLabel"] = {"en": alts}
    return labels


def _temporal(r: dict) -> dict:
    """Yalnız ÖLÜM yılı (dc) resolver'a verilir — bc doğumdur, ölüm-bracket'lı
    store'a karşı yanlış sinyaldir (H10 final-review dersi, ei1 canonicalize.py
    ile aynı kural)."""
    dc = r.get("dc")
    try:
        return {"start_ce": int(dc)} if dc is not None else {}
    except (TypeError, ValueError):
        return {}


def resolve_saglam(records_by_id: dict, saglam_ids: list[int], reset: bool) -> dict:
    from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402

    resolver = EntityResolver(REPO_ROOT)
    if reset:
        cc = resolver._cache_connect()
        n = cc.execute("DELETE FROM decision_cache WHERE adapter_id = ?",
                       (ADAPTER,)).rowcount
        cc.commit()
        if QUEUE.exists():
            QUEUE.unlink()
        print(f"[h21:ei1] reset: {n} cache satırı + kuyruk dosyası silindi")
    conn = resolver._connect()
    if conn is None:
        raise RuntimeError("lookup.sqlite yok — önce build_lookup koş.")

    mapped = {row[0].split(":", 1)[1] for row in conn.execute(
        "SELECT source_id FROM source_curie WHERE source_id LIKE 'ei1:%'")}
    self_layer_pids = {row[0] for row in conn.execute(
        "SELECT pid FROM source_curie WHERE source_id LIKE 'ei1:%'")}

    augments: dict[str, dict[str, list]] = {"person": {}, "place": {}}
    crosswalk: dict[str, str] = {}
    self_layer: dict[str, dict] = {}
    unmatched: dict[str, dict] = {}
    stats = Counter()
    magnet: Counter = Counter()

    for rid_int in saglam_ids:
        r = records_by_id[rid_int]
        ns = AT_TO_NS.get(r.get("at") or "")
        if ns is None:
            stats["kapsam_disi_tip"] += 1
            continue
        curie = f"ei1:{r['id']}"
        if str(r["id"]) in mapped:
            stats["zaten_curieli"] += 1
            continue
        labels = _labels(r)
        if not labels:
            unmatched[curie] = {"name": None, "reason": "temizlik sonrası boş başlık",
                                "ns": ns, "confidence": 0.0}
            stats["labelsiz"] += 1
            continue
        d = resolver.resolve(
            entity_type=ns, adapter_id=ADAPTER, extracted_record_id=curie,
            source_curies=[curie], labels=labels,
            temporal=_temporal(r) if ns == "person" else {})
        name = labels["prefLabel"]["en"]
        stats[f"{ns}_toplam"] += 1
        if d.kind == "match":
            crosswalk[curie] = d.matched_pid
            magnet[d.matched_pid] += 1
            if d.matched_pid in self_layer_pids:
                self_layer[curie] = {"pid": d.matched_pid, "ns": ns, "name": name,
                                     "confidence": round(d.confidence, 4)}
                stats[f"{ns}_self_layer"] += 1
                continue
            augments[ns].setdefault(d.matched_pid, []).append({
                "ei1_id": r["id"], "name": name, "at": r.get("at"),
                "confidence": round(d.confidence, 4), "tier": d.tier,
                "vol": r.get("vol"), "page": r.get("is"),
            })
            stats[f"{ns}_match"] += 1
        elif d.kind == "review":
            stats[f"{ns}_review"] += 1
        else:
            unmatched[curie] = {"name": name, "ns": ns,
                                "confidence": round(d.confidence, 4)}
            stats[f"{ns}_unmatched"] += 1

    resolver.close()

    # H20-1 mıknatıs kontrolü İKİ yüzlü yapılır: auto-match tarafı (kaç kayıt
    # tek pid'e gitti) VE kuyruk tarafı (H20'de mıknatıs kuyrukta görünmüştü:
    # 34 girdinin 25'i tek pid'e gidiyordu). Kuyruğun ilk-aday dağılımı
    # dosyadan okunur.
    queue_magnet: Counter = Counter()
    n_queue = 0
    if QUEUE.exists():
        for line in QUEUE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            n_queue += 1
            cands = o.get("candidates") or []
            if cands:
                queue_magnet[cands[0]["pid"]] += 1

    return {"augments": augments, "crosswalk": crosswalk,
            "self_layer_matches": self_layer, "unmatched": unmatched,
            "stats": dict(stats), "magnet": magnet,
            "queue_magnet": queue_magnet, "n_queue": n_queue}


# ---------------------------------------------------------------------------

def audit_store(tri: dict) -> dict:
    """Geriye dönük kirlilik denetimi: mağazada ZATEN `ei1:<id>` curie'si olan
    kayıtların kaçı bu triyajda artifact/belirsiz kovasına düşüyor?

    H10'da EI-1'den 1.174 kişi curie'si üretilmişti; o koşuda gürültü triyajı
    YOKTU. Eğer bir mağaza kaydı bir yazar imzasından ya da Roma rakamından
    mint edildiyse, mağazada hayalet bir kişi vardır. Denetim SİLMEZ, yalnız
    listeler — kayıt silme/birleştirme insanın kararı (North Star)."""
    import sqlite3
    idx = REPO_ROOT / "data" / "_index" / "lookup.sqlite"
    if not idx.exists():
        return {"_not": "lookup.sqlite yok — denetim atlandı"}
    art = {x["id"]: x["kural"] for x in tri["artifact"]}
    bel = {x["id"]: x["kural"] for x in tri["belirsiz"]}
    saglam = set(tri["saglam"])
    conn = sqlite3.connect(idx)
    rows = [(int(s.split(":", 1)[1]), p) for s, p in conn.execute(
        "SELECT source_id, pid FROM source_curie WHERE source_id LIKE 'ei1:%'")]
    conn.close()

    def _label(pid: str) -> str | None:
        ns = pid.split(":", 1)[1].rsplit("-", 1)[0]
        p = REPO_ROOT / "data" / "canonical" / ns / f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json"
        if not p.exists():
            return None
        pref = (json.loads(p.read_text(encoding="utf-8"))
                .get("labels", {}).get("prefLabel") or {})
        return pref.get("en") or next(iter(pref.values()), None)

    art_hits = [{"pid": p, "ei1_id": i, "kural": art[i], "magaza_etiketi": _label(p)}
                for i, p in rows if i in art]
    bel_hits = [{"pid": p, "ei1_id": i, "kural": bel[i]} for i, p in rows if i in bel]
    return {
        "ei1_curieli_magaza_kaydi": len(rows),
        "artifact_kovasindan_mint_edilmis": len(art_hits),
        "belirsiz_kovasindan_mint_edilmis": len(bel_hits),
        "saglam_kovasindan_mint_edilmis": sum(1 for i, _ in rows if i in saglam),
        "kural_dagilimi_artifact": dict(Counter(h["kural"] for h in art_hits)),
        "kural_dagilimi_belirsiz": dict(Counter(h["kural"] for h in bel_hits)),
        "artifact_kayitlari": sorted(art_hits, key=lambda h: h["pid"]),
        "not": ("SİLME/BİRLEŞTİRME YAPILMADI. Bu liste insan kuyruğudur: "
                "artifact'ten mint edilmiş bir kayıt hayalet kişi adayıdır, "
                "ama v1 verisini tek taraflı bozmayız — kararı tarihçi verir."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true",
                    help="triyajdan sonra sağlam alt kümeyi Tier-2 ile eşleştir")
    ap.add_argument("--reset", action="store_true",
                    help="h21-ei1 karar cache'ini + kuyruk dosyasını sil")
    args = ap.parse_args()

    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in records}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    tri = triage(records)
    audit = audit_store(tri)
    at_dist = Counter(r.get("at") for r in records)
    at_saglam = Counter(by_id[i].get("at") for i in tri["saglam"])

    TRIAGE_OUT.write_text(json.dumps({
        "_meta": {
            "run_at": now,
            "kaynak": "data/sources/ei1/ei1_lite.json",
            "evren": len(records),
            "saglam": len(tri["saglam"]),
            "artifact": len(tri["artifact"]),
            "belirsiz": len(tri["belirsiz"]),
            "at_dagilimi_evren": dict(at_dist),
            "at_dagilimi_saglam": dict(at_saglam),
            "kurallar": tri["kurallar"],
            "magaza_kirlilik_denetimi": audit,
            "not": ("SİLME YOK: artifact yalnız İŞARETLENİR, kaynak dosya "
                    "dokunulmadan kalır. belirsiz = kural emin değil → insan "
                    "kuyruğu; ne artifact sayılır ne eşleştirmeye sokulur. "
                    "Kural sırası: A* (artifact) → B2 (birebir tekrar) → B* "
                    "(belirsiz); ilk yakalayan kural kazanır."),
        },
        "saglam": tri["saglam"],
        "artifact": tri["artifact"],
        "belirsiz": tri["belirsiz"],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"[h21:ei1] evren={len(records)} saglam={len(tri['saglam'])} "
          f"artifact={len(tri['artifact'])} belirsiz={len(tri['belirsiz'])}")
    for rid, info in tri["kurallar"].items():
        print(f"  {info['kova']:8} {rid:28} n={info['yakalanan']:5}  "
              f"ör: {info['ornekler']}")
    if "ei1_curieli_magaza_kaydi" in audit:
        print(f"[h21:ei1] mağaza kirlilik denetimi: "
              f"{audit['ei1_curieli_magaza_kaydi']} ei1-curie'li kayıttan "
              f"{audit['artifact_kovasindan_mint_edilmis']}'i ARTIFACT, "
              f"{audit['belirsiz_kovasindan_mint_edilmis']}'i BELİRSİZ kovasından "
              f"(silinmedi, insan kuyruğu)")
    print(f"[h21:ei1] → {TRIAGE_OUT.relative_to(REPO_ROOT)}")

    if not args.resolve:
        return 0

    res = resolve_saglam(by_id, tri["saglam"], args.reset)
    magnet = res.pop("magnet")
    qmagnet = res.pop("queue_magnet")
    n_queue = res.pop("n_queue")
    top = magnet.most_common(5)
    qtop = qmagnet.most_common(5)
    n_events = sum(len(v) for ns in res["augments"].values() for v in ns.values())
    n_pids = sum(len(ns) for ns in res["augments"].values())

    AUGMENT_OUT.write_text(json.dumps({
        "_meta": {
            "run_at": now, "adapter": ADAPTER,
            "girdi_saglam": len(tri["saglam"]),
            "istatistik": res["stats"],
            "auto_match_kayit": n_events, "auto_match_pid": n_pids,
            "self_layer_matches": len(res["self_layer_matches"]),
            "unmatched": len(res["unmatched"]),
            "miknatis_kontrolu": {
                "auto_match_tarafi": [{"pid": p, "cekilen_kayit": n} for p, n in top],
                "kuyruk_tarafi": [{"pid": p, "ilk_aday_oldugu_girdi": n}
                                  for p, n in qtop],
                "kuyruk_toplam": n_queue,
                "kuyruk_tekil_hedef_pid": len(qmagnet),
                "en_yogun_kuyruk_payi": (round(qtop[0][1] / n_queue, 4)
                                         if qtop and n_queue else 0.0),
            },
            "not": ("Tier-2 kalibrasyonu DEĞİŞTİRİLMEDİ (person auto=0.95, "
                    "place auto=0.90 — resolver_weights.yaml). MİNT YOK. "
                    "Eşik altı kararlar data/review_queue/h21-ei1.jsonl'de "
                    "insanda. crosswalk kanıt içindir, curie yazımı için "
                    "değil — provenance.derived_from ekleme kararı insana ait."),
        },
        **res,
    }, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"[h21:ei1] eşleştirme: auto-match={n_events} kayıt → {n_pids} pid | "
          f"self-layer={len(res['self_layer_matches'])} | "
          f"review={res['stats'].get('person_review', 0) + res['stats'].get('place_review', 0)} | "
          f"unmatched={len(res['unmatched'])}")
    print(f"[h21:ei1] mıknatıs — auto-match tarafı (en yoğun 5 pid): {top}")
    print(f"[h21:ei1] mıknatıs — kuyruk tarafı: {n_queue} girdi / "
          f"{len(qmagnet)} tekil hedef; en yoğun 5: {qtop}")
    print(f"[h21:ei1] → {AUGMENT_OUT.relative_to(REPO_ROOT)} + "
          f"data/review_queue/{ADAPTER}.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
