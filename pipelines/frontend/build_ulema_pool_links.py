#!/usr/bin/env python3
"""Havuz kaydının İLİŞKİ KENARLARINI ayrı bir yan dosyaya çıkarır (H44).

SORUN (Ali'nin sorusu): "havuzda artırınca ne elde ediyoruz?"
Ölçüldü: havuz 22.824 kişiye çıktı ama YAYINLANAN kayıt yalnız 7 alan taşıyor
(id, ad_tr, ad_ar, oh, om, k, m). Mağazadaki canonical kişi kayıtlarında duran
hoca/talebe/yer/eser bağlarının ve biyografik notun HİÇBİRİ arayüze çıkmıyordu.
Yani büyüme kayıt SAYISINI artırdı, kayıt DERİNLİĞİNİ ekrana taşımadı.

ÇÖZÜM: LITE endeksi (ulema_pool.json) BOZULMADAN ikinci bir dosya. Liste hâlâ
hafif kalır — 22.824 satırlık sanal liste aynı hızda açılır; bu dosya yalnız
SAĞ PANEL için, seçim anında tembel okunur.

İKİ ÇIKTI — boyut ölçülerek ayrıldı (ilişki 659 KB, not 3.8 MB):
  view-data/ulema_pool_links.json  { "<id>": {"h":[pid…],"o":[pid…],"y":[pid…]} }
      hoca / talebe / yer. Havuz modu açılınca yüklenir.
  view-data/ulema_pool_notes.json  { "<id>": {"y":doğum yeri,"k":[kategori],"o":ölüm ifadesi,"s":serbest not} }
      İlk kişi seçildiğinde bir kez yüklenir (panel açılışında değil).

NOT ALANI BİYOGRAFİ DEĞİLDİR — ÖLÇÜLDÜ: canonical `note` alanının %84'ü üretim
izidir ("El-Aʿlām cross-reference", "slug=", "URL:", "Chunk count:", "Tier-4
placeholder", "Promoted from iac:…"). Bunu kullanıcıya "biyografik not" diye
göstermek yanıltıcı olurdu. Bu yüzden not HAM GÖSTERİLMEZ: içine gömülü gerçek
bilgi AYIKLANIR (doğum yeri 3.848, uzmanlık kategorisi 5.606, kaynağın kendi
ölüm ifadesi 7.165) ve teknik iz atılır. Ayıklanamayan serbest metin (Bosworth
akrabalık notları gibi) `s` alanında kalır; teknik önekli olanlar düşürülür.

UYDURMA YOK: yalnız canonical kayıtta FİİLEN bulunan alanlar taşınır; boş olan
kişi dosyaya hiç girmez. Determinizm: id sıralı, timestamp yok.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERSON_DIR = REPO / "data" / "canonical" / "person"
POOL = REPO / "web" / "public" / "books" / "ulema_pool.json"
OUT = REPO / "web" / "public" / "view-data" / "ulema_pool_links.json"
OUT_NOTES = REPO / "web" / "public" / "view-data" / "ulema_pool_notes.json"
REDIR = REPO / "web" / "public" / "view-data" / "person_redirects.json"

NOT_MAX = 240        # panelde okunur uzunluk; tam metin mağazada kalır

# Notun içine gömülü GERÇEK bilgiyi ayıklayan desenler (ölçülerek seçildi).
import re as _re
_PAT = {
    "y": _re.compile(r"birth place:\s*([^|]+)"),
    "k": _re.compile(r"categories:\s*([^|]+)"),
    "o": _re.compile(r"death-date string:\s*([^|]+)"),
}
# Teknik iz: bu önekle başlayan serbest metin kullanıcıya GÖSTERİLMEZ.
_TEKNIK = _re.compile(r"^(El-A|DİA|DIA|Tier-\d|Promoted from|Chunk count|"
                      r"[A-Za-z-]+ cross-reference|.*slug=|.*URL:)", _re.I)


def ayikla(note: str) -> dict:
    """Ham nottan gösterilebilir alanları çıkar; teknik izi at."""
    out: dict = {}
    for key, pat in _PAT.items():
        m = pat.search(note)
        if m:
            v = m.group(1).strip(" .|")
            if key == "k":
                out[key] = [x.strip() for x in v.split(">") if x.strip()]
            else:
                out[key] = v[:120]
    # serbest metin: '||' ile ayrılmış parçalardan teknik olmayanlar
    # "<kaynak> relation note: …" gibi ETİKET ÖNEKLERİ atılır; okuyucuya
    # kaynağın iç terimi değil, cümlenin kendisi gösterilir.
    _ONEK = _re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşü'\- ]{0,28}note:\s*", _re.I)
    serbest = []
    for x in note.split("||"):
        x = x.strip()
        if not x or _TEKNIK.match(x):
            continue
        x = _ONEK.sub("", x)
        # "Bosworth death code: k. (murdered)" gibi kod satırları da iz sayılır
        if _re.match(r"^[A-Za-z ]+code:", x):
            continue
        if x:
            serbest.append(x)
    if serbest:
        out["s"] = " · ".join(serbest)[:NOT_MAX]
    return out


def _num(pid: str):
    """iac:person-00003412 → 3412 (havuz kimliği sayıdır: iac:person-%08d)."""
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def main() -> None:
    if not POOL.is_file():
        print("atlandı: ulema_pool.json yok (build_ulema_pool.py koşulmamış)")
        return
    havuz_ids = {r["id"] for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]}

    # H49 YAN ETKİSİ: birleştirmeden sonra isnâd uçlarının bir kısmı
    # yumuşak-silinmiş pid'e işaret ediyor ve panelde "(havuz dışı)" görünüyordu
    # (ölçüldü: 206 uç). Oysa o kişiler yönlendirmeyle bulunabilir. Uçlar
    # kazanan pid'e çevrilir — kenar KAYBOLMAZ, doğru kayda bağlanır.
    # (Zincir sırası önemli: build_person_clusters.py bu script'ten ÖNCE koşar.)
    redir = {}
    if REDIR.is_file():
        raw = json.loads(REDIR.read_text(encoding="utf-8"))["redirects"]
        redir = {f"iac:person-{int(k):08d}": f"iac:person-{int(v):08d}" for k, v in raw.items()}

    def yonlendir(pid: str) -> str:
        return redir.get(pid, pid)

    links: dict[str, dict] = {}
    notes: dict[str, str] = {}
    sayac = {"hoca": 0, "talebe": 0, "yer": 0, "not": 0, "yonlendirilen_uc": 0}
    for f in sorted(PERSON_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        num = _num(r.get("@id"))
        if num is None or num not in havuz_ids:
            continue           # havuzda görünmeyen kayıt panelde de görünmez
        e: dict = {}
        for src, dst, key in (("teachers", "h", "hoca"),
                              ("students", "o", "talebe"),
                              ("active_in_places", "y", "yer")):
            # Uçları yönlendir ve kendi kendine bağı (birleşme sonrası oluşabilir) düşür
            v = [yonlendir(x) for x in (r.get(src) or []) if x]
            v = [x for x in dict.fromkeys(v) if _num(x) != num]
            if v:
                e[dst] = v
                sayac[key] += len(v)
        note = r.get("note")
        if isinstance(note, dict):
            note = note.get("tr") or note.get("en")
        if isinstance(note, str) and note.strip():
            a = ayikla(note.strip())
            if a:
                notes[str(num)] = a
                sayac["not"] += 1
        if e:
            links[str(num)] = e

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "_doc": ("Havuz kişilerinin İLİŞKİ kenarları — UlemaPool sağ paneli için "
                 "tembel yüklenir. LITE endeksi (ulema_pool.json) değişmez. "
                 "Yalnız canonical kayıtta FİİLEN bulunan alanlar; uydurma yok. "
                 "Üretici: build_ulema_pool_links.py"),
        "counts": {"kisi": len(links), **sayac},
        "links": {k: links[k] for k in sorted(links, key=int)},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    OUT_NOTES.write_text(json.dumps(
        {"_doc": ("Havuz kişilerinin nottan AYIKLANMIŞ bilgisi (y=doğum yeri, "
                  "k=uzmanlık kategorileri, o=kaynağın ölüm ifadesi, s=serbest not). "
                  "Ham `note` alanının %84'ü üretim izidir ve GÖSTERİLMEZ. "
                  "Üretici: build_ulema_pool_links.py"),
         "counts": {"kisi": len(notes)},
         "notes": {k: notes[k] for k in sorted(notes, key=int)}},
        ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    kb = OUT.stat().st_size // 1024
    kbn = OUT_NOTES.stat().st_size // 1024
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {kb} KB")
    print(f"yazıldı: {OUT_NOTES.relative_to(REPO).as_posix()} | {kbn} KB")
    print(f"  bağı olan kişi : {len(links)} / {len(havuz_ids)} "
          f"(%{len(links)*100//max(len(havuz_ids),1)})")
    print(f"  hoca kenarı    : {sayac['hoca']}")
    print(f"  talebe kenarı  : {sayac['talebe']}")
    print(f"  yer bağı       : {sayac['yer']}")
    print(f"  biyografik not : {sayac['not']}")


if __name__ == "__main__":
    main()
