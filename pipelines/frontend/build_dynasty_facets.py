#!/usr/bin/env python3
"""Hanedan yayın katmanı — canonical'ın v1'e EKLEDİĞİ bağlar (H57).

SORUN (H56 denetimi, ölçüldü): canonical `dynasty` namespace'inin HİÇBİR öz
alanı arayüze çıkmıyor. `grep web/src` → bosworth_id 0 · dynasty_subtype 0 ·
had_capital 0 · had_ruler 0 · patron_dynasty 0 isabet. 186 kayıt, 828 hükümdar
ucu, 99 başkent bağı, 85 ardıllık kenarı ve 457 kurum-himaye bağı yalnızca
diskte duruyordu.

NE YAYINLANIR — KURAL: **v1'de OLMAYAN ya da v1'de TIKLANAMAYAN bilgi.**
H54 dersi: ekrana yeni bilgi koyarken v1'de zaten olanı TEKRARLAMA.

  ARDILLIK (öncül/ardıl) — v1'de HİÇ YOK. v1'in `ctx_b`/`ctx_a` alanları
      serbest ANLATI metnidir, bağ değildir. Canonical 48 öncül + 37 ardıl
      kenarı taşıyor ve bunlar gezilebilir: Râşidûn → Emevî → Abbâsî.
      Bu, canonical'ın bu eksende v1'e kattığı ASIL şeydir.

  BAŞKENT — v1'de `cap` var (181/186) ama SERBEST METİN ("Kahire (Mısır);
      Şam (Suriye); Halep…"). Canonical'ın `had_capital`'ı bir PLACE
      kaydına işaret eder; yani adı tekrarlamak için değil, YERE GİDEBİLMEK
      için yayınlanır. Popup adı v1'den basmaya devam eder.

  HİMAYE — 457 kurum `patron_dynasty` ile bir hanedana bağlı. v1'de bu bağ
      hiç yok. Sayı yayınlanır; kurumların kendisine bağ verilmez, çünkü
      kurum görünümlerinde canonical pid mint edilmemiş (H56 üçüncü dalga:
      join anahtarı yok, hedefsiz bağ üretilmez).

NE YAYINLANMAZ — ve neden:

  `dynasty_subtype` (79 kayıt). ÖLÇÜLDÜ: değer kaynağın kendi ayrımından
      KABA. `sultanate` etiketli 35 kaydın yalnız 12'si v1'de "Sultanlık";
      12'si HANLIK, 7'si ŞAHLIK. Bir hanlık sultanlık değildir. v1'in `gov`
      alanı hem daha ince hem zaten ekranda. Bilinerek yanlış bir etiketi
      yaymaktansa hiç yaymamak doğrudur.

  `had_ruler` (828 uç). v1 zaten 830 hükümdarı listeliyor ve popup onları
      basıyor; tekrar olurdu.

Çıktı: web/public/view-data/dynasty_facets.json
Determinizm: v1 id sıralı, timestamp yok.
"""

import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DYN_DIR = REPO / "data" / "canonical" / "dynasty"
PLACE_DIR = REPO / "data" / "canonical" / "place"
INST_DIR = REPO / "data" / "canonical" / "institution"
DB = REPO / "web" / "src" / "data" / "db.json"
OUT = REPO / "web" / "public" / "view-data" / "dynasty_facets.json"

V1_ID_RE = re.compile(r"bosworth-nid:(\d+)")
# had_capital girdisi {place, note} nesnesidir ve note ÇÖZÜM DURUMUNU taşır.
STATUS_RE = re.compile(r"status=([\w-]+)")
ROL_RE = re.compile(r"'[^']*',\s*([\w ]+?)\s+capital")
# Çözücünün BAŞLADIĞI ad. Bunu taşımak, "otomatik çözüm" iddiasını
# denetlenebilir kılar: kullanıcı 'Şam' → 'Sâm' sapmasını KENDİ görebilir.
KAYNAK_AD_RE = re.compile(r"capital_name field \('([^']+)'")


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def place_label(pid: str):
    """Yer adı — kayıt yoksa ya da EMEKLİYSE None (hedefsiz bağ verilmez)."""
    n = _num(pid)
    if n is None:
        return None
    f = PLACE_DIR / f"iac_place_{n:08d}.json"
    if not f.is_file():
        return None
    try:
        r = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (r.get("provenance") or {}).get("deprecated"):
        return None
    pref = (r.get("labels") or {}).get("prefLabel") or {}
    return {"pid": pid, "tr": pref.get("tr") or "", "ar": pref.get("ar") or ""}


