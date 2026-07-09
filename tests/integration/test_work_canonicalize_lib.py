"""H9 Stage 3 — locks for the AP-prep library fixes (no canonical store needed).

Covers: title fingerprint symmetry (w/v drop, Arabic stopword order),
build_work_type_array vs the frozen v0.3.0 enum, the ADR-009 rich-mint gate,
and PidMinter's batch session API.
"""
import json
import pathlib
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pipelines._lib import work_canonicalize as wc  # noqa: E402
from pipelines._lib.pid_minter import PidMinter, PidMinterError  # noqa: E402


# ---- title fingerprint ------------------------------------------------------

@pytest.mark.parametrize("a,b", [
    ("al-Qānūn fī al-Ṭibb", "el-Kânûn fi't-Tıb"),
    ("Kitāb al-Ḥayawān", "Kitabu'l-Hayevan"),          # w/v symmetry (Stage 3 fix)
    ("Wafayāt al-aʿyān", "Vefeyâtü'l-a'yân"),           # w↔v in Turkish translit
    ("Khwarizmi Cebir", "Hârizmî Cebir"),               # kh + w-drop still folds
])
def test_fingerprint_translit_pairs_match(a, b):
    fa, fb = wc.title_fingerprint(a), wc.title_fingerprint(b)
    assert fa and fa == fb, (
        f"{a!r} -> {wc.normalize_title_for_fingerprint(a)!r} vs "
        f"{b!r} -> {wc.normalize_title_for_fingerprint(b)!r}")


def test_fingerprint_distinct_titles_stay_distinct():
    assert wc.title_fingerprint("Kitāb al-Ḥayawān") != wc.title_fingerprint("al-Qānūn fī al-Ṭibb")


def test_fingerprint_arabic_stopword_not_garbage():
    # "في" is a stopword; the pre-fix code prefix-stripped it to "ي" and kept it.
    norm = wc.normalize_title_for_fingerprint("القانون في الطب")
    assert "ي" not in norm.split(), norm
    assert wc.normalize_title_for_fingerprint("في") == ""


# ---- @type array vs frozen v0.3.0 enum -------------------------------------

def _schema_type_enum():
    schema = json.loads((REPO / "schemas" / "work.schema.json").read_text(encoding="utf-8"))
    return set(schema["properties"]["@type"]["items"]["enum"]), \
        schema["properties"]["@type"].get("maxItems", 99)


def test_work_subtypes_match_schema_enum():
    enum, _ = _schema_type_enum()
    assert wc.WORK_SUBTYPES == enum, (
        f"WORK_SUBTYPES drifted from schema enum: "
        f"only-in-lib={sorted(wc.WORK_SUBTYPES - enum)} "
        f"only-in-schema={sorted(enum - wc.WORK_SUBTYPES)}")
    assert set(wc._SUBJECT_TO_SUBTYPE.values()) <= enum


def test_build_work_type_array_respects_enum_and_cap():
    enum, max_items = _schema_type_enum()
    out = wc.build_work_type_array(["hadith", "history", "tafsir", "poetry"])
    assert "iac:Work" in out and len(out) <= max_items
    assert set(out) <= enum
    # no subjects → base only; unknown subject ignored
    assert wc.build_work_type_array() == ["iac:Work"]
    assert wc.build_work_type_array(["astronomy-unknown"]) == ["iac:Work"]
    # extra_subtypes outside the enum are dropped, inside are kept
    out = wc.build_work_type_array(extra_subtypes=["iac:Sira", "iac:NotAClass"])
    assert out == ["iac:Sira", "iac:Work"] or out == ["iac:Work", "iac:Sira"]


# ---- ADR-009 rich-mint gate --------------------------------------------------

def _rich_record(**over):
    rec = {
        "labels": {
            "prefLabel": {"tr": "Kitâbü'l-Hiyel", "ar": "كتاب الحيل"},
            "description": {"tr": "Hanefî fıkhında hiyel literatürünün ilk örneği."},
        },
        "provenance": {"derived_from": [
            {"source_id": "dia-rich:hassaf", "page_or_locator": "TDV DiA cilt 16 s. 395"},
        ]},
    }
    rec.update(over)
    return rec


def test_adr009_gate_passes_rich_record():
    assert wc.adr009_rich_gate(_rich_record()) == []


def test_adr009_gate_accepts_dated_web_locator():
    rec = _rich_record(provenance={"derived_from": [
        {"page_or_locator": "https://islamansiklopedisi.org.tr/muneccimbasi (erişim 2026-07-06 / Erişim Tarihi 2026)"},
    ]})
    assert wc.adr009_rich_gate(rec) == []


def test_adr009_gate_flags_each_threshold():
    single_lang = _rich_record(labels={
        "prefLabel": {"tr": "X"}, "description": {"tr": "y"}})
    assert any("adr009(a)" in f for f in wc.adr009_rich_gate(single_lang))

    no_desc = _rich_record(labels={
        "prefLabel": {"tr": "X", "ar": "س"}, "description": {}})
    assert any("adr009(b)" in f for f in wc.adr009_rich_gate(no_desc))

    no_loc = _rich_record(provenance={"derived_from": [
        {"page_or_locator": "(unavailable: see H9 scraping)"}]})
    assert any("adr009(c)" in f for f in wc.adr009_rich_gate(no_loc))


# ---- PidMinter batch session --------------------------------------------------

def test_pid_session_identical_semantics_and_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        a = m.mint("work", "x:1")                      # per-call path
        with m.session():
            b = m.mint("work", "x:2")
            assert m.mint("work", "x:1") == a          # idempotent inside session
            assert m.lookup("work", "x:2") == b
        m2 = PidMinter(tmp)                            # fresh instance: state persisted?
        assert m2.lookup("work", "x:2") == b
        assert m2.mint("work", "x:3") == "iac:work-00000003"


def test_pid_session_does_not_nest():
    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        with m.session():
            with pytest.raises(PidMinterError):
                with m.session():
                    pass


def test_pid_session_persists_on_exception():
    """Review-proven failure mode: allocations from a crashed session MUST
    survive — the caller may already have written records with those PIDs;
    losing them would let the next run reissue the ordinal to another entity."""
    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        with pytest.raises(RuntimeError, match="boom"):
            with m.session():
                minted = m.mint("work", "x:1")
                raise RuntimeError("boom")
        m2 = PidMinter(tmp)
        assert m2.lookup("work", "x:1") == minted          # allocation survived
        assert m2.mint("work", "x:2") == "iac:work-00000002"  # no ordinal reuse


def test_pid_session_stats_no_deadlock():
    """stats() inside an open session used to re-acquire flock on a new fd →
    self-deadlock. Must return the in-session view instead."""
    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        with m.session():
            m.mint("work", "x:1")
            assert m.stats().get("work") == 1              # returns, no hang


def test_pid_session_readonly_block_writes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        m.mint("work", "x:1")
        mtime = (pathlib.Path(tmp) / "pid_index.json").stat().st_mtime_ns
        with m.session():
            m.lookup("work", "x:1")                    # reads only
        assert (pathlib.Path(tmp) / "pid_index.json").stat().st_mtime_ns == mtime
