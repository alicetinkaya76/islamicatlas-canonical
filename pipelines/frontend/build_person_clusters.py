#!/usr/bin/env python3
"""Aynı kişinin dağılmış kayıtlarını KÜME olarak görünür kılar (H47).

SORUN (H44 denetimi): "22.824" bir kişi sayısı değil KAYIT sayısıdır. Aynı kişi
2-3 ayrı pid'de duruyor ve bunun bedeli sayı değil, ZENGİNLİK PARÇALANMASI:
biyografi bir pid'de, eserleri başka pid'de, ağ düğümü üçüncüsünde. Kullanıcı
hiçbir ekranda "bütün Gazzâlî"yi göremiyor, çünkü bütün Gazzâlî hiçbir kayıtta
yok.

BU SCRIPT NE YAPMAZ — ve neden:
    BİRLEŞTİRME YAPMAZ. Hiçbir pid silinmez, hiçbir kayıt ötekine katılmaz.
    Birleştirme geri alınması zor, veri-yıkıcı bir işlemdir ve iki farklı kişiyi
    tek kayda indirme riski taşır (ortaçağda aynı yıl ölen aynı adlı iki kişi
    olağandır). Merge kararı tarihçinindir — ADR-008 Tier-3.

BU SCRIPT NE YAPAR:
    Kanıtı katmanlayıp KÜME önerir; kümeler arayüzde "aynı kişi olabilir"
    olarak gösterilir. Kullanıcı her iki kaydı da görür, hangisinde ne olduğunu
    anlar. Veri bozulmadan parçalanma görünür hale gelir.

KANIT KATMANLARI (hepsi ölçülür, hiçbiri tahmin değildir):
    ad     — mevcut aday listesi (rapidfuzz ≥0.95, data/_state/…candidates)
    tarih  — ölüm yılı BİREBİR aynı | ±2 | farklı
    kaynak — kayıtların kaynak kümeleri AYRIK mı (tamamlayıcı mint deseni:
             Bosworth/450-tohum ayrı, el-Aʿlâm/DİA ayrı mint edilmiş)
    güven  — yalnız bu üçünden türetilir:
             kesin  = tarih birebir + kaynaklar ayrık
             olası  = tarih birebir (kaynak örtüşüyor) ya da ±2 + ayrık
             zayıf  = ±2 ve kaynak örtüşüyor
    Tarihi FARKLI olan çift küme YAPMAZ — aday listesinde kalır.

YARGI KATMANI (H47, ölçüldü): 120 kümelik örneklem iki bağımsız mercekle
(prosopografi + çürütme) yargılandı. Kalibrasyon:
    kesin (60) → 58 aynı kişi ·  0 ayrı ·  2 belirsiz   (%97 isabet, 0 yanlış)
    olası (30) → 16 aynı kişi ·  7 ayrı ·  7 belirsiz
    zayıf (30) →  3 aynı kişi · 15 ayrı · 12 belirsiz   (YARISI YANLIŞ)

Bunun iki sonucu var ve ikisi de uygulanır:
  1) "zayıf" katman ARAYÜZDE GÖSTERİLMEZ (`goster: false`). Yarısı yanlış olan
     bir uyarıyı göstermek, kullanıcıyı yanlış birleştirmeye teşvik eder.
     Kümeler dosyada kalır — aday listesi olarak değerlidir.
  2) Yargılanan kümelerin kararı kayda işlenir; "hayır" çıkanlar ÇIKARILIR
     (ölçüldü: 22 küme gerçekte AYRI kişilerdi — ör. "b. Artuk" (Artuklu) ile
     "el-Kutbî" (Ahlatşahlar) aynı yıl ölmüş iki farklı hanedan mensubu).

Çıktı: web/public/view-data/person_clusters.json
Determinizm: pid sıralı, timestamp yok.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CAND = REPO / "data" / "_state" / "person_dedup_candidates.json"
MERGED = REPO / "data" / "_state" / "h22_person_dup_merge.json"
JUDGE = REPO / "data" / "_state" / "person_cluster_judgments.json"
POOL = REPO / "web" / "public" / "books" / "ulema_pool.json"
OUT = REPO / "web" / "public" / "view-data" / "person_clusters.json"
REDIR = REPO / "web" / "public" / "view-data" / "person_redirects.json"
MERGE_LEDGER = REPO / "data" / "_state" / "h49_cluster_merge.json"


def _num(pid):
    try:
        return int(str(pid).rsplit("-", 1)[-1])
    except (ValueError, AttributeError):
        return None


def guven(a, b):
    """(güven, gerekçe) — YALNIZ ölçülen alanlardan; tahmin yok."""
    ta, tb = a.get("om"), b.get("om")
    ka, kb = set(a.get("k") or []), set(b.get("k") or [])
    ayrik = not (ka & kb)
    if ta is None or tb is None:
        return None, "ölüm yılı eksik"
    if ta == tb:
        return ("kesin", "ölüm yılı birebir + kaynaklar ayrık") if ayrik \
            else ("olasi", "ölüm yılı birebir, kaynaklar örtüşüyor")
    if abs(ta - tb) <= 2:
        return ("olasi", f"ölüm yılı ±{abs(ta - tb)} + kaynaklar ayrık") if ayrik \
            else ("zayif", f"ölüm yılı ±{abs(ta - tb)}, kaynaklar örtüşüyor")
    return None, f"ölüm yılı farklı ({ta} vs {tb})"


def main() -> None:
    if not (CAND.is_file() and POOL.is_file()):
        print("atlandı: aday listesi ya da havuz yok")
        return
    pool = {r["id"]: r for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]}

    # h22'de karara bağlanmış pid'ler yeniden önerilmez.
    kapali = set()
    if MERGED.is_file():
        for m in json.loads(MERGED.read_text(encoding="utf-8"))["merges"]:
            kapali.add(m["kazanan"])
            kapali.update(m["kaybedenler"])

    pairs = json.loads(CAND.read_text(encoding="utf-8"))["pairs"]

    # Yargılanmış kümeler: karar kayda işlenir, "hayır" çıkanlar ÇIKARILIR.
    yargi = {}
    if JUDGE.is_file():
        yargi = json.loads(JUDGE.read_text(encoding="utf-8"))["kararlar"]

    # Union-Find: A~B, B~C ise {A,B,C} tek küme.
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    kenar = []
    sayac = {"kesin": 0, "olasi": 0, "zayif": 0, "elendi": 0, "kapali": 0, "havuz_disi": 0}
    for p in pairs:
        if p["a"] in kapali or p["b"] in kapali:
            sayac["kapali"] += 1
            continue
        na, nb = _num(p["a"]), _num(p["b"])
        A, B = pool.get(na), pool.get(nb)
        if not A or not B:
            sayac["havuz_disi"] += 1
            continue
        g, neden = guven(A, B)
        if g is None:
            sayac["elendi"] += 1
            continue
        sayac[g] += 1
        kenar.append({"a": na, "b": nb, "guven": g, "neden": neden,
                      "ad_skor": round(p.get("score", 0), 3)})
        union(na, nb)

    # Kümeleri topla
    kume = {}
    for e in kenar:
        kok = find(e["a"])
        kume.setdefault(kok, {"uyeler": set(), "kenarlar": []})
        kume[kok]["uyeler"].update((e["a"], e["b"]))
        kume[kok]["kenarlar"].append(e)

    out = {}
    dagilim = {"kesin": 0, "olasi": 0, "zayif": 0}
    yargi_sayac = {"evet": 0, "hayir": 0, "belirsiz": 0}
    atilan = 0
    for kok, v in kume.items():
        uyeler = sorted(v["uyeler"])
        kid = "-".join(map(str, uyeler))
        karar = (yargi.get(kid) or {}).get("karar")
        if karar:
            yargi_sayac[karar] += 1
        if karar == "hayir":
            atilan += 1        # yargı AYRI kişi dedi → küme gösterilmez
            continue
        # Küme güveni = en ZAYIF kenar (zincirin en zayıf halkası kadar güçlü)
        sira = {"kesin": 0, "olasi": 1, "zayif": 2}
        kg = max((e["guven"] for e in v["kenarlar"]), key=lambda g: sira[g])
        dagilim[kg] += 1
        rec = {
            "uyeler": uyeler,
            "guven": kg,
            "gerekce": sorted({e["neden"] for e in v["kenarlar"]}),
            "adlar": [pool[u].get("ad_tr", "") for u in uyeler if u in pool],
            "kaynaklar": sorted({c for u in uyeler for c in (pool.get(u, {}).get("k") or [])}),
            # zayıf katman arayüzde GÖSTERİLMEZ (örneklemde yarısı yanlıştı)
            "goster": kg != "zayif",
            "yargi": karar,          # None = yargılanmadı (ölçüt tabanlı)
        }
        for u in uyeler:
            out[str(u)] = rec

    doc = {
        "_doc": ("Aynı kişi OLABİLECEK kayıt kümeleri. BİRLEŞTİRME DEĞİLDİR — "
                 "hiçbir pid silinmez; arayüz 'aynı kişi olabilir' diye gösterir. "
                 "Merge kararı tarihçinindir (ADR-008 Tier-3). "
                 "Üretici: build_person_clusters.py"),
        "counts": {"kume": len(kume), "kume_icindeki_kayit": len(out),
                   "kenar": sayac, "kume_guveni": dagilim,
                   "yargilanan": yargi_sayac, "yargi_ile_atilan": atilan,
                   "gosterilen_kume": dagilim["kesin"] + dagilim["olasi"] - atilan},
        "clusters": {k: out[k] for k in sorted(out, key=int)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")

    # ── ATIF İSTİKRARI (H49) ────────────────────────────────────────────────
    # Birleştirmede kaybeden pid YAŞAMAYA DEVAM EDER, ama havuz dosyasında
    # görünmez. Dolayısıyla eski bir bağ (ör. kitap manifestindeki author.pid,
    # ya da dışarıda paylaşılmış bir #scholars?pid= linki) BOŞ EKRANA düşerdi.
    # ÖLÇÜLDÜ: birleştirmeden hemen sonra 17 kitabın 5'inin müellif bağı koptu.
    # Yönlendirme haritası bunu kapatır: tüketici eski pid'i kazanana çevirir.
    # KAYNAK: canonical kayıtların kendisi (ledger DEĞİL). Ledger denetim/geri
    # alma içindir; yönlendirmenin doğruluğu ondan bağımsız olmalı. Ölçüldü:
    # ikinci tur ledger'ı ezince ilk turun kayıtları kaybolmuştu — yönlendirme
    # ledger'a bağlı kalsaydı 544 bağ sessizce kopardı.
    redir = {}
    for f in sorted((REPO / "data" / "canonical" / "person").glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        prov = r.get("provenance") or {}
        hedef = prov.get("deprecated_in_favor_of")
        if prov.get("deprecated") and hedef:
            redir[str(_num(r.get("@id")))] = _num(hedef)
    REDIR.write_text(json.dumps({
        "_doc": ("Yumuşak-silinen pid → kazanan pid. Eski bağlar (kitap müellifi, "
                 "paylaşılmış derin linkler) kırılmasın diye; kaybeden pid canonical'da "
                 "YAŞIYOR, yalnız havuzda görünmüyor. Üretici: build_person_clusters.py"),
        "counts": {"yonlendirme": len(redir)},
        "redirects": {k: redir[k] for k in sorted(redir, key=int)},
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"yazıldı: {REDIR.relative_to(REPO).as_posix()} | yönlendirme: {len(redir)}")
    print(f"yazıldı: {OUT.relative_to(REPO).as_posix()} | {OUT.stat().st_size // 1024} KB")
    print(f"  küme            : {len(kume)}  ({dagilim})")
    print(f"  küme içi kayıt  : {len(out)}")
    print(f"  kenar           : {sayac}")
    print(f"  yargilanan      : {yargi_sayac} | yargı ile atılan: {atilan}")
    print(f"  ARAYUZDE gosterilen: {dagilim['kesin'] + dagilim['olasi'] - atilan} "
          f"(zayif {dagilim['zayif']} gizli)")
    tekil = len(pool) - (len(out) - len(kume))
    print(f"  havuz {len(pool)} kayıt → kümeler birleşseydi TEKİL tavan ≈ {tekil}")


if __name__ == "__main__":
    main()
