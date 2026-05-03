# ADR-007: Rich Entity Page Contract

**Status:** Accepted (autonomous resolution; subject to maintainer override)
**Date:** 2026-05-03
**Phase:** 0
**Supersedes:** —
**Related:** ADR-004 (Search-first), ADR-005 (Unified Catalog)

---

## Bağlam

Search-first vizyonun ikinci kanadı: arama sonucundan tıklanan her entity, **zengin bir entity sayfasıyla** açılır. Mevcut islamicatlas.org'un katman zenginliği (3D harita, timeline, network) tek-bir-entity ölçeğine indirgenir ama kaybolmaz: bir Place sayfası harita + zaman çizelgesi + ilişki grafiği + kaynak alıntıları + cross-layer mention'lar gösterir.

Bu sayfaların **hardcode edilmemesi** kritik: yeni entity tipi eklediğinde (ADR-006 §6.4) o tipe özgü sayfa kodlamak istemeyiz. Onun yerine: her entity tipinin bir **page recipe**'si olur (hangi section'lar, hangi sırada, hangi field'dan beslenecek), UI bu recipe'yi okur ve generic component'larla render eder.

Bu ADR şu kararları verir: (1) section envanteri, (2) per-entity-type page recipe contract, (3) section-component map (UI tarafına teslim), (4) i18n stratejisi, (5) responsive breakpoint'ler.

---

## Karar 7.1: Section envanteri

**Karar:** Tüm entity sayfaları aşağıdaki **9 section'dan biraz veya tamamı** ile compose olur. Her section bir bağımsız UI component — tüm entity tipleri aynı component'leri paylaşır.

