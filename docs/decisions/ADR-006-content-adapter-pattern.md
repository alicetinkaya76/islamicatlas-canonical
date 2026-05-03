# ADR-006: Content Adapter Pattern

**Status:** Accepted (autonomous resolution; subject to maintainer override)
**Date:** 2026-05-03
**Phase:** 0
**Supersedes:** —
**Related:** ADR-004 (Search-first), ADR-005 (Unified Catalog)

---

## Bağlam

Yeni vizyonun en kritik gereksinimlerinden biri: **"yeni gelebilecek kitaplar ve content easily entegre edilebilmeli"**. Bu, mimaride bir genişletilebilirlik (extensibility) noktasıdır — yanlış tasarlanırsa her yeni kaynak (yeni Bosworth, yeni Yâqūt, yeni Ibn Khaldun, yeni Ottoman defter külliyatı) ETL kodunda derin değişiklikler gerektirir; doğru tasarlanırsa **yeni klasör + yeni manifest = yeni içerik**.

Bu ADR şu kararları verir: (1) adapter sözleşmesi (interface), (2) registry mekanizması, (3) yeni içerik ekleme runbook'u, (4) yeni entity tipi ekleme runbook'u (daha nadir ama gerekli), (5) adapter versiyonlama.

---

## Karar 6.1: Adapter contract

**Karar:** Her içerik kaynağı `pipelines/adapters/<source_name>/` altında bir klasör olarak tanımlanır ve şu dört zorunlu artifakt'ı içerir:

```
pipelines/adapters/<source_name>/
├── manifest.yaml         # adapter meta + zorunlu metadata
├── extract.py            # raw kaynak → normalized JSON (in-memory or build/<source>.json)
├── canonicalize.py       # normalized JSON → canonical entity records (data/canonical/<ns>/iac_<ns>_NNNNNNNN.json)
└── README.md             # bu kaynağın tarihçesi, edition, lisansı, bilinen sorunlar
```

İsteğe bağlı:

```
├── projection_overrides.yaml  # bu kaynağa özgü search projection ayarları (default'a override)
├── tests/                     # adapter-specific test fixtures
└── notebooks/                 # exploration / verification not defterleri
```

### `manifest.yaml` zorunlu alanlar

```yaml
adapter_id: bosworth                    # snake_case, registry primary key
display_name: "Bosworth — New Islamic Dynasties (2nd ed., 2004)"
adapter_version: 0.1.0                  # semver
source_kind: secondary_scholarly        # primary_textual | secondary_scholarly | tertiary_reference | manual_editorial | authority_file
languages: [en]                         # source language(s)
license: "© Edinburgh University Press 2004; data ingested under fair-use scholarly extraction"
target_namespaces: [dynasty, person]    # bu adapter hangi entity tiplerine veri üretir
target_phase_min: P0                    # bu adapter en erken hangi phase'de aktif
target_phase_max: ~                     # hâlâ aktif (~ = open-ended)
extraction_method: manual               # manual | ocr | htr | structured_csv | structured_json | wikidata_query | scraping
input_paths:
  - data/sources/bosworth/nid-001.json
  - data/sources/bosworth/nid-002.json
  # ...
output_paths:
  - data/canonical/dynasty/             # bu adapter'ın yazdığı klasör(ler)
provenance_template:                    # her canonical kayıt için provenance bloğunun tipik şekli
  source_id_pattern: "bosworth-nid:{nid_number}"
  page_or_locator_pattern: "Bosworth, NID-{nid_number}, p. {page_range}"
  edition_or_version: "Edinburgh University Press 2004"
maintainer: https://orcid.org/0000-0002-7747-6854
contact_for_updates: [ali.cetinkaya@selcuk.edu.tr]
```

### `extract.py` sözleşmesi

```python
def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    """
    Yields normalized records (one per input row/entry/page).
    Output schema: free-form, but MUST be deterministic and reproducible.
    Output is NOT canonical — it's an intermediate representation.
    """
```

`extract.py` HİÇ İLE canonical schema bilmemeli; sadece kaynağı normalize eder. Bu sayede aynı kaynak farklı canonical map'lemelerine yönlendirilebilir (örn. Bosworth → dynasty + person + event'e).

### `canonicalize.py` sözleşmesi

```python
def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter: PidMinter,
    reconciler: WikidataReconciler,
    options: dict | None = None
) -> Iterator[dict]:
    """
    Yields canonical entity records, each conforming to schemas/<namespace>.schema.json.
    Each record is independently schema-valid and writable to data/canonical/<ns>/<id>.json.
    Cross-record references (predecessor, successor, etc.) MAY use placeholders that
    pipelines/integrity/resolve_refs.py resolves in a second pass.
    """
```

### Adapter çıkışlarının zorunlu garantileri

1. **Şema-uyumluluk:** Her output kayıt `schemas/<namespace>.schema.json`'a karşı `Draft202012Validator`'dan hatasız geçer.
2. **Provenance bütünlüğü:** Her output kayıt `provenance.derived_from`'da en az bir entry `manifest.yaml.provenance_template`'e uygun.
3. **PID kararlılığı:** Aynı input'a aynı PID atanır (idempotent). PidMinter input-hash bazlı cache kullanır.
4. **Hatalar fast-fail:** Bir kaydın canonicalize'ı başarısızsa pipeline `--strict` modunda durur; `--lenient` modda hata loglanır ve geri kalan kayıtlar üretilmeye devam eder.

