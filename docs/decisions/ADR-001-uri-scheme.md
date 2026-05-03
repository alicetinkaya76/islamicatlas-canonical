# ADR-001 — URI Şeması (Stable Identifier Strategy)

| Alan | Değer |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-03 |
| **Decision-maker** | Ali Çetinkaya (solo) |
| **Supersedes** | — |
| **Superseded by** | — |
| **Related** | ADR-002 (Authority Reconciliation), ADR-003 (Ontology Stack) |
| **Affects** | `data/`, `schemas/`, `ontology/iac_context.jsonld`, `pipelines/` PID generator |

---

## 1. Context

islamicatlas.org bugün 13 katmanda ~59.000 entity tutuyor; 7 farklı ID şeması (int, slug, prefix-int kombinasyonları) kullanılıyor. Stable URI yokluğu üç somut soruna yol açıyor:

1. **Akademik alıntılanabilirlik yok.** Bir Yâkût yer kaydına alıntı verilemez; sadece "site içinde 12.954 yer arasında ara" denilebilir.
2. **Cross-layer query mantığı kırık.** Yâkût ID 7842 ile Le Strange ID 312 aynı yere işaret ediyorsa, bu eşleştirme harici bir tabloda; URI seviyesinde değil.
3. **LOD entegrasyonu imkânsız.** Pelagios Network, Linked Pasts ekosistemi, Wikidata cross-references — hiçbiri stable, dereferenceable URI'ler olmadan çalışmaz.

Bu ADR, `islamicatlas-canonical`'in URI omurgasını tanımlar. Karar, geri alınması en pahalı tasarım kararıdır: bir kez yayınlanan URI'lerin değişmesi tüm dış alıntıları kırar.

---

## 2. Decision

**Üç katmanlı URI mimarisi** kullanılacak:

```
Katman 1 (immutable internal PID):  iac:place-00012345
Katman 2 (public dereferenceable):  https://islamicatlas.org/id/place/aleppo
Katman 3 (LOD persistent):          https://w3id.org/islamicatlas/place/aleppo
Snapshot (versioned):               https://islamicatlas.org/id/place/aleppo?v=v0.1.0
```

### 2.1 Internal PID (Katman 1)

**Format:** `iac:{namespace}-{8-digit-zero-padded-int}`

- `iac` = `islamicatlas canonical`. CURIE prefix; `iac:` `https://w3id.org/islamicatlas/`'e expand eder (bkz. `iac_context.jsonld`).
- `{namespace}` = full namespace name (`place`, `dynasty`, `person`, `source`, `event`, `monument`, ...). Kısaltma yok (bkz. alt-karar 1.1).
- `{8-digit-int}` = ardışık integer, namespace başına bağımsız sayaç. 8 digit → 99.999.999 entity headroom.

**Generation rule:** Pipeline ETL sırasında deterministik atama. Her entity için canonical record ilk yazıldığında PID assign edilir; bir kez assign edildikten sonra **asla değişmez**. PID assignment, source record fingerprint hash'i + namespace counter kombinasyonuyla idempotent.

