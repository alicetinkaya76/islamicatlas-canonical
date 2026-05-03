# ADR-005: Unified Entity Catalog

**Status:** Accepted (autonomous resolution; subject to maintainer override)
**Date:** 2026-05-03
**Phase:** 0
**Supersedes:** —
**Related:** ADR-001 (URI scheme), ADR-003 (Ontology stack), ADR-004 (Search-first), ADR-006 (Adapter pattern)

---

## Bağlam

Hafta 0'da Phase 0 namespace'i sadece `place` ve `dynasty` ile sınırlıydı; geri kalan entity tipleri `iac_ontology.ttl`'de "forward-declared" olarak duruyordu (Madhab, Tariqa, Madrasa, Mosque, Tekke, Vakıf, Iqta, Tabaqa, Isnad, CaliphalRole, CaliphalInstitution).

Search-first vizyonu (ADR-004) ve "yeni kitap/içerik kolayca entegre olmalı" gereksinimi şunu gerektirir: **birinci-sınıf entity tipleri P0-P0.2'de tam tanımlı olmalı**, çünkü:

1. Mevcut altyapıda zaten persons (Science Layer 186 scholar), works (Bosworth NID kayıtları, OpenITI Enrichment 13,681 file), manuscripts (Ottoman HTR pilot, kadı sicilleri 33,149 record), events (Salibiyyat çatışmaları, Evliya seyahat olayları) **veri olarak mevcut**.
2. Search collection (`iac_entities`) tek collection — entity_type discriminator'ı tüm tiplerle birlikte tanımlanmalı, sonradan eklemek schema migration zahmeti yaratır.
3. Adapter pattern (ADR-006) "yeni kitap → mevcut entity tipleri" demek; `Person`, `Work`, `Manuscript` tipleri Phase 0'da yoksa Bosworth ETL bile rulers field'ını kanonikal person'a bağlayamaz.

Bu ADR şu kararları verir: (1) aktif namespace listesi, (2) per-namespace Phase aktivasyon planı, (3) cross-namespace değişmezlikler, (4) namespace başına minimum required field.

---

## Karar 5.1: Aktif namespace listesi

**Karar:** İki kademeli aktivasyon — **P0-P0.2 hard scope** (6 namespace), **P1+ soft scope** (3 ek namespace forward-declared).

### P0-P0.2 (hard scope, schema'sı bu repo'da var)

