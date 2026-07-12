"""H10 Stage 1 — Tier-2 fuzzy resolver tests (fixture index; no live store).

Builds a tiny throwaway repo (3 synthetic persons + 1 place), indexes it with
the real build_lookup.py, then exercises the blocking+similarity path:
match / review / new decisions, the name-only auto-match guard, the hard
year-block, review-queue JSONL, and weight renormalization.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402

rapidfuzz = pytest.importorskip("rapidfuzz")


def _person(pid, tr, ar=None, death_ce=None, alt_tr=None):
    rec = {"@id": pid, "@type": ["iac:Person"],
           "labels": {"prefLabel": {"tr": tr}},
           "provenance": {"derived_from": [{"source_id": f"fix:{pid[-3:]}"}]}}
    if ar:
        rec["labels"]["prefLabel"]["ar"] = ar
    if alt_tr:
        rec["labels"]["altLabel"] = {"tr": alt_tr}
    if death_ce:
        rec["death_temporal"] = {"start_ce": death_ce}
    return rec


@pytest.fixture(scope="module")
def fixture_repo(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("resolver_repo")
    person_dir = tmp / "data" / "canonical" / "person"
    place_dir = tmp / "data" / "canonical" / "place"
    person_dir.mkdir(parents=True)
    place_dir.mkdir(parents=True)

    persons = [
        _person("iac:person-00000001", "Gazzâlî", ar="الغزالي", death_ce=1111,
                alt_tr=["Ebû Hâmid el-Gazzâlî", "İmam Gazali"]),
        # namesake, 3 centuries later — the hard year-block target
        _person("iac:person-00000002", "Gazzâlî (Şair)", death_ce=1450),
        _person("iac:person-00000003", "İbn Sînâ", ar="ابن سينا", death_ce=1037),
    ]
    for p in persons:
        (person_dir / f"iac_person_{p['@id'].rsplit('-', 1)[1]}.json").write_text(
            json.dumps(p, ensure_ascii=False), encoding="utf-8")

    place = {"@id": "iac:place-00000010", "@type": ["iac:Place"],
             "labels": {"prefLabel": {"tr": "Haleb", "en": "Aleppo"}},
             "coords": {"lat": 36.2, "lon": 37.16},
             "provenance": {"derived_from": [{"source_id": "fix:aleppo"}]}}
    (place_dir / "iac_place_00000010.json").write_text(
        json.dumps(place, ensure_ascii=False), encoding="utf-8")

    # Index with the REAL builder (its @id-derived entity_type + person
    # death_temporal bracket fixes are part of what we're locking).
    import shutil
    shutil.copytree(REPO / "pipelines", tmp / "pipelines")
    r = subprocess.run([sys.executable, str(tmp / "pipelines/_index/build_lookup.py"),
                        "--quiet"], cwd=tmp, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp


@pytest.fixture()
def resolver(fixture_repo):
    r = EntityResolver(fixture_repo)
    yield r
    r.close()


def _resolve(resolver, rid, **kw):
    return resolver.resolve(entity_type=kw.pop("entity_type", "person"),
                            adapter_id="t2test", extracted_record_id=rid, **kw)


def test_match_name_plus_year(resolver):
    """Diacritic-fold variant + close death year → tier-2 auto-match at the
    calibrated 0.95 person threshold."""
    d = _resolve(resolver, "m1",
                 labels={"prefLabel": {"tr": "Gazzali"}},   # â/î folded away
                 temporal={"start_ce": 1111})
    assert d.kind == "match" and d.matched_pid == "iac:person-00000001"
    assert d.tier == 2 and d.confidence >= 0.95
    assert "temporal" in d.feature_scores and "label" in d.feature_scores


def test_distant_translit_variant_lands_in_review(resolver):
    """'Ebu Hamid Gazali' vs stored 'Gazzâlî' (+alt 'Ebû Hâmid el-Gazzâlî'):
    single-z/double-z token mismatch keeps the score under the calibrated
    0.95 auto bar → review, with the right candidate on the list. This is
    the intended behavior, not a miss — the calibration showed 0.90-0.95
    autos carry real namesake errors; the human lane decides here."""
    d = _resolve(resolver, "m1b",
                 labels={"prefLabel": {"tr": "Ebu Hamid Gazali"}},
                 temporal={"start_ce": 1111})
    assert d.kind == "review", (d.kind, d.confidence)
    assert any(c.pid == "iac:person-00000001" for c in d.candidates)


def test_name_only_never_auto_matches(resolver):
    """North-Star guard: a perfect name with NO corroborating feature caps at
    review — namesakes are the norm in this corpus."""
    d = _resolve(resolver, "m2", labels={"prefLabel": {"ar": "ابن سينا"}})
    assert d.kind == "review", (d.kind, d.confidence)
    assert any(c.pid == "iac:person-00000003" for c in d.candidates)
    assert d.queue_id is not None


def test_hard_year_block_suppresses_namesake(resolver):
    """Same surname, 339 years apart → the 1450 namesake must not win."""
    d = _resolve(resolver, "m3",
                 labels={"prefLabel": {"tr": "Gazzâlî"}},
                 temporal={"start_ce": 1111})
    if d.kind == "match":
        assert d.matched_pid == "iac:person-00000001"
    assert all(c.pid != "iac:person-00000002" or c.score < 0.7
               for c in d.candidates)


def test_unrelated_name_is_new(resolver):
    d = _resolve(resolver, "m4",
                 labels={"prefLabel": {"tr": "Tamamen Bambaşka Birisi"}},
                 temporal={"start_ce": 1111})
    assert d.kind == "new"


def test_place_spatial_signal(resolver):
    """Place: name + coords within a few km → two features → can auto-match."""
    d = _resolve(resolver, "m5", entity_type="place",
                 labels={"prefLabel": {"en": "Aleppo"}},
                 coords={"lat": 36.21, "lon": 37.15})
    assert d.kind == "match" and d.matched_pid == "iac:place-00000010"
    assert "spatial" in d.feature_scores


def test_review_queue_written(resolver, fixture_repo):
    d = _resolve(resolver, "m6", labels={"prefLabel": {"tr": "İbn Sina"}})
    assert d.kind == "review"
    queue = fixture_repo / "data" / "review_queue" / "t2test.jsonl"
    assert queue.exists()
    entries = [json.loads(l) for l in queue.read_text(encoding="utf-8").splitlines()]
    assert any(e["queue_id"] == d.queue_id and e["candidates"] for e in entries)


def test_weight_renormalization():
    """Missing features must renormalize away, not dilute the score."""
    score_full, n_full = EntityResolver._weighted_score(
        {"label": 1.0, "temporal": 1.0}, {"w_label": 0.35, "w_temporal": 0.20})
    score_label_only, n_one = EntityResolver._weighted_score(
        {"label": 1.0}, {"w_label": 0.35, "w_temporal": 0.20})
    assert score_full == pytest.approx(1.0) and n_full == 2
    assert score_label_only == pytest.approx(1.0) and n_one == 1


def test_normalize_name_folds():
    n = EntityResolver._normalize_name
    assert n("Gazzâlî") == n("Gazzali")
    assert n("el-Kânûn fi't-Tıb") == n("el Kanun fi t Tib").strip()
    assert n("İbn Sînâ") == "ibn sina"
