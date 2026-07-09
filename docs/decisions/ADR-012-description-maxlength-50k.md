# ADR-012: multilingual_text.description maxLength 5000 → 50000

**Status:** Accepted
**Date:** 2026-05-17
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-011 (dia_chunks → person enrichment), H8 Stage 2b
analyzer findings, Karar 4 (truncation strategy)

---

## Context

H8 Stage 2b analyzer v2 measured per-slug aggregated narrative length
across the 3,309 Category-A direct-enrichment candidates from
`data/sources/dia_chunks.json`:

| Statistic | Per-slug aggregated `t_total_len` |
|---|---:|
| min | 1,209 chars |
| median | **6,337 chars** |
| mean | 8,854 chars |
| p95 | 20,450 chars |
| max | 318,213 chars |
| stdev | 12,578 chars |

The current `schemas/_common/multilingual_text.schema.json`
`description.<lang>` field has `maxLength: 5000`. At this limit,
**68.8% of Cat A eligible slugs (2,278 of 3,309) would be truncated**
when written to `labels.description.tr` by the dia_person_enrichment
adapter.

Karar 4 (recorded in H8_DECISION_LOG.md) originally specified
"truncate-at-5000 with sentence-boundary detection + provenance flag"
as the default strategy. That decision was made BEFORE the per-slug
aggregation effect was understood (analyzer v1 reported per-chunk
overflow at 0%, hiding the per-slug truncation crisis).

With 68.8% of records affected, "truncation as default" is no longer
acceptable: it produces information loss in the vast majority of
enriched records, which contradicts the academic-credibility argument
behind ADR-011 (enrichment is meaningful only if the narrative is
substantially preserved).

## Decision

Bump `schemas/_common/multilingual_text.schema.json` `description.<lang>`
maxLength from **5,000** to **50,000** characters.

Coverage achieved at 50,000:
- median (6,337) — well within
- mean (8,854) — well within
- p95 (20,450) — well within
- max (318,213) — STILL exceeds 50K; long-tail truncation applies

Long-tail behavior (>50,000 chars): the Karar 4 truncation strategy
fires only on the tail (~5% of records, the truly massive entries like
Süleyman the Magnificent, İbn Teymiyye, Selçuklular, etc.). Sentence-
boundary detection + provenance flag `note="truncated_at_50000_chars"`.

**Why 50,000 specifically:**

- Covers p95 (20,450) with ~2.5x headroom for natural growth.
- Single Turkish DiA entry of 50K chars ≈ 10,000 words ≈ ~30-40 print
  pages — a generous upper bound for any single encyclopedia entry
  (DiA editorial practice caps entries well below this).
- A round number that's documentation-friendly.
- Not 100K or higher because: (a) JSON-LD parsers and downstream
  consumers may have row-size assumptions; (b) frontend rendering
  performance on PersonCard pages degrades past ~20K chars without
  pagination; (c) keeping a meaningful cap signals "this is a
  description, not a book."

## Scope

This change affects:

- `schemas/_common/multilingual_text.schema.json` — single string
  patch (`"maxLength": 5000` → `"maxLength": 50000` in the
  description.patternProperties subschema).
- **All entity types** indirectly: person, work, place, dynasty,
  manuscript, event — because every entity's `labels` field
  `$ref`s the common multilingual_text schema. The bump applies
  uniformly. This is intentional: any entity benefits from richer
  multilingual descriptions, not just person.

The `$id` of `multilingual_text.schema.json` is NOT bumped (kept at
v0.1.0). Rationale mirrors ADR-010 §"Schema versioning": coordinated
$id bumping across all 10 schemas is tracked separately as PE-2 in
`H8_KNOWN_ISSUES.md`.

## Data implications

**Zero data mutation.** All existing records that validated under
maxLength=5000 continue to validate under maxLength=50000 (additive
relaxation). The migration script `h8_002_description_maxlength_50k.py`
re-validates the full canonical store to confirm the assertion.

## Alternatives Considered

### Alternative A: Keep maxLength 5000, truncate at write

Discarded. 68.8% truncation rate produces a dataset where most
enriched records are truncated narratives — academic value drops
substantially, especially for canonical figures whose entries are
the longest.

### Alternative B: Bump to 100,000+ or remove maxLength

Discarded. (1) Loses signal that descriptions are documentation, not
full-text storage. (2) Frontend pagination becomes a hard requirement
instead of a polish item. (3) Downstream JSON-LD / Turtle exports may
hit row-size limits in some triplestores. 50K is a balanced ceiling.

### Alternative C: Multi-field overflow

Adapter writes first 5K to `description.tr`, remainder to a new field
(e.g., `description_extended` or `note`). Discarded because (1) it
introduces a schema concept that exists ONLY for this overflow case,
(2) frontend rendering becomes conditional logic, (3) the natural
mental model "description is a single multilingual field" is broken.

### Alternative D: Bump description maxLength only for person.schema, not common

Discarded. The schema indirection (person.labels → multilingual_text)
is structural; person-only bumps would require duplicating
multilingual_text inline, which propagates schema drift. The bump is
a single common-schema change.

## Consequences

### Positive

- 95% of Cat A enrichment records preserve full narrative.
- ADR-011's "academic credibility" argument holds: enriched
  descriptions are substantially complete, not arbitrarily clipped.
- Long-tail truncation (Karar 4 fallback) becomes a documented edge
  case, not the default — provenance flag `truncated_at_50000_chars`
  is rare, signalling that the entry is exceptionally long.
- Downstream consumers (Fatıma's PersonCard frontend) gain richer
  data without conditional handling.

### Negative / Tradeoff

- `$id` coherence drift now spans an additional change point
  (multilingual_text.schema.json was at v0.1.0; semantically becomes
  v0.2.1 after this patch but file-level $id stays). PE-2 housekeeping
  carries this forward.
- Frontend pagination becomes necessary for long descriptions
  (>~2000 chars). Already in scope per ADR-007 rich-page-contract;
  this just makes it concrete.
- Existing tests that asserted on description length behavior may
  need adjustment (Stage 3 inspects).

### Neutral

- ADR-009 (work-mint rich-mint doctrine) is unaffected.
- ADR-010 (digital_corpus enum) is unaffected.

## Migration

`pipelines/migrations/h8_002_description_maxlength_50k.py` — runs a
no-op-data migration that re-validates every record in
`data/canonical/{person,work,place,dynasty,manuscript,event}`
against the patched schema set. Expected outcome: 46,702 records pass
(same baseline as h8_001 post-PE-1).

## References

- `docs/decisions/ADR-011-dia-chunks-scope-person-enrichment.md`
- `docs/h8/H8_STAGE_2b_ANALYZER_FINDINGS.md`
- `data/_state/h8_dia_enrichment_feasibility_v2.json` — empirical
  ground truth from analyzer v2
- `schemas/_common/multilingual_text.schema.json` — patched file
- `pipelines/migrations/h8_002_description_maxlength_50k.py` —
  re-validation script

---

**Revision history:**

- 2026-05-17: Initial version, Ali Çetinkaya (H8 Stage 2c schema bump).
