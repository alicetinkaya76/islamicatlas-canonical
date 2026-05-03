# Bosworth — The New Islamic Dynasties (EUP 2004)

Seeds the `iac:dynasty-*` namespace from C. E. Bosworth's *The New Islamic Dynasties: A Chronological and Genealogical Manual*, the standard tertiary reference for Islamicate political continuity (186 NIDs covering Rāshidūn → Brunei).

This is the **Hafta 2** ETL pilot of Phase 0. All 186 dynasties are canonicalized in one CSV-driven pass.

## Source

| Edition | Year | Publisher |
|--|--|--|
| The New Islamic Dynasties (NID) | 2004 | Edinburgh University Press, paperback reprint |

Upstream tabularization (the `data/sources/bosworth/*.csv` bundle) was prepared by the islamicatlas.org content team. The CSV ships pre-aligned to Bosworth's NID numbering (`dynasty_id` column ↔ NID-001 … NID-186). The schema is documented in `data/sources/bosworth/DATA_DICTIONARY.md`.

The actual CSV ships **52 columns** (the data dictionary lists 44; eight tail-fields appended by the content team — `narrative_tr/en`, `key_contribution_tr/en`, `rise_reason_tr`, `fall_reason_tr`, `context_before_tr`, `context_after_tr`). The adapter handles both shapes.

## License

**Fair use.** The canonical store records *derivative facts* — names, dates, regnal lists, chapter pointers, NID numbers. Bosworth's narrative prose is not redistributed.

The CSV bundle's `narrative_*` and `key_contribution_*` fields are summary text written by the islamicatlas.org content team (not from Bosworth verbatim) and are emitted under the canonical store's CC-BY-SA 4.0 license as `labels.description.{en,tr}` and `note`.

## CSV → schema mapping

| CSV column | Canonical field |
|---|---|
| `dynasty_id` | minted PID via `bosworth-nid:{id}` input_hash → `iac:dynasty-NNNNNNNN` |
| `chapter` | `bosworth_id` (formatted `NID-{:03d}`) |
| `dynasty_name_en/tr/ar` | `labels.prefLabel.{en, tr, ar | ar-Latn-x-alalc}` (Arabic-script vs. transliteration distinguished by Unicode block) |
| `narrative_en/tr` | `labels.description.{en, tr}` |
| `key_contribution_en/tr` | concatenated into `note` |
| `date_start_ce/end_ce`, `date_start_hijri/end_hijri` | `temporal.{start_ce, end_ce, start_ah, end_ah}` (with end ≥ start invariant; if violated, the inconsistent `end_*` is dropped) |
| `government_type` | drives `dynasty_subtype` + `@type` array (see mapping table below) |
| `end_cause` | appended to `note` |
| `predecessor` / `successor` (Turkish free-text in main CSV) | **ignored** — predecessor/successor PIDs are resolved separately from `dynasty_relations.csv` `selef` rows in `pipelines/integrity/check_all.py` (second pass) |
| `capital_city`, `capital_lat`, `capital_lon` | **sidecar** → `data/_state/bosworth_capital_pending.json` (Hafta 3 backfills `had_capital[]` once Yâqūt populates `iac:place-*`) |
| `regions_all`, `region_primary` | **sidecar** → same file (Hafta 3 backfills `territory[]`) |
| rulers (joined from `all_rulers_merged.csv` by `dynasty_id`) | `rulers[]`: `name` (= `short_name` ‖ `full_name_original`), `name_ar` (only when full name contains Arabic-script Unicode), `regnal_title` (= `title` ‖ `laqab`), reign CE/AH from `reign_start_ce` etc., loose-year strings (`c. 1012`, `1056?`) parsed leniently and dropped if unparseable |

### Government type mapping

The CSV uses 12 Turkish values; the schema has 5 English enum values:

