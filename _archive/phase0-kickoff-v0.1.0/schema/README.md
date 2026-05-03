# Canonical Schema

Phase 0 kapsamında tasarlanan kanonik veri modelleri. Referans: **Pleiades** (yerler), **Perseus/Syriaca** (kişiler), **CIDOC-CRM** (kültürel miras ontolojisi).

## Temel model

```
          Source              Person
            ▲                    │
            │                    │ participates_in
            │              ┌─────┼─────┐
    ┌──── attests ─────┐   ▼     ▼     ▼
    │       │          │  Event  Work  Dynasty
    ▼       ▼          ▼
  Place   Person    Work/Event...
```

**Anahtar kuralı:** Kanonik varlık (Place/Person/Work/Event/Dynasty) bilgisi doğrudan taşımaz — bilgi **Attestation**'lardan gelir. Canonical kayıt, attestation'ların birleştirilmiş (reconciled) hâlidir.

## Şema dosyaları

| Varlık | Dosya | Prefix | Örnek ID |
|---|---|---|---|
| Place | `place.schema.json` | `plc_` | `plc_baghdad`, `plc_konya` |
| Person | `person.schema.json` | `per_` | `per_al_khwarizmi`, `per_ibn_sina` |
| Work | `work.schema.json` | `wrk_` | `wrk_muqaddima`, `wrk_kitab_al_shifa` |
| Event | `event.schema.json` | `evt_` | `evt_battle_manzikert_1071` |
| Dynasty | `dynasty.schema.json` | `dyn_` | `dyn_umayyad`, `dyn_seljuk_great` |
| Route | `route.schema.json` | `rte_` | `rte_silk_road_main` |
| Source | `source.schema.json` | `src_` | `src_yaqut_mujam` |
| Attestation | `attestation.schema.json` | `att_` | `att_yaqut_baghdad_v1_p456` |

## URI şeması

Her varlık üç adreslenebilirlik seviyesi taşır:

1. **HTTP URI (dereferenceable)** — `https://islamicatlas.org/place/baghdad`
2. **Canonical ID** — `plc_baghdad` (API payload'larında)
3. **JSON-LD `@id`** — `https://islamicatlas.org/id/plc_baghdad`

## Attestation modelinin önemi

Mevcut mimaride "Bağdat" hem Yâkût'ta, hem Le Strange'de, hem DİA'da, hem Salibiyyat olaylarında **dört ayrı kayıt** olarak bulunuyor. Canonical modelde:

- **1 `Place` kaydı:** `plc_baghdad`
- **N `Attestation` kaydı:** her kaynağa bir tane — Yâkût'un verdiği koordinat, Le Strange'in notu, DİA'nın makale referansı, Salibiyyat olayları.

Bu ayrım sayesinde:
- Kaynaklar arası **ihtilaf** görünür olur (Yâkût X koordinatı der, Le Strange Y der).
- **Entity-level citation** mümkündür — araştırmacı `/place/baghdad` sayfasını atıf gösterdiğinde, altta hangi kaynaklardan beslendiği bellidir.
- **Attestation provenance** ile zaman damgalı veri izlenir: "Mart 2026'da şöyleydi, Nisan'da güncellendi."

## Doğrulama

JSON Schema draft-07 kullanılıyor. Python ile doğrulama:

```python
import json
from jsonschema import validate, Draft7Validator

schema = json.load(open("schema/canonical/place.schema.json"))
place = json.load(open("data/canonical/place/plc_baghdad.json"))
validate(instance=place, schema=schema)  # ValidationError raise eder
```

## Phase 0 hedefi

Week 2 sonunda:
- ✅ 8 temel canonical schema (Place, Person, Work, Event, Dynasty, Route, Source, Attestation) — **JSON Schema tamamlandı**
- [ ] Her birinin Pydantic modeli (Python runtime validation) — Week 2 Fatıma
- [ ] Her birinin CIDOC-CRM + schema.org + DublinCore mapping dokümantasyonu — Week 2 Ali (ADR-002)
- [ ] Controlled vocabulary dosyaları (`schema/vocab/*.json`) — Week 2 Ali: madhab, field, genre, event_type, place_type

Week 6 sonunda bu schema'lar production database'de tablo yapısı olarak oturmuş olacak.
