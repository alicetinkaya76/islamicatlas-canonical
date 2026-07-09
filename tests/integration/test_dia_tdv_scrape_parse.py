"""H9 Stage 2b — offline parser unit tests for the dia-tdv-scrape adapter.

Runs against SYNTHETIC fixtures (no TDV copyrighted HTML committed; ADR-014).
Real-world selector robustness is validated separately by the 2c live pilot.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines.adapters.dia_tdv_scrape import parse as P  # noqa: E402

FIX = REPO / "pipelines" / "adapters" / "dia_tdv_scrape" / "tests" / "fixtures"


def _load(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_single_part_fields():
    m = P.parse_madde(_load("fixture_single.html"), "test-single")
    assert m["title_tr"] == "TEST MADDE"
    assert m["title_ar"] == "اختبار"
    assert m["n_parts"] == 1
    p = m["parts"][0]
    assert p["part_id"] == "_1"
    assert p["section_slug"] is None
    assert p["part_index"] == 1 and p["total_parts"] == 1
    assert p["author_raw"] == "AHMET YAZAR"
    assert (p["cilt"], p["sayfa_baslangic"], p["sayfa_bitis"]) == (16, 395, None)
    assert p["baski_yili"] == 1997
    assert "elma armut kiraz" in p["body"]


def test_multi_part_per_section_author():
    m = P.parse_madde(_load("fixture_multi.html"), "test-multi")
    assert m["n_parts"] == 2
    p1, p2 = m["parts"]
    assert p1["part_id"] == "_1" and p1["section_slug"] is None
    assert p1["author_raw"] == "BİRİNCİ YAZAR"
    assert (p1["cilt"], p1["sayfa_baslangic"]) == (1, 535)
    assert p1["part_index"] == 1 and p1["total_parts"] == 2
    assert p2["part_id"] == "_2-ornek-bolum"
    assert p2["section_slug"] == "ornek-bolum"
    assert p2["author_raw"] == "İKİNCİ YAZAR"
    assert (p2["cilt"], p2["sayfa_baslangic"]) == (1, 536)


def test_range_and_missing_arabic():
    m = P.parse_madde(_load("fixture_range.html"), "test-range")
    assert m["title_ar"] is None
    p = m["parts"][0]
    assert (p["cilt"], p["sayfa_baslangic"], p["sayfa_bitis"]) == (2, 40, 42)
    assert p["author_raw"] == "ÜÇÜNCÜ YAZAR"


def test_cilt_sayfa_regex():
    assert P.parse_cilt_sayfa("... 16. cildinde, 395 numaralı sayfada ...") == (16, 395, None)
    assert P.parse_cilt_sayfa("... 2. cildinde, 40-42 numaralı sayfalarda ...") == (2, 40, 42)
    assert P.parse_cilt_sayfa("kaynak yok") == (None, None, None)


def test_section_slug_helper():
    assert P.section_slug_from_part_id("_1") is None
    assert P.section_slug_from_part_id("_2-turk-tarihi") == "turk-tarihi"
    assert P.section_slug_from_part_id("_10-kelam-ilmindeki-yeri") == "kelam-ilmindeki-yeri"
    assert P.section_slug_from_part_id(None) is None


def test_coverage_metric():
    assert P.coverage("elma armut", "elma armut kiraz") == 1.0
    assert P.coverage("", "x") == 0.0
    c = P.coverage("elma armut kiraz", "elma armut")
    assert 0.6 < c < 0.7


def test_madde_body_concat():
    body = P.madde_body(P.parse_madde(_load("fixture_multi.html"), "test-multi"))
    assert "birinci bölüm" in body and "ikinci bölüm" in body


def test_verify_review_flags_are_title_and_coverage():
    m = P.parse_madde(_load("fixture_single.html"), "test-single")
    ok = P.verify(m, "TEST MADDE", "اختبار", "elma armut kiraz vişne")
    assert ok["h1_match"] is True and ok["ar_match"] is True
    assert ok["coverage"] >= 0.95 and ok["flags"] == []

    bad = P.verify(m, "BAŞKA MADDE", "خطأ", "tamamen alakasiz kelimeler burada")
    assert "title_mismatch" in bad["flags"] and "low_coverage" in bad["flags"]
    assert "arabic_mismatch" not in bad["flags"]     # arabic is advisory (2d.1)
    assert bad["ar_match"] is False


def test_arabic_mismatch_is_advisory_not_review():
    """h1 + coverage confirm identity → a differently-normalized Arabic title
    (definite article + hamza, as in the live dia_chunks `a`) is NOT review."""
    m = P.parse_madde(_load("fixture_single.html"), "test-single")  # title_ar='اختبار'
    v = P.verify(m, "TEST MADDE", "الاختبار", "elma armut kiraz vişne")
    assert v["flags"] == []
    assert v["ar_match"] is True                      # rasm folds the ال


def test_rasm_and_arabic_matches():
    assert P.rasm("الْعَبَّاس") == P.rasm("عباس")        # harakat + definite article
    assert P.rasm("أحمد") == P.rasm("احمد")             # hamza fold
    assert P.arabic_matches("العبّاس بن أحمد", "عباس بن احمد")
    assert not P.arabic_matches("عباس", "محمد")