| CSV value | `dynasty_subtype` |
|---|---|
| Hilafet | caliphate |
| Sultanlık | sultanate |
| Şahlık | sultanate (Persian-style monarchy ≈ sultanate in the schema's coarse taxonomy) |
| Hanlık | sultanate (post-Mongol khanate ≈ sovereign monarchy) |
| Emirlik | emirate |
| Atabeglik | emirate (atabegs as regional sub-sovereigns) |
| İmamet | imamate |
| Beylik | beylik |
| Hanedan/Beylik | beylik (mostly small Anatolian/Caucasian principalities) |
| Mixed (`Hanlık\|Beylik`, `Sultanlık\|Şahlık`, `Sultanlık\|Emirlik`) | **omit** — record stays at `@type: ["iac:Dynasty"]`; raw value preserved verbatim in `note` |

Result: ~95% of records get a subtype; the remainder are left unannotated rather than force-fit into a category they don't belong in.

## Two-pass canonicalization

* **Pass 1** (`canonicalize.py`): mint PIDs, emit canonical records *without* `predecessor` / `successor` / `had_capital` / `territory`. Capital + region info goes to the sidecar JSON.

* **Pass 2** (`pipelines/integrity/check_all.py`): walk `dynasty_relations.csv`. For each `selef` row (`dynasty_id_1` is predecessor of `dynasty_id_2`), look up both PIDs via the minter's idempotent index and append:
  - `predecessor` array on the canonical file at `id_2`
  - `successor` array on the canonical file at `id_1`
  Re-validate. The bidirectional invariant is enforced: every `predecessor` link has a matching `successor` link on the other side.

## Reconciliation

Live API: `https://wikidata.reconci.link/en/api` (OpenRefine recon protocol). SQLite cache at `data/cache/wikidata_reconcile.sqlite` (TTL 30 days). Type hint: `Q164950` (caliphate); the API matches subclasses too.

Thresholds (from `manifest.yaml`): `auto_accept ≥ 0.85`, `review ≥ 0.70`, drop below.

A small **offline seed** of 26 high-confidence QIDs (canonical caliphates, sultanates, the Mongol succession, Mughal/Safavid/Ottoman/Qajar) ships at `seed/wikidata_qid_seed.json`. This guarantees the adapter produces meaningful `authority_xref` entries even when the recon API is unreachable. The seed is curator-verified and overrides any cache or API result. Run `python3 pipelines/_lib/wikidata_reconcile.py --inspect --cache data/cache/wikidata_reconcile.sqlite --seed pipelines/adapters/bosworth/seed/wikidata_qid_seed.json` to view stats.

## Known issues

* **Anatolian beyliks** (~30–40 records): Wikidata coverage is sparse. The recon API will frequently return no auto-match for these; they accumulate in `data/review_queue/bosworth.jsonl` (medium-confidence) or simply remain without `authority_xref`. The Hafta 2 acceptance criterion (≥70% reconciled) tolerates this.

* **Cairo Abbasid line (1261–1517)**: Bosworth records the entire 750–1517 span as NID-3, not as a separate dynasty. Per default decision **H2.5/H2.7**, we keep this as one canonical entity and note the Cairo continuation in the `temporal.note` / `record.note` field. A future schema-stable split is deferred.

* **Loose ruler dates (199 rows)**: `reign_start_ce` values like `"c. 1012"`, `"1056?"`, `"755/56"` are parsed by stripping `c.` / `?` / fraction tail. If the result is still unparseable, the field is dropped (the rulers schema only requires `name`).

* **Non-numeric ruler ordering**: when `reign_order` and `reign_start_ce` disagree about the chronological order, canonicalize.py re-sorts by `reign_start_ce`; rulers without a known start year keep their relative position at the tail.

* **Mixed government types**: 5 records (e.g., `Hanlık|Beylik`) leave `dynasty_subtype` unset. Search faceting by subtype will exclude them; that is the correct behaviour for entities whose category is genuinely contested in the source.

## Running

```bash
python3 pipelines/run_adapter.py --id bosworth
python3 pipelines/integrity/check_all.py --adapter bosworth
python3 pipelines/_index/build_lookup.py --rebuild
python3 pipelines/search/full_reindex.py --dry-run
```

Acceptance check:
```bash
python3 tests/integration/test_bosworth_pilot.py
python3 tests/run_schema_tests.py        # 15/15 must still pass
python3 tests/test_projector.py          # 3/3 must still pass
python3 tests/test_resolver.py           # 5/5 must still pass
```
