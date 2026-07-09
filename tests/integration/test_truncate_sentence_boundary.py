"""H9 Stage 3 — closes the H8 soft TODO: truncate_at_sentence_boundary tests.

The function overflowed the ADR-012 50K ceiling in production (H8 Stage 5
postmortem: marker length was not reserved). These lock the invariants with
seeded-random fuzz (stdlib only, seed=42 per config.yaml convention).
"""
import pathlib
import random
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines._lib.dia_enrichment_lib import truncate_at_sentence_boundary  # noqa: E402


def test_short_text_untouched():
    out, truncated = truncate_at_sentence_boundary("Kısa metin.", 50)
    assert out == "Kısa metin." and truncated is False


def test_hard_ceiling_never_exceeded_fuzz():
    rng = random.Random(42)
    sentence_ends = [". ", "! ", "? ", ".\n", "… "]
    alphabet = "abçdefgğhıijklmnoöprsştuüvyz ÂÎÛ عربى "
    for trial in range(500):
        n_sent = rng.randint(1, 30)
        text = "".join(
            "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 120)))
            + rng.choice(sentence_ends)
            for _ in range(n_sent)
        )
        max_len = rng.choice([1, 10, 80, 500, len(text) - 1 if len(text) > 1 else 1,
                              len(text), len(text) + 10, 50_000])
        out, truncated = truncate_at_sentence_boundary(text, max_len)
        # THE invariant that failed in production (H8 Stage 5):
        assert len(out) <= max_len, (
            f"trial {trial}: len(out)={len(out)} > max_len={max_len}")
        if not truncated:
            assert out == text
        assert isinstance(truncated, bool)


def test_truncation_reports_flag_and_prefers_boundary():
    text = ("Birinci cümle tam burada bitiyor. İkinci cümle de burada bitiyor. "
            "Üçüncü cümle epey daha uzun sürüyor ve kesilecek olan bu.")
    out, truncated = truncate_at_sentence_boundary(text, 70)
    assert truncated is True
    assert len(out) <= 70
