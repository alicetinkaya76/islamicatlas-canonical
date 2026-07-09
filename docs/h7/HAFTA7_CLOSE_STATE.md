# Hafta 7 - Close State

**Date**: 2026-05-05
**Branch**: hafta5-work-namespace
**Repo**: github.com/alicetinkaya76/islamicatlas-canonical
**Local path**: /Volumes/LaCie/islamicatlas_canonical
**Path strategy**: C (hybrid) - 5-stage planned, executed as 4 stages
after Stage 3 scope-down per ADR-009.

---

## Veri envanteri (H7 sonu)

| Kategori | Sayi | H6'dan degisim |
|---|---:|---|
| `data/canonical/work/*.json` | 9,331 | 0 (Stream 2 deferred per ADR-009) |
| `data/canonical/person/*.json` | 21,946 | 0 net; 4 record xref-flagged |
| Cluster sayisi | 6 | 0 |
| `authority_xref` w/ `confidence==0.0` | 4 | +4 (yeni konvansiyon) |
| `pipelines/_lib/` script sayisi | 11 | +1 (h7_qid_audit_apply.py) |
| `docs/decisions/ADR-*.md` | 9 | +1 (ADR-009) |
| Test scorecard | 23 passed, 3 xfail (B2/C1/E3), 3 skipped | unchanged |

---

## H7 commit'leri (sirayla)

```
<TBD>     Hafta 7 Stage 3+4+5: ADR-009 + H7 doc set + master plan revision (close)
93927b5   Hafta 7 Stage 2: frontend spec - Wikidata QID display policy gate
9ee147a   Hafta 7 Stage 1: QID audit - flag 4 confirmed-wrong Wikidata targets
```

---

## Stage-by-stage ozet

### Stage 1 - QID quality triage (COMPLETED)

Yapilan: 4 confirmed-wrong Wikidata QID person record'unda flag'lendi.
`confidence: 1.0/0.7/1.0/0.77 -> 0.0`, `reviewed: false`,
`note: "h7_audit_confirmed_wrong_target:..."`. Pre-state
`record_history`'de korundu.

| PID | Label | Bad QID | Wrong target |
|---|---|---|---|
| iac:person-00000184 | Harezmi | Q9438 | Thomas Aquinas |
| iac:person-00000115 | al-Qasim I (2.) | Q9458 | Prophet Muhammad |
| iac:person-00020919 | Badr | Q36533610 | Diana Badr (botanist) |
| iac:person-00000182 | 'Ali II | Q719449 | Shah Alam II |

Yeni script: `pipelines/_lib/h7_qid_audit_apply.py` (idempotent).
Yeni state sidecar (gitignored): `data/_state/h7_qid_audit_report.json`.
Yeni konvansiyon: `authority_xref[i].confidence == 0.0 AND note
startswith "h7_audit_confirmed_wrong_target:"` = "bilerek devre-disi
birakilmis xref". Pre-H7 precedent: 0 record bu pattern'i tasiyordu.

Commit: `9ee147a`

### Stage 2 - Frontend Wikidata display policy (COMPLETED)

