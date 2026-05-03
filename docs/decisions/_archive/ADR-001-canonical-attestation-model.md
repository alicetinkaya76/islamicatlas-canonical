# ADR-001: Canonical Entity + Attestation Model

**Durum:** Proposed (ilk toplantıda onaylanacak)  
**Tarih:** 2026-04-21  
**Karar vericiler:** Ali Çetinkaya, Fatıma Zehra Nur Balcı  
**Etkilenen bileşenler:** tüm şema, ETL, API, uzun vadede frontend

---

## Context

Mevcut islamicatlas.org mimarisinde 13 veri katmanı birbirinden bağımsız entity ID uzaylarına sahip. "Bağdat" kavramı:

- Yâkût `yaqut_lite.json`'da: `{id: 789, h: "بغداد", ...}`
- Le Strange `le_strange_eastern_caliphate.json`'da: `{id: 42, name_ar: "بغداد", ...}`
- DİA `dia_lite.json`'da: `{id: "bagdat", t: "BAĞDAT", ...}`
- Salibiyyat olayları: `events[*].location: "Bagdat"` (string)
- Muqaddasî `muqaddasi_atlas_layer.json`'da: `{id: "muq_234", name: "Baghdad"}`

**Sorun:** Beş ayrı kayıt, beş ayrı ID uzayı, beş ayrı koordinat iddiası. Bunların aynı yer olduğu bilgisi ya hiç yok ya da manuel tutulan `*_xref.json` sözlüklerinde kısmen.

Bu mimari şu sınırları getiriyor:

- **Stable URI imkânsız** — hangi "Bağdat"ın URL'si? `yaqut/789` mi? `dia/bagdat` mı? Her biri farklı.
- **Entity-level citation imkânsız** — araştırmacı "islamicatlas'taki Bağdat kaydı" diye atıf veremiyor; çünkü o tek bir kayıt değil, beş kayıt.
- **Source ayrımı yok** — "Bağdat 33.33°N" kim diyor? Yâkût mu, Le Strange mi, modern geocoder mı? Ayırt edilemez.
- **Kaynaklar arası ihtilaf görünmez** — iki kaynak farklı koordinat verirse bunu gösterecek mekanizma yok.
- **Cross-ref kırılgan** — `dia_alam_xref.json` manuel bakımlı, tek yönlü, doğrulama yok.

Aynı sorun kişiler için de geçerli. El-Harezmî:
- Science Layer'da `scholar_0001`
- Muhtemelen al-Aʿlām'da farklı ID
- DİA'da `harizmi-muhammed` (slug)

## Decision

**Pleiades (eski dünya coğrafyası) ve Perseus/Syriaca (klasik ve Süryani filoloji) veri modellerinden uyarlanan "canonical entity + attestation" ayrımı kullanılacak.**

İki ayrı kayıt tipi var:

### 1. Canonical Entity
Değişmez, otoriter varlık. Tipleri: `Place`, `Person`, `Work`, `Event`, `Dynasty`, `Route`.

- Her birinin stable ID'si (`plc_baghdad`, `per_al_khwarizmi`)
- Her birinin stable URI'si (`https://islamicatlas.org/place/baghdad`)
- Kanonik bilgi taşır: **ama bu bilgi attestation'lardan türetilmiştir**, bağımsız bir "doğru" değildir
- `sameAs` ile Wikidata/VIAF/GeoNames'e linked
- Her biri 1..N attestation'a sahip

### 2. Attestation
Bir kanonik varlığın bir kaynakta geçişi.

- Bir `Place` ve bir `Source`'a bağlı
- O kaynakta ne dendiğini, hangi sayfada olduğunu, hangi koordinatı verdiğini taşır
- "Confidence" alanı: bu attestation'ın varlığa eşleştirilme güven skoru
- "Surface form" alanı: kaynakta geçen ham metin (normalize edilmemiş)

### Veri akışı

```
Legacy kayıt → ETL → Attestation oluşturulur
                  → Matching/ER → Attestation bir Canonical'a bağlanır (veya yeni Canonical üretir)
                  → Canonical'ın konsolide alanları güncellenir (koordinat = attestation'ların medianı, vb.)
```

### Örnek: Bağdat'ın canonical temsili

```json
// plc_baghdad.json (canonical)
{
  "id": "plc_baghdad",
  "slug": "baghdad",
  "names": {"tr": "Bağdat", "en": "Baghdad", "ar": "بغداد"},
  "place_type": ["city", "capital"],
  "geography": {
    "canonical_coordinates": {
      "lat": 33.3152, "lon": 44.3661,
      "source": "modern_geocoder"
    }
  },
  "sameAs": {
    "wikidata": "Q1530",
    "geonames": "98182"
  },
  "attestations": [
    "att_yaqut_baghdad_v1_p456",
    "att_lestrange_baghdad_ch02",
    "att_dia_baghdad",
    "att_muqaddasi_baghdad_p120",
    "att_salibiyyat_event_1258"
  ],
  "legacy_ids": {
    "yaqut_id": 789,
    "le_strange_id": 42,
    "dia_id": "bagdat",
    "muqaddasi_id": "muq_234"
  }
}

// att_yaqut_baghdad_v1_p456.json (attestation)
{
  "id": "att_yaqut_baghdad_v1_p456",
  "source_id": "src_yaqut_mujam",
  "entity_type": "place",
  "entity_id": "plc_baghdad",
  "locator": {"volume": 1, "page_start": 456},
  "surface_form": {
    "original_script": "بغداد",
    "translit": "Baghdād",
    "context": "Yâkût burayı, Dicle üzerinde, halifelerin başkenti olarak tanımlar..."
  },
  "assertions": {
    "coordinates": {"lat": 33.33, "lon": 44.40, "method": "stated"}
  },
  "confidence": {
    "match_score": 0.98,
    "verification_status": "human_verified"
  }
}
```

