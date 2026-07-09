# Hafta 9 — Close state

**Date:** 2026-07-09
**Branch:** hafta5-work-namespace
**H8 close reference:** commit `a41642d`, tag `hafta8-close`
**H9 close commit:** *(this commit — Stage 6)*
**H9 close tag:** `hafta9-close`

---

## What H9 accomplished — one paragraph

H9 opened with a schema-coherence fix (Stage 1: the 11-file set atomically
unified at **v0.3.0** + ADR-013), then delivered its headline body of work —
**AO, the TDV İslâm Ansiklopedisi scraper** (Stages 2a-2e): a compliance gate
(ADR-014; robots `Allow:/` but İSAM ToS requires written permission → GO under
maintainer confirmation), a source-producing `dia_tdv_scrape` adapter, and a
polite ~4.5 h bulk run of **8,093/8,093 maddes (0 errors)** producing
`data/sources/dia_chunks_rich.json`: **cilt+sayfa 99.94 %, Arabic title 66.9 %,
per-section müellif 99.9 % (1,423 distinct authors — data absent from the
chunks)**, with 10 records honestly flagged for human review and never
silently accepted. H9 then absorbed a **full-repo review** (Stages 3-5): a
56-agent adversarial sweep surfaced 16 verified bug/perf issues (a live
work-PID collision that would have corrupted the next mint; a TTL-expired recon
cache silently dropping QIDs; a search projector broken on 768 records; phantom
PID classes; dead AP-prep code), all remediated and each fix re-reviewed by a
second 30-agent diff-review (which caught 6 more real defects, also fixed). The
test suite went **101 → 147**, gained a ~9 s inner loop (`make test-fast`), and
CI — previously red on every push and green-on-nothing — now runs the real
gate. Ten H9 commits, zero reverts, zero canonical-data drift (the one state
touch, h9_001, is an idempotent PID-index repair).

## H9 commit chain (oldest first; all on `hafta5-work-namespace`)

```
89cfd79  Stage 1     PE-2 remediation — schema set v0.3.0 + ADR-013
83b006a  Stage 2a    AO compliance gate + Phase-0 verification — ADR-014
2c2284a  Stage 2b    dia-tdv-scrape scaffold + parser + hygiene
84fae1c  Stage 2c    100-slug pilot — coverage 100 %, resume ok
2707ab3  Stage 2d    bulk-run delivery
17c93e0  Stage 2d.1  Arabic-title verification → advisory (rasm)
12dc460  Stage 2e    AO integration — dia_chunks_rich.json (8,093 maddes)
57a84f9  Stage 3     review remediation — data safety + AP-prep + search
3ba1653  Stage 4     test infra + CI + dev tooling
05236be  Stage 5     hygiene + outward docs + PHASE0_CLOSEOUT
89d4b98  Stage 3 ek  el_alam Track B mint deferred past temporal-skip
<close>  Stage 6     this close state + hafta9-close tag
```

Linear chain. No merges into the branch. No reverts.

## Schemas changed

| Schema | Change | Commit |
|---|---|---|
| all 11 `*.schema.json` | `$id`/`$ref` unified at v0.3.0 (38 URI rewrites; bytes otherwise identical) | `89cfd79` |
| `dynasty.schema.json` | trailing newline added (cosmetic; `$id` unchanged → no set bump) | `05236be` |
| `ui_contract/entity_page.meta.schema.json` | allow `$schema` key (6/6 recipes now validate) | `57a84f9` |

No `data/canonical/*` record was mutated by any schema change (v0.3.0 is a
schemas-only rename; the coherence + newline invariants are test-pinned).

## Adapters / registry

| Item | Change | Commit |
|---|---|---|
| `dia-tdv-scrape` | new source-producing adapter (scrape.py + parse.py; NOT run_adapter) | 2b-2e |
| `openiti` → `openiti-works` | registry id fixed to match manifest | `05236be` |
| `science-works` | missing registry entry added | `05236be` |
| registry header | corrected (no `run_all_adapters.py`; match is by CLI `--id`) | `05236be` |