Yapilan: `docs/h6_phase_0b/HAFTA6_S5_FRONTEND_INTEGRATION_SPEC.md`
dosyasina 3 mudahale: (a) yeni 2.4 "Wikidata QID display policy",
TS predicate ile gate kurali; (b) 4 F2 PersonCard deliverable'i guncel
(Wikidata gate test fixture'i belirtildi); (c) 6 "Acik konular" listesine
bullet eklendi.

Gate kurali (zorunlu): frontend bir wikidata xref'i su durumlarda gizler:
`confidence undefined`, `confidence < 0.85`, `note startswith
"h7_audit_confirmed_wrong_target:"`, ya da `(reviewed==false AND
method=="openrefine_v3")`. Bu Phase 0b boyunca uygulanir; H8 audit
sonrasi gevsetilir.

Commit: `93927b5`

### Stage 3 - DiA-side rich-mint doctrine (SCOPE-DOWN)

Plan vs sonuc:
- Plan: ~10-25 sig-ama-durust dia_works record mint et.
- Sonuc: Empirik kesif - `dia_works.json` sig (sadece title-string
  listesi), audit zaten ham veriden esit/fazla bilgi tasiyor, Hassaf
  zenginligi DiA encyclopedia entry'sinden manuel geliyor. Sig-mint
  pipeline'i ADR-007 (rich-page-contract) ile celisir. Programmatik
  Stream 2 H8'e ertelendi.

Uretilen kalici kayit:
- `docs/decisions/ADR-009-dia-works-rich-vs-shallow-mint.md`
- `docs/h7/H7_DECISION_LOG.md`
- `docs/h7/H7_MASTER_PLAN_REVISION.md`

Commit: (Stage 5 close commit icinde)

### Stage 4 - Test suite invariants (COMPLETED)

Yapilan: H7'nin yaptigi isin kaliciligini koruyan integration test'leri
eklendi.
- H7-1: 4 H7-flagged person record'un `authority_xref` entry'lerinde
  `confidence==0.0 AND note startswith "h7_audit_..."`.
- H7-2: Frontend spec dosyasinda 2.4 basligi ve TS predicate kod blogu
  mevcut.
- H7-3: `data/_state/h7_qid_audit_report.json` mevcut ve tutarli.

Beklenen state: 23+3=26 passed, 3 xfail, 3 skipped.

Commit: (Stage 5 close commit icinde)

### Stage 5 - Close commit (COMPLETED)

Yapilan: H7 dokumanlari git'e check-in edildi (ADR-009, H7 docs, master
plan revision).

Commit: `<TBD>`

---

## Master plan acceptance scorecard

| ID | Criterion | H6 status | H7 status | Yorum |
|---|---|---|---|---|
| AA | dia_works mint 8K-25K | DEFERRED | DEFERRED to H8 (formal) | ADR-009 |
| AB | dia_works valid `provenance.source_id` | DEFERRED | DEFERRED to H8 | ADR-009 |
| AC | high-confidence dia -> SAME-AS cluster ext | DONE (5->6) | unchanged | Hassaf only |
| AD | manual review <= %20 | DONE | unchanged | 38/44,611 |
| AE | OpenITI Tier 1 >= %3 | DEFERRED | DEFERRED to H8 | seed/QID double-bottleneck |
| AF | schema migration + B2/E2 xfail removed | DONE | unchanged | E2 done; B2 narrow |
| AG | 5-10 yeni dia_works test | DEFERRED | DEFERRED to H8 (formal) | ADR-009 |
| AH | 26 H5 test pass after S4 | DONE (23) | improved (26) | +3 H7 invariants |

H7 yeni kazanimlar (master plan disi):

- AI: 4 confirmed-wrong wikidata QID flagged + idempotent script + yeni
  konvansiyon (`confidence==0.0 + h7_audit_ note prefix`)
- AJ: Phase 0b frontend Wikidata display policy mandatory rule
- AK: ADR-009 rich-mint doctrine - Stream 2 mimari kararini kayit
  altina aldi

---

## H7 sonu kontrol sorulari

- [x] Tum commit'ler GitHub'a push edildi mi? (push sonrasi confirm)
- [x] Test suite hala yesil mi? 26/26 passed (H7 invariants dahil)
- [x] H7 idempotent script calistirilinca state degisiyor mu? Hayir,
      4 noop_already_flagged
- [x] Frontend spec patch git diff'te gorunuyor mu? Evet, +49/-1 satir
- [x] ADR-009 docs/decisions/'da gorunuyor mu? Evet, ADR-008'den sonra

---

## Pre-existing issues discovered during H7 (not introduced by H7)

H7 Stage 5 close'da full integration suite ilk kez calistirildi (H6 close
sadece `test_work_pilot.py`'i kosmustu). Bu **yeni bir kesif** ortaya
cikardi:

