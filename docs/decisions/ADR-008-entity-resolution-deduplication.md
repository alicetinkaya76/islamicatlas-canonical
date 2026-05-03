# ADR-008: Entity Resolution & De-Duplication

**Status:** Accepted (autonomous resolution; subject to maintainer override)
**Date:** 2026-05-03
**Phase:** 0
**Supersedes:** —
**Related:** ADR-004 (Search-first), ADR-005 (Unified Catalog), ADR-006 (Adapter pattern)

---

## Bağlam

ADR-006 adapter pattern'ini kurdu: yeni içerik = yeni adapter klasörü. Ama bu pattern **tek başına entegrasyonu garanti etmiyor.** Eğer her adapter naïve davranır ve gördüğü her entity için yeni PID mintlerse, canonical store şişer ve çakışır:

- A'lam'da Bīrūnī, DİA'da Bīrūnī, EI1'de Bīrūnī = 3 farklı PID.
- Halep mevcut sitede 6+ katmanda geçiyor (Yâqūt, Le Strange, major_cities, evliya, ibn-battuta, maqrizi). 6 ayrı PID.
- Bosworth NID-3 (Abbâsî) DİA'da, alam'da, ei1'de geçer. 4 ayrı PID.

Bu durumda canonical store'un **tüm değer önerisi çöker**: tek-entity-tek-PID, citable persistent identifier, cross-reference graph — hepsi anlamsızlaşır. Search-first vizyon ise tamamen göçer: kullanıcı "Bīrūnī" arar, 3 farklı sonuç görür, hangisinin "doğru" olduğu belirsiz; "her üç kaynakta da geçen" facet'i kuramazsın çünkü 3 ayrı entity, layer attribution değil.

Bu ADR şunu kurar: **adapter'lar kayıt yazmadan önce mevcut canonical store'da match arar.** Match varsa append-merge, yoksa yeni PID. Bu işin nasıl yapılacağı, hangi confidence eşikleri, manual review akışı, persistent lookup index — hepsi burada.

---

## Karar 8.1: Resolver = adapter sözleşmesinin zorunlu üçüncü ayağı

**Karar:** ADR-006 §6.1'deki adapter sözleşmesine bir aşama daha eklenir:

```
extract.py    : kaynak → normalize JSON
resolve.py    : normalize JSON → her entity için match kararı (existing PID veya null)
canonicalize.py: existing PID varsa MERGE; null ise YENI PID + full record
```

`resolve.py` sözleşmesi:

```python
def resolve(
    extracted_records: Iterator[dict],
    resolver: EntityResolver,
    options: dict | None = None,
) -> Iterator[tuple[dict, ResolutionDecision]]:
    """
    Yields (extracted_record, decision) pairs.
    
    decision.kind: "match" | "new" | "review"
    decision.matched_pid: str | None (when kind="match")
    decision.confidence: float (0..1)
    decision.candidates: list[Candidate] (top-K considered, for audit)
    decision.feature_scores: dict (per-feature similarity, for debugging)
    """
```

`canonicalize.py` `resolve.py`'in kararına göre dallanır:

- **kind="match"**: mevcut canonical kaydı yükle, alanları **append-only merge** et (Karar 8.4), `provenance.record_history`'ye `update` entry ekle, write.
- **kind="new"**: yeni PID mintle, full canonical kayıt inşa et, write.
- **kind="review"**: kaydı `data/review_queue/<adapter_id>.jsonl`'a düşür; canonicalize bu pass'te skip; manual karar sonrası ikinci pass'te resolve.

`pipelines/_lib/entity_resolver.py` resolver mantığının %95'ini paylaşır; `resolve.py`'nin adapter-spesifik kısmı yalnızca **feature extraction kuralları** (extract output şeması farklı olduğu için).

---

## Karar 8.2: Üç-katmanlı resolution stratejisi

**Karar:** Her extracted entity için resolver şu sırayla dener:

