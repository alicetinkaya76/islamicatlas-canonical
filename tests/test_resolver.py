#!/usr/bin/env python3
"""
test_resolver.py — Smoke test for the entity resolver + lookup index.

Strategy:
  1. Materialize the existing valid place + dynasty fixtures into a temp repo.
  2. Build the lookup index from those canonical records.
  3. Resolve queries that should hit Tier 1 (Wikidata QID, source CURIE).
  4. Resolve queries that should miss → "new" via Tier 2 stub.
  5. Verify decision cache returns same answer on second call.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402


def setup_temp_repo(tmp: Path) -> None:
    """Mirror minimal repo skeleton + fixtures into tmp."""
    # Copy pipelines + canonicalized fixtures
    shutil.copytree(REPO_ROOT / "pipelines", tmp / "pipelines")

    canonical = tmp / "data" / "canonical"
    (canonical / "place").mkdir(parents=True)
    (canonical / "dynasty").mkdir(parents=True)

    with (REPO_ROOT / "tests/fixtures/valid/place_valid.json").open(encoding="utf-8") as fh:
        place = json.load(fh)
    with (REPO_ROOT / "tests/fixtures/valid/dynasty_valid.json").open(encoding="utf-8") as fh:
        dynasty = json.load(fh)

    pid_p = place["@id"]
    pid_d = dynasty["@id"]
    (canonical / "place" / f"iac_place_{pid_p.split('-')[1]}.json").write_text(
        json.dumps(place, ensure_ascii=False), encoding="utf-8"
    )
    (canonical / "dynasty" / f"iac_dynasty_{pid_d.split('-')[1]}.json").write_text(
        json.dumps(dynasty, ensure_ascii=False), encoding="utf-8"
    )


def build_index(tmp: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(tmp / "pipelines/_index/build_lookup.py"), "--quiet"],
        cwd=tmp,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Index build failed:\n{result.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_repo = Path(tmp)
        setup_temp_repo(tmp_repo)
        build_index(tmp_repo)

        resolver = EntityResolver(tmp_repo)
        results: list[tuple[str, bool, str]] = []

        # ---- Test 1: Tier 1 hit by Wikidata QID (place=Aleppo, Q41183) ----
        try:
            decision = resolver.resolve(
                entity_type="place",
                adapter_id="test",
                extracted_record_id="aleppo-test-1",
                authority_xref=[{"authority": "wikidata", "id": "Q41183"}],
                labels={"prefLabel": {"en": "Aleppo"}},
            )
            assert decision.kind == "match", f"expected match, got {decision.kind}"
            assert decision.matched_pid == "iac:place-00000042", f"matched wrong PID: {decision.matched_pid}"
            assert decision.confidence == 1.0
            assert decision.tier == 1
            results.append(("Tier 1 hit: Wikidata QID Q41183 → Aleppo", True, f"matched {decision.matched_pid}"))
        except AssertionError as e:
            results.append(("Tier 1 hit: Wikidata QID Q41183 → Aleppo", False, str(e)))

        # ---- Test 2: Tier 1 hit by source CURIE (yaqut:7842 → Aleppo) ----
        try:
            decision = resolver.resolve(
                entity_type="place",
                adapter_id="test",
                extracted_record_id="aleppo-test-2",
                source_curies=["yaqut:7842"],
                labels={"prefLabel": {"en": "Aleppo"}},
            )
            assert decision.kind == "match"
            assert decision.matched_pid == "iac:place-00000042"
            assert decision.tier == 1
            results.append(("Tier 1 hit: source CURIE yaqut:7842 → Aleppo", True, f"matched {decision.matched_pid}"))
        except AssertionError as e:
            results.append(("Tier 1 hit: source CURIE yaqut:7842 → Aleppo", False, str(e)))

        # ---- Test 3: Tier 1 hit for Abbasid (dynasty Q11707) ----
        try:
            decision = resolver.resolve(
                entity_type="dynasty",
                adapter_id="test",
                extracted_record_id="abbasid-test",
                authority_xref=[{"authority": "wikidata", "id": "Q11707"}],
                labels={"prefLabel": {"en": "Abbasid Caliphate"}},
            )
            assert decision.kind == "match"
            assert decision.matched_pid == "iac:dynasty-00000003"
            assert decision.tier == 1
            results.append(("Tier 1 hit: Wikidata Q11707 → Abbasid", True, f"matched {decision.matched_pid}"))
        except AssertionError as e:
            results.append(("Tier 1 hit: Wikidata Q11707 → Abbasid", False, str(e)))

        # ---- Test 4: Tier 1 miss → Tier 2 stub returns "new" ----
        try:
            decision = resolver.resolve(
                entity_type="place",
                adapter_id="test",
                extracted_record_id="unknown-place-1",
                authority_xref=[{"authority": "wikidata", "id": "Q9999999999"}],  # no such PID indexed
                labels={"prefLabel": {"en": "Some Unknown Town"}},
                temporal={"start_ce": 900},
                coords={"lat": 35.0, "lon": 40.0},
            )
            assert decision.kind == "new", f"expected new, got {decision.kind}"
            assert decision.matched_pid is None
            results.append(("Tier 1 miss → Tier 2 stub returns 'new'", True, "kind=new as expected"))
        except AssertionError as e:
            results.append(("Tier 1 miss → Tier 2 stub returns 'new'", False, str(e)))

        # ---- Test 5: Decision cache idempotency (re-run returns same answer) ----
        try:
            d1 = resolver.resolve(
                entity_type="place",
                adapter_id="test",
                extracted_record_id="cache-test",
                authority_xref=[{"authority": "wikidata", "id": "Q41183"}],
                labels={"prefLabel": {"en": "Aleppo"}},
            )
            d2 = resolver.resolve(
                entity_type="place",
                adapter_id="test",
                extracted_record_id="cache-test",
                authority_xref=[{"authority": "wikidata", "id": "DOES_NOT_MATTER_NOW"}],  # ignored: cache hit
                labels={"prefLabel": {"en": "DIFFERENT_INPUT"}},
            )
            assert d1.matched_pid == d2.matched_pid, f"cache miss: {d1.matched_pid} vs {d2.matched_pid}"
            assert d1.kind == d2.kind
            results.append(("Decision cache idempotency", True, "second call returned cached decision"))
        except AssertionError as e:
            results.append(("Decision cache idempotency", False, str(e)))

        resolver.close()

        # ---- Report ----
        print("Entity resolver smoke tests")
        print("=" * 70)
        for name, ok, msg in results:
            marker = "PASS" if ok else "FAIL"
            print(f"  [{marker}] {name:<55} {msg}")
        n_pass = sum(1 for _, ok, _ in results if ok)
        print()
        print(f"Summary: {n_pass}/{len(results)} passed")
        return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
