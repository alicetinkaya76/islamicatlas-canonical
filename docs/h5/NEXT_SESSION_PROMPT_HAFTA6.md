# Next Session — Hafta 6 Startup Prompt

Paste this into the Hafta 6 session opener. It assumes you have just
finished applying Hafta 5 to the Mac repo (commit on
`hafta5-work-namespace` branch, merged or to-be-merged into main).

---

## Context summary for the next session

You are continuing **Hafta 6** of the islamicatlas.org v7.8 → v8
canonical refactor. The work namespace seed is already in place from
Hafta 5:

- ~9,200–9,400 `iac:work-*` records from two adapters (science_works
  + openiti_works)
- 3,618 OpenITI authors cross-walked (T1+T2 ≥70%, ~600-1,300 T4
  placeholders minted)
- Bidirectional `work.authors[] ↔ person.authored_works[]` invariant
  holds at ≥95%
- ~30-80 SAME-AS clusters identified via fingerprint+author dual gate
- 29 acceptance tests green
- `data/_state/dia_works_h5_audit.json` is the Hafta 6 starting input

**Refactor priority remains**: islamicatlas.org as the consumer. Papers
queued for *after* the canonical store stabilizes.

---

## Hafta 6 scope (4 streams, prioritize in this order)

### Stream 1 — dia_works canonical mint (the biggest deferred item)

This is what Hafta 5 explicitly didn't do. The audit script's output
band-classifies every (slug × title) pair:

```bash
jq '.summary.confidence_band_counts' data/_state/dia_works_h5_audit.json
```

**Per-band action plan**:

- `high_validated_both_sources` (~500 expected): mint a new
  canonical record + add SAME-AS link to the matched existing work
  (extends the cluster). These are confidence-1.0 records that
  triangulate three sources (DİA + science_works + openiti_works).

- `moderate_validated_one_source` (~3,000-5,000): cross-check against
  Brockelmann/GAL pipeline. The GAL pipeline is at GAL-1.2-001..171
  with target 26 sessions; for Hafta 6, focus on running 5-10 more
  GAL sessions to widen the validation cone, then re-audit.

- `low_likely_misattribution` (~5,000-15,000): **drop these from
  canonical mint**. They go to a manual review queue
  (`data/_state/dia_works_h6_manual_review.jsonl`). The upstream DİA
  parser fed bibliography references as "works by"; this band
  contains those errors. Don't try to mint them as low-confidence —
  the refactor's premise is *authoritative* records.

- `no_external_match_dia_only` (largest band, est. 15,000-25,000):
  These are titles that exist in DİA but not in science_works or
  openiti_works. Could be:
  - (a) Legitimate DİA-unique scholar attributions that other corpora
    don't have. Mint as standalone iac:work-* with single-source
    provenance.
  - (b) Mis-attributions invisible to fingerprint matching (e.g.
    titles common enough to appear in multiple bibliographies).
  
  Distinguish via DİA chunk re-extraction (Stream 2).

- `scholar_unresolved` (~varies): the DİA scholar's PID isn't
  resolvable. Pre-pass to map dia_slug → person_pid.

### Stream 2 — DİA chunk re-extraction (bypass upstream parser)

The upstream `dia_works.json` was parsed via heuristics that conflate
"works by" with "works cited/about." Hafta 6 builds a structural
extractor working from `data/sources/dia/dia_chunks.json` (the raw
chunk store):

**Lexical anchors for "works by" extraction** (prioritized):
1. `"telif etti"` (composed)
2. `"yazdı"`, `"yazdığı"` (wrote)
3. `"kaleme aldı"` (penned)
4. `"<Name>'in <Title> adlı eseri"` (the work titled <Title> by <Name>)
5. `"Eserleri:"` section header

**Lexical anchors to AVOID** (these are "works about/cited"):
- `"hakkında bilgi veren <Title>"`
- `"<Title> adlı eserden naklen"`
- Section headers `"Bibliografya"` / `"Kaynaklar"` (this is where the
  upstream parser went wrong)

Output: a *new* `data/_state/dia_works_h6_reextracted.json` that the
canonical mint adapter consumes instead of the original
`dia_works.json`.

### Stream 3 — OpenITI Tier 3 manual seed (top-100 authors)