### Tier 1 — Deterministic key match (auto-accept, %100 confidence)

Eğer extracted kayıt aşağıdakilerden birini taşıyorsa, lookup index'inde sorgulanır; hit varsa eşleşme kesin, otomatik kabul:

| Authority | Lookup namespace |
|-----------|-----------------|
| Wikidata QID (`Q41183`) | tüm tipler |
| Pleiades PID (`658381`) | place |
| VIAF ID | person |
| OpenITI URI (`0429Yaqut.MucamBuldan`) | work |
| Bosworth NID (`NID-003`) | dynasty |
| Existing canonical CURIE in source (`yaqut:7842`) | place (Yâqūt-derived sources) |
| `dia_alam_xref.json`'dan crosswalk hit | person |
| `le_strange_xref.json`'dan crosswalk hit | place |

**Tier 1 etkili olduğu yer**: A'lam ↔ DİA ↔ EI1 zaten her entry için Wikidata QID + cross-source xref dosyaları içeriyor. Bu tier alone person namespace'inde ~%50-60 entity'yi resolve eder; deterministic, hatasız, hızlı (SQLite indexed lookup).

### Tier 2 — Blocking + similarity scoring (threshold-based)

Tier 1 miss ise:

**Step 1 — Blocking**: ~60k canonical entity'yi 50-200 candidate'a indir. Bloking key per-type:

- **Place**: `(century_ce_bucket, iqlim, prefLabel_translit[:3])` — örn. `(8, "Sham", "Hal")` → 50-200 candidate.
- **Person**: `(century_ce_bucket, prefLabel_translit[:4])` veya `(century_ce_bucket, nisba)` — örn. `(4, "Bukh")` → al-Bukhārī etrafı.
- **Dynasty**: `(century_start, region_primary)` — dynasty çok az, blocking gevşek olabilir.
- **Work**: `(author_pid, genre)` veya `(century_ce_bucket, prefLabel_translit[:5])`.
- **Manuscript**: `(library, dating_century)`.
- **Event**: `(century_ce_bucket, location_iqlim)`.

Blocking key'i match etmeyen entity'ler **resolution dışı** (false negative kabul edilen risk; threshold seçimi blocking gevşekliğini kompanse eder).

**Step 2 — Multi-feature similarity scoring**: her candidate için score:

```
score = w_label    × max(translit_levenshtein, ar_levenshtein) 
      + w_alt      × jaccard(altLabel_set_extracted, altLabel_set_canonical)
      + w_temporal × temporal_overlap_ratio
      + w_spatial  × (1 - haversine_distance_normalized)        # place için
      + w_authority × authority_partial_match                    # şared QID/VIAF
      + w_kunya    × kunya_nasab_match                          # person için
      + w_genre    × (1 if genre overlap else 0)                # work için
```

Default ağırlıklar `pipelines/_lib/resolver_weights.yaml`'da, per-entity-type ayarlanabilir. Hafta 2 başlangıç ayarları:

```yaml
person:
  w_label: 0.35
  w_alt: 0.15
  w_temporal: 0.20
  w_authority: 0.20
  w_kunya: 0.10
place:
  w_label: 0.30
  w_alt: 0.15
  w_temporal: 0.05
  w_spatial: 0.30
  w_authority: 0.20
dynasty:
  w_label: 0.40
  w_temporal: 0.30
  w_authority: 0.20
  w_alt: 0.10
```

**Step 3 — Threshold karar**:

| Skor aralığı | Karar | Aksiyon |
|--------------|-------|---------|
| ≥ 0.90 | auto-match | matched_pid set, kind="match" |
| 0.70 – 0.90 | review | review_queue'ya, kind="review" |
| < 0.70 | new entity | matched_pid=null, kind="new" |

Eşikler `pipelines/_lib/resolver_weights.yaml`'da entity-type başına override edilebilir (örn. dynasty için review threshold 0.80'e çek, çünkü dynasty count az ve her bir karar etkili).

