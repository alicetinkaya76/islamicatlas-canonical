# Data Sources Inventory

This directory holds **upstream source files** for the canonical store.
Each subdirectory feeds one or more adapters in `pipelines/adapters/`.

**Origin:** Existing islamicatlas.org Vite/React repository (data export 2026-04-09).
**Total size:** ~40 MB (excluding `dia_chunks.json` which is 73 MB and lives outside the canonical repo until Phase 0.2 deep content).

---

## Phase 0 — places + dynasties (Hafta 2-8)

### `bosworth/` — 186 dynasties + 830 rulers (Hafta 2)

This is the **primary Hafta 2 input.** The CSV is already aligned with Bosworth's
*New Islamic Dynasties* numbering: `dynasty_id=1` is Rāshidūn, `dynasty_id=2` is
Umayyad, `dynasty_id=3` is Abbasid, ..., `dynasty_id=186` is Brunei.

| File | Rows × Cols | Purpose |
|------|-------------|---------|
| `all_dynasties_enriched.csv` | 186 × 44 | Master dynasty table. Columns include name (TR/AR/EN), region, capital, dates (CE+AH), predecessor, successor, government_type, religious_orientation, capital_lat/lon, region_bbox, narrative_tr/en, key_contribution_tr/en. **All fields needed for `dynasty.schema.json` are present or derivable.** |
| `all_rulers_merged.csv` | 830 × 38 | Rulers across all 186 dynasties. Columns: person_id, dynasty_id (FK), full_name_original, short_name, kunya, nasab, laqab, title, role, reign_start_hijri/ce, reign_end_hijri/ce. **Direct fit for `dynasty.schema.json` rulers[]** (Phase 0); promotion to `iac:person-` PIDs in Phase 0.2. |
| `dynasty_relations.csv` | 101 × 6 | Inter-dynasty relations: vassal/allied/successor/rival. Feeds `dynasty.predecessor` + `dynasty.successor` post-canonicalization integrity pass. |
| `dynasty_analytics.csv` | 186 × 16 | Computed analytics: duration, ruler_count, stability_ratio, battle_win_ratio, power_index, lifecycle. **Not canonicalized**; exposed via search facet boosts and dynasty page sidebars. |
| `DATA_DICTIONARY.md` | — | Source-of-truth schema documentation. Read first. |

**Adapter:** `pipelines/adapters/bosworth/` (to be implemented Hafta 2).

### `le-strange/` — 434 places (Hafta 3-4)

| File | Items | Purpose |
|------|-------|---------|
| `le_strange_eastern_caliphate.json` | 434 | Le Strange's *Lands of the Eastern Caliphate* placenames with coords, alternate forms, geo type. Canonical fields: `name_ar`, `name_en`, `name_tr`, `le_strange_form`, `alternate_names`, `geo_type`. |
| `le_strange_xref.json` | (50 KB) | Le Strange ↔ Yâqūt cross-references. Feeds `place.cross_refs[]`. |

**Adapter:** `pipelines/adapters/le-strange/`.

### `major-cities/` — 20 cities × multi-period (Hafta 4)

| File | Rows | Purpose |
|------|------|---------|
| `major_cities.csv` | 69 (≈20 cities × multiple periods) | Population estimates per period, role per dynasty, narrative. Augments place records with temporal demographic data. Feeds `place.population_history[]` (P0 schema field forward-declared). |

**Adapter:** `pipelines/adapters/major-cities/`.

### `battles-events/` — events + battles + causal graph (Hafta 5-8)

| File | Rows | Target |
|------|------|--------|
| `battles.csv` | 50 × 23 | Will become `iac:event-` records of subtype Battle in P0.3. Carries lat/lon, date_ce, date_hijri, dynasty_id_1/2, related_ruler_ids, causes_event_id, caused_by_event_id. |
| `events.csv` | 50 × 19 | `iac:event-` non-battle events (foundings, conquests, revolts). Carries causal_links via causes_event_id. |
| `causal_links.csv` | (35 KB) | Event-to-event causation graph. Feeds `event.causes` + `event.consequences`. |
| `diplomacy.csv` | 30 × 10 | Inter-dynasty diplomatic events. P0.3 feed. |
| `monuments.csv` | 40 × 17 | Architectural monuments. Splits in P1: structural monuments → `iac:institution-`; field-level objects (towers, gates, fountains) → place subtypes. |
| `trade_routes.csv` | 15 × 18 | Routes with waypoints + active periods. P1 → `iac:route-` namespace. |

