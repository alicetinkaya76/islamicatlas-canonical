#!/usr/bin/env python3
"""Müellif → eser köprüsü (H55).

SORUN (eser ekseni denetimi):
  Merkezî defterde 9.404 eser var; sitede okunabilen 17. Kalan 9.387 eserin
  HİÇBİR sayfası yok. Ulema Havuzu'nda 2.246 kişi "OpenITI külliyatı" rozeti
  taşıyor ama rozetin hedefi `() => null` — yani havuzu büyütmek bu eksende
  kullanıcıya hiçbir şey vermiyordu. Bu dosya rozete gerçek bir içerik verir:
  kişinin merkezî defterdeki ESER LİSTESİ.

  İkinci ve sessiz kusur: H49/H50 kimlik birleştirmesi kişi kayıtlarını
  yumuşak-sildi, ama eser kayıtlarının `authors` alanına HİÇ uğramadı.
  Ölçüldü: 9.385 eser→müellif bağının 1.177'si yumuşak-silinmiş pid'e gidiyor.
  Bu bağlar havuzda karşılık bulamaz; eserler "müellifsiz" görünürdü.
  Çözüm izlenen desen: canonical'a DOKUNMA, yayın katmanında yönlendir
  (H49'da isnâd uçlarında aynısı yapıldı — build_ulema_pool_links.py).

ÜÇ TUZAK — ölçülerek bulundu, koda gerekçesiyle gömüldü:

  1) `composition_temporal` TELİF TARİHİ DEĞİL. 9.385 kaydın 9.158'inde
     `start_ah`, OpenITI URI'sindeki MÜELLİF ÖLÜM YILI ile birebir aynı ve
     9.159'u `approximation: "before"` taşıyor. Yani alan "müellif ölmeden
     önce yazıldı" sınırıdır. Çıplak yıl basmak, olmayan bir kesinlik
     üretirdi. Bu yüzden yıl `yk` (approximation) ile BİRLİKTE taşınır ve
     arayüz "212 öncesi" diye yazar.

  2) `note` alanı %100 üretim izi ("Promoted from OpenITI corpus_works…").
     Kişi tarafında aynı desen H44'te ölçülmüştü (%84). Ham note TAŞINMAZ.

  3) `genre` alanı 9.404 kayıtta BOŞ; konu bilgisi `subjects`'te (39 tekil
     değer). Şemadaki ölü alan yerine dolu alan kullanılır.

NE TAŞIMAZ: ham note, uydurulmuş başlık, eseri olmayan kişiye boş liste.
Determinizm: pid sıralı, timestamp yok.

Çıktı: web/public/view-data/author_works.json
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK_DIR = REPO / "data" / "canonical" / "work"
PERSON_DIR = REPO / "data" / "canonical" / "person"
SHELF = REPO / "web" / "public" / "reading" / "core_shelf.json"
OUT = REPO / "web" / "public" / "view-data" / "author_works.json"


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


class KisiDefteri:
    """Kişi kaydının provenance'ını bir kez okur, yönlendirme zincirini çözer."""

    def __init__(self, kok: Path):
        self.kok = kok
        self._cache = {}

    def prov(self, num: int) -> dict:
        if num not in self._cache:
            p = self.kok / f"iac_person_{num:08d}.json"
            try:
                self._cache[num] = (json.loads(p.read_text(encoding="utf-8"))
                                    .get("provenance") or {})
            except (OSError, json.JSONDecodeError):
                self._cache[num] = {}
        return self._cache[num]

    def cozumle(self, num: int):
        """Yumuşak-silinmiş pid → kazanan pid. Döngüye karşı korumalı.

        Zincir olabilir: A→B birleşti, sonra B→C birleşti. Tek adım atmak
        kullanıcıyı yine görünmeyen bir kayda bırakırdı.
        """
        gorulen = set()
        while True:
            pr = self.prov(num)
            if not pr:
                return None            # kayıt yok → dürüstçe bağ verilmez
            if not pr.get("deprecated"):
                return num
            hedef = _num(pr.get("deprecated_in_favor_of"))
            if hedef is None or hedef in gorulen:
                return None            # hedefsiz ya da döngü → bağ verilmez
            gorulen.add(num)
            num = hedef


def _baslik(labels: dict):
    pref = (labels or {}).get("prefLabel") or {}
    orig = (labels or {}).get("originalScript") or {}
    if isinstance(pref, str):
        return None, pref
    ar = orig.get("ar") or pref.get("ar")
    lat = pref.get("tr") or pref.get("en")
    return ar, lat


