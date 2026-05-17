# H8 Known Issues — for H9+ backlog

> H8'de keşfedilen ama H8 scope'u dışındaki sorunlar veya bilinçli
> deferral'lar.

---

## PE-2: Schema $id coherence drift across the 10-file schema set

**Severity**: Low (cosmetic — does not affect validation behavior)
**Discovered**: H8 Stage 1, while planning PE-1 remediation
**Affected**: All 10 files in `schemas/`

### Current state

| File | `$id` version tag |
|---|---|
| `schemas/_common/provenance.schema.json` | v0.1.0 (semantically v0.2.1 after PE-1 patch) |
| `schemas/_common/authority_xref.schema.json` | v0.1.0 |
| `schemas/_common/coords.schema.json` | v0.1.0 |
| `schemas/_common/multilingual_text.schema.json` | v0.1.0 |
| `schemas/_common/temporal.schema.json` | v0.1.0 |
| `schemas/person.schema.json` | v0.1.0 |
| `schemas/place.schema.json` | v0.1.0 |
| `schemas/dynasty.schema.json` | v0.1.0 |
| `schemas/manuscript.schema.json` | v0.1.0 |
| `schemas/event.schema.json` | v0.1.0 |
| `schemas/work.schema.json` | **v0.2.0** (bumped at H6 Stream 4, commit f5f502f) |

All entity schemas' `$ref` strings point to
`https://w3id.org/islamicatlas/schemas/v0.1.0/_common/*.schema.json` —
including `work.schema.json` itself, which is `v0.2.0` but refs
`v0.1.0/_common/provenance.schema.json`.

### Why this matters

- Documentation ambiguity: external consumers reading `$id` URLs cannot
  tell from the URL alone whether they have the latest semantic schema.
- Web-of-data citation: if the project later publishes the schemas to
  w3id.org with content-negotiation, version coordination becomes a
  blocker.
- Audit trail: the H6→H8 history is recoverable from git but not from
  the schemas themselves.

### Why this does NOT matter operationally

- `referencing.Registry` keys schemas by their actual `$id` strings;
  as long as every `$ref` matches an `$id` somewhere in the registry,
  resolution works. The current state is **internally consistent** —
  it just has stale version tags.
- All integration tests pass (after PE-1 fix).

### Remediation options (H9+)

**Option PE-2-A: Big-bang to v1.0.0**
Bump every file's `$id` to `https://w3id.org/islamicatlas/schemas/v1.0.0/...`
and rewrite every `$ref` accordingly. Atomic 10-file commit. Establishes
the schema set's first "stable" version. ADR-011 codifies the
versioning policy (e.g., "every additive enum revision bumps minor;
every required-field addition bumps major; every commit that bumps any
schema `$id` must update all `$ref`s in the same commit").

**Option PE-2-B: Bump to v0.3.0 (next minor)**
Same mechanism, lower version tag. Signals "still pre-stable, but
internally coherent now."

**Option PE-2-C: Leave as-is, formalize via "schema set semver"**
Maintain a single `schemas/VERSION` file or `CHANGELOG.md` entry that
declares the schema-set semantic version, accept the per-file `$id`
drift as cosmetic. Lower-effort, but does not fix documentation
ambiguity.

**Recommendation**: PE-2-A or PE-2-B at the H8 close commit, OR as
a standalone H9 Stage 1. Effort: 1-2 hours including ADR-011, the
10-file atomic edit, and a `pipelines/migrations/h9_001_schema_id_bump.py`
verification script.

### H9 acceptance criterion (proposed)

`AM: All 10 schema files share a single $id version tag; all $refs
match the new tag; full integration suite green; ADR-011 written.`

---

## H8 Close — final state of known issues

**As of H8 close commit** *(see HAFTA8_CLOSE_STATE.md for the SHA)*,
H8 introduced one new logged-and-deferred issue (PE-2 above), and
discovered-and-closed one issue within H8 itself (the Stage 5
`truncate_at_sentence_boundary` maxLength overflow, postmortem
preserved in `docs/h8/HAFTA8_STAGE_5_BULK.md` §"Postmortem"). The
Stage 5 bug is **not** a residual H9 issue; it is documented here for
audit trail only.

### Soft TODOs (process improvement, not formal issues)

- **Property-based test for `truncate_at_sentence_boundary`**: A
  Hypothesis-style randomized test asserting
  `len(truncate(text, max_len)) <= max_len` for varying inputs would
  guard against future regressions of the same class of bug. The
  existing `test_ag7_description_within_50k` covers the invariant on
  the actual canonical population (3,309 records), but a property
  test would catch it at lib level before any record is written.
  Effort: ~30 min. Suggested target: H9 Stage 1 (alongside PE-2
  housekeeping) or as opportunistic during any later refactor of
  `pipelines/_lib/dia_enrichment_lib.py`.
- **Hybrid-sampling pilot template**: Stage 4's alphabetical sort
  systematically underrepresented the overflow tail (~5% of population
  per Stage 2b). Future pilot fixtures (`run_adapter.py --limit N
  --sample STRATEGY`) could benefit from a `STRATEGY` parameter
  supporting `alphabetical | random | stratified_by_<attribute>`.
  Not blocking; not yet specced. Suggested target: H10+ as part of
  any pilot-template tooling sweep.

### Issue ledger at H8 close

| Issue | Severity | Status | Target |
|---|---|---|---|
| PE-1 (2,262 records' source_type not in enum) | High → CLOSED | Resolved at Stage 1, commit `4e6176a` | n/a |
| PE-2 (schema $id coherence across 10 files) | Low (cosmetic) | OPEN | H9 Stage 1 (recommended) |
| Stage 5 truncate maxLength overflow | High → CLOSED | Resolved at Stage 5, commit `ec9ba52` (patch in `apply_h8_stage5_truncate_fix.py`) | n/a — postmortem only |

**Net: PE-2 is the sole open H8-originated issue carried into H9.**

<!-- Future H8-discovered issues here -->
