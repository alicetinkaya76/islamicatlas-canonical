"""H45 guard — havuza giren/çıkan rotaların sözleşmesi.

Denetim (docs/h44) üç kopukluk ölçtü; bu test üçünün de geri gelmesini engeller:
  1) person_bridge'de EI-1 yönü yoktu → 972 EI-1 rozeti ölüydü.
  2) Kitap müellifi hiçbir kişi kaydına bağlanmıyordu (17/17 pid varken).
  3) Kaynak kartları terminal siloydu; havuza dönüş bağı yoktu.

Veri dosyaları gitignore'da olabilir → veri testleri koşulmadığında ATLANIR,
ama KAYNAK SÖZLEŞMESİ testleri her zaman koşar.
"""
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WEB = REPO / "web" / "src"
BRIDGE = REPO / "web" / "public" / "books" / "person_bridge.json"
EI1_LITE = REPO / "web" / "public" / "view-data" / "ei1_lite.json"
POOL = REPO / "web" / "public" / "books" / "ulema_pool.json"
SHELF = REPO / "web" / "public" / "reading" / "core_shelf.json"


# ── 1) EI-1 yönü ───────────────────────────────────────────────────────────
def test_personbridge_ei1_yonunu_okuyor():
    """TERS İNDEKS (BY_PID) ei1 haritasından da beslenmeli.

    Mutasyonla sınandı: ilk sürüm yalnız dosyada "BR.ei1" arıyordu ve
    `bridgeFromEi1` yardımcısı yüzünden kusuru KAÇIRIYORDU. Guard'ın kilitlemesi
    gereken şey ters indeksin kendisi — havuzdaki rozeti canlandıran o.
    """
    src = (WEB / "data" / "personBridge.js").read_text(encoding="utf-8")
    m = re.search(r"function bridgeByPid[\s\S]*?\n}", src)
    assert m, "bridgeByPid bulunamadı"
    govde = m.group(0)
    assert "BR.ei1" in govde, (
        "bridgeByPid ters indeksi ei1 haritasından beslenmiyor — "
        "yalnız-EI1 kişilerin (972) rozeti ölü kalır")


@pytest.mark.skipif(not BRIDGE.is_file(), reason="köprü üretilmemiş")
def test_kopruda_ei1_haritasi_var():
    d = json.loads(BRIDGE.read_text(encoding="utf-8"))
    assert d.get("ei1"), "person_bridge.json'da ei1 haritası yok"
    assert d.get("n_ei1") == len(d["ei1"]), "n_ei1 harita boyutuyla tutmuyor"


@pytest.mark.skipif(not (BRIDGE.is_file() and EI1_LITE.is_file()), reason="veri yok")
def test_ei1_hedefleri_yayinlanan_katalogda_var():
    """YAYIN KAPISI: köprü, katalogda karşılığı olmayan id'ye link üretmemeli.

    Mağazada 1.174 ei1 curie'si var ama 30'u yumuşak-silinmiş kayıt (27'si h22
    hayalet defteri) ve yayınlanan katalogda YOK. Kapı olmasa bu 30 rozet
    tıklanabilir görünüp boş karta götürürdü — sahte tıklanabilirlik.
    """
    d = json.loads(BRIDGE.read_text(encoding="utf-8"))
    lite = json.loads(EI1_LITE.read_text(encoding="utf-8"))
    arr = lite if isinstance(lite, list) else (lite.get("records") or lite.get("items") or [])
    ids = {str(x.get("id")) for x in arr if x.get("id") is not None}
    kacak = [k for k in d.get("ei1", {}) if k not in ids]
    assert not kacak, f"yayınlanan katalogda olmayan EI-1 hedefi: {kacak[:5]}"


# ── 2) Kitap müellifi → havuz ──────────────────────────────────────────────
def test_libraryview_yazari_pid_ile_bagliyor():
    src = (WEB / "components" / "library" / "LibraryView.jsx").read_text(encoding="utf-8")
    assert "scholars?pid=" in src, "müellif kutusu havuza pid ile bağlanmıyor"
    assert "#dia?search=" not in src, "DİA bağı hâlâ ad aramasıyla (slug varken kayıplı)"


@pytest.mark.skipif(not (SHELF.is_file() and POOL.is_file()), reason="raf/havuz üretilmemiş")
def test_her_kitap_muellifi_havuzda_var():
    books = json.loads(SHELF.read_text(encoding="utf-8"))["books"]
    havuz = {r["id"] for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]}
    eksik = []
    for b in books:
        pid = b.get("author_pid")
        if not pid:
            eksik.append(f"{b.get('pidnum')}: author_pid YOK")
            continue
        if int(str(pid).rsplit("-", 1)[-1]) not in havuz:
            eksik.append(f"{b.get('pidnum')}: {pid} havuzda yok")
    assert not eksik, f"müellif bağı kurulamayan kitap: {eksik}"


# ── 3) Kartlardan havuza dönüş ─────────────────────────────────────────────
@pytest.mark.parametrize("kart", [
    "components/alam/AlamIdCard.jsx",
    "components/dia/DiaIdCard.jsx",
    "components/ei1/Ei1IdCard.jsx",
])
def test_kaynak_kartlarinda_havuza_donus_var(kart):
    src = (WEB / kart).read_text(encoding="utf-8")
    assert "PoolLink" in src, f"{kart}: havuza dönüş bağı yok — kart terminal silo"


def test_poollink_pid_yoksa_dugme_basmaz():
    """Sahte tıklanabilirlik yasağı: pid yoksa düğme HİÇ çıkmamalı."""
    src = (WEB / "components" / "shared" / "PoolLink.jsx").read_text(encoding="utf-8")
    assert re.search(r"if\s*\(!pid\)\s*return null", src), \
        "PoolLink pid yokken de düğme basıyor olabilir"
