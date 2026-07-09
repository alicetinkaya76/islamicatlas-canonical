# Hafta 9 — Known Issues

H9'a girişte devralınan ve H9 içinde keşfedilen konuların kaydı.
H8 ledger'ı (`docs/h8/H8_KNOWN_ISSUES.md`) mühürlü kapanış kaydıdır;
oradaki "PE-2 open" ifadesi H8 close anı için doğrudur ve geriye dönük
düzenlenmez. Güncel durum bu dosyadadır.

---

## PE-2: Schema $id coherence drift — ✅ CLOSED (H9 Stage 1)

**Kapanış tarihi:** 2026-06-11
**Kapanış commit'i:** H9 Stage 1 commit'i (bkz. `git log --oneline -1`,
`HAFTA9_STAGE_1_PE2_FIX.md` journal'ı bu commit'tedir)
**Çözüm:** 11 dosyalık schema seti tek etikete (v0.3.0) atomik bump —
38 URI geçişi (11 `$id` + 27 `$ref`) yeniden yazıldı, içerik başka
hiçbir baytta değişmedi. Set-düzeyi versiyonlama politikası ADR-013
olarak yazıldı; kalıcı koruma `test_h9_schema_set_coherence.py`
(PE2.1–PE2.4) suite'e eklendi.

**Not (sayım düzeltmesi):** H8 girdisinin başlığı "10-file schema set"
der; kendi tablosu 11 satırdır. "10", o an v0.1.0'da duran dosyaları
sayar — v0.2.0'daki `work.schema.json` on birincidir. Bu ledger'dan
itibaren doğru sayı: **11**.

## Devralınan açık işler (H8 close ledger'ından)

| ID | Konu | Severity | Durum |
|---|---|---|---|
| **AN** | Category B fuzzy match — dia_chunks'taki 4,784 non-direct slug | Medium | Open (H9 aday / H10) |
| **AO** | TDV scraping pipeline → `dia_chunks_rich.json` (cilt + sayfa + arabic_title) | High | ✅ **DONE** (H9 Stage 2a–2e; 8.093 madde, cilt/sayfa %99.94, title_ar %66.9, müellif %99.9 / 1.423 yazar; 10 review insan denetimine) |
| **AP** | dia_works rich-mint (ADR-009 eşikleri) | High | Open — **AO tamam, blok kalktı**; H10+ |

### AO kapanış notu (Stage 2e)

`data/sources/dia_chunks_rich.json` (Path 3a, lean, gövdesiz, gitignore'lu;
`scrape.py --assemble` ile yeniden üretilebilir). AP için devredilen açık
uçlar: (1) **yazar namespace** modellemesi (person vs contributor — proposal
açık soru 3/4; rich dosyada ham `author_raw` + `section_slug` var), (2) **5
online-only madde** (`muneccimbasi`, `rasathane`, `tamani-huseyin-rifki`,
`yahya-b-ebu-kesir`, `yahya-yi-sirvani`) → print cilt/sayfa yerine web-locator,
(3) **10 review vakası** (3 low-coverage / 3 title-varyant / 5 online-only) →
insan denetimi. ADR-014 izin belge referansı hâlâ `needs_human_review`
(yayından önce).

## Soft TODOs (formal issue değil)

- `schemas/dynasty.schema.json` dosya sonunda trailing newline yok
  (11 dosyadan tek istisna). Kozmetik; bu commit'te bilinçli
  dokunulmadı (diff'i yalnız URI satırlarında tutmak için). İlk uygun
  housekeeping commit'inde düzeltilebilir.
- `_common/provenance.schema.json` `$comment`'ındaki "in v0.1.0"
  ibaresi tarihsel referanstır (kuralın hangi versiyonda
  sadeleştirildiğini anlatır); bilinçli bırakıldı.
- H8'den devir: `truncate_at_sentence_boundary` için property-based
  test + hybrid-sampling pilot şablonu (H8 soft TODO'ları, hâlâ açık).

## DH-1: AppleDouble artıkları data/ altında — ✅ RESOLVED (Stage 1 kabulü sırasında)

**Tespit:** 2026-06-11, Stage 1 kabul koşusu; `test_yaqut_pilot` a2 + i
failed (a2: `._iac_place_00000001.json` ad kalıbına uymadı; i: dosya
sayımı 15.240 ≠ pid_index 15.239).
**Envanter:** 5 artık — `place/`, `person/`, `dynasty/` dizinlerinin
her birinin İLK kaydı (`._iac_*_00000001.json`), `_state`'te
`._dia_works_h6_manual_review.jsonl`, `sources`'ta
`._openiti_qid_seed.json`. Desen Quick Look/Finder önizlemesiyle
tutarlı (harici exFAT volume'de xattr → AppleDouble materyalizasyonu).
**Neden grep görmedi:** zsh `ls`/glob dot-file'ları gizler; testlerin
kullandığı Python `pathlib.glob("*.json")` gizlemez.
**Aklama:** Stash A/B — aynı 2 test pristine a41642d üzerinde aynı
mesajlarla düştü; Stage 1 schema bump'ıyla nedensel bağ yok.
pid_index (15.239) gerçek kayıt sayısıyla birebir tutarlıydı; veri
sorunu yok, fark yalnız artıklardan.
**Çözüm:** `find data -name '._*' -type f -delete`; iki test yeşil.
**Scope düzeltmesi:** H8 close'un "10 skipped" değeri geniş-scope
koşudandı (close state'in kendi "fixture topology" notu; Stage-3 satırı
74/3/3). `tests/integration/` scope'unda doğru beklenti **3 skipped**;
Stage 1 journal'ı ve Karar 1 buna göre düzeltildi.
**Soft TODO:** Finder volume'e dokundukça `._*` yeniden oluşabilir;
ileride bir hygiene commit'inde a2 + `count_files` glob'larının
dot-file'lara sertleştirilmesi değerlendirilebilir.
(DH = data hygiene serisi; PE serisi schema/pipeline errata'ya ayrık.)

<!-- Future H9-discovered issues here -->