### Tier 3 — Manual review queue

Tier 2'de 0.70–0.90 düşen kararlar `data/review_queue/<adapter_id>.jsonl`'a write edilir, her satır:

```json
{
  "queue_id": "<uuid>",
  "adapter_id": "dia",
  "extracted_record_id": "dia:5847",
  "extracted_summary": {
    "name": "Ebû Bekir Muhammed b. Ahmed el-Bağdâdî",
    "dates": "780-?-855",
    "context": "..."
  },
  "candidates": [
    {
      "pid": "iac:person-00000423",
      "score": 0.84,
      "feature_scores": { "label": 0.91, "temporal": 0.7, "authority": 0.0, ... },
      "summary": { "name": "Abū Bakr Muḥammad b. Aḥmad al-Baghdādī", "dates": "780-855", "from_sources": ["alam:1234"] }
    },
    { "pid": "iac:person-00000891", "score": 0.78, ... }
  ],
  "deferred_at": "2026-05-15T14:32:11Z"
}
```

CLI tool `pipelines/review_queue/cli.py` her queue entry'sini interaktif gösterir:

```
[1/47] adapter=dia, extracted=dia:5847
  Extracted: Ebû Bekir Muhammed b. Ahmed el-Bağdâdî (780-855)
  
  Candidates:
    [a] iac:person-00000423 — Abū Bakr Muḥammad b. Aḥmad al-Baghdādī (780-855) [score=0.84, sources=alam, ei1]
    [b] iac:person-00000891 — Abū Bakr al-Baghdādī (?-855) [score=0.78, sources=ei1]
    [n] new entity (mint new PID)
    [s] skip (decide later)
  Choice: a
  Note (optional): "Same person; DİA gives ahmed b. ahmed forms"
```

Karar `data/review_decisions.jsonl`'a append-only write (asla rewrite). Adapter ikinci pass çalıştırmasında resolver bu kararları cache'ler — aynı queue_id için kararı uygular, manual review tekrarı yok.

**Karar formatı:**

```json
{
  "queue_id": "<uuid>",
  "decision": "match" | "new" | "skip",
  "matched_pid": "iac:person-00000423" | null,
  "decided_at": "2026-05-15T15:01:00Z",
  "decided_by": "https://orcid.org/0000-0002-7747-6854",
  "note": "Same person; DİA gives ahmed b. ahmed forms"
}
```

---

## Karar 8.3: Persistent lookup index

**Karar:** Canonical store yanında **SQLite-based reverse lookup index** tutulur — `data/_index/lookup.sqlite`.

Şema:

```sql
-- Authority index: deterministic Tier 1 lookup
CREATE TABLE authority_xref (
  authority TEXT NOT NULL,            -- 'wikidata' | 'pleiades' | 'viaf' | ...
  authority_id TEXT NOT NULL,
  pid TEXT NOT NULL,                  -- canonical PID
  PRIMARY KEY (authority, authority_id)
);

-- Source CURIE index: deterministic xref-file lookup
CREATE TABLE source_curie (
  source_id TEXT PRIMARY KEY,         -- 'yaqut:7842', 'bosworth-nid:3', ...
  pid TEXT NOT NULL
);

-- Label index: Tier 2 blocking + similarity
CREATE TABLE label (
  pid TEXT NOT NULL,
  lang TEXT NOT NULL,                 -- 'en' | 'ar' | 'tr' | 'translit'
  kind TEXT NOT NULL,                 -- 'pref' | 'alt' | 'translit'
  text TEXT NOT NULL
);
CREATE INDEX label_text_idx ON label(text);
CREATE VIRTUAL TABLE label_fts USING fts5(pid, text);  -- fuzzy match support

-- Bracket index: Tier 2 blocking
CREATE TABLE entity_bracket (
  pid TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  century_ce_bucket INTEGER,          -- floor(start_ce / 100) * 100
  iqlim TEXT,                         -- primary iqlim if applicable
  lat REAL, lon REAL,                 -- primary coords if applicable
  start_year_ce INTEGER, end_year_ce INTEGER
);

-- Decision cache: idempotent re-runs
CREATE TABLE decision_cache (
  adapter_id TEXT NOT NULL,
  extracted_record_id TEXT NOT NULL,
  decision_kind TEXT NOT NULL,        -- 'match' | 'new' | 'review' | 'review_resolved'
  matched_pid TEXT,
  confidence REAL,
  decided_at TEXT NOT NULL,
  PRIMARY KEY (adapter_id, extracted_record_id)
);
```

