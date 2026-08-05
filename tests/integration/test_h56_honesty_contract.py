"""Uydurma-sınıfı kusurların geri gelmemesi (H56).

Bu dosyadaki her test, denetimde ÖLÇÜLEREK bulunmuş ve onarılmış somut bir
"veri bilmiyor ama ekran biliyormuş gibi davranıyor" vakasını kilitler.
Hepsi mutasyonla doğrulandı: kusur geri konunca ilgili test kızarıyor.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

BLOK_YORUM = re.compile(r"/\*.*?\*/", re.S)


def yorumsuz(metin: str) -> str:
    """Yorumları söker.

    Bu oturumun ikinci kez öğrendiği ders: kapının kendisi yanlış alarm
    verirse görmezden gelinir. İlk sefer JSDoc içindeki örnek bir `import`
    gerçek sanılmıştı; burada da ONARIMI AÇIKLAYAN yorum ("elle yazılmıştı
    '5.618'") onarılmamış kod sanıldı. Kusurun ADI kusurun KENDİSİ değildir.
    """
    metin = BLOK_YORUM.sub("", metin)
    return "\n".join("" if l.lstrip().startswith(("//", "*")) else l
                      for l in metin.split("\n"))
SRC = REPO / "web" / "src"
DB = SRC / "data" / "db.json"
FLAGS = REPO / "web" / "public" / "view-data" / "dynasty_temporal_flags.json"
KUYRUK = REPO / "data" / "review_queue" / "dynasty_temporal.jsonl"

HICRET = 622


# ── 1) Savaş sonucu: veri yoksa "zafer" değil, "bilinmiyor" ────────────────

def test_savas_sonucu_varsayilani_zafer_degil():
    """ÖLÇÜLDÜ: 100 savaşın 39'unda sonuç metni yok ve hepsi ✓ alıyordu.
    İkisi tarihsel olarak YANLIŞTI: Tarain I (Gurlu yenilgisi) ve Belgrad
    1456 (Osmanlı yenilgisi) ekranda zafer görünüyordu."""
    f = SRC / "data" / "battleOutcome.js"
    assert f.is_file(), "battleOutcome.js yok — tek otorite kaldırılmış olabilir"
    s = f.read_text(encoding="utf-8")
    assert "return 'unknown'" in s, "sonuç metni yokken 'unknown' dönmüyor"
    # Fonksiyonun SON satırı 'win' olabilir (metin varsa doğru); ama boş
    # girdide 'unknown' dönen erken çıkış ŞART.
    assert re.search(r"if\s*\(\s*!out\s*\)\s*return\s*'unknown'", s), \
        "boş sonuç için erken çıkış yok"


def test_savas_sonucu_kopyasi_geri_gelmesin():
    """Aynı fonksiyon ÜÇ dosyada kopyalanmıştı ve üçünün de varsayılanı 'win'di."""
    suclu = []
    for f in (SRC / "components" / "battles").glob("*.jsx"):
        s = f.read_text(encoding="utf-8")
        if re.search(r"function\s+getOutcomeType\s*\(", s):
            suclu.append(str(f.relative_to(REPO)))
    assert not suclu, f"yerel getOutcomeType kopyası geri gelmiş: {suclu}"


def test_bilinmeyen_sonuca_rozet_basilmiyor():
    f = SRC / "data" / "battleOutcome.js"
    s = f.read_text(encoding="utf-8")
    assert "outcomeMark" in s, "rozet üreticisi yok"
    card = SRC / "components" / "battles" / "BattleCard.jsx"
    assert "outcomeMark(ot)" in card.read_text(encoding="utf-8"), \
        "BattleCard rozeti koşulsuz basıyor olabilir"


# ── 2) Hanedan yıl aralığı: imkânsız aralık çıplak basılmaz ────────────────

@pytest.fixture(scope="module")
def bayraklar():
    if not FLAGS.is_file():
        pytest.skip("dynasty_temporal_flags.json yok (üretici koşmamış)")
    return json.loads(FLAGS.read_text(encoding="utf-8"))


def test_imkansiz_yil_araliklari_bayrakli(bayraklar):
    """İslam takvimi 622'de başlar; 622 öncesi başlangıç ya da start>end
    imkânsızdır. ÖLÇÜLDÜ: 186 hanedanın 9'u böyle."""
    if not DB.is_file():
        pytest.skip("db.json yok")
    dyn = json.loads(DB.read_text(encoding="utf-8")).get("dynasties") or []
    flags = bayraklar["flags"]
    kacak = []
    for d in dyn:
        s, e = d.get("start"), d.get("end")
        if not isinstance(s, int) or not isinstance(e, int):
            continue
        bozuk = s < HICRET or (0 < e < HICRET) or (e != 2025 and s > e)
        if bozuk and flags.get(str(d["id"]), {}).get("d") != "tutarsiz":
            kacak.append(f"{d['id']} {d.get('tr')} {s}–{e}")
    assert not kacak, "bayraksız imkânsız aralık: " + "; ".join(kacak)


def test_tutarsiz_kayitlar_insan_kuyrugunda(bayraklar):
    """Doktrin: borderline durum otomatik çözülmez, kuyruğa alınır."""
    if not KUYRUK.is_file():
        pytest.skip("kuyruk dosyası yok")
    satirlar = [json.loads(x) for x in KUYRUK.read_text(encoding="utf-8").splitlines() if x.strip()]
    tutarsiz = sum(1 for v in bayraklar["flags"].values() if v.get("d") == "tutarsiz")
    assert len(satirlar) == tutarsiz, (
        f"kuyruk {len(satirlar)} kayıt taşıyor ama tutarsız {tutarsiz}"
    )
    for x in satirlar:
        assert x.get("needs_human_review") is True
        assert x.get("nedenler"), "gerekçesiz kuyruk kaydı"


def test_dogru_yil_tahmin_edilmemis(bayraklar):
    """Üretici hiçbir yeri 'düzeltmemeli' — yalnız işaretlemeli."""
    if not KUYRUK.is_file():
        pytest.skip("kuyruk dosyası yok")
    for x in (json.loads(l) for l in KUYRUK.read_text(encoding="utf-8").splitlines() if l.strip()):
        assert "onerilen_start" not in x and "duzeltilmis" not in x, \
            "kuyruk kaydı tahmin edilmiş yıl taşıyor"


def test_ui_ciplak_yil_basmiyor():
    """PopupFactory ve SearchBar tek otoriteden geçmeli."""
    pf = SRC / "components" / "shared" / "PopupFactory.js"
    sb = SRC / "components" / "shared" / "SearchBar.jsx"
    for f in (pf, sb):
        s = f.read_text(encoding="utf-8")
        assert "dynastyYearRange" in s, f"{f.name} yıl aralığını tek otoriteden almıyor"
    assert "${d.start} – ${d.end}" not in yorumsuz(pf.read_text(encoding="utf-8")), \
        "PopupFactory hâlâ çıplak yıl basıyor"


# ── 3) Şematik yayılım ve devralınmış hükümdar konumu ──────────────────────

def test_sematik_yayilim_soyleniyor():
    """186 hanedanın 185'inde dikdörtgen veriden GELMİYOR (başkent ± sabit
    derece, yarıçap editöryel 'önem' etiketinden)."""
    h = SRC / "data" / "dynastyHonesty.js"
    assert h.is_file(), "dynastyHonesty.js yok"
    s = h.read_text(encoding="utf-8")
    assert "EXTENT_NOTE" in s and "hasMeasuredExtent" in s
    pf = (SRC / "components" / "shared" / "PopupFactory.js").read_text(encoding="utf-8")
    assert "EXTENT_NOTE" in pf, "popup şematik yayılımı söylemiyor"
    lm = (SRC / "components" / "map" / "LayerManager.js").read_text(encoding="utf-8")
    assert "olculmus" in lm, "şematik dikdörtgen görsel olarak ayrılmıyor"


def test_gercek_bbox_sayisi_hala_bir():
    """Ölçüm bozulursa test yanlış şey savunmaya başlar."""
    if not DB.is_file():
        pytest.skip("db.json yok")
    dyn = json.loads(DB.read_text(encoding="utf-8")).get("dynasties") or []
    gercek = [d for d in dyn if all(d.get(k) for k in ("bn", "bs", "bw", "be"))]
    assert len(gercek) <= 5, (
        f"{len(gercek)} hanedan gerçek bbox taşıyor — ölçüm değişmiş, "
        "şematik uyarısının kapsamı gözden geçirilmeli"
    )


def test_hukumdar_konumu_devralinmis_soyleniyor():
    """830 hükümdarın 830'u hanedanının başkent koordinatında."""
    if not DB.is_file():
        pytest.skip("db.json yok")
    db = json.loads(DB.read_text(encoding="utf-8"))
    dmap = {d["id"]: d for d in db.get("dynasties") or []}
    rulers = db.get("rulers") or []
    ayni = sum(1 for r in rulers
               if dmap.get(r.get("did"))
               and r.get("lat") == dmap[r["did"]].get("lat")
               and r.get("lon") == dmap[r["did"]].get("lon"))
    assert ayni > len(rulers) * 0.5, "ölçüm değişmiş: koordinatlar artık devralınmıyor"
    pf = (SRC / "components" / "shared" / "PopupFactory.js").read_text(encoding="utf-8")
    assert "RULER_COORD_NOTE" in pf, "hükümdar popup'ı devralınmış konumu söylemiyor"


# ── 4) Elle yazılmış sayı ──────────────────────────────────────────────────

def test_katman_rozeti_elle_yazilmamis():
    mv = yorumsuz((SRC / "components" / "map" / "MapView.jsx").read_text(encoding="utf-8"))
    assert "5,618" not in mv and "5.618" not in mv, \
        "MapView'da elle yazılmış olay sayısı geri gelmiş"
    assert "CANON_EVENT_N" in mv, "sayı üretilen dosyadan okunmuyor"


# ── 5) Birleştirme artığı: kaynak izleri kazanana taşınmalı ────────────────

def test_kaynak_izleri_kazanana_tasiniyor():
    """ÖLÇÜLDÜ: birleştirmeden sonra 1.976 curie yumuşak-silinmiş kayıtta
    kalmış, 1.382 kazanan kişiyi etkiliyordu — birleştirme tam da birleştirmek
    istediği zenginliği ekrandan düşürüyordu."""
    p = REPO / "pipelines" / "frontend" / "build_ulema_pool.py"
    s = p.read_text(encoding="utf-8")
    assert "merge_winner" in s, "kaynak izi yönlendirmesi yok"
    assert "kaz = merge_winner(num)" in s, "load_source_codes yönlendirme yapmıyor"


def test_dia_slug_guvencesi_korunuyor():
    """H46 dersi: slug BAŞKA pid'e bağlıysa link yazılmaz. Yönlendirme bu
    güvenceyi gevşetmemeli — yalnız iki tarafı da kazanana çevirmeli."""
    p = REPO / "pipelines" / "frontend" / "build_ulema_pool.py"
    s = p.read_text(encoding="utf-8")
    assert "sahip is not None and sahip == num" in s, \
        "pid eşitlik kontrolü kaldırılmış — yanlış DİA maddesi açılabilir"
