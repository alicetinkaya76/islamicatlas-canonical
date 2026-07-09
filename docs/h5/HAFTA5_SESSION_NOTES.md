# Hafta 5 Session Notes — Decisions & Trade-offs Journal

This file captures the *why* behind Hafta 5's structural choices, so
the next session (Hafta 6) — and Fatıma Zehra Nur Balcı when she joins
in Phase 0b — can see the context, not just the code.

## Session frame

- **Priority lens**: islamicatlas.org v7.8 → v8 refactor (frontend
  authority + engineering layer consumer). Papers explicitly NOT the
  driver this session — they're queued for after the canonical store
  is solid.
- **Working mode**: "sen seç" (the assistant chooses), with explicit
  decision points surfaced for sign-off.
- **Output style**: Türkçe high-level discussion + English code/docs.

---

## Decision 1 — dia_works dropped from Hafta 5 (Option A)

**Context**: Pre-flight inspection of `data/sources/dia/dia_works.json`
revealed a structurally large dataset (44,611 work-mention rows across
3,369 DİA scholar slugs, median 11 titles/scholar, max 94 at
"ibnul-arabi-muhyiddin"). On the surface, this looked like the biggest
high-leverage adapter to write.

**Spot-check that broke the plan**: `abbadi-ebu-mansur` has 11 listed
titles. Manual review of the first 4 found:
- `Mu'cemü'l-büldân` → actually Yâqūt's geographical dictionary
- `el-Muntaẓam` → actually İbnü'l-Cevzî's chronicle
- `Dîvân-ı Kebîr` → actually Mevlânâ's collected poetry
- `el-Hidâye fi'l-Furû'` → likely legitimate Abbâdî attribution

That's a 75% mis-attribution rate on a single sampled scholar,
suggesting the upstream DİA parser is extracting bibliography section
entries (the "see also" / "sources cited" footer of each entry) as if
they were "works by" entries.

**Three options weighed**:

| Option | Mechanism | Why rejected |
|---|---|---|
| A | Drop entirely from H5; mint nothing | ✓ chosen |
| B | Mint all 44K with confidence-flag metadata | Breaks P0.2 invariant; UI scope-creep ("hide low-confidence" toggles); refactor priority is *authoritative* single-source store |
| C | OpenITI cross-attestation gate (mint only HIGH-confidence subset) | Hafta-4 xref_alam audit lesson: cross-attestation alone gives MEDIUM-HIGH at best (~%23 of "validated" records still wrong). Single-layer gate insufficient. |

**Refactor-priority lens** (added later in the session after explicit
user reminder): islamicatlas.org users encountering Mevlânâ's
*Dîvân-ı Kebîr* on Abbâdî's scholar page would directly damage the
site's academic credibility. The whole point of the v7.8 → v8 refactor
is establishing an *authoritative* single-source store. Polluting it
with known-bad attributions, even with confidence flags, defeats the
refactor's purpose.

**Hafta 6 plan**:
1. Re-extract from `dia_chunks.json` with structural lexical patterns
   ("telif etti", "yazdı", "kaleme aldı") that bypass the broken
   upstream parser
2. Use Brockelmann/GAL pipeline (171 records GAL-1.2-001..171 already
   exist) as ground truth; target 26 sessions to cover GAL fully
3. **Three-way cross-attestation**: re-extracted DİA ∩ OpenITI
   corpus_authors.works[] ∩ Brockelmann GAL — mint only when ≥2 of 3
   agree
4. Use `dia_works_h5_audit.json` as the priority triage list — the
   `low_likely_misattribution` band is where the upstream parser bugs
   live

---

## Decision 2 — Two adapters only, no Tier 3 manual seed

**Context**: The session-plan acceptance criteria initially included
both:
- T (patron field on works)
- Y (dia_works spot-audit deliverable)

Both were **descoped** mid-planning:
- **T (patron)**: work.schema v0.1.0 doesn't have a `patrons[]` field,
  per pre-flight schema dump. Adding one would require a schema
  migration in this session. Deferred — patron data is mostly in
  science_layer's curated entries already (note field), not lost.
- **Y (dia_works spot-audit)**: replaced by the much more useful
  `dia_works_h5_audit.json` (audit with confidence bands), which is
  Hafta 6's actual starting input rather than a dead-end record.

OpenITI Tier 3 (manual top-100 author seed) was also descoped to
Hafta 6 — Tier 1+2+4 already meets the ≥70% acceptance, and manual
seeding is brittle solo work that benefits from being batched with
Hafta 6's biographic enrichment of Tier 4 placeholders.

