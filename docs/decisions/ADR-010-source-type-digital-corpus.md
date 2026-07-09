# ADR-010: source_type='digital_corpus' for OpenITI Tier-4 placeholder seeds

**Status:** Accepted
**Date:** 2026-05-16
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-006 (Adapter pattern), ADR-009 (DiA rich-mint doctrine),
H4 v2 person seed (commit 6ac18b2), H6 Stream 4 schema migration
(commit f5f502f), H7 Stage 5 close (commit 8833ec0)

---

## Context

The H4 v2 person-namespace seed minted 21,946 records using
`provenance.derived_from[0].source_type == "digital_corpus"` for
~2,262 placeholder authors attested only via an OpenITI text URI
(no biographical entry mint, no fulltext attestation, no bibliographic
match against Brockelmann GAL / Sezgin GAS / DiA). At H4 time, the
common provenance schema accepted this value; the H4 acceptance suite
ran green (26/26 tests).

H6 Stream 4 (schema v0.1.0 → v0.2.0, commit f5f502f) revised the
common provenance schema enum to a narrower closed list:
`["primary_textual", "secondary_scholarly", "tertiary_reference",
"manual_editorial", "authority_file"]`. The migration journal covered
only `work.schema.json`; the 21,946 pre-existing person records were
not re-validated. The integration suite at H6 close ran only
`test_work_pilot.py`, so the violation was latent.

H7 Stage 5 ran `pytest tests/integration/` for the first time;
`test_dia_pilot.py::test_a1_all_person_records_validate` reported
2,262 schema violations (issue PE-1, see `docs/h7/H7_KNOWN_ISSUES.md`).
Sample affected PIDs: iac:person-00021298, 21299, 21300, 24359, 24706.

**Semantic of the affected records.** Each carries:
- `provenance.derived_from[0].source_id`: an OpenITI text URI (e.g.
  `openiti:0816Jahiz.BukhalaTha2`).
- `provenance.derived_from[0].source_type`: `"digital_corpus"`
  (rejected by current schema).
- `provenance.derived_from[0].extraction_method`: usually
  `"structured_json"`.
- Minimal personal-metadata: just author name (often Arabic), birth/
  death tentative, no biographical narrative.

This is a meaningful provenance category. These records do not derive
from a primary text in the way a Yâqût biographical extract does;
they do not derive from secondary scholarship (Bosworth, Le Strange);
they are not tertiary reference (DiA, EI); they are not editorial; they
are not authority-file imports. They are **placeholder authors attested
only via the OpenITI digital corpus' text URI catalog** — the canonical
store needs them as graph nodes so that openiti_works can attach to a
named author PID, but the records carry only structural skeleton.

## Decision

Add `"digital_corpus"` as a sixth enum value in
`schemas/_common/provenance.schema.json`'s
`derived_from[].source_type` enum. Update the enum description to
define the new value:

> 'digital_corpus' = OpenITI Tier-4 placeholder where author/work is
> attested via an OpenITI text URI but no full mint exists yet — see
> ADR-010.

Acceptance criterion: after the patch,
`test_dia_pilot.py::test_a1_all_person_records_validate` transitions
from FAILED to PASSED with zero record mutation.

**Scope.** Because the enum lives in the *common* provenance schema,
the new value is admissible across all six canonical entity types
(person, work, place, dynasty, manuscript, event). Today only person
records use it; future Tier-4 pipelines (e.g., placeholder mints for
unattested OpenITI works) may legitimately reuse it.

**Schema versioning.** The patch is **additive and backward-compatible**:
all records that validated before the patch continue to validate.
Per JSON-Schema semver convention (Vocabularies & Versioning, draft
2020-12 annex notes), additive enum extensions are minor revisions.
However, the file's `$id` is **NOT bumped** in this commit because:

