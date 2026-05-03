# NEXT_SESSION_PROMPT.md — Hafta 2: Bosworth ETL Pilot (CSV-driven)

> Bu dosyayı bir sonraki Claude seansında ilk olarak yapıştır. Repo zip'i (içinde `data/sources/` ve adapter framework) yeterli — ek upload gerek yok.

---

## Bağlam (kısa)

`islamicatlas-canonical` Phase 0'da Hafta 0 + Hafta 1 + Hafta 1.5 (search-first refactor) + dataset inventory tamamlandı:

- **7 ADR** (URI / authority / ontology / search-first / unified catalog / adapter pattern / page contract).
- **6 entity şeması** (place + dynasty active; person + work + manuscript + event forward-declared).
- **Search artifacts**: Typesense collection schema + 6 projection + generic `projector.py` rule-driven engine.
- **UI contract**: meta-schema + 6 page recipe + search_result.schema.
- **Adapter framework**: `_template/` boilerplate + `registry.yaml`.
- **`data/sources/`**: 13 dataset klasörü, 40 MB, Phase 0/0.2/0.3/1 için **tüm upstream veriler hazır**.
- **Tests**: 18/18 PASS (15 schema + 3 projector).

**Stratejik dönüşüm:** İslamicatlas.org arşiv paketi geldikten sonra Hafta 2 planı revize edildi. Manuel-tablolaştırılmış JSON ihtiyacı **yok**: `all_dynasties_enriched.csv` zaten 186 dynasty'yi Bosworth NID hierarşisine hizalı şekilde tutuyor (NID-001=Rāshidūn → NID-186=Brunei), `all_rulers_merged.csv` 830 ruler içeriyor. Hafta 2 hedefi **CSV-driven adapter** — 10 değil, **186** dynasty tek pass'te canonical olur.

---

## Bu seansta üretilecek

### 1. `pipelines/adapters/bosworth/`

`_template/` kopyası, ama gerçek implementasyonla:

- **`manifest.yaml`** — adapter_id=bosworth, target_namespaces=[dynasty], source_id_pattern="bosworth-nid:{dynasty_id}", input_paths=["data/sources/bosworth/all_dynasties_enriched.csv", "data/sources/bosworth/all_rulers_merged.csv", "data/sources/bosworth/dynasty_relations.csv"], extraction_method=structured_csv.
- **`extract.py`** — CSV'leri normalize edilmiş JSON'a çevir. Her dynasty için: kendi satırı + ilgili rulers (dynasty_id JOIN) + ilgili relations (predecessor/successor type filter). Yield: `{"source_record_id": "bosworth-nid:1", "raw_data": {...full dynasty + rulers + relations...}}`.
- **`canonicalize.py`** — `dynasty.schema.json`'a uygun canonical kayıt üret. Field map (CSV → schema):

  | CSV column | Schema field |
  |------------|--------------|
  | `dynasty_id` | derived `@id` via PID minter (deterministic from input_hash="bosworth-nid:{id}") |
  | `dynasty_name_en/tr/ar` | `labels.prefLabel.{en,tr,ar}` |
  | `date_start_ce/end_ce`, `date_start_hijri/end_hijri` | `temporal.{start_ce, end_ce, start_ah, end_ah}` |
  | `government_type` | drives `@type` array suffix (caliphate/sultanate/emirate/imamate/beylik) |
  | `capital_city`, `capital_lat`, `capital_lon` | `had_capital[]` (placeholder place PID, with denormalized name+coords for Hafta 3 resolution) |
  | `regions_all` | `territory[]` (placeholder region PIDs; resolved Hafta 3) |
  | `predecessor`, `successor` | resolved cross-record in second pass via `dynasty_relations.csv` |
  | `chapter` | `bosworth_id` (formatted as `NID-{:03d}`) |
  | `narrative_en/tr` | `labels.description.{en,tr}` |
  | `key_contribution_en/tr` | `note` (multilingual) |
  | rulers (joined from `all_rulers_merged.csv` by `dynasty_id`) | `rulers[]` array, fields: name (=`short_name` or `full_name_original`), name_ar (from `full_name_original` if Arabic-script), kunya, nasab, laqab, regnal_title (from `title`), reign_start_ce, reign_end_ce, reign_start_ah, reign_end_ah |

- **`README.md`** — Bosworth NID-aligned olduğunu, edition (EUP 2004), known issues (Anatolian beylik Wikidata zayıf, Cairo Abbasid line ayrı entity olarak işlendi), license fair-use'u açıklıyor.

### 2. `pipelines/_lib/`

