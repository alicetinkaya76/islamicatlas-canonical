# Next Session Prompt — Hafta 3: Yâqūt + Le Strange (place namespace seeding)

## Status entering this session

**Hafta 2 (Bosworth ETL Pilot) — COMPLETE.** All acceptance criteria green:

- 186/186 dynasty records canonicalized in `data/canonical/dynasty/`
- All schema-valid against `dynasty.schema.json`
- 51 selef edges resolved into `predecessor[]`/`successor[]` (bidirectional invariant holds)
- 830 ruler records embedded
- 26 records carry verified Wikidata `authority_xref` (live API will raise this to ~70%+ on a networked run)
- Lookup index built (`data/_index/lookup.sqlite`)
- Search projector dry-run clean: 186/186 docs project without error
- Regression suite still green: 15/15 schema, 3/3 projector, 5/5 resolver

**Carried forward to Hafta 3:**

- `data/_state/bosworth_capital_pending.json` — 186 capital + region entries to be backfilled into `had_capital[]` / `territory[]` once `iac:place-*` PIDs exist.
- `pipelines/_lib/pid_minter.py` and `pipelines/_lib/wikidata_reconcile.py` are reusable for new adapters as-is.
- `pipelines/integrity/check_all.py` is the second-pass pattern; extend it for new cross-record edges as new namespaces land.
- Two upstream data-quality issues flagged in `HAFTA2_DELIVERABLE.md` for the content team (NID-91 Seljuqs misclassified as Atabeglik in CSV; relations row 94→130 mislabelled).

## Goal of Hafta 3

Seed the **`iac:place-*` namespace** from two sources — Yâqūt al-Hamawī's *Mu'jam al-Buldān* (the canonical Islamic gazetteer, ~12,000 entries pre-1228 CE) and Le Strange's *The Lands of the Eastern Caliphate* (434 administrative-region records, already prepared as CSV from v7.7 work). Then run a backfill pass on the dynasty store to consume `bosworth_capital_pending.json`.

## Default decisions for "sen seç" mode

1. **Yâqūt adapter at `pipelines/adapters/yaqut/`** with same structure as `bosworth/`. Source is the `data/sources/yaqut/mujam_albuldan.csv` bundle the content team prepared (verify before starting). Same CSV-driven extract; same canonicalization → resolver → reconciler pipeline as Bosworth.
2. **Le Strange adapter at `pipelines/adapters/le_strange/`**. Source: `data/sources/le_strange/lands_eastern_caliphate.csv` (434 records, 34 provinces). Targets `iac:place-*` (cities) and a new `iac:region-*` (administrative provinces) namespace if the schema supports it; otherwise tag region records with `@type=['iac:Place','iac:AdministrativeRegion']`.
3. **Reconciliation mode**: `auto` (live API + offline seed fallback). Seed file should cover the major iqlim and the ~50 most-cited cities (Mecca/Q5806, Medina/Q35525, Damascus/Q3766, Baghdad/Q1530, Cairo/Q85, Aleppo/Q41183 [already verified in fixture], Cordoba/Q5818, Konya/Q83036, Bukhara/Q5687, Samarkand/Q5530, etc.).
4. **Backfill pass after both adapters complete**: extend `pipelines/integrity/check_all.py` (or add a sibling `backfill_capitals.py`) that reads `bosworth_capital_pending.json`, fuzzy-matches `capital_name` against place labels in the lookup index (with `region_primary` as a tiebreaker), and patches `had_capital[]` into the corresponding dynasty file. Keep the bidirectional invariant: `iac:place-X.was_capital_of` / `iac:dynasty-Y.had_capital[].place=iac:place-X` must agree.
5. **Cross-reference dynasty.rulers ↔ Yâqūt's biographical mentions** is *deferred to Hafta 4* (DİA adapter introduces person namespace); Hafta 3 stays focused on place + region.

## Acceptance criteria

(Mirror the Hafta 2 checklist verbatim with adjustments.)

- [ ] All Yâqūt records canonicalize to schema-valid `iac:place-*` records
- [ ] Le Strange records canonicalize as place + region records
- [ ] Reconciliation ≥70% on networked run (Yâqūt's well-known cities have abundant Wikidata coverage)
- [ ] Re-running adapter is idempotent (PIDs stable)
- [ ] Backfill pass populates `had_capital[]` for every dynasty whose `bosworth_capital_pending.json` entry resolves to a known place; remaining unresolved capitals get a warning log, not a failure
- [ ] Bidirectional invariant on dynasty.had_capital ↔ place.was_capital_of holds
- [ ] All regression tests still green (schema, projector, resolver)
- [ ] Integration test `tests/integration/test_yaqut_pilot.py` (mirror the bosworth pilot test)

## Known risks / things to watch

- **Yâqūt's place names overlap with Bosworth dynasty names** for some cases (Baghdad as a city + as a topographic capital reference; Konya vs. the Saljuqs of Rūm; etc.). The resolver will need its Tier-1 logic (Wikidata QID match) to disambiguate, with `entity_type` namespacing protecting against cross-namespace collision.
- **Coordinates from Yâqūt** are approximate (medieval geographer); coordinates from Le Strange are modern (early 20th-c. orientalist). The `coords` schema field has uncertainty markers — use them.
- **Iqlim labels may need a fixture** at `data/iqlim_labels.json`. The projector references this file; check the existing `search/projector.py` for the expected format.
- **Don't replicate the Hanedan/Beylik catch-all mistake** — if Yâqūt's CSV has an unreliable category column, leave it unmapped rather than force-fit.

## Repo layout reminders

```
pipelines/
  _lib/
    pid_minter.py             reusable
    wikidata_reconcile.py     reusable
    entity_resolver.py        reusable (ADR-008)
  adapters/
    bosworth/                 reference implementation
    yaqut/                    NEW — mirror bosworth/ structure
    le_strange/               NEW — mirror bosworth/ structure
    registry.yaml             flip new adapters to enabled: true
  integrity/
    check_all.py              extend with backfill_capitals logic
    backfill_capitals.py      OR add as a sibling file
  search/
    full_reindex.py           --dry-run validates new namespace projection
data/
  canonical/
    dynasty/                  186 files (Hafta 2)
    place/                    NEW (this session)
    region/                   NEW (this session) — if separate namespace warranted
  _state/
    pid_counter.json          will tick: dynasty:186, place:N, region:M
    pid_index.json            additive
    bosworth_capital_pending.json    consumed by backfill pass
  sources/
    yaqut/mujam_albuldan.csv          (verify presence)
    le_strange/lands_eastern_caliphate.csv   (verify presence)
schemas/
  place.schema.json           already exists (used by Aleppo fixture)
  region.schema.json          ?  may need to be added if separate namespace
```

## Working style ("sen seç" mode active)

- Take judgment calls and document them in commit-style decision records
- Keep the modular pipeline pattern from Hafta 2 (extract → canonicalize → resolve → integrity)
- Document upstream data-quality issues (do not silently work around them)
- End the session with a `HAFTA3_DELIVERABLE.md` mirroring the Hafta 2 format
