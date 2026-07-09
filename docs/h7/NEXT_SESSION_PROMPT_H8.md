# Next session prompt - Hafta 8

> Paste this into a new Claude session, paired with the
> `islamicatlas_h7_close_snapshot.zip` upload, to start Hafta 8.

---

## Session frame

I am Dr. Ali Cetinkaya (ORCID 0000-0002-7747-6854), assistant professor
at Selcuk University Computer Engineering. I am continuing solo data
work on the **islamicatlas-canonical** Phase 0 refactor of
islamicatlas.org. My primary collaborator on Islamic-history domain
questions is Dr. Huseyin Gokalp (ORCID 0000-0002-7954-083X). My
engineering collaborator Fatima Zehra Nur Balci will start Phase 0b
frontend integration work after Phase 0 data is stable.

This session opens **Hafta 8 (H8)**. The previous session
(H7, 2026-05-05) closed cleanly at commit `8833ec0`.

I am working on a Mac in zsh. Vim is unavailable; sed/heredoc with
Turkish characters tends to choke. **Prefer downloadable Python files
over embedded heredocs** for any non-trivial multi-line content.

## Repo state at H8 open

- **Repo path**: `/Volumes/LaCie/islamicatlas_canonical`
- **Branch**: `hafta5-work-namespace`
- **HEAD**: `8833ec0` (Hafta 7 close)
- **Working tree**: clean
- **GitHub**: github.com/alicetinkaya76/islamicatlas-canonical (push pending)

## Required reading order

Before proposing any H8 stages, read these in order from the snapshot zip:

1. `SNAPSHOT_README.md` - what this snapshot contains and what it does NOT
2. `docs/h7/HAFTA7_CLOSE_STATE.md` - master ledger of H7 outcomes,
   acceptance scorecard, pre-existing issues
3. `docs/h7/H7_KNOWN_ISSUES.md` - PE-1 documentation (the H8 first task)
4. `docs/decisions/ADR-009-dia-works-rich-vs-shallow-mint.md` -
   the doctrine that constrains DiA-side mint pipelines
5. `docs/h7/H7_DECISION_LOG.md` - 6 decisions made in H7, for context
6. `docs/h7/H7_MASTER_PLAN_REVISION.md` - re-defined AA/AB/AG criteria

After reading, **confirm baseline understanding** before proposing
H8 stages. Do not propose Stream 2 mint pipelines without first
confirming you have read ADR-009.

## H8 priority structure

H7 close commit established three priorities for H8:

### Priority 1 - PE-1 remediation (RECOMMENDED FIRST)

**What**: 2,262 person records carry `provenance.derived_from[0].source_type
== "digital_corpus"`, but person.schema enum allows only
`[primary_textual, secondary_scholarly, tertiary_reference,
manual_editorial, authority_file]`. Source: H4 v0.1.0 seed (commit
6ac18b2). H6 schema migration narrowed enum but did not re-validate
existing records. H7 surfaced the issue when running full integration
suite.

**Why first**: Closes a long-standing schema invariant violation,
unlocks "test suite fully green" baseline for any subsequent H8 work.
Quick win, ~30-60 min.

**Recommended approach (Option B1)**:
1. Patch `schemas/person.schema.json` (or whichever common schema
   defines source_type enum) to add `digital_corpus`. Schema bump
   v0.2.0 -> v0.2.1.
2. Write `docs/decisions/ADR-010-source-type-digital-corpus.md`
   documenting the semantic of digital_corpus as "OpenITI digital
   corpus tier 4 placeholder where author is attested via OpenITI
   text URI but no fulltext mint exists yet".
3. Write a small migration journal in `docs/h7/`-equivalent
   `docs/h8/` (start the H8 doc set!).
4. Re-run full integration suite, confirm 74 passed (was 73 + the
   1 fixed PE-1).
5. Commit as `Hafta 8 Stage 1: PE-1 remediation - schema enum
   digital_corpus + ADR-010 + suite green baseline`.

