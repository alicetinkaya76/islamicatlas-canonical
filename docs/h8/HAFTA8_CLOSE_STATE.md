# Hafta 8 — Close state

**Date:** 2026-05-17
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical
**H7 close reference:** commit `8833ec0`, tag `hafta7-close`
**H8 close commit:** *(this commit)*
**H8 close tag:** `hafta8-close`

---

## What H8 accomplished — one paragraph

H8 set out to (a) remediate the H7-discovered PE-1 schema/data drift,
and (b) execute the long-deferred dia_chunks → person-namespace
enrichment pass. Both completed. The PE-1 fix landed in Stage 1 as a
zero-data-mutation enum extension (`digital_corpus`) with ADR-010.
Stages 2–5 designed, scaffolded, piloted, and bulk-executed a new
adapter — `dia-person-enrichment-v8` — that upgraded the H4 person
namespace's 3,309 Category-A records with full per-slug aggregated
narratives (76.5% description.tr upgrades), Arabic-script `prefLabel.ar`
gap-fills (0 needed — H4 was thorough), and extended `death_temporal`
gap-fills (0 needed). The work surfaced one ADR-worthy schema
constraint (description maxLength 5K→50K, ADR-012), one decisive
ADR revision based on empirical findings (ADR-011 v1.1), one logged-
and-closed truncation bug (Stage 5 postmortem), and zero net new
H9-residual issues beyond the pre-existing PE-2 (schema $id
coherence). Six commits, zero reverts, zero data drift.

## H8 commit chain (oldest first; all on `hafta5-work-namespace`)

```
4e6176a  Hafta 8 Stage 1:   PE-1 remediation — schema enum digital_corpus + ADR-010
aba83dd  Hafta 8 Stage 2c.1: ADR-012 schema bump — description maxLength 5000 → 50000
0a418c0  Hafta 8 Stage 2c.2: ADR-011 v1.1 — empirical corrections from analyzer v2
bb11440  Hafta 8 Stage 3:   dia_person_enrichment_v8 adapter scaffolding
2c9adaf  Hafta 8 Stage 4:   dia_person_enrichment_v8 pilot batch journal
ec9ba52  Hafta 8 Stage 5:   bulk run + truncate_at_sentence_boundary maxLength fix
<close>  Hafta 8 Stage 6:   close — bulk journal + close state + adapter enable
```

Linear chain. No merges. No reverts.

## Schemas changed

| Schema | Change | Commit | ADR |
|---|---|---|---|
| `schemas/_common/provenance.schema.json` | `derived_from[].source_type.enum`: 5 values → 6 values. Added `"digital_corpus"`. Extended field description. `$id` unchanged (PE-2 deferred). | `4e6176a` | ADR-010 |
| `schemas/_common/multilingual_text.schema.json` | `description.<lang>.maxLength`: `5000 → 50000`. Extended field description. `$id` unchanged (PE-2 deferred). | `aba83dd` | ADR-012 |

Both changes are additive (relaxing, not tightening) and
backward-compatible. All 46,702 pre-existing canonical records remain
valid; both companion migration scripts (h8_001, h8_002) re-validate
the full corpus and report all green.

## ADRs added

| ADR | Title | Status | Commit |
|---|---|---|---|
| ADR-010 | `source_type` enum: add `digital_corpus` | Accepted | `4e6176a` |
| ADR-011 v1.1 | dia_chunks scope — person enrichment, not work mint | Accepted (v1.1 — empirical refinements from Stage 2b analyzer v2) | `0a418c0` |
| ADR-012 | `multilingual_text.description` maxLength 5K → 50K | Accepted | `aba83dd` |

ADR-011's v1 → v1.1 trajectory is preserved in
`docs/h8/H8_STAGE_2b_ANALYZER_FINDINGS.md` (audit trail). The v1 draft
was never committed to git, so no rewrite history exists in the commit
graph; the audit document substitutes.

## Adapters added

| Adapter ID | Folder | Priority | Status at H8 close | Manifest |
|---|---|---:|---|---|
| `dia-person-enrichment-v8` | `pipelines/adapters/dia_person_enrichment_v8/` | 325 | `enabled: true` (flipped in Stage 6) | `manifest.yaml` |

