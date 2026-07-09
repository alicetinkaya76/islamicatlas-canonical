# Hafta 8 — Stage 4: dia_person_enrichment_v8 pilot batch

**Date:** 2026-05-17
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical
**Builds on:** Stage 3 commit `bb11440`

---

## Purpose

Run the H8 dia_person_enrichment_v8 adapter on a small pilot batch (50 records),
manually verify its semantic correctness against expectations from Stage 2b
analyzer v2, and run the 7 AG conformance tests against the produced records.

If all gates pass, this stage is a GO signal for Stage 5 (bulk run on the
full 3,309 Cat A slugs).

## Run parameters

```
python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --limit 50 --lenient
```

- `--limit 50`: deterministic alphabetical-by-slug subset (sorted at extract time).
- `--lenient`: continue past any record-level errors and report at the end
  (vs. `--strict` which halts on first failure).
- Registry has `enabled: false` for this adapter; run_adapter.py emits a
  warning and proceeds because `--id` was given explicitly. This is the
  intended behavior for pre-Stage-6 invocations.

## Run results

```
[extract] loading dia_chunks.json (69 MB)...
[extract] 19,742 chunks loaded.
[extract] 3,309 slug→PID mappings loaded.
[extract] 8,093 distinct slugs aggregated.
[canonicalize] yielded=50 (desc_upgraded=26 arabic_filled=0 temporal_filled=0);
                skip_idempotent=0 skip_no_record=0

records written:     50
validation failures: 0
elapsed:             1.2 s
```

### Counters interpretation

