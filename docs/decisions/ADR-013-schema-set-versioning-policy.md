# ADR-013: Schema-set semantic versioning — single $id tag, atomic bumps

**Status:** Accepted
**Date:** 2026-06-11
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-002 (registry-based $ref resolution), ADR-010 (PE-2
deferral rationale), ADR-012 (description maxLength 50K), H6 Stream 4
schema migration (commit f5f502f), H8 close (commit a41642d, tag
hafta8-close), PE-2 (docs/h8/H8_KNOWN_ISSUES.md)

---

## Context

The schema set consists of **11 files**: six entity schemas (`dynasty`,
`event`, `manuscript`, `person`, `place`, `work`) and five shared
component schemas under `schemas/_common/` (`authority_xref`, `coords`,
`multilingual_text`, `provenance`, `temporal`). (The PE-2 entry's title
says "10-file schema set"; its own table lists 11 rows. The "10" counted
the files then sitting at v0.1.0 — `work.schema.json`, already at
v0.2.0, was the eleventh.)

Version drift accumulated in three steps:

1. **H6 Stream 4** (commit f5f502f) bumped `work.schema.json` `$id` to
   `v0.2.0` but left the other ten files — including the `_common`
   schemas that `work` itself `$ref`s — at `v0.1.0`. From that commit
   on, a v0.2.0 schema referenced v0.1.0 components.
2. **H8 migration h8_001** (PE-1 remediation, ADR-010) extended the
   `source_type` enum in `_common/provenance.schema.json` — a
   behavioral change — under an unchanged `v0.1.0` `$id`.
3. **H8 migration h8_002** (ADR-012) raised `description.<lang>`
   maxLength from 5,000 to 50,000 in
   `_common/multilingual_text.schema.json` — likewise behavioral,
   likewise under a frozen `v0.1.0` `$id`.

The result: the URI `…/v0.1.0/_common/provenance.schema.json` no longer
denotes what it denoted at H1. The drift is **cosmetic with respect to
validation** — ADR-002's resolution mechanism builds a
`referencing.Registry` by walking `schemas/` on disk and keying each
schema by whatever `$id` it carries, so `$ref`s resolve regardless of
whether the version tags are truthful. It is **not** cosmetic with
respect to documentation, reproducibility claims, or the planned
w3id.org URI publication (Faz 0.5), all of which take the `$id` at its
word.

A repo-wide audit at `a41642d` (recorded in
`docs/h9/HAFTA9_STAGE_1_PE2_FIX.md`) found **38 occurrences** of the
versioned URI prefix, all inside `schemas/`: 11 `$id` declarations and
27 `$ref` targets. No pipeline code, adapter manifest, test, fixture,
or migration embeds a versioned schema URI, and no canonicalize library
stamps one into records — so a `$id` bump carries **no data-migration
obligation** in the current architecture.

## Decision

The schema set is versioned **as a set**, not per file:

- **R1 — Single tag.** All 11 `$id` values carry the same version tag
  at every commit. Per-file divergence is outlawed.
- **R2 — Atomic bumps.** Any commit that changes the validation
  behavior of *any* schema bumps the set tag and rewrites all 11 `$id`
  values **and** all internal `$ref` URIs in that same commit.
- **R3 — Increment semantics.** Pre-1.0: any behavioral change
  (additive or breaking) bumps **minor**; editorial-only changes
  (`description`, `$comment`, examples) bump **patch**. From v1.0.0 on:
  standard semver — breaking bumps major, additive bumps minor,
  editorial bumps patch.
- **R4 — Test-pinned enforcement.** 
  `tests/integration/test_h9_schema_set_coherence.py` pins the expected
  tag in the `EXPECTED_SET_VERSION` constant. A bump that forgets any
  file, any `$ref`, or the pinned constant turns the suite red. Updating
  the constant in the bump commit is the deliberate, visible act of
  versioning.
- **R5 — Data-coupling guard.** R2's "schemas only" blast radius rests
  on the audited fact that canonical records do not embed schema URIs.
  If a future change writes `$schema`/`$id` URIs into records, bumps
  acquire a data-migration obligation and this ADR must be revisited.

