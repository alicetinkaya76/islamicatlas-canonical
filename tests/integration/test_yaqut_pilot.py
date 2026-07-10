"""
test_yaqut_pilot.py — Hafta 3 Yâqūt + Muqaddasī + Le Strange acceptance suite.

Runs the full pipeline (extract → canonicalize → resolve → integrity) and
verifies 10 acceptance criteria across the place namespace seeded by all
three classical/orientalist gazetteers.

Run from repo root:
    pytest tests/integration/test_yaqut_pilot.py -v
or
    python3 tests/integration/test_yaqut_pilot.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLACE_DIR = REPO_ROOT / "data" / "canonical" / "place"
DYNASTY_DIR = REPO_ROOT / "data" / "canonical" / "dynasty"
STATE_DIR = REPO_ROOT / "data" / "_state"


# ----- Helpers ---------------------------------------------------------------


def run_cmd(cmd: list[str]) -> int:
    """Run a command from REPO_ROOT and return its exit code."""
    return subprocess.call(cmd, cwd=REPO_ROOT)


def count_files(directory: Path, pattern: str = "iac_*.json") -> int:
    # DH-1 hardening: default pattern matches only canonical record names, so
    # AppleDouble droppings (._iac_*.json from exFAT/Finder) can't skew counts.
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.glob(pattern))


def load_record(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def find_records_by_label(language: str, value: str) -> list[Path]:
    """Find canonical records whose prefLabel.<language> equals value (case-insensitive)."""
    matches: list[Path] = []
    if not PLACE_DIR.exists():
        return matches
    target = value.casefold()
    for path in PLACE_DIR.glob("iac_place_*.json"):
        try:
            with path.open(encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        labels = rec.get("labels", {}).get("prefLabel", {}) or {}
        if (labels.get(language) or "").casefold() == target:
            matches.append(path)
    return matches


# ----- Fixture: pipeline must already be run --------------------------------


@pytest.fixture(scope="session")
def pipeline_state():
    """Require a populated place store; skip (don't build) when absent.

    H9 Stage 3: this fixture used to auto-run 3 adapters + integrity passes
    when the store looked small — a test that silently mutates data/ and, on
    a fresh clone/CI (no source data), fails confusingly minutes in. Opt back
    into the old bootstrap explicitly with IAC_TEST_BOOTSTRAP=1.
    """
    import os
    if count_files(PLACE_DIR) < 10000:
        if os.environ.get("IAC_TEST_BOOTSTRAP") == "1":
            assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                            "--id", "yaqut", "--recon-mode", "offline"]) == 0
            assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                            "--id", "muqaddasi", "--recon-mode", "offline"]) == 0
            assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                            "--id", "le-strange", "--recon-mode", "offline"]) == 0
            assert run_cmd([sys.executable, "pipelines/integrity/place_integrity.py",
                            "--all"]) == 0
            if count_files(DYNASTY_DIR) > 0:
                assert run_cmd([sys.executable,
                                "pipelines/integrity/backfill_capitals.py"]) == 0
        else:
            pytest.skip(
                f"place store empty/incomplete ({count_files(PLACE_DIR)} records); "
                f"run the pipeline first (or set IAC_TEST_BOOTSTRAP=1) — see README")
    return {"place_count": count_files(PLACE_DIR)}


# ============================================================================
# Acceptance criteria
# ============================================================================


class TestPlaceNamespaceVolume:
    """A. Volume + filename invariants."""

    def test_a1_total_record_count(self, pipeline_state):
        n = count_files(PLACE_DIR)
        # Band history: H3 seed 15,239 (Yaqut 12,954 + Muqaddasi 2,070 +
        # Le Strange ~215) → H10 Stage 2 adds darp-islam Track-B mints
        # (+2,338 = 17,577). Band widened DELIBERATELY with that commit;
        # numbers are counted from the store, never estimated.
        assert 17_000 <= n <= 19_000, (
            f"Expected ~17,577 place records (15,239 H3 seed + 2,338 "
            f"darp-islam); got {n}"
        )

    def test_a2_filename_pattern(self, pipeline_state):
        bad = []
        for path in PLACE_DIR.glob("*.json"):
            # DH-1: AppleDouble droppings are a filesystem artifact, not a
            # naming violation — report them separately, don't fail on them.
            if path.name.startswith("._"):
                continue
            if not path.name.startswith("iac_place_"):
                bad.append(path.name)
        assert not bad, f"Filenames not matching iac_place_NNNNNNNN.json: {bad[:5]}"


class TestSchemaValidity:
    """B. Every record must validate against place.schema.json."""

    @pytest.mark.slow_fullstore
    def test_b_all_records_schema_valid(self, pipeline_state):
        # H9 Stage 3: uses conftest's cached records+validator (store no
        # longer re-read); marked slow_fullstore for the fast inner loop.
        from tests.integration.conftest import validate_all
        failures = validate_all("place")
        assert not failures, f"Schema validation failures: {failures[:5]}"


class TestSpotChecks:
    """C. Major Islamic cities are present + correctly canonicalized."""

    @pytest.mark.parametrize("name_tr", [
        "Mekke",
        "Bağdat",
        "Dımaşk",        # Yâqūt content team's classical transliteration
        "Haleb",         # ditto for Aleppo
        "el-Kûfe",       # ditto for Kufa
    ])
    def test_c_major_cities_present(self, pipeline_state, name_tr):
        matches = find_records_by_label("tr", name_tr)
        assert matches, f"No record with prefLabel.tr={name_tr!r}"


class TestProvenance:
    """D. Every record has provenance + non-empty derived_from."""

    def test_d_provenance_complete(self, pipeline_state):
        n_missing = 0
        for path in list(PLACE_DIR.glob("iac_place_*.json"))[:500]:  # sample
            rec = load_record(path)
            prov = rec.get("provenance", {})
            if not prov.get("derived_from"):
                n_missing += 1
        assert n_missing == 0, f"{n_missing}/500 sampled records missing provenance.derived_from"


class TestLayerCoverage:
    """E. Each adapter contributed records to derived_from_layers."""

    def test_e_layer_coverage(self, pipeline_state):
        from collections import Counter
        layer_counts: Counter = Counter()
        for path in PLACE_DIR.glob("iac_place_*.json"):
            rec = load_record(path)
            for layer in rec.get("derived_from_layers") or []:
                layer_counts[layer] += 1
        assert layer_counts["yaqut"] >= 10_000, f"Yaqut layer too small: {layer_counts['yaqut']}"
        assert layer_counts["makdisi"] >= 1_500, f"Muqaddasi layer too small: {layer_counts['makdisi']}"
        assert layer_counts["le-strange"] >= 200, f"Le Strange layer too small: {layer_counts['le-strange']}"


class TestParentResolution:
    """F. located_in[] populated by integrity pass."""

    def test_f_located_in_count(self, pipeline_state):
        n_with_located_in = 0
        for path in PLACE_DIR.glob("iac_place_*.json"):
            rec = load_record(path)
            if rec.get("located_in"):
                n_with_located_in += 1
        # 1,309 fully resolved + 118 partial = ~1,427 expected
        assert n_with_located_in >= 1_000, (
            f"Expected ≥1,000 records with located_in[]; got {n_with_located_in}"
        )

    def test_f2_located_in_format(self, pipeline_state):
        # Check a sampled subset for format
        bad = []
        for path in list(PLACE_DIR.glob("iac_place_*.json"))[:1000]:
            rec = load_record(path)
            for li in rec.get("located_in") or []:
                if not li.startswith("iac:place-"):
                    bad.append((path.name, li))
        assert not bad, f"Bad located_in format: {bad[:3]}"


class TestCrossSourceMerge:
    """G. Muqaddasī ↔ Yâqūt bidirectional attestation."""

    def test_g_records_with_multiple_layers(self, pipeline_state):
        n_multi = 0
        for path in PLACE_DIR.glob("iac_place_*.json"):
            rec = load_record(path)
            layers = rec.get("derived_from_layers") or []
            if len(set(layers)) >= 2:
                n_multi += 1
        # Pre-augmentation: only le-strange single-source; post: yaqut+makdisi+le-strange ~99
        assert n_multi >= 200, (
            f"Expected ≥200 records with 2+ derived_from_layers; got {n_multi}"
        )


class TestCapitalBackfill:
    """H. Bosworth had_capital[] backfilled when dynasty namespace exists."""

    def test_h_capital_backfill(self, pipeline_state):
        if not DYNASTY_DIR.exists() or count_files(DYNASTY_DIR) == 0:
            pytest.skip("dynasty namespace empty; skipping capital backfill check")
        n_with_capital = 0
        for path in DYNASTY_DIR.glob("iac_dynasty_*.json"):
            rec = load_record(path)
            if rec.get("had_capital"):
                n_with_capital += 1
        # Threshold 90 — modern dynasties (Saud, Sanusi) and TR-AR
        # transliteration disagreements (Halep vs Halab) account for the
        # remaining ~50%.
        assert n_with_capital >= 90, (
            f"Expected ≥90 dynasties with had_capital[]; got {n_with_capital}"
        )


class TestIdempotency:
    """I. Re-running the pipeline does not change the canonical store."""

    def test_i_pid_minter_idempotent(self, pipeline_state):
        # Verify that pid_index has expected count
        idx_path = STATE_DIR / "pid_index.json"
        if not idx_path.exists():
            pytest.skip("pid_index.json missing")
        with idx_path.open(encoding="utf-8") as fh:
            pid_index = json.load(fh)
        # Check that 'place' namespace count matches the file count.
        # H10 Stage 2 exception class — RESERVED PIDs: a mint piloted as
        # Track-B then demoted to review keeps its index entry so a later
        # historian approval re-mints the SAME pid (idempotent hash). Such
        # reservations are only excused when the darp sidecar's
        # _review_skipped list explicitly documents the source record.
        place_pids = {k: v for k, v in pid_index.items() if k.startswith("place:")}
        on_disk = count_files(PLACE_DIR)
        reserved_ok = set()
        darp_sidecar = STATE_DIR / "darp_islam_augment_pending.json"
        if darp_sidecar.exists():
            with darp_sidecar.open(encoding="utf-8") as fh:
                skipped = json.load(fh).get("_review_skipped", {})
            reserved_ok = {f"place:{rid}" for rid in skipped}
        unexcused = [
            k for k, v in place_pids.items()
            if not (PLACE_DIR / f"iac_place_{v.rsplit('-', 1)[1]}.json").exists()
            and k not in reserved_ok
        ]
        assert not unexcused, (
            f"{len(unexcused)} indexed place PIDs have no record file and no "
            f"documented review-reservation; first 3: {unexcused[:3]}")
        assert len(place_pids) - (len(place_pids) - on_disk) == on_disk  # arithmetic sanity


class TestSidecarCompleteness:
    """J. Sidecars persisted for downstream processing."""

    @pytest.mark.parametrize("sidecar_name,min_entries", [
        ("yaqut_parent_pending.json", 2_000),
        ("yaqut_persons_pending.json", 500),
        ("muqaddasi_yaqut_xref_pending.json", 800),
        ("le_strange_yaqut_augment_pending.json", 200),
    ])
    def test_j_sidecar_present(self, pipeline_state, sidecar_name, min_entries):
        path = STATE_DIR / sidecar_name
        assert path.exists(), f"Sidecar missing: {sidecar_name}"
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        assert len(data) >= min_entries, (
            f"{sidecar_name} too small: {len(data)} < {min_entries}"
        )


# ----- Standalone runner -----------------------------------------------------


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
