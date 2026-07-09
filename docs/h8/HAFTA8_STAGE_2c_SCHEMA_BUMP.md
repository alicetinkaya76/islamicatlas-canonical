# Hafta 8 — Stage 2c.1: Schema bump (ADR-012)

**Date:** 2026-05-17
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical

---

## What this commit does

ADR-012: bumps `schemas/_common/multilingual_text.schema.json`
`description.<lang>.maxLength` from **5,000** to **50,000** chars.

Trigger: H8 Stage 2b analyzer v2 measured per-slug aggregated
narrative length at median 6,337 chars (above 5K), p95 20,450, max
318,213. Under maxLength=5000, 68.8% of Cat A enrichment records
would truncate — unacceptable per ADR-011's academic credibility
argument.

Resolution at 50,000: 95% of records preserve full narrative;
long-tail (~5%, the canonical figures with massive entries) still
truncates per Karar 4 sentence-boundary strategy.

## Files touched

| Path | Change | Idempotent? |
|---|---|---|
| `schemas/_common/multilingual_text.schema.json` | Single line change: maxLength 5000 → 50000 + extended field description. `$id` unchanged (PE-2). | ✓ |
| `docs/decisions/ADR-012-description-maxlength-50k.md` | New ADR with empirical grounding | ✓ |
| `pipelines/migrations/h8_002_description_maxlength_50k.py` | New no-op-data re-validation migration | ✓ |
| `docs/h8/HAFTA8_STAGE_2c_SCHEMA_BUMP.md` | This journal | ✓ |

## What this stage does NOT do

- Does not bump `$id` of multilingual_text.schema.json (PE-2 deferred).
- Does not modify any `data/canonical/*.json` record.
- Does not touch test files; existing tests should pass unchanged.

## Acceptance criteria

- [ ] `python3 -m json.tool schemas/_common/multilingual_text.schema.json > /dev/null` — valid JSON.
- [ ] `description.<lang>.maxLength == 50000` in patched schema.
- [ ] `python3 pipelines/migrations/h8_002_description_maxlength_50k.py` — 46,702 records pass, 0 failures.
- [ ] `pytest tests/integration/` — remains 74 passed, 0 failed, 3 skipped, 3 xfailed.
- [ ] `git status` — exactly 4 paths (1 modified schema + 3 new files).

## Expected commit message

```
Hafta 8 Stage 2c.1: ADR-012 schema bump — description maxLength 5000 → 50000

- schemas/_common/multilingual_text.schema.json: bump
  description.<lang>.maxLength from 5000 to 50000 chars + extended field
  description (additive, backward-compatible; $id unchanged per PE-2)
- docs/decisions/ADR-012-description-maxlength-50k.md: new ADR with
  empirical grounding from Stage 2b analyzer v2 (median 6337 chars,
  p95 20450, max 318213; 68.8% would truncate at 5000)
- pipelines/migrations/h8_002_description_maxlength_50k.py: idempotent
  re-validation (no data mutation; 46,702 records expected green)
- docs/h8/HAFTA8_STAGE_2c_SCHEMA_BUMP.md: migration journal

Test: pytest tests/integration/ remains 74 passed; h8_002 reports 46702 green.

Sets stage for Stage 2c.2 (ADR-011 v1.1 doctrine commit referencing this).
```

## Rollback

`git revert <commit>` restores maxLength=5000. ADR-011 v1.1 (in
Stage 2c.2) would then have a dangling forward-reference; recommended
atomic revert: revert both 2c.1 + 2c.2 together.
