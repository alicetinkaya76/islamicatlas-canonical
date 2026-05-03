# ADR-004: Search-First Architecture

**Status:** Accepted (autonomous resolution; subject to maintainer override)
**Date:** 2026-05-03
**Phase:** 0
**Supersedes:** —
**Related:** ADR-001 (URI scheme), ADR-005 (Unified Catalog), ADR-006 (Adapter pattern), ADR-007 (Entity page contract)

---

## Bağlam

islamicatlas.org'un mevcut hâli **katman odaklı**: Yâqūt katmanı, Le Strange katmanı, Makdisî katmanı, Evliya katmanı, Salibiyyat, Bosworth, Konya City Atlas, DarpIslam, Science Layer, Ibn Battuta panel. Her katman kendi içinde zengin (3D harita, timeline, network görselleştirmesi), ama **çapraz arama yok**: "Sayf al-Dawla" araması Wikidata'da çıkar ama sitenin kendisinde Hamdânid kaydını + Halep'i + ona referans veren kaynakları + onun döneminde aktif şair-âlimleri tek bir sonuç sayfasında getiremez.

Yeni vizyon: **birinci sınıf etkileşim modu = arama**. Kullanıcı bir tek arama çubuğuna yazar; sonuçlar place/dynasty/person/work/manuscript/event tiplerinden federe gelir; her sonuç tıklandığında **rich entity page** açılır (harita + timeline + ilişki ağı + kaynak alıntıları + cross-layer görünümler). Mevcut katman zenginliği kaybolmaz — facet hâline gelir (`source_layer:yaqut`, `source_layer:evliya`).

Bu ADR şu kararları verir: (1) hangi search engine, (2) collection/index modeli, (3) çok-dilli analyzer stratejisi, (4) facet taksonomisi, (5) ranking sinyalleri, (6) geo-search modeli, (7) re-index stratejisi.

---

## Karar 4.1: Search engine = Typesense

**Karar:** Search backend olarak **Typesense** (Apache 2.0, self-hosted) seçilir.

**Değerlendirilen alternatifler ve ret gerekçeleri:**

| Aday | Lehine | Aleyhine | Sonuç |
|------|--------|----------|-------|
| **Typesense** | Native geo-search (radius/bbox), güçlü facet'leme, açık Arapça analyzer config, schema-first (mimarimizle eşleşir), vector search hazır (semantik genişletme için), tek-binary ops | Genç ekosistem (ama 60k entity ölçeğinde sorun değil) | **SEÇİLDİ** |
| Meilisearch | Mükemmel typo toleransı, basit ops | Schemaless (mimarimizle çelişir), geo-search daha az olgun, facet'leme daha zayıf | Reddedildi |
| OpenSearch / Elasticsearch | En güçlü query DSL, en olgun Arapça analyzer'lar (icu, kuromoji benzeri) | JVM, RAM-yoğun, solo-ops için ağır, 60k için aşırı | Reddedildi |
| Algolia | En iyi sonuç kalitesi, sıfır ops | Kapalı kaynak vendor lock-in, traffic ile orantılı maliyet, kütüphane sahipliğine ters | Reddedildi |
| Pagefind | Statik, sunucusuz | Yapısal entity araması yerine markdown sayfası araması için tasarlanmış; facet/geo yok | Reddedildi |
| Postgres FTS / SQLite FTS5 | Tek veritabanı, sıfır ek altyapı | Çok dilli analyzer zayıf, fuzzy/typo toleransı yok düzeyde, facet'leme yavaş | Reddedildi |

**Gerekçeyi destekleyen üç somut senaryo:**

1. **"Halep'in 200 km çevresindeki şehirler"** — Typesense `_geopoints` field tipi ile native, tek query. Meilisearch yeni eklendi ama radius+facet kombinasyonu eksik. Postgres'te PostGIS gerekir. Typesense kazanıyor.

2. **"Halab" yazılınca "Aleppo / Halep / Ḥalab" hepsinin gelmesi** — Typesense per-field analyzer + ALA-LC translit field'ları + multi-field ranking. Konfigüre edilebilir typo toleransı (`num_typos: 2` Arapça için, `num_typos: 1` İngilizce için).

3. **"Sayf al-Dawla → Hamdânîler → Halep"** — Search document'ta denormalize edilmiş ilişki etiketleri (her person doc'unda mensup olduğu dynasty'lerin prefLabel'ları string array olarak). Bu sayede tek query "Sayf al-Dawla" çağırınca hem person hem dynasty hem place sonucu skorlanabilir.

