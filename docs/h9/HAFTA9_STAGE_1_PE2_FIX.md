# Hafta 9 — Stage 1: PE-2 remediation ($id coherence)

**Date:** 2026-06-11
**Branch:** hafta5-work-namespace
**Repo:** /Volumes/LaCie/islamicatlas_canonical
**Entry HEAD:** a41642d (tag: hafta8-close)
**Trigger:** PE-2, logged at H8 Stage 1 (`docs/h8/H8_KNOWN_ISSUES.md`),
carried to H9 as the recommended Stage 1 by `HAFTA8_CLOSE_STATE.md`.

---

## What this stage does

Resolves PE-2. The 11-file schema set is unified on a single version
tag — `$id` and `$ref` URI prefixes `…/v0.1.0/` (10 files + 27 refs)
and `…/v0.2.0/` (work.schema.json `$id`) are rewritten to `…/v0.3.0/`.
38 URI occurrences total; no other byte changes. The set-level
versioning policy is codified as ADR-013; a permanent 4-test coherence
invariant (PE2.1–PE2.4) joins the integration suite.

Pre-rewrite audit at a41642d: the versioned URI prefix appears **only**
under `schemas/` — zero occurrences in `pipelines/`, `tests/`,
`data/_state/` samples, adapter manifests, or fixtures. No canonicalize
library stamps schema URIs into records, so this is a schemas-only
change with **no data migration**. (Local spot-check is in the
acceptance list below.)

## Files touched (16)

| Path | Change | Idempotent? |
|---|---|---|
| `schemas/_common/*.schema.json` (5) | URI prefix flip → v0.3.0 (`$id` + incoming-`$ref` targets) | ✓ probe-gated |
| `schemas/{dynasty,event,manuscript,person,place}.schema.json` (5) | Same flip ($id + outgoing `$ref`s) | ✓ probe-gated |
| `schemas/work.schema.json` | `$id` v0.2.0→v0.3.0 + 4 `$ref`s v0.1.0→v0.3.0 | ✓ probe-gated |
| `docs/decisions/ADR-013-schema-set-versioning-policy.md` | New ADR — set-level semver, rules R1–R5 | ✓ (exists+matches → no-op; `--force` to overwrite) |
| `docs/h9/H9_DECISION_LOG.md` | New — Karar 1 + insertion marker | ✓ |
| `docs/h9/H9_KNOWN_ISSUES.md` | New — PE-2 closure + AN/AO/AP carry-over ledger + marker | ✓ |
| `docs/h9/HAFTA9_STAGE_1_PE2_FIX.md` | This journal | ✓ |
| `tests/integration/test_h9_schema_set_coherence.py` | New — PE2.1–PE2.4 permanent invariants | ✓ |

## What this stage does NOT do

- Does not modify any `data/canonical/*.json` record (PE-2 is
  schemas-only; the audit above is the warrant).
- Does not edit any `docs/h8/` file. H8 close documents are sealed;
  PE-2's closure lives in the H9 ledger, with the H8 entry remaining a
  true statement about H8-close time.
- Does not change validation behavior. Resolution is registry-based
  (ADR-002): the registry keys schemas by on-disk `$id`, so a coherent
  rename is behavior-neutral. `tests/run_schema_tests.py` must report
  the same 15/15 before and after.
- Does not assign a ledger letter to the acceptance criterion below.
  The H8 PE-2 entry proposed labeling it "AM", but AM was already
  consumed by H8's enrichment criterion (≥2,647); to avoid a ledger
  collision the criterion is tracked here unlettered.
- Does not tag. Stage 1 is not a hafta close.
- Does not invoke git (orchestrator prints the suggested sequence).

## Acceptance criteria

- [ ] `grep -r "islamicatlas/schemas/v0\.[12]\.0" schemas/` → empty.
- [ ] All 11 `$id`s carry `v0.3.0`; `python3 - <<'EOF'` one-liner in
      handoff prints a single-element tag set.
- [ ] `grep -rl "w3id.org/islamicatlas/schemas" data/canonical | head`
      → empty (spot-confirms the no-data-coupling audit on the full
      store, which the sandbox could not see).
- [ ] `python3 tests/run_schema_tests.py` → 15/15 passed (unchanged).
- [ ] `pytest tests/integration/test_h9_schema_set_coherence.py -v`
      → 4 passed (PE2.1–PE2.4).
- [ ] `pytest tests/integration/` → **85 passed, 3 skipped, 3 xfailed**
      (81+4; zero new failures). If the totals differ, stop and report.
- [ ] `git diff --stat` lists exactly 16 paths (11 schemas + 5 new).

## Expected commit message

```
Hafta 9 Stage 1: PE-2 remediation — schema-set $id coherence, atomic
bump to v0.3.0 + ADR-013

- schemas/ (11 files): $id and all $ref URIs unified at
  https://w3id.org/islamicatlas/schemas/v0.3.0/ (was: 10× v0.1.0 +
  work.schema.json at v0.2.0; 38 URI occurrences rewritten, bytes
  otherwise identical)
- docs/decisions/ADR-013-schema-set-versioning-policy.md: set-level
  semver — single tag (R1), atomic bumps (R2), pre-1.0 increment rules
  (R3), test-pinned enforcement (R4), data-coupling guard (R5)
- docs/h9/{HAFTA9_STAGE_1_PE2_FIX.md, H9_DECISION_LOG.md,
  H9_KNOWN_ISSUES.md}: H9 doc set scaffolding; Karar 1 (v0.3.0, not
  v1.0.0 — stability tag reserved for Faz 0.5 post-AP)
- tests/integration/test_h9_schema_set_coherence.py: PE2.1–PE2.4
  permanent invariants (single tag / refs resolve / pinned tag /
  schemas compile against full registry)

Resolves: PE-2 (H8 known issue — schema $id coherence drift)
Defers:   v1.0.0 stable tag to Faz 0.5 (ADR-013 Alternative A rationale)
Test:     tests/integration/ 81→85 passed; run_schema_tests 15/15
          unchanged
```

## Rollback

Single `git revert <commit>` restores the drifted-but-functional
pre-Stage-1 state: schemas return to v0.1.0/v0.2.0, the coherence test
leaves the suite with the same revert (no orphaned red test), ADR-013
and the H9 docs disappear together. No data was touched, so rollback is
side-effect-free. Note the revert recreates PE-2 — reopen it in this
ledger if that path is ever taken.
