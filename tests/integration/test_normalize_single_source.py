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
