"""Her yayın-katmanı üreticisi ya ZİNCİRDE ya da GEREKÇELİ olarak dışında (H55).

NEDEN VAR — bu kapı da bir unutmanın ardından kondu:
    H55'te `build_author_works.py` yazıldı, çıktısı üretildi, arayüz ona
    bağlandı — ama üretici `make build-view-data` zincirine EKLENMEDİ. Çıktı
    dizini (`web/public/view-data/`) gitignore'da olduğu için temiz bir
    kopyada dosya HİÇ oluşmayacak, arayüz sessizce boş kalacaktı. Aynı sınıf
    hata daha önce de göze battı: `core_shelf.json` yoksa müellif rozeti
    sessizce çıkmıyor (UlemaPool'da bunun için açık bir yorum var).

    Ders: üreticiyi yazmak işin yarısı; ZİNCİRE BAĞLAMAK diğer yarısı.

Bu test bir üreticinin zincirde olmasını ŞART KOŞMAZ — bazıları bilerek elle
koşulur. Şart koştuğu şey KARARIN KAYITLI olmasıdır: zincirde değilse
aşağıdaki listede gerekçesiyle bulunmalı. Böylece "unutuldu" ile "bilerek
dışarıda" birbirinden ayrılır.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
URETICI_DIR = REPO / "pipelines" / "frontend"
MAKEFILE = REPO / "Makefile"
START_LOCAL = REPO / "scripts" / "start_local.sh"

# Zincir DIŞINDA kalması BİLİNÇLİ olan üreticiler + gerekçe.
# Buraya bir isim eklemek, "her koşuda üretilmesi gerekmiyor" demektir;
# gerekçe yazmadan eklemek bu kapının amacını boşa çıkarır.
ZINCIR_DISI = {
    "build_containers.py":
        "Kitap kabı üreticisi: kaynak kitap verisi değişmedikçe çıktısı sabit; "
        "pahalı ve çıktıları depoda izleniyor. Yeni kaynak eklendiğinde elle koşulur.",
    "build_visits.py":
        "Durak (ziyaret) modeli TASLAK üretir ve çıktısı insan onay kuyruğuna "
        "girer (H21). Her koşuda yeniden üretmek onaylanmış taslağı ezerdi.",
    "build_place_index.py":
        "Yer→kitap ters indeksi Çekirdek Külliyat metinlerinden türer; "
        "yeni kitap işlenmedikçe değişmez ve tarama pahalıdır.",
    "build_yaqut_graph.py":
        "Yâkût yer grafı yalnız yaqut_lite değiştiğinde değişir; çıktısı "
        "depoda izleniyor (iki eş kopya, H17 S5).",
    # H58: BU GEREKÇE YANLIŞ ÇIKTI ve madde listeden ÇIKARILDI.
    # "Kaynak ağacı kirlenir" doğruydu ama BAYATLAMA MALİYETİ daha ağır:
    # H49/H50 birleştirmesi 1.364 kaydı yumuşak-sildikten sonra ALTI rozet
    # 30 Temmuz'dan beri şişik kaldı (havuz 22.824 ↔ gerçek 21.460, aynı
    # ekranda liste 21.460 diyordu). Üretici artık zincirde; dosyanın
    # değişmesi kirlilik değil, DOĞRU DAVRANIŞTIR.
}


def _zincir_metni() -> str:
    parcalar = []
    for p in (MAKEFILE, START_LOCAL):
        if p.is_file():
            parcalar.append(p.read_text(encoding="utf-8"))
    return "\n".join(parcalar)


def test_zincir_dosyalari_var():
    assert MAKEFILE.is_file(), "Makefile yok"


def test_her_uretici_ya_zincirde_ya_gerekceli():
    if not URETICI_DIR.is_dir():
        pytest.skip("pipelines/frontend yok")
    metin = _zincir_metni()
    unutulan = [
        f.name
        for f in sorted(URETICI_DIR.glob("build_*.py"))
        if f.name not in metin and f.name not in ZINCIR_DISI
    ]
    assert not unutulan, (
        "Bu üreticiler ne zincirde ne de gerekçeli dışarıda — temiz bir "
        "kopyada çıktıları HİÇ oluşmaz ve arayüz sessizce boş kalır:\n  "
        + "\n  ".join(unutulan)
        + "\n\nYa Makefile/start_local.sh'e ekleyin, ya ZINCIR_DISI'na "
          "gerekçesiyle yazın."
    )


def test_gerekce_listesi_bayatlamamis():
    """Silinmiş bir üretici listede kalırsa gerekçe yalan söylemeye başlar."""
    if not URETICI_DIR.is_dir():
        pytest.skip("pipelines/frontend yok")
    mevcut = {f.name for f in URETICI_DIR.glob("build_*.py")}
    hayalet = sorted(set(ZINCIR_DISI) - mevcut)
    assert not hayalet, f"ZINCIR_DISI'nda artık var olmayan üretici: {hayalet}"


def test_gerekceler_bos_degil():
    bos = [k for k, v in ZINCIR_DISI.items() if len(v.strip()) < 30]
    assert not bos, f"gerekçesi yetersiz: {bos}"


def test_h55_uretici_zincirde():
    """H55'in kendi unutması: bu kapının doğuş sebebi."""
    assert "build_author_works.py" in _zincir_metni(), (
        "build_author_works.py zincirde değil — müellif→eser köprüsü temiz "
        "kopyada üretilmez"
    )