**Versiyonu:** Typesense ≥ 27.0 (2025-Q4'te çıkan sürüm; vector + geo + multi-search kombinasyonu için minimum).

**Dağıtım modeli:** Tek instance, Docker, persistent volume. Production için 3-node cluster Phase 1'de. Dev/CI için in-memory mode (`TYPESENSE_DATA_DIR=/tmp/...`).

---

## Karar 4.2: Tek collection, entity_type discriminator

**Karar:** Tüm entity tipleri **tek bir collection** (`iac_entities`) içinde indekslenir. `entity_type` field'ı (place|dynasty|person|work|manuscript|event) discriminator görevi görür.

**Alternatif (reddedildi):** Her tip için ayrı collection (`iac_places`, `iac_dynasties`, ...), `multi_search` ile federe.

**Tek collection lehine:**

- **Birleşik arama:** Kullanıcı "Bağdat" yazınca place + dynasty + person + work hepsinden sonuç gelir — tek query, tek skoru, tutarlı ranking. Multi-search'te collection-arası skor normalizasyonu manuel iş.
- **Ortak facet'ler:** `century_ce`, `source_layer`, `iqlim`, `language` — bunlar tüm entity tiplerinde geçerli, tek collection'da tek facet config.
- **Cross-type ilişkiler:** Bir search doc'unda denormalize edilmiş ilişki etiketleri (örn. person doc'unda `affiliated_dynasties: [...]`) sayesinde "Sayf al-Dawla" araması Hamdânîler'i de yukarı çeker.

**Tek collection aleyhine (kabul edilen risk):**

- Schema 50+ field'a ulaşır (her tipin kendi field'ları opsiyonel olarak eklendiğinde). Typesense default field limiti 150, sorun değil ama monitoring lazım.
- Type-spesifik ranking ayarları (örn. dynasty için `start_year_ce` recency bonus, place için `population_estimate` boost) tek collection'da if/else yerine query-time dinamik sort kombinasyonlarıyla yapılır.

---

## Karar 4.3: Çok-dilli analyzer stratejisi — 3 dil × translit

**Karar:** Her metinsel field 4 varyantta indekslenir: `<field>_ar` (Arapça orijinal), `<field>_tr` (Türkçe), `<field>_en` (İngilizce), `<field>_translit` (ALA-LC romanize). Query default'ta 4'üne paralel atılır, ranking field-boost ile ayarlanır.

**Ayrıntı:**

- `prefLabel_ar` — Typesense `locale: "ar"` ile Arapça normalizasyon (alif variants, ta marbūṭa, hamza pozisyonu)
- `prefLabel_tr` — `locale: "tr"` (Türkçe i/ı, dotless I)
- `prefLabel_en` — `locale: "en"` default
- `prefLabel_translit` — diakritiksiz ALA-LC ASCII'ye düşürülmüş forma (`Halab` from `Ḥalab`); 1-typo tolerance ile alfa-numerik fuzzy

**Query-time davranış:**

```
q=halab → 
  prefLabel_translit: exact match → score boost ×3
  prefLabel_en: prefix match "halab" → score ×1.5
  prefLabel_ar: ASCII'den Arapça'ya transliterate edilmez (otomatik translit risk)
  altLabel_translit: match → ×1
```

**Sınır durumu:** Karışık-script query (örn. "Halep حلب") split edilir, her parça uygun field'a yönlendirilir. Bu Phase 0.2'de — Phase 0'da tek-script query default.

---

## Karar 4.4: Facet taksonomisi — kademeli

**Karar:** Facet'ler iki katmanda tanımlanır: (a) **global facet'ler** tüm entity tiplerinde geçerli, (b) **type-specific facet'ler** sadece o tip seçildiğinde gösterilir.

**Global facet'ler:**

| Facet | Tip | Kaynak | Açıklama |
|-------|-----|--------|----------|
| `entity_type` | enum | doğrudan | place / dynasty / person / work / manuscript / event |
| `century_ce` | int (bucketed) | temporal'dan türetilir | -5..21; "5th c." gibi etiketlenir |
| `century_ah` | int (bucketed) | temporal'dan türetilir | 1..15 |
| `iqlim` | string array | place: falls_within_iqlim; dynasty: territory; person/work: place_of_origin → iqlim | Khurāsān, Andalus, Shām, Mağrib, Mısır, Hicaz, Yemen, Irak, Cezîre, Rûm |
| `source_layer` | string array | provenance.derived_from'dan türetilir | yaqut, le-strange, makdisi, bosworth, evliya-celebi, ibn-battuta, salibiyyat, darp-islam, konya-city-atlas, science-layer, manual |
| `language` | string array | labels'tan + work language'tan | ar, fa, ota, tr, en, la (sadece kayıtlı diller) |
| `has_coords` | bool | coords field varlığı | mappable filtering |
| `has_wikidata` | bool | authority_xref'te wikidata varlığı | reconciliation status |

**Type-specific facet'ler:**