**Index lifecycle:**

- **Bootstrap**: `pipelines/_index/build_lookup.py` tüm `data/canonical/*` taranır, index sıfırdan inşa edilir. ~60k entity için ~30-60 saniye.
- **Incremental update**: her canonical record write'tan sonra `pipelines/_index/upsert.py` çağrısı (canonicalize.py'den otomatik). Tek-PID upsert ~1 ms.
- **Repair**: `pipelines/_index/verify.py` index ↔ canonical files arası tutarlılık kontrolü. Mismatch varsa rebuild.

**Index, canonical store'un içsel aracıdır** — kullanıcı arama'sı için DEĞİL, **resolver'ın hızlı çalışması için.** Typesense (search-first user-facing engine) ayrı bir sorumluluk; ikisi karıştırılmaz. Bu ayrım önemli çünkü:

- Resolver index'i schema-strict, internal, write-heavy.
- Typesense schema-flexible, public-facing, read-heavy.
- Typesense'i resolver'a bağlamak = production search engine'i ETL bağımlılığına sokmak; reindex sırasında resolution kırılır.

---

## Karar 8.4: Append-only merge semantics

**Karar:** Resolver mevcut PID döndürdüğünde, canonicalize.py o kayda **veri ekler, üzerine yazmaz**.

### Append-only field'lar (otomatik union)

| Field | Birleşim semantik |
|-------|-------------------|
| `provenance.derived_from[]` | yeni source entry append edilir; mevcut entry'ler dokunulmaz |
| `labels.altLabel.<lang>[]` | yeni alt label'lar union'a eklenir, deduplication |
| `labels.transliteration.<scheme>` | yoksa eklenir, varsa override edilmez |
| `authority_xref[]` | yeni authority entries append; (authority, id) ikilisi unique |
| `mentions_persons[]`, `mentions_places[]`, `cites_works[]` (work) | union |
| `predecessor[]`, `successor[]` (dynasty/place) | union |
| `derived_from_layers[]` (place) | union |

### Override-protected field'lar (asla otomatik üzerine yazılmaz)

| Field | Kural |
|-------|-------|
| `labels.prefLabel.<lang>` | sadece o dilde mevcut prefLabel YOKsa eklenir |
| `temporal.start_ce`, `end_ce`, `start_ah`, `end_ah` | mevcut değer korunur |
| `coords.lat`, `lon` | mevcut değer korunur |
| `dynasty_subtype`, `place_subtype`, `event_subtype` | mevcut değer korunur |
| `bosworth_id`, `yaqut_id`, `openiti_uri` | mevcut değer korunur |

### Çakışma davranışı

Yeni kaynak override-protected bir field için **farklı** bir değer veriyorsa:

1. Mevcut canonical değer korunur.
2. `provenance.record_history[]`'ye `change_type: "merge_conflict"` entry append edilir, açıklama: "Source X says 'Y', current value is 'Z' (set by source W); kept current."
3. Adapter loglarına warning yazılır.
4. Eğer maintainer karar değiştirmek isterse, `tools/edit_canonical.py` ile manuel override + record_history'ye `editorial_override` entry'si.

### Provenance audit

Her merge `provenance.record_history[]`'ye eklenen entry içerir:

