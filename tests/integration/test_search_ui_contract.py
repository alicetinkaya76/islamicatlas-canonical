"""H9 Stage 3 — locks for the search layer + UI contract (no store needed).

Covers the review findings that were live-broken until this stage:
  * projector inferred entity type from @type[0] → 768 subtype-first person
    records failed projection (now @id-derived);
  * facets.yaml source_layer values drifted from the projector's prefix_map;
  * all 6 entity-page recipes failed their own meta-schema ($schema key);
    nothing validated ui_contract at all.
"""
import json
import pathlib
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from search.projector import Projector  # noqa: E402


@pytest.fixture(scope="module")
def projector():
    return Projector(repo_root=REPO)


def _fake_person(types):
    return {
        "@id": "iac:person-00000001",
        "@type": types,
        "labels": {"prefLabel": {"tr": "Test Kişi", "ar": "شخص"}},
        "provenance": {
            "derived_from": [{"source_id": "dia:test-slug"},
                             {"source_id": "el-alam:42"}],
            "generated_at": "2026-01-01T00:00:00Z",
            "modified": "2026-01-01T00:00:00Z",
        },
    }


def test_projector_handles_subtype_first_type_array(projector):
    """The exact failure shape of the 768 broken records."""
    doc = projector.project(_fake_person(["iac:Scholar", "iac:Person"]))
    assert doc["entity_type"] == "person"
    assert doc.get("subtypes") == ["scholar"]


def test_projector_subtypes_exclude_supertype_any_order(projector):
    d1 = projector.project(_fake_person(["iac:Person", "iac:Scholar"]))
    d2 = projector.project(_fake_person(["iac:Scholar", "iac:Person"]))
    assert d1.get("subtypes") == d2.get("subtypes") == ["scholar"]


def test_projector_source_layers_cover_person_era_prefixes(projector):
    doc = projector.project(_fake_person(["iac:Person"]))
    assert "dia" in doc.get("source_layer", [])
    assert "el-alam" in doc.get("source_layer", [])


def test_facets_source_layer_matches_projector_map(projector):
    """Every layer value the projector can emit is a declared facet value,
    so no record becomes invisible behind an undeclared facet bucket.

    Primary probe: the REAL source_id prefixes of the canonical store (when
    present) — hard-coding the map's own keys couldn't catch a prefix the
    store uses but the map doesn't know (that exact gap hid the 2,070-record
    'muqaddasi:' layer; review catch, H9 Stage 3). Storeless (CI) fallback:
    every prefix the map itself claims to handle."""
    import json as _json
    facets = yaml.safe_load((REPO / "search" / "facets.yaml").read_text(encoding="utf-8"))
    source_layer = next(f for f in facets["global_facets"] if f["id"] == "source_layer")
    declared = {v["value"] for v in source_layer["values"]}

    prefixes: set[str] = set()
    canonical = REPO / "data" / "canonical"
    if canonical.exists():
        for ns_dir in canonical.iterdir():
            if not ns_dir.is_dir():
                continue
            # Sampling every 25th record keeps this <1 s yet sweeps all
            # adapters (each stamps thousands of contiguous records).
            for path in sorted(ns_dir.glob(f"iac_{ns_dir.name}_*.json"))[::25]:
                rec = _json.loads(path.read_text(encoding="utf-8"))
                for e in (rec.get("provenance", {}).get("derived_from") or []):
                    sid = e.get("source_id", "")
                    if ":" in sid:
                        prefixes.add(sid.split(":", 1)[0])
    if not prefixes:
        prefixes = {"yaqut", "le-strange", "bosworth-nid", "makdisi", "muqaddasi",
                    "evliya", "ibn-battuta", "openiti", "manual", "science-works",
                    "el-alam", "dia", "dia-chunks-v8", "dia-rich", "tdv_dia"}

    emitted = set(projector._d_source_layers(
        {"provenance": {"derived_from": [{"source_id": f"{p}:x"} for p in sorted(prefixes)]}}))
    missing = emitted - declared
    assert not missing, f"projector emits undeclared facet values: {sorted(missing)}"


def test_facet_fields_exist_in_collection_schema():
    facets = yaml.safe_load((REPO / "search" / "facets.yaml").read_text(encoding="utf-8"))
    coll = json.loads((REPO / "search" / "typesense_collection.schema.json")
                      .read_text(encoding="utf-8"))
    field_names = {f["name"] for f in coll["fields"]}
    for facet in facets["global_facets"]:
        assert facet["field"] in field_names, (
            f"facet {facet['id']!r} references unknown collection field {facet['field']!r}")


def test_entity_page_recipes_validate_against_meta_schema():
    from jsonschema import Draft202012Validator
    meta = json.loads((REPO / "ui_contract" / "entity_page.meta.schema.json")
                      .read_text(encoding="utf-8"))
    validator = Draft202012Validator(meta)
    recipes_dir = REPO / "ui_contract" / "entity_pages"
    recipes = sorted(recipes_dir.glob("*.json"))
    assert len(recipes) == 6
    bad = []
    for path in recipes:
        recipe = json.loads(path.read_text(encoding="utf-8"))
        errs = list(validator.iter_errors(recipe))
        if errs:
            bad.append((path.name, errs[0].message[:160]))
        if recipe.get("entity_type") != path.stem:
            bad.append((path.name, f"entity_type={recipe.get('entity_type')!r} != filename"))
    assert not bad, f"recipe/meta-schema violations: {bad}"


def test_typesense_emit_produces_clean_api_body():
    """H10 S10: emit strips doc-keys and yields a live-creatable body."""
    from search.typesense_schema_emit import emit
    body = emit()
    assert body["name"] == "iac_entities"
    assert body["fields"], "no fields emitted"
    for f in body["fields"]:
        assert "comment" not in f and "description" not in f, f
        assert set(f) <= {"name", "type", "facet", "optional", "index",
                          "sort", "infix", "locale", "stem"}, f
    names = {f["name"]: f for f in body["fields"]}
    dsf = body.get("default_sorting_field")
    if dsf:  # Typesense: numeric + mevcut alan olmalı, yoksa create patlar
        assert dsf in names, f"default_sorting_field {dsf!r} not among fields"
        assert names[dsf]["type"] in ("int32", "int64", "float"), names[dsf]


def test_projected_docs_fit_collection_schema(projector):
    """Sampled real projections must only carry fields the collection
    declares (a live import would otherwise silently drop/err them)."""
    import json as _json
    from search.typesense_schema_emit import emit
    declared = {f["name"] for f in emit()["fields"]}
    canonical = REPO / "data" / "canonical"
    if not canonical.exists():
        pytest.skip("canonical store not present")
    checked = 0
    for ns_dir in sorted(canonical.iterdir()):
        if not ns_dir.is_dir():
            continue
        for path in sorted(ns_dir.glob(f"iac_{ns_dir.name}_*.json"))[::200]:
            doc = projector.project(_json.loads(path.read_text(encoding="utf-8")))
            extra = set(doc) - declared
            assert not extra, f"{path.name}: undeclared fields {sorted(extra)}"
            checked += 1
    assert checked > 100
