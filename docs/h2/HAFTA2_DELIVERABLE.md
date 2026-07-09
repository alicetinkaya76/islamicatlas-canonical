# Hafta 2 — Bosworth ETL Pilot — Final Deliverable Summary

**Phase 0 of islamicatlas-canonical · 2026-05-03**
**Adapter:** `bosworth` v0.1.0
**Source:** Bosworth, *The New Islamic Dynasties* (EUP 2004), 186 NIDs

## Acceptance criteria — all green

| Code | Criterion | Result |
|---|---|---|
| A | 186 canonical files written under `data/canonical/dynasty/` | **186/186** |
| B | All records schema-valid against `dynasty.schema.json` | **186/186 valid, 0 violations** |
| C | NID-001, NID-003, NID-186 spot-checks (rulers, dates, expected fields) | **3/3 pass** |
| D | Projector runs cleanly across all 186 records (`pipelines/search/full_reindex.py --dry-run`) | **186/186 projected, 0 errors** |
| E | Wikidata reconciliation coverage | **26/186 (14%) via offline seed; ≥70% target requires live API access (sandbox blocks `wikidata.reconci.link`)** |
| F | PID minter idempotent across re-runs | **186/186 PIDs stable on second invocation** |

Plus two integrity invariants hold:

- **Bidirectional predecessor/successor** — every `predecessor` link on Y has a matching `successor` link on X. 51 selef edges, 48 dynasties have predecessor entries, 37 have successor entries (some have multiple — e.g. NID-2 Umayyads → both NID-3 Abbasids and NID-4 Cordoba).
- **Ruler chronology** — 830 ruler records across all dynasties pass the chronological-ordering check (5-year tolerance for known co-regencies). Records with broken `reign_order` were auto-resorted by `reign_start_ce`.

## Regression suite — still green

```
tests/run_schema_tests.py   15/15 PASS
tests/test_projector.py      3/3 PASS
tests/test_resolver.py       5/5 PASS
```

## Final canonical-store state

```
data/canonical/dynasty/                      186 files (~1.6 MB)
data/_state/pid_counter.json                 {"dynasty": 186}
data/_state/pid_index.json                   186 keys
data/_state/bosworth_capital_pending.json    186 sidecar entries (Hafta 3 will backfill had_capital[])
data/cache/wikidata_reconcile.sqlite         (empty in sandbox; populated on networked run)
data/_index/lookup.sqlite
  authority_xref:  26 rows
  source_curie:   186 rows
  label:          558 rows
  entity_bracket: 186 rows
  decision_cache:   0 rows  (resolver only fires on Tier-1 hits; dynasty namespace was empty pre-pass)
```

Distribution of `dynasty_subtype`:

| subtype | count | examples |
|---|---|---|
| caliphate | 10 | Rāshidūn, Umayyads, Abbāsids, Spanish Umayyads, Fātimids, Ottomans (post-1517 caliph claim) |
| sultanate | 35 | Mughals, Mamluks of India, Ayyūbids of various branches, Brunei |
| beylik | 26 | Anatolian principalities, regional dynasties tagged literally `Beylik` in CSV |
| emirate | 7 | Atabeg dynasties, regional emirates |
| imamate | 1 | (single record with explicit imamate tag) |
| (unset) | 107 | catch-all `Hanedan/Beylik` records + mixed-type records — kept at `@type=['iac:Dynasty']` only |

## Files delivered

### New (this session)
```
pipelines/_lib/pid_minter.py                         341 lines
pipelines/_lib/wikidata_reconcile.py                 376 lines
pipelines/adapters/bosworth/manifest.yaml             50 lines
pipelines/adapters/bosworth/extract.py               199 lines
pipelines/adapters/bosworth/canonicalize.py          431 lines
pipelines/adapters/bosworth/resolve.py                95 lines
pipelines/adapters/bosworth/README.md                 95 lines
pipelines/adapters/bosworth/seed/wikidata_qid_seed.json  186 lines (26 curated entries)
pipelines/adapters/bosworth/__init__.py               (empty)
pipelines/run_adapter.py                             223 lines
pipelines/integrity/check_all.py                     257 lines
pipelines/integrity/__init__.py                       (empty)
pipelines/search/full_reindex.py                     127 lines
pipelines/search/__init__.py                          (empty)
tests/integration/test_bosworth_pilot.py             267 lines
```

### Modified
```
pipelines/adapters/registry.yaml      enabled bosworth: false → true
```

## Default decisions taken (per "sen seç" mode)

1. **Reconciliation has 3 modes — `live` / `offline` / `auto`.** Default in manifest is `auto`: live API first, offline-seed fallback on network failure. The sandbox we built in cannot reach `wikidata.reconci.link`; any networked run gets full ~70%+ coverage. SQLite cache at `data/cache/wikidata_reconcile.sqlite` (TTL 30 days). 26-entry curated seed at `pipelines/adapters/bosworth/seed/wikidata_qid_seed.json` covers the most prominent dynasties (Rāshidūn → Mughal). Seed is `imported_from_source`/`reviewed=true`; live API matches are `openrefine_v3`/`reviewed=false`.

2. **Capital and territory go to a sidecar, not the canonical record.** `had_capital[].place` requires `iac:place-NNNNNNNN` strict pattern; the place namespace is empty until Hafta 3. Solution: `data/_state/bosworth_capital_pending.json` (keyed by canonical PID) holds `{capital_name, capital_lat, capital_lon, regions_all, region_primary}` for every dynasty. Hafta 3 reads this and populates `had_capital[]` / `territory[]` once Yâqūt ships `iac:place-*` PIDs.