- **Place:** `place_subtype` (settlement/region/iqlim), `modern_country` (Phase 0.3'te eklenecek)
- **Dynasty:** `dynasty_subtype` (caliphate/sultanate/emirate/imamate/beylik), `predecessor_count`
- **Person:** `profession` (scholar/ruler/narrator/poet/...), `madhab`, `tariqa` (P0.2)
- **Work:** `genre` (fiqh/hadith/tarikh/edebiyat/coğrafya/...), `original_language`
- **Manuscript:** `library` (Süleymaniye/BnF/British Library/...), `dating_century`
- **Event:** `event_type` (battle/treaty/founding/conference/...)

Facet listesi `search/facets.yaml`'da tutulur, UI bunu okur — UI'a hardcode edilmez.

---

## Karar 4.5: Ranking sinyalleri

**Karar:** Default ranking aşağıdaki sinyallerin lineer kombinasyonu:

```
score = 
    query_match × 1.0          # Typesense BM25 + typo penalty
  + prefLabel_match × 2.0      # exact/prefix prefLabel match boost
  + has_wikidata × 0.3         # reconciliation güveni
  + has_coords × 0.2           # mappable entity tercihi
  + capital_status × 0.5       # had_capital_of != [] olan place'lere boost
  + manual_curation_bonus × 0.4 # provenance.derived_from has manual_editorial
  - deprecated_penalty × 100   # deprecated kayıtlar dipte
```

Query-time `sort_by` parametresiyle override edilebilir (örn. "tarihçe sırala" için `start_year_ce:asc`).

**Tie-breaker:** Eşit skorlu sonuçlarda en yeni `provenance.modified` ilk gelir (taze kayıt görünürlüğü).

---

## Karar 4.6: Geo-search modeli

**Karar:** Place tipindeki entity'ler `coords.lat`, `coords.lon` field'ından `_geo: [lat, lon]` field'ına projecte edilir; Typesense `_geo` filter ve sort native destekler.

Dynasty tipindeki entity'ler **hem** `had_capital[].place`'in coordinatları olarak (capital array) **hem de** `territory[]` üzerinden hesaplanan bbox merkezi olarak indekslenir. Bu sayede:

- "Bağdat'tan 200 km içindeki dynasty'ler" → capital coords filter
- "Khurāsān'da tarihte hüküm sürmüş dynasty'ler" → territory bbox containment

Person tipindeki entity'ler P0.2'de `birth_place`, `death_place`, `active_in[]` üzerinden noktalar — life-trajectory polyline değil (Phase 1+).

Manuscript tipindeki entity'ler `current_library` coordinatından (Süleymaniye, BnF vb.) noktalar.

---

## Karar 4.7: Re-index stratejisi

**Karar:** **İki-aşamalı**: (a) full reindex pipeline, (b) per-entity incremental update.

- **Full reindex** (`pipelines/search/full_reindex.py`): tüm `data/canonical/*` taranır, her kayıt `search/projector.py` ile search doc'a dönüştürülür, Typesense'e batch upload edilir (1000 doc/batch). v0.1.0 release pipeline'ında zorunlu.
- **Incremental update** (`pipelines/search/upsert.py`): bir adapter veya editorial fix sonrasında değişen kayıtlar için tekil PUT/DELETE. Ad-hoc geliştirme döngüsünde kullanılır.

**Idempotency:** search doc'ların Typesense ID'si kanonikal `@id` (örn. `"id": "iac:place-00000042"`). Aynı ID için PUT replace; hash farkı yoksa Typesense no-op.

**Reindex tetikleyicisi:** `search/projections/<type>.yaml` veya `search/typesense_collection.schema.json` değiştiğinde **alias-swap** ile sıfır-downtime reindex (Phase 1 production). Phase 0'da sadece full reindex kabul edilir.

---

## Sonuçlar

**Pozitif:**

- Tek search bar, tüm entity tipleri arası federe arama.
- Mevcut katman zenginliği (Yâqūt, Le Strange, Makdisî, Evliya, Bosworth, ...) `source_layer` facet'i olarak görünür kalır.
- Yeni içerik (yeni kitap, yeni adapter) eklenince re-index dışında search code değişmez.
- Vector search hazır → "Mu'jam'a benzer entry'ler" tarzı semantik aramalar P0.3'te eklenebilir.
- Self-hosted, vendor lock-in yok, CC-BY-SA dump'ı için külliyat üretilebilir.

**Negatif (kabul edilen):**

- Typesense Tek Instance Phase 0'da single point of failure. Phase 1'de cluster.
- Çok-dilli analyzer stack tuning gerektirir (Arapça normalizasyon hassas).
- Tek collection büyüdükçe (P1+ 200k+ entity) field count monitoring lazım.
- Translit field'ı index boyutunu ~%25 büyütür.

**Yeniden gözden geçirme:** Phase 0.3 sonunda. Vector search sertifiksyonu, Arapça analyzer kalite metrikleri (precision@10), ve 200k entity'de query latency p95 ölçülür. Eğer Typesense yetmezse OpenSearch'e geçiş yolları planlanır (search projector engine-agnostic tasarlandığı için yer değişimi sınırlı kapsamlı bir iş).

---

## Atıflar

- Typesense documentation: https://typesense.org/docs/
- ALA-LC Arabic Romanization: https://www.loc.gov/catdir/cpso/romanization/arabic.pdf
- BM25 ranking: Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond" (2009)
- ADR-001 (URI scheme), ADR-005 (Unified Catalog), ADR-006 (Adapter pattern), ADR-007 (Entity page contract)
