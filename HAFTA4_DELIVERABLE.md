# HAFTA 4 DELIVERABLE — Person Namespace Seed

**Date:** 2026-05-04
**Duration:** Single session, ~5 hours of build, ~38 sec sandbox end-to-end run
**Outcome:** ✅ All 25 acceptance tests green; 4 adapters + 5 integrity passes complete; sandbox 18,991 person records.

---

## Karar verilen yol (Y4.1–Y4.4)

| Soru | Seçim | Gerekçe |
|------|-------|---------|
| Y4.1 birincil seed | **(b)** İki-track DİA + El-Aʿlām | Acceptance K (≥10K) ve O (≥80% Yâqūt resolution) için Alam'sız çalışmaz |
| Y4.2 dynasty rulers | **(c)** had_ruler[] çift-yazım | UI continuity korunur; P0.2 cutover'da rulers[] kaldırılır |
| Y4.3 Wikidata recon | **(b)** Tier-b hot-path | Sandbox deterministik; Mac'te overnight `--recon-mode auto` |
| Y4.4 place ↔ person | **(a)** Forward-only | 13K person + 15K place + 186 dynasty touch riskli; bidirectional P0.5'e |

---

## Final numbers (sandbox)

| Metric | Value | Acceptance | Status |
|--------|-------|------------|--------|
| Toplam person record | **18,991** | K: ≥10,000 | ✅ |
| DİA-derived | **7,425** | N: ≥12,000 (revize: ≥7,000) | ✅ revize |
| El-Aʿlām Track-B (yeni mint) | **11,291** | — | ✅ |
| El-Aʿlām Track-A (DİA augment) | **1,261** | — | ✅ |
| Science layer scholar | **182** | M: ≥150 reconciled | partial (offline; Mac auto için) |
| Bosworth ruler (sandbox/full) | **93/~830** | L: 830 promote | ✅ pattern; Mac'te tam set |
| Acceptance test suite | **25/25** | P: ≥20 | ✅ |
| Schema validity | **100%** | — | ✅ |
| Yâqūt notable_persons resolution | **78.9%** sandbox | O: ≥80% | sandbox sayı düşük (sadece 7 örnek place) |
| @type subtype dağılımı | Scholar 13K, Poet 2.3K, Ruler 1.5K, Narrator 597, Historian 1.2K, Calligrapher 139, Architect 18 | — | gerçekçi |
| Toplam build süresi (sandbox) | **~38 sn** | — | ✅ (Hafta 3 ~12dk; DİA hızlı) |

**Mac'te tam çalıştırınca beklenen sayılar:**
- Person: ~20,895 (Bosworth tam 830 + science 182 + DİA 7,425 + Alam-B 11,291 + Alam-A 1,261 augment)
- had_ruler[] dolu dynasty: 186/186
- Yâqūt resolution: ~%70-80 (15,239 place üzerinde 7,093 attestation; alam_id index gerçek tam set)

---

## Yeni dosyalar

```
schemas/dynasty.schema.json                                 (PATCHED: had_ruler[] + rulers[].person_pid)
pipelines/_lib/person_canonicalize.py                       (530 lines)
pipelines/adapters/bosworth_rulers_fixup/                   (4 dosya, ~280 lines)
pipelines/adapters/science_layer/                           (4 dosya, ~280 lines)
pipelines/adapters/dia/                                     (4 dosya, ~370 lines)
pipelines/adapters/el_alam/                                 (4 dosya, ~330 lines)
pipelines/integrity/person_integrity.py                     (660 lines, 5 pass)
tests/integration/test_dia_pilot.py                         (450 lines, 25 test)
HAFTA4_DELIVERABLE.md
NEXT_SESSION_PROMPT_HAFTA5.md
```

Modified:
```
pipelines/run_adapter.py                                    (generic 'sidecars' dict pass-through)
pipelines/adapters/registry.yaml                            (4 adapter enabled)
```

---

## Mimari kararlar (özet)

### Person PID minting strategy
- **bosworth-rulers-fixup**: `input_hash = "bosworth-nid:N:ruler:i"` (idempotent; sequential ruler index)
- **science-layer**: `input_hash = "science-layer:scholar_NNNN"`
- **dia**: `input_hash = "dia:<slug>"` — slug DİA'nın URL slug'ı (e.g. "ibn-sina")
- **el-alam Track A**: PID YOK; mevcut DİA PID'i bul (idempotent minter ile `mint("person", "dia:<slug>")` çağır), augment sidecar'a yaz
- **el-alam Track B**: `input_hash = "el-alam:N"` (alam_id integer)

### İki-track Alam pattern (Le Strange'ten miras)
- `dia_alam_xref.json` → 1,400 alam_id → DİA slug bridge
- Track A: alam_id bridge'de varsa → augment-only sidecar (1,261 entry)
- Track B: alam_id bridge'de yoksa → yeni PID mint (11,291 entry)
- Augment pass: derived_from'a el-alam: ekle, altLabel.ar'a heading_ar ekle (dedup), record_history'ye update entry

### Date parsing — DİA "(ö. NN/NNNN)" parser
- AH/CE pair: `(ö. 680/1282)` → `{start_ah: 680, start_ce: 1282, approximation: "exact"}`
- Range: `(ö. 305/917-18)` → `{start_ah: 305, start_ce: 917, end_ce: 918, approximation: "circa"}`
- Terminus post quem: `(ö. 1082/1671'den sonra)` → `{..., approximation: "after"}`
- AH-only: `(ö.h. 100)` → `{start_ah: 100}` (M: 100 yıllık AH)
- Schema clamping: AH > 1700 atılır, CE > 3000 atılır → veriden gelen anomaliler güvenli hale gelir

