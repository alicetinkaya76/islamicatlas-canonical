# NEXT SESSION PROMPT — Hafta 4: Person Namespace Seed

**Context for Claude:** This is the kickoff for Hafta 4 of the islamicatlas-canonical Phase 0 build. Hafta 2 (Bosworth dynasty pilot, 186 NIDs) and Hafta 3 (place namespace via Yâqūt + Muqaddasī + Le Strange, 15,239 records) are complete. The next milestone is the **person namespace seed** — building `iac:person-*` PIDs from the available biographical sources.

---

## Tools and state

The user works on a Mac at `/Volumes/LaCie/islamicatlas_canonical/`. The repo's main branch has commits through Hafta 3. Sandbox builds happen at `/home/claude/work/islamicatlas-canonical/` (regenerable from the user's repo).

**Source data available on user's Mac (`data/sources/`):**

| Source | Volume | Status |
|--------|--------|--------|
| `dia/dia_chunks.json` | 19,742 biography chunks (70 MB, gitignored) | **PRIMARY input for Hafta 4** |
| `dia/dia_lite.json` | 2.5 MB lite biography metadata | Companion |
| `dia/dia_relations.json` | 466 KB relations | Companion |
| `el-alam/alam_lite.json` | 4.1 MB El-Aʿlām biography metadata | Cross-source corroboration |
| `el-alam/alam_gazetteer.json` | 285 places with biography counts | Hafta 3 already used cross-ref |
| `science-layer/science_layer.json` (NEW, in user's recent zip) | 182 scholars + 37 institutions | Compact seed for major figures |
| `ei1/ei1_lite.json` | 2.9 MB Encyclopaedia of Islam (1st ed.) lite | Cross-source corroboration |

**Sidecars from Hafta 2 and Hafta 3 carrying person-related deferrals:**

| Sidecar | Entries | Use in Hafta 4 |
|---------|---------|----------------|
| `data/_state/yaqut_persons_pending.json` | 606 places × 8,692 person attestations | Resolve person mentions in Yâqūt to person PIDs once seeded. |
| `data/canonical/dynasty/*.rulers[]` (inline) | 830 rulers across 186 Bosworth dynasties | Promote to `iac:person-*` PIDs. |
| (new) `bosworth_rulers_pending.json` | TBD | Will be created by a Hafta 4 promotion adapter. |

---

## Hafta 4 deliverable scope

**Primary goal:** Seed `iac:person-*` namespace from DİA chunks + science_layer + Bosworth rulers, with cross-attestation from El-Aʿlām and EI1.

**Adapter rough plan:**

1. **`pipelines/adapters/dia/`** — DİA biography adapter
   - Extract: read `dia_chunks.json` (19,742 chunks). Each chunk has `id`, `s` (slug), `n` (name), `d` (death dates parenthetical), `t` (text). Group chunks by slug to assemble per-person biographies.
   - Canonicalize: target `iac:person-*` namespace. Build labels from `n`; parse death/birth dates from `d`; fill description from concatenated `t` chunks (truncated to 5000 chars).
   - Expected volume: ~12,000-14,000 person records (each slug = one person; some slugs are non-biographical like place entries — needs filtering by chunk count + name pattern).
   - Recon: live Wikidata reconciliation against type Q5 (human).

2. **`pipelines/adapters/science-layer/`** — High-confidence seed for ~182 major scholars
   - These are curated entries (Khwarizmi, Ibn Sina, al-Biruni, etc.) with full trilingual names + dates + birth/active places.
   - Use as resolver Tier-1 seed: when DİA adapter encounters "el-Hârizmî", check science-layer for canonical name + QID.
   - Run BEFORE the DİA adapter so DİA's resolver can find existing PIDs.

3. **`pipelines/adapters/bosworth-rulers-fixup/`** — Promotion of inline rulers
   - For each Bosworth dynasty's `rulers[]` array, mint a person PID per ruler.
   - Replace the inline `rulers[]` array with `had_ruler[]` array of PID references (schema field already exists).
   - Cross-resolve to DİA via name+death-date matching where possible.

4. **Cross-source resolver work:** the resolver currently treats persons as a stub (Hafta 2 and Hafta 3 didn't use it for person merging). Tier-1 (Wikidata QID), Tier-2 (DİA slug match), Tier-3 (name + death date proximity ±2 years) need real implementations.

5. **Person namespace integrity pass:** `pipelines/integrity/person_integrity.py`
   - Resolve `notable_persons[]` strings in Yâqūt records to person PIDs (sidecar from Hafta 3).
   - Resolve dynasty.rulers references.
   - Bidirectional `worked_at[]` ↔ `place.had_active_scholars[]` if schema supports it.

---

## Working style reminders

- "sen seç" mode is active. Make architectural decisions (modular vs monolithic, eager vs lazy resolver, recon volume strategy) and propose them with brief justification.
- Communication: Turkish for high-level discussion; English for code, technical notes, schemas.
- Modular session-based working: each Hafta delivery is a self-contained zip + handoff prompt.
- Doçentlik clock: every Hafta's output should also feed publication strategy. Hafta 3 produced a place layer that's globally unique in scope; Hafta 4 person layer + cross-attestation against DİA/EI1 will be similarly distinctive.

## Pre-flight check at session start

1. Read `HAFTA3_DELIVERABLE.md` for full state of place namespace.
2. Verify `data/canonical/dynasty/` has 186 records, `data/canonical/place/` has ~15,239 records.
3. Check `data/sources/dia/dia_chunks.json` exists locally on Mac (gitignored, 70 MB).
4. Read `schemas/person.schema.json` to confirm field shape.
5. Inspect `data/canonical/dynasty/iac_dynasty_*.json` `rulers[]` field — what's the inline ruler shape?

## Known unknowns to investigate first

- DİA chunk grouping logic: how to detect the boundary between biographical entry and place/topic entry? (Hint: look at chunk count per slug + first-chunk text patterns like "(ö. NN/NNNN)" death-date markers.)
- science_layer.json: are dates CE or AH? Are names complete (full_name vs name)?
- Bosworth rulers: how many distinct persons across 830 entries? (Same person can rule sequential dynasties.)
- Wikidata recon volume: 13,000 person records × ~1.7 s = 6 hours. Tier the recon: only entries with DİA URL + science_layer presence + Bosworth ruler appearance get live API; rest are seed-only.

---

## Acceptance criteria (target for Hafta 4)

(K) Person namespace has ≥10,000 records, all schema-valid.
(L) Bosworth's 830 rulers fully promoted to person PIDs (no inline rulers array remaining).
(M) Science-layer's 182 scholars all canonicalized with high-confidence Wikidata QIDs (≥150 reconciled).
(N) DİA biography coverage: ≥12,000 person records derived from dia_chunks.
(O) Yâqūt notable_persons sidecar has ≥80% of mentions resolved to person PIDs.
(P) Integration test suite: ≥20 acceptance tests, all green in sandbox.

---

## Final note for handoff

The Hafta 3 place namespace is now the spine of the canonical store. Yâqūt + Muqaddasī + Le Strange together represent the most comprehensive computationally-tractable Islamic gazetteer ever assembled. Hafta 4 turns this into a **person-place attestation graph**: every person in DİA gets linked to every place in Yâqūt where they're mentioned. This becomes the foundation for the methods paper "Cross-attesting medieval Islamic biographical and geographical records via algorithmic reconciliation" (Q1 target: International Journal of Digital Humanities, ESwA, or similar).

Good luck.