| Namespace | Phase aktivasyon | Anlam | Alt tipler |
|-----------|------------------|-------|------------|
| `place` | **P0 aktif** (Hafta 0'da yapıldı) | Coğrafi yerler | Settlement, Region, Iqlim |
| `dynasty` | **P0 aktif** (Hafta 0'da yapıldı) | Siyasi hanedanlar | Caliphate, Sultanate, Emirate, Imamate, Beylik |
| `person` | **P0.2 aktif** (Bosworth rulers fix-up + Science Layer entegrasyonu) | İnsan birey | Scholar, Ruler, Narrator, Poet, Architect, Patron |
| `work` | **P0.2 aktif** (kaynak namespace olarak; Bosworth, Yâqūt, Le Strange'in kendisi) | Soyut entelektüel eser (FRBR Work) | Book, Treatise, Poem, Fatwa, Letter, Map |
| `manuscript` | **P0.3 aktif** | Fiziksel taşıyıcı (FRBR Manifestation+Item) | Codex, Scroll, Fragment |
| `event` | **P0.3 aktif** | Tarihi olay | Battle, Treaty, Founding, Death, Birth, Conference |

### P1+ (soft scope, forward-declared, schema henüz draft)

| Namespace | Phase | Anlam | Şu an |
|-----------|-------|-------|-------|
| `institution` | P1 aktif | Madrasa, mosque, tekke, vakıf, iqta | Ontoloji'de class var, schema yok |
| `concept` | P1 aktif | Madhab, tariqa, intellectual movement | Ontoloji'de class var, schema yok |
| `route` | P1.2 aktif | Hac, ticaret, seyahat rotaları | Yalnız ontoloji rezervasyonu |

**Kapsam dışı (current scope):**

- `coin` namespace: DarpIslam'ın 3,458 mint'i mevcut altyapısında kalır; canonical store'a ithal Phase 1.5'te değerlendirilir.
- `inscription` namespace: Ottoman kitabeleri Phase 2.
- `fragment` (papirüs/genizah): Phase 2+.

---

## Karar 5.2: Phase aktivasyon planı

| Phase | Namespace'ler aktive | Acceptance criterion |
|-------|--------------------:|----------------------|
| P0 (current, Hafta 0-8) | place, dynasty | Bosworth NID-001..186 tam canonical; Yâqūt pilot ≥1k place; tüm kayıtlar `dynasty.schema.json` veya `place.schema.json` validates |
| P0.2 (Hafta 9-16) | person, work | Science Layer 186 scholar canonical person; Bosworth rulers inline → person PID linkage; OpenITI 13,681 file → work PID seed |
| P0.3 (Hafta 17-24) | manuscript, event | Ottoman HTR pilot kadı sicilleri → manuscript PID; Salibiyyat çatışmaları → event PID; Evliya seyahat olayları → event PID |
| P1 (Hafta 25+) | institution, concept | Konya City Atlas 583 structure → institution PID; madhab/tariqa SKOS hierarchy → concept PID |

**Bağımlılık zinciri:** person → work → manuscript (manuscripts kim tarafından nesnel, hangi work'ün nüshası?). Event → person, place. Institution → place, person. Concept → person, work.

**Geri-uyumluluk garantisi:** P0.2'de `person` aktive olduğunda `dynasty.schema.json`'ın `rulers[].person_pid` field'ı (zaten forward-declared) doldurulmaya başlar; eski kayıtlar inline `name` ile kalmaya devam eder, breaking change yok.

---

## Karar 5.3: Cross-namespace değişmezlikler

Bu invariant'lar pipeline integrity-check katmanında zorlanır (JSON Schema'da değil — çünkü cross-document referans kontrolü):

1. **Bidirectional capital pointer**: `place.had_capital_of` ↔ `dynasty.had_capital[].place`. P0'da aktif.
2. **Bidirectional dynasty succession**: `dynasty.predecessor` ↔ `dynasty.successor`. P0'da aktif.
3. **Bidirectional place succession**: `place.predecessor_place` ↔ `place.successor_place`. P0'da aktif.
4. **Person-dynasty membership** (P0.2): `person.affiliated_dynasties[]` ↔ `dynasty.rulers[].person_pid` (rulers için) veya `dynasty.affiliated_persons[]` (non-ruler patrons/officials).
5. **Work authorship** (P0.2): `work.authors[]` ↔ `person.authored_works[]`.
6. **Manuscript witness** (P0.3): `manuscript.witnesses_work[]` ↔ `work.extant_manuscripts[]`.
7. **Event participants** (P0.3): `event.participants[]` (places, persons, dynasties) ↔ ilgili entity'lerin `events_participated_in[]`.
8. **Source citation chain**: her entity'nin `provenance.derived_from[].source_id` ya bir CURIE (yaqut:N, bosworth-nid:N) ya da P0.2'den itibaren bir `iac:work-NNNNNNNN` PID. CURIE → PID dönüşüm haritası `data/source_curie_resolver.yaml`'da tutulur.

Integrity-check pipeline (`pipelines/integrity/check_all.py`) her release öncesi tüm bu invariant'ları doğrular; başarısızlıklar release blocker'dır.

---

## Karar 5.4: Namespace başına ortak alanlar

Tüm entity şemalarında **zorunlu** dört alan:

```
@id            : iac:<namespace>-NNNNNNNN
@type          : array, ilk eleman iac:<TypeName>
labels         : multilingual_text $ref (prefLabel zorunlu)
provenance     : provenance $ref (derived_from + generated_by + attributed_to + created)
```

Tüm entity şemalarında **isteğe bağlı, ama desteklenmesi tavsiye edilen** alanlar:

```
authority_xref : authority_xref $ref
note           : string ≤5000 chars (free-text editorial)
deprecated     : bool (provenance.deprecated'a delege; üst seviyede convenience field)
```

Entity-tipi-spesifik alanlar her şemada ayrı tanımlanır; sonsuz polimorfizm yerine ortak temele sadık kalınır → search projector tek bir generic projeksiyon mantığı yazar (ADR-006).

---

## Sonuçlar

**Pozitif:**

- Tek arama deneyimi tüm entity tiplerinde tutarlı (ortak alanlar).
- Yeni adapter eklemek = mevcut entity şemalarına kayıt üretmek; yeni schema yazılmıyor.
- Phase aktivasyonu deterministik — hangi içerik ne zaman canonical olacak belli.
- Forward-declared P1 namespace'leri ontology + URI'de hazır; schema sonradan eklenir (yarı-breaking change yok).

**Negatif (kabul edilen):**

- 6 entity tipi × ~10 alan = ~60 alan ortalama; search collection schema 200 field'a yaklaşır (Typesense default 150 field limitini aşar — `enable_nested_fields=true` ile çözülür).
- Cross-namespace integrity check pipeline'ı her release öncesi 5-10 dakika sürebilir.

**Yeniden gözden geçirme:** P0.2 sonunda. Person + work aktivasyonundan sonra Bosworth rulers'ı person'a göçüren migrasyon başarısı; OpenITI → work eşleme reconciliation rate; namespace catalog kapsamının yeterliliği.

---

## Atıflar

- ADR-001 (URI scheme), ADR-003 (Ontology stack), ADR-004 (Search-first), ADR-006 (Adapter pattern)
- FRBR (Functional Requirements for Bibliographic Records): https://www.ifla.org/publications/functional-requirements-for-bibliographic-records
- CIDOC CRM v7.1.2: http://www.cidoc-crm.org/