## Alternatives Considered

### Alternative A: Tek tablo, multiple sources columns

Her `Place` kaydı `yaqut_source_id`, `lestrange_source_id`, `dia_id` gibi sabit alanlar taşır.

- **Artıları:** Basit, bildiğimiz relational pattern. SQL sorguları kolay.
- **Eksileri:**
  - Yeni kaynak eklemek schema migration gerektirir (genişleyemez)
  - Attestation metadata (sayfa, bağlam, confidence) nereye konacak?
  - Aynı kaynaktan aynı entity'ye birden fazla mention modellenemez (tek satır sınırı)
- **Neden seçilmedi:** Akademik tool olmanın temel gereksinimi — source-level provenance — modellenemez.

### Alternative B: Triple store (RDF) + SPARQL

Her bilgi kırıntısı RDF triple olarak saklanır: `(plc_baghdad, yaqut:mentioned_in, yaqut:vol1_p456)`.

- **Artıları:** Maksimum esneklik, native LOD
- **Eksileri:**
  - Tool zinciri (Apache Jena, Virtuoso) bizim ekibimize göre ağır
  - Operational cost yüksek
  - Phase 0 için fazla iddialı
  - Fatıma'nın skill set'inin dışında
- **Neden seçilmedi:** Phase 0 için yanlış zamanlama. **RDF export**'u Phase 2'de eklenir (JSON-LD zaten aldığımız).

### Alternative C: Mevcut xref dosyalarının geliştirilmesi

Mevcut `dia_alam_xref.json` gibi dosyaları iki yönlü ve güven skorlu hale getirmek — canonical entity üretmeden.

- **Artıları:** Minimal değişiklik
- **Eksileri:**
  - Her katman yine bağımsız — "Bağdat"ın URI'si yok
  - Citation sorunu çözülmüyor
  - Ihtilaf görselleştirmesi için ek adapter katmanı gerekir
- **Neden seçilmedi:** Mevcut sorunun kökünü çözmez, üstüne yama atar.

## Consequences

### Olumlu

- **Stable URI mümkün:** `/place/baghdad`, `/person/al-khwarizmi` gerçekten anlamlı
- **Entity-level citation:** her entity sayfasında "cite this" çalışır
- **Source transparency:** her bilgi kırıntısının kaynağı görünür
- **Ihtilaf modellenebilir:** aynı entity için birden fazla kaynağın farklı iddiaları yan yana gösterilebilir
- **LOD-ready:** `sameAs` ile Wikidata'ya bağlanmak mimari olarak doğal
- **Yeni kaynak ekleme kolay:** schema migration gerekmez, yeni Source + Attestation'lar
- **Akademik peer review'a dayanıklı:** provenance zinciri tam

### Olumsuz / Tradeoff'lar

- **Sorgu karmaşıklığı artar:** "Bağdat'ın koordinatları" demek için canonical tabloya, "Bağdat'ı Yâkût ne diyor?" demek için attestation join gerekir
- **Storage overhead:** 58K entity + 100K+ attestation beklenir. PostgreSQL için sorun değil, ama CPU/disk artar
- **ER komplikasyonu:** attestation → canonical eşleştirme doğruluğu kritik. Yanlış eşleştirme canonical'ı kirletir
- **Migration non-trivial:** mevcut 13 katman için ETL yazılması gerekiyor (Week 5)
- **Frontend'in bilmesi gereken şema sayısı artar** — ama Phase 0'da frontend dokunulmadığı için Phase 1'e ertelenir

### Neutral / Gelecekte revizyon gerektirebilir

- **Attestation granularity:** Bir Source'un içinde her mention bir attestation mı, yoksa bir entry (madde) bir attestation mı? Şu an "bir entry = bir attestation". Manuscript IIIF eklendiğinde bu revise edilebilir.
- **Canonical coordinates seçim mantığı:** Birden fazla kaynak farklı koordinat verirse median? En yüksek reliability_tier'den mi? ADR-006 (gelecek) bunu çözecek.
- **Person vs Work ayrımı:** Bir müellif ve eseri aynı entity mi? Farklı. `per_tabari` ve `wrk_tabari_tarikh` ayrı kayıtlardır, ilişki `Person.works` → `[wrk_tabari_tarikh]`.

## References

- Pleiades Conceptual Overview: https://pleiades.stoa.org/help/conceptual-overview
- Perseus Digital Library — about and citation conventions
- CIDOC-CRM spec (özellikle E13 Attribute Assignment, E31 Document)
- Syriaca.org — The Syriac Reference Portal — attestation model örneği
- Winkler, W. E. (2006). "Overview of Record Linkage and Current Research Directions"
- İlgili issue: #001 (açılacak)

---

**Revisyon geçmişi:**
- 2026-04-21: İlk sürüm, Ali Çetinkaya
- [toplantı tarihi]: Toplantı sonrası revizyon (varsa)
