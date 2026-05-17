# H8 Master Plan Revision Patch — AA/AB/AG re-redefinition under ADR-011 v1.1

**Date:** 2026-05-17
**Trigger:** ADR-011 v1.1 (dia_chunks scope) + ADR-012 (schema bump)
**Supersedes:** Selected sections of `docs/h7/H7_MASTER_PLAN_REVISION.md`

---

## Why patched (v1.1)

H7's master plan revision deferred AA/AB/AG "to H8+ pending raw DiA
source." H8 Stage 2b analyzer v2 confirmed dia_chunks exists locally
AND determined: (a) dia_chunks is biographical/encyclopedic, not
bibliographic, so it's the wrong source for dia_works mint; (b)
dia_chunks IS the right source for person enrichment with 3,309
direct-resolution candidates; (c) dia_works rich-mint still needs
H9+ TDV scraping pipeline.

This patch v1.1 (revising v1 with Stage 2b empirical grounding) hardens
AA/AB/AG against the corrected scope.

---

## Acceptance scorecard — H8 patch v1.1

### AA — dia_works mint volume

**Pre-H8 form (H7):** "Rich-mint doctrine count for ADR-009-conformant
records; number TBD pending raw DiA source."

**H8 v1.1:** **TWO TRACKS, with Stage 2b numbers**:

- **AA.1 — dia_person_enrichment** (this H8): ≥ N persons enriched
  with `labels.description.tr` from dia_chunks. **Stage 2b v2 ground
  truth: N upper bound = 3,309 (100% of resolved slug_to_pid; 100%
  eligible at ≥200 chars).** Target for H8 Stage 6 close: ≥ 2,647
  (80% of 3,309), allowing 20% margin for pilot-driven exclusions
  (cross-validation date mismatches, sample-inspection edge cases).
- **AA.2 — dia_works rich mint** (H10+, gated on H9 scraping): ≥ K
  rich work records satisfying ADR-009 thresholds (a)+(b)+(c).
  K-target TBD at H9 close.

### AB — dia_works valid provenance.source_id

**v1.1:** Unchanged from v1. For `dia_person_enrichment`, analogous
criterion is implicit in AA.1's idempotency requirement (every
enriched record gains `source_id="dia-chunks:<slug>"`).

### AG — integration tests

**v1.1:** Redirected to `tests/integration/test_dia_person_enrichment_pilot.py`.
Tests cover:

1. **Schema validity post-patch** (no regression; baseline 46,702
   records green from h8_001 + h8_002 migrations).
2. **Idempotency** (re-run = no-op via `dia-chunks:` provenance probe).
3. **Conformance (a')** — every enriched record has
   `description.tr` ≥ 200 chars.
4. **Conformance (b')** — every enriched record has
   `provenance.derived_from[].source_id` matching `dia-chunks:<slug>`.
5. **Non-destructive update** — pre-existing `description.tr` /
   `death_temporal` preserved.
6. **Arabic prefLabel coverage** — for Cat A slugs with
   `a_classification == "arabic_primary"`, enriched record has
   `labels.prefLabel.ar`.
7. **Bidirectional traceability** — every `dia-chunks:<slug>`
   provenance value corresponds to a real chunk in dia_chunks.json.

### New scorecard entries

- **AL** — PE-1 remediated (Stage 1). **DONE at commit 4e6176a.**
- **AM** — dia_person_enrichment Cat A complete; ≥ 2,647 patches
  applied; AG tests pass. **Target: H8 Stage 6.**
- **AN** — Cat B fuzzy-match strategy designed; ≥ 50% non-scholar
  person chunks matched. **Target: H8.5 or H9.**
- **AO** — TDV scraping pipeline implemented;
  `dia_chunks_rich.json` produced with cilt+sayfa+arabic_title.
  **Target: H9.**
- **AP** — dia_works ADR-009 rich-mint executed; ≥ K records minted.
  **Target: H10+.**
- **AQ** *(new in v1.1)* — ADR-012 schema bump applied;
  `description.<lang>` maxLength = 50,000; h8_002 migration green.
  **Target: H8 Stage 2c.1. DONE upon commit 2c.1.**

---

## Net change to H8 acceptance gate

H8 close requires:

- [x] PE-1 remediated (AL — DONE, commit 4e6176a)
- [ ] ADR-012 + schema bump (AQ — Stage 2c.1)
- [ ] ADR-011 v1.1 + master plan v1.1 (Stage 2c.2)
- [ ] Stage 2b analyzer feasibility profile committed (Stage 2c.2)
- [ ] dia_person_enrichment adapter implemented + pilot batch (Stage 3-4)
- [ ] AG tests + suite green (Stage 5)
- [ ] AM target met (≥ 2,647 enrichments) OR documented partial close (Stage 6)
- [ ] H8 close commit + push + HAFTA8_CLOSE_STATE.md

---

## What is OUT of H8 scope per v1.1

- Category B (fuzzy-match for non-scholar person chunks; 4,784 slugs)
- Category C (places/concepts/dynasties; subset of 4,784)
- TDV scraping pipeline implementation
- dia_works rich-mint execution

Concrete deferrals to AN, AO, AP in H8.5 / H9 / H10+.
