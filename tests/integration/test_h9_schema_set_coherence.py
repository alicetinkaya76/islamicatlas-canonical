"""
H9 Stage 1 — PE-2 schema-set coherence invariants (PE2.1-PE2.4).

Guards the ADR-013 contract permanently:

  PE2.1  The on-disk schema set is exactly the expected 11 files, every
         file declares an $id under the canonical URI base, and all
         $ids share ONE version tag (R1).
  PE2.2  Every external $ref anywhere in the set resolves to one of the
         set's own $ids via a freshly built referencing.Registry —
         i.e. the $ref graph and the $id set are mutually consistent
         (the property whose absence was PE-2).
  PE2.3  The shared tag equals EXPECTED_SET_VERSION. This constant is
         the enforcement pin of ADR-013 R4: a schema-set version bump
         MUST update it in the same commit, or the suite goes red.
  PE2.4  Every schema compiles as Draft 2020-12 against the full local
         registry (check_schema + validator construction + resolver
         lookup of each external ref).

No data/canonical access required: this module reads schemas/ only, so
it runs in any checkout (CI, sandbox, fresh clone) without the store.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"

URI_BASE = "https://w3id.org/islamicatlas/schemas/"
TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")

# ADR-013 R4 enforcement pin. A set-level version bump updates this
# constant in the SAME commit that rewrites the $ids — see
# docs/decisions/ADR-013-schema-set-versioning-policy.md.
EXPECTED_SET_VERSION = "v0.3.0"

# Set membership is intentionally pinned (relative to schemas/): adding
# or removing a schema file is a conscious, reviewed act that updates
# this list alongside registry-awareness elsewhere.
EXPECTED_FILES = {
    "_common/authority_xref.schema.json",
    "_common/coords.schema.json",
    "_common/multilingual_text.schema.json",
    "_common/provenance.schema.json",
    "_common/temporal.schema.json",
    "dynasty.schema.json",
    "event.schema.json",
    "manuscript.schema.json",
    "person.schema.json",
    "place.schema.json",
    "work.schema.json",
}


def _discover() -> dict[str, dict]:
    """rel-path -> parsed schema for every *.schema.json under schemas/."""
    out: dict[str, dict] = {}
    for p in sorted(SCHEMAS_DIR.rglob("*.schema.json")):
        rel = p.relative_to(SCHEMAS_DIR).as_posix()
        out[rel] = json.loads(p.read_text(encoding="utf-8"))
    return out


def _iter_external_refs(node, acc: list[str]) -> None:
    """Collect every $ref value that is an absolute http(s) URI."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(("http://", "https://")):
            acc.append(ref)
        for v in node.values():
            _iter_external_refs(v, acc)
    elif isinstance(node, list):
        for v in node:
            _iter_external_refs(v, acc)


def _tag_of(schema_id: str) -> str:
    assert schema_id.startswith(URI_BASE), (
        f"$id outside canonical base: {schema_id}"
    )
    return schema_id[len(URI_BASE):].split("/", 1)[0]


@pytest.fixture(scope="module")
def schema_set() -> dict[str, dict]:
    return _discover()


def test_pe2_1_single_version_tag_across_expected_set(schema_set):
    """PE2.1 — exact expected membership; one tag for all $ids (R1)."""
    assert set(schema_set) == EXPECTED_FILES, (
        "schema-set membership changed; update EXPECTED_FILES consciously "
        f"(unexpected: {sorted(set(schema_set) ^ EXPECTED_FILES)})"
    )
    tags = {}
    for rel, schema in schema_set.items():
        sid = schema.get("$id")
        assert sid, f"{rel} has no $id"
        tag = _tag_of(sid)
        assert TAG_RE.match(tag), f"{rel} $id tag not semver-shaped: {tag}"
        # $id path must mirror the on-disk relative path
        assert sid == f"{URI_BASE}{tag}/{rel}", (
            f"{rel}: $id path segment does not mirror file path: {sid}"
        )
        tags[rel] = tag
    distinct = set(tags.values())
    assert len(distinct) == 1, f"version drift (PE-2 regression): {tags}"


def test_pe2_2_every_external_ref_resolves_to_a_local_id(schema_set):
    """PE2.2 — $ref graph is closed over the set's own $ids."""
    ids = {s["$id"] for s in schema_set.values()}
    for rel, schema in schema_set.items():
        refs: list[str] = []
        _iter_external_refs(schema, refs)
        for ref in refs:
            base = ref.split("#", 1)[0]
            assert base in ids, (
                f"{rel} $refs {ref!r}, which matches no on-disk $id "
                "(drifted or dangling reference)"
            )


def test_pe2_3_set_version_is_pinned_expected(schema_set):
    """PE2.3 — the shared tag equals the ADR-013 R4 pin."""
    tags = {_tag_of(s["$id"]) for s in schema_set.values()}
    assert tags == {EXPECTED_SET_VERSION}, (
        f"schema-set tag {sorted(tags)} != pinned {EXPECTED_SET_VERSION}; "
        "if this is a deliberate bump, update EXPECTED_SET_VERSION in "
        "this file in the same commit (ADR-013 R4)"
    )


def test_pe2_4_schemas_compile_against_full_registry(schema_set):
    """PE2.4 — Draft 2020-12 compile + resolver lookup of every ref."""
    registry = Registry()
    for schema in schema_set.values():
        registry = registry.with_resource(
            uri=schema["$id"], resource=Resource.from_contents(schema)
        )
    resolver = registry.resolver()
    for rel, schema in schema_set.items():
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=registry)  # constructible
        refs: list[str] = []
        _iter_external_refs(schema, refs)
        for ref in refs:
            base = ref.split("#", 1)[0]
            resolved = resolver.lookup(base)  # raises Unresolvable on miss
            assert resolved.contents.get("$id") == base, (
                f"{rel}: resolver returned wrong resource for {base}"
            )
