# NEXT SESSION PROMPT — Hafta 5: Work Namespace Seed (Önerilen Yön A)

**Context for Claude:** This is the kickoff for Hafta 5 of the islamicatlas-canonical Phase 0 build. Hafta 2 (Bosworth dynasty pilot, 186 NIDs), Hafta 3 (place namespace via Yâqūt + Muqaddasī + Le Strange, 15,239 records), and Hafta 4 (person namespace via DİA + science_layer + Bosworth rulers + El-Aʿlām, ~20,895 records) are complete. The next milestone is the **work namespace seed** — building `iac:work-*` PIDs from biographical mentions of works.

---

## Tools and state at start of Hafta 5

**Mac repo state (after `git push` of Hafta 4 commit):**
- `data/canonical/dynasty/`: 186 records (with had_ruler[] populated)
- `data/canonical/place/`: 15,239 records
- `data/canonical/person/`: ~20,895 records
- `data/_state/` carries 20+ sidecars from Haftas 2-4

**Source data already on Mac (gitignored or in data/sources/):**

| Source | Volume | Notes |
|--------|--------|-------|
| `dia/dia_chunks.json` (gitignored) | 19,742 chunks | Re-parse for `key_works` mentions in person bios |
| `dia/dia_lite.json` | 8,528 entries | `wm` field = work_count per person (max 7) |
| `science-layer/science_layer.json` | 182 scholars | `key_works` field is canonical seed |
| `science-layer/discoveries[]` (in same file) | 129 entries | Each discovery is a work-like entity |
| `el-alam/alam_lite.json` | 13,940 entries | Bio descriptions mention works |
| `openiti/openiti_uri_index.json` (NEW for H5) | TBD | If user has OpenITI URIs available |
| `kashf-al-zunun/kashf.json` (NEW, optional) | ~14,500 entries | Hâcî Halîfe's bibliographical encyclopedia |

**Decision to confirm at session start (Y5.1):**
- Y5.1: Sources for work namespace —
  (a) Science layer discoveries + science layer key_works + DİA wm field hints (small, curated, ~500-700 works)
  (b) (a) + OpenITI URI index (if user has the file) (~3,000-5,000 works)
  (c) (a) + Kashf al-Zunûn (Hâcî Halîfe) (very large; ~14,500 work entries with author crossrefs)
  (d) All three — most ambitious; ~20,000 works

---

## Hafta 5 deliverable scope

**Primary goal:** Seed `iac:work-*` namespace with bidirectional `work.authors[] ↔ person.authored_works[]` invariant (Phase 0.2 hard rule from person.schema $comment).

**Adapter rough plan:**

1. **`pipelines/adapters/science_works/`** — Science layer key_works + discoveries adapter
   - Input: `data/sources/science_layer.json` (already in Hafta 4 sandbox)
   - Each scholar's `key_works` array → mint work PIDs
   - Each `discoveries[]` entry → mint work PID with `discovered_by` linkage
   - Tight integration: scholar's PID is already in person namespace, so `work.authors[] = [<scholar_pid>]` is direct

2. **`pipelines/adapters/dia_works/`** — DİA biography re-parse for work titles
   - Re-load `dia_chunks.json` (Hafta 4'ün cache'i kalkmış olabilir; tekrar 70 MB load)
   - Title-detection patterns:
     - Italic patterns in DİA (often unmarked in our text-only chunks; will need NER-light heuristics)
     - "telif etti", "yazdı", "kaleme aldı" trigger words
     - Quoted titles (Turkish: `"Title"`, Arabic: `«Title»`)
   - Each detected work title → mint work PID with current DİA-derived person as author

3. **`pipelines/adapters/openiti/`** (Y5.1 (b)/(d)) — OpenITI URI seed
   - If user has OpenITI URI corpus → straight import (each `XXXXAuthorYYYYWork` → work PID)
   - Resolver Tier-1: OpenITI URI in authority_xref (already in v0.1.0 enum)

4. **`pipelines/adapters/kashf_al_zunun/`** (Y5.1 (c)/(d)) — Hâcî Halîfe bibliography
   - Each entry: title (Ar), author name, possible cross-refs to other works
   - Largest single source (~14,500 entries) — biggest opportunity for work coverage