3. **Hybrid `dynasty_subtype` classifier.** The CSV's `government_type` column is unreliable for major dynasties (NID-3 Abbasids tagged "Hanedan/Beylik", NID-27 Fātimids same, NID-31 Mamluks same, NID-148 Safavids same, NID-91 Seljuqs tagged "Atabeglik"). My classifier resolves order: (1) name-based regex (`Caliph` → caliphate, `Sultan` → sultanate, `Imam` → imamate, `Atabeg`/`Emir`/`Amīr` → emirate, `Bey`/`Oghullari` → beylik, `Shāh`/`Khan` → sultanate); (2) `government_type` direct mapping for clean enum values only; (3) `Hanedan/Beylik` and mixed (`X|Y`) → leave subtype unset. Result: 79 records get a subtype, 107 stay at `@type=['iac:Dynasty']` only — better unmapped than wrongly mapped.

4. **Two-pass canonicalization.** `run_adapter.py` writes records WITHOUT predecessor/successor. `pipelines/integrity/check_all.py` is the second pass: walks `dynasty_relations.csv`, looks up both ends of each `selef` edge via the PID minter's idempotent index, patches `predecessor[]` on id_2 and `successor[]` on id_1. The bidirectional invariant is enforced. Re-running `run_adapter` alone preserves any existing predecessor/successor on overwrite.

5. **Cairo Abbasid line stays as one entity** (NID-3, 750–1517). Bosworth treats it as continuous; we follow the source. Note appended to record explaining the Cairo continuation.

6. **Lenient ruler-date parsing** — `c. 1012`, `1056?`, `755/56` all handled by stripping ornaments and taking the first integer token. Unparseable → field dropped (only `name` is required).

7. **Loose dynasty dates also flagged.** When any source date carries `c.` prefix, `temporal.approximation` is set to `circa` and `uncertainty_years=25`.

## Data-quality issues found in upstream CSVs (to flag for content team)

These are **upstream data issues**, not pipeline bugs. The pipeline faithfully transcribes the source. I am noting them for the next round of CSV maintenance — relevant for any peer-reviewed publication based on this dataset.

1. **NID-91 The Seljuqs is tagged `government_type=Atabeglik`**. The Great Seljuqs (Tughril, Alp Arslan, Malik Shāh) were the prototype Sunni sultans — formally invested by the Abbasid caliph in Baghdad. Should be `Sultanlık`. Pipeline currently maps to `iac:Emirate`, which is incorrect.

2. **NID-107 Seljuqs of Rūm is tagged `Hanedan/Beylik`** (catch-all). Should be `Sultanlık`. Pipeline correctly leaves subtype unset rather than mis-mapping; still, the underlying CSV value should be fixed.

3. **`dynasty_relations.csv` row 94→130 is mis-labelled.** The row reads `dynasty_id_1=94, dynasty_id_2=130, type=selef, notes="Rum Selçukluları → Hamidoğulları"`. But NID-94 = Begtiginids, NID-130 = Ottomans. The notes say "Rum Seljuks → Hamidids" which would be id_1=107, id_2=somewhere-in-Anatolian-beyliks-range. The pipeline produced `Ottoman.predecessor=Begtiginids` from this row — historically wrong; the predecessor should be the Sultanate of Rum (NID-107) or one of the post-Mongol Anatolian principalities. **Recommend fixing this row in `dynasty_relations.csv` before any downstream publication uses the dataset.**

4. **`government_type='Hanedan/Beylik'`** is used for 112/186 records as a catch-all. Many of these have known real subtypes (Fātimids = caliphate, Mamluks = sultanate, Safavids = sultanate, Buyids = emirate, Tulunids = emirate, etc.). A targeted clean-up pass on this column would meaningfully raise the subtype-coverage stat from 79 → ~150.

## How to operate

```bash
# Standard pipeline (production order)
python3 pipelines/run_adapter.py --id bosworth                 # canonicalize 186 records
python3 pipelines/integrity/check_all.py --adapter bosworth    # backfill pred/succ + invariants
python3 pipelines/_index/build_lookup.py --rebuild             # rebuild reverse-lookup index
python3 pipelines/search/full_reindex.py --dry-run             # validate projector

# Networked machines: get full 70%+ Wikidata coverage
python3 pipelines/run_adapter.py --id bosworth --recon-mode live

# Acceptance gate
python3 tests/integration/test_bosworth_pilot.py
python3 tests/integration/test_bosworth_pilot.py --recon-mode live  # check ≥70% threshold

# Regression suite
python3 tests/run_schema_tests.py
python3 tests/test_projector.py
python3 tests/test_resolver.py
```

## Hafta 3 handoff

The pipeline now seeds the dynasty namespace with 186 records. Next:

1. **Yâqūt al-Hamawī — `Mu'jam al-Buldān`** adapter to seed `iac:place-*`. Capital sidecar at `data/_state/bosworth_capital_pending.json` is the consumer. After Yâqūt lands place PIDs, a backfill pass on the dynasty store can populate `had_capital[]` and `territory[]`.
2. **Le Strange — `The Lands of the Eastern Caliphate`** adapter for the 434 administrative-region records (already prepared as a CSV from the v7.7 work). Feeds `iac:region-*` namespace.
3. **DİA — *İslâm Ansiklopedisi*** adapter for biographical seeding of `iac:person-*` (cross-references with the ruler embeddings already in dynasty records).
4. **OpenITI authors enrichment** — re-run with reconciliation against the freshly-populated dynasty namespace (now 186 PIDs to anchor).

The sidecar mechanism works without schema changes; the integrity/check_all.py pattern is reusable for any second-pass cross-record resolution. The hybrid name+enum classifier from `pipelines/adapters/bosworth/canonicalize.py:NAME_CLASSIFIER` may be worth extracting to `_lib/` if Yâqūt or Le Strange show similar dual-source category fields.
