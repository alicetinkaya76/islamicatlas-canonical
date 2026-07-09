# Hafta 3 Deliverable — Place Namespace Pilot (Yâqūt + Muqaddasī + Le Strange)

**Status:** ✅ All 19 acceptance criteria green (sandbox verified, 2026-05-03).

## What's in this delivery

Three classical/orientalist gazetteer adapters, a shared place-canonicalization library, three integrity passes, capital backfill, and a comprehensive integration test suite. All running end-to-end.

### Adapter outputs (sandbox verified)

| Adapter | Records | Time | Notes |
|---------|---------|------|-------|
| **Yâqūt** | 12,954 | 93.7 s | All schema-valid; 13,721/15,239 (90%) have coords thanks to the 5-level geo_confidence stratification merge with project's rich format (Y3.7 (c) merge decision). |
| **Muqaddasī** | 2,070 (21 iqlim + 2,049 places) | 25.6 s | First use of `iac:Iqlim` subtype; 1,081/2,049 places carry yaqut_id cross-refs. |
| **Le Strange** | 215 new + 218 augmentations | 3.1 s | 274/434 sidecar augments existing Yâqūt PIDs; 160 new + 55 special cases mint new PIDs. |
| **Total place namespace** | **15,239 records** | ~2 min | All schema-valid, no errors. |

### Integrity passes

| Pass | Input | Output | Result |
|------|-------|--------|--------|
| **1. Parent resolution** | 2,699 yaqut entries with parent_locations | located_in[] field | **1,427/2,699 (53%)** resolved (1,309 fully + 118 partial). 1,272 unresolved are tribe names ("العرب", "غطفان"), generic regions ("مصر"), or non-place referents. |
| **2. Muqaddasī ↔ Yâqūt** | 1,081 cross-refs | Bidirectional `derived_from_layers` + cross-ref note on both records | **1,081/1,081 (100%)** applied. |
| **3. Le Strange augmentation** | 218 yaqut PIDs to augment | derived_from_layers += "le-strange", altLabel += le_strange_form, page/chapter provenance entry | **218/218 (100%)** applied. |

### Capital backfill (Bosworth integration)

- 186 dynasty capital_name strings → fuzzy-match against the place namespace
- 67 fully resolved + 30 partially resolved = **97 total dynasties** with had_capital[] populated
- 83 unresolved: modern places (Riyadh post-1229, Benghazi, Zanzibar) + TR/AR transliteration disagreements (Bosworth's "Halep" ≠ Yâqūt content team's "Haleb"; "Mayorka" ≠ "Mayūrqa"). These need a curated trilingual disambiguation table — separate human-editorial task.

## Acceptance criteria (19/19 green)

```
TestPlaceNamespaceVolume
  ✓ test_a1_total_record_count        (15,239 within [14k, 16k])
  ✓ test_a2_filename_pattern          (all iac_place_NNNNNNNN.json)

TestSchemaValidity
  ✓ test_b_all_records_schema_valid   (15,239/15,239 valid)

TestSpotChecks
  ✓ test_c[Mekke]                     (matched)
  ✓ test_c[Bağdat]                    (matched)
  ✓ test_c[Dımaşk]                    (matched)
  ✓ test_c[Haleb]                     (matched, content-team transliteration)
  ✓ test_c[el-Kûfe]                   (matched, content-team transliteration)

TestProvenance
  ✓ test_d_provenance_complete        (sample of 500, all complete)

TestLayerCoverage
  ✓ test_e_layer_coverage             (yaqut=14035, makdisi=3025, le-strange=433)

TestParentResolution
  ✓ test_f_located_in_count           (1,427 ≥ threshold 1,000)
  ✓ test_f2_located_in_format         (all match iac:place-NNNNNNNN pattern)

TestCrossSourceMerge
  ✓ test_g_records_with_multiple_layers  (>200 with 2+ layers; 99 with all 3)

TestCapitalBackfill
  ✓ test_h_capital_backfill           (97 ≥ threshold 90)

TestIdempotency
  ✓ test_i_pid_minter_idempotent      (PID index count = file count)

TestSidecarCompleteness
  ✓ test_j[yaqut_parent_pending]      (2,699 entries)
  ✓ test_j[yaqut_persons_pending]     (606 entries)
  ✓ test_j[muqaddasi_yaqut_xref]      (1,081 entries)
  ✓ test_j[le_strange_augment]        (218 entries)
```

## What's new in the codebase

### New files