### Priority 2 - Raw DiA encyclopedia source data acquisition

**What**: ADR-009 requires rich-mint records with multilingual
prefLabel + description + page locator. The current dataset
`data/sources/dia/dia_works.json` is shallow (just title strings
per slug) and cannot provide this richness. The actual source
must be either:
- `data/sources/dia/dia_chunks.json` (gitignored, may exist locally)
- TDV Islam Ansiklopedisi web pages (https://islamansiklopedisi.org.tr)
  via polite scraping
- A structured DiA dataset acquired through institutional access

**First step**: Check locally for `dia_chunks.json` or equivalent
structured raw source. If not present, the H8 plan must include a
data acquisition session.

### Priority 3 - ADR-009-conformant rich-mint pipeline

**What**: Once raw source data is available, implement
`pipelines/adapters/dia_works/` per the ADR-006 4-file adapter
contract (manifest.yaml + extract.py + resolve.py + canonicalize.py).
Each generated record must pass an ADR-009 conformance check before
being written.

**Effort**: 6-10 hours if dia_chunks accessible; multi-session if
scraping pipeline must be built.

## Constraints from H7

- **No new dia_works mints unless rich-mint threshold met** (ADR-009).
- **No silent schema enum changes** - every schema change must have
  an ADR and migration journal.
- **No `digital_corpus -> tertiary_reference` mass rename** - that
  was Option B2, rejected as wrong semantic.
- **Test suite must remain runnable as a whole**: run
  `pytest tests/integration/` (not just one file) at every close.
- **Doc set per week**: H7 established a `docs/h7/` template with
  4 files (CLOSE_STATE, DECISION_LOG, KNOWN_ISSUES,
  MASTER_PLAN_REVISION); H8 should follow the same pattern in
  `docs/h8/`.

## Open questions for me at H8 kickoff

When proposing H8 plan, please ask me:

1. Is `data/sources/dia/dia_chunks.json` present on my Mac? (I should
   `ls -la` to check.) If yes, sample its schema to determine if
   rich-mint is feasible from it. If no, we plan acquisition.
2. What is the time budget for H8? (4 hours? 6 hours? full day?)
3. Should Priority 1 (PE-1) be done in this session as a quick
   first stage, then Priority 2/3 in a later session - OR - do the
   full pipeline this session?
4. Any new H7-after-the-fact decisions or context I should know?

## Communication mode

- High-level discussion in Turkish, code/docs in English.
- "sen sec" - default to choosing autonomously, surface real decision
  points for explicit sign-off.
- Brief but thorough; don't ask for my opinion on every minor choice.
- For non-trivial multi-line content (heredocs, sed patches with
  Turkish chars), produce a downloadable Python file via the file
  output channel rather than embedding in shell commands.

## H7 commit chain (for reference)

```
8833ec0 Hafta 7 Stage 3+4+5: ADR-009 doctrine + H7 doc set + close
93927b5 Hafta 7 Stage 2: frontend spec - Wikidata QID display policy gate
9ee147a Hafta 7 Stage 1: QID audit - flag 4 confirmed-wrong wikidata QIDs
5e7618e Hafta 6 Stream 5: frontend integration spec (H6 close, Phase 0b kickoff)
b03a8a5 Hafta 6 Stream 3: OpenITI QID seed diagnostic harness
564f1c8 Hafta 6 Stream 1: Hassaf one-off mint + slug-to-pid
f5f502f Hafta 6 Stream 4: schema v0.1.0 -> v0.2.0 SAME-AS structural field
1034ca9 Hafta 5: work namespace seed (science_works + openiti_works)
6ac18b2 Hafta 4 v2: person namespace seed (20,650 records, 26/26 tests green)
```

The H4 v2 commit is the source of PE-1; the rest of the chain is
clean.

---

**End of next session prompt.** Begin H8 by reading the snapshot
files in the order specified, then asking me the open questions
above before proposing stages.
