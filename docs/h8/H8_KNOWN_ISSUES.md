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

<!-- Future H8-discovered issues here -->