---

## Karar 6.2: Adapter registry

**Karar:** `pipelines/adapters/registry.yaml` tüm aktif adapter'ları sıralar. Pipeline orkestrasyon (`pipelines/run_all_adapters.py`) bu dosyayı okur, her adapter için extract → canonicalize → write çevrimini koşar.

Registry yapısı:

```yaml
version: 0.1.0
adapters:
  - adapter_id: bosworth
    enabled: true
    priority: 100              # düşük sayı önce; bağımlılıklarda önemli (örn. dynasty önce, sonra person)
    config:
      strict_mode: true
      reconciliation_threshold: 0.85
  - adapter_id: yaqut
    enabled: true
    priority: 200
    config:
      pilot_subset: ["place"]   # opsiyonel scope
  # ...
```

Yeni adapter eklemek için yalnızca yeni klasör + registry'ye satır gerekir; orchestration kodu değişmez.

---

## Karar 6.3: Runbook — yeni kitap/içerik eklemek

**Senaryo:** "Ibn Khaldun'un Mukaddime'sini canonical store'a ekle."

### Adımlar

1. **Adapter klasörü oluştur:**
   ```
   pipelines/adapters/ibn-khaldun-muqaddima/
   ```

2. **`manifest.yaml` yaz** (target_namespaces: `[work, person, place, event]` — Mukaddime hem bir Work, hem yazarı Ibn Khaldun bir Person, hem zikrettiği şehirler Place, hem aktarılan olaylar Event).

3. **Kaynağı `data/sources/ibn-khaldun-muqaddima/` altına koy** (PDF, OCR çıktısı veya transkribe edilmiş JSON — `manifest.yaml.extraction_method` ile tutarlı).

4. **`extract.py` yaz:** Mukaddime metnini normalize edilmiş JSON'a çevir (her bölüm bir record, içinde named-entity'ler işaretli).

5. **`canonicalize.py` yaz:** Normalize çıktıyı canonical kayıtlara map'le. Her named-entity için: önce mevcut canonical store'da o entity var mı (örn. Halep zaten `iac:place-00000042` mi?) — varsa cross-reference ekle, yoksa yeni PID mintle.

6. **Adapter registry'ye satır ekle:**
   ```yaml
   - adapter_id: ibn-khaldun-muqaddima
     enabled: true
     priority: 250
   ```

7. **Çalıştır:**
   ```
   python3 pipelines/run_adapter.py --id ibn-khaldun-muqaddima
   python3 pipelines/integrity/check_all.py
   python3 pipelines/search/full_reindex.py
   ```

8. **Sonuç:** Search çubuğuna "Mukaddime" yazınca eserin entity sayfası gelir; "Ibn Khaldun" yazınca yazarın entity sayfası gelir; her ikisi de Mukaddime'nin zikrettiği yerleri ve olayları cross-ref panelinde gösterir.

**Kod değişikliği yok:** Search projector, UI page renderer, ontoloji — hiçbiri dokunulmadı.

---

## Karar 6.4: Runbook — yeni entity tipi eklemek

**Senaryo:** "Fatwa'ları kendi entity tipi olarak modellemek istiyorum (work'ün alt tipi yerine first-class)."

Bu daha nadir bir işlem ve daha ağır bir değişiklik. Adımlar:

1. **Ontoloji'ye sınıf ekle:** `iac:Fatwa` → `iac:Work` (subClassOf), CIDOC CRM `crm:E33_Linguistic_Object` ve FRBR `frbr:Work`. `iac_ontology.ttl` dosyasını güncelle.

2. **Schema yaz:** `schemas/fatwa.schema.json` — `work.schema.json`'u baz alarak fatwa'ya özgü field'ları ekle (`mufti` person ref, `mustafti` person ref, `legal_question`, `ruling`, `school` madhab ref).

3. **Search projection rule yaz:** `search/projections/fatwa.yaml` — fatwa için search doc nasıl üretilecek (hangi field'lar denormalize edilecek, hangi facet'ler aktif).

4. **Search collection schema güncelle:** `search/typesense_collection.schema.json` — `entity_type` enum'una `fatwa` ekle, fatwa-spesifik field'ları opsiyonel olarak tanımla.

5. **UI page recipe yaz:** `ui_contract/entity_pages/fatwa.schema.json` — fatwa entity sayfası hangi section'larla render edilecek (header, ruling, parties, citations).

6. **Forward-namespace'leri güncelle:** `docs/decisions/ADR-001-uri-scheme.md`'de namespace enum'una `fatwa` ekle. `docs/decisions/ADR-005-unified-entity-catalog.md`'de phase aktivasyon tablosuna fatwa satırı ekle.

7. **Integrity-check'e cross-ref invariant ekle:** Eğer fatwa ↔ person bidirectional pointer varsa.

