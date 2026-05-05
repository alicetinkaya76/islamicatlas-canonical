# ADR-009: DiA-side work records - rich-mint-only doctrine

**Status:** Accepted
**Date:** 2026-05-05
**Phase:** 0
**Decision-makers:** Ali Cetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-006 (Adapter pattern), ADR-008 (Entity resolution),
H5 Decision 1 (dia_works dropped from Hafta 5), H6 Stream 1 (Hassaf
one-off mint), H7 Stage 3 (programmatic Stream 2 deferred)

---

## Context (Baglam)

Phase 0'in sonraki adimlarindan biri, TDV Islam Ansiklopedisi'nin
(DiA) 3,369 scholar slug'inda bahsi gecen ~44,611 eseri canonical
`iac:work-*` namespace'ine eklemekti. H5 oturumunda `dia_works.json`
dosyasinin yapisal incelemesi sonucunda "upstream parser bibliography'i
'eserler' olarak cikariyor" hipotezi ortaya atildi (sample
mis-attribution rate ~%75). Bu yuzden dia_works tum hafta scope'undan
cikarildi; bunun yerine bir audit sidecar
(`data/_state/dia_works_h5_audit.json`) uretildi ve H6+ icin
"Brockelmann/GAL triangulation + DiA chunk re-extraction" yol haritasi
onerildi.