---

## Decision 3 — Title fingerprint algorithm trade-offs

The fingerprint algorithm is the heart of cross-source SAME-AS
clustering. Three algorithm iterations during the session:

**Iteration 1** (failed): Diacritic strip + lowercase + dash/quote
strip + tokenize + sort. Result: 0/3 same-work test groups matched.
Failure mode: Turkish `ı` doesn't NFKD-decompose (precomposed
codepoint), leaving `tıb` ≠ `tib`; apostrophe-split orphans (`fi't` →
`fi t` → orphan `t` token) inflated tokens; Arabic `ال-` prefix
unhandled.

**Iteration 2** (3 fixes added): Turkish ASCII fold table
(`ı→i, ş→s, ğ→g, ç→c, ö→o, ü→u, â→a, î→i, û→u`), single-letter
orphans dropped, Arabic article/connector token-strip. Result:
3/3 test groups passed but `Hayawan` ↔ `Hayevan` still failed (same
work, different vowel: medieval Turkish `e` ↔ Arabic `a`).

**Iteration 3** (final): Added per-token Latin transliteration folds
(`kh→h, dh→d, th→t, gh→g, sh→s, j→c, w→v, q→k`), aggressive
**`e→a` fold** (Cebr ↔ Jabr, Hayevan ↔ Hayawan, Mes'udi ↔ Mas'udi),
double-letter collapse (`tt→t, bb→b, etc.`), trailing Arabic
case-ending strip (`Makamatu → Makamat, Hisabi → Hisab`), modifier-
letter strip (`ʾʿ` for Sifaʾ ↔ Sifa). Final: 8/8 same-work test
groups match, 0/5 different-work test groups collide.

