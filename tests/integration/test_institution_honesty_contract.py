"""Kurum ekseninde iki "sessiz kesinlik" vakası (H56 dördüncü dalga).

  1) SINIFLANDIRMA GÜVENİ DÜŞÜRÜLÜYORDU. v1 evliya katmanı 5.444 yerin
     HEPSİNDE `category_confidence` taşıyor; adaptör bunu canonical'a hiç
     geçirmiyor (`note`'da `güven` geçen evliya kaydı: 0) ve arayüz de hiç
     okumuyordu (`grep web/src category_confidence` → 0).
     Sonuç: kaynak "%20 eminim" derken merkezî defter SERT bir
     `institution_subtype` — ve ondan türeyen `@type` — ilan ediyordu.
     Ölçüldü: eşleşen 2.575 kaydın 321'i eşiğin altında ve sonuçlar gözle
     görülür yanlış:
         "Üsküp Saat Kulesi"      → mosque  (güven 0,40)
         "Kolçvar (Cetatea Colț)" → palace  (güven 0,40)
         "Nalband (Perdikkas)"    → mosque  (güven 0,20)  [yerleşim adı]

  2) TOPLU ÜST KONUM. Hıtat katmanının 801 kaydının TAMAMI tek bir Tier-2
     çözümüyle Kahire'ye bağlanıyor. Bu adaptörün BELGELİ kararı (Hıtat zaten
     Kahire topografyasıdır) ama sonuçları her kayıt için doğru değil:
     29 kayıt Kahire'den 50 km'den uzakta VE koordinatı şüpheli değil —
     çoğu Yukarı Mısır (Saîd) manastırı, en uzağı 482 km (Dayr Abī Maysās).
     Ayrı 24 kayıt da uzak ama koordinatı "düşük güvenilirlikli" işaretli;
     onlarda MESAFE KANIT DEĞİLDİR ve kuyruğa alınmazlar.

Her ikisinde de doğru değer TAHMİN EDİLMEZ: güven/uzaklık yayınlanır, kayıt
insan kuyruğuna alınır.
"""

import json
import re
from pathlib import Path

import pytest

from ._jsutil import yorumsuz

REPO = Path(__file__).resolve().parents[2]
FACETS = REPO / "web" / "public" / "view-data" / "institution_facets.json"
EVLIYA = REPO / "web" / "public" / "view-data" / "evliya_atlas_layer.json"
KUYRUK = REPO / "data" / "review_queue" / "institution_tip_ve_ust.jsonl"
DETAIL = REPO / "web" / "src" / "components" / "evliya" / "EvliyaDetail.jsx"

ESIK = 0.5


@pytest.fixture(scope="module")
def fac():
    if not FACETS.is_file():
        pytest.skip("institution_facets.json yok (üretici koşmamış)")
    return json.loads(FACETS.read_text(encoding="utf-8"))


# ── 1) Tip güveni ──────────────────────────────────────────────────────────

def test_tip_guveni_yayina_cikiyor(fac):
    n = sum(1 for v in fac["facets"].values() if "tip_guven" in v)
    assert n > 2000, f"yalnız {n} kayıtta tip güveni var — v1 eşleşmesi kopmuş olabilir"


def test_esik_alti_tipler_supheli_isaretli(fac):
    supheli = [k for k, v in fac["facets"].items() if v.get("tip_supheli")]
    assert supheli, "hiçbir kayıt şüpheli işaretlenmemiş"
    # İşaret YALNIZ eşik altındakilere basılmalı — aksi hâlde gürültü olur.
    for k in supheli:
        g = fac["facets"][k].get("tip_guven", {}).get("v")
        assert g is not None and g < ESIK, f"{k}: güven {g} ama şüpheli işaretli"


def test_guven_uydurulmamis(fac):
    """Yayınlanan değer v1'in kendi değeri olmalı; yuvarlama dışında sapma yok."""
    if not EVLIYA.is_file():
        pytest.skip("evliya katmanı yok")
    v1 = {p["pid"]: p.get("category_confidence")
          for p in json.loads(EVLIYA.read_text(encoding="utf-8")).get("places", [])
          if p.get("pid")}
    hatali = []
    for k, v in list(fac["facets"].items())[:4000]:
        if "tip_guven" not in v:
            continue
        pid = f"iac:institution-{int(k):08d}"
        beklenen = v1.get(pid)
        if beklenen is None:
            continue
        if abs(v["tip_guven"]["v"] - round(float(beklenen), 2)) > 0.005:
            hatali.append((k, v["tip_guven"]["v"], beklenen))
    assert not hatali, f"güven değeri kaynakla uyuşmuyor: {hatali[:5]}"


