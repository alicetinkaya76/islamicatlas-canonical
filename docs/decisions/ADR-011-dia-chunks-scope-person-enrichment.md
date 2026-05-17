# ADR-011: dia_chunks scope — person enrichment, not work mint  (v1.1)

**Status:** Accepted (v1.1 — empirical refinements from Stage 2b
analyzer v2)
**Date:** 2026-05-17
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-006 (Adapter pattern), ADR-007 (Rich entity page
contract), ADR-009 (DiA rich-mint doctrine for works), ADR-012
(description maxLength bump 5000→50000), H7 Stage 3 (ADR-009 origin),
H8 Stage 1 (PE-1 remediation), H8 Stage 2 doctrine, H8 Stage 2b
analyzer findings (this revision's empirical grounding)

---

## Context

ADR-011 v1 was written based on a profile (`profile_dia_chunks.py`)
that under-described the dia_chunks.json schema. Stage 2b's
calibrated analyzer (`analyze_dia_enrichment_v2.py`) produced
ground-truth measurements that contradict three v1 claims:

1. **`a` field semantics** — v1 read `a` as TDV contributor (entry
   author) and routed it to `provenance.attributed_to`. Analyzer v2
   classified the `a` field via Arabic-script detection
   (Unicode 0600-06FF): 68.4% of Cat A slugs (2,265 of 3,309) carry
   Arabic-primary content. Sample inspection confirms: `a` is the
   **Arabic-script form of the entry title** (e.g. `الحصاف` for
   Hassâf, `أحمد يسوي` for Ahmed Yesevî, `ابن النجّار البغدادي`
   for Ibn al-Najjar al-Baghdadi). NOT the TDV contributor (the
   chunks file does NOT carry that information at all).

2. **Per-slug aggregation** — v1 treated each chunk as an
   independently-eligible enrichment unit, missing the multi-chunk
   pattern. Stage 2b measured: 19,742 chunks span 8,093 distinct
   slugs (avg 2.44 chunks/slug; max 12+ chunks for canonical figures
   like İbn Teymiyye, Süleyman, Selçuklular). The adapter writes ONE
   `description.tr` per slug, aggregating all chunks of that slug
   (sorted by `c`, joined with `\n`).

3. **Truncation crisis** — v1 reported per-chunk overflow (>5000
   chars) at 0%. Stage 2b reported per-slug aggregated overflow at
   68.8%. Karar 4 truncation strategy as written would lose
   information from majority of records, not from the exception.
   Resolution: **ADR-012** bumps `description.<lang>` maxLength
   5,000 → 50,000. After bump, only ~5% long-tail entries truncate.

This v1.1 revision integrates these three corrections. The doctrinal
direction (dia_chunks → person enrichment, not work mint) is
unchanged. The PATCH SHAPE and CONFORMANCE THRESHOLDS are corrected.

## Empirical ground truth (Stage 2b analyzer v2 output)

| Metric | Value | Adapter implication |
|---|---:|---|
| Total chunks | 19,742 | Loader scans full file |
| Distinct slugs | 8,093 | Aggregation reduces 19,742 → 8,093 work items |
| slug_to_pid resolved | 3,309 | Cat A upper bound — all resolved |
| Cat A eligible (≥200 char aggregated) | 3,309 (100%) | Zero stub-rejection in Cat A |
| Per-slug median narrative | 6,337 chars | Above ADR-012 threshold; truncation rare |
| Per-slug overflow (>5000) | 68.8% | Drove ADR-012 |
| Per-slug overflow (>50000) | ~5% est. | Karar 4 fallback fires on long-tail only |
| `a` arabic_primary in Cat A | 2,265 (68.4%) | `labels.prefLabel.ar` for 68% of patches |
| `a` empty in Cat A | 1,044 (31.6%) | Mostly modern non-Muslim/Western figures |
| Date parseable (extended) | 88.8% | hijri_gregorian 52.3% + gregorian_range 34.6% + hijri_only 1.8% |
| Cat B/C distinct slugs | 4,784 | Deferred to H8.5/H9 |

## Decision

dia_chunks.json feeds a new pipeline branch — `dia_person_enrichment`
— that updates existing person records via additive idempotent
patches, in three categories:

- **Category A** (this H8): chunks whose slug is in
  `dia_slug_to_pid.slug_to_pid`. 3,309 person records affected.
- **Category B** (deferred to H8.5/H9): 4,784 slugs not in
  slug_to_pid. Require fuzzy-name match (rulers, narrators, modern
  figures) or new mint pattern.
- **Category C** (out of scope until H10+): non-person entries
  (places, dynasties, concepts) — for later namespace work.

ADR-009 (work-side rich-mint doctrine) remains in force. Work-side
mint waits for the H9 TDV scraping pipeline.

### Conformance thresholds (v1.1)

The pipeline writes an enrichment update to an existing person record
if and only if:

> **(a')** Per-slug aggregated `t_total_len` ≥ 200 characters
> (filters out stub entries; %100 of Cat A passes).
>
> **(b')** Slug resolves to a known person PID via
> `dia_slug_to_pid.slug_to_pid` (Cat A) — or fuzzy name match
> (Cat B, future iteration).
>
> **(c')** Patch is additive — never overwrites existing
> `labels.description.tr`, never replaces a verified `death_temporal`;
> only fills gaps and appends to `provenance.derived_from`.

### Patch shape (v1.1) — per slug, not per chunk

For each Cat A slug → resolved person PID, the adapter performs these
idempotent updates (in this order):

| Step | Source | Target field | Action |
|---|---|---|---|
| 1 | `chunks_by_slug[s]` sorted by `c` | (internal) | Aggregate: ordered list of chunks |
| 2 | concat `[c.t for c in chunks]` joined by `\n` | `labels.description.tr` | Set if absent; truncate at 50,000 chars (ADR-012) at sentence boundary; provenance flag `truncated_at_50000_chars` if applied |
| 3 | `chunks[0].n.title()` (cap fix: `İBN TEYMİYYE` → `İbn Teymiyye`) | `labels.altLabel.tr` | Append to list if not already present |
| 4 | `chunks[0].a` IF a_classification == "arabic_primary" | `labels.prefLabel.ar` | Set if absent. Validation: must contain ≥1 Arabic-script char (Unicode 0600-06FF) AND be majority-Arabic. |
| 5 | `chunks[0].d` via extended parser | `death_temporal` | If absent, set from parsed struct. If present and parsed mismatches existing, append `provenance.note` warning, NO overwrite. |
| 6 | (always) | `provenance.derived_from` | Append: `source_id="dia-chunks:<slug>"`, `source_type="tertiary_reference"`, `page_or_locator="(unavailable: see H9 scraping)"`, `extraction_method="structured_json"`, `note="enriched via dia_person_enrichment v1"` |
| 7 | (always) | `provenance.record_history` | Append: `{change_type:"update", note:"dia_person_enrichment v1", date: now()}` |

**Note on `provenance.attributed_to`**: v1 mistakenly used `chunk.a`
for this field. v1.1: leave unset. The actual TDV entry author is not
available in chunks; it would require TDV scraping (H9+). When that
arrives, a follow-up enrichment pass can populate `attributed_to`.

### Idempotency

Re-running the adapter on already-enriched records is a no-op,
detected by checking for an existing
`provenance.derived_from[].source_id` starting with `dia-chunks:`. If
present, the adapter skips that slug entirely (does not append a
duplicate provenance entry, does not modify labels).

### Date parser (extended)

The H8 Stage 3 adapter uses `pipelines/_lib/dia_date_parser.py`
(Stage 3 deliverable) with four patterns in priority order:

1. **hijri_gregorian** `(ö. 728/1328)` — pre-modern; populates both
   `hijri_year` and `gregorian_year`.
2. **gregorian_range** `(1891-1965)` — modern; populates
   `gregorian_year` from death year only.
3. **hijri_only** `(ö. 562)` — pre-modern terse; populates
   `hijri_year`, leaves `gregorian_year` undef.
4. **gregorian_only** `(ö. 1965)` — modern terse; populates
   `gregorian_year`.
5. **approximate** `(ö. h. 685 civarı)` — soft date; populates
   `hijri_year` with `approximation="circa"`.
6. **century** `(IX/XV yüzyıl)` — coarse; populates `floruit_temporal`
   instead of `death_temporal` with `approximation="floruit"`.

Patterns not matching → `temporal` left untouched on the record.

## Alternatives Considered

### Alternative A v1.1: Relax ADR-009 thresholds, mint 19,742 work records

Discarded (same as v1). dia_chunks content is biographical/encyclopedic.

### Alternative B v1.1: Treat `a` as TDV contributor → `provenance.attributed_to`

Discarded — empirically wrong. v2 sample inspection: `a` is the
Arabic-script title.

### Alternative C v1.1: Per-chunk enrichment, multiple description.tr per slug

Discarded. (1) Schema doesn't support multi-valued `description.<lang>`
under one record. (2) Frontend would have to render N separate
description fragments per person, which is incoherent UX. (3) The
natural mental model is one entry = one person = one description.

### Alternative D v1.1: Truncate at 5000 always (no ADR-012)

Discarded. 68.8% truncation rate is unacceptable per analyzer v2.
See ADR-012 §Alternative A.

## Consequences

### Positive (v1.1)

- 95% of enriched records preserve full DiA narrative (post-ADR-012).
- 68% of records gain Arabic-script prefLabel (new — was missing in v1).
- Date cross-validation across 88.8% of records (was 33% in v1).
- Adapter is per-slug clean: 8,093 work units instead of 19,742.

### Negative / Tradeoff

- Adapter complexity higher than v1: chunk grouping + sort + concat +
  truncate logic. Mitigated by `pipelines/_lib/dia_chunks_io.py`
  encapsulation (Stage 3 deliverable).
- ADR-012 introduces a new schema invariant; PE-2 ($id housekeeping)
  carries one more divergence to reconcile.
- Master plan AM target retained (≥80% of resolved slugs = ≥2,647).
  Stage 2b confirms full coverage (3,309/3,309 = 100% eligible);
  AM is achievable at Stage 6 close.

### Neutral / Revisit triggers

- Long-tail truncation (>50K) frequency: pilot Stage 4 measures.
- Cat B fuzzy-match design: separate doctrine (potential ADR-013 in
  H8.5 or H9).

## References

- `docs/decisions/ADR-009-dia-works-rich-vs-shallow-mint.md`
- `docs/decisions/ADR-010-source-type-digital-corpus.md`
- `docs/decisions/ADR-012-description-maxlength-50k.md` (companion
  schema bump; committed in same H8 Stage 2c push as this v1.1)
- `docs/h8/H8_STAGE_2b_ANALYZER_FINDINGS.md` (empirical audit trail)
- `data/sources/dia_chunks.json` (19,742-record source)
- `data/_state/dia_slug_to_pid.json` (3,309-entry envelope)
- `data/_state/h8_dia_enrichment_feasibility_v2.json` (Stage 2b
  analyzer v2 output)
- `pipelines/adapters/dia_person_enrichment/` — Stage 3 deliverable

---

**Revision history:**

- 2026-05-17: v1 initial version (incorrect `a` field interpretation,
  per-chunk patch shape).
- 2026-05-17: v1.1 revision — empirical corrections from Stage 2b
  analyzer v2: `a` field → `labels.prefLabel.ar`, per-slug
  aggregation explicit, companion ADR-012 for description maxLength,
  extended date parser specification.
