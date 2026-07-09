# Hafta 5 Deliverable — Work Namespace Build

**Status**: Sandbox build complete, ready for Mac apply.
**Target**: islamicatlas.org v7.8 → v8 refactor — canonical `iac:work-*`
namespace seeded with two adapters, two integrity passes, 29 acceptance
tests, and one Hafta 6 hand-off audit script.
**Scope decision**: dia_works.json (44,611 mention-rows across 3,369 DİA
slugs) is INTENTIONALLY out of scope. Spot-audit revealed systemic
upstream-parser mis-attribution; mint-as-is would corrupt the canonical
store. Hafta 6 will handle dia_works via Brockelmann/GAL triangulation
+ DİA chunk re-extraction. This deliverable produces a diagnostic audit
sidecar (`dia_works_h5_audit.json`) as the Hafta 6 starting point.

---

## What was built

### 1. Shared library — `pipelines/_lib/work_canonicalize.py`

The Hafta-4 person-namespace `person_canonicalize.py` analog for works.
Provides:

- **PID + label builders**: `build_work_labels()`, `build_work_provenance()`,
  `build_composition_temporal()`, `build_work_type_array()`, `make_xref()`,
  `make_openiti_xref()`
- **Title fingerprint algorithm**: `title_fingerprint()` /
  `normalize_title_for_fingerprint()` / `fingerprint_all_labels()` —
  10-step pipeline (NFKD → Turkish ASCII fold → lowercase → punctuation
  strip → tokenize → Arabic article strip → Latin transliteration folds
  (`kh→h`, `j→c`, `w→v`, `q→k`, `e→a`, double-letter collapse) →
  trailing case-ending strip → stopword drop → sort → SHA1[:16]).
- **Note formatters** for v0.1.0 schema-enum gaps (DİA, science_layer
  cross-references go to `note`, not `authority_xref`).
- **Author PID resolver**: `try_resolve_author_pid()` — uses pid_minter
  reverse lookup (idempotent input_hash → existing PID).

**Title fingerprint validation** on 8 same-work test groups (Canon of
Medicine, Book of Animals, Algebra, Healing, Maqamat, Bukhala, Optics,
Indica) with multiple Latin transliterations:

- Within-Latin matching: 8/8 same-work groups produce identical
  fingerprints across all variants
- Across 5 different-work test sets (including Mu'jam genre family,
  Khwarizmi 3 distinct works, Dhahabi 2 works): 0 false-positive
  collisions

Cross-script (Latin ↔ Arabic) matching is handled via
`fingerprint_all_labels()` set-intersection rather than algorithmic
fold (Arabic→Latin transliteration table is too costly for marginal
gain).

### 2. Adapter — `pipelines/adapters/science_works/`

Converts the curated science_layer.json (181 of 182 scholars carry
`key_works`, plus 129 discoveries) into work records.

- ~224 key_works records yielded directly (each multilingual, year-
  precise, with `significance.tr` captured into `note`)