def main() -> None:
    if not (DYN_DIR.is_dir() and DB.is_file()):
        print("atlandı: canonical/dynasty ya da db.json yok")
        return

    v1_ids = {d.get("id") for d in json.loads(DB.read_text(encoding="utf-8")).get("dynasties", [])}

    # canonical dynasty pid → v1 id (curie üzerinden; ad eşleştirme YOK)
    kayit, pid2v1 = {}, {}
    for f in sorted(DYN_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        m = V1_ID_RE.search(json.dumps(r, ensure_ascii=False))
        if not m:
            continue
        vid = int(m.group(1))
        kayit[vid] = r
        pid2v1[r.get("@id")] = vid

    # kurum → hanedan himaye sayısı
    himaye = Counter()
    if INST_DIR.is_dir():
        for f in INST_DIR.glob("*.json"):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if (r.get("provenance") or {}).get("deprecated"):
                continue
            pd = r.get("patron_dynasty")
            for x in (pd if isinstance(pd, list) else [pd] if pd else []):
                himaye[x] += 1

    out, s = {}, Counter()
    s["hanedan"] = len(kayit)
    for vid in sorted(kayit):
        r = kayit[vid]
        fac = {"pid": r.get("@id")}

        for alan, kisa in (("predecessor", "onc"), ("successor", "ard")):
            hedefler = r.get(alan) or []
            if isinstance(hedefler, str):
                hedefler = [hedefler]
            cozulen = []
            for h in hedefler:
                hv = pid2v1.get(h)
                # v1'de karşılığı YOKSA bağ verilmez: #dynasty/<id> açılmaz.
                if hv is None or hv not in v1_ids:
                    s[f"{kisa}_cozulemedi"] += 1
                    continue
                cozulen.append(hv)
            if cozulen:
                fac[kisa] = cozulen
                s[kisa] += len(cozulen)

        # had_capital: [{place, note}] — note çözüm DURUMUNU taşıyor.
        # ÖLÇÜLDÜ: 129 girdinin 61'i `ambiguous-picked`, yani birden çok aday
        # arasından İNSAN ONAYI OLMADAN seçilmiş. Bunu düz bir bağ gibi
        # yayınlamak, bu oturum boyunca onardığım "sessiz kesinlik" kalıbının
        # ta kendisi olurdu. Durum bağla BİRLİKTE taşınır; arayüz söyler.
        bkt = r.get("had_capital") or []
        if isinstance(bkt, (str, dict)):
            bkt = [bkt]
        etiketli = []
        for x in bkt:
            pid = x.get("place") if isinstance(x, dict) else x
            lab = place_label(pid) if pid else None
            if not lab:
                continue
            nt = (x.get("note") or "") if isinstance(x, dict) else ""
            m = STATUS_RE.search(nt)
            if m and m.group(1) != "unique":
                lab["belirsiz"] = m.group(1)      # ambiguous-picked | narrowed
                s["baskent_belirsiz"] += 1
            mr = ROL_RE.search(nt)
            if mr:
                lab["rol"] = mr.group(1).strip()  # primary | successor
            # Kaynak adı çözülen addan FARKLIYSA taşınır. Doğrulanmış vaka:
            # Emevîler'in başkenti kaynakta 'Şam', çözüm 'Sâm' (سام) —
            # Gûta'da AYRI bir yerleşim, Dımaşk DEĞİL; üstelik status=unique.
            # Bu sapmayı genel bir kuralla YAKALAYAMIYORUM (TR katlamasında
            # 'Şam' ve 'Sâm' aynı dizeye iniyor), o yüzden yargılamak yerine
            # İKİSİNİ DE gösteriyorum; hükmü okuyan verir.
            mk = KAYNAK_AD_RE.search(nt)
            if mk and mk.group(1).strip() != (lab.get("tr") or "").strip():
                lab["kn"] = mk.group(1).strip()
                s["baskent_ad_sapmasi"] += 1
            etiketli.append(lab)
        if etiketli:
            fac["bkt"] = etiketli
            s["baskent"] += len(etiketli)
        s["baskent_cozulemedi"] += len(bkt) - len(etiketli)

        n = himaye.get(r.get("@id"), 0)
        if n:
            fac["kurum"] = n
            s["himaye_hanedan"] += 1

        if len(fac) > 1:
            out[str(vid)] = fac
            s["facet_olan"] += 1

    doc = {
        "_doc": (
            "Hanedan yayın katmanı: canonical'ın v1'e EKLEDİĞİ bağlar. "
            "`onc`/`ard` = öncül/ardıl hanedanın v1 id'si (v1'de bu bilgi HİÇ "
            "YOK; ctx_b/ctx_a serbest anlatıdır, bağ değildir). `bkt` = başkent "
            "PLACE kaydı — v1 adı zaten basıyor, bu bağ YERE GİTMEK içindir; "
            "emekli yere bağ VERİLMEZ. `kurum` = patron_dynasty ile bu hanedana "
            "bağlı kurum sayısı (kurumun kendisine bağ verilmez: canonical "
            "institution pid'i v1 görünümlerinde mint edilmemiş). "
            "`dynasty_subtype` BİLEREK yayınlanmaz — ölçüldü: 'sultanate' "
            "etiketli 35 kaydın 12'si v1'de HANLIK, 7'si ŞAHLIK; v1'in `gov` "
            "alanı daha ince ve zaten ekranda. "
            "Üretici: build_dynasty_facets.py"
        ),
        "counts": dict(s),
        "facets": {k: out[k] for k in sorted(out, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  hanedan {s['hanedan']} → facet'i olan {s['facet_olan']}")
    print(f"  ARDILLIK (v1'de HİÇ YOK): öncül {s['onc']} · ardıl {s['ard']} "
          f"(çözülemeyen {s['onc_cozulemedi'] + s['ard_cozulemedi']})")
    print(f"  BAŞKENT bağı (v1 adı basıyor, bu YERE GİDER): {s['baskent']} "
          f"(çözülemeyen {s['baskent_cozulemedi']})")
    print(f"    bunlardan İNSAN ONAYI OLMADAN aday arasından seçilmiş: "
          f"{s['baskent_belirsiz']} — arayüz bunu SÖYLER")
    print(f"    çözülen ad kaynaktaki addan FARKLI: {s['baskent_ad_sapmasi']} "
          f"— ikisi de gösterilir, hüküm verilmez")
    print(f"  HİMAYE: {sum(himaye.values())} kurum → {s['himaye_hanedan']} hanedan")
    print("  dynasty_subtype YAYINLANMADI (kaynaktan kaba: sultanate 35'in 12'si Hanlık)")


if __name__ == "__main__":
    main()
