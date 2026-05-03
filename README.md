# islamicatlas-canonical

Canonical Linked-Open-Data backend for **islamicatlas.org** with a **search-first** architecture. A single, persistent, citable identifier space (`iac:place-NNNNNNNN`, `iac:dynasty-NNNNNNNN`, `iac:person-NNNNNNNN`, `iac:work-NNNNNNNN`, `iac:manuscript-NNNNNNNN`, `iac:event-NNNNNNNN`) consolidates ~59,000 entities currently distributed across 13 layers of the public-facing atlas, into a unified search-first user experience: one search bar, federated results across all entity types, rich entity pages with map / timeline / relations / sources / cross-refs.

> **Status:** Phase 0 (v0.1.0) — schema + ontology + search foundations.
> **Maintainer:** Dr. Ali Çetinkaya (Selçuk University, Department of Computer Engineering)
> **License (data):** CC-BY-SA 4.0 · **License (code):** MIT

---

## Architecture in one paragraph

The canonical store sits **upstream** of three downstream consumers: (1) a Typesense search engine that indexes a denormalized projection of every canonical record into a single collection (`iac_entities`); (2) a UI layer that renders rich entity pages from a per-entity-type "page recipe"; (3) the existing islamicatlas.org map/timeline/network visualizations, now reframed as facets and cross-references rather than parallel silos. **Adding new content** means writing a new adapter folder under `pipelines/adapters/` — search/UI/ontology code is untouched. **Adding a new entity type** is a one-time effort across schema + ontology + projection + page recipe.

---

## Phase 0 deliverables (this release)

| Layer | Files |
|------|-------|
| **Decisions** | 7 ADRs covering URI scheme, authority targets, ontology stack, **search-first architecture**, **unified entity catalog**, **content adapter pattern**, **rich entity page contract**. |
| **Ontology** | `iac_ontology.ttl` (P0 active classes for place + dynasty + their subtypes, plus forward-declared classes for person, work, manuscript, event). `iac_context.jsonld` JSON-LD 1.1 context. |
| **Common schemas** | Five reusable JSON Schema 2020-12 building blocks: `coords`, `multilingual_text`, `temporal`, `authority_xref`, `provenance`. |
| **Namespace schemas** | place + dynasty (active P0); person + work (forward P0.2); manuscript + event (forward P0.3). |
| **Search artifacts** | `typesense_collection.schema.json`, `facets.yaml`, 6 projection rules, `projector.py` rule-driven engine. |
| **UI contract** | `entity_page.meta.schema.json` + 6 page recipes, `search_result.schema.json`. |
| **Adapter framework** | `_template/` boilerplate, `registry.yaml`. |
| **Tests** | 15 schema fixtures + 3 projector tests. **All 18 PASS.** |

```
islamicatlas-canonical/
├── docs/decisions/        7 ADRs
├── ontology/              TTL + JSON-LD context
├── schemas/               6 entity schemas + 5 common building blocks
├── search/                Typesense schema, facets, projection rules, projector.py
├── ui_contract/           page recipes + search-result schema
├── pipelines/adapters/    _template + registry
└── tests/                 schema fixtures + projector tests
```

---

## Running the tests

```bash
pip install jsonschema referencing pyyaml
python3 tests/run_schema_tests.py        # → 15/15 passed (schema validation)
python3 tests/test_projector.py          # → 3/3 passed (search projector)
```

---

## Adding new content (the daily case)

```bash
cp -r pipelines/adapters/_template pipelines/adapters/<your-source-id>
# edit manifest.yaml, drop sources under data/sources/<your-source-id>/,
# customize canonicalize.py, register in adapters/registry.yaml
python3 pipelines/run_adapter.py --id <your-source-id>
python3 pipelines/integrity/check_all.py
python3 pipelines/search/full_reindex.py
```

No search/UI/ontology code is touched. See `pipelines/adapters/_template/README.md` and ADR-006 for the full runbook (incl. "Add Ibn Khaldūn's Muqaddima" worked example).

---

## Adding a new entity type (the rare case)

See ADR-006 §6.4. Steps: ontology class → schema → projection rule → page recipe → manifest → typesense field → test fixtures → reindex.

---

## Phase activation table

| Phase | Active namespaces | Acceptance criterion |
|-------|------------------:|----------------------|
| **P0** (Hafta 0-8) | place, dynasty | Bosworth NID-001..186 canonical; Yâqūt pilot ≥1k places. |
| P0.2 (Hafta 9-16) | + person, work | Science Layer 186 scholars → person; OpenITI ~13.7k files → work; Bosworth rulers fix-up. |
| P0.3 (Hafta 17-24) | + manuscript, event | Ottoman HTR + Salibiyyat + Evliya. |
| P1 (Hafta 25+) | + institution, concept | Konya City Atlas → institution; madhab/tariqa → concept. |

---

See `NEXT_SESSION_PROMPT.md` for Hafta 2 (Bosworth ETL pilot).