- Discoveries pass through a regex filter (`Kitāb / Risāla / Maqāla /
  Dīwān / Tārīkh / Muʿjam / book / treatise / compendium /
  Arabic-script openers`); concept-only entries ("Algebra as a
  discipline") drop to `science_works_discovery_drops` sidecar
- Author resolution via `pid_minter.lookup("person",
  "science-layer:scholar_NNNN")` — idempotent reverse lookup of the PID
  minted by the Hafta-4 science-layer person adapter
- Orphan handling: if scholar PID unresolvable, work still minted, no
  `authors[]`, sidecar entry written for triage

### 3. Adapter — `pipelines/adapters/openiti_works/`

Converts OpenITI corpus_works.json (9,104 entries) into work records,
with author cross-walk via the pre-pass sidecar.

Distinctive output features:
- `openiti_uri` stored in dedicated structural field + mirrored as
  `authority_xref` entry (`authority="openiti_uri"`)
- `subjects[]` from corpus_genres.json LLM-tagged primary_genre +
  rule_based_type (deduped)
- `original_language` from `languages[0]` normalized via ISO 639-3 →
  639-1 map (`ara → ar`, etc.)
- `extant_manuscripts[]` derived from `versions_detail` (size_bytes,
  word_count, source provenance)
- `composition_temporal`: explicit year if present; else
  `{"end_ce": author_death_ce, "approximation": "before"}` derived from
  resolved author metadata — visible on the islamicatlas.org timeline
  as a "≤" indicator

### 4. Pre-pass — `pipelines/integrity/openiti_author_resolve.py`

Cross-walks OpenITI author IDs (e.g. `0428IbnSina`) to existing
`iac:person-*` PIDs before openiti_works canonicalize runs.

Three tiers (Tier 3, manual top-100 seed, deferred to Hafta 6):

| Tier | Mechanism | Confidence |
|---|---|---|
| 1 | Wikidata QID match (via seed file) | 1.0 |
| 2 | death_ce ±3 + name token Jaccard ≥0.5 | 0.5–1.0 |
| 4 | Mint placeholder person + Tier 4 sidecar | 0.5 |

Acceptance criterion **X**: T1 + T2 ≥ 70% of OpenITI's 3,618 authors.
Tier 4 placeholders include `death_temporal`, minimal multilingual
labels, and `provenance.derived_from = [{source_id: "openiti:..."}]`.
They are valid person records that integrity_pass_A back-populates
with `authored_works[]` after openiti_works mints.

### 5. Integrity Pass A — `pass_a_bidirectional` (in `work_integrity.py`)

For every `work.authors[X]`, ensure `person[X].authored_works[]`
contains the work PID. **Set-semantics idempotent** — re-runs add no
duplicates. Acceptance criterion **R**: ≥95% bidirectional coverage
(work-author pair has both directions).

Stats produced:
- `bidirectional_links_written` / `bidirectional_links_already_present`
- `orphan_author_pids[]` (work.authors[X] but person X missing)
- `bidirectional_coverage_pct`

### 6. Integrity Pass B — `pass_b_same_as` (same file)

Cross-source SAME-AS clustering between science_works and
openiti_works via **dual-gate**:

1. `fingerprint_all_labels()` set intersection ≥1 common fingerprint
2. `authors[]` PID set intersection ≥1 common author PID

The author-overlap second gate strongly suppresses false-positives
even with the aggressive Latin transliteration folds in the
fingerprint algorithm.

Output:
- `data/_state/work_same_as_clusters.json` — structured cluster info +
  audit of `gate1-passed-only` pairs (false-positives prevented)
- Each cluster member's record gets `_same_as_cluster_id` field +
  `note` line ("Same-as cluster:cluster-NNNNNN, members: ...")

Cluster sidecar enables frontend deduplication (see "frontend
integration" below).

### 7. Hafta 6 hand-off — `pipelines/integrity/dia_works_h5_audit.py`

Per-slug × per-title diagnostic for dia_works.json. For each title:
- Compute fingerprint via `wc.title_fingerprint()`
- Check fingerprint match in science_works namespace
- Check fingerprint match in openiti_works namespace
- Compute `mis_attribution_signal` (resolved DİA scholar PID NOT in
  matched works' authors)

Five confidence bands inform Hafta 6 minting strategy:

| Band | Hafta 6 action |
|---|---|
| `high_validated_both_sources` | Direct mint + SAME-AS link |
| `moderate_validated_one_source` | Brockelmann/GAL cross-check |
| `low_likely_misattribution` | Drop + manual review queue |
| `no_external_match_dia_only` | DİA-unique attribution, manual triage |
| `scholar_unresolved` | Pre-pass needed |

### 8. Test suite — `tests/integration/test_work_pilot.py`

29 acceptance tests across 8 categories (A. Schema validity, B. PID
minting, C. Cross-source author resolution, D. Bidirectional
invariant, E. SAME-AS clustering, F. Counts and acceptance thresholds,
G. Spot checks, H. Adapter sidecar sanity).

Sandbox dry-run: 22 passed against mock canonical store; F1-F4 fail
(expected — they enforce ≥9000 work / ≥150 sci-layer scholars
thresholds that need real Mac data); 3 schema tests skip (sandbox
lacks `schemas/`).

---

## Acceptance criteria status

| ID | Criterion | Mechanism | Sandbox check |
|---|---|---|---|
| Q | ≥9,000 canonical work records | F1 test | ✗ (mock=5; needs real run) |
| R | Bidirectional ≥95% | D1+D2 tests + Pass A stats | ✓ (100% in mock) |
| S | ≥150 of 182 sci-layer scholars carry `authored_works[]` | F4 test | ✗ (mock=2; needs real run) |
| U | ≥18 acceptance tests | test_work_pilot.py | ✓ (29 tests) |
| V | SAME-AS precision ≥90% on 30-record hand-curated overlap | E3 + manual review | ✓ proxy (1.0 in mock; real measurement is post-run audit) |
| X | Tier 1+2 ≥70% of OpenITI's 3,618 authors | C1 test + pre-pass stats | ✗ (mock=75% on 4-author fixture; statistical sample too small — real measurement on Mac) |

**T (patron) and Y (dia_works spot-audit) were dropped** in the
session-plan revision — patron field is not in v0.1.0 work.schema, and
dia_works moved to Hafta 6 with audit script as the seed.

---

## Architecture decision: dia_works DROPPED from Hafta 5

**Pre-flight finding** on `data/sources/dia/dia_works.json`:
44,611 work-mentions across 3,369 DİA slugs (median 11
titles/scholar, max 94 at "ibnul-arabi-muhyiddin"). Spot-check on
"abbadi-ebu-mansur": 4 of 11 listed titles wrongly attributed —
- Mu'cemü'l-büldân = Yâqūt's, not Abbâdî's
- el-Muntaẓam = İbnü'l-Cevzî's
- Dîvân-ı Kebîr = Mevlânâ's

The systemic pattern indicates the upstream DİA parser extracts
bibliography section entries as "works by" rather than "works
about/cited."

**Three options were considered**:

- **A**: Drop dia_works from Hafta 5 entirely → ✓ chosen
- **B**: Mint all 44K with confidence flags → rejected (breaks P0.2
  invariant; confidence-flag UI work scope-creep; refactor priority is
  authoritative single-source store, not "mostly-correct")
- **C**: Cross-validate gate (mint only HIGH-confidence subset via
  OpenITI cross-attestation) → rejected (single-layer attestation gives
  MEDIUM-HIGH at best; Hafta-4 xref_alam audit lesson: ~%23 of
  cross-validated records still wrong)

**Hafta 6 plan** (deferred):

1. Re-extract dia_works from `dia_chunks.json` with structural
   "telif etti / yazdı / kaleme aldı" lexical patterns (bypass upstream
   parser)
2. Brockelmann/GAL pipeline as ground truth (171 records GAL-1.2-001
   to 171 already exists; target 26 sessions)
3. Three-way cross-attestation: re-extracted DİA ∩ OpenITI
   corpus_authors.works[] ∩ Brockelmann GAL — record passes if in
   ≥2 of 3
4. Use `dia_works_h5_audit.json` from this session as the priority
   triage list (low_likely_misattribution rows go straight to manual
   review queue)

---

## Frontend integration note (Phase 0b — Fatıma Zehra Nur Balcı)

**Critical invariant for engineering layer**: After Pass A runs, a
person's `authored_works[]` may include both science_works and
openiti_works PIDs of the SAME work (cross-source duplicates that Pass
B clustered).

**Example**: Ibn Sina's `authored_works = [iac:work-00000001 (sci_works
Canon), iac:work-00000010 (openiti_works Qanun), iac:work-00000011
(openiti_works Najat)]`. Pass B detected work-001 and work-010 belong
to the same SAME-AS cluster (`cluster-000001`).

When rendering "Eserleri" on the scholar page, the engineering layer
must:
1. Read each work's `_same_as_cluster_id` field
2. Group works by cluster (works without cluster ID stay solo)
3. Display ONE entry per cluster, using the cluster's `canonical`
   member as the primary representation (or merge labels from all
   members)
4. Show "Multiple sources" badge for cross-source clusters (counts in
   `cluster.sources_seen`)

Without this, the same work appears 2x in the scholar's Eserleri
list. The cluster sidecar at
`data/_state/work_same_as_clusters.json` is the lookup index.

---

## File layout

```
hafta5-deliverable-v1/
├── pipelines/
│   ├── _lib/
│   │   └── work_canonicalize.py          ~600 lines
│   ├── adapters/
│   │   ├── science_works/
│   │   │   ├── manifest.yaml
│   │   │   ├── extract.py                ~110 lines
│   │   │   ├── canonicalize.py           ~250 lines
│   │   │   └── __init__.py
│   │   └── openiti_works/
│   │       ├── manifest.yaml
│   │       ├── extract.py                 ~75 lines
│   │       ├── canonicalize.py           ~250 lines
│   │       └── __init__.py
│   └── integrity/
│       ├── openiti_author_resolve.py     ~390 lines
│       ├── work_integrity.py             ~430 lines (Pass A + Pass B)
│       ├── dia_works_h5_audit.py         ~340 lines
│       └── __init__.py
├── tests/
│   └── integration/
│       └── test_work_pilot.py            ~700 lines, 29 tests
├── sample_records/                        5 illustrative work JSONs
├── sidecar_samples/                       3 sidecar examples
└── docs/
    ├── HAFTA5_DELIVERABLE.md             this file
    ├── APPLY_TO_MAC.md                    Mac apply guide
    ├── HAFTA5_SESSION_NOTES.md            decisions journal
    └── NEXT_SESSION_PROMPT_HAFTA6.md      Hafta 6 startup prompt
```

---

## Total LOC

~3,150 lines of Python + ~1,700 lines of test/audit/docs.
