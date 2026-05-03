# ADR-003 — Ontoloji Omurgası

| Alan | Değer |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-03 |
| **Decision-maker** | Ali Çetinkaya (solo) |
| **Supersedes** | — |
| **Superseded by** | — |
| **Related** | ADR-001 (URI Scheme), ADR-002 (Authority Reconciliation) |
| **Affects** | `ontology/iac_ontology.ttl`, `ontology/iac_context.jsonld`, `schemas/*` (`@type` field'ları), tüm LOD export pipeline'ları |

---

## 1. Context

islamicatlas-canonical'in entity'lerinin RDF dünyasında nasıl tipleneceğini sabitlemek zorundayız. Tek bir ontoloji yeterli değildir — İslam medeniyeti tarihinin ölçek ve çeşitliliği (yer, kişi, hanedan, kurum, eser, olay, sikke, yapı, yol, sefer) **birden fazla mevcut standardın katmanlı kullanımını** zorunlu kılıyor.

Karar üç boyutta verilmeli:

1. **Üst seviye sınıf hiyerarşisi:** Hangi standart "place", "person", "dynasty" gibi temel tipleri sağlar?
2. **Domain-specific extension:** İslam tarihi'ne özgü kavramlar (Caliphate, Madhab, Tariqa, Vakıf, Iqta, Tabaqa…) hangi namespace altında, hangi üst sınıfa bağlı?
3. **Yardımcı ontolojiler:** Provenance, time, multilingual labels, bibliography için hangi standartlar?

Bu ADR üçünü de sabitliyor.

---

## 2. Decision

### 2.1 Ontology stack (katmanlı)

| Katman | Standard | Ne için |
|---|---|---|
| **Üst sınıf hiyerarşisi** | **CIDOC-CRM** v7.1.3 (E1–E97) | Müze/arşiv/dijital miras dünyasının altın standardı; Pelagios + Linked Pasts uyumu |
| **Yer (place) profili** | **CIDOC-CRM E53 Place** + **Pleiades application profile** | Pelagios Network'e katılım için zorunlu |
| **Kişi (person) profili** | **CIDOC-CRM E21 Person** + `schema.org/Person` + `foaf:Person` *(Phase 0.2'de)* | Web ekosistemiyle (Google KG) köprü |
| **Hanedan/kurum (dynasty)** | **CIDOC-CRM E40 Legal Body** | Vergi toplayan, ordu kuran, halefi olan kurum |
| **Eser/metin** | **CIDOC-CRM E73 Information Object** + `schema.org/CreativeWork` *(Phase 0.2)* | OAI-PMH + Bibframe köprüsü |
| **Olay** | **CIDOC-CRM E5 Event** + `schema.org/Event` *(Phase 0.3)* | Ortak olay modeli |
| **Provenance** | **PROV-O** (W3C) | "Hangi kayıt, ne zaman, kim girdi, hangi kaynaktan" |
| **Bibliyografi** | **Dublin Core Terms** (Phase 0); **BIBO** (Phase 0.2+) | Generic metadata vs. detailed bibliographic |
| **Temporal** | **OWL-Time** (Allen interval calculus) | "öncesinde / sonrasında / örtüşür" sorguları |
| **Multilingual** | **SKOS** (`prefLabel`, `altLabel`) + ISO 639-3 lang tag'leri | Kontrollü vocabulary köprüsü |
| **Web-ekosistem köprüsü** | **schema.org** (subset, JSON-LD context'te) | SEO + Google Knowledge Graph |
| **Domain extension** | **`iac:` namespace** | İslam tarihine özgü sınıflar |

### 2.2 `iac:` extension namespace — Phase 0 sınıfları

Phase 0'da fiilen kullanılacak `iac:` sınıfları (place + dynasty namespace için minimal):

```turtle
@prefix iac: <https://w3id.org/islamicatlas/ontology#> .
@prefix crm: <http://www.cidoc-crm.org/cidoc-crm/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

# === HANEDAN HİYERARŞİSİ ===
iac:Dynasty            rdfs:subClassOf  crm:E40_Legal_Body .
iac:Caliphate          rdfs:subClassOf  iac:Dynasty .
iac:Sultanate          rdfs:subClassOf  iac:Dynasty .
iac:Emirate            rdfs:subClassOf  iac:Dynasty .
iac:Imamate            rdfs:subClassOf  iac:Dynasty .
iac:Beylik             rdfs:subClassOf  iac:Dynasty .

# === YER ALT TİPLERİ (Phase 0'da minimum kullanım) ===
iac:Settlement         rdfs:subClassOf  crm:E53_Place .
iac:Region             rdfs:subClassOf  crm:E53_Place .  # iqlim, kūra
iac:Iqlim              rdfs:subClassOf  iac:Region .     # Makdisi/Yâkût coğrafi taksim
```

Tam ontoloji (Phase 0.2+ için kapsamlı extension) `ontology/iac_ontology.ttl` dosyasında; aşağıdaki sınıflar tanımlı ama Phase 0'da kullanılmaz:

| Class | Üst sınıf | Phase'i hangi P'de aktif |
|---|---|---|
| `iac:Madhab` | `crm:E55 Type` + `skos:Concept` | P0.2 (person) |
| `iac:Tariqa` | `crm:E40 Legal Body` | P0.3 |
| `iac:Madrasa` | `crm:E74 Group` + `iac:Settlement` (binası) | P0.3 |
| `iac:Mosque` | `crm:E27 Site` | P0.3 |
| `iac:Tekke` | `crm:E27 Site` | P0.3 |
| `iac:Vakıf` | `crm:E40 Legal Body` | P0.3 |
| `iac:Iqta` | `crm:E40 Legal Body` | P0.3 |
| `iac:Tabaqa` | `crm:E78 Curated Holding` | P0.3 |
| `iac:Isnad` | `crm:E29 Design` | P0.3 |
| `iac:CaliphalRole` | `crm:E55 Type` | P0.2 (person) |

**Genişletme yetkisi:** Yeni `iac:` sınıfı ekleme kararı Çetinkaya'ya aittir; her ekleme bir CHANGELOG entry + ontology version bump (semver).

---

## 3. Sub-decisions (Hafta 0'da finalize edilen 4 alt nokta)

### 3.1 `iac:Caliphate` `crm:E40 Legal Body` mı `crm:E74 Group` mu?

**Karar: Üç ayrı kavram, üç ayrı sınıf.**

| Kavram | Class | Üst sınıf | Örnek |
|---|---|---|---|
| **Hilafet kurumu** (Râşidîn, Ümeyye, Abbasi…) | `iac:Caliphate` | `iac:Dynasty` → `crm:E40 Legal Body` | Abbasi Hilafeti (750-1258) — vergi toplar, ordu kurar |
| **Halife rolü** (kişinin sıfatı) | `iac:CaliphalRole` | `crm:E55 Type` | Hârûnürreşîd'in "halife" sıfatı |
| **Hilafet kavramı/teorisi** (Sünni/Şîi hilafet düşüncesi) | `iac:CaliphalInstitution` | `crm:E55 Type` + `skos:Concept` | "Sünni hilafet" doktrini |

**Gerekçe:**
- CIDOC-CRM `E40 Legal Body` "yasal kişiliği olan, yasal yükümlülüklere girebilen kurum" — devlet, hilafet kurumu, hanedan tam buraya oturuyor.
- `E74 Group` "ortak özelliği veya hedefi olan grup" (örn. "Bağdat'taki âlimler") — daha gevşek; kurumsal yasal kişilik içermez.
- Halife **rolü** ile halife **kişi** ile hilafet **kurumu** ile hilafet **kavramı** akademik yazımda sıkça karıştırılır; ontolojide ayırt edilmesi sorgu netliği için kritiktir.

**Phase 0 kullanımı:** Sadece `iac:Caliphate` (kurum, dynasty namespace'inde). Diğer ikisi Phase 0.2'de person namespace ile aktif olur.

**Reject:**
- "Tek class `iac:Caliphate` her şey için" → karışık prosopografi sorguları.
- `crm:E74 Group`: hilafetin yasal kişiliğini görmezden gelir; vergi/ordu/halef ilişkileri ifade edilemez.

### 3.2 `iac:Madhab` Type mı Class mı?

**Karar: `iac:Madhab` çift tipli — `crm:E55 Type` + `skos:Concept`.**

```turtle
iac:Madhab  rdfs:subClassOf  crm:E55_Type ;
            rdfs:subClassOf  skos:Concept .

iac:Hanafi   rdf:type  iac:Madhab ;
             skos:prefLabel  "Hanefî"@tr , "Ḥanafī"@en-Latn-x-alalc , "حنفي"@ar .
```

**Gerekçe:**
- `crm:E55 Type` CIDOC-CRM dünyasıyla uyumlu kalmayı sağlar (kişi.has_type → Hanafi).
- `skos:Concept` SKOS kavram hiyerarşisi sunar — "Hanefî" `skos:broader` `iac:Sunni` `skos:broader` `iac:Madhab` zinciri kurulabilir; SPARQL sorgularında `skos:transitive` kullanışlı.
- "Hanefî mensupları" bir grup olarak ifade edilmek istendiğinde `iac:HanafiFollowers` ayrı bir entity (E74 Group) olarak tanımlanabilir; ama bu Phase 0.3+ konusu.

**Reject:**
- Sadece `crm:E55 Type`: SKOS kavramsal hiyerarşisi kayboluyor.
- Sadece `crm:E74 Group`: "kişi.madhab = Hanafi" ilişkisi modellemek için zorlanırdı (kişi gruba ait — bireysel kişiyi grup üyeliği üzerinden tipleyemezsin temiz biçimde).
- `iac:Madhab` kendi top-level class: `crm:E55` veya `skos:Concept` "üst sınıf" sağlamadan ontoloji izole kalırdı.

**Phase 0 kullanımı:** Yok (P0'da person namespace yok). Ontoloji'de tanımlı, P0.2'de aktif.

### 3.3 schema.org Phase 0'da mı Phase 4'te mi?

**Karar: Phase 0 — `iac_context.jsonld` içinde minimum subset olarak; full alignment Phase 4'te.**

**Phase 0'da context'e giren schema.org map'leri:**

```json
{
  "@context": {
    "schema": "https://schema.org/",
    "Place": "schema:Place",
    "Organization": "schema:Organization",
    "name": "schema:name",
    "description": "schema:description",
    "url": "schema:url",
    "geo": "schema:geo"
  }
}
```

Yani: Phase 0 entity'lerinin JSON-LD export'unda `@type: "Place"` hem `crm:E53_Place` hem `schema:Place`'e çift tiplenir; `name` field'ı hem `crm:P1_is_identified_by` hem `schema:name`'e map'lenir.

**Gerekçe:**
- **Maliyet sıfır:** JSON-LD context'te 5-6 satır ekleme. Pipeline değişikliği yok.
- **Fayda yüksek:** Public release'de Google Knowledge Graph + Bing Snapshots gibi web crawler'ları yer/hanedan kayıtlarını machine-readable olarak indeksler. SEO yan kazanç.
- **Phase 4'e ertelemenin maliyeti:** Phase 4'te tüm export'lar regenerate edilmek zorunda kalır → release-history pollution.

**Phase 4'te yapılacak (Phase 0'da değil):**
- Tam schema.org alignment (`schema:GeoCoordinates`, `schema:PostalAddress`, `schema:event`, `schema:hasPart`).
- Schema.org domain-specific types (`schema:Religion`, `schema:Ethnicity`, ...).
- Validator-doğrulanmış `application/ld+json` script tags HTML head'lerinde.

**Reject:**
- Phase 0'da hiç schema.org: SEO + web ekosistemi köprüsü kayboluyor; Phase 4'te retroaktif eklemek migration getirir.
- Phase 0'da tam alignment: scope creep, JSON-LD context şişer, debug zorlaşır.

### 3.4 BIBO ve Dublin Core Phase 0'da mı?

**Karar: Dublin Core Terms (`dcterms:`) Phase 0'da; BIBO Phase 0.2'de.**

**Phase 0'da Dublin Core kullanımı:**

```json
{
  "@context": {
    "dcterms": "http://purl.org/dc/terms/",
    "title": "dcterms:title",
    "creator": "dcterms:creator",
    "created": "dcterms:created",
    "modified": "dcterms:modified",
    "source": "dcterms:source",
    "license": "dcterms:license"
  }
}
```

`dcterms:` provenance metadata için kullanılır:
- `dcterms:source` — entity'nin türetildiği primary source (Yâkût'un kendisi, Bosworth NID kaydı).
- `dcterms:created` — canonical record'un ilk yaratılma tarihi.
- `dcterms:modified` — son revizyon tarihi.

**Gerekçe (DC yes / BIBO no):**
- Dublin Core alanlar generic; her entity için anlamlı (provenance.source, provenance.created).
- BIBO (Bibliographic Ontology) sadece source namespace doğduğunda anlamlı: `bibo:Book`, `bibo:Article`, `bibo:Chapter`. Phase 0'da source namespace yok → BIBO field'ları boş kalırdı.
- DC'in PROV-O ile çakışması yok; tamamlayıcı (PROV-O process odaklı, DC field-level metadata).

**Phase 0.2'de BIBO eklenecek:**
- Source namespace doğduğunda `bibo:Book` (Yâkût Mu'cem), `bibo:Edition` (Wüstenfeld 1866), `bibo:Article` (DİA maddeleri) tipleri kullanılacak.

**Reject:**
- Phase 0'da BIBO context'e dahil etmek: tip referansları döner ama hiçbir entity bu tipte değil → context kalabalıklaşır.
- Phase 0'da Dublin Core'u dahil etmemek: provenance modeli eksik kalır; PROV-O alone source attribution için yeterli ifade gücüne sahip değil.

---

## 4. Ontology versioning

`iac:` ontology'sinin kendisi **semver**'lı:
- `iac_ontology_v0.1.0.ttl` Phase 0 release'inde.
- `iac:` namespace URI **stable**: `https://w3id.org/islamicatlas/ontology#`. Sınıf eklendi/kaldırıldı diye namespace değişmez.
- Sınıf çıkarımı **deprecation** ile yapılır (`owl:deprecated true`); silinmez. Backward compatibility.

---

## 5. Consequences

### Pozitif

- **CIDOC-CRM omurgası:** Müze/arşiv harvester'ları (OAI-PMH) entity'leri tanır; LIDO/EAD/MARC köprüleri kurulabilir.
- **Pleiades application profile uyumu:** Pelagios Network'e participant olma yolu açık.
- **PROV-O provenance:** "Bu kayıt 2026-05-15'te Yâkût Wüstenfeld 1866 baskısının cilt 2 sayfa 145'ten Çetinkaya tarafından canonical store'a girildi" tam ifade edilebilir.
- **Schema.org Phase 0'da minimum subset:** Web ekosistemi köprüsü düşük maliyetle açık.
- **`iac:` extension namespace:** İslam tarihine özgü kavramları ifade etmek için kontrolümüzde bir genişletme yolu.

### Negatif / kabul edilen risk

- **Multi-ontology stack karmaşıklığı:** 8+ namespace (crm, prov, dcterms, owl-time, skos, schema, foaf P0.2, iac) JSON-LD context'i şişiriyor; debug zorlaşıyor. Mitigation: context dosyası ayrı ayrı modüllerden oluşturulur, ana context import eder.
- **CIDOC-CRM öğrenme eğrisi:** E1-E97 tipoloji öğrenme yatırımı gerektiriyor; Phase 0 boyunca ~10-15 saat doküman okuması.
- **`iac:` namespace'in bakım yükü:** Yeni İslam tarihi kavramı ekleme her seferinde ontology revision + version bump.
- **Pleiades application profile** dokümantasyonu seyrek; manuel review gerekiyor.

### İzlenecek metrikler

- Hafta 6 sonu: JSON-LD export'ların W3C JSON-LD playground validator'dan geçmesi (≥ 1.000 örnek).
- Hafta 6 sonu: Turtle dump'ların `riot --validate` (Apache Jena) çıktısının hatasız olması.
- Phase 0 sonu: `ontology/iac_ontology.ttl` `pyshacl` veya `protege`'de açıldığında hata vermemesi.

---

## 6. Implementation checklist (Hafta 0 sonu + Hafta 1)

- [x] `ontology/iac_ontology.ttl` Phase 0 minimum (Dynasty hierarchy + Place subtypes).
- [x] `ontology/iac_context.jsonld` JSON-LD context.
- [ ] `schemas/*` `@type` field'ları yukarıdaki class hiyerarşisini kullanır.
- [ ] Hafta 6: Pleiades application profile field'ları integration (export pipeline'da).
- [ ] Phase 0 sonu: `ontology/crosswalks/iac_to_pleiades.ttl` (place için CRM↔Pleiades crosswalk).

---

## 7. References

- CIDOC-CRM. [Definition v7.1.3](http://www.cidoc-crm.org/sites/default/files/CIDOC%20CRM_v7.1.3_2024.pdf).
- W3C. [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/).
- W3C. [Time Ontology in OWL (OWL-Time)](https://www.w3.org/TR/owl-time/).
- W3C. [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/).
- DCMI. [Dublin Core Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/).
- D'Arcus & Giasson. [BIBO: Bibliographic Ontology](http://bibliontology.com/).
- Pleiades. [Application profile (informal)](https://pleiades.stoa.org/help/conceptual-overview).
- Pelagios. [Linked Places format](https://github.com/LinkedPasts/linked-places-format).
- schema.org. [Type hierarchy](https://schema.org/docs/full.html).

---

**Versiyon:** 1.0 (Accepted)
**Son güncelleme:** 03 Mayıs 2026

---

## 8. Update Note v1.1 — Forward-Declared Person/Work/Manuscript/Event (03 May 2026)

ADR-005 (Unified Entity Catalog) ile birlikte ontoloji şu sınıflarla genişletildi (forward-declared, ilgili Phase'de aktive):

| Class | Aktivasyon | CIDOC CRM align | Diğer hizalamalar |
|-------|-----------|-----------------|-------------------|
| `iac:Person` | P0.2 | `crm:E21_Person` | `foaf:Person`, `schema:Person` |
| `iac:Scholar`, `iac:Ruler`, `iac:Narrator`, `iac:Poet`, `iac:Architect`, `iac:Patron`, `iac:Mufti`, `iac:Calligrapher` | P0.2 | `crm:E21` + `crm:E55_Type` | rolleri `dcterms:type` ile |
| `iac:Work` | P0.2 | `crm:E73_Information_Object` | `frbr:Work`, `bibo:Document`, `schema:CreativeWork` |
| `iac:Book`, `iac:Treatise`, `iac:Poem`, `iac:Fatwa`, `iac:Letter`, `iac:Map`, `iac:Compendium`, `iac:Dictionary`, `iac:HadithCollection`, `iac:Tafsir`, `iac:Tarikh`, `iac:Sira`, `iac:Tabaqa`, `iac:Geography` | P0.2 | `crm:E73` subClass | Genre vocab `iac_ontology.ttl`'de SKOS scheme olarak |
| `iac:Manuscript` | P0.3 | `crm:E84_Information_Carrier` | `frbr:Manifestation`+`frbr:Item`, `schema:Manuscript` |
| `iac:Codex`, `iac:Scroll`, `iac:Fragment`, `iac:Defter` | P0.3 | `crm:E84` subClass | — |
| `iac:Event` | P0.3 | `crm:E5_Event` | `schema:Event` |
| `iac:Battle`, `iac:Treaty`, `iac:Founding`, `iac:Death`, `iac:Birth`, `iac:Conference`, `iac:Conquest`, `iac:Revolt`, `iac:Coronation`, `iac:Pilgrimage`, `iac:Voyage`, `iac:Composition`, `iac:Disaster` | P0.3 | `crm:E5` subClass | — |

**Ontoloji TTL dosyası `ontology/iac_ontology.ttl` v1.1 ile yukarıdaki forward-declared sınıfları eklendi.** Aktive Phase'leri için `rdfs:comment "FORWARD-DECLARED for P0.2"` (veya P0.3) annotation'u var; integrity-check pipeline o Phase aktive olana kadar bu sınıfların kanonikal kayıtlara `@type` olarak basılmasına izin vermez (yalnızca cross-reference field'larında PID olarak görünebilirler).

**Yeni properties (P0.2-P0.3 forward):**

- `iac:authoredBy` (Person → Work; subPropertyOf `dcterms:creator`)
- `iac:witnessesWork` (Manuscript → Work; subPropertyOf `frbr:exemplifies`)
- `iac:teacherOf` (Person → Person; SKOS-style soft assertion, NOT `crm:P11`)
- `iac:participantIn` (Person/Dynasty → Event; subPropertyOf `crm:P11_had_participant` inverse)
- `iac:precededByEvent`, `iac:followedByEvent` (Event ↔ Event temporal chain)
- `iac:causes`, `iac:consequences` (Event ↔ Event causal chain; not symmetric with preceded/followed)

P0.2 aktive olunca bu properties tam olarak ontoloji'de `rdfs:domain`/`rdfs:range` ile kısıtlanacak; P0'da yalnız property URI'leri rezerve.