```json
{
  "change_type": "update",
  "changed_at": "2026-08-12T09:14:22Z",
  "changed_by": "https://orcid.org/0000-0002-7747-6854",
  "release": "v0.2.5-phase0_2",
  "note": "Merged from adapter=dia, extracted_record=dia:5847; added altLabels[tr], authority_xref[viaf], provenance.derived_from[+1].",
  "merged_from_source": "dia:5847",
  "fields_added": ["altLabel.tr", "authority_xref.viaf", "provenance.derived_from"],
  "fields_skipped_conflict": []
}
```

Bu sayede her canonical kayıtta **tam audit log** vardır: hangi kaynak hangi alanı ne zaman ekledi, hangi alanın çakıştığı ve nasıl çözüldüğü.

---

## Karar 8.5: Search projection — değişen PID'lerde otomatik upsert

**Karar:** Canonicalize.py bir PID'i write ettikten sonra (yeni veya merge), `pipelines/search/upsert.py` çağrısı atılır → Typesense `iac_entities` collection'ında o PID için search doc upsert.

Mekanizma:

```python
# canonicalize.py sonunda:
written_pid = ...
projector.project_one(written_pid)        # canonical → search doc
typesense_client.collections['iac_entities'].documents.upsert(search_doc)
```

Idempotent: aynı PID iki kez yazılırsa Typesense replace-by-id semantiği hatasız geçer.

**Search doc'un içinde mucize:** `source_layer` field'ı array. Bir entity DİA + alam + EI1 + Bosworth-rulers'tan merge edilmişse, search doc'unda:

```json
{
  "id": "iac:person-00000423",
  "prefLabel_translit": "Abu Bakr al-Baghdadi",
  "source_layer": ["dia", "alam", "ei1", "bosworth-rulers"],
  ...
}
```

Kullanıcı facet panelinde "kaynak katmanı: DİA + alam + EI1 hepsinde geçen kişiler" filtresi yaratabilir → 4 silodan 1 entity sonucu. **Bu mevcut sitede kavramsal olarak yapılamayan şey**; canonical entegrasyon + resolver bunu mümkün kılan tek mimari.

---

## Karar 8.6: Bosworth Hafta 2 — resolver'ın trivial case'i

**Karar:** Hafta 2 Bosworth pilot'unda resolver **her extracted dynasty için null döner** (yeni PID), çünkü:

1. Bosworth dynasty namespace'in ilk kayıtlarını yazıyor; canonical store boş, match imkansız.
2. Tier 1 deterministic check Wikidata QID için yapılır ama hit yok (henüz indexed değil).
3. Tier 2 blocking devre dışı (canonical entity 0).

Bu sayede Hafta 2'de resolver tam-implementasyon zorunluluğu yok; **skeleton + Tier 1 lookup yeter**. Tier 2 (blocking + similarity) ve Tier 3 (review queue CLI) Hafta 9-12'de **DİA + alam + EI1 → person namespace'in seed'i sırasında** gerçek kullanım kazanır.

**Hafta 2 deliverable:** `pipelines/_lib/entity_resolver.py` skeleton (Tier 1 + null fallback), `pipelines/_index/build_lookup.py` (basit), Bosworth `resolve.py` (her zaman null döner).

**Hafta 9 deliverable:** Tier 2 + Tier 3 tam implementasyon, A'lam adapter'ı resolver'ın ilk gerçek kullanıcısı.

---

## Karar 8.7: Yeni adapter author'lar için runbook