1. Bumping `$id` of `_common/provenance.schema.json` from
   `v0.1.0/...` to `v0.2.1/...` would invalidate the `$ref`
   resolution in all 9 entity-level schemas that reference it (their
   `$ref` strings hardcode the old URL). The `referencing.Registry`
   used by the integration suite keys schemas by `$id`, so a unilateral
   bump breaks validation across the entire suite.
2. The existing schema-set already has `$id` coherence drift (H6
   Stream 4 bumped only `work.schema.json` to v0.2.0; the other 9
   schemas remain at v0.1.0). A coordinated bump policy is a separate
   architectural decision — tracked as **PE-2** in
   `docs/h8/H8_KNOWN_ISSUES.md`, to be addressed in a future commit
   that updates all `$id`s and all `$ref`s atomically.
3. Mixing additive enum surgery with a 10-file `$id` housekeeping pass
   would obscure what PE-1 actually fixed and inflate the failure
   surface of a 30-minute remediation.

The semantic schema version of the islamicatlas-canonical schema set
*is* effectively v0.2.1 after this commit; the file-level `$id`
tags lag this by design until PE-2 is resolved.

## Alternatives Considered

### Alternative A: Mass-rename to `tertiary_reference`

Patch the 2,262 records to use `source_type="tertiary_reference"`.

- **Why rejected**: Wrong semantic. `tertiary_reference` =
  encyclopaedic (DiA, EI handbooks). OpenITI is a digital text corpus,
  not a tertiary encyclopaedic reference. The records would now
  silently lie about their provenance type.

### Alternative B: Mass-rename to `primary_textual`

Closer semantic (OpenITI texts ARE primary texts in many cases) but
loses the "Tier-4 placeholder, no full mint yet" distinction. Future
re-mints of these placeholders into rich records (when OpenITI
text extraction pipelines come online) would need to flip the
source_type back, doubling the migration surface.

### Alternative C: Coordinated bump of all 9 schema $ids

Bump every `$id` to v0.2.1 and update every `$ref` accordingly in
the same commit. Architecturally cleanest but conflates two unrelated
concerns (PE-1 enum + general schema-set hygiene) and turns a 30-minute
fix into a 2-3 hour audit. Deferred as PE-2.

## Consequences

### Positive

- Zero data mutation. 2,262 records become valid without
  `record_history` append, without re-validation churn.
- `test_dia_pilot.py::test_a1` becomes green; full integration suite
  reaches 74 passed, 0 failed, 3 skipped, 3 xfailed baseline.
- The semantic of digital_corpus is now first-class in the schema
  vocabulary; future Tier-4 pipelines have an explicit anchor.

### Negative / Tradeoff

- `$id` coherence drift across the schema set (now 10 schemas at three
  different version tags — v0.1.0, v0.2.0, and the "semantically
  v0.2.1" provenance schema that still wears the v0.1.0 `$id`) is
  technical debt. PE-2 logged.
- The H6 migration practice gap (not re-validating existing records
  after enum narrowing) is documented but not structurally prevented.
  A future ADR-011 may codify the rule "every schema enum narrowing
  must run full-suite validation in the same commit".

### Neutral

- ADR-009 (rich-mint doctrine for DiA-side work records) is unaffected.
  Tier-4 placeholder authors continue to exist; rich-mint conformance
  applies to *work* records, not to author placeholders.

## References

- `docs/h7/H7_KNOWN_ISSUES.md` (PE-1 detection, options B1/B2/B3)
- `docs/h7/HAFTA7_CLOSE_STATE.md` §"Pre-existing issues discovered
  during H7"
- `docs/h8/HAFTA8_STAGE_1_PE1_FIX.md` (migration journal)
- `schemas/_common/provenance.schema.json` (the patched file)
- `pipelines/migrations/h8_001_schema_v0_2_1_digital_corpus.py`
  (re-validation script)
- ADR-006 §6.1 (adapter contract; placeholder records' provenance
  fields)
- ADR-009 (rich-mint doctrine, scope: DiA-side work records)

---

**Revision history:**

- 2026-05-16: Initial version, Ali Çetinkaya (H8 Stage 1).
