# Hafta 8 — Stage 3: dia_person_enrichment_v8 adapter

**Date:** 2026-05-17
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical

---

## What this stage produces

A new ADR-006-compliant adapter `dia-person-enrichment-v8` (folder name:
`dia_person_enrichment_v8/` per run_adapter.py hyphen→underscore translation)
that operates as an UPGRADE PASS for the existing H4 `dia` adapter output.

H4 already minted 3,309 person records from dia_chunks. H4 truncated
description.tr at 5,000 chars (68.8% affected per Stage 2b analyzer v2),
and sometimes left prefLabel.ar empty when chunk.a was Arabic-script.
This adapter UPGRADES those records — never overwrites, only fills gaps
and extends truncations.

## Adapter strategy

For each Cat A slug (3,309 slugs in dia_slug_to_pid.slug_to_pid):
1. **Extract**: read dia_chunks, group by slug, sort each group by `c`,
   concat `t` with space (H4-compatible). Filter to Cat A.
2. **Read existing**: open `data/canonical/person/iac_person_<id>.json`.
3. **Idempotency probe**: if `provenance.derived_from` already contains
   a `dia-chunks-v8:<slug>` entry, skip.
4. **Patch additively**:
   - `labels.description.tr` — upgrade to full aggregated (≤50K, ADR-012)
     iff new is longer AND existing is a verifying prefix (200-char window).
   - `labels.prefLabel.ar` — gap-fill from chunk.a iff existing absent
     AND `classify_arabic_script(chunk.a) == "arabic_primary"`.
   - `death_temporal` — gap-fill from chunk.d iff existing absent AND
     parseable by extended parser (5 formats).
5. **Augment provenance**:
   - `derived_from`: APPEND `dia-chunks-v8:<slug>` entry.
   - `record_history`: APPEND update entry describing the changes.
   - `modified`: UPDATE to now().
6. **Yield**: run_adapter.py validates against person.schema.json and writes.

## Why per-slug aggregation matches H4

Stage 2b analyzer v2 measured: 19,742 chunks → 8,093 distinct slugs
(avg 2.44 chunks/slug). H4 adapter's `extract.py` already uses
`" ".join(c.get("t", "") for c in slug_chunks if c.get("t"))` with c-sort.
Our `dia_enrichment_lib.aggregate_chunks_by_slug` mirrors this exactly,
so the first 5000 chars of our v8 aggregated narrative are BYTE-IDENTICAL
to H4's description.tr. The 200-char prefix verification in
`_apply_h8_patches` exploits this for safety.

## Files produced

| Path | Purpose |
|---|---|
| `pipelines/_lib/dia_enrichment_lib.py` | Aggregation, Arabic classification, extended date parser, sentence-boundary truncation, provenance entry builder, idempotency probe |
| `pipelines/adapters/dia_person_enrichment_v8/__init__.py` | Package marker |
| `pipelines/adapters/dia_person_enrichment_v8/manifest.yaml` | ADR-006 manifest (target=person, recon disabled) |
| `pipelines/adapters/dia_person_enrichment_v8/extract.py` | Cat A filter + per-slug aggregation iterator |
| `pipelines/adapters/dia_person_enrichment_v8/canonicalize.py` | Read-merge-yield upgrade pattern |
| `tests/integration/test_dia_person_enrichment_v8_pilot.py` | 7 AG conformance tests (skip until Stage 4 pilot runs) |
| `pipelines/adapters/registry.yaml` | Append new entry at priority 325, `enabled: false` |
| `docs/h8/HAFTA8_STAGE_3_ADAPTER.md` | This journal |

## What is OUT of scope (per ADR-011 v1.1)

- Minting new PIDs (H4 already covered Cat A).
- Cat B/C slugs (4,784 — deferred to H8.5/H9 fuzzy match).
- Wikidata reconciliation (no new entities → manifest sets reconciliation.enabled: false).
- Overwriting H4 fields beyond description.tr upgrade (per ADR-011 v1.1
  conformance threshold (c'): "patch is additive — never overwrites
  existing labels.description.tr, never replaces a verified death_temporal;
  only fills gaps and appends").

## Acceptance criteria

- [x] All 7 files written, registry.yaml has new entry at priority 325, enabled: false
- [ ] `pytest tests/integration/` — remains 74 passed + 7 skipped (v8 tests skip
      until pilot runs)
- [ ] Dry-run smoke test: `python3 pipelines/run_adapter.py --id
      dia-person-enrichment-v8 --limit 1 --dry-run` yields 1 record without writing

## Stage 4-6 roadmap

**Stage 4 — Pilot batch (50 records)**:
```
python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --limit 50 --lenient
```
Then manual inspection:
- `git diff data/canonical/person/` — review 5 sample diffs
- Verify description.tr ends at sentence boundary (not mid-word)
- Verify prefLabel.ar new additions are valid Arabic
- Verify provenance.derived_from has BOTH dia:<slug> AND dia-chunks-v8:<slug>

If sample manual inspection passes, proceed to Stage 5.

**Stage 5 — Tests + bulk run prep**:
```
pytest tests/integration/test_dia_person_enrichment_v8_pilot.py -v
```
All 7 tests must pass against the 50-record pilot batch. If any fail,
fix and re-run pilot (the adapter is idempotent — re-run on already-v8
records is a no-op).

**Stage 6 — Bulk run + H8 close**:
```
# Flip enabled: true in registry.yaml (separate commit)
git commit -am 'H8 Stage 6: enable dia-person-enrichment-v8 for bulk run'
# Bulk run all 3,309 Cat A slugs
python3 pipelines/run_adapter.py --id dia-person-enrichment-v8 --strict
# Full suite re-validation
python3 pipelines/migrations/h8_002_description_maxlength_50k.py  # 46702 green
pytest tests/integration/  # 81 passed (74 baseline + 7 AG)
# H8 close commit + HAFTA8_CLOSE_STATE.md
```

## Rollback

`git revert <commit>` removes the new adapter folder, lib module, tests,
journal, and registry entry. Since `enabled: false` and no records were
actually written (Stage 3 only scaffolds), no data rollback needed.
For Stage 4-6 rollback (after records mutated), separate plan: re-run
adapter with --strict on the already-v8 records detects idempotency,
takes no action; manual `git checkout` of the pre-Stage-6 `data/canonical/`
commit if reversion needed.
