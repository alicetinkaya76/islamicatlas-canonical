# Hafta 8 — Stage 1: PE-1 remediation

**Date:** 2026-05-16
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical
**Trigger:** H7 close discovery (commit 8833ec0)

---

## What this stage does

Resolves PE-1 (2,262 of 21,946 person records carry an enum value not
admitted by the common provenance schema). Approach: additive enum
extension (Option B1 from H7_KNOWN_ISSUES). No data mutation.

## Files touched

| Path | Change | Idempotent? |
|---|---|---|
| `schemas/_common/provenance.schema.json` | Add `"digital_corpus"` to `derived_from[].source_type.enum`; extend description. `$id` unchanged. | ✓ (no-op if already patched) |
| `docs/decisions/ADR-010-source-type-digital-corpus.md` | New file documenting the decision, scope, and PE-2 deferral rationale. | ✓ (skipped if exists, --force to overwrite) |
| `docs/h8/HAFTA8_STAGE_1_PE1_FIX.md` | This journal. | ✓ |
| `docs/h8/H8_DECISION_LOG.md` | Decision 1 written. | ✓ |
| `docs/h8/H8_KNOWN_ISSUES.md` | PE-2 (schema $id coherence) logged. | ✓ |
| `pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py` | New re-validation migration (no data mutation). | ✓ |

## What this stage does NOT do

- Does not bump `$id` of `_common/provenance.schema.json`. See ADR-010
  §"Schema versioning" and `H8_KNOWN_ISSUES.md` PE-2.
- Does not modify any `data/canonical/*.json` record.
- Does not touch test files; the existing
  `test_dia_pilot.py::test_a1_all_person_records_validate` is expected
  to transition FAILED → PASSED with no test edit.

## Acceptance criteria

- [ ] `python3 -m json.tool schemas/_common/provenance.schema.json > /dev/null` — valid JSON.
- [ ] Source_type enum contains 6 values, last is `"digital_corpus"`.
- [ ] `pytest tests/integration/test_dia_pilot.py::test_a1_all_person_records_validate -v` PASSED.
- [ ] `pytest tests/integration/` reports 74 passed, 0 failed, 3 skipped, 3 xfailed.
- [ ] `git status` shows exactly 6 staged paths above (no extras).
- [ ] `python3 pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py` reports green for all entity types.

## Expected commit message

```
Hafta 8 Stage 1: PE-1 remediation — schema enum digital_corpus + ADR-010

- schemas/_common/provenance.schema.json: add 'digital_corpus' enum value
  + extended description (additive, backward-compatible; $id unchanged)
- docs/decisions/ADR-010-source-type-digital-corpus.md: new ADR
  documenting the decision, alternatives, and PE-2 deferral
- docs/h8/{HAFTA8_STAGE_1_PE1_FIX.md, H8_DECISION_LOG.md,
  H8_KNOWN_ISSUES.md}: H8 doc set scaffolding
- pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py: idempotent
  re-validation script (no data mutation)

Resolves: PE-1 (2,262 person records, H7 known issue)
Defers:   PE-2 (schema $id coherence across 10 files) to future commit
Test:     test_dia_pilot::test_a1 FAILED → PASSED;
          tests/integration/ 73→74 passed
```

## Rollback

`git revert <commit>` restores the prior enum without touching records.
No data migration was performed, so rollback is safe.