def test_ui_guveni_okuyor():
    """H56'ya kadar `grep web/src category_confidence` SIFIR isabet veriyordu."""
    # Yorumlar SÖKÜLÜR: `category_confidence` bu dosyanın açıklama bloğunda da
    # geçiyor ve kod kaldırılsa bile testi yeşil bırakırdı (yanlış negatif).
    s = yorumsuz(DETAIL.read_text(encoding="utf-8"))
    assert "category_confidence" in s, "arayüz sınıflandırma güvenini hiç okumuyor"
    assert "0.5" in s, "eşik yok — her kayıt aynı kesinlikte görünüyor olabilir"


# ── 2) Toplu üst konum ─────────────────────────────────────────────────────

def test_toplu_ust_konum_isaretli(fac):
    toplu = [k for k, v in fac["facets"].items() if v.get("ust_toplu")]
    assert len(toplu) > 700, (
        f"yalnız {len(toplu)} kayıtta toplu-üst işareti var; maqrizi katmanı 801"
    )


def test_uzak_kayitlarda_mesafe_yayinlaniyor(fac):
    uzak = [k for k, v in fac["facets"].items() if "ust_uzaklik_km" in v]
    assert uzak, "hiçbir uzak kayıt işaretlenmemiş"
    for k in uzak:
        assert fac["facets"][k]["ust_uzaklik_km"]["v"] > 50


def test_supheli_koordinatli_kayit_kuyruga_alinmamis(fac):
    """Mesafe, şüpheli bir koordinattan hesaplanıyorsa KANIT DEĞİLDİR."""
    if not KUYRUK.is_file():
        pytest.skip("kuyruk yok")
    kuyruk_pids = {x["pid"] for x in
                   (json.loads(l) for l in KUYRUK.read_text(encoding="utf-8").splitlines() if l.strip())
                   if x.get("adapter_id") == "institution-blanket-containment"}
    hatali = []
    for k, v in fac["facets"].items():
        if v.get("koord_supheli") and "ust_uzaklik_km" in v:
            pid = f"iac:institution-{int(k):08d}"
            if pid in kuyruk_pids:
                hatali.append(pid)
    assert not hatali, f"şüpheli koordinatlı kayıt kuyruğa alınmış: {hatali[:5]}"


# ── 3) Kuyruk sözleşmesi ───────────────────────────────────────────────────

def test_kuyruk_tahmin_tasimiyor():
    if not KUYRUK.is_file():
        pytest.skip("kuyruk yok")
    satirlar = [json.loads(l) for l in KUYRUK.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert satirlar, "kuyruk boş"
    for x in satirlar:
        assert x.get("needs_human_review") is True
        assert x.get("sorun"), "gerekçesiz kuyruk kaydı"
        for alan in ("onerilen_subtype", "onerilen_located_in", "duzeltilmis"):
            assert alan not in x, f"kuyruk kaydı tahmin taşıyor: {alan}"


def test_kuyruk_iki_sinifi_da_kapsiyor():
    if not KUYRUK.is_file():
        pytest.skip("kuyruk yok")
    tipler = {json.loads(l)["adapter_id"]
              for l in KUYRUK.read_text(encoding="utf-8").splitlines() if l.strip()}
    assert "institution-type-confidence" in tipler
    assert "institution-blanket-containment" in tipler


def test_kuyruk_ornekleri_hala_gecerli():
    """Ölçüm bozulursa test yanlış şeyi savunmaya başlar."""
    if not KUYRUK.is_file():
        pytest.skip("kuyruk yok")
    satirlar = [json.loads(l) for l in KUYRUK.read_text(encoding="utf-8").splitlines() if l.strip()]
    tip = [x for x in satirlar if x["adapter_id"] == "institution-type-confidence"]
    ust = [x for x in satirlar if x["adapter_id"] == "institution-blanket-containment"]
    assert 200 < len(tip) < 500, f"eşik altı tip sayısı beklenen aralıkta değil: {len(tip)}"
    assert 10 < len(ust) < 80, f"uzak kayıt sayısı beklenen aralıkta değil: {len(ust)}"
    assert max(x["kahireye_km"] for x in ust) > 400, "en uzak kayıt ölçümü değişmiş"
