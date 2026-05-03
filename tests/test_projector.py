#!/usr/bin/env python3
"""
test_projector.py — Smoke + structural tests for search/projector.py.

Strategy:
  1. Materialize the existing valid fixtures (place_valid.json, dynasty_valid.json)
     as canonical records under data/canonical/{place,dynasty}/ using the @id-derived
     filename convention.
  2. Project each record.
  3. Assert a set of structural properties on the resulting search documents.

This is NOT a full schema-conformance test of search docs against
typesense_collection.schema.json (which would require Typesense's own validator,
not JSON Schema). It IS a property-based test that the projector populates the
fields it should and skips the ones it shouldn't.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "search"))

from projector import Projector  # noqa: E402


def materialize_fixtures(tmp_repo: Path) -> None:
    """Copy minimal repo skeleton + valid fixtures into a temp working repo."""
    # Copy schemas + search/ + data/iqlim_labels.json (if exists) into tmp
    for sub in ("search",):
        shutil.copytree(REPO_ROOT / sub, tmp_repo / sub)

    # Place the two fixtures as canonical records
    canonical = tmp_repo / "data" / "canonical"
    (canonical / "place").mkdir(parents=True, exist_ok=True)
    (canonical / "dynasty").mkdir(parents=True, exist_ok=True)

    with (REPO_ROOT / "tests/fixtures/valid/place_valid.json").open(encoding="utf-8") as fh:
        place = json.load(fh)
    with (REPO_ROOT / "tests/fixtures/valid/dynasty_valid.json").open(encoding="utf-8") as fh:
        dynasty = json.load(fh)

    # Write each at the location lookup expects: data/canonical/<ns>/iac_<ns>_NNNNNNNN.json
    pid = place["@id"]                                # "iac:place-00000042"
    ord_ = pid.split("-")[1]
    (canonical / "place" / f"iac_place_{ord_}.json").write_text(
        json.dumps(place, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pid = dynasty["@id"]
    ord_ = pid.split("-")[1]
    (canonical / "dynasty" / f"iac_dynasty_{ord_}.json").write_text(
        json.dumps(dynasty, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def assert_place_doc(doc: dict) -> None:
    assert doc["id"] == "iac:place-00000042", f"id mismatch: {doc.get('id')}"
    assert doc["entity_type"] == "place", f"entity_type mismatch: {doc.get('entity_type')}"
    assert "settlement" in doc.get("subtypes", []), f"subtypes missing 'settlement': {doc.get('subtypes')}"
    assert doc["place_subtype"] == "settlement"
    assert doc["prefLabel_en"] == "Aleppo"
    assert doc["prefLabel_ar"] == "حلب"
    assert doc["prefLabel_tr"] == "Halep"
    # ASCII-folded translit: Ḥalab → Halab
    assert doc["prefLabel_translit"] == "Halab", f"translit fold: {doc.get('prefLabel_translit')!r}"
    # altLabels flattened across languages and includes the translit variant strings
    assert "Halab" in doc["altLabels"]
    assert "Beroea" in doc["altLabels"]
    assert "Şehbâ" in doc["altLabels"]
    # geopoint
    assert doc["_geo"] == [36.2021, 37.1343], f"_geo mismatch: {doc.get('_geo')}"
    # century: start_ce=637 → 7th c.
    assert doc["century_ce"] == 7, f"century_ce: {doc.get('century_ce')}"
    assert doc["start_year_ce"] == 637
    # source layers from yaqut + le-strange
    assert "yaqut" in doc["source_layer"]
    assert "le-strange" in doc["source_layer"]
    # languages
    assert "ar" in doc["language"]
    assert "en" in doc["language"]
    assert "tr" in doc["language"]
    # bool flags
    assert doc["has_coords"] is True
    assert doc["has_wikidata"] is True
    assert doc["wikidata_qid"] == "Q41183"
    # related_pids includes located_in + falls_within_iqlim + had_capital_of placeholders
    assert "iac:place-00000099" in doc["related_pids"]
    assert "iac:dynasty-00000017" in doc["related_pids"]
    # deprecated absent (false omitted by default)
    assert doc.get("deprecated") in (None, False, []), f"deprecated leaked: {doc.get('deprecated')}"
    # _score is positive (has_wikidata + has_coords + has_capital + manual_curation NOT set)
    assert doc["_score"] >= 1.0, f"_score: {doc['_score']}"


def assert_dynasty_doc(doc: dict) -> None:
    assert doc["id"] == "iac:dynasty-00000003"
    assert doc["entity_type"] == "dynasty"
    assert "caliphate" in doc.get("subtypes", [])
    assert doc["dynasty_subtype"] == "caliphate"
    assert doc["prefLabel_en"] == "Abbasid Caliphate"
    assert doc["start_year_ce"] == 750
    assert doc["end_year_ce"] == 1258
    assert doc["century_ce"] == 8  # 750 → 8th century
    assert "bosworth" in doc["source_layer"]
    assert doc["has_wikidata"] is True
    assert doc["wikidata_qid"] == "Q11707"
    # rulers' names should be in altLabels
    assert any("Manṣūr" in s or "Mansur" in s for s in doc.get("altLabels", []))
    # related_pids includes predecessor + successor + capital places + territory
    assert "iac:dynasty-00000002" in doc["related_pids"]
    assert "iac:dynasty-00000019" in doc["related_pids"]
    assert "iac:place-00000001" in doc["related_pids"]  # Baghdad (placeholder)
    # _score boosted by is_caliphate + has_bosworth_id + has_wikidata
    assert doc["_score"] > 1.5, f"_score: {doc['_score']}"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_repo = Path(tmp)
        materialize_fixtures(tmp_repo)
        proj = Projector(tmp_repo)

        results: list[tuple[str, bool, str]] = []

        # Test 1: project place_valid
        try:
            place_record = json.loads(
                (tmp_repo / "data/canonical/place/iac_place_00000042.json").read_text(encoding="utf-8")
            )
            doc = proj.project(place_record)
            assert_place_doc(doc)
            results.append(("place projection", True, "all assertions passed"))
            place_doc_for_print = doc
        except AssertionError as e:
            results.append(("place projection", False, str(e)))
            place_doc_for_print = None
        except Exception as e:
            results.append(("place projection", False, f"unexpected {type(e).__name__}: {e}"))
            place_doc_for_print = None

        # Test 2: project dynasty_valid
        try:
            dynasty_record = json.loads(
                (tmp_repo / "data/canonical/dynasty/iac_dynasty_00000003.json").read_text(encoding="utf-8")
            )
            doc = proj.project(dynasty_record)
            assert_dynasty_doc(doc)
            results.append(("dynasty projection", True, "all assertions passed"))
            dynasty_doc_for_print = doc
        except AssertionError as e:
            results.append(("dynasty projection", False, str(e)))
            dynasty_doc_for_print = None
        except Exception as e:
            results.append(("dynasty projection", False, f"unexpected {type(e).__name__}: {e}"))
            dynasty_doc_for_print = None

        # Test 3: project_all walks both
        try:
            docs = list(proj.project_all())
            assert len(docs) == 2, f"expected 2 docs, got {len(docs)}"
            ids = {d["id"] for d in docs}
            assert ids == {"iac:place-00000042", "iac:dynasty-00000003"}
            results.append(("project_all walk", True, f"yielded {len(docs)} docs"))
        except AssertionError as e:
            results.append(("project_all walk", False, str(e)))
        except Exception as e:
            results.append(("project_all walk", False, f"unexpected {type(e).__name__}: {e}"))

        # Report
        print("Search projector tests")
        print("=" * 70)
        for name, ok, msg in results:
            marker = "PASS" if ok else "FAIL"
            print(f"  [{marker}] {name:<32} {msg}")

        if place_doc_for_print:
            print()
            print("Sample place search document (truncated values):")
            preview = {k: (v[:60] + "..." if isinstance(v, str) and len(v) > 60 else v)
                       for k, v in place_doc_for_print.items()}
            print(json.dumps(preview, ensure_ascii=False, indent=2)[:2000])

        n_pass = sum(1 for _, ok, _ in results if ok)
        print()
        print(f"Summary: {n_pass}/{len(results)} passed")
        return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