**This commit applies the first set-level bump: v0.1.0 / v0.2.0 →
v0.3.0.** Rationale for the number: the set's *content* has already
moved twice past the v0.2.0 mark (h8_001 ≈ v0.2.1, h8_002 ≈ v0.2.2 in
semantic terms), and the unification itself rewrites every file —
the next minor, v0.3.0, is the smallest tag that is strictly newer than
every version any file has truthfully or untruthfully claimed.

## Alternatives Considered

### Alternative A: Big-bang to v1.0.0 (PE-2-A)
- **Pros:** One move establishes the "stable" tag; never bump twice.
- **Cons:** v1.0.0 is a stability promise. `manuscript` and `event` are
  forward-declared skeletons; AP (dia_works rich-mint, H10+) is
  expected to touch `work.schema.json`; the Faz 0.5 roadmap already
  schedules "Schema set v1.0.0 stable release" as its own milestone
  *after* AP. Claiming stability now would be false.
- **Why rejected:** v1.0.0 should be earned at Faz 0.5, not spent on a
  coherence fix.

### Alternative B: Per-file independent semver
- **Pros:** Smaller diffs; a touched file bumps alone.
- **Cons:** Independence is illusory under ADR-002's coupling — bumping
  a `_common` schema's `$id` forces a `$ref` rewrite in every consumer
  anyway, which is most of the set. Eleven version counters to reason
  about; "which combination is deployed" becomes a question.
- **Why rejected:** All cost of coordination, none of the benefit; H6
  proved the failure mode by creating PE-2.

### Alternative C: VERSION sidecar file, leave $ids frozen (PE-2-C)
- **Pros:** Two-line change.
- **Cons:** The `$id` keeps lying; w3id publication would mint URIs
  whose version segment is false; documentation ambiguity — the thing
  PE-2 actually complains about — survives.
- **Why rejected:** Treats the symptom's paperwork, not the symptom.

### Alternative D: Strip versions from $id URIs entirely
- **Pros:** Nothing to drift.
- **Cons:** Breaks the URI shape established at H1 (ADR-001/002) and
  the w3id publishing plan built on it; versioned URIs are the academic
  citation story ("validated against schemas v0.3.0").
- **Why rejected:** Largest blast radius for the least honest payoff.

## Consequences

### Positive
- Every `$id` is truthful; `$ref` graph and `$id` set are mutually
  consistent and machine-checked on every test run.
- Clean ground for AO/AP: the next schema-touching work starts from a
  coherent, policy-governed set.
- The road to v1.0.0 is now a defined act (Faz 0.5, post-AP) instead of
  an accident.

### Negative / Tradeoffs
- Any behavioral schema change now rewrites 11 files — noisier diffs.
  Accepted: the rewrite is mechanical, and R4 makes forgetting it
  impossible rather than easy.
- `EXPECTED_SET_VERSION` must be co-updated on every bump. Accepted:
  that friction *is* the enforcement (R4).

### Neutral / Future revision triggers
- Historical artifacts (migration journals, H6-H8 docs, provenance
  `release` labels like `v0.1.0-phase0`) retain old version strings.
  Correct: they record what was true when written; history is not
  rewritten. The `release` label namespace (pipeline releases) is
  distinct from the schema-set tag and is untouched by this ADR.
- Bare-version mentions inside `$comment`/`description` prose (e.g.
  provenance's "not by JSON Schema in v0.1.0") are historical
  references, intentionally retained.
- w3id.org PR (Faz 0.5) will publish the then-current tag's paths.

## References

- PE-2 entry: `docs/h8/H8_KNOWN_ISSUES.md` §"PE-2" (options A/B/C
  enumerated there; this ADR selects B's tag with A's policy ambition)
- Resolution mechanics: `tests/run_schema_tests.py::build_registry`,
  `pipelines/migrations/h6_001_schema_v0_2_0.py::_load_schema`
- Drift origin: `pipelines/migrations/h6_001_schema_v0_2_0.py`,
  `h8_001_schema_v0_2_1_digital_corpus.py`,
  `h8_002_description_maxlength_50k.py`
- Enforcement: `tests/integration/test_h9_schema_set_coherence.py`

---

**Revision history:**
- 2026-06-11: First version, accepted at H9 Stage 1 (Ali Çetinkaya;
  drafted with Claude).
