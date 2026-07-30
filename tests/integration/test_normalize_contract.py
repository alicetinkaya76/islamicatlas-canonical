"""H44 guard — arama normalizasyonu sözleşmesi.

İki kusur ÖLÇÜLDÜ ve onarıldı; bu test ikisinin de geri gelmesini engeller.

1) Arapça karakter sınıfı HARFLERİ yutuyordu. `[\\u0610-\\u065F]` "hareke
   aralığı" sanılmıştı; oysa U+061B–U+064A arasında 43 Arap HARFİ var.
   Ölçüm: havuzdaki 16.305 Arapça addan 16.146'sı (%99) boşa düşüyordu —
   Arapça arama tümüyle ölüydü.

2) `'İ'.toLowerCase()` → `'i' + U+0307`. Bileşik nokta kalınca "İbn Sînâ"
   araması "ibn sina" ile eşleşmiyordu. (H31'de aynı sınıf hata veri
   tarafında onarılmıştı; arayüz atlanmıştı — bu test o boşluğu kapatır.)

Test JS'i çalıştırmaz; normalize.js'in KAYNAĞINI denetler. Karakter sınıfı
`\\u` kaçışıyla yazılmalıdır: çıplak Arapça sınıf kaynak dosyada bidi ile
yer değiştirip sessizce başka bir aralığa dönüşebiliyor (bu kusurun kökeni).
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
NORM = REPO / "web" / "src" / "components" / "shared" / "bookkit" / "normalize.js"

pytestmark = pytest.mark.skipif(not NORM.is_file(), reason="normalize.js yok")


@pytest.fixture(scope="module")
def src() -> str:
    return NORM.read_text(encoding="utf-8")


def test_arapca_sinifi_harf_yutmuyor(src):
    """Silinen aralık YALNIZ hareke bloklarını kapsamalı."""
    # Kaçışlı sınıfları çöz: \uXXXX-\uYYYY çiftleri
    araliklar = [(int(a, 16), int(b, 16))
                 for a, b in re.findall(r"\\u([0-9A-Fa-f]{4})-\\u([0-9A-Fa-f]{4})", src)]
    assert araliklar, "normalize.js'te \\u kaçışlı aralık yok — çıplak sınıf bidi ile bozulur"
    # U+0620–U+064A: Arap harf bloğu. Silinen hiçbir aralık buraya girmemeli.
    ihlal = [f"U+{lo:04X}-U+{hi:04X}" for lo, hi in araliklar if lo <= 0x064A and hi >= 0x0620]
    assert not ihlal, f"silme aralığı Arap HARF bloğunu kapsıyor: {ihlal}"


def test_birlesik_diyakritikler_temizleniyor(src):
    """İ→i+U+0307 sorunu: NFKD + birleşik-işaret silme olmalı."""
    assert "NFKD" in src, "NFKD ayrıştırması yok — 'İ' noktalı kalır, 'ibn' ile eşleşmez"
    assert re.search(r"\\u0300-\\u036[Ff]", src), "birleşik diyakritik aralığı silinmiyor"


def test_harekeler_hala_siliniyor(src):
    """Harekeler silinmeye devam etmeli — harekeli/haresiz yazım eşleşsin."""
    aralik = {(int(a, 16), int(b, 16))
              for a, b in re.findall(r"\\u([0-9A-Fa-f]{4})-\\u([0-9A-Fa-f]{4})", src)}
    tashkil = any(lo <= 0x064B and hi >= 0x0652 for lo, hi in aralik)
    assert tashkil, "teşkîl bloğu (U+064B–U+0652) silinmiyor"


def test_turkce_harfler_korunuyor(src):
    for ch in ("ı", "ğ", "ü", "ş", "ö", "ç"):
        assert f"/{ch}/g" in src or f"[{ch}" in src, f"TR harfi {ch} eşlemesi kayıp"