- **`pid_minter.py`** — atomik 8-haneli ordinal minter. State: `data/_state/pid_counter.json` (per-namespace counter). Mint algoritması: `mint(namespace, input_hash)` → input_hash'i SHA256'la, eğer `data/_state/pid_index.json`'da varsa cache hit (idempotent), yoksa counter++ ve cache'e yaz. **NOT:** Bosworth için input_hash="bosworth-nid:{dynasty_id}" deterministik; ikinci pass'te aynı PID üretir.
- **`wikidata_reconcile.py`** — OpenRefine Reconciliation API client (`https://wikidata.reconci.link/en/api`) + `requests`. SQLite cache: `data/cache/wikidata_reconcile.sqlite` (key=label_en+context, TTL=30 gün). Confidence ≥0.85 auto-accept, 0.70-0.85 review queue.

### 3. `pipelines/run_adapter.py`

CLI: `python3 pipelines/run_adapter.py --id bosworth [--strict|--lenient] [--limit N]`.
Akış: registry'den manifest oku → input_paths resolve et → extract.py.extract() → for each: canonicalize.py.canonicalize() → schema-validate → write to `data/canonical/dynasty/iac_dynasty_NNNNNNNN.json`.

### 4. `pipelines/integrity/check_all.py`

Ayrı pass: tüm canonical kayıtları yükle, bidirectional invariant'ları kontrol et:
- `dynasty.predecessor` ↔ `dynasty.successor` simetrik mi?
- `dynasty.had_capital[].place` PID'leri çözüyor mu? (Hafta 3'e kadar placeholder bekleniyor — warning OK, error değil.)
- Rulers kronolojik sıralı mı?

Failure mode: report on stdout + exit code 1 if strict.

### 5. `tests/integration/test_bosworth_pilot.py`

End-to-end:
1. Run adapter on Bosworth source CSVs.
2. Assert 186 canonical files written.
3. Each file passes `dynasty.schema.json` validation.
4. Spot-check NID-001, NID-003, NID-186 (Rāshidūn / Abbasid / Brunei) for ruler count, dates, expected fields.
5. Run search projector on each → 186 search docs without errors.
6. Wikidata reconciliation: assert ≥%70 of dynasties have an authority_xref entry (live API, cache OK).

---

## Default kararlar (`sen seç` aktif)