8. **Test fixture yaz:** Pozitif + negatif fatwa fixture'ları, manifest'e ekle.

9. **Reindex.**

**Tahmini efor:** 1 günlük solo iş. Adapter eklemekten ~5× pahalı, ama tek seferlik. Ondan sonra fatwa entity'leri için adapter eklemek (yeni fatwa kaynağı) tek-seferlik 6.3 runbook'una düşer.

---

## Karar 6.5: Adapter versiyonlama

**Karar:** Adapter `manifest.yaml.adapter_version` semver ile etiketlenir. Aynı adapter'ın canonical çıktıları her zaman `provenance.generated_by.pipeline_version` ile birlikte yazılır → "bu kayıt Bosworth adapter v0.1.0 ile üretildi" deterministik biliniyor.

**Migration:** Adapter v0.2.0 (örn. yeni alan ekleme) yayınlandığında:

- v0.1.0 ile üretilmiş kayıtlar `provenance.record_history`'ye yeni bir `update` entry eklenerek re-canonicalize edilir.
- `record_history.note`: "Re-canonicalized by Bosworth adapter v0.2.0; new field <X> populated."
- Adapter v0.1.0 → v1.0.0 gibi major bump breaking change demektir; legacy kayıtlar `deprecated_in_favor_of` ile yeni PID'ye yönlendirilir.

**Adapter sürüm uyumluluğu:** Adapter `manifest.yaml.target_phase_max` ile sınırlandırılabilir (örn. `target_phase_max: P0.5` adapter P0.6'dan itibaren retire edileceğini bildirir; orkestrasyon `enabled` field'ını otomatik false yapar).

---

## Sonuçlar

**Pozitif:**

- Yeni içerik (kitap, defter, koleksiyon) eklemek tek-klasörlük iş; search/UI/ontology kodu dokunulmuyor.
- Adapter registry merkezî kontrol noktası — bir komutla tüm adapter'lar koşturulabilir, devre dışı bırakılabilir.
- Versiyonlama deterministik; her canonical kayıtta hangi adapter sürümü tarafından üretildiği yazılı.
- Adapter'lar paralel geliştirilebilir (bağımlılık priority field'ı ile yönetilir).

**Negatif (kabul edilen):**

- Adapter sözleşmesi (extract + canonicalize ayrımı) bazı basit kaynaklarda over-engineering hissi verir; çözüm: `_template/` boilerplate üretir, her yeni adapter'da minimum kod yazılır.
- Cross-adapter referans çözümü iki-pass'lı (her adapter kendi pass'ında PID minter, sonra integrity check resolve'ler) — debugging zorluğu kabul edilir.

**Yeniden gözden geçirme:** P0.2 sonunda. 5+ adapter aktive olduktan sonra orkestrasyon performansı, paralelizasyon ihtiyacı, registry'nin ölçeklenmesi.

---

## Atıflar

- ADR-004 (Search-first), ADR-005 (Unified Catalog)
- ETL pipeline patterns: dbt project structure (https://docs.getdbt.com/) — yapısal ilham; biz schema-first çalışıyoruz
- Adapter pattern (Gamma et al., GoF): yapısal ilham; içerik dünyasına genişletme

---

## Update Note v1.1 — Resolver Stage (03 May 2026)

ADR-008 (Entity Resolution & De-Duplication) bu ADR'i tamamlar. Adapter sözleşmesi 3 dosyadan **4 dosyaya** çıkar:

```
pipelines/adapters/<source>/
├── manifest.yaml
├── extract.py            # raw → normalize JSON
├── resolve.py            # NEW: normalize JSON → match decisions
├── canonicalize.py       # decision'a göre: merge mevcut PID veya yeni PID
└── README.md
```

**Resolver = entegrasyon garantörü.** Resolver olmadan adapter'lar kanonikal store'u şişiririr (Halep 6 kez, Bīrūnī 4 kez). Resolver Tier 1 (deterministic authority match) + Tier 2 (blocking + similarity, P0.2'de aktif) + Tier 3 (manual review queue) ile bu çakışmayı engeller.

**Append-only merge semantics**: mevcut PID match olduğunda canonicalize.py kayıt **üzerine yazmaz**, sadece append eder (provenance.derived_from, altLabels, authority_xref union'a; prefLabel/temporal/coords override edilmez). Audit log `provenance.record_history` ile tam izlenir.

**Search ile uyum**: her merge sonrası Typesense upsert; search doc'un `source_layer` field'ı tek entity için çoklu kaynak attribution'ı tutar → kullanıcı facet'te "DİA + alam + EI1 hepsinde geçen kişiler" gibi cross-source query atabilir. Bu mevcut sitede yapılamayan kullanıcı deneyimi.

**Yeni içerik runbook'u (ADR-006 §6.3) güncellenir**: extract → resolve → canonicalize → review queue → reindex; ADR-008 §8.7'deki tam runbook'a bakınız.

`_template/` skeleton'a `resolve.py` eklendi. Resolver'ın ortak mantığı `pipelines/_lib/entity_resolver.py`'da; adapter sadece feature extraction kurallarını yazar (5-10 dakika ek iş).