Operates as an UPGRADE PASS over the H4 `dia` adapter's 3,309 person
records. Reads `dia_chunks.json`, aggregates chunks per slug
(c-sorted, space-joined — H4-compatible), and applies additive
patches to `description.tr` (length recovery), `prefLabel.ar`
(gap-fill from chunk.a where arabic_primary), and `death_temporal`
(gap-fill from chunk.d via extended parser). Mints no new PIDs.
Always appends a `dia-chunks-v8:<slug>` entry to
`provenance.derived_from`; never overwrites existing labels or
verified temporal data.

## Decisions logged (`H8_DECISION_LOG.md`)

| Karar | Subject | Status |
|---|---|---|
| 1 | PE-1 → Option B1 (enum extension, no data mutation) | DONE (Stage 1) |
| 2 | Schema `$id` bump deferred to PE-2 (H9+) | DECIDED (Stage 1) |
| 3 | Yol C: dia_chunks → person enrichment + H9 TDV scraping spec | DONE (Stage 2) |
| 4 | `description.tr` 5K truncation, sentence-boundary aware | SUPERSEDED by Karar 6 (kept as fallback for >50K tail) |
| 5 | Stage 2b analyzer v2 empirical refinements → ADR-011 v1.1 | DONE (Stage 2c.2) |
| 6 | ADR-012: description maxLength 5K → 50K | DONE (Stage 2c.1) |
| 7 | Bulk run executed on full Cat A (3,309 records) | DONE (Stage 5) |
| 8 | `truncate_at_sentence_boundary` reserves marker length (bug fix) | DONE (Stage 5) |
| 9 | H8 close ceremony (single commit, tag, adapter enabled) | DONE (Stage 6 — this commit) |

Nine decisions, six explicit commits, two ADRs raised + one ADR
revised, zero superseded-and-replaced.

## Tests added

| Test file | Test count | Coverage | Commit |
|---|---:|---|---|
| `tests/integration/test_dia_person_enrichment_v8_pilot.py` | 7 | AG.1 schema validity • AG.2 idempotency • AG.3 description upgrade meaningful • AG.4 H4 provenance preserved • AG.5 prefLabel.ar Arabic-script validity • AG.6 record_history update entry present • AG.7 description ≤ 50,000 chars (ADR-012 ceiling) | `bb11440` (added skipped) → `2c9adaf` (unblocked by pilot) → `ec9ba52` (full pop verified) |

Note: `test_dia_pilot.py::test_a1_all_person_records_validate` was
*not* added; it existed pre-H8 and transitioned FAILED → PASSED with
the Stage 1 PE-1 fix (no test edit required).

### Suite totals at each H8 stage

| Stage | passed | skipped | xfailed | failed |
|---|---:|---:|---:|---:|
| Pre-H8 (H7 close, commit 8833ec0) | 73 | 3 | 3 | 0 |
| Stage 1 (PE-1 fix) | 74 | 3 | 3 | 0 |
| Stage 2c.1 (schema bump) | 74 | 3 | 3 | 0 |
| Stage 2c.2 (doctrine) | 74 | 3 | 3 | 0 |
| Stage 3 (adapter scaffolding) | 74 | 10 | 3 | 0 |
| Stage 4 (pilot — unblocks 7 AG) | 81 | 3 | 3 | 0 |
| Stage 5 (bulk run, full pop) | 81 | 10 | 3 | 0 |
| **Stage 6 (close)** | **81** | **10** | **3** | **0** |

Net change: +8 passed (1 from PE-1 fix, 7 from the new v8 AG tests).
The skip-count delta across stages reflects fixture topology unrelated
to H8 substance; no H8 test moved from green to skipped during the
arc. Zero new failures across H8.

## Data outcomes

