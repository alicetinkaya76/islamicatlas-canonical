"""Mağazaya dokunan her modül ORTAK kapıyı bildirmeli (H59).

NEDEN VAR — bir varsayım CI'yı yedi gün kırmızı tuttu ve kimse bakmadı:

    Store-bağımlı modüller `PERSON_DIR.exists()` ile kapatılmıştı.
    Varsayım: *"kişi mağazası varsa gerisi de vardır."* H49 (30 Temmuz)
    `data/canonical/person`'ı depoya commit edince varsayım kırıldı —
    CI'da person VAR, `_state/` ve `place/` YOK. Kapı "hazır" dedi,
    8 test koştu ve düştü. Son yeşil koşu 30 Temmuz; sonraki her push
    kırmızı. Yerelde `make test` yeşil olduğu için 14 push boyunca
    fark edilmedi.

    Testlerin ürettiği mesajlar da yanıltıcıydı: CI "8.376 kırık PID
    referansı" diyordu — gerçek bir veri kusuru değil, `place/` dizininin
    yokluğuydu. **Eksik bağımlılık, testin YANLIŞ ŞEY hakkında konuşmasına
    yol açar.**

Bu kapı, mağaza dizinlerine modül düzeyinde dokunan her test dosyasının
`_store.STORE_SKIP`'i (ya da kendi açık `skipif`'ini) bildirmesini şart
koşar. Böylece "kapı koymayı unuttum" ile "bilerek kapısız" ayrılır.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BURASI = Path(__file__).resolve().parent

# Mağaza yollarına modül düzeyinde dokunma izi.
STORE_IZI = re.compile(r'"data"\s*/\s*"(?:canonical|_state|_index)"|data/(?:canonical|_state|_index)')
# Kabul edilen kapı biçimleri.
KAPI = re.compile(r"STORE_SKIP|pytestmark\s*=\s*pytest\.mark\.skipif|pytest\.skip\(")

# Kapısız olması BİLİNÇLİ olan dosyalar + gerekçe.
#
# Bu tarama STATİK: yolu METİNDE görürse işaretler, o yola gerçekten
# BAĞIMLI olup olmadığını bilemez. Aşağıdakiler mağaza yolunu anıyor ama
# mağazasız da yeşil — ÖLÇÜLDÜ (data/_state ve data/canonical/place
# geçici olarak gizlenip koşuldu, 2026-08-06):
KAPISIZ_TAMAM = {
    "_store.py": "kapının kendisi",
    "_jsutil.py": "mağazaya dokunmaz, JS yorum sökücüsü",
    "conftest.py": "fixture'lar tembel; testler kendi kapılarını taşır",
    "test_store_gate_declared.py": "bu dosya (statik tarama, mağaza okumaz)",
    "test_bosworth_pilot.py": "mağazasız hiç test toplamıyor — ölçüldü (no tests ran)",
    "test_entity_resolver_tier2.py": "mağazasız 9 test YEŞİL — ölçüldü (fixture'lar kendi kapısını taşıyor)",
    "test_h9_schema_set_coherence.py": "mağazasız 5 test YEŞİL — ölçüldü (yalnız schemas/ okuyor)",
    "test_no_dotted_i_artifact.py": "mağazasız 2 test YEŞİL — ölçüldü (kaynak ağacını tarıyor)",
}


def test_magazaya_dokunan_modul_kapi_bildiriyor():
    kapisiz = []
    for f in sorted(BURASI.glob("test_*.py")) + sorted(BURASI.glob("_*.py")):
        if f.name in KAPISIZ_TAMAM:
            continue
        s = f.read_text(encoding="utf-8")
        if not STORE_IZI.search(s):
            continue
        if not KAPI.search(s):
            kapisiz.append(f.name)
    assert not kapisiz, (
        "Mağaza dizinlerine dokunuyor ama kapı bildirmiyor — temiz klonda/CI'da "
        "eksik veriyi VERİ KUSURU sanıp kırmızı yanar:\n  " + "\n  ".join(kapisiz)
        + "\n\n`from ._store import STORE_SKIP` + `pytestmark = STORE_SKIP` ekleyin."
    )


def test_iki_dusen_modul_ortak_kapiya_bagli():
    """H59'un doğuş sebebi: tam bu iki modül CI'da 8 test düşürüyordu."""
    for ad in ("test_dia_pilot.py", "test_h7_invariants.py"):
        s = (BURASI / ad).read_text(encoding="utf-8")
        assert "STORE_SKIP" in s, f"{ad} ortak kapıyı kullanmıyor"


def test_kapi_gercekten_eksigi_goruyor():
    """Kapı, bağlı olduğu HER parçayı sormalı — 'parçası var' ≠ 'hazır'."""
    from ._store import GEREKENLER
    assert "canonical/person" in GEREKENLER
    assert "canonical/place" in GEREKENLER, (
        "place/ sorulmuyor — H49 sonrası CI'da tam bu eksiklik '8.376 kırık "
        "PID referansı' diye raporlandı"
    )
    assert "_state" in GEREKENLER, "_state sorulmuyor — sidecar testleri düşer"


def test_kapisiz_listesi_gerekceli():
    bos = [k for k, v in KAPISIZ_TAMAM.items() if len(v.strip()) < 10]
    assert not bos, f"gerekçesi yetersiz: {bos}"
