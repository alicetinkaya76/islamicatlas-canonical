# Hafta 8 — Stage 2: Doctrine (dia_chunks pivot) — v1.1

**Date:** 2026-05-17
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical

---

## What this stage produces

Two atomic commits (in order):

**Commit 2c.1 — Schema bump (ADR-012 + multilingual_text patch + migration)**
**Commit 2c.2 — Doctrine corrections (ADR-011 v1.1 + audit docs)**

The split mirrors Stage 1's pattern (schema + ADR + migration grouped;
doctrine docs separate).

## Files written this stage

### Commit 2c.1 contents

| Path | Change | Idempotent? |
|---|---|---|
| `schemas/_common/multilingual_text.schema.json` | description.<lang>.maxLength 5000 → 50000 | ✓ (no-op if already 50000) |
| `docs/decisions/ADR-012-description-maxlength-50k.md` | New ADR | ✓ |
| `pipelines/migrations/h8_002_description_maxlength_50k.py` | New no-op-data migration (re-validation) | ✓ |
| `docs/h8/HAFTA8_STAGE_2c_SCHEMA_BUMP.md` | Migration journal for 2c.1 | ✓ |

### Commit 2c.2 contents

| Path | Change | Idempotent? |
|---|---|---|
| `docs/decisions/ADR-011-dia-chunks-scope-person-enrichment.md` | FORCE rewrite to v1.1 | ✓ (rewrite each time with --force) |
| `docs/h8/H8_STAGE_2b_ANALYZER_FINDINGS.md` | New audit trail | ✓ |
| `docs/h8/HAFTA8_STAGE_2_DOCTRINE.md` | FORCE rewrite — this journal | ✓ |
| `docs/h8/H8_MASTER_PLAN_REVISION_PATCH.md` | FORCE rewrite — adds AQ for ADR-012 | ✓ |
| `docs/h8/H8_DECISION_LOG.md` | Append Karar 5 + Karar 6 at marker | ✓ (probe-based dedup) |

## Verification

Stage 2c.1:
```
python3 -m json.tool schemas/_common/multilingual_text.schema.json > /dev/null
# Should be valid JSON

git diff schemas/_common/multilingual_text.schema.json
# Should show ONE-LINE change (maxLength 5000 → 50000) + extended description text

python3 pipelines/migrations/h8_002_description_maxlength_50k.py
# Should report: 46702 passed, 0 failed across all entity types

pytest tests/integration/
# Should remain: 74 passed, 0 failed, 3 skipped, 3 xfailed
```

Stage 2c.2:
```
ls -la docs/decisions/ADR-011-*.md docs/decisions/ADR-012-*.md docs/h8/H8_*.md docs/h8/HAFTA8_STAGE_2*.md
# All files present

git diff docs/h8/H8_DECISION_LOG.md
# Should show append at marker: Karar 5 + Karar 6
```

## Commit 2c.1 message (template)

```
Hafta 8 Stage 2c.1: ADR-012 schema bump — description maxLength 5000 → 50000

- schemas/_common/multilingual_text.schema.json: bump
  description.<lang>.maxLength from 5000 to 50000 chars + extended description
  (additive, backward-compatible; $id unchanged per PE-2 deferral)
- docs/decisions/ADR-012-description-maxlength-50k.md: new ADR
  rationale, empirical grounding from Stage 2b analyzer v2
- pipelines/migrations/h8_002_description_maxlength_50k.py: idempotent
  re-validation (no data mutation; 46702 records expected green)
- docs/h8/HAFTA8_STAGE_2c_SCHEMA_BUMP.md: migration journal

Resolves: Karar 4 truncation crisis (68.8% of Cat A slugs would
truncate under maxLength 5000; bump preserves full narrative for 95%
of records, long-tail truncation only)

Test: pytest tests/integration/ remains 74 passed; h8_002 migration
reports 46702 records validated green
```

## Commit 2c.2 message (template)

```
Hafta 8 Stage 2c.2: ADR-011 v1.1 — empirical corrections from analyzer v2

- docs/decisions/ADR-011-dia-chunks-scope-person-enrichment.md: rewrite
  to v1.1 with three corrections from Stage 2b analyzer v2:
    (a) `a` field routes to labels.prefLabel.ar (Arabic-script; 68.4%
        coverage), NOT provenance.attributed_to
    (b) Per-slug chunk aggregation explicit (8,093 work units, not
        19,742; avg 2.44 chunks/slug; sort by c, concat with \n)
    (c) Truncation strategy revised: ADR-012 bumps maxLength so
        truncation fires on long-tail (~5%) only, not majority
- docs/h8/H8_STAGE_2b_ANALYZER_FINDINGS.md: empirical audit trail —
  the v1→v2 analyzer trajectory + three findings + process
  retrospective
- docs/h8/HAFTA8_STAGE_2_DOCTRINE.md: stage journal noting v1→v1.1
- docs/h8/H8_MASTER_PLAN_REVISION_PATCH.md: adds AQ scorecard entry
  for ADR-012; refines AA.1 with Stage 2b numbers (3,309 Cat A slugs;
  100% eligible)
- docs/h8/H8_DECISION_LOG.md: Karar 5 (empirical refinements) +
  Karar 6 (ADR-012 schema bump rationale) appended at marker

Stage 2 doctrine commit. Builds on Stage 2c.1 (schema bump committed
in prior commit).
```

## Rollback

Either commit can be reverted independently:
- Revert 2c.2 (doctrine): removes v1.1 + audit + master plan + decision
  log. ADR-012 schema bump remains.
- Revert 2c.1 (schema bump): restores maxLength 5000. ADR-011 v1.1
  would then have a dangling forward-reference; revert 2c.2 too.

Recommended atomic revert: revert both commits together.