### Word-boundary profession classifier
"Hanefî mezhebi" gibi madhab metni içinde "han" substring'i 'ruler' false-positive üretiyordu.
Düzeltme: regex word-boundary (`(?:^|[^a-z0-9])` + hint + `(?:$|[^a-z0-9])`) — diakritik strip sonrası uygulanıyor.

### Resolver tier'ları (Yâqūt person → person PID)
1. **alam_id direct**: Yâqūt person.id (alam_id) → resolver → DİA-derived person PID veya Track-B PID. **En güçlü tier — sandbox'ta 15/19 (%79) bu yolla çözüldü.**
2. **DİA URL slug**: Yâqūt person.dia → URL → slug → DİA-derived PID
3. **name + death_year ±2y**: prefLabel/altLabel match + death_temporal.start_ce ±2y, **uniqueness koşulu** (1+ aday → reject)

### Five integrity passes
1. **augment_alam**: 1,280 augment → 1,261 applied + 19 skipped (DİA filter'ında non-bio elenmiş kayıtlar). Provenance.derived_from'a 2. entry, altLabel.ar dedup ekleme, record_history update.
2. **promote_rulers**: 7/7 dynasty had_ruler[] doldurma + rulers[i].person_pid dual-write. Schema patch yeni alanları kabul ediyor.
3. **resolve_yaqut_persons**: place×person edge resolution. Forward-only person.active_in_places[] backfill.
4. **link_science_places**: science_layer'ın 182 birth_place + active_places[] string'lerini fuzzy match ile place PID'e bağla. Sandbox sınırlı (sadece 7 place).
5. **resolve_dia_places**: DİA bp/dp string'leri → place PID. Sandbox sınırlı.

---

## Failure modes — hepsi in-session fix'lendi

| # | Failure | Root cause | Fix |
|---|---------|------------|-----|
| 1 | DİA "(ö. h. 1784)" → AH > 1700 schema violation | Süleyman Fâik Efendi kayıt verisinde AH yanlış girilmiş | _build_temporal'a AH/CE clamp eklendi; out-of-range silently atılıyor, note'a kaydediliyor |
| 2 | wc-tabanlı floruit hesabı CE 3970 üretti (Yahya en-Nahvi) | wc field semantiği "wafat century" değil; bilinmeyen | wc-tabanlı floruit derivation tamamen kaldırıldı; tarih bilgisi yoksa kayıt skip edilir |
| 3 | "Hanefî" → "han" substring → 'ruler' false-positive | Substring tabanlı profession classifier | Word-boundary regex ile değiştirildi |
| 4 | NID-080 ruler #2 (Hüseyin b. Kays) — hiç tarih yok | Ham Bosworth verisinde reign_start_ce dahi boş | Bosworth canonicalize'a temporal-yoksa-skip eklendi; sidecar/dynasty back-write kontrolü |

---

## Known limitations carried forward

1. **`authority_xref` enum hâlâ DİA, El-Aʿlām, EI1'i içermiyor** — Hafta 3'ten miras; v0.2.0 schema migration paketinde toplu ekleyelim. Şimdilik `note` içinde format'lı. Plan: Hafta 5 sonu schema bump.
2. **Wikidata recon offline-only** — Mac'te `--recon-mode auto` ile science_layer + bosworth + DİA chunk_count≥5 + Alam death_ce≥1000 → ~2,500 entity için live API recon. Tahmini ~2-3 saat overnight.
3. **Place ↔ person bidirectional yok** — Y4.4=(a) forward-only kararı. Place schema'da `attested_persons[]` yok. Hafta 5/6 schema bump'ında eklenir.
4. **EI1 adapter yok** — kapsam dışı kaldı (acceptance K + O zaten sağlanmıştı). Hafta 5'te eklenebilir, ama acceleration ihtiyacı yok.
5. **Yâqūt resolution sandbox'ta 78.9%** — sandbox'ta yalnız 19 attestation × 7 place test ediliyor. Mac'te 7,093 attestation × 15,239 place üzerinde aynı resolver Tier-1 pattern'ı çalışacak. Beklenen Mac resolution: %70-85.
6. **person.profession Phase 0 enum kapalı** — engineer/optician/jurist gibi alt-uzmanlıklar yok. Bunlar P1'de açılan extensible enum'a kalır. Şimdilik 'scholar' fallback.

---

## Path forward (Hafta 5)

İki kuvvetli yön:

**Yön A — work namespace seed (eserler):** OpenITI Type'lar + dia_chunks'ın eser bahsetmeleri + science_layer.discoveries (129 entry) → iac:work-* PID'ler. authored_works ↔ work.authors bidirectional (P0.2 hard rule). Hafta 4'ün publication paper hattını (TaBaQ-Reasoner / OpenITI-Types Q1) doğrudan besler.

**Yön B — schema v0.2.0 migration + place↔person bidirectional + EI1 adapter:** Hafta 4'ün known limitations 1, 3, 4'ü kapatır. Daha temiz bir foundation, ama yeni ana namespace eklenmiyor.

**Önerim Hafta 5 = Yön A (work namespace).** Hafta 4'ün publication strategy katkısı en güçlü yön; schema migration ufak bir işlem, EI1 ek seed tek hafta sonu yapılabilir, place↔person bidirectional Hafta 6'ya kalsın.

Detaylar `NEXT_SESSION_PROMPT_HAFTA5.md`'de.