**The `e→a` fold is intentionally aggressive** — semantically `e` and
`a` are sometimes the same vowel in transliteration (Turkish `Cebr` =
Arabic `Jabr`; `Şerh` = `Sharh`), sometimes different (`Mecmu` ≠
`Macmu` rarely; `Ferh` doesn't really exist). False-positive risk is
mitigated by Pass B's *author-PID dual gate*: even if two unrelated
works fingerprint to the same hash, they don't get clustered unless
they also share at least one author PID.

**Cross-script (Latin ↔ Arabic) NOT folded algorithmically**.
Implementing a full Arabic → Latin transliteration table would take
~150 lines of mappings for marginal gain. Instead,
`fingerprint_all_labels()` returns a *set* of fingerprints (one per
label variant), and Pass B uses set intersection — works that have
both Arabic and Latin labels overlap via either.

---

## Decision 4 — `composition_temporal` derivation for OpenITI works

OpenITI corpus_works.json mostly lacks an explicit `composition_year`
field. Three options:

| Option | Behavior |
|---|---|
| A | Omit `composition_temporal` field entirely | Frontend timeline rendering breaks for ~95% of OpenITI works |
| B | Estimate "30 years before death" | Fictitious precision — refactor anti-goal |
| C | Use `{end_ce: author_death_ce, approximation: "before"}` | ✓ chosen |

C says "this work was composed before this date" without inventing
precision the source doesn't carry. Frontend timelines render as a
"≤" indicator. The truthful framing matters for academic credibility.

---

## Decision 5 — Tier 4 placeholders are real person records, not stubs

The pre-pass mints `iac:person-*` PIDs for unmatched OpenITI authors
(Tier 4). Two paths:

| Option | Mechanism |
|---|---|
| Stub | Just allocate the PID, no person record file. openiti_works.authors[] points to a non-existent record. |
| Full record | Mint a minimal but schema-valid person record. ✓ chosen |

The bidirectional invariant (P0.2 hard rule) requires every author
PID in any work record to map to a real person record. Stubs would
violate that. So Tier 4 placeholders include:

- `@id`, `@type: ["iac:Person"]`
- `labels.prefLabel` (Latin from camelCase split of author_id, Arabic
  from `name_native_ar` if present)
- `death_temporal` (from author_id prefix AH year, converted to CE
  via standard Tabular Islamic formula)
- `provenance.derived_from = [{source_id: "openiti:0494ObscureWriter",
  source_type: "digital_corpus"}]`
- `profession: ["scholar"]` default — Hafta 6 enrichment can revise
- `note`: explicit "Tier 4 placeholder, biographic content sparse,
  pending Hafta 6 enrichment"

This means **the canonical person count grows from ~19,684 to
~20,300–20,900** after Tier 4 mint. That's expected and doesn't
affect Hafta-4 acceptance criteria (which were on the existing person
namespace).

---

## Decision 6 — SAME-AS info storage: note field, not authority_xref

**Schema constraint discovered**: `authority_xref.authority` enum in
v0.1.0 doesn't include `iac_same_as` or `same_as`. Adding it would
require schema migration.

**Pattern from Hafta 4**: DİA, El-Aʿlām, EI1 cross-references hit the
same enum gap. The Hafta-4 solution was to put structured info in a
sidecar (e.g. `science_layer_xref_alam.json`) and a human-readable
line in the work's `note` field.

**Hafta 5 mirrors that pattern**:
- Structured cluster info → `data/_state/work_same_as_clusters.json`
  (the engineering layer queries this)
- Human-readable line in `note`: `"Same-as cluster:cluster-NNNNNN
  (size=2, cross_source=True); members: iac:work-XXX, iac:work-YYY"`
- A non-schema-validated `_same_as_cluster_id` field is also added
  (underscore prefix flags it as internal/draft; consumers can use it
  but must not depend on it being in the schema). Hafta 6 schema
  migration: promote this to a proper field.

---

## Decision 7 — Test count: 29 (target was 20-22)

Initially planned 20-22 tests. Ended at 29. The extra 7-9 tests came
from:
- Splitting bidirectional into D1 (work→person) + D2 (person→work) +
  D3 (orphan threshold) — three independent failure modes
- Adding G4 (Tier 4 placeholder shape sanity) after writing the
  Tier 4 mint logic
- Adding H1/H2/H3 sidecar-sanity tests (low-cost, high-value
  diagnostic if pipeline ordering breaks)

The trade-off here was: test count over diagnostic granularity. With
29 tests, when something breaks, the failing test name immediately
points to the broken subsystem.

---

## Decision 8 — Frontend integration is OUT of scope

Sample-record observations during Pass A testing made clear: after
Pass A back-writes, Ibn Sina's `authored_works = [00000001, 00000010,
00000011]` includes both science_works and openiti_works PIDs of the
SAME work (cluster_001 members). The engineering layer (Phase 0b)
must dedupe via `_same_as_cluster_id`.

**This is documented but NOT implemented in Hafta 5**. The canonical
store is correct; the rendering is a downstream concern.

When Fatıma Zehra Nur Balcı starts Phase 0b, the
`HAFTA5_DELIVERABLE.md` "frontend integration note" section is the
hand-off for this. Not addressing it leaves "Eserleri" lists with
duplicates on islamicatlas.org.

---

## What I'd do differently next time

1. **Pre-flight schema dumps earlier**. Some of the work_canonicalize.py
   design (especially WORK_SUBTYPES enum) is best-guess from
   pre-flight queries. A direct `cat schemas/work.schema.json` at
   session start would have saved one round-trip. Mac apply may
   surface schema-enum mismatches that need fixing post-hoc.

2. **Hand-curated 30-record SAME-AS validation set built BEFORE Pass B**.
   Acceptance V (precision ≥90%) currently has only the precision
   *proxy* (dual-gate-pass / dual+gate1-only). The real measure
   requires hand-labeled known overlaps. Defer to Hafta 6 audit.

3. **Author-PID gate could be tier-aware**. Currently Pass B's gate-2
   treats all author overlaps the same. A T1-resolved author overlap
   is much stronger evidence than a T4-placeholder overlap. Future
   refinement: weight cluster confidence by author resolution tier.

4. **Composition_temporal `before` for OpenITI** is correct but
   visually noisy on islamicatlas.org timelines (every OpenITI work
   shows a "≤ death year" tick instead of a point). Frontend may
   need a per-work "show as range" or "show as point at midpoint"
   toggle. Talk to Fatıma Zehra Nur Balcı.

---

## Numbers worth remembering for Hafta 6

| Metric | Mac-run target |
|---|---|
| science_works records minted | ~220–300 (181 scholars × ~1.2 key_works avg + ~80 filtered discoveries) |
| openiti_works records minted | ~9,000–9,104 (depends on author-id parse success rate) |
| Total iac:work-* | ~9,200–9,400 |
| Tier 4 placeholders minted | ~600–1,300 (depends on T1+T2 rate) |
| New canonical person count | ~20,300–20,900 (was ~19,684) |
| SAME-AS clusters | ~30–80 (cross-source pairs of "famous" works) |
| dia_works audit titles processed | 44,611 |
| dia_works `low_likely_misattribution` rows | likely 5,000–15,000 (the priority Hafta 6 triage) |
