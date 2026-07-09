"""H9 Stage 3 — pytest wrapper around tests/run_schema_tests.py.

Folds the 15 schema fixture checks into the single `pytest tests/integration`
command (they previously required a separate `python3 tests/run_schema_tests.py`
invocation). The standalone script stays authoritative for CLI use; this
wrapper imports and parametrizes its own validate_one — no logic duplicated.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import run_schema_tests as rst  # noqa: E402

_MANIFEST = json.loads((REPO / "tests" / "test_manifest.json").read_text(encoding="utf-8"))
_SCHEMAS = rst.discover_schemas(REPO / "schemas")
_REGISTRY = rst.build_registry(_SCHEMAS)


@pytest.mark.parametrize("case", _MANIFEST["tests"], ids=lambda c: c["name"])
def test_schema_fixture(case):
    ok, msg = rst.validate_one(case, _SCHEMAS, _REGISTRY)
    assert ok, msg