These battles + events are P0.3 active (forward-declared in current schemas). In Hafta 5-8 they may be referenced as PID placeholders by dynasty/place records.

---

## Phase 0.2 — persons + works (Hafta 9-16)

### `scholars/` — Science Layer (49 scholars + identity registry)

| File | Items | Target |
|------|-------|--------|
| `scholars.csv` | 49 × 24 | Curated scholar entries with birth/death CE, lat/lon, field, sub_field, dynasty_id_patron, major_work, intellectual_context. Direct seed for `iac:person-` namespace. |
| `scholar_identity.js` | (436 KB) | Multi-source person identity registry (cross-source disambiguation). Critical for Bosworth ruler ↔ Science Layer scholar reconciliation. |
| `scholar_meta.js` | (15 KB) | Metadata extension. |
| `scholar_links.js` | (15 KB) | External authority links (Wikidata QID, VIAF, etc.) per scholar. |
| `isnad_chains.js` | (8 KB) | Teacher-student chains. Direct feed for `person.teachers` + `person.students`. |

**Adapter:** `pipelines/adapters/science-layer/`.

### `alam/` — A'lam biographical dictionary (13,940 entries)

| File | Items | Target |
|------|-------|--------|
| `alam_lite.json` | 13,940 | Compact biographical entries (id, h=headword, ht/he=transliteration, dt/de=dates, c=category, g=geography). Direct seed for `iac:person-` namespace at scale. |
| `alam_xrefs.json` | (54 KB) | Cross-references to other authority files. |

**Adapter:** `pipelines/adapters/alam/`.

### `dia/` — Türk Diyanet İslâm Ansiklopedisi (DİA)

| File | Items | Target |
|------|-------|--------|
| `dia_lite.json` | 8,528 | DİA biographical/topical entries (id, t=title, ds=description, bp=birthplace, c1=category, dh/dc=dates, fl=floruit). Largest TR-language biographical/topical authority. |
| `dia_works.json` | (2.1 MB, dict by author slug) | Works listed per DİA biographical entry. **Direct seed for `iac:work-` namespace.** |
| `dia_relations.json` | (476 KB) | Cross-entry relations (teacher/student/citation). |
| `dia_travel.json` | (394 KB) | Travel/migration data per scholar. Feeds `person.active_in_places[]`. |
| `dia_geo.json` | (228 KB) | Geographic data per entry. |
| `dia_alam_xref.json` | (60 KB) | DİA ↔ A'lam crosswalk. **Critical for de-duplication** when seeding person namespace from two large sources. |

**Adapter:** `pipelines/adapters/dia/`. **Note:** Full content (`dia_chunks.json`, 73 MB) lives outside this repo; load on demand for P0.2 deep content (full-text search beyond title-level).

### `ei1/` — Encyclopaedia of Islam, 1st edition (7,568 entries)

| File | Items | Target |
|------|-------|--------|
| `ei1_lite.json` | 7,568 | EI1 entries (t=title, tn=transliterated, ds=description, is=signed, vol=volume, at=author). EN-language biographical/topical authority complementing DİA. |
| `ei1_works.json` | (12 KB) | EI1 referenced works. |
| `ei1_relations.json` | (139 KB) | Cross-entry relations. |
| `ei1_geo.json` | (33 KB) | Geographic data per entry. |

**Adapter:** `pipelines/adapters/ei1/`.

---

## Phase 0.3 — manuscripts + events Faz 2 (Hafta 17-24)

### `evliya-celebi/` — Evliya Çelebi (10 voyages, ~5,400 places)

| File | Size | Target |
|------|------|--------|
| `evliya_atlas_layer.json` | 14 MB | Full Evliya layer: travelers, voyages, stops with coords, full TR/EN/AR multilingual descriptions, cross-references. **Largest single dataset.** Mostly feeds events (voyage stops as `iac:event-` of subtype Voyage); secondarily augments place records with Evliya layer references. |

**Adapter:** `pipelines/adapters/evliya-celebi/`.

