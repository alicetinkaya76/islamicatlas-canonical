"""web/src içindeki her göreli import GERÇEKTEN çözülmeli (H55).

NEDEN VAR — bu kapı bir REGRESYONUN ARDINDAN kondu:
    H51'de "tek otorite normalize" onarımı yapılırken yedi dosyaya
    `from '../../shared/bookkit/normalize'` yazıldı. Doğru derinlik
    `../shared/...` idi; `../../` `web/src/shared/` demek oluyordu ve öyle bir
    dizin YOK. Sonuç: `vite build` TAMAMEN çöküyordu ve bu H51'den H55'e kadar
    fark edilmedi.

    Neden fark edilmedi? Çünkü `make test` yalnız Python tarafını sınıyordu;
    hiçbir kapı ön yüzü derlemiyordu. Geliştirme sunucusu de sessiz kaldı,
    zira kırık modülleri yükleyen görünümlere o oturumlarda girilmemişti.

    Ders (H51'in kendi dersinin devamı): "tek kaynağa taşıdım" demek yetmez —
    TAŞIMANIN KENDİSİ de sınanmalıdır.

Bu test `vite build` çalıştırmaz (yavaş ve node bağımlılığı ister); statik
olarak her göreli import yolunu dosya sistemine karşı çözer. Yakaladığı sınıf
tam olarak yukarıdaki kusurdur ve milisaniyeler sürer.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "web" / "src"

# import/export ... from '<yol>'  ve  import('<yol>')
IMPORT_RE = re.compile(r"""(?:from|import)\s*\(?\s*['"](\.[^'"]*)['"]""")
UZANTILAR = ("", ".js", ".jsx", ".ts", ".tsx", ".json", ".css")

BLOK_YORUM = re.compile(r"/\*.*?\*/", re.S)


def _yorumsuz(metin: str) -> str:
    """Yorumları söker. Kapı ilk koşusunda YANLIŞ ALARM verdi: evliya/index.js
    içindeki `Usage: import { EvliyaView } from './components/evliya';` bir
    JSDoc satırıydı ve gerçek import sanıldı. Yanlış alarm veren kapı,
    görmezden gelinen kapıdır — o yüzden yorumlar taramadan çıkarılır."""
    metin = BLOK_YORUM.sub("", metin)
    satirlar = []
    for s in metin.split("\n"):
        d = s.lstrip()
        satirlar.append("" if d.startswith("//") or d.startswith("*") else s)
    return "\n".join(satirlar)


def _cozulur(temel: Path, hedef: str) -> bool:
    yol = (temel.parent / hedef).resolve()
    for u in UZANTILAR:
        if u and yol.with_name(yol.name + u).is_file():
            return True
    if yol.is_file():
        return True
    if yol.is_dir():                       # dizin → index.* aranır
        return any((yol / f"index{u}").is_file() for u in (".js", ".jsx", ".ts", ".tsx"))
    return False


def _kaynak_dosyalari():
    if not SRC.is_dir():
        return []
    out = []
    for u in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        out.extend(SRC.rglob(u))
    return sorted(p for p in out if "node_modules" not in p.parts)


def test_web_src_var():
    assert SRC.is_dir(), f"{SRC} yok — ön yüz kabuğu taşınmamış olabilir"


def test_tum_goreli_importlar_cozuluyor():
    """Çözülmeyen tek bir göreli import bile üretim derlemesini düşürür."""
    dosyalar = _kaynak_dosyalari()
    assert dosyalar, "web/src altında kaynak dosya bulunamadı"

    kirik = []
    for f in dosyalar:
        try:
            metin = f.read_text(encoding="utf-8")
        except OSError:
            continue
        temiz = _yorumsuz(metin)
        for m in IMPORT_RE.finditer(temiz):
            hedef = m.group(1)
            if not _cozulur(f, hedef):
                satir = temiz[: m.start()].count("\n") + 1
                kirik.append(f"{f.relative_to(REPO)}:{satir} → {hedef}")

    assert not kirik, (
        "Çözülmeyen göreli import (vite build bunlarda çöker):\n  "
        + "\n  ".join(kirik)
    )


def test_bookkit_tek_otorite_dizini():
    """normalize'ın tek otoritesi bookkit; yolu sabit ve TEK olmalı.

    H51 hatası tam da burada doğdu: doğru dosyaya YANLIŞ derinlikten
    işaret edildi. Yol bir kez ölçülüp sabitlenirse, kopyala-yapıştır
    sırasında sapma testte görünür.
    """
    hedef = SRC / "components" / "shared" / "bookkit" / "normalize.js"
    assert hedef.is_file(), f"bookkit/normalize.js beklenen yerde yok: {hedef}"

    tuketiciler = []
    for f in _kaynak_dosyalari():
        try:
            metin = f.read_text(encoding="utf-8")
        except OSError:
            continue
        metin = _yorumsuz(metin)
        if "bookkit/normalize" in metin or "from '../shared/bookkit'" in metin:
            tuketiciler.append(f)

    assert len(tuketiciler) >= 5, (
        f"bookkit tüketicisi beklenenden az ({len(tuketiciler)}); "
        "kopya normalize geri gelmiş olabilir"
    )
    for f in tuketiciler:
        for m in IMPORT_RE.finditer(_yorumsuz(f.read_text(encoding="utf-8"))):
            if "bookkit" in m.group(1):
                assert _cozulur(f, m.group(1)), (
                    f"{f.relative_to(REPO)} bookkit'e çözülmeyen yolla bağlanıyor: "
                    f"{m.group(1)}"
                )


@pytest.mark.parametrize("yanlis", ["../../shared/bookkit", "../../../shared/bookkit"])
def test_yanlis_bookkit_derinligi_geri_gelmesin(yanlis):
    """H51'in tam kalıbı: doğru dosya, yanlış derinlik."""
    suclu = [
        str(f.relative_to(REPO))
        for f in _kaynak_dosyalari()
        if yanlis in _yorumsuz(f.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert not suclu, f"yanlış bookkit derinliği ({yanlis}) geri gelmiş: {suclu}"