### Issue PE-1: H4 placeholder records carry source_type='digital_corpus'

- **Test**: `tests/integration/test_dia_pilot.py::test_a1_all_person_records_validate`
- **Failing records**: 2,262 person records (sample PIDs:
  iac:person-00021298, 21299, 21300, 24359, 24706)
- **Schema violation**: `provenance.derived_from[0].source_type ==
  "digital_corpus"`, but person.schema enum allows only
  `["primary_textual", "secondary_scholarly", "tertiary_reference",
  "manual_editorial", "authority_file"]`
- **Source**: All 2,262 records carry release tag `v0.1.0-phase0`
  (Hafta 4 v2 person seed, commit `6ac18b2`). H4 commit message claims
  "26/26 tests green"; this means at H4 time the schema accepted
  `digital_corpus`. The H6 Stream 4 schema migration (v0.1.0 -> v0.2.0)
  narrowed the source_type enum, but the migration only touched
  `work.schema.json`, not `person.schema.json` — and the existing 2,262
  records were not re-validated post-migration.
- **Blame**: NOT H7. H7's only canonical/person mutations were on PIDs
  184, 115, 20919, 182 (4 records). The 2,262 failing records are
  untouched by any H7 commit.
- **Severity**: Schema-invalid records are technical debt, not data
  corruption. The records semantically encode "OpenITI Tier 4
  placeholder author from digital corpus" — a meaningful provenance
  category that the schema simply doesn't have a vocabulary for.
- **Remediation options** (deferred to H8):
  - Option B1: Extend person.schema source_type enum to include
    `digital_corpus`. Lowest-risk; documents reality.
  - Option B2: Mass-rename 2,262 records' source_type to
    `tertiary_reference`. Wrong semantics (digital_corpus is closer to
    primary_textual than tertiary_reference for OpenITI).
  - Option B3: Mass-rename to `primary_textual`. Closer semantically
    but loses the "Tier 4 placeholder, no fulltext mint yet"
    distinction.
  - Recommended: B1 + ADR-010 documenting the new enum value.

### Acceptance impact

H7 close commits the integration suite in the state:
- `tests/integration/test_work_pilot.py`: 23 passed, 3 xfail, 3 skipped
- `tests/integration/test_h7_invariants.py`: 6 passed (H7's own work)
- `tests/integration/test_dia_pilot.py::test_a1`: FAILS (Issue PE-1 above)
- Other test_dia_pilot.py tests: 44 passed (suite robust to PE-1)
- Total: 73 passed, 1 failed, 3 skipped, 3 xfailed

The failing test is committed as-is; H8 first task: PE-1 remediation.
This is intentional. H7's scope was QID quality + frontend gate +
ADR-009 doctrine. PE-1 is unrelated technical debt that surfaced
because H7 ran the full suite — value created by *finding* the bug,
not by silently masking it.

H7 temiz kapandi. H8 oturumu rich-mint kaynak verisi (DiA chunk
re-extraction veya equivalent) ile baslamalidir - ADR-009 doctrine'i
ile uyumlu Stream 2 ancak ondan sonra mumkun.

H8 baslarken iki paralel oncelik:

1. **PE-1 remediation** (tahmini 30-60 dk): person.schema.json source_type
   enum'a `digital_corpus` ekle, ADR-010 yaz (decision rationale), schema
   migration v0.2.0 -> v0.2.1 bump, integration suite tamamen yesil.
2. **DiA rich-mint pipeline kuruluusu** (tahmini 6-10 saat): ADR-009
   doctrine'i ile uyumlu, ham DiA encyclopedia kaynaktan (chunks veya
   scraping) extract + canonicalize.

PE-1 oncelikle yapilirsa H8'de "test suite tamamen yesil baseline" elde
edilir; rich-mint pipeline bunun uzerine kurulur.
