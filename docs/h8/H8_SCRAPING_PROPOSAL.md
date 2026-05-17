# H8 → H9 Proposal: TDV İslâm Ansiklopedisi scraping pipeline

**Date:** 2026-05-17
**Status:** Draft proposal (H8 Stage 2 deliverable; H9 to refine and execute)
**Author:** Ali Çetinkaya
**Related:** ADR-009 (rich-mint doctrine), ADR-011 (dia_chunks scope),
H8_MASTER_PLAN_REVISION_PATCH §AO/AP

---

## Why this proposal exists

ADR-009 requires DiA-side work records to satisfy three thresholds —
(a) multilingual prefLabel, (b) description, (c) cilt+sayfa locator —
before being written to canonical. The H8 Stage 2 analysis of
`data/sources/dia_chunks.json` confirmed (b) is satisfiable from the
chunks (Turkish narrative present, %89.8 coverage) but (a) and (c)
are NOT in the chunks — no Arabic title field, no cilt+sayfa fields.

The H8 path (ADR-011) routes the chunks to person enrichment, NOT
work mint. dia_works rich-mint remains deferred. This proposal
specifies the H9+ session that closes the work-mint gap by adding
a TDV scraping pipeline.

## Hypothesis

The TDV İslâm Ansiklopedisi web edition at
`https://islamansiklopedisi.org.tr` exposes per-entry HTML pages that
include:

1. **Cilt + sayfa** in the masthead (`Cilt: 16 — Sayfa: 395`).
2. **Arabic title** (where applicable) in a header element or first
   paragraph (`الحصاف` for Hassâf).
3. **Entry author** (TDV contributor) in a metadata block.
4. **Full Turkish body** matching dia_chunks's `t` field (provides
   verification path).
5. **Cross-references** to related slugs (graph-augmentation
   opportunity).

These five elements together close ADR-009's threshold gaps.

## Proposed pipeline architecture

### Phase 1 — Compliance verification

1. Read TDV's terms of service at the site footer (or contact
   `iletisim@tdv.org.tr`) for research-use clearance.
2. Verify `robots.txt` permits crawling of `/madde/*` paths.
3. Document compliance posture in `docs/decisions/ADR-012-tdv-scraping-compliance.md`
   (or similar). If ToS prohibits scraping, pivot to a printed-edition
   re-extraction or formal institutional data request.

### Phase 2 — Polite scraper

Architecture: a one-off batch pipeline (not real-time), structured as
an ADR-006-compliant adapter `pipelines/adapters/dia_tdv_scrape/`
with the four files (manifest, extract, resolve, canonicalize).

**Politeness budget**:
- 1 request per 2 seconds (i.e. ~1,800 entries/hour); 19,742 entries =
  ~11 hours of compute. Run overnight.
- Conditional GET with `If-Modified-Since` headers on re-runs.
- User-Agent identifying the project + ORCID + contact email.
- Resume-from-checkpoint design: per-slug success flag in a state
  sidecar (`data/_state/h9_scrape_progress.json`), idempotent restart.

**Per-entry HTTP**:
- GET `https://islamansiklopedisi.org.tr/madde/<slug>` (or
  `/<numeric-id>` if slug-URLs not stable).
