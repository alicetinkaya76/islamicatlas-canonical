"""H51 guard — normalize TEK OTORİTE, ve uydurma koordinat sabiti YOK.

İki kural, ikisi de bu turda ölçülen kusurlardan doğdu:

1) ARAPÇA SINIFI HARF YEMEZ — ve kopya kalmaz.
   H44'te `bookkit/normalize.js` onarıldı ama 9 KOPYA taranmadı; kırık sınıf
   10 dosyada canlı kaldı. Ölçüldü: global aramada 12.935 Arapça adın %99,6'sı
   boşa düşüyordu; "Bu yeri kitaplarda oku" köprüsü (4.566 yer / 102.984
   anılma) kurulduğu H18'den beri TAMAMEN ÖLÜYDÜ (db.json'ın 80 şehrinden
   eşleşen: 0 → onarım sonrası 21).
   Bu test dosyaları KOD NOKTASI düzeyinde çözer — görsel karşılaştırma bidi
   yüzünden güvenilmez.

2) UYDURMA KOORDİNAT SABİTİ YASAK.
   `lat: x || 30, lon: y || 45` kalıbı koordinatsız kaydı sessizce tek bir
   noktaya çakıyordu (yalnız Yâkût kolunda 1.483 kayıt) ve kullanıcı bunu
   "bilinen konum" sanıyordu. Deponun en sert kuralının ihlaliydi.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "web" / "src"


def _dosyalar():
    return sorted(list(SRC.rglob("*.js")) + list(SRC.rglob("*.jsx")))


def _siniflar(metin: str):
    """`.replace(/[...]/g, '')` sınıflarını kod noktası aralıklarına çöz."""
    out = []
    for m in re.finditer(r"\.replace\(/\[([^\]]{2,60})\]/g,\s*''\)", metin):
        cls, cps, i = m.group(1), [], 0
        while i < len(cls):
            if cls[i:i + 2] == "\\u":
                cps.append(int(cls[i + 2:i + 6], 16)); i += 6
            else:
                cps.append(ord(cls[i])); i += 1
        araliklar, j = [], 0
        while j < len(cps):
            if j + 2 < len(cps) and cps[j + 1] == 0x2D:
                araliklar.append((cps[j], cps[j + 2])); j += 3
            else:
                j += 1
        out.append((m.group(1), araliklar))
    return out


def test_hicbir_dosya_arap_harfi_yemiyor():
    """Silme aralığı U+0620–U+064A (Arap harf bloğu) ile kesişmemeli."""
    ihlal = []
    for f in _dosyalar():
        for ham, araliklar in _siniflar(f.read_text(encoding="utf-8")):
            for lo, hi in araliklar:
                if lo <= 0x064A and hi >= 0x0620:
                    ihlal.append(f"{f.relative_to(SRC)}: U+{lo:04X}-U+{hi:04X}")
    assert not ihlal, f"Arap HARF bloğunu silen sınıf: {ihlal}"


def test_normalize_kopyasi_yok():
    """`normalize` tek yerde tanımlanmalı; kopya = sürüklenme demektir."""
    tanim = [f.relative_to(SRC) for f in _dosyalar()
             if re.search(r"^(export )?const normalize = \(s\) =>", f.read_text(encoding="utf-8"), re.M)]
    assert len(tanim) <= 1, f"normalize birden fazla yerde tanımlı: {tanim}"


def test_uydurma_koordinat_sabiti_yok():
    """Koordinat yoksa null kalır; sabite çakılmaz."""
    kalip = re.compile(r"(lat|lon)\s*:\s*[^,\n]*?(\|\||\?\?)\s*-?\d+(\.\d+)?")
    ihlal = []
    for f in _dosyalar():
        for i, satir in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "H51" in satir or satir.strip().startswith(("//", "*", "/*")):
                continue
            if kalip.search(satir):
                ihlal.append(f"{f.relative_to(SRC)}:{i}  {satir.strip()[:70]}")
    assert not ihlal, f"uydurma koordinat sabiti: {ihlal[:5]}"


# ── H52: popup alan sözleşmesi + harita guard'ı ────────────────────────────
def test_popup_ureticileri_var_olan_alan_okuyor():
    """Popup, veride BULUNMAYAN alan adı okumamalı.

    İki kez ölçüldü: âlim popup'ı `s.field`/`s.sub` okuyordu (db.json'da 0/450)
    ve "undefined — undefined" basıyordu; şehir popup'ı `c.yr` okuyordu (0/80)
    ve "(undefined)" basıyordu. Ortak sınıf: kod ile veri arasında ad sürüklenmesi.
    Bu test KOŞULSUZ basılan alanları veriye karşı doğrular.
    """
    import json as _json
    db = _json.loads((REPO / "web" / "src" / "data" / "db.json").read_text(encoding="utf-8"))
    src = (SRC / "components" / "shared" / "PopupFactory.js").read_text(encoding="utf-8")
    kod = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    kod = re.sub(r"^\s*//.*$", "", kod, flags=re.M)
    esleme = {"buildDynastyPopup": "dynasties", "buildBattlePopup": "battles",
              "buildEventPopup": "events", "buildScholarPopup": "scholars",
              "buildMonumentPopup": "monuments", "buildCityPopup": "cities",
              "buildRoutePopup": "routes"}
    ihlal = []
    for fn, coll in esleme.items():
        i = kod.find(f"export function {fn}")
        if i < 0:
            continue
        govde = kod[i:kod.find("\n}", i)]
        m = re.match(r"export function \w+\((\w+)", govde)
        if not m:
            continue
        var, rows = m.group(1), db.get(coll) or []
        if not rows:
            continue
        alanlar = set()
        for r2 in re.finditer(r'`<div class="p-row">.*?</div>`', govde):
            seg = r2.group(0)
            alanlar |= set(re.findall(rf"\b{var}\.(\w+)", seg))
            alanlar |= set(re.findall(rf"lf\({var},\s*'(\w+)'", seg))
        for a in sorted(alanlar):
            dolu = sum(1 for r3 in rows
                       if r3.get(a) not in (None, "", [], {})
                       or any(r3.get(f"{a}_{L}") not in (None, "", [], {}) for L in ("tr", "en", "ar")))
            if dolu == 0:
                ihlal.append(f"{fn}: {var}.{a} → {coll}'de 0/{len(rows)}")
    assert not ihlal, f"popup veride olmayan alan okuyor (undefined basar): {ihlal}"


def test_flyto_boyutsuz_haritada_cagrilmiyor():
    """Leaflet, konteyner 0x0 iken flyTo'da NaN üretir ve bileşen çöker.

    H17'de AlamMap'te, H52'de YaqutMap'te ölçüldü — ikincisinde pid ile
    doğrudan açılış (#yaqut?pid=…) tam bu yolu tetikliyordu.
    """
    for rel in ("components/yaqut/YaqutMap.jsx",):
        s = (SRC / rel).read_text(encoding="utf-8")
        if "flyTo(" not in s:
            continue
        assert "getSize()" in s, f"{rel}: flyTo öncesi konteyner boyutu kontrol edilmiyor"


def test_darphane_pid_koprusu_uydurmuyor():
    """H53: darphane→yer bağı YALNIZ curie eşleşmesinden gelmeli.

    Ad benzerliğiyle eşleştirme YASAK: aynı adı taşıyan farklı darphaneler
    olağandır ve yanlış eşleşme kullanıcıyı başka bir şehre götürür. Ayrıca
    yumuşak-silinmiş yere bağ verilmez (ölçüldü: 3 kayıt böyleydi, atlandı) —
    "pid yaşar" ile "UI onu bulur" aynı şey değildir (H49 dersi).
    """
    import json as _json
    kopru = REPO / "web" / "public" / "view-data" / "darp_pids.json"
    lite = REPO / "web" / "public" / "data" / "darpislam_lite.json"
    if not (kopru.is_file() and lite.is_file()):
        pytest.skip("darphane verisi yok")
    pids = _json.loads(kopru.read_text(encoding="utf-8"))["pids"]
    d = _json.loads(lite.read_text(encoding="utf-8"))
    mints = d if isinstance(d, list) else (d.get("mints") or [])
    lite_ids = {str(m.get("id")) for m in mints}
    # Her anahtar gerçekten lite'ta olmalı; uydurma id olmamalı
    hayalet = [k for k in pids if k not in lite_ids]
    assert not hayalet, f"lite'ta olmayan darphane id'sine pid: {hayalet[:5]}"
    # Hedefler yumuşak-silinmiş olmamalı
    place = REPO / "data" / "canonical" / "place"
    if place.is_dir():
        olu = []
        for k, pid in list(pids.items()):
            num = int(str(pid).rsplit("-", 1)[-1])
            p = place / f"iac_place_{num:08d}.json"
            if not p.is_file():
                olu.append(f"{k}→{pid} (dosya yok)")
            elif (_json.loads(p.read_text(encoding="utf-8")).get("provenance") or {}).get("deprecated"):
                olu.append(f"{k}→{pid} (deprecated)")
        assert not olu, f"ölü yere bağlanan darphane: {olu[:5]}"


def test_yer_olgulari_kaynak_isareti_tasiyor():
    """H54: ayıklanmış bilgi, doğrulanmış alan gibi gösterilemez.

    `place_facets.json`'daki her olgu `_kaynak` taşır: 'alan' = canonical
    yapısal alan (doğrulanmış), 'note' = kaynak metninden ayıklandı. UI kesik
    çerçeveyle ayırıyor. Bu ayrım kaybolursa türetilmiş bilgi doğrulanmış gibi
    okunur — bu deponun dürüstlük doktrinine aykırı.
    """
    import json as _json
    p = REPO / "web" / "public" / "view-data" / "place_facets.json"
    if not p.is_file():
        pytest.skip("place_facets üretilmemiş")
    d = _json.loads(p.read_text(encoding="utf-8"))
    eksik = []
    for pid, fac in list(d["facets"].items())[:3000]:
        for k, v in fac.items():
            if not isinstance(v, dict) or v.get("_kaynak") not in ("alan", "note"):
                eksik.append(f"{pid}.{k}")
    assert not eksik, f"kaynak işareti olmayan olgu: {eksik[:5]}"
    # UI kaynak ayrımını gösteriyor mu?
    ui = (SRC / "components" / "yaqut" / "YaqutIdCard.jsx").read_text(encoding="utf-8")
    assert "dashed" in ui, "UI 'note'tan ayıklanan olguyu görsel olarak ayırmıyor"


def test_yer_olgulari_v1_alanlarini_tekrarlamiyor():
    """v1 kartında zaten olan ülke/bölge/tip ekrana ikinci kez basılmamalı.

    Ölçüldü: yaqut_lite ct 10.997 · rg 8.519 · gt 12.935 taşıyor ve tipi
    canonical'dan DAHA İNCE ('city' ↔ 'settlement'). Bunları rozet yapmak kartı
    tekrarla şişirir. Yan dosyada durmaları sorun değil (canonical'ın v1'den
    fakir olduğunun ölçüsü); ekrana çıkmamaları gerekir.
    """
    ui = (SRC / "components" / "yaqut" / "YaqutIdCard.jsx").read_text(encoding="utf-8")
    blok = re.search(r"\{fac && \(fac\..*?\n      \)\}", ui, re.S)
    assert blok, "facet rozet bloğu bulunamadı"
    for alan in ("fac.ulke", "fac.bolge", "fac.tip"):
        assert alan not in blok.group(0), f"{alan} ekrana basılıyor — v1 zaten gösteriyor"
