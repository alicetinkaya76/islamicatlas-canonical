# H7 Known Issues — for H8 backlog

> H7'de kesfedilen ama H7 scope'u disindaki sorunlar. H8'de
> oncelik sirasi ile ele alinmasi onerilir.

---

## PE-1: H4 placeholder records carry invalid source_type='digital_corpus'

**Severity**: Medium (schema invalid, not data corrupt)
**Discovered**: H7 Stage 5, full integration suite first run
**Affected**: 2,262 of 21,946 person records (~10%)
**Test**: `tests/integration/test_dia_pilot.py::test_a1_all_person_records_validate`

### Detection

H7 Stage 5 close'da `pytest tests/integration/` ilk kez tum suite olarak
calistirildi. `test_a1` 2,262 schema violation rapor etti, ilk 5 sample:

```
iac:person-00021298, 21299, 21300, 24359, 24706
provenance.derived_from[0].source_type == 'digital_corpus'
schema enum: [primary_textual, secondary_scholarly, tertiary_reference,
              manual_editorial, authority_file]
```

### Root cause

Tum 2,262 record release tag'i `v0.1.0-phase0` (Hafta 4 v2 person seed,
commit `6ac18b2`). H4 commit message: "26/26 tests green" — yani H4
zamaninda schema bu source_type'i kabul ediyordu.

H6 Stream 4 (schema migration v0.1.0 -> v0.2.0) source_type enum'i
sadece `work.schema.json`'da revize etti, ama person.schema.json'i da
ayni enum'a baglayan `_common/provenance.schema.json` (veya esdegeri)
sessizce daraldi. Mevcut 2,262 record migration'da re-validate
edilmedi — H6'da migration journal yalnizca work records icin tutuldu.

### Why discovered now

H6 close'da sadece `test_work_pilot.py` kosturuldu. `test_dia_pilot.py`
ve `test_yaqut_pilot.py` H4'ten beri tracked olsalar da H6 acceptance
kontrolu disinda kaldi. H7 Stage 5'te full `tests/integration/` ilk kez
tetiklendi.

### Remediation options (H8'de karar)

**Option B1 — Schema gevsetme (recommended)**: source_type enum'a
`digital_corpus` ekle. Schema bump v0.2.0 -> v0.2.1, ADR-010 yaz
("digital_corpus source_type semantics" decision rationale).

- **Artilari**: Sifir data mutation; semantic dogru
  ("digital_corpus" = OpenITI tier 4 placeholder kaynak); migration
  trivially idempotent.
- **Eksileri**: Schema bump documentation overhead.

**Option B2 — Mass rename to `tertiary_reference`**: 2,262 record patch.

- **Artilari**: Schema dokunulmaz.
- **Eksileri**: Yanlis semantic. `tertiary_reference` = encyclopedia,
  dictionary, handbook (DiA gibi). OpenITI digital_corpus tier 4
  placeholder degil — bu kategoriye uymuyor.

**Option B3 — Mass rename to `primary_textual`**: Daha yakin semantic
ama "Tier 4 placeholder, no fulltext mint yet" distinction'i kaybolur.

**Recommendation**: B1. ADR-010 dosyasi `digital_corpus` source_type'in
hangi durumlarda kullanildigini netlestirir, gelecekte tier 4
placeholder pipeline'i bu enum'a baglanir.

### Effort estimate

B1: 30-60 dakika (schema patch + migration script + ADR-010 + test
re-run).

B2 veya B3: 30-45 dakika (data patch + record_history append +
test re-run); ama yanlis semantic kaliyor.

### Why deferred to H8 (not fixed in H7)

PE-1 ne H7 commit'lerinden tetiklendi, ne H7 hedeflerine bagli. H7'nin
core scope'u QID quality (Stage 1) + frontend gate (Stage 2) + ADR-009
doctrine (Stage 3). PE-1'i H7 close'da fix etmek scope creep yaratir,
"H7 her seyi temizleyen hafta" kafa karistiricisi olur. Daha onemlisi:
PE-1 ne kadar **yeni keşif** olarak kayda geçerse, H4 -> H6 migration
practice'inde bir gap oldugu gorunur — bu, dokumanin kendisiyle
academic deger uretir.

H8'de B1 oncelikle yapilirsa, H8 kalan saatler rich-mint pipeline
(ADR-009) icin saglam bir baseline'da calisir.

### H8 acceptance criterion (proposed)

`AL: Pre-existing PE-1 (2,262 person record schema invalid) remediated;
test_dia_pilot::test_a1 PASSED; ADR-010 written.`