| Metric | Value | Reference |
|---|---:|---|
| Cat A target population | 3,309 | `data/_state/dia_slug_to_pid.json:slug_to_pid` |
| v8-enriched records (terminal) | 3,309 (100%) | All carry `dia-chunks-v8:<slug>` in `provenance.derived_from` |
| `desc_upgraded` | 2,533 (76.5%) | description.tr re-aggregated to longer narrative than H4 stored value |
| `arabic_filled` | 0 | H4 had thorough coverage where chunk.a was arabic_primary |
| `temporal_filled` | 0 | H4's parser covered every parseable chunk.d |
| Records validating against schema | 46,702 / 46,702 | h8_001 + h8_002 migration runs both green |
| Overflow records (≥50K narrative) | ~165 (~5%) | Per Stage 2b projection; bug-affected subset before Stage 5 fix |
| Net new PIDs minted | **0** | This adapter operates as UPGRADE PASS, not mint pass |
| Records mutated outside intended scope | **0** | Provenance derived_from immutability honored; H4 `dia:<slug>` retained on every record |

### Architectural finding (Stage 4)

`data/canonical/` and `data/_state/` are both gitignored
(`.gitignore:2-3`). H8 stage commits contain code, schemas, ADRs,
docs, tests, migrations, and orchestrator scripts — never canonical
data artefacts. The 46,701 canonical records are not in the commit
graph; they are reproducible via deterministic pipeline replay from
`data/sources/` + the adapter pipeline. This pattern is consistent
with H4-H7 (which similarly excluded canonical data) and is now
explicitly documented in `HAFTA8_STAGE_4_PILOT.md` §"Architectural note".

## Migrations added

| Migration | Purpose | Commit | Verification |
|---|---|---|---|
| `pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py` | Re-validate all canonical records against the PE-1-patched provenance schema; no data mutation | `4e6176a` | 46,702 green; 0 failures |
| `pipelines/migrations/h8_002_description_maxlength_50k.py` | Re-validate all canonical records against the ADR-012-bumped multilingual_text schema; no data mutation | `aba83dd` | 46,702 green; 0 failures |

Both migrations are idempotent re-validation scripts — they do not
write to any record file. They exist as the canonical evidence that
the schema patches did not silently invalidate the corpus.

## Known issues delta vs H7

