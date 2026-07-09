"""H9 Stage 3 — invariants of dia_chunks_rich.json, AP's (H10+) sole input.

The file is gitignored/regenerable (scrape.py --assemble), so every test
skips cleanly when it is absent (fresh clone / CI). Against a real assembly
these lock the AO acceptance numbers and the ADR-014 §4 body-free guarantee.
"""
import json
import pathlib

import pytest

RICH = pathlib.Path(__file__).resolve().parents[2] / "data" / "sources" / "dia_chunks_rich.json"

pytestmark = pytest.mark.skipif(
    not RICH.exists(),
    reason="dia_chunks_rich.json not assembled (gitignored; scrape.py --assemble)",
)


@pytest.fixture(scope="module")
def rich():
    with RICH.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_rich_meta_and_count(rich):
    assert rich["_meta"]["adapter"] == "dia-tdv-scrape"
    assert rich["_meta"]["compliance"] == "ADR-014"
    # AO acceptance: one record per distinct dia_chunks slug.
    assert rich["_meta"]["n_records"] == len(rich["records"]) == 8093


def test_rich_is_body_free(rich):
    """ADR-014 §4: no scraped narrative text is redistributed."""
    for slug, rec in rich["records"].items():
        for part in rec.get("parts", []):
            assert "body" not in part, f"{slug}: part carries scraped body text"


def test_rich_coverage_floors(rich):
    """Locks the measured AO outcomes (H9 Stage 2e journal) as floors."""
    recs = rich["records"].values()
    n = len(rich["records"])
    with_cs = sum(1 for r in recs if any(p.get("cilt") for p in r["parts"]))
    with_ar = sum(1 for r in recs if r.get("title_ar"))
    assert with_cs / n >= 0.999, f"cilt+sayfa coverage regressed: {with_cs}/{n}"
    assert 0.60 <= with_ar / n <= 0.75, f"title_ar share off-band: {with_ar}/{n}"


def test_rich_review_flags_are_explicit(rich):
    """Flagged records stay flagged — never silently accepted (North Star)."""
    flagged = {s for s, r in rich["records"].items() if r["verify"]["flags"]}
    assert len(flagged) == rich["_meta"]["n_review_flagged"]
    # The five online-only maddes (no print locator on the live site) must
    # carry no_cilt_sayfa until AP assigns them a web locator.
    for slug in ("muneccimbasi", "rasathane", "tamani-huseyin-rifki",
                 "yahya-b-ebu-kesir", "yahya-yi-sirvani"):
        assert "no_cilt_sayfa" in rich["records"][slug]["verify"]["flags"], slug