```
pipelines/_lib/place_canonicalize.py             (shared lib, ~340 lines)
pipelines/adapters/yaqut/
  manifest.yaml
  extract.py          (joins lite + detail + crossref + optional rich format)
  canonicalize.py     (~330 lines, geo_confidence-aware coord builder)
  resolve.py
  seed/wikidata_qid_seed.json
pipelines/adapters/muqaddasi/
  manifest.yaml
  extract.py          (yields iqlim + place records)
  canonicalize.py     (~270 lines, two-track logic for iqlim vs settlement)
  resolve.py
  seed/wikidata_qid_seed.json
pipelines/adapters/le_strange/
  manifest.yaml
  extract.py
  canonicalize.py     (~210 lines, augmentation track via sidecar)
  resolve.py
  seed/wikidata_qid_seed.json
pipelines/integrity/place_integrity.py           (~480 lines, 3 passes)
pipelines/integrity/backfill_capitals.py         (~270 lines)
tests/integration/test_yaqut_pilot.py            (~250 lines, 19 tests)
.gitignore                                       (canonical, _state, dia_chunks excluded)
```

### Modified files

```
pipelines/run_adapter.py                         (multi-sidecar support, hyphen→underscore folder fallback)
pipelines/adapters/registry.yaml                 (yaqut/muqaddasi/le-strange enabled=true)
data/sources/INVENTORY.md                        (Hafta 3 datasets documented)
```

### Source datasets imported (committed to repo)

```
data/sources/yaqut/
  yaqut_lite.json
  yaqut_detail.json
  yaqut_crossref.json
data/sources/muqaddasi/
  muqaddasi_atlas_layer.json
  muqaddasi_xref.json
```

`data/sources/le-strange/` was already in repo from Hafta 1 baseline.

## Live reconciliation note

Sandbox runs use `--recon-mode offline` (no Wikidata API). All 19 acceptance tests pass without live recon. To enrich with Wikidata QIDs:

```bash
# Targeted recon: only entries with coords or DİA xref or alam crossref
# (~7,500 entries × ~1.7 s = ~3.5 hours)
python3 pipelines/run_adapter.py --id yaqut --recon-mode auto

# Muqaddasī: only certain/exact certainty places (~989 entries × ~1.7 s = ~28 minutes)
python3 pipelines/run_adapter.py --id muqaddasi --recon-mode auto

# Le Strange: cities/towns/fortresses only (~350 entries × ~1.7 s = ~10 minutes)
python3 pipelines/run_adapter.py --id le-strange --recon-mode auto

# Re-run integrity passes (idempotent)
python3 pipelines/integrity/place_integrity.py --all
python3 pipelines/integrity/backfill_capitals.py
```

The cache at `data/cache/wikidata_reconcile.sqlite` makes re-runs very fast.

## Known limitations (deferred)

1. **DİA in authority_xref:** v0.1.0 schema enum is `[wikidata, pleiades, viaf, geonames, openiti, tgn, lcnaf, isni, gnd, bnf]` — no `dia`. Currently DİA cross-references go in the `note` field. Schema migration to v0.2.0 will add `dia` to the enum and a one-shot script will move 6,089 DİA refs from notes to authority_xref entries.

2. **Yâqūt geo_type subtype gaps:** schema has 3 subtypes (settlement/region/iqlim). Yâqūt's 80 geo_types include mountain (1,213), river (328), well (237), monastery (170), spring (128), pass (85), etc. — none of these get a subtype. The original geo_type is preserved in the `note` field; Phase 0.3+ will add `iac:Mountain`, `iac:RiverSystem`, `iac:Desert` subtypes.

3. **Capital backfill TR-AR disagreement:** Bosworth content team uses modern Turkish ("Halep", "Mayorka", "Maskat") while Yâqūt content team uses classical Turkish transliteration ("Haleb", "Mayūrqa", "Muscat"). 50% of the 83 unresolved Bosworth capitals fail for this reason. A curated TR-disambiguation table (~30 entries) would close this gap; deferred to Hafta 4 or as a separate maintenance task.

4. **dia_chunks.json (70 MB):** still gitignored. Hafta 4 person-namespace adapter consumes it at ingest; canonical records (also gitignored) reference chunk IDs. The raw file stays out of git until Phase 0.5 git-lfs migration.

5. **Live Wikidata recon:** sandbox cannot reach `wikidata.reconci.link`, so all sandbox runs are offline. The user runs live recon locally on their Mac.

## Files in this delivery zip

- Full repo state at `/home/claude/work/islamicatlas-canonical/` packaged as `hafta3.zip`.
- Excludes `data/canonical/` and `data/_state/` (regenerable from source data).
- Includes everything else: schemas, adapters, integrity, tests, source data, manifests.

## Next session: Hafta 4 — Person namespace seed

See `NEXT_SESSION_PROMPT_HAFTA4.md` for the handoff prompt.