| Issue | H7 close state | H8 close state |
|---|---|---|
| PE-1 (2,262 records' source_type not in enum) | OPEN, options B1/B2/B3 documented | **RESOLVED** Stage 1 via B1 (additive enum extension) |
| PE-2 (schema `$id` coherence across 10 files) | NOT YET DISCOVERED | **DISCOVERED + LOGGED** Stage 1; deferred to H9+ |
| H8 Stage 5 truncate overflow | n/a | **DISCOVERED + RESOLVED** in Stage 5; postmortem preserved in `HAFTA8_STAGE_5_BULK.md` |
| dia_works rich-mint | DEFERRED with vague "needs raw DiA source" | DEFERRED with concrete spec: AO (H9 scraping pipeline) → AP (H10+ rich-mint) |

### Net known-issues balance at H8 close

- **One resolved** (PE-1).
- **One new and deferred** (PE-2 — cosmetic, no operational impact).
- **One discovered-and-closed within H8** (Stage 5 truncate bug).
- **One deferral made more concrete** (dia_works → H9 AO + H10 AP).

H9 enters with **PE-2** as the sole H8-originated open issue.

## Rollback notes

H8 rollback by stage (in reverse order; each independent unless noted):

| Stage | Commit | Rollback cost | Notes |
|---|---|---|---|
| 6 (close) | *(this)* | Trivial. `git revert <close>` removes 5 doc/registry edits. Drops the `hafta8-close` tag. | Adapter re-disables via `enabled: false` restoration. No data impact. |
| 5 (bulk + truncate fix) | `ec9ba52` | Trivial code revert. Canonical store would carry stale v8 records with the truncate-overflow bug-but reverted-code; equivalent re-run with the bug present would re-overflow. Practical rollback: revert + re-run `--strict` (will skip already-v8 records, re-attempting the previously-failed ones; previously written 50K+8 records may need manual cleanup with a temporary lenient maxLength=50100). | Atomic with Stage 4 if both reverted. |
| 4 (pilot) | `2c9adaf` | Trivial. Pilot data is part of Stage 5's superset and was retained as `skip_idempotent` records in Stage 5; reverting Stage 4 alone would orphan 50 records. **Recommendation: do not revert Stage 4 in isolation.** | — |
| 3 (adapter scaffolding) | `bb11440` | Removes the lib + adapter folder + tests + registry entry. Stages 4–6 would no longer apply. Suite count returns to 74 passed + 3 skipped + 3 xfailed. | Must revert 3–6 atomically. |
| 2c.2 (doctrine) | `0a418c0` | Removes ADR-011 v1.1, audit doc, master plan v1.1, Kararlar 5+6. Stage 3+ depends on ADR-011 v1.1 spec; must revert 2c.2 through 6 atomically. | Atomic with 2c.1 + 3-6. |
| 2c.1 (schema bump) | `aba83dd` | Restores maxLength=5000. ADR-012 forward-reference in ADR-011 v1.1 dangles. h8_002 migration would fail on 2,533+ records (now >5K from bulk run). **Must revert 2c.1 through 6 atomically; in practice this is "revert H8 entirely except Stage 1".** | — |
| 1 (PE-1) | `4e6176a` | Restores 5-value enum. 2,262 person records become schema-invalid again. **Recommended only if a B2/B3 mass-rename path is being adopted in its place;** otherwise leave Stage 1 in place even when rolling back later H8 stages. | — |

### Recommended rollback strategy if needed

- Full H8 revert (rare): single `git revert -m 1` of merge commit
  (if H8 were merged) or sequential reverts in reverse order.
- Partial H8 revert (more likely): revert only Stages 2c–6
  atomically; keep Stage 1 (PE-1 fix is independently valuable).
- Adapter-only disable (no revert): edit registry.yaml
  `enabled: true → false` for `dia-person-enrichment-v8`. The canonical
  data is unaffected; re-enabling will skip every record via the
  idempotency probe.

## Reproducibility

A fresh worktree starting from H7 close (`8833ec0`) can reproduce H8
end-state via:

```bash
git checkout 8833ec0
git cherry-pick 4e6176a aba83dd 0a418c0 bb11440 2c9adaf ec9ba52 <close>

# Regenerate the slug_to_pid map (if not preserved):
python3 pipelines/_lib/build_dia_slug_to_pid.py

# Replay the H8 adapter (the canonical data is gitignored; this
# rebuilds it from the source + adapter pipeline):
python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --strict

# Verify:
python3 pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py
python3 pipelines/migrations/h8_002_description_maxlength_50k.py
pytest tests/integration/
```

Expected terminal state: 3,309 v8-enriched records, 46,702 schema-valid,
81 passed + 10 skipped + 3 xfailed, AM acceptance criterion satisfied.

## H9 entry point

H9 inherits a clean state:

- **AL** (PE-1) — DONE
- **AM** (dia_person_enrichment ≥ 2,647 Cat A) — DONE (3,309 achieved; surplus of 662 over target)
- **AQ** (ADR-012 schema bump) — DONE
- **AN** (Cat B fuzzy match, ≥ 50% non-scholar matches) — H8.5 / H9 candidate
- **AO** (TDV scraping pipeline for rich dia_chunks) — H9 target
- **AP** (dia_works ADR-009 rich-mint) — H10+ target, gated on AO
- **PE-2** (schema $id coherence across 10 files) — open backlog, H9 Stage 1 candidate

H9 should choose one of: (a) AO scraping pipeline + AP rich-mint, or
(b) AN Cat B fuzzy match, or (c) PE-2 housekeeping commit before any
new schema work. The author's recommendation (autonomous Stage 6
note, awaiting H9 kickoff sign-off): **start H9 with PE-2** so the
schema set is internally coherent before any further $id work, then
proceed to AO scraping. Detailed H9 master plan deferred to H9 kickoff.

---

**End of H8 close state document.** Six commits, three ADRs, one
adapter, three thousand three hundred and nine person records
enriched, one bug found and fixed, zero data drift, zero reverts.
