# Adapter template

Boilerplate for a new content adapter. Copy this folder to
`pipelines/adapters/<your-source-id>/` and follow the steps below.

## What is an adapter?

An adapter is the bridge between a raw content source (a book, a manuscript
catalog, a defter collection, a Wikidata query) and the canonical entity
store (`data/canonical/<namespace>/`). One folder = one source.

See `docs/decisions/ADR-006-content-adapter-pattern.md` for the full design.

## Quick start

```bash
# 1. Copy the template
cp -r pipelines/adapters/_template pipelines/adapters/ibn-khaldun-muqaddima

# 2. Edit manifest.yaml — set adapter_id, license, target_namespaces, paths
$EDITOR pipelines/adapters/ibn-khaldun-muqaddima/manifest.yaml

# 3. Drop your source files under data/sources/ibn-khaldun-muqaddima/
mkdir -p data/sources/ibn-khaldun-muqaddima
cp ~/research/muqaddima/*.json data/sources/ibn-khaldun-muqaddima/

# 4. Override extract.py and canonicalize.py for your source's quirks
$EDITOR pipelines/adapters/ibn-khaldun-muqaddima/canonicalize.py

# 5. Register in registry
$EDITOR pipelines/adapters/registry.yaml
# add:
#   - adapter_id: ibn-khaldun-muqaddima
#     enabled: true
#     priority: 250

# 6. Run
python3 pipelines/run_adapter.py --id ibn-khaldun-muqaddima

# 7. Validate
python3 tests/run_schema_tests.py
python3 pipelines/integrity/check_all.py

# 8. Reindex search
python3 pipelines/search/full_reindex.py
```

## Files in this template

| File | Purpose |
|------|---------|
| `manifest.yaml` | Adapter metadata: id, version, source kind, license, namespaces, paths, reconciliation behaviour, maintainer. |
| `extract.py` | Source → normalized intermediate JSON. No network calls; deterministic. |
| `canonicalize.py` | Normalized intermediate → canonical entity records that pass `schemas/<namespace>.schema.json`. |
| `README.md` | This file. Replace with: source history, edition info, license details, known issues. |

## Optional artifacts

```
pipelines/adapters/<your-source>/
├── projection_overrides.yaml   # source-specific search projection tweaks
├── tests/                      # adapter-specific test fixtures
└── notebooks/                  # exploration / verification notebooks
```

## Contract reminders

- `extract.py` must NOT import canonical schemas. It produces an intermediate, full stop.
- `canonicalize.py` must produce records that pass schema validation in strict mode (`tests/run_schema_tests.py`).
- `@id` is always allocated via `pid_minter`; never hand-assigned.
- Provenance block is always populated; `derived_from` array always has ≥1 entry citing the source.
- Cross-record references (predecessor, successor, authors, witnesses_work) MAY use placeholder PIDs; integrity check resolves them in a second pass.
