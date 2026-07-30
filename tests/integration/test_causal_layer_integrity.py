"""H37: nedensellik katmanının bütünlük kilidi.

Bu katmanın tek meşruiyeti, her bağın KAYNAĞIN ARAPÇA ASLINDA kendi kurduğu
ifadeye dayanması. H36'da iki denetim, iki ayrı yoldan bu meşruiyetin
kaybedilebildiğini ölçtü:
  1) döngüsellik — kanıt türev Türkçe metinden geliyordu,
  2) sahte eşleşme — bağlaç, alâkasız kelimenin içinde eşleşiyordu (308/415).

Testler o iki kaybı da SESSİZ olmaktan çıkarır: bağlaç alıntının içinde
geçmiyorsa kanıt yok demektir, ve karar/kuyruk alanları tutarsızsa onay kapısı
delinmiş demektir.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LINKS = REPO / "data" / "sources" / "causal" / "causal_links.json"
VIEW = REPO / "web" / "public" / "view-data" / "causal_review.json"

pytestmark = pytest.mark.skipif(not LINKS.is_file(), reason="H36 hattı koşulmamış")


@pytest.fixture(scope="module")
def records():
    return json.loads(LINKS.read_text(encoding="utf-8"))["records"]


def test_her_bagin_arapca_asil_alintisi_var(records):
    """Kanıt Arapça asıldan gelir; alıntısız bağ = yorum."""
    eksik = [f"{r['book_pid']}:{r['seq']}" for r in records if not (r.get("quote_ar") or "").strip()]
    assert not eksik, f"Arapça alıntısı olmayan bağ: {eksik[:5]}"


def test_baglac_alintinin_icinde_gecer(records):
    """Bağlaç alıntıda GEÇMİYORSA kanıt yok — 2. denetimin sahte-eşleşme sınıfı."""
    kopuk = [
        f"{r['book_pid']}:{r['seq']} ({r.get('connector_ar')!r})"
        for r in records
        if (r.get("connector_ar") or "").strip()
        and (r["connector_ar"].strip() not in (r.get("quote_ar") or ""))
    ]
    assert not kopuk, f"bağlacı alıntısında geçmeyen bağ: {kopuk[:5]}"


def test_sebep_ve_sonuc_dolu(records):
    bos = [f"{r['book_pid']}:{r['seq']}" for r in records
           if not (r.get("cause_tr") or "").strip() or not (r.get("effect_tr") or "").strip()]
    assert not bos, f"sebep/sonuç boş: {bos[:5]}"


def test_onay_kapisi_delinmemis(records):
    """Karara BAĞLANMAMIŞ her kayıt insan kuyruğunda kalmalı; kararlı kayıt çıkmalı.

    Bu iki yönlü: kendiliğinden 'onaylanmış' görünen bağ da, karara bağlandığı
    hâlde kuyrukta kalan bağ da hatadır.
    """
    hatali = []
    for r in records:
        karar = (r.get("review") or {}).get("verdict")
        kuyrukta = r.get("needs_human_review")
        if karar and kuyrukta:
            hatali.append(f"{r['book_pid']}:{r['seq']} karar={karar} ama kuyrukta")
        if not karar and not kuyrukta:
            hatali.append(f"{r['book_pid']}:{r['seq']} kararsız ama kuyruk dışı")
    assert not hatali, hatali[:5]


def test_karar_degerleri_gecerli(records):
    gecersiz = [((r.get("review") or {}).get("verdict")) for r in records
                if (r.get("review") or {}).get("verdict") not in (None, "approve", "reject")]
    assert not gecersiz, f"geçersiz karar: {set(gecersiz)}"


def test_anahtarlar_tekil(records):
    """book_pid:seq inceleme aracının anahtarı — çakışırsa karar yanlış kayda yazılır."""
    anahtarlar = [f"{r['book_pid']}:{r['seq']}" for r in records]
    assert len(anahtarlar) == len(set(anahtarlar)), "book_pid:seq anahtarı tekil değil"


@pytest.mark.skipif(not VIEW.is_file(), reason="view-data üretilmemiş")
def test_arayuz_verisi_kaynakla_ayni_sayida():
    """build_causal_review.py zincirde koşmazsa ekran BAYAT veri gösterir."""
    src = json.loads(LINKS.read_text(encoding="utf-8"))["records"]
    view = json.loads(VIEW.read_text(encoding="utf-8"))["records"]
    assert len(src) == len(view), (
        f"kaynak {len(src)} ≠ arayüz {len(view)} — `make view-data` koşulmamış")


def test_alintilar_kaynakla_birebir(records):
    """H40: her alıntı KAYNAK METİNDE birebir bulunmalı.

    Ekranda ve journal'da "alıntılar kaynakla bayt-bayt aynıdır" deniyor. Bu
    iddia ÖLÇÜLMEDEN doğru sayılamaz: ölçüldüğünde 170 kaydın 2'sinde model
    kaynaktaki OCR hatasını (بقال → يقال) SESSİZCE DÜZELTMİŞTİ. İyileştirme
    yönünde bir sapma da sapmadır — alıntı, kaynağın ne dediğidir. İkisi
    kaynakla hizalandı; bu test sapmanın geri gelmesini engeller.

    Elipsli alıntılarda her parça ayrı ayrı aranır (elips, atlanan metnin
    yerini tutar; birleşik hâli kaynakta zaten bulunmaz).
    """
    import re as _re
    reading = REPO / "web" / "public" / "reading"

    def norm(s):
        return _re.sub(r"\s+", " ", s or "").strip()

    sapan = []
    atlanan = 0
    for r in records:
        p = reading / str(r["book_pid"]) / f"sec_{str(r['sec']).zfill(4)}.json"
        if not p.is_file():
            atlanan += 1          # okuma verisi gitignored; CI'da yoksa atla
            continue
        full = norm(" ".join(x.get("t", "")
                             for x in json.loads(p.read_text(encoding="utf-8")).get("paras", [])))
        parts = [norm(x) for x in _re.split(r"\.\.\.|…", norm(r["quote_ar"])) if norm(x)]
        if not all(x in full for x in parts):
            sapan.append(f"{r['book_pid']}:{r['seq']}")
    if atlanan == len(records):
        pytest.skip("okuma verisi yok (web/public/reading üretilmemiş)")
    assert not sapan, f"alıntısı kaynakla birebir tutmayan bağ: {sapan[:5]}"
