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


# ── 4) 'b' rozeti alt-kodları (H46) ────────────────────────────────────────
def test_havuz_kod_tablosu_ureticiyle_ayni():
    """SRC tablosu ile üreticinin CODE_LABELS'ı AYNI kod kümesini tanımalı.

    meta.kaynak_basina anahtarları filtre çiplerini besliyor; script ile bileşen
    ayrı commit'lerde giderse çipler ya sayısız görünür ya da hiçbir kişiyi
    süzemez. Bu test ikisini bir arada tutar.
    """
    py = (REPO / "pipelines" / "frontend" / "build_ulema_pool.py").read_text(encoding="utf-8")
    jsx = (WEB / "components" / "scholars" / "UlemaPool.jsx").read_text(encoding="utf-8")
    m = re.search(r"CODE_ORDER = \[(.*?)\]", py, re.S)
    assert m, "CODE_ORDER bulunamadı"
    uretici = {x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()}
    m2 = re.search(r"const SRC_ORDER = \[(.*?)\]", jsx, re.S)
    assert m2, "SRC_ORDER bulunamadı"
    ui = {x.strip().strip("\"'") for x in m2.group(1).split(",") if x.strip()}
    assert uretici == ui, f"kod kümeleri ayrıştı — üretici {uretici - ui}, UI {ui - uretici}"


@pytest.mark.skipif(not POOL.is_file(), reason="havuz üretilmemiş")
def test_dia_madde_parcasi_hedefi_ayni_kisiye_ait():
    """EN BÜYÜK TUZAK: dia-chunks slug'ı BAŞKA bir pid'e bağlı olabiliyor.

    Ölçüldü: 300 kayıtta slug başka kişiye aitti; pid eşitliği kontrol
    edilmeseydi o kişilerde link YANLIŞ DİA maddesini açardı. Üretici hedefi
    yalnız eşitlik sağlanınca yazar — bu test o kuralı kilitler.
    """
    dia = REPO / "web" / "public" / "view-data" / "dia_lite.json"
    if not dia.is_file():
        pytest.skip("dia_lite yok")
    d = json.loads(dia.read_text(encoding="utf-8"))
    arr = d if isinstance(d, list) else (d.get("records") or d.get("items") or [])
    slug2pid = {str(x.get("id")): x.get("pid") for x in arr if x.get("id")}
    yanlis = []
    for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]:
        slug = (r.get("t") or {}).get("bc")
        if not slug:
            continue
        pid = f"iac:person-{r['id']:08d}"
        if slug2pid.get(slug) != pid:
            yanlis.append(f"{pid} → {slug} (asıl sahip: {slug2pid.get(slug)})")
    assert not yanlis, f"başka kişiye ait DİA slug'ına link: {yanlis[:5]}"


@pytest.mark.skipif(not POOL.is_file(), reason="havuz üretilmemiş")
def test_hedefsiz_kod_hedef_yazmiyor():
    """openiti/alatli için sitede açılabilir sayfa YOK — hedef yazılmamalı."""
    kacak = [r["id"] for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]
             if set((r.get("t") or {})) & {"bo", "ba"}]
    assert not kacak, f"açılabilir sayfası olmayan koda hedef yazılmış: {kacak[:5]}"
