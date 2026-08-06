"""Merkezî defterin aranabilir katmanının sözleşmesi (H56 üçüncü dalga).

DENETİM BULGUSU: `SearchBar` indeksi TAMAMEN v1'in `db.json`'ından ve beş
"lite" dosyadan kuruluyordu. Mağazadaki 9.956 olayın, 9.404 eserin ve 5.423
kurumun ARANABİLİR OLANI SIFIRDI — yani havuzu büyütmenin arama eksenindeki
karşılığı yoktu.

BU KATMANIN TEK SERT KURALI: **her kayıt gerçekten açılan bir hedefe gitmeli.**
H46 doktrini: sahte tıklanabilirlik, dürüst boşluktan kötüdür. Bu yüzden
kurumlar (hedefi olmayan 5.423 kayıt) BİLEREK indekslenmez; testler bunun
kazara "düzeltilmemesini" de korur.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
IDX = REPO / "web" / "public" / "view-data" / "canonical_search.json"
SB = REPO / "web" / "src" / "components" / "shared" / "SearchBar.jsx"
READING = REPO / "web" / "public" / "reading"
POOL = REPO / "web" / "public" / "books" / "ulema_pool.json"


@pytest.fixture(scope="module")
def idx():
    if not IDX.is_file():
        pytest.skip("canonical_search.json yok (üretici koşmamış)")
    return json.loads(IDX.read_text(encoding="utf-8"))


def test_yapi(idx):
    for k in ("_doc", "counts", "kayitlar"):
        assert k in idx
    assert len(idx["kayitlar"]) > 15000, "indeks beklenenden çok küçük"


def test_her_kaydin_hedefi_var(idx):
    """Hedefsiz kayıt = boş ekrana götüren arama sonucu."""
    hedefsiz = [r for r in idx["kayitlar"]
                if r.get("b") is None and r.get("p") is None]
    assert not hedefsiz, f"{len(hedefsiz)} kayıt hedefsiz: {hedefsiz[:3]}"


def test_olay_kitap_bolum_ciftini_tasiyor(idx):
    olaylar = [r for r in idx["kayitlar"] if r["t"] == "ce"]
    assert olaylar, "hiç canonical olay indekslenmemiş"
    eksik = [r for r in olaylar if r.get("b") is None or r.get("s") is None]
    assert not eksik, f"{len(eksik)} olayda kitap/bölüm çifti eksik"


def test_olay_hedefleri_gercekten_var(idx):
    """Örneklem: işaret edilen bölüm dosyası diskte olmalı."""
    if not READING.is_dir():
        pytest.skip("reading/ yok (gitignored — temiz kopyada bulunmaz)")
    olaylar = [r for r in idx["kayitlar"] if r["t"] == "ce"]
    kirik = []
    for r in olaylar[:600]:
        d = READING / f"{r['b']:08d}"
        if not d.is_dir():
            continue                     # o kitap henüz işlenmemiş — ayrı mesele
        f = d / f"sec_{r['s']:04d}.json"
        if not f.is_file():
            kirik.append(f"{r['b']}/{r['s']}")
    assert not kirik, f"var olmayan bölüme giden olay: {kirik[:5]}"


def test_eser_hedefleri_havuzda(idx):
    """Eser müellifine gidiyorsa o müellif havuzda GÖRÜNÜR olmalı."""
    if not POOL.is_file():
        pytest.skip("ulema_pool.json yok")
    havuz = {r["id"] for r in json.loads(POOL.read_text(encoding="utf-8"))["kisiler"]}
    kirik = [r for r in idx["kayitlar"]
             if r["t"] == "cw" and r.get("b") is None and r.get("p") not in havuz]
    assert not kirik, f"{len(kirik)} eser havuz DIŞI müellife gidiyor: {kirik[:3]}"


def test_kurumlar_bilerek_disarida(idx):
    """5.423 kurumun açılabilir hedefi yok; indekslenirse boş ekran üretir."""
    assert not [r for r in idx["kayitlar"] if r["t"] == "ci"], \
        "kurum indekslenmiş — join anahtarı mint edilmeden hedef üretilemez"
    assert idx["counts"].get("kurum_hedefsiz_indekslenmedi", 0) > 5000, \
        "kurum sayısı raporlanmıyor — sessiz düşürme"


def test_yil_ciplak_degil(idx):
    """Eser tarafında `y` telif tarihi DEĞİL, müellifin ölüm yılı sınırı."""
    ciplak = [r for r in idx["kayitlar"]
              if r["t"] == "cw" and r.get("y") is not None and "yk" not in r]
    oran = len(ciplak) / max(sum(1 for r in idx["kayitlar"] if r["t"] == "cw"), 1)
    assert oran < 0.05, f"%{oran*100:.1f} eserde yıl var ama yaklaşıklık işareti yok"


# ── Arayüz sözleşmesi ──────────────────────────────────────────────────────

def test_ui_indeksi_okuyor():
    s = SB.read_text(encoding="utf-8")
    assert "canonical_search.json" in s, "arayüz indeksi hiç çekmiyor"
    assert "canon_event" in s and "canon_work" in s, "tipler indekse eklenmiyor"


def test_ui_kategori_cipini_tanimliyor():
    """KRİTİK: doSearch her sonucu catMatch'ten geçirir; tanımlı bir
    kategoriye düşmeyen tip SESSİZCE elenir — 18.487 kayıt indekse girip
    aramada hiç görünmezdi."""
    s = SB.read_text(encoding="utf-8")
    assert "CANON_TYPES" in s, "canonical tipler için kategori eşlemesi yok"
    assert re.search(r"key:\s*'canon'", s), "'canon' çipi CATEGORIES'te yok"
    assert "cats.has('canon')" in s, "catMatch canonical tipleri geçirmiyor"


def test_ui_rotalari_kuruyor():
    s = SB.read_text(encoding="utf-8")
    assert "#library?book=" in s and "sec=" in s, "olay rotası kurulmuyor"
    assert "#scholars?pid=iac:person-" in s, "eser rotası kurulmuyor"


def test_uydurma_koordinat_geri_gelmesin():
    """H51 süpürgesinden kaçan `lat: 30, lon: 45` sabiti (182 bilim âlimi)."""
    kok = REPO / "web" / "src"
    suclu = []
    for u in ("*.js", "*.jsx"):
        for f in kok.rglob(u):
            t = f.read_text(encoding="utf-8", errors="ignore")
            t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
            if re.search(r"lat:\s*30\s*,\s*lon:\s*45", t):
                suclu.append(str(f.relative_to(REPO)))
    assert not suclu, f"uydurma koordinat sabiti geri gelmiş: {suclu}"
