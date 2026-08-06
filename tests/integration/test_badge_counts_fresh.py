"""Rozet sayıları KAYNAK DOSYALARIYLA tutmalı (H58).

NEDEN VAR — sessiz bir yalan altı rozette bir haftadan uzun yaşadı:

    H49/H50 kimlik birleştirmesi 1.364 kaydı yumuşak-sildi (havuz
    22.824 → 21.460). `build_source_counts.py` bu sayıları üretiyor ama
    ZİNCİR DIŞINDAYDI ve kimse yeniden koşturmadı. Sonuç: 30 Temmuz'dan
    2026-08-06'ya kadar ekranda

        Havuz rozeti  22.824   ↔   havuz listesi  21.460

    aynı ekranda yan yana duruyordu. Şişik olan yalnız havuz değildi:

        alam       13.844 → 12.833
        dia         8.491 →  8.186
        ei1         7.538 →  7.498
        scholarnet  3.393 →  3.266   (kenar 7.869 → 7.457)
        ulemapool  22.824 → 21.460

    H55'te `ZINCIR_DISI` listesine "zincire alınırsa kaynak ağacı kirlenir"
    gerekçesiyle YAZMIŞTIM. Gerekçe doğruydu ama TARTIYI YANLIŞ KURMUŞUM:
    dosyanın değişmesi kirlilik değil, mağaza değiştiğinde OLMASI GEREKEN
    şeydir. Bayatlama maliyeti daha ağır çıktı; üretici zincire alındı.

Bu kapı sayıyı KAYNAĞINDAN yeniden ölçer ve rozetle karşılaştırır. Üretici
koşturulmayı unutulursa test kızarır — insanın gözüne değil, kapıya kalır.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COUNTS = REPO / "web" / "src" / "data" / "source_counts.json"

# rozet anahtarı → (kaynak dosya, o dosyadan sayıyı çıkaran fonksiyon)
KAYNAK = {
    "ulemapool": ("web/public/books/ulema_pool.json",
                  lambda d: d.get("n") or len(d.get("kisiler") or [])),
    "alam": ("web/public/view-data/alam_lite.json",
             lambda d: len(d if isinstance(d, list) else (d.get("records") or []))),
    "dia": ("web/public/view-data/dia_lite.json",
            lambda d: len(d if isinstance(d, list) else (d.get("records") or []))),
    "ei1": ("web/public/view-data/ei1_lite.json",
            lambda d: len(d if isinstance(d, list) else (d.get("records") or []))),
}
# Küçük sapmalar bile gizlenmemeli: bu sayılar TAM olmalı.
TOLERANS = 0


@pytest.fixture(scope="module")
def rozet():
    if not COUNTS.is_file():
        pytest.skip("source_counts.json yok")
    d = json.loads(COUNTS.read_text(encoding="utf-8"))
    for k in ("counts", "sources", "detail"):
        if isinstance(d.get(k), dict):
            return d[k]
    return d


def _oku(rel):
    p = REPO / rel
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@pytest.mark.parametrize("anahtar", sorted(KAYNAK))
def test_rozet_kaynagiyla_tutuyor(rozet, anahtar):
    rel, cikar = KAYNAK[anahtar]
    d = _oku(rel)
    if d is None:
        pytest.skip(f"{rel} yok (gitignored katman olabilir)")
    gercek = cikar(d)
    kayitli = (rozet.get(anahtar) or {}).get("count")
    assert kayitli is not None, f"'{anahtar}' rozeti source_counts'ta yok"
    assert abs(kayitli - gercek) <= TOLERANS, (
        f"'{anahtar}' rozeti BAYAT: ekranda {kayitli:,} ↔ kaynakta {gercek:,}. "
        f"`python3 pipelines/frontend/build_source_counts.py` koşturun."
    ).replace(",", ".")


def test_uretici_zincirde():
    """Bayatlamanın KÖK NEDENİ zincir dışı kalmasıydı."""
    metin = ""
    for p in (REPO / "Makefile", REPO / "scripts" / "start_local.sh"):
        if p.is_file():
            metin += p.read_text(encoding="utf-8")
    assert "build_source_counts.py" in metin, (
        "build_source_counts.py zincirde değil — H58'de tam bu yüzden altı "
        "rozet bir haftadan uzun şişik kaldı"
    )


def test_havuz_rozeti_liste_ile_celismiyor():
    """Aynı ekranda rozet 22.824, liste 21.460 diyordu — en görünür belirti."""
    pool = _oku("web/public/books/ulema_pool.json")
    if pool is None:
        pytest.skip("ulema_pool.json yok")
    n_alan = pool.get("n")
    n_liste = len(pool.get("kisiler") or [])
    assert n_alan == n_liste, (
        f"havuz dosyasının kendi içinde çelişki: n={n_alan}, liste={n_liste}"
    )