5. **Work namespace integrity pass:** `pipelines/integrity/work_integrity.py`
   - Pass A: Bidirectional `work.authors[] ↔ person.authored_works[]` (P0.2 hard rule)
   - Pass B: Cross-source work merge — same Kitâbü'l-Cihâd attested by 5 authors? → SAME-AS chain via authority_xref OR title-fingerprint match
   - Pass C: `work.influenced_by[]`, `work.commentaries_on[]` if schema supports (check work.schema.json)

---

## Pre-flight check at session start

1. Read `HAFTA4_DELIVERABLE.md` and `HAFTA4_SESSION_NOTES.md` (this session's notes).
2. Verify `data/canonical/person/` has ~20,895 records.
3. Read `schemas/work.schema.json` to confirm field shape.
4. Inspect `data/sources/science_layer.json` `discoveries[]` field — what's the inline shape?
5. Check whether the user has OpenITI URI index locally.
6. Verify `dia_chunks.json` is still on Mac (gitignored, 70 MB — was deleted post-Hafta 4? Re-fetch if so).

---

## Acceptance criteria (target for Hafta 5)

(Q) Work namespace has ≥1,000 records (Y5.1 (a)) or ≥5,000 (b/c) or ≥15,000 (d), all schema-valid.
(R) Bidirectional invariant `work.authors[] ↔ person.authored_works[]` holds for ≥95% of work-author pairs.
(S) Science_layer's 182 scholars have ≥150 of them with at least one authored_works entry.
(T) Bosworth's 830 rulers — at least 200 of them get cross-linked to a work where they appear as patron (`work.patrons[]` if schema field exists).
(U) Integration test suite for work pilot: ≥18 acceptance tests, all green.

---

## Working style reminders (carried from Hafta 4 + earlier)

- "sen seç" mode is active (Hafta 4 used this — produced 25/25 green tests in single session).
- Communication: Turkish for high-level discussion; English for code, technical notes, schemas.
- Modular session-based working: each Hafta delivery is a self-contained zip + handoff prompt.
- Doçentlik clock: every Hafta's output should also feed publication strategy. Hafta 4 produced a person layer with 1,261 cross-attested DİA+Alam records — the cross-attestation methods paper hook. Hafta 5 work seed is the prerequisite for the OpenITI-Types→IPM Q1 paper that's already in the doçentlik plan.

---

## Known unknowns to investigate first

- DİA work-title detection — without HTML markup, how accurate is keyword-based extraction? Run a smoke detection on 100 random bios and have the user spot-check.
- science_layer.discoveries — is `name` always work-like? Some are concepts (e.g., "Algebra as a discipline" — that's a discipline, not a work). Need triage.
- Kashf al-Zunûn — what's the file format? CSV? JSON? OpenITI URIs? If the file isn't ready, defer Y5.1 (c).
- Bosworth rulers as patrons — does Bosworth's data have any patron-of-work signals? Check the source CSV for fields not yet utilized.

---

## Final note for handoff

The Hafta 4 person namespace, combined with the Hafta 3 place namespace, is now a 36,134-record graph (15,239 places + 20,895 persons + 186 dynasties) with active person↔dynasty bidirectional links and forward person→place links. Hafta 5 work namespace adds the **third major axis** — what people wrote, where, and to/for whom. This unlocks:

- The person→work→place chain ("Ibn Sina wrote al-Qānūn fī al-Ṭibb in Hamadan")
- The patron→work chain ("Sultan Selim II commissioned the Süleymaniye Mosque" — architecture as a "work")
- The science_layer discovery layer (129 attributed innovations) becomes navigable graph nodes
- The OpenITI corpus (which user already has integrations with) connects directly via work PIDs

This positions the Q1 methodology paper "Cross-attesting medieval Islamic biographical, geographical, and bibliographical records via algorithmic reconciliation" — the title implied in Hafta 4 expanded to its three-axis form. Submit target: International Journal of Digital Humanities or ESwA Q1 (per doçentlik plan).

Good luck.