ADR-006 §6.3 (yeni kitap eklemek runbook'u) güncellenir:

```bash
# 1. Adapter klasörünü kopyala
cp -r pipelines/adapters/_template pipelines/adapters/<your-source-id>

# 2. Edit manifest.yaml + extract.py + resolve.py + canonicalize.py
$EDITOR pipelines/adapters/<your-source-id>/manifest.yaml
$EDITOR pipelines/adapters/<your-source-id>/extract.py    # NEW pattern
$EDITOR pipelines/adapters/<your-source-id>/resolve.py    # NEW: feature extraction rules
$EDITOR pipelines/adapters/<your-source-id>/canonicalize.py

# 3. Drop sources, register
$EDITOR pipelines/adapters/registry.yaml

# 4. Test resolution decisions on a small sample
python3 pipelines/run_adapter.py --id <your-source-id> --limit 50 --dry-run
# Output: "X matches (auto), Y new entities, Z review queue"

# 5. Review the queue
python3 pipelines/review_queue/cli.py --adapter <your-source-id>

# 6. Full run (idempotent — safe to re-run)
python3 pipelines/run_adapter.py --id <your-source-id>

# 7. Integrity + reindex (auto-tetiklenir, manuel olarak da çağrılabilir)
python3 pipelines/integrity/check_all.py
python3 pipelines/search/full_reindex.py --since-last-run
```

**Solo dev'in günlük iş yükü:** %80'i otomatik. Manual review queue (Tier 3) en yorucu kısım, ama 0.70-0.90 confidence'lı kararların sayısı genellikle dataset'in toplam ~%5-15'i. 14k entity'lik bir dataset → ~700-2100 manual decision. CLI tool batch decision (örn. "tüm DİA kayıtları için authority_xref'te VIAF varsa otomatik match") destekler → manuel iş ~%10'a düşer.

---

## Sonuçlar

**Pozitif:**

- Yeni dataset eklemek **kanonikal store'u şişirmiyor**, entegre ediyor. Halep 6 kez değil, 1 kez kanonikal; 6 kaynak attribution'ı.
- Search-first vizyon canlı: facet panelinde "DİA + alam + EI1 hepsinde geçen" gibi cross-source query atılabilir.
- Provenance bütünüyle audit'lenebilir: hangi kaynak ne zaman hangi alana katkı yaptı.
- Idempotent: adapter ikinci pass çalıştırması aynı kararları üretir, tekrarlanan iş yok.
- Geri alınabilir: `record_history` append-only; merge yanlış kararsa `revert_merge.py` aracı eski state'e döner.

**Negatif (kabul edilen):**

- Adapter sözleşmesi 3 dosyadan 4 dosyaya çıktı (extract + resolve + canonicalize + manifest). _template/ skeleton'ları boilerplate üretiyor; ek iş ~5-10 dakika.
- Manual review queue (Tier 3) maintainer zamanı tüketir. Trade-off entegrasyon kalitesi için makul; batch decision UI bunu hafifletir.
- Persistent lookup index (~60k entity → 100-200 MB SQLite) bakım gerektirir; bootstrap rebuild ~60 saniye. Acceptable.
- Resolution kararları "doğru" olmayabilir (false positive merge → iki farklı kişi aynı PID; false negative miss → aynı kişi iki PID). Manual review + record_history audit + `tools/edit_canonical.py` rollback path bu riskleri yönetir; sıfır değil.

**Yeniden gözden geçirme:** Phase 0.2 sonunda — A'lam + DİA + EI1 entegrasyonundan sonra. Tier 2 ağırlıkları ve eşikler ML-based learn edilebilir mi (ground truth: manual decisions log)? Wikidata QID kapsamı %30'un altındaysa Tier 1 yetersiz, fallback strateji genişletilmeli mi?

---

## Atıflar

- ADR-004 (Search-first), ADR-005 (Unified Catalog), ADR-006 (Adapter pattern)
- Christen, P. (2012). *Data Matching: Concepts and Techniques for Record Linkage, Entity Resolution, and Duplicate Detection*. Springer. Standard reference for blocking + similarity scoring.
- Papadakis, G. et al. (2020). "Blocking and Filtering Techniques for Entity Resolution: A Survey". *ACM Computing Surveys*.
- OpenRefine Reconciliation API spec: https://reconciliation-api.github.io/specs/latest/
- Wikidata Reconciliation: https://wikidata.reconci.link/