### `ibn-battuta/` — İbn Battuta voyages

| File | Size | Target |
|------|------|--------|
| `ibn_battuta_atlas_layer.json` | 0.6 MB | 7 voyages, 317 stops, traveler metadata. |
| `ibn_battuta_routes.geojson` | 266 KB | Route geometries (LineString). |

**Adapter:** `pipelines/adapters/ibn-battuta/`.

### `maqrizi-khitat/` — Cairo / Egypt monuments

| File | Size | Target |
|------|------|--------|
| `maqrizi_khitat_atlas_layer.json` | 0.9 MB | Maqrīzī's *al-Khitat* — Cairo structures, categorized. Feeds places (P0.3) + institutions (P1). |

**Adapter:** `pipelines/adapters/maqrizi-khitat/`.

---

## Phase 1 — institutions + concepts + coins (Hafta 25+)

### `darp-islam/` — Mints (3,458 mint records)

| File | Size | Target |
|------|------|--------|
| `darpislam_lite.json` | 1.3 MB (`metadata` + `mints` array) | Compact mint records. Feeds `iac:place-` (mint location) + `iac:event-` (minting events) + (optional, P1.5) `iac:coin-` namespace. |
| `darpislam_detail_0.json` … `_6.json` | ~5 MB total | Full coin records (sharded). Loaded on demand. |

**Adapter:** `pipelines/adapters/darp-islam/` (P1.5).

### `konya-city-atlas/` — Konya structures (583 buildings)

| File | Size | Target |
|------|------|--------|
| `konya_translated.json` | 0.8 MB | Translated city atlas content. |
| `*` (city-atlas/ subfolder contents) | ~2.5 MB | Per-structure JSON files. **Direct seed for `iac:institution-` namespace** (madrasa, mosque, tekke, çeşme, türbe). |

**Adapter:** `pipelines/adapters/konya-city-atlas/` (P1).

---

## Datasets NOT in this repo

| File | Size | Why excluded |
|------|------|--------------|
| `dia_chunks.json` | 73 MB | Full-text content of every DİA entry. Useful for P0.2 deep content (search snippet generation, NER), but too large to keep in canonical repo. Load on demand into a separate `data/cache/dia_full/` directory at P0.2 onset. **Status as of Hafta 3:** still excluded; held locally on Mac at `data/sources/dia/dia_chunks.json` (gitignored). Hafta 4 person-namespace adapter consumes this file at ingest time — canonical store records (which ARE gitignored) carry the relevant chunk references; the raw chunks file itself stays out of the repo until Phase 0.5 git-lfs migration. |

---

## Hafta 3 additions (Yâqūt + Muqaddasī expansion)

### `yaqut/` — Muʿjam al-Buldān, 12,954 entries (Hafta 3)

The classical Islamic gazetteer; primary seed for the `iac:place-*` namespace.