| ID | Soru | Default |
|----|------|---------|
| H2.1 | Hangi CSV → JSON normalization formati? | **all_dynasties_enriched.csv → JSON list of objects (one per row), keep all 44 columns; rulers ve relations join'i canonicalize.py'da**. |
| H2.2 | Tüm 186 dynasty mi yoksa pilot 10? | **Tüm 186** — manuel iş yok, CSV temiz, otomatize edilebilir. |
| H2.3 | Rulers'ın role/title değerleri (CSV'de "Caliph", "Sultan", "Emir", ...) | Direkt `rulers[].regnal_title` veya `rulers[].title` field'ına yaz; `dynasty.dynasty_subtype`'ı belirlemek için `government_type` CSV column'unu kullan, role değerini değil. |
| H2.4 | Wikidata reconciliation tüm 186 için mi? | **Evet** — 186 query × ~500 ms = ~90 saniye. Cache sonrası yeniden çalıştırma anında. |
| H2.5 | Capital placeholder PID stratejisi | `had_capital[].place` field'ına `iac:place-PLACEHOLDER-{normalized_name}` yaz (regex pattern karşılamayacak şekilde **sentinel**), Hafta 3'te Yâqūt + Le Strange canonicalize sonrası gerçek PID'lerle replace. Schema validation buna izin verecek mi? **Evet** — `had_capital` opsiyonel, ama eğer yazılırsa `place` zorunlu pattern karşılamak zorunda. **Çözüm:** Hafta 2'de `had_capital`'ı yazma; sadece `_capital_denormalized` adlı non-canonical yardımcı field'a yaz (Hafta 3'te schema değişikliği OLMADAN kullanılacak). |
| H2.6 | predecessor/successor Hafta 2'de? | **Evet, dynasty_relations.csv'den resolve edilebilir** — relations CSV'sinde "successor" type'lı satırlar 1:1 dynasty_id → dynasty_id mapping; ikinci pass'te canonical PID'leri lookup et. (Hafta 2 sonu integrity check başarılı olmalı.) |
| H2.7 | Search Hafta 2 sonunda full reindex çağrılsın mı? | **Dry-run**: `pipelines/search/full_reindex.py --dry-run` projector'ın 186 dynasty üzerinde başarılı çalıştığını ndjson stdout dump ile gösterir. Gerçek Typesense Hafta 6'da bootstrap. |

---

## Acceptance criteria

- [ ] `pipelines/adapters/bosworth/{manifest.yaml,extract.py,canonicalize.py,README.md}` yazılı.
- [ ] `pipelines/_lib/pid_minter.py` + `pipelines/_lib/wikidata_reconcile.py` yazılı, idempotent.
- [ ] `python3 pipelines/run_adapter.py --id bosworth` 186 dosya üretir: `data/canonical/dynasty/iac_dynasty_00000001.json` … `iac_dynasty_00000186.json`.
- [ ] `python3 tests/run_schema_tests.py` hâlâ 15/15 geçer.
- [ ] `python3 tests/test_projector.py` hâlâ 3/3 geçer.
- [ ] `python3 tests/integration/test_bosworth_pilot.py` 186/186 dynasty schema validation + projector başarılı.
- [ ] Wikidata: 186/186 için query atılmış, ≥%70'inde QID auto-matched (`authority_xref[?authority='wikidata'].confidence ≥ 0.85`).
- [ ] `pipelines/integrity/check_all.py` predecessor/successor bidirectional başarılı (warnings for unresolved capital placeholders OK).
- [ ] PID minter ikinci pass çalıştırmasında same PIDs üretiyor (idempotent).
- [ ] `pipelines/adapters/registry.yaml`'da `bosworth: enabled=true`.

---

## Beklenen sürtünme noktaları

- **Anatolian beyliklerde Wikidata zayıf**: ~30-40 NID için QID otomatik bulunmayabilir → review queue dolar. Bu yapısaldır, Hafta 2 acceptance kriterine engel değil (%70 hedef bunu karşılar).
- **`government_type` enum mismatch**: CSV'de "Hilafet", "Sultanlık", "Emirlik" Türkçe yazılı olabilir; schema'da `dynasty_subtype: caliphate|sultanate|emirate|imamate|beylik` İngilizce. Çevirim mapping `pipelines/adapters/bosworth/canonicalize.py` içinde explicit.
- **`role/title` heterojen**: bazı ruler kayıtlarında title="Caliph", bazılarında "Sultan", bazılarında "Atabeg". Schema enum yok (free string), o yüzden direkt kopyala — search facet'i için P0.3'te taxonomy.
- **Cairo Abbasid line (1261-1517)**: Bosworth'da NID-3 olarak 750-1517 verilmiş ama mevcut dynasty.schema.json fixture'ında Cairo line ayrı entity olarak modellendi (note'a yazılı). Kararı yap: tek entity 750-1517 (CSV'ye sadık) vs. iki entity (kayıt manuel split). **Default: tek entity** (CSV'ye uy, sonradan split deferred).

---

## Resume entry-point cümlesi

> "Hafta 2 Bosworth pilot'a başla. NEXT_SESSION_PROMPT.md ve data/sources/bosworth/'taki CSV'ler hazır. Default kararlarla ilerleyelim. Önce extract.py + canonicalize.py + pid_minter.py + wikidata_reconcile.py + run_adapter.py'ı yaz; sonra çalıştır; sonra integration test'i yaz; sonra schema + projector regression testleri kontrol et. 186 dynasty hepsi tek pass'te canonical olsun."

---

## Update v1.1 — ADR-008 (Entity Resolution) entegrasyonu

Hafta 2 görev listesi şu şekilde genişler:

**Yeni dosya:** `pipelines/adapters/bosworth/resolve.py` — Bosworth dynasty kayıtları için resolver. Trivial case (canonical store boş, hep null döner — yeni PID); ama sözleşme dahilinde olması gerekiyor ki ileri adapter'ların template'i tutarlı kalsın.

**Resolver smoke test:** Hafta 2 sonunda mevcut `tests/test_resolver.py` (5/5 PASS) hâlâ geçer; ek olarak Bosworth integration test'i resolver'ı çağırıp her dynasty için `kind="new"` döndüğünü doğrular.

**Lookup index bootstrap:** Bosworth canonicalization sonrası `pipelines/_index/build_lookup.py --rebuild` çağrılır — index 186 dynasty + her birinin Wikidata QID'si (reconciliation hit'leri) ile dolar. Hafta 3'te Yâqūt + Le Strange resolve.py'leri Tier 1'de bu index'i kullanarak dynasty referans'larını çözecek.

**Default kararlar (ek):**

| ID | Soru | Default |
|----|------|---------|
| H2.8 | Resolver Hafta 2'de Tier 2 implementasyonu? | **Hayır, stub yeterli.** Tier 2 P0.2'de A'lam adapter'ında ilk gerçek kullanımına gelir. Hafta 2'de Tier 1 + null fallback yeter. |
| H2.9 | Lookup index Hafta 2 sonunda dolu mu? | **Evet** — Bosworth canonicalize sonrası `build_lookup.py --rebuild`. 186 dynasty + Wikidata QID + source CURIE entries indexed. Hafta 3 Yâqūt adapter'ı bu index'i kullanır. |