| Section | Slug | Purpose | Hangi entity tiplerinde varsayılan |
|---------|------|---------|------------------------------------|
| **Header** | `header` | prefLabel + altLabel + transliteration + dil değiştirici + entity_type badge | Hepsi |
| **Quick Facts** | `quick_facts` | Yan-bar key-value: dates, type, primary subtype, authority QID/PID | Hepsi |
| **Map** | `map` | Leaflet/MapLibre, point veya bbox | Place, Dynasty (capitals), Manuscript (current library), Event (location) |
| **Timeline** | `timeline` | Yatay kronoloji (D3 veya vis.js) | Dynasty (rulers), Person (life events), Work (composition + copies), Event (single point) |
| **Relations** | `relations` | İlişki grafiği (Cytoscape.js) — predecessor/successor/affiliated/cited | Hepsi (ama içerik tipe göre farklı) |
| **Sources** | `sources` | Bibliografik alıntılar (provenance.derived_from'dan) | Hepsi |
| **Cross-references** | `cross_refs` | Bu entity'nin diğer layer'larda nasıl göründüğü (Yâqūt'ta var, Le Strange'ta var, Evliya'da geçer...) | Hepsi |
| **Authority Links** | `authority_links` | Wikidata, Pleiades, VIAF, GeoNames buton dizisi | Hepsi (var olduğu kadar) |
| **Editorial Notes** | `editorial` | Markdown-rendered editorial commentary | Hepsi (opsiyonel) |

**Negatif scope:** Aşağıdaki section'lar Phase 0'da YOK — sonraki phase'lere bırakıldı:

- **Discussion / comments** (Phase 2 — community feature)
- **Edit history viewer** (Phase 1 — direkt git log'una link)
- **Citation generator** (BibTeX, RIS) (Phase 1)
- **Embed widget** (Phase 2)
- **Print view** (Phase 1)

---

## Karar 7.2: Page recipe contract

**Karar:** Her entity tipi için bir **page recipe schema** dosyası vardır: `ui_contract/entity_pages/<type>.schema.json`. Bu dosya o tipin sayfasında hangi section'ların hangi sırada, hangi konfigürasyonla render edileceğini belirtir.

**Örnek (place):**

```json
{
  "entity_type": "place",
  "sections": [
    {"id": "header", "order": 1, "config": {"show_subtype_badge": true}},
    {"id": "quick_facts", "order": 2, "config": {
      "fields": ["coords", "located_in", "falls_within_iqlim", "had_capital_of", "yaqut_id"]
    }},
    {"id": "map", "order": 3, "config": {
      "layer_style": "ottoman-historical",
      "show_neighbors_within_km": 50,
      "default_zoom": 8
    }},
    {"id": "timeline", "order": 4, "config": {
      "events_source": "cross_refs",
      "filter_by": "place_pid"
    }},
    {"id": "relations", "order": 5, "config": {
      "graph_layout": "force-directed",
      "show_dynasty_capitals": true,
      "show_predecessor_successor_chain": true
    }},
    {"id": "sources", "order": 6},
    {"id": "cross_refs", "order": 7, "config": {
      "layers_priority": ["yaqut", "le-strange", "makdisi", "evliya-celebi", "ibn-battuta"]
    }},
    {"id": "authority_links", "order": 8},
    {"id": "editorial", "order": 9, "render_only_if_present": true}
  ]
}
```

**Recipe'nin avantajı:**

- UI generic component'leri çağırır; "place sayfası" hardcode'lanmaz.
- Yeni entity tipi eklendiğinde (örn. `fatwa`) bir page recipe yazılır, UI kodu değişmez.
- A/B test: aynı entity tipi için iki recipe (örn. "deneysel: relations önce, map sonra") kolayca denenir.
- Power user override (URL parametresi `?recipe=experimental`).

---

## Karar 7.3: Section-component map (UI tarafı)

**Karar:** UI tarafı (mevcut islamicatlas.org SPA'sı veya yeni Next.js front-end) aşağıdaki component map'ini implemente eder:

| Section ID | Beklenen component (örn. React) | Beklenen prop'lar |
|------------|---------------------------------|-------------------|
| `header` | `<EntityHeader>` | `labels`, `entity_type`, `subtypes`, `deprecated`, `current_lang` |
| `quick_facts` | `<QuickFactsSidebar>` | `fields_to_show`, `entity` |
| `map` | `<EntityMap>` | `coords` veya `coords_array`, `layer_style`, `default_zoom`, `additional_overlays` |
| `timeline` | `<EntityTimeline>` | `events`, `start_year`, `end_year`, `granularity` |
| `relations` | `<RelationsGraph>` | `nodes`, `edges`, `layout`, `clickable` |
| `sources` | `<SourcesList>` | `provenance.derived_from`, `citation_style` (default chicago) |
| `cross_refs` | `<CrossRefsList>` | `cross_refs_by_layer`, `layers_priority` |
| `authority_links` | `<AuthorityLinksRow>` | `authority_xref` |
| `editorial` | `<MarkdownNotes>` | `markdown_content`, `lang` |

**UI repo Phase 0 kapsamı dışında** — bu repo (islamicatlas-canonical) sadece **contract'ı** sağlar; implementation farklı bir repo'da (mevcut islamicatlas.org veya yeni front-end).

**Veri akışı:** UI bir entity sayfası açtığında:

1. Canonical record fetch (REST: `GET /api/v1/entity/{pid}`)
2. Page recipe fetch (`GET /api/v1/page-recipe/{entity_type}`)
3. Recipe'deki her section için ilgili component, ilgili config + entity verisiyle render edilir.

---

## Karar 7.4: i18n stratejisi

**Karar:** UI 3 dilde paralel render eder: **Türkçe (default), İngilizce, Arapça**. Dil değiştirici header'da; seçim localStorage + URL'de tutulur.

**Field-level davranış:**

- `labels.prefLabel.<lang>` mevcutsa → o dil
- mevcut değilse → fallback chain: TR → EN → AR → translit → "—"
- `labels.description.<lang>` benzer fallback
- Sayısal/tarih field'ları locale-formatted (Türkçe için "750/132 H./M.S.", İngilizce için "750 CE / 132 AH")
- Arapça arayüzde RTL mirror (Tailwind `dir-rtl` utility class'ları)

**Gelecek dil:** Farsça (P1), Ottomanca translitfor scholar audience (P1.5).

---

## Karar 7.5: Responsive breakpoint'ler

**Karar:** Üç breakpoint, mobil-first:

| Breakpoint | Layout |
|------------|--------|
| `<768px` (mobile) | Tek kolon dikey stack; sections tab'lı (örn. "Genel / Harita / Kaynaklar / İlişkiler") |
| `768-1280px` (tablet) | İki kolon: header tüm genişlik, sonra sol-ana / sağ-quick-facts |
| `>1280px` (desktop) | Üç kolon mümkün: sol nav, orta ana içerik, sağ quick facts. Map ve relations expand-to-full-screen butonları |

Bu page recipe'in dışında — UI implementation'ın işi. Bu ADR sadece UI'ya rehber olur.

---

## Sonuçlar

**Pozitif:**

- UI ile canonical store arasında temiz contract; UI yeniden yazılabilir, contract değişmez (örn. mevcut Three.js SPA'dan Next.js'e geçiş contract'ı bozmaz).
- Yeni entity tipi eklemek için UI kodu değişmez (yeni page recipe yeter).
- A/B testing, kişiselleştirilmiş recipe'ler kolay.
- Multi-lingual fallback davranışı tüm sayfa tiplerinde tutarlı.

**Negatif (kabul edilen):**

- Generic component'lerin tüm entity tiplerini kapsayabilecek esneklikte yazılması başlangıçta ekstra iş (UI tarafında).
- Entity-tipi-spesifik özel render (örn. dynasty rulers tablosu) bir custom section ile çözülür → "section catalog" ileride genişlemek zorunda.

**Yeniden gözden geçirme:** UI implementation Phase 1'in büyük parçası — page recipe'lerin ne ölçüde gerçekçi olduğu o sırada test edilir.

---

## Atıflar

- ADR-004 (Search-first), ADR-005 (Unified Catalog)
- Pattern Library (Atomic Design): https://atomicdesign.bradfrost.com/
- Pleiades site UX: https://pleiades.stoa.org/places/658381 (örnek entity sayfası referansı)
- World Historical Gazetteer entity pages: https://whgazetteer.org/places/portal/ (modern entity-page UX)
