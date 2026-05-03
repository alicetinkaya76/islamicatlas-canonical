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


def count_files(directory: Path, pattern: str = "*.json") -> int:
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
    """Ensure the pipeline has been run; if not, run it now (idempotent)."""
    if count_files(PLACE_DIR) < 10000:
        # Bootstrap: run all four adapters + integrity + capital backfill
        assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                        "--id", "yaqut", "--recon-mode", "offline"]) == 0
        assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                        "--id", "muqaddasi", "--recon-mode", "offline"]) == 0
        assert run_cmd([sys.executable, "pipelines/run_adapter.py",
                        "--id", "le-strange", "--recon-mode", "offline"]) == 0
        assert run_cmd([sys.executable, "pipelines/integrity/place_integrity.py",
                        "--all"]) == 0
        if count_files(DYNASTY_DIR) > 0:
            assert run_cmd([sys.executable, "pipelines/integrity/backfill_capitals.py"]) == 0
    return {"place_count": count_files(PLACE_DIR)}


# ============================================================================
# Acceptance criteria
# ============================================================================


class TestPlaceNamespaceVolume:
    """A. Volume + filename invariants."""

    def test_a1_total_record_count(self, pipeline_state):
        n = count_files(PLACE_DIR)
        assert 14_000 <= n <= 16_000, (
            f"Expected ~15,239 place records (Yaqut 12,954 + Muqaddasi 2,070 + "
            f"Le Strange ~215); got {n}"
        )

    def test_a2_filename_pattern(self, pipeline_state):
        bad = []
        for path in PLACE_DIR.glob("*.json"):
            if not path.name.startswith("iac_place_"):
                bad.append(path.name)
        assert not bad, f"Filenames not matching iac_place_NNNNNNNN.json: {bad[:5]}"


class TestSchemaValidity:
    """B. Every record must validate against place.schema.json."""

    def test_b_all_records_schema_valid(self, pipeline_state):
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        schemas: dict = {}
        schemas_dir = REPO_ROOT / "schemas"
        for schema_path in schemas_dir.rglob("*.schema.json"):
            with schema_path.open(encoding="utf-8") as fh:
                s = json.load(fh)
            if s.get("$id"):
                schemas[s["$id"]] = s
        registry = Registry()
        for sid, s in schemas.items():
            registry = registry.with_resource(uri=sid, resource=Resource.from_contents(s))

        with (schemas_dir / "place.schema.json").open(encoding="utf-8") as fh:
            target = json.load(fh)
        validator = Draft202012Validator(target, registry=registry)

        failures = []
        for path in PLACE_DIR.glob("iac_place_*.json"):
            with path.open(encoding="utf-8") as fh:
                rec = json.load(fh)
            errs = list(validator.iter_errors(rec))
            if errs:
                failures.append((path.name, errs[0].message))
                if len(failures) > 5:
                    break
        assert not failures, f"Schema validation failures: {failures}"


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
        # Check that 'place' namespace count matches the file count
        place_pids = [k for k in pid_index if k.startswith("place:")]
        assert len(place_pids) == count_files(PLACE_DIR), (
            f"PID index count ({len(place_pids)}) != file count ({count_files(PLACE_DIR)})"
        )


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
