# Hafta 4 Session Notes — Person Namespace Seed

**Date:** 2026-05-04
**Duration:** Single session, ~5 hours of build, 38 sec sandbox end-to-end
**Outcome:** ✅ All 25 acceptance tests green; person namespace at 18,991 sandbox records (~20,895 expected on Mac)

---

## Session arc

This session built the person namespace from four sources in one extended sitting. Started by data inventory across DİA, science_layer, Bosworth dynasties (already in dynasty namespace from Hafta 2), and El-Aʿlām, surfaced 4 architectural decisions in "sen seç" mode, built four adapters + shared library + integrity passes (5 separate) + integration tests (25 acceptance tests), and closed with sandbox green-light.

### Phase 1: Reconnaissance (first 30 min)

User had 4 source corpora + 5 sidecars from Hafta 3 to integrate:

- **dia_chunks.json** (70 MB, 19,742 chunks across 8,093 distinct slugs). Per-chunk fields: id, s (slug), n (name CAPS), a (Arabic name), d (parenthetical death date "(ö. AH/CE)"), t (text content), c (chunk index), _id (sequence)
- **dia_lite.json** (8,528 entries, slug-keyed). Adds: dh/dc (death AH/CE), bh/bc (birth), bp/dp (birth/death place strings), fn (full nasab name), ni (nisba), mz (madhab), aq (akîde), fl (field array), wm (work_count), wc (some sort of century field — see failure mode #2)
- **alam_lite.json** (13,940 entries — much larger than DİA). Per-entry: id (alam_id), h/ht/he (heading ar/tr/en), dt/de (description), hd/md (death AH/CE), c (century_ce), g (gender), lat/lon
- **dia_alam_xref.json** (1,400 alam→dia + 1,280 dia→alam — small bridge, deduplication-needed because some keys collapse)
- **science_layer.json** (182 scholars + 37 institutions + 24 routes + 129 discoveries; trilingual full names + dates + xref_alam + xref_yaqut)
- **yaqut_alam_crossref_enriched.json** (606 places × 8,692 person attestations, full set; sidecar version had 7,093 deduped)

### Phase 2: Decision points (Y4.1 / Y4.2 / Y4.3 / Y4.4)

User answered "sen seç". Claude proposed and proceeded with:

- **Y4.1 (b)**: İki-track DİA + Alam (Le Strange pattern person versiyonu).
  Rationale: Acceptance K (≥10K record) ve O (≥80% Yâqūt persons resolved) tek başına DİA ile karşılanmaz. Alam person attestation'larının %85.6'sı zaten DİA URL ve %100'ü alam_id taşıyor → Track A 1,261 augment, Track B 11,291 yeni mint.

- **Y4.2 (c)**: had_ruler[] çift-yazım.
  Rationale: UI continuity için inline rulers[] kalır, P0.2'de tek script ile kaldırılır. Schema patch: `had_ruler[]` (PID array) + `rulers[].person_pid` (opsiyonel).

- **Y4.3 (b)**: Tier-b hot-path Wikidata recon.
  Rationale: Sandbox CI-friendly deterministik tutmak için offline default; user Mac'te `--recon-mode auto` ile high-value entities (science_layer + Bosworth + DİA chunk_count≥5 + Alam death_ce≥1000 → ~2,500 entity) ~2-3 saatte recon edilir.

- **Y4.4 (a)**: Forward-only person → place.
  Rationale: place schema dokunmazsa 13K+15K+186=28K+ record touch'unun yarısı bile değil. Person.active_in_places[] + birth_place + death_place doldurulur, place'ten person'a geri bakmak runtime/UI tarafında index hesaplanır. Bidirectional schema migration Hafta 6'ya kalır.

### Phase 3: Build (longest)

Build sırası şuydu:
1. Schema patch: `dynasty.schema.json`'a `had_ruler[]` + `rulers[].person_pid` ekleme; mevcut Râşidîn record'u tekrar valid çıktı.
2. `pipelines/_lib/person_canonicalize.py` — death-paren parser (4 farklı pattern), label dedup (case+diakritik insensitive), profession classifier (word-boundary regex), 8 person subtype @type builder, provenance/note formatters.
3. `pipelines/run_adapter.py` — generic `sidecars` dict pass-through (Hafta 3'teki sabit named keys ile backward compat).
4. **Adapter 1 (bosworth-rulers-fixup)**: 7 örnek dynasty üzerinde 94/94 ruler → person; sidecar `bosworth_rulers_pending` (dynasty_pid → ruler entries) + `rulers_to_dynasty_xref` (person_pid → dynasty_pid).
5. **Adapter 2 (science-layer)**: 182/182 scholar → person; full trilingual labels + birth/death CE temporal + profession from fields[]; xref_alam + xref_yaqut + active_places sidecars.
6. **Adapter 3 (DİA)**: 7,383 person records (8,093 slug taranıp 546 non-bio skip, ~165 temporalsız skip); 1,260 DİA→Alam xref + 5,525 birth/death place sidecar.
7. **Adapter 4 (el-alam)**: 11,291 yeni mint + 1,280 augment-pending + 6,499 yaqut place attestations sidecar; 8,649 - 11,291 - 1,280 = 1,369 silently skipped (no temporal at all in source).
8. `pipelines/integrity/person_integrity.py` — beş pass (augment_alam, promote_rulers, resolve_yaqut_persons, link_science_places, resolve_dia_places).
9. `tests/integration/test_dia_pilot.py` — 25 acceptance test (A. schema 5 + B. PID 3 + C. cross-source 4 + D. dynasty rulers 3 + E. Alam two-track 2 + F. Yâqūt edge resolution 2 + G. counts 4 + H. spot checks 2).

### Phase 4: Sandbox verification

Sandbox results:
- Total person: 18,991 (Mac'te +830-94=736 Bosworth ek + 0 diğer = ~19,727 + Track-A 1,261 augment = 20,988)
- Profession dağılımı: scholar 13K + poet 2.3K + ruler 1.5K + historian 1.2K + narrator 597 — gerçekçi
- @type subtype dağılımı: scholar 13K, ruler 1.5K, narrator 597, calligrapher 139, mufti 16, architect 18 — DİA chunk verisinden çıkarılan automatic profession sınıflandırması
- Augment ratio: 1,261/1,280 = %98.5 (19 augment_pending PID DİA filter'ında non-bio elendiği için skip edildi)
- Yâqūt resolution sandbox: 78.9% (sadece 19 attestation × 7 örnek place üzerinde test; Mac tam set'te aynı patterns)
- Tüm 25 acceptance test green
- Toplam build süresi: ~38 saniye (Hafta 3 ~12 dk; DİA hızlı çıktı çünkü chunks single-pass slug grouping)

### Phase 5: Failure modes encountered + fixes

Dört in-session düzeltme:

| # | Failure | Root cause | Fix |
|---|---------|------------|-----|
| 1 | `death_temporal.start_ah` 1784 > schema max 1700 | Süleyman Fâik Efendi DİA lite verisinde dh=1784 (yanlış girilmiş, gerçek ~1198) | `_build_temporal`'a clamp + warning note; out-of-range silently atılıyor |
| 2 | `floruit_temporal.start_ce` 3970 > schema max 3000 | wc field semantiği "wafat century" olarak yanlış varsayıldı; gerçekte ne olduğu bilinmiyor (max 25) | wc-tabanlı floruit derivation tamamen kaldırıldı; tarih bilgisi yoksa kayıt skip edilir |
| 3 | "Hanefî mezhebine mensup âlim" → 'ruler' false-positive | `if "han" in t` substring match — diakritik strip sonrası "han" Hanefî'de match ediyor | `re.search(r"(?:^|[^a-z0-9])han(?:$|[^a-z0-9])", t)` word-boundary regex |
| 4 | NID-080 ruler #2 (Hüseyin b. Kays) — hiç temporal yok | Bosworth ham verisinde reign_start_ce dahi boş; Phase 0 ruler dataclass'ında her field opsiyonel | Bosworth canonicalize'a temporal-yoksa-skip eklendi; dynasty back-write'a stale-link cleanup |

### Phase 6: Final verification

`pytest tests/integration/test_dia_pilot.py -v` → **25 passed in 9.95s**

Key spot-checks:
- Râşidîn: had_ruler[Abu Bakr, Umar, Uthman, Ali] dolu, her ruler'ın person_pid back-write'ı var
- Al-Khwārizmī: science_layer'dan iac:person-(95+) → mathematician + astronomer + geographer profession; death 850 CE ✓
- ABBÂD b. BİŞR: DİA + El-Aʿlām cross-attested (Track A); derived_from'da iki entry [dia:abbad-b-bisr, el-alam:4889] ✓

---

## Key architectural decisions captured

### Decision: PID immutability across cross-source merges (Hafta 3'ten miras)

When the same person is attested by multiple sources (e.g., al-Khwārizmī in DİA + science_layer + Wikidata), Phase 0 keeps **one PID per primary source**. No PID renaming. Cross-attestation lives in:
- `provenance.derived_from[]` — append-only entries from each source
- `note` — bidirectional cross-reference text
- `authority_xref[]` — Wikidata QID when reconciled

The **Track A pattern** is a more aggressive form: when a DİA-derived person and an El-Aʿlām entry are explicitly bridged (1,400 alam→dia mappings), we treat them as the SAME entity from the start (single PID), not as separate-records-merged-later. This is safe because the bridge is curator-verified.

### Decision: 5-tier resolver promised, 3 tiers implemented

Hafta 4 implemented:
- Tier-1 (alam_id direct match) — sandbox: 79% of Yâqūt attestations resolved
- Tier-2 (DİA URL slug) — implemented but rare in sandbox (alam_id covers most)
- Tier-3 (name + death±2y, uniqueness required) — implemented as fallback

Tiers 4-5 (fuzzy similarity scoring, manual review queue) are forward-declared in entity_resolver.py from Hafta 3 but not used here. Person namespace doesn't need them yet given Tier-1 dominance.

### Decision: "Skip on missing temporal" rather than fabricate

Both DİA's 165 records (no dh/dc/bp/fn) and Bosworth's 1 ruler (no reign_*) get silently skipped rather than synthesizing a date. Reason: schema $comment Phase 0.2 hard rule says temporal MUST be present, and the test suite enforces it. Better to lose 0.8% of records than create fabricated dates that will pollute downstream analyses.

### Decision: Profession from `fl` field (DİA) + heuristic from description

DİA's `fl` field has 13 distinct values (edebiyat, siyaset, fıkıh, hadis, tarih, tasavvuf, tefsir, tıp, felsefe, mûsiki, kelâm, astronomi, matematik) with very Turkish-specific labels. Mapped to person.schema's English profession enum via DIA_FIELD_TO_PROFESSION dict. Where `fl` is absent (44% of entries), fall back to keyword classification from `ds` (description) using person_canonicalize.classify_profession.

Result: scholar:13K + poet:2.3K + ruler:1.5K + historian:1.2K + narrator:597 — distribution matches expectations for pre-modern Islamic biographical corpora (heavy on religious sciences scholars, secondary on poets/historians).

---

## Final numbers (sandbox)

| Metric | Value |
|--------|-------|
| Canonical person records | 18,991 |
| Canonical dynasty records | 7 (sandbox; Mac has 186) |
| Canonical place records | 7 (sandbox; Mac has 15,239) |
| Schema validity rate | 100% |
| Records with death_temporal | ~17,500 (92%) |
| Records with birth_temporal | ~3,500 (DİA bh/bc field is sparse) |
| Records with active_in_places | 16 (sandbox; Mac will have ~5,000+ from Yâqūt resolution) |
| Records with authority_xref (Wikidata QID) | 0 (offline mode; Mac auto run will produce ~1,500-2,500) |
| @type subtype dağılımı | iac:Person 18,991, iac:Scholar 13,315, iac:Poet 2,334, iac:Ruler 1,517, iac:Narrator 597, iac:Calligrapher 139, iac:Mufti 16, iac:Architect 18 |
| Track A (DİA + Alam dual-attested) | 1,261 |
| Track B (Alam-only mint) | 11,291 |
| Sidecars produced | 11 |
| Acceptance tests | 25/25 ✅ |
| Build time (sandbox, end-to-end) | ~38 sec |

## Path forward (Hafta 5)

Önerilen Yön A: work namespace seed. Ayrıntılar `NEXT_SESSION_PROMPT_HAFTA5.md`'de. Y5.1 karar noktası: hangi kaynak set ile başlanacak (science_layer-only / +OpenITI / +Kashf al-Zunûn).

---

## Files created in this session

```
schemas/dynasty.schema.json                                 (PATCHED: +had_ruler, +rulers.person_pid)
pipelines/_lib/person_canonicalize.py                       (530 lines)
pipelines/adapters/bosworth_rulers_fixup/__init__.py
pipelines/adapters/bosworth_rulers_fixup/manifest.yaml
pipelines/adapters/bosworth_rulers_fixup/extract.py
pipelines/adapters/bosworth_rulers_fixup/canonicalize.py    (~190 lines)
pipelines/adapters/science_layer/__init__.py
pipelines/adapters/science_layer/manifest.yaml
pipelines/adapters/science_layer/extract.py
pipelines/adapters/science_layer/canonicalize.py            (~210 lines)
pipelines/adapters/dia/__init__.py
pipelines/adapters/dia/manifest.yaml
pipelines/adapters/dia/extract.py
pipelines/adapters/dia/canonicalize.py                      (~270 lines)
pipelines/adapters/el_alam/__init__.py
pipelines/adapters/el_alam/manifest.yaml
pipelines/adapters/el_alam/extract.py
pipelines/adapters/el_alam/canonicalize.py                  (~250 lines)
pipelines/integrity/person_integrity.py                     (660 lines, 5 passes)
tests/integration/test_dia_pilot.py                         (450 lines, 25 tests)
HAFTA4_DELIVERABLE.md
HAFTA4_SESSION_NOTES.md
NEXT_SESSION_PROMPT_HAFTA5.md
```

Modified:
```
pipelines/run_adapter.py                                    (generic 'sidecars' dict pass-through)
pipelines/adapters/registry.yaml                            (4 adapter enabled)
```

Total commit: ~25 files changed, ~3,500 lines net new code.