def main() -> None:
    if not WORK_DIR.is_dir():
        print("atlandı: canonical/work yok")
        return

    # Sitede okunabilen eserler (17). reading/ gitignore'da: temiz kopyada
    # dosya YOKTUR — o zaman hiçbir esere "okunabilir" denmez, sessizce.
    okunabilir = set()
    if SHELF.is_file():
        try:
            d = json.loads(SHELF.read_text(encoding="utf-8"))
            for b in (d.get("books") or []):
                n = _num(b.get("pid"))
                if n is not None:
                    okunabilir.add(n)
        except (OSError, json.JSONDecodeError):
            pass

    kisiler = KisiDefteri(PERSON_DIR)
    eserler, yazar_map = {}, {}
    s = {
        "eser": 0, "deprecated_eser": 0, "yazarsiz": 0,
        "bag": 0, "yonlendirilen_bag": 0, "cozulemeyen_bag": 0,
        "arapca_baslik": 0, "yalniz_latin_baslik": 0, "okunabilir": 0,
    }

    for f in sorted(WORK_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        s["eser"] += 1
        if (r.get("provenance") or {}).get("deprecated"):
            s["deprecated_eser"] += 1      # yayında görünmeyen esere kart açılmaz
            continue
        wn = _num(r.get("@id"))
        if wn is None:
            continue

        ar, lat = _baslik(r.get("labels"))
        if ar:
            s["arapca_baslik"] += 1
        elif lat:
            s["yalniz_latin_baslik"] += 1

        kayit = {}
        if ar:
            kayit["a"] = ar[:160]
        if lat:
            kayit["t"] = lat[:160]
        subj = r.get("subjects") or []
        if subj:
            kayit["k"] = [str(x) for x in subj][:4]
        ct = r.get("composition_temporal") or {}
        if ct.get("start_ah") is not None:
            kayit["y"] = ct["start_ah"]
            # TUZAK 1: yıl tek başına yanıltıcı — sınır işareti hep yanında gider.
            if ct.get("approximation"):
                kayit["yk"] = ct["approximation"]
        if r.get("openiti_uri"):
            kayit["u"] = r["openiti_uri"]
        if r.get("original_language") and r["original_language"] != "ar":
            kayit["d"] = r["original_language"]   # varsayılan Arapça; sapma yazılır
        if wn in okunabilir:
            kayit["r"] = 1
            s["okunabilir"] += 1
        eserler[str(wn)] = kayit

        authors = r.get("authors") or []
        if not authors:
            s["yazarsiz"] += 1
            continue
        for x in authors:
            pid = x.get("person") if isinstance(x, dict) else x
            pn = _num(pid)
            if pn is None:
                continue
            s["bag"] += 1
            hedef = kisiler.cozumle(pn)
            if hedef is None:
                s["cozulemeyen_bag"] += 1
                continue
            if hedef != pn:
                s["yonlendirilen_bag"] += 1
            yazar_map.setdefault(str(hedef), []).append(wn)

    # Determinizm: her müellifin listesi eser pid'ine göre sıralı.
    yazar_map = {k: sorted(set(v)) for k, v in yazar_map.items()}

    doc = {
        "_doc": (
            "Müellif → eser köprüsü. Merkezî defterdeki 9.404 eserin kişiye bağlı "
            "listesi; Ulema Havuzu'ndaki 'OpenITI külliyatı' rozetine içerik verir. "
            "`r:1` = sitede OKUNABİLİR (yalnız çekirdek raf); geri kalanı kayıtlıdır "
            "ama metni sitede yok — kart bunu açıkça söyler. `y` alanı TELİF TARİHİ "
            "DEĞİLDİR: kayıtların %97'sinde müellifin ölüm yılıdır ve `yk:'before'` "
            "ile 'o yıldan önce yazıldı' sınırını gösterir; çıplak yıl basılmaz. "
            "Yumuşak-silinmiş müellif pid'leri canonical'daki "
            "`deprecated_in_favor_of` zinciriyle kazanana çevrilir (canonical'a "
            "DOKUNULMAZ). Ham `note` taşınmaz (%100 üretim izi). "
            "Üretici: build_author_works.py"
        ),
        "counts": {**s, "yazar": len(yazar_map), "eser_kart": len(eserler)},
        "eserler": {k: eserler[k] for k in sorted(eserler, key=int)},
        "yazar": {k: yazar_map[k] for k in sorted(yazar_map, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  eser {s['eser']} → kart {len(eserler)} (deprecated atlandı {s['deprecated_eser']})")
    print(f"  müellif {len(yazar_map)} · bağ {s['bag']}")
    print(f"  YÖNLENDİRİLEN bağ (yumuşak-silinmiş müellif): {s['yonlendirilen_bag']}")
    print(f"  çözülemeyen bağ (dürüstçe bağsız): {s['cozulemeyen_bag']}")
    print(f"  başlık: Arapça {s['arapca_baslik']} · yalnız Latin {s['yalniz_latin_baslik']}")
    print(f"  sitede okunabilir işaretlenen: {s['okunabilir']}")


if __name__ == "__main__":
    main()