H6 Stream 1'de bir tek scholar (al-Khassaf, slug=hassaf) icin elle
zengin mint yapildi - bu mint, slug'in 6 audit-band'i arasinda sadece
1'inin (`high_validated_both_sources`) prosedure uygun oldugunu
dogruladi; geri kalan 5 title (`no_external_match_dia_only`,
`low_likely_misattribution`) mint'e dahil edilmedi. Hassaf record'unun
zenginligi (Arapca baslik, Turkce aciklama, "TDV DiA cilt 16 s. 395"
sayfa locator'i) `dia_works.json`'dan degil, DiA encyclopedia
entry'sinden manuel transcription'la geldi.

H7 Stage 3'te bu pattern'in programmatik scale edilebilirligi
arastirildi. Empirik bulgu:

1. `dia_works.json` (3,369 slug) yalnizca title-string listeleri
   tutuyor. Multilingual label, description, composition tarihi,
   sayfa locator'i yok. Per-slug payload `["Title 1", "Title 2", ...]`
   seklinde, baska hicbir alan yok.
2. `data/_state/dia_works_h5_audit.json` (44,611 title satiri) ham
   `dia_works.json`'dan esit veya daha fazla bilgi tasiyor - title
   normalization, fingerprinting, OpenITI/science_works
   cross-match'leri ekliyor; ham veriye kiyasla bilgi kaybi yok.
3. Hassaf record'unun zenginligi audit'te de yok, ham `dia_works.json`'da
   da yok. Kaynak DiA encyclopedia entry'sinin kendisi - su an
   `data/sources/dia/dia_chunks.json` (gitignored) ya da harici scraping
   ile erisilen bir kaynak.

Sonuc: audit + `dia_works.json` join'i, Hassaf'in zenginligini uretemez.
Programmatik adapter en iyi durumda (a) tek-dilli (TR) title, (b) scholar
death'inden turetilen `composition_temporal`, (c) provenance pointer
(slug + title_index), (d) author=dia_scholar_pid, (e) opsiyonel SAME-AS
pair uretebilir - bu Hassaf'in yaklasik %30'u zenginliginde sig bir
record'dur.

## Decision (Karar)

DiA-side work record'lari sadece "rich mint" doktriniyle uretilir.
Bu doktrin su kurali koyar:

> Bir DiA-side work record canonical store'a yazilabilir ANCAK VE ANCAK
> kayit en az su zenginlik esigini karsiliyorsa: (a) `labels.prefLabel`
> en az iki dilde (orn. ar + tr veya ar + en), (b) bir
> `labels.description` alani en az bir dilde, (c)
> `provenance.derived_from.page_or_locator` spesifik bir cilt+sayfa
> referansi.

Sig mint (yalnizca audit + `dia_works.json` kaynakli kayitlar) yasaktir.
Sig-mint pipeline'i yazilmaz; programmatik bir Stream 2 adapter'i,
yalniz zengin kaynak verisi (DiA encyclopedia entry full text +
structured metadata) baglandiktan sonra implemente edilir.

Yururluge giris: Bu ADR ile derhal. H7 itibariyle 1 zengin DiA-side
work record (`iac:work-00009331`, Hassaf Kitab al-Hiyal) mevcut. Ek
dia_works mint'leri H8+ scope'unda, ham veri pipeline'i kuruldektan
sonra.

Etkilenen bilesenler:

- ETL: yeni `pipelines/adapters/dia_works/` klasoru olusturulmaz
  (geriye donuk olarak Hassaf one-off
  `pipelines/_lib/build_dia_slug_to_pid.py` zaten mevcut; o sadece
  slug-PID mapping uretir, mint pipeline'i degil).
- Acceptance kriterleri: H6 master plan'in AA, AB, AG kriterleri H8+'ya
  ertelenir.
- Frontend: ADR-007 (rich entity page contract) ile uyumlu - yalniz
  zengin record'lar PersonCard "Bu yazarin eserleri" bolumunde
  listelenir.

## Alternatives Considered

### Alternative A: Sig-ama-durust mint (~10-25 record)

`audit.confidence_band == "moderate_validated_one_source"` filtresinden
gecen + 6 ek kalite filtresinden gecen ~10-25 title icin minimal field
set'iyle mint. Tek-dilli (TR) title, turetilmis composition, slug-based
provenance.

- Artilari: AC kriterini (cluster ext) ileri tasir, +25 SAME-AS pair,
  H8'de description enrichment icin iskelet hazir.
- Eksileri: Frontend'de "bos alanlar" sorunu (kapak yok, aciklama yok);
  ADR-007 rich-page-contract ile celiski; H8'de zenginlestirme pass'i
  her record icin update operasyonu demek (idempotent ama maliyet iki
  misli); academic credibility acisindan "sig veri = yari-dogru veri"
  algisi.
- Neden secilmedi: Marjinal kazanc (cluster +25), kalici mimari borc.
  ADR-007 ile celisme kabul edilemez.

### Alternative B: Sadece SAME-AS cluster, yeni record yok

Audit'in `match_in_openiti_works` non-empty'lerinden DiA-side mint
yapmadan sadece OpenITI-side mevcut record'lara SAME-AS marker ekle.

- Neden secilmedi: Yapisal olarak tutarsiz. SAME-AS en az iki uye ister;
  DiA-side record yoksa "OpenITI work-X DiA'da-da-var" claim'ini hangi
  PID'le tutacagiz?

### Alternative C: Tam-is Stream 2 (8K-25K bulk mint)

Ham DiA encyclopedia entry'lerini scrape/parse et, multilingual label
ve description cikar, batch mint et.

- Artilari: AA/AB/AG kriterlerini acar; docentlik icin "n=17K dia_works"
  cumlesi mumkun.
- Eksileri: 1-2 hafta'lik ham veri pipeline isi; H7'nin scope'u disinda.
- Neden bu ADR'de secilmedi: Bu ADR secimi bu hafta icin yapmiyor; bu
  yolu H8+ scope'una atiyor. Tam-is Stream 2 ileride bu doktrinle uyumlu
  sekilde yapilabilir.

## Consequences (Sonuclar)

### Olumlu

- ADR-007 (rich entity page contract) surdurulebilir kalir; canonical
  store'a "sig record" istisnasi girmez.
- Academic credibility korunur: yayinlanan dataset'te "her DiA-side
  work record en az iki dilde baslik + sayfa locator + aciklama tasir"
  garantisi verilebilir.
- H8'de ham DiA pipeline'i kuruldugunda mevcut record'larda idempotent
  enrichment update'i degil, tek-pass full mint calisir - hata yuzeyi
  azalir.
- ADR-006 + ADR-008 ile uyumlu: adapter pattern korunur, sig adapter
  bypass'i yapilmamis olur.

### Olumsuz / Tradeoff'lar

- AA/AB/AG acceptance kriterleri H7'de kapali kalir; H6 master plan
  revize edilmek zorunda (formal not:
  `docs/h7/H7_MASTER_PLAN_REVISION.md`).
- Frontend (Phase 0b, Fatima) icin DiA-side work gorunurlugu minimum
  duzeyde kaliyor: yalniz Hassaf'in 1 record'u gorunur.
- "Volume kazanci yok" gorintusi kisa vadede negatif. Bu trade-off
  bilincli.

### Neutral / Gelecekte revizyon gerektirebilir

- Rich-mint esigi (a)+(b)+(c) yeterince kati mi? H8'de pratik olarak
  bu esigi gecen kayit sayisi dususe, esigi gevsetmek gerekebilir.
- "Rich" tanimi ileride frontend ihtiyaclari gelistikce degisebilir.
- DiA disi tertiary_reference kaynaklar (Sezgin GAS, Brockelmann GAL)
  ayni doktrine tabi mi? Onceden acik degil.

## References

- H5 Session Notes - Decision 1 (dia_works dropped from Hafta 5)
- H6 Stream 1 commit `564f1c8` (Hassaf one-off mint)
- H7 Stage 1 commit `9ee147a` (QID quality audit)
- H7 Stage 2 commit `93927b5` (Frontend Wikidata gate)
- `data/_state/dia_works_h5_audit.json` (44,611 title, audit-only)
- `data/sources/dia/dia_works.json` (3,369 slug, sig kaynak)
- ADR-007 Rich entity page contract

---

**Revision history:**

- 2026-05-05: Ilk surum, Ali Cetinkaya (H7 Stage 3)