- Parse with BeautifulSoup or lxml.
- Extract cilt + sayfa + Arabic title + entry-author + body-text-hash
  (for verification against dia_chunks's `t`).
- Save raw HTML to `data/sources/dia_html/<slug>.html.gz` (gitignored)
  for archival + re-parse without re-fetch.

**Per-entry validation**:
- Body-text hash must match dia_chunks `t` to within configurable
  Levenshtein distance (e.g. ≤ 5% character difference, allowing for
  HTML stripping + whitespace normalization). Mismatch → flag for
  manual review.
- Cilt + sayfa pattern must match `^Cilt: \d+ — Sayfa: \d+$` (or
  equivalent stable selector). Drift → log + skip.

### Phase 3 — Enrichment integration

Two integration paths:

**Path 3a (preferred)**: Write a parallel file
`data/sources/dia_chunks_rich.json` with the same 19,742-record
structure plus added fields: `cilt`, `sayfa_baslangic`, `title_ar`,
`author_normalized` (TDV contributor disambiguated against existing
person records). The `dia_chunks.json` stays untouched.

**Path 3b** (alternative): Re-generate `dia_chunks.json` in-place
with the added fields. Cleaner state but loses the provenance
distinction between "structured-from-source" and "scraped".

### Phase 4 — dia_works rich-mint adapter

Once `dia_chunks_rich.json` is available:

1. Create `pipelines/adapters/dia_works/` (the originally-planned
   adapter from H5/H6 that ADR-009 blocked).
2. Per-slug, build a work record with:
   - `labels.prefLabel.tr` = `chunks_rich.n` (title-cased)
   - `labels.prefLabel.ar` = `chunks_rich.title_ar`
   - `labels.description.tr` = `chunks_rich.t` (truncation strategy
     mirrors ADR-011's)
   - `provenance.derived_from`:
     - `source_id`: `dia-rich:<slug>`
     - `source_type`: `tertiary_reference`
     - `page_or_locator`: `f"TDV DiA cilt {cilt} s. {sayfa_baslangic}"`
     - `attributed_to`: TDV contributor PID
3. ADR-009 conformance check runs as a pre-write gate. Records that
   fail any of (a)/(b)/(c) are routed to a review queue, never
   silently written.
4. Author linkage: each work's `authors` array points to the existing
   person PIDs from `dia_slug_to_pid` (where the slug overlaps with
   chunks).

### Phase 5 — Cross-validation against existing data

- The H8 dia_person_enrichment pass already attached
  `provenance.derived_from[].source_id == "dia-chunks:<slug>"` to ~3,309
  persons. The H10 dia_works rich-mint produces work records with
  `provenance.derived_from[].source_id == "dia-rich:<slug>"`. Both
  share the slug; integrity test confirms consistency.
- Hassâf's H6 one-off rich work record (`iac:work-00009331`) is
  retrofitted with `dia-rich:hassaf` provenance entry (idempotent
  augmentation, not replacement).

## Compliance & ethics

- **Attribution**: Every record minted from scraped data carries
  `provenance.attributed_to` pointing to the TDV contributor PID.
  Public dataset documentation cites TDV İslâm Ansiklopedisi as
  primary source.
- **No redistribution of raw HTML**: `data/sources/dia_html/` is
  gitignored. The canonical store carries only normalized,
  fact-based extractions (titles, cilt+sayfa, dates), not full
  body text from the scraped HTML (the body comes from the
  already-acquired `dia_chunks.json` `t` field).
- **Rate limiting**: Politeness budget above; respect any `Retry-After`
  headers from the server.
- **Cease-on-request**: If TDV requests cessation, the pipeline halts;
  the existing dia_person_enrichment work (H8) is independent and
  retains validity.

## Estimated work

- Phase 1 (compliance): 0.5 session (correspondence + ADR write-up).
- Phase 2 (scraper): 1-2 sessions (architecture + checkpointing + 11h
  overnight run + verification).
- Phase 3 (integration): 0.5 session.
- Phase 4 (rich-mint adapter): 4-6 hours.
- Phase 5 (cross-validation tests): 1-2 hours.

Total: 3-4 H8-sized sessions, completable across H9 + H10.

## Open questions for H9 kickoff

1. **TDV institutional access**: would a formal collaboration request
   (Hüseyin Hoca → Selçuk İlahiyat → TDV liaison) yield a bulk data
   package, bypassing scraping entirely? Worth pursuing in parallel
   with Phase 1.
2. **Slug stability**: do TDV's URL slugs match `dia_chunks.s` exactly,
   or does the public web edition use different slugs? Sample 10
   chunks against the live site as Phase-0 verification.
3. **Author disambiguation**: the chunks' `a` field has names like
   "Cengiz Kallek", "Coşkun Alptekin" — modern TDV contributors. Are
   they (or should they be) modeled in the person namespace, or in a
   separate `iac:contributor-*` namespace?
4. **Multi-author entries**: some long DiA entries have multiple
   sections by different authors. The chunks file collapses these
   (one `a` per slug). Scraping might recover per-section author —
   worth modeling, or out-of-scope?
