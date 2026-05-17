# H8 Stage 2b — Analyzer findings audit trail

**Date:** 2026-05-17
**Purpose:** Document the v1 → v2 analyzer trajectory and the three
empirical findings that prompted ADR-011 v1.1 + ADR-012.

---

## Why this document exists

Stage 2 produced ADR-011 v1 on the basis of a profiler that under-
described the dia_chunks.json schema. The first run of the calibrated
analyzer (v1, `analyze_dia_enrichment.py`) revealed three discrepancies
that v1 of ADR-011 had baked-in incorrect assumptions about. Rather
than silently rewrite ADR-011, this document preserves the v1 → v2
audit trail: what was thought, what was measured, what was revised.

## The three findings

### Finding 1: Per-slug chunk aggregation (smoking gun: 275.9%)

**v1 output line**: `Cat A eligible: 9,129 (100.0% of Cat A, 275.9%
of slug_to_pid)`

The 275.9% number is the smoking gun. slug_to_pid has 3,309 entries;
Cat A has 9,129 chunks; ratio is 2.76 chunks per slug. This contradicts
the v1 ADR-011 premise that each chunk is an independent enrichment
unit.

**v2 measurement** (analyzer v2 with explicit slug aggregation):

| Metric | Value |
|---|---:|
| Total chunks | 19,742 |
| Distinct slugs | 8,093 |
| Avg chunks/slug | 2.44 |
| Cat A distinct slugs | 3,309 (exactly matches slug_to_pid) |
| Chunks-per-slug distribution | 1: 672, 2: 1,474, 3: 623, 4: 258, 5: 89, 6: 64, 7+: ~88 slugs |
| Max chunks for one slug | 12+ (canonical figures) |

**Adapter implication**: aggregate by slug (sort by `c`, concat `t`
with `\n`), produce one description.tr per slug. ADR-011 v1.1 §"Patch
shape" formalizes this.

### Finding 2: `a` field is Arabic title, NOT TDV contributor

**v1 sample output** (after v1 ADR-011 was written):

```
'ibnun-neccar-el-bagdadi'      t_len= 3101  → iac:person-00004301
   a='ابن النجّار البغدادي'                                    ← Arabic name
'ibn-tolun-semseddin'          t_len= 4179  → iac:person-00004055
   a='شمس الدين ابن طولون'                                    ← Arabic name
'ibn-kadi-aclun-takiyyuddin'   t_len=  472  → iac:person-00003889
   a='تقيّ الدين ابن قاضي عجلون'                                ← Arabic name
```

The `a` field contains Arabic-script content matching the SUBJECT of
each entry, not the contributor's name. ADR-011 v1 routed this to
`provenance.attributed_to` — factually wrong.

**v2 measurement** (Arabic-script Unicode check on Cat A):

| Class | Count | % |
|---|---:|---:|
| arabic_primary | 2,265 | 68.4% |
| empty | 1,044 | 31.6% |

Empty entries are predominantly modern figures (Erişirgil, Cerulli,
Hourani — Western scholars or modern Turkish intellectuals) for whom
no Arabic name form exists.

**Adapter implication**: `a` routes to `labels.prefLabel.ar` when
a_classification == "arabic_primary"; ignored when empty. ADR-011 v1.1
§"Patch shape" Step 4 formalizes this. `provenance.attributed_to` is
left unset (no source for TDV contributor available without H9
scraping).

**Doctrinal implication beyond enrichment**: dia_chunks satisfies
ADR-009 threshold (a) (multilingual prefLabel ≥ 2 langs) for 68% of
slugs — combining Turkish `n` and Arabic `a`. The ADR-009 deferral
for `dia_works` rich-mint remains because threshold (c) (cilt+sayfa)
is still absent; only the scraping pipeline closes that gap. But the
"chunks lack Arabic" claim from v1 is corrected.

### Finding 3: Truncation crisis at 5,000-char limit

**v1 verdict**: "0% overflow rate — Karar 4 truncation strategy is fine"

This was per-chunk overflow, hiding the per-slug aggregation reality.

**v2 measurement** (per-slug aggregated narrative length):

| Statistic | Value |
|---|---:|
| min | 1,209 |
| median | **6,337** |
| mean | 8,854 |
| p95 | 20,450 |
| max | 318,213 |
| stdev | 12,578 |

**At maxLength=5,000**: 68.8% of Cat A slugs (2,278 of 3,309) would
truncate. Unacceptable per ADR-011's academic credibility argument.

**Decision**: ADR-012 bumps `description.<lang>` maxLength 5,000 →
50,000. At 50,000, truncation fires on ~5% long-tail (the truly
massive entries — İbn Teymiyye, Süleyman, Selçuklular). Karar 4
strategy applies to that tail only.

### Date format diversity (auxiliary)

v1 regex matched `(ö. HHHH/MMMM)` and `(ö. NNN)` — covered 33% of
chunks. v2 regex (six patterns) covered 88.8% of Cat A slugs:

| Pattern | Cat A coverage |
|---|---:|
| hijri_gregorian `(ö. 728/1328)` | 52.3% |
| gregorian_range `(1891-1965)` | 34.6% |
| hijri_only `(ö. 562)` | 1.8% |
| approximate `(ö. h. 685 civarı)` | <0.1% |
| unparseable | 11.1% |
| no_d_field | 0.1% |

Most unparseable cases are exotic patterns (`(M.S. 800 civarı)`,
`(VI. yüzyıl sonu)`, etc.). 88.8% coverage is sufficient for date
cross-validation across the bulk of records; unparseable cases simply
leave `death_temporal` unset (no false data injected).

## Process retrospective

Three lessons for future weeks:

1. **Profile against the actual schema, not an assumed one.** The
   first profiler (`profile_dia_chunks.py`) made field-name
   assumptions (looking for `title_tr`, `cilt`, `sayfa`) that didn't
   match dia_chunks's tersely-named schema (`n`, `t`, `s`, `c`). The
   recovery cost was one full doctrine iteration.

2. **Per-record vs per-key distinctions matter early.** The "9,129
   chunks at 275.9% of slug_to_pid" line should have triggered
   immediate suspicion about chunk-per-slug multiplicity. Future
   analyzers should report both record-count and distinct-key-count
   side by side.

3. **Sample inspection reveals what statistics miss.** The five
   sample rows in v1 output were the proof that `a` is Arabic-script
   subject name, not TDV contributor. Always include samples; never
   trust statistics alone.

## Trajectory summary

```
Stage 2 v1 (uncommitted draft, written from v0 profiler):
    ADR-011 v1: a → provenance.attributed_to (WRONG)
                per-chunk patch (PARTIAL)
                truncate at 5000 as default (PARTIAL — works per-chunk)
                date regex: 2 patterns (PARTIAL)

Stage 2b analyzer v2 (run after v1 doctrine drafted, before v1 commit):
    Three findings surfaced.

Stage 2c (this turn — single ADR-011 v1.1 commit, no v1 git history):
    ADR-011 v1.1: a → labels.prefLabel.ar (correct)
                  per-slug patch (correct)
                  ADR-012 bumps schema; truncate fires on long-tail (correct)
                  date regex: 6 patterns (correct)
    ADR-012: new — schema bump rationale
    Both committed in Stage 2c.1 (schema bump) + Stage 2c.2 (doctrine).
```

Result: clean Stage 2 git history (no superseded ADR-011 v1 commit).
Audit trail preserved in this document for academic transparency.
