# islamicatlas-canonical

Canonical Linked-Open-Data backend for **islamicatlas.org** with a **search-first** architecture. A single, persistent, citable identifier space (`iac:place-NNNNNNNN`, `iac:dynasty-NNNNNNNN`, `iac:person-NNNNNNNN`, `iac:work-NNNNNNNN`, `iac:manuscript-NNNNNNNN`, `iac:event-NNNNNNNN`) consolidates ~59,000 entities currently distributed across 13 layers of the public-facing atlas, into a unified search-first user experience: one search bar, federated results across all entity types, rich entity pages with map / timeline / relations / sources / cross-refs.

> **Status:** Phase 0, Hafta 9 sonu — schema set **v0.4.0** (ADR-013/015 — institution aktif);
> canonical store **67,833 kayıt** (person 22,935 · place 19,929 · event 9,956 · work 9,404 ·
> institution 5,423 · dynasty 186 — koddan sayılır, `make reindex-dry`
> özetiyle doğrulanır);
> AO (TDV DiA scraper) tamam, AP (dia_works rich-mint) H10 hedefi.
> Kalan işlerin sıralı listesi: [`docs/PHASE0_CLOSEOUT.md`](docs/PHASE0_CLOSEOUT.md).
> **Maintainer:** Dr. Ali Çetinkaya (Selçuk University, Department of Computer Engineering)
> **License (data):** CC-BY-SA 4.0 · **License (code):** MIT

---

## Architecture in one paragraph

The canonical store sits **upstream** of three downstream consumers: (1) a Typesense search engine that indexes a denormalized projection of every canonical record into a single collection (`iac_entities`); (2) a UI layer that renders rich entity pages from a per-entity-type "page recipe"; (3) the existing islamicatlas.org map/timeline/network visualizations, now reframed as facets and cross-references rather than parallel silos. **Adding new content** means writing a new adapter folder under `pipelines/adapters/` — search/UI/ontology code is untouched. **Adding a new entity type** is a one-time effort across schema + ontology + projection + page recipe.

---

## Phase 0 deliverables (H9 itibarıyla)

| Layer | Files |
|------|-------|
| **Decisions** | **14 ADR** — URI scheme, authority targets, ontology stack, search-first, unified catalog, adapter pattern, rich page contract, entity resolution, DiA rich-mint doktrini (ADR-009), digital_corpus, dia_chunks scope, maxLength 50K, schema-set versiyonlama (ADR-013), TDV scraping compliance (ADR-014). |
| **Ontology** | `iac_ontology.ttl` + `iac_context.jsonld` (H2 vintage; Faz 0.5'te w3id yayını öncesi bakım gerekir — bkz. PHASE0_CLOSEOUT). |
| **Schemas** | 12 dosyalık set, tek etiket **v0.4.0** (ADR-013; test-pinli): 6 entity + 5 `_common` yapı taşı. |
| **Canonical store** | 67,833 kayıt (gitignored; `data/sources/` + adapter replay'den yeniden üretilebilir). |
| **Adapters** | 19 adapter (`registry.yaml`); en yeniler: scholars, ei1, battles-events, konya-city-atlas, maqrizi-khitat, evliya-institutions (H10-H11). |
| **Search artifacts** | `typesense_collection.schema.json`, `facets.yaml`, 6 projection rules, `projector.py`; `full_reindex.py --dry-run` = 67,833/67,833 projeksiyon regresyon kapısı. |
| **UI contract** | `entity_page.meta.schema.json` + 6 page recipes (testle doğrulanır), `search_result.schema.json`. |
| **Tests** | `pytest tests/integration` → **160 passed** (17 şema fixture'ı dahil); ayrıca CLI: `run_schema_tests.py`, `test_projector.py`, `test_resolver.py`. |

```
islamicatlas-canonical/
├── docs/decisions/        14 ADR
├── docs/h5..h9/           haftalık journal + karar logları
├── ontology/              TTL + JSON-LD context
├── schemas/               12 dosyalık v0.4.0 seti (7 entity + 5 _common)
├── search/                Typesense schema, facets, projection rules, projector.py
├── ui_contract/           page recipes + search-result schema
├── pipelines/             adapters (12) + _lib + integrity + migrations + search
└── tests/                 integration suite + schema fixtures + CLI testleri
```

---

## Running the tests

```bash
pip install -r requirements.txt
make test        # tam kapı: schema CLI + projector + resolver + pytest (160 passed)
make test-fast   # iç döngü (~9 sn): tüm-store validasyonları hariç
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

| Phase | Active namespaces | Plan / gerçekleşen (2026-07 durumu) |
|-------|------------------:|----------------------|
| **P0** (Hafta 0-8) | place, dynasty | ✅ Bosworth 186 dynasty; Yâqūt+Muqaddasī+Le Strange 15,239 place. |
| P0.2 | + person, work | ✅ Erken geldi (H4-H5): DİA+el-Aʿlām+science 21,946 person; OpenITI+science 9,331 work. H8 v8 enrichment; H9 AO scraper. |
| P0.3 | + manuscript, event | Şemalar forward-declared; içerik açık. |
| P1 | + institution, concept | institution ✅ ERKEN GELDİ (H11, ADR-015): 3,918 yapı (Konya+Kahire+Evliyâ). concept açık. |

Kalan işlerin sahipli/sıralı listesi (AP → AN → Faz 0.5 → v1.0.0):
**[`docs/PHASE0_CLOSEOUT.md`](docs/PHASE0_CLOSEOUT.md)**. Haftalık oturum
kayıtları `docs/h5..h9/` altındadır (H2-H4 kökten `docs/h2..h4/`e taşındı,
H9 Stage 5).
