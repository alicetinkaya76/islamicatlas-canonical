"""Mağaza hazır mı? — store-bağımlı testlerin ORTAK kapısı (H59).

NEDEN VAR — bir varsayım yedi gün boyunca CI'yı kırmızı tuttu:

    H9 Stage 3'te store-bağımlı modüller `PERSON_DIR.exists()` ile
    kapatılmıştı. Varsayım: *"kişi mağazası varsa geri kalanı da vardır."*
    Temiz klonda hiçbiri yoktu, modül atlanıyordu, CI yeşildi.

    H49'da (dfc20836, 30 Temmuz) `data/canonical/person` DEPOYA COMMIT
    EDİLDİ — ama `data/_state/`, `data/canonical/place/` ve `data/_index/`
    gitignore'da kaldı. Varsayım kırıldı: CI'da person VAR, gerisi YOK.
    Kapı "mağaza hazır" diye karar verdi, testler koştu ve düştü.

    Sonuç: son yeşil koşu 30 Temmuz (H48); H49'dan itibaren HER PUSH
    kırmızı — 8 test, aynı 8 test (H9 Stage 3'ün onardığı sekiz).
    Yerelde `make test` yeşil olduğu için fark edilmedi.

    Ders: **bir kapı, bağlı olduğu HER şeyi sormalı.** "Parçası var" ile
    "hazır" aynı şey değildir; eksik parça, testin yanlış şey hakkında
    konuşmasına yol açar (CI'daki "8.376 kırık PID referansı" gerçek bir
    kusur değil, place/ dizininin yokluğuydu).

Kullanım:

    from ._store import STORE_SKIP
    pytestmark = STORE_SKIP
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
STATE = REPO / "data" / "_state"

# Store-bağımlı testlerin GERÇEKTEN dokunduğu parçalar. Biri bile eksikse
# mağaza "hazır" değildir — çünkü test o eksikliği bir VERİ KUSURU sanır.
GEREKENLER = {
    "canonical/person": CANON / "person",
    "canonical/place": CANON / "place",
    "_state": STATE,
}


def eksikler() -> list:
    return sorted(ad for ad, yol in GEREKENLER.items() if not yol.is_dir())


def store_hazir() -> bool:
    return not eksikler()


_eksik = eksikler()
STORE_SKIP = pytest.mark.skipif(
    bool(_eksik),
    reason=(
        "canonical mağaza EKSİK — " + ", ".join(_eksik) + " yok. "
        "Bu testler yerelde üretilmiş bir mağaza ister; temiz klonda/CI'da "
        "atlanırlar. (H59: eskiden yalnız person/ sorulurdu ve H49 person'ı "
        "depoya alınca kapı yanlış karar verip CI'yı 7 gün kırmızı tuttu.)"
    ),
)
