"""H9 Stage 2c — resume + rich-projection unit tests (pure, NO network).

The live pilot's coverage / parse-success stats live in
HAFTA9_STAGE_2c_PILOT.md. These tests lock the invariants that make the bulk
run safe: checkpoint-skip on resume, error retry, and a body-free rich file
(ADR-014 §4 — no scraped body persisted).
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines.adapters.dia_tdv_scrape import scrape as S  # noqa: E402


def test_plan_fetch_skips_completed():
    selected = ["a", "b", "c", "d"]
    progress = {"a": {"status": "ok"}, "b": {"status": "review"},
                "c": {"status": "unchanged"}}
    todo, done = S.plan_fetch(selected, progress)
    assert todo == ["d"]
    assert done == {"a", "b", "c"}


def test_plan_fetch_retries_errors():
    todo, _ = S.plan_fetch(["a", "b"], {"a": {"status": "error"}, "b": {"status": "ok"}})
    assert todo == ["a"]                       # error retried; ok skipped


def test_plan_fetch_refetch_forces_all():
    todo, _ = S.plan_fetch(["a", "b"], {"a": {"status": "ok"}, "b": {"status": "ok"}},
                           refetch=True)
    assert todo == ["a", "b"]


def test_project_rich_lean_and_flags():
    progress = {
        "ok1": {"status": "ok", "fetched_at": "t", "http": 200, "content_sha256": "h",
                "verify": {"coverage": 1.0, "flags": []},
                "extracted": {"title_ar": "x", "n_parts": 1,
                              "parts": [{"part_id": "_1", "cilt": 5,
                                         "sayfa_baslangic": 10, "author_raw": "A"}]}},
        "rev1": {"status": "review", "verify": {"coverage": 0.8, "flags": ["low_coverage"]},
                 "extracted": {"title_ar": None, "n_parts": 1, "parts": []}},
        "err1": {"status": "error", "http": 404},
    }
    rich, n_flagged = S.project_rich(progress)
    assert set(rich) == {"ok1", "rev1"}        # error excluded
    assert n_flagged == 1
    assert rich["ok1"]["parts"][0]["cilt"] == 5
    assert rich["ok1"]["verify"]["flags"] == []
    assert rich["rev1"]["verify"]["flags"] == ["low_coverage"]


def test_record_excludes_body():
    """ADR-014 §4: the scraped narrative body is NEVER persisted."""
    parsed = {"title_tr": "T", "title_ar": "x", "n_parts": 1,
              "parts": [{"part_id": "_1", "part_index": 1, "total_parts": 1,
                         "section_slug": None, "author_raw": "A", "cilt": 1,
                         "sayfa_baslangic": 2, "sayfa_bitis": None, "baski_yili": 1990,
                         "body": "THIS BODY MUST NOT BE PERSISTED"}]}
    verdict = {"coverage": 1.0, "flags": [], "h1_match": True, "ar_match": True}
    rec = S._record("slug", parsed, verdict, 200,
                    {"ETag": "e", "Last-Modified": "lm"}, "sha")
    assert rec["status"] == "ok"
    part = rec["extracted"]["parts"][0]
    assert "body" not in part
    assert part["cilt"] == 1 and part["author_raw"] == "A"
    assert "THIS BODY MUST NOT BE PERSISTED" not in repr(rec)