Adds Wikidata QIDs for ~85 famous authors not yet in the auto-seed.
Boosts Tier 1 from a few percent to ~5-10%, and tightens Tier 2 hits
for those authors.

```bash
# The seed file: data/sources/openiti_qid_seed.json
# Add entries like:
#   "0204Shafii": "Q199517",
#   "0241IbnHanbal": "Q193710",
#   ...
```

After updating the seed, re-run the pre-pass + openiti_works adapter
+ Pass A. **Do not re-run integrity Pass B** unless the seed change
materially affected fingerprint clustering.

### Stream 4 — Frontend integration handover (Phase 0b)

Hand off to Fatıma Zehra Nur Balcı:

1. `_same_as_cluster_id` field semantics — engineering layer must
   dedupe via this when rendering scholar pages
2. `composition_temporal.approximation = "before"` rendering — show
   "≤ year" tick rather than a point on timelines
3. `_quick_validation_errors` debug field (only present on records
   that failed quick validation; ignore in normal rendering)
4. Tier 4 placeholder persons distinguished by minimal labels +
   `provenance.derived_from[].source_id.startswith("openiti:")` —
   these are scholars whose biographic content will be enriched in
   Hafta 6 (or later); UI may want a "limited info" badge

---

## Acceptance criteria — proposed for Hafta 6

| ID | Criterion | Notes |
|---|---|---|
| AA | dia_works mint count: 8,000-25,000 records | After dropping `low_likely_misattribution` band; depends on Stream 2's re-extraction quality |
| AB | dia_works DİA-unique mints have valid `provenance.source_id` starting with `dia:` | Single-source provenance, schema-valid |
| AC | High-confidence dia_works → SAME-AS link to existing work | At least one cluster member from `high_validated_both_sources` band gets a cluster ID |
| AD | manual_review queue ≤ 20% of total dia_works | Indicates Stream 2's re-extraction worked |
| AE | OpenITI Tier 1 ≥ 3% of authors after manual seed | Was ≤1% in Hafta 5 |
| AF | Schema migration applied: `authority_xref.authority` enum extended with `iac_same_as` | Allows promoting `_same_as_cluster_id` to structural xref |
| AG | tests/integration/test_work_pilot.py extended with 5-10 dia_works-specific tests | E.g. mis-attribution-band records absent from canonical store |
| AH | dia_works canonical records pass all existing 29 H5 tests | No regression |

T (patron) deferred again to Hafta 7 with schema migration alongside.

---

## Things to verify on session start

```bash
cd /Volumes/LaCie/islamicatlas_canonical
git log --oneline | head -5    # Hafta 5 commit visible
ls data/canonical/work | wc -l                          # ≥ 9,000
ls data/_state/dia_works_h5_audit.json                 # exists
jq '.summary' data/_state/dia_works_h5_audit.json      # band counts visible
pytest tests/integration/test_work_pilot.py -v 2>&1 | tail -3   # all green
```

If any of these fail, run the Hafta 5 APPLY_TO_MAC.md "Common failure
modes" section before proceeding to Hafta 6 work.

---

## First-turn ask in Hafta 6

Drop into the new session with this opener:

> Hafta 6 başlıyorum. islamicatlas.org refactor önceliği devam.
> Hafta 5'te dia_works'i tamamen erteledik, audit sidecar
> (`data/_state/dia_works_h5_audit.json`) Hafta 6 başlangıç noktası.
> 
> İlk kararım: Stream 2 (DİA chunk re-extraction) mı, yoksa Stream 1
> (audit-band-driven mint) mi öncelik? Stream 2 daha temiz veri
> üretir ama Stream 1'e göre daha uzun sürer (chunk parser yazımı +
> validation). Stream 1 ile başlarsam high_validated_both_sources
> band'ında ~500 hızlı mint olur, momentum kazanırım. Hangisi?
> 
> Senin (Claude) görüşün ne?

Claude (in that next session) should:
1. Read `dia_works_h5_audit.json` summary stats first
2. Inspect 5-10 spot-check entries from each band
3. Recommend Stream order based on band-count distribution
4. If `high_validated_both_sources` is small (≤200), Stream 2 first
   makes more sense; if it's substantial (≥1,000), Stream 1 quick-win
   first