**Örnekler:**
- `iac:place-00000001` (Mekke — first place loaded)
- `iac:dynasty-00000001` (Râşidîn — Bosworth NID #1)
- `iac:place-00012954` (Yâkût'un sonuncu kaydı, hipotetik)

### 2.2 Public dereferenceable URI (Katman 2)

**Format:** `https://islamicatlas.org/id/{namespace}/{slug}`

- `/id/` path prefix — Berners-Lee Linked Data design issues "Cool URIs" dokümantasyonuna uyumlu (303-redirect target pattern).
- `{namespace}` = singular: `/id/place/`, `/id/dynasty/` (Pleiades plural `/places/` kullanır; biz singular tercih ediyoruz çünkü "tek bir entity'nin identifier'ı" anlamı pluraldan daha temiz).
- `{slug}` = ASCII transliterasyon + lowercase + hyphen-separated.

**Slug üretimi:**
1. Birincil isim (`prefLabel`) ASCII'ye dönüştürülür (Arapça → ALA-LC romanization simplified, diakritik düşürülür: `حلب` → `ḥalab` → `halab`).
2. Lowercase + non-alphanumeric → hyphen.
3. Çakışma durumunda discriminator suffix: `aleppo`, `aleppo-2`, `aleppo-3` (kaynak prefix değil, sadece ardışık discriminator).

**Content negotiation** (Phase 2'de implementasyon — Phase 0'da spec olarak yazılır):
- `Accept: text/html` → `https://islamicatlas.org/doc/place/aleppo` (HTML page)
- `Accept: application/ld+json` → `https://islamicatlas.org/data/place/aleppo.jsonld`
- `Accept: text/turtle` → `https://islamicatlas.org/data/place/aleppo.ttl`

`/id/` resolver Phase 2'de canlı; Phase 0'da URI'ler **schema'da yazılır ama resolve etmez** (bilinçli kabul).

### 2.3 LOD persistent URI (Katman 3)

**Format:** `https://w3id.org/islamicatlas/{namespace}/{slug}`

W3id ([w3id.org](https://w3id.org)) [W3C Permanent Identifier Community Group](https://www.w3.org/community/perma-id/) tarafından işletilen kalıcı redirect servisi. Domain (`islamicatlas.org`) bir gün düşse veya el değiştirse bile w3id mirror dış alıntıları korur.

**Setup:** github.com/perma-id/w3id.org reposuna PR atılır. Phase 0 Hafta 6'da (JSON-LD export hazırlanırken — `@id` field'ları zaten w3id formatına göre yazılıyor olacak).

### 2.4 Versioned snapshot URI

**Format:** `?v={semver-tag}` query string.

- `?v=v0.1.0` → 2026-Haziran release snapshot.
- Memento (RFC 7089 `Accept-Datetime`) Phase 4'e ertelendi (alt-karar 1.4).

---

## 3. Sub-decisions (Hafta 0'da finalize edilen 5 alt nokta)

### 1.1 PID format: `place-00012345` mi `pl-00012345` mı?

**Karar: Full namespace name (`place-00012345`).**

**Gerekçe:**
- Uzun PID internal'dır — public URI zaten slug kullanır. URL boyu argümanı geçersiz.
- Self-documenting: log/debug/error mesajlarında `iac:dy-00000042` `iac:dynasty-00000042`'den daha az okunabilir.
- Gelecekte 10+ namespace olduğunda (place/person/dynasty/source/event/monument/route/voyage/work/institution) iki-harfli prefix collision riski var (`pe`=person mu place mi?).
- Pleiades pattern'i (`pleiades:places/12345`) full namespace kullanıyor; en yakın referans projeye uyum.

**Reject:**
- 2-3 harfli abbreviation (`pl-`, `dy-`): minor URL gain, major readability loss.

### 1.2 W3id namespace registration — ne zaman?

**Karar: Phase 0 Hafta 6 başında PR.**

**Gerekçe:**
- W3id PR review tipik olarak 1-3 hafta sürüyor (Community Group volunteer-driven).
- Hafta 6'da JSON-LD export pipeline yazılıyor — `@id` field'ları w3id URL'lerine işaret ediyor olacak. PR Hafta 6 başında atılırsa Hafta 8 release'inde aktif.
- Daha erken (Hafta 0-1) atılırsa: w3id config'i değiştirme riski (henüz schema kararsız).
- Daha geç (Hafta 7-8) atılırsa: release kapısında PR henüz merge olmamış olabilir → URI'ler 404 verir.

**Implementation note:** PR template, namespace owner = Çetinkaya ORCID, redirect target = `https://islamicatlas.org/id/$1` (regex capture).

### 1.3 `/id/` mı `/entity/` mi `/places/` mi (path prefix)?

**Karar: `/id/{namespace}/{slug}`.**

**Gerekçe:**
- LOD best practice (Berners-Lee, "Cool URIs for the Semantic Web"): `/id/` resource identifier; `/doc/` HTML representation; `/data/` machine-readable. Bu üçleme content negotiation'ı temiz ayırır.
- Wikidata `/entity/Q123` kullanıyor ama Wikidata'nın evrensel domain'i var; biz domain-specific olduğumuz için `/entity/` redundant ("islamicatlas.org/entity/" zaten domain entity'si demek).
- Pleiades `/places/{id}` namespace-prefix kullanıyor; bu pattern domain-specific siteler için yaygın ama 13+ namespace açıldığında `/places/`, `/persons/`, `/dynasties/`, `/sources/`, `/events/`... nahoş pluralization gerektirir.
- `/id/` path prefix tek seçim olarak geleceğe dayanıklı.

**Reject:**
- `/entity/`: redundant.
- `/{namespace}/` (no `id` prefix): content negotiation pattern'iyle çakışır.
- `/resource/` (DBpedia tarzı): "resource" terimi RDF jargonudur, akademik kullanıcı için opaque.

### 1.4 Versioning: query string mi Memento mu?

**Karar: Phase 0'da query string (`?v=`); Memento Phase 4'e.**

**Gerekçe:**
- Query string pattern (`?v=v0.1.0`) statik dosya servisinde çalışır (Phase 2 öncesi infra ile uyumlu); cache-friendly; tüm tarayıcılarda tıklanabilir.
- Memento (RFC 7089) akademik olarak doğru ama HTTP header negotiation gerektirir (Apache/nginx config + content router); Phase 2 API katmanında daha doğal yaşar.
- Query string pattern Memento'yu engellemez — Phase 4'te `Accept-Datetime` header support eklendiğinde her iki mekanizma paralel çalışabilir (URI uzayı çakışmıyor).

**Reject (şimdilik):**
- Memento'yu Phase 0'da implementasyon: solo modda overengineering.

### 1.5 Arapça transliterasyon: DİN 31635 mi ALA-LC mi?

**Karar: ALA-LC (Library of Congress romanization), simplified ASCII slug için; full transliteration `transliteration` field'ında saklanır.**

**Gerekçe:**
- **OpenITI alignment:** Çetinkaya'nın enrichment pipeline'ı OpenITI URI'leri üzerinden çalışıyor; OpenITI ALA-LC kullanıyor. Aynı standart = ileride otomatik xref daha kolay.
- **DİN 31635** Almanca akademik geleneğe (Brockelmann, EI3) uygun; ama tabakat.io / GAS pipeline'ları ALA-LC'ye yatık.
- **Pratik gözlem:** Slug'da diakritikler düşer (`ḥ` → `h`, `ʿ` → düşer, `ā` → `a`). Çoğu kelimede DİN ile ALA-LC slug çıktısı aynı (`Halab`/`Aleppo`/`Damashq`). Fark sadece full transliteration field'ında görünür.

**Implementation:**
- `multilingual_text.schema.json` `transliteration` field'ı: full ALA-LC form (`ḥalab`).
- Slug generation: ALA-LC'den diakritik strip + lowercase.
- `original_script` field'ı (`حلب`) korunur.

**Reject:**
- DİN 31635: OpenITI alignment kaybı.
- IJMES (Brill): yaygın ama akademik dergilerin redaktör tercih varyantı; standardize edilmiş bir digital pipeline'ı yok.

---

## 4. Consequences

### Pozitif

- **Citation stability:** `iac:place-00012345` 100 yıl sonra hâlâ aynı entity'ye işaret edecek (immutable PID guarantee).
- **Pelagios uyumu:** w3id URI + Pleiades reconciliation kombinasyonu gazetteer'ı Pelagios indexer'larında görünür kılar.
- **Domain-failure resilience:** `islamicatlas.org` düşse w3id mirror canlı kalır.
- **OpenITI ile pipeline-level uyum** (ALA-LC kararının somut faydası).

### Negatif / kabul edilen risk

- **Slug collision yönetimi karmaşık:** `aleppo` üç farklı yer (Suriye Halep, Pakistan Halep, Texas Halep) olabilir. Discriminator suffix mekanizması ek complexity getiriyor; manual resolution queue gerekecek.
- **Slug değişikliği = URI değişikliği:** Bir entity'nin prefLabel'ı düzeltilirse slug değişir → public URI değişir. Mitigation: PID katmanı zaten immutable; slug değişikliklerinde 301 redirect zorunluluğu (Phase 1 resolver'da implementasyon kuralı).
- **W3id PR onay süresi:** Hafta 6'da atılan PR'ın Hafta 8 release'ine yetişmemesi riski (`v0.1.0` URI'lerinin geçici olarak sadece `islamicatlas.org/id/...` ile çalışması). Mitigation: dual-publish (URI'ler hem her iki forma da yazılır; resolver hangisi canlıysa onu kullanır).
- **Content negotiation Phase 2'ye ertelendi:** Phase 0 release'inde URL'ler "ölü görünür" — JSON-LD dump var ama `/id/place/aleppo` resolve etmez. Paper'da bu bir sınırlama olarak raporlanır.

### İzlenecek metrikler

- Hafta 6 sonu: w3id PR durumu (open/merged/rejected).
- Hafta 8 sonu: `iac-place-*.json` dosyalarının `@id`'lerinin %100'ü hem internal PID'i (`iac:place-...`) hem public URI'yi (`https://islamicatlas.org/id/place/...`) içerir.
- v0.1.0 sonrası 6 ay: hiçbir PID değiştirilmemiş olmalı (`docs/reports/pid_stability_report.md`).

---

## 5. Implementation checklist (Hafta 1-2)

- [ ] `pipelines/utils/pid_generator.py` — deterministic PID assignment + counter persistence (`data/_counters/{namespace}.txt`).
- [ ] `pipelines/utils/slug_generator.py` — ALA-LC simplified + collision detection.
- [ ] `pipelines/utils/uri_builder.py` — URI üçlemesi üreten yardımcı.
- [ ] `schemas/_common/identifiers.schema.json` (opsiyonel — alt schema).
- [ ] Test fixtures: collision case'leri (`aleppo` × 3 farklı kayıt).
- [ ] Hafta 6: w3id PR template hazırlığı (`docs/architecture/w3id-pr-template.md`).

---

## 6. References

- Berners-Lee, T. (2008). [Cool URIs for the Semantic Web](https://www.w3.org/TR/cooluris/). W3C Interest Group Note.
- Sanderson, R. et al. (2013). [Memento Framework](https://datatracker.ietf.org/doc/html/rfc7089). RFC 7089.
- W3C Permanent Identifier Community Group. [w3id.org Setup](https://w3id.org/).
- Pleiades. [URI Pattern Documentation](https://pleiades.stoa.org/help/conceptual-overview).
- Library of Congress. [ALA-LC Romanization Tables](https://www.loc.gov/catdir/cpso/roman.html).
- OpenITI. [Naming Convention](https://openiti.org/).

---

**Versiyon:** 1.0 (Accepted)
**Son güncelleme:** 03 Mayıs 2026

---

## 7. Update Note v1.1 — Search-First Refactor (03 May 2026)

ADR-005 (Unified Entity Catalog) bu ADR'in bağlayıcı tamamlayıcısıdır. ADR-005, namespace listesini somutlaştırır:

- **P0 aktif:** `place`, `dynasty`
- **P0.2 aktif:** `person`, `work`
- **P0.3 aktif:** `manuscript`, `event`
- **P1 forward-declared:** `institution`, `concept`, `route`

Yukarıdaki §2'de geçen "place, dynasty, person, source, event, monument, ..." nominal liste idi; ADR-005 ile final ve sürüm-bağımlı hâle gelir. URI regex `^iac:[a-z]+-[0-9]{8}$` ve PID minter algoritması değişmedi — bu update yalnızca aktive edilmiş namespace setini netleştirir.

`source` namespace'i ADR-005'te `work` namespace'ine birleştirildi: bibliografik kaynaklar (Bosworth NID, Yâqūt Mu'cem, OpenITI) `iac:work-NNNNNNNN` PID'leriyle modellenir; `provenance.derived_from[].source_id` field'ı P0.2'den itibaren CURIE string'leri yerine work PID referanslarına geçer.

`monument` namespace'i ADR-005'te `institution` (P1) ve `place` arasında split edildi (madrasa/mosque/tekke → institution; surlar/kapılar/çeşmeler → place subtype'ı olarak P0.4'te eklenecek).