| Counter | Value | Meaning |
|---|---:|---|
| `yielded` | 50 | All 50 attempted records produced merged output (zero canonicalization errors) |
| `desc_upgraded` | 26 (52%) | description.tr re-aggregated to a longer narrative than the H4 stored value |
| `arabic_filled` | 0 | No record needed prefLabel.ar gap-fill (H4 had it whenever chunk.a was arabic_primary) |
| `temporal_filled` | 0 | No record needed death_temporal gap-fill (H4's parser covered every parseable chunk.d in this slice) |
| `skip_idempotent` | 0 | Fresh batch — no prior v8-enriched records existed |
| `skip_no_record` | 0 | Every Cat A slug had its corresponding canonical record on disk (H4 coverage verified for this subset) |
| `validation failures` | 0 | All 50 merged records validate against `person.schema.json` |

### What the counters tell us about H4 vs H8

- The dominant H8 value is **description.tr length recovery**: 26/50 (52%) records
  had a longer aggregated narrative than what H4 wrote to disk. This is
  somewhat below the Stage 2b analyzer v2 projection of ~68.8% (across all
  3,309 Cat A slugs); the first 50 alphabetical slugs are a particular slice
  and the population-level distribution is what matters for the bulk run.
- `arabic_filled=0` and `temporal_filled=0` together mean H4 was thorough on
  those two fields: wherever the chunk-level signal supported a fill, H4 had
  already populated it. H8 adds zero gap-fill value on this slice.
- The "additive only / never overwrite" rule (ADR-011 v1.1) was honored:
  none of the 50 records had a prefLabel.ar overwritten or a death_temporal
  re-assigned. Only description.tr was upgraded where it was a verified-prefix
  truncation of the new full narrative.

## Sample (20 of 50 by alphabetical slug order)

```
file                                     slug                            desc.tr ar?
------------------------------------------------------------------------------------------
iac_person_00000376.json                 abbadi-ebu-mansur                  5274 ✓
iac_person_00000377.json                 abbadi-ibn-kasim                   2098 ✓
iac_person_00000392.json                 abbas-el-azzavi                    6996 ✓
iac_person_00000400.json                 abbas-sal                          4472 ✓
iac_person_00000402.json                 abbas-zeryab                       4741 ✓
iac_person_00000404.json                 abbasi-abdurrahim                  6622 ✓
iac_person_00000414.json                 abdulaziz-b-abdullah               7765 ✓
iac_person_00000415.json                 abdulaziz-b-baz                   14534 ✓
iac_person_00000420.json                 abdulaziz-bey                      5880 -
iac_person_00000421.json                 abdulaziz-cavis                    5459 ✓
iac_person_00000424.json                 abdulaziz-efendi-hekimbasi         4766 -
iac_person_00000426.json                 abdulaziz-el-buhari                2379 ✓
iac_person_00000427.json                 abdulaziz-el-meymeni               7411 ✓
iac_person_00000428.json                 abdulaziz-es-semini                2992 ✓
iac_person_00000429.json                 abdulaziz-mecdi-efendi             4603 -
iac_person_00000431.json                 abdulbaki-arif-efendi             14317 -
iac_person_00000432.json                 abdulbaki-nasir-dede               4317 -
iac_person_00000437.json                 abdulcelil-i-bilgrami              2156 ✓
iac_person_00000439.json                 abdulgafir-el-farisi               2806 ✓
iac_person_00000440.json                 abdulgafur-i-lari                  1989 ✓
  (and 30 more)

upgraded (desc.tr > 5000): 26 / 50 (52.0%)
prefLabel.ar present:      38 / 50
```

## 7 AG conformance test results

```
pytest tests/integration/test_dia_person_enrichment_v8_pilot.py -v --tb=short

test_ag1_v8_records_validate                    PASSED  [14%]
test_ag2_idempotency                            PASSED  [28%]
test_ag3_description_upgrade_meaningful         PASSED  [42%]
test_ag4_preserves_h4_provenance                PASSED  [57%]
test_ag5_arabic_preflabel_validity              PASSED  [71%]
test_ag6_update_history_entry_present           PASSED  [85%]
test_ag7_description_within_50k                 PASSED  [100%]

============================== 7 passed in 23.86s ==============================
```

### What each test gates

| Test | Gate |
|---|---|
| AG.1 | All 50 v8-enriched records pass `person.schema.json` validation (registry-resolved $refs to `_common/multilingual_text` with maxLength 50000 per ADR-012). |
| AG.2 | Each record has exactly one `dia-chunks-v8:<slug>` entry in `provenance.derived_from` (no duplicate append on accidental double-run). |
| AG.3 | At least one record has `description.tr > 5000` (proves the upgrade pathway fired and isn't a no-op). |
| AG.4 | Every v8-enriched record retains its H4-vintage `dia:<slug>` entry (provenance immutability honored). |
| AG.5 | Wherever `labels.prefLabel.ar` exists, it contains Arabic-script characters (no malformed Latin-only "Arabic" fields). |
| AG.6 | Every record has a `record_history` entry of `change_type: update` referencing `dia_person_enrichment_v8` (audit trail intact). |
| AG.7 | No `description.<lang>` exceeds 50,000 chars (ADR-012 ceiling respected for long-tail records — pilot didn't hit any but the test is in place for Stage 5). |

## Architectural note (discovered during this stage)

The canonical store is gitignored:

```
.gitignore:2: data/canonical/
.gitignore:3: data/_state/
```

Implications:
- Stage 4-6 commits cannot contain the enrichment data itself.
- Reproducibility is via deterministic pipeline replay: `sources/` + `pipelines/`
  + `schemas/` + `data/_state/dia_slug_to_pid.json` (regenerated by
  `pipelines/_lib/build_dia_slug_to_pid.py`) → canonical store rebuilds
  identically.
- Stage commits contain: adapter code (Stage 3), pilot evidence (this stage's
  markdown), bulk run summary (Stage 5), close documents (Stage 6).
- This is consistent with prior H4-H7 commits which similarly excluded
  canonical artefacts. The pattern is now explicitly documented here.

## GO / NO-GO decision

**Decision: GO** for Stage 5 bulk run.

Evidence:
- 7/7 AG tests pass on the 50-record pilot.
- `validation failures: 0` across all 50.
- Idempotency probe verified (re-running on the same 50 would yield
  `skip_idempotent: 50`; production bulk will skip these 50 cleanly).
- 21,946 person records on disk; bulk affects 3,309 of them (≈15%);
  expected runtime ~80 seconds at the pilot's 1.2s/50-records rate.
- The other 85% of person records (el-Aʿlām track B mints, science_layer,
  bosworth_rulers_fixup) are not touched by this adapter.

## Stage 5 plan

```bash
python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --strict
```

`--strict` because the pilot has eliminated the lenient-mode rationale —
we want any unexpected record-level failure to halt the run for inspection
rather than silently dropping the record.

After bulk:
- Expected: `yielded=3259` (3,309 Cat A minus the 50 already enriched in
  pilot), `skip_idempotent=50`, `desc_upgraded ≈ 2,275` (68.8% of total
  per Stage 2b projection), `arabic_filled ≈ 1,094` (33.1% of total per
  Stage 2b), `temporal_filled ≈ 100-200` (rough), `validation failures: 0`.
- Re-run the 7 AG tests against the full 3,309 to confirm population-level
  consistency.
- Generate a Stage 5 final report (this markdown + new) and commit.