## Tests

`pytest tests/integration/` **101 → 147 passed** / 2 skipped / 3 xfailed
(~21 s; `make test-fast` ~9 s). `run_schema_tests.py` 15/15.
`full_reindex --dry-run` **46,702/46,702, 0 fail** (was exit 1 on 768 records).
New suites: dia_tdv_scrape parse/pilot, work_canonicalize_lib, search_ui_contract,
dia_chunks_rich, truncate_sentence_boundary, schema_fixtures; b2 un-xfailed as a
PID-drift guard; g3 skip→xfail (removing dead coverage). No threshold was
loosened; skip→xfail conversions increase visibility.

## Data outcomes

| Metric | Value | Note |
|---|---:|---|
| canonical records | 46,702 | unchanged (AP not run) |
| `dia_chunks_rich.json` | 8,093 maddes | gitignored source; cilt/sayfa 99.94 %, title_ar 66.9 %, 1,423 authors |
| work-PID state | repaired | h9_001: counter/index/disk coherent at 9,331; `iac:work-00009331` now indexed |
| net new PIDs minted | **0** | AO is source-side; remediation is forward-only + one state repair |

## Known-issues delta vs H8

- **PE-2** (schema `$id` coherence): RESOLVED Stage 1.
- **AO** (TDV scraper): RESOLVED Stages 2a-2e.
- **NEW, deferred to H10 (repair runs, PHASE0_CLOSEOUT §2):** el_alam re-run
  (20 lost Ziriklī persons, fix landed forward-only); phantom-PID audit
  (dia + el_alam mint-before-skip, fixed forward; a background task is auditing
  the existing entries); 9,330 works' generic provenance pipeline_name.
- **AP scope clarified (see below + PHASE0_CLOSEOUT §1)** — AO unblocked the
  (c) locator, but per-work (a)/(b) richness remains bounded.
- **AN** (Cat B fuzzy match): still open, H10+.
- The sole hard external blocker remains **ADR-014 §Koşul** (İSAM written-
  permission document reference) before any derived-data publication.

## AP entry point — corrected scope (important)

The H10 AP work (`dia_works` rich-mint) is unblocked but is **bounded-mint, not
bulk-mint** — a boundary made explicit at close so H10 does not drift:

- The Hassâf template (`iac:work-00009331`) needs (a) ≥2-language prefLabel,
  (b) description, (c) cilt+sayfa locator per ADR-009.
- **AO delivered (c)** for every scholar madde (the print locator).
- **(a)/(b) per individual work are still NOT available at scale:**
  `dia_chunks_rich.json` is madde-level (the scholar's Arabic name + locator),
  not per-title-in-bibliography. `dia_works_h5_audit.json` (44,611 titles)
  breaks down as **42,449 `no_external_match_dia_only`** (ADR-009's forbidden
  sig-mint zone), 1,457 `low_likely_misattribution`, only **37
  `moderate_validated_one_source`**.
- Therefore AP's rich-mintable set is roughly the **externally-validated
  subset** (OpenITI/science-works matches, ~1,519 `matched_in_either` before
  quality filtering), where an Arabic title + description can be sourced. The
  ~42K DiA-only titles stay UNMINTED per ADR-009 — this is a feature (no
  unverified citations), not a gap.
- Decisions Ali must make at AP kickoff (framed with numbers in
  `docs/h10/HAFTA10_AP_KICKOFF.md`): the ADR-009 (a) threshold for the 2,681
  Arabic-title-less maddes, and TDV-contributor namespace modeling (Q3/Q4).

## Rollback

Each H9 stage is an independent `git revert`. h9_001's state repair does not
revert with git (gitignored state); undoing it means resetting
`pid_counter.work` to 9,330 and deleting the hassaf index key — which re-arms
the PID-collision bomb, so it should not be undone. No canonical record was
touched across H9.

---

**End of H9 close state.** Eleven commits, one scraper + 8,093-madde rich
source, one 56-agent review with 16+6 verified fixes, suite 101→147, CI
resurrected, zero reverts, zero data drift.