| File | Size | Purpose |
|------|------|---------|
| `yaqut_lite.json` | 6.5 MB | Compact format, 18 fields per entry, flat lat/lon + geo_confidence (5-level enum: exact / approximate / inferred / region / country). Coverage: 12,954/12,954 names + descriptions, 11,471/12,954 with coords. |
| `yaqut_detail.json` | 11 MB | Per-id full Arabic text + parent_locations array. Joined to lite by integer id. |
| `yaqut_crossref.json` | 1.5 MB | 606 places with person crossrefs (8,692 person attestations from El-Aʿlām). Sidecar for Hafta 4 person-namespace linkage. |
| `yaqut_entries.json` | 32 MB | (OPTIONAL — on user's Mac at `project/data/yaqut/`, not committed) Richer 37-field format with curated coords, etymology, alternate_names. The yaqut adapter auto-detects this file as a sibling of yaqut_lite; when present, it merges richer-format provenance with lite's wider coord coverage. |
| `yaqut_alam_crossref_enriched.json` | (variable) | (OPTIONAL) Enriched person-place crossref with TR + DİA URL + coords for 13,940 persons. Hafta 4 prep. |
| `yaqut_place_graph.json` | (variable) | (OPTIONAL) Pre-computed parent/neighbor adjacency for 2,523 nodes. Hafta 3 doesn't directly use this — adapter walks parent_locations from the detail file — but it's a useful cross-check. |
| `yaqut_translations.json` | (variable) | (OPTIONAL) Translation-pipeline metadata, not directly used. |

**Adapter:** `pipelines/adapters/yaqut/`. **Output:** 12,954 canonical place records.

### `muqaddasi/` — Aḥsan al-Taqāsīm, 21 iqlims + 2,049 places + 1,427 routes (Hafta 3)

The earliest comprehensive Islamic geographical work that survives intact (al-Muqaddasī, d. 390/1000), predating Yâqūt by ~240 years. Provides independent attestation and the canonical 14-iqlim regional schema.

| File | Size | Purpose |
|------|------|---------|
| `muqaddasi_atlas_layer.json` | 1.8 MB | Top-level: 21 `aqualim` (iqlim) records + nested children, 2,049 flat `places` records (all with coords + TR/EN/AR names + certainty enum), 1,427 `routes` records (transport edges, **deferred to Hafta 5+ event/transport namespace**). |
| `muqaddasi_xref.json` | 0.2 MB | 245 muq-id → yaqut_id cross-references. Drives the Muqaddasī ↔ Yâqūt bidirectional attestation pass in `pipelines/integrity/place_integrity.py`. |

**Adapter:** `pipelines/adapters/muqaddasi/`. **Output:** 2,070 canonical records (21 iqlim + 2,049 settlements). Routes deferred.

### `le-strange/` — Updated to v2 (Hafta 3)

Same files as Hafta 2 baseline, but the adapter is now operational:
- 274/434 entries are augmentations of existing Yâqūt PIDs (sidecar consumed by `place_integrity.py`).
- 160/434 entries are new place records (rivers, smaller fortresses, Le Strange-only attestations).

---

## Cross-source merge logic (Hafta 3 invariant)

When the same medieval place is attested by multiple sources (e.g., Aleppo / Halab is in Yâqūt's gazetteer, Muqaddasī's iqlim al-Shām, and Le Strange's Eastern Caliphate chapter), Phase 0 keeps **one canonical PID per source** (no PID renaming — PIDs are immutable). Cross-attestation is recorded via:

- `derived_from_layers[]`: union of `["yaqut", "makdisi", "le-strange"]`
- `provenance.derived_from[]`: append-only entries from each source
- `note`: bidirectional cross-reference text ("Same place is canonicalized at iac:place-NNNN under Muqaddasī's id=...")

A future Phase 0.5 ResolverV2 pass will consolidate same-as chains into single PIDs once the authority_xref Wikidata QIDs are resolved across all three layers.

---

## How sources map to canonical namespaces

| Canonical namespace | Primary sources | Secondary sources |
|---------------------|-----------------|-------------------|
| `place` | Le Strange, major_cities, all_dynasties_enriched.capital_*, evliya, ibn-battuta, maqrizi-khitat | konya-city-atlas (institutional places), darp-islam.mint_location |
| `dynasty` | Bosworth (all_dynasties_enriched + all_rulers_merged + dynasty_relations + dynasty_analytics) | — |
| `person` (P0.2) | scholars, alam, dia, ei1, isnad_chains, scholar_identity | bosworth-rulers (promotion from inline) |
| `work` (P0.2) | dia_works, ei1_works | scholars.major_work, alam.referenced_works |
| `manuscript` (P0.3) | (not in this archive — comes from external sources Phase 0.3+) | — |
| `event` (P0.3) | battles, events, causal_links, diplomacy, evliya.voyages, ibn-battuta.voyages | dynasty foundings/falls (synthesized) |
| `institution` (P1) | konya-city-atlas, monuments | maqrizi-khitat structures |
| `route` (P1) | trade_routes, ibn_battuta_routes.geojson, evliya voyages | — |

---

## Hafta 2 takeaway

Manual transcription is no longer needed. The Bosworth pilot becomes:
1. CSV-driven adapter (`pipelines/adapters/bosworth/extract.py` reads CSVs).
2. All 186 dynasties canonicalized in one pass (not 10).
3. 830 rulers populated as `dynasty.rulers[]` inline arrays.
4. Predecessor/successor populated from `dynasty_relations.csv` in second pass.
5. Wikidata reconciliation runs against ~186 entities (cache hit-rate likely high).
