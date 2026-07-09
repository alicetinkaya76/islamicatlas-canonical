# Hafta 9 — Stage 5: Hijyen + dış-yüz dokümantasyonu + Phase-0 closeout haritası

**Date:** 2026-07-07
**Branch:** hafta5-work-namespace
**Entry:** Stage 3-4'ün üstüne; incelemenin hygiene/docs/roadmap bulguları.

---

## Bu stage ne yapar

### A. Kök dizin arşivi (git mv — tarihçe korunur)

- `HAFTA2_DELIVERABLE.md` → `docs/h2/`; `HAFTA3_DELIVERABLE.md` → `docs/h3/`;
  `HAFTA4_{DELIVERABLE,PATCH_NOTES,SESSION_NOTES}.md` → `docs/h4/`
  (H5+'ın `docs/hN/` düzenine geriye dönük uyum).
- `NEXT_SESSION_PROMPT*.md` ×4 (en yenisi H5'i hedefliyordu; proje H9'da) +
  `mac_h5_context_zip.sh` (tek-seferlik H5 aracı) → `_archive/root/`.

### B. Tekrarlanan veri temizliği (git rm — 13,3 MB)

`cmp` ile bayt-özdeş doğrulanan 4 çift; manifest'ler yalnız KÖK kopyaları
referans alıyor (commit öncesi grep ile yeniden doğrulandı):
`data/sources/alam/alam_lite.json`, `data/sources/dia/dia_lite.json`,
`data/sources/dia/dia_alam_xref.json`,
`data/sources/yaqut/yaqut_alam_crossref_enriched.json` silindi
(kök eşleri kalır).

### C. Şema-seti mikro-hijyeni

- `dynasty.schema.json` dosya-sonu newline (11 dosyadan tek istisnaydı;
  H9_KNOWN_ISSUES soft TODO). `$id` değişmedi → ADR-013 gereği bump yok.
- Bekçi: `test_h9_schema_set_coherence.py::test_pe2_5_every_schema_file_ends_with_newline`.

### D. Kayıt-düzeltmeleri (ADR'lerde)

- **ADR-013:** "registry-based $ref resolution"un ADR-002'ye yanlış atfı
  düzeltildi (mekanizma kodda yaşar — `run_schema_tests.build_registry`;
  ADR-002 = Authority Reconciliation) + ADR-010/H8'in "future ADR-011"
  öngörüsü için numara notu (ADR-014 kalıbı). Revision history'ye kayıt.
- **registry.yaml:** başlıktaki var-olmayan `run_all_adapters.py` iddiası
  gerçekle değiştirildi; `openiti` id'si → `openiti-works` (manifest'le
  eşleşmiyordu), eksik `science-works` girdisi eklendi. Bu eşleşmezliğin
  ölçülmüş sonucu: 9.330 work kaydının provenance'ında jenerik
  "canonicalize_work" — ileriye dönük düzeldi; mevcut kayıtların migration'ı
  PHASE0_CLOSEOUT §2'de (düşük öncelik).

### E. Dış yüz güncellemeleri

- **README:** Status v0.1.0/7 ADR/18 test kalıntısından → v0.3.0 seti, 14 ADR,
  46.702 kayıt (koddan sayıldı), 12 adapter, `make test`/`make test-fast`,
  gerçekleşen-fazlı aktivasyon tablosu, PHASE0_CLOSEOUT bağlantısı.
- **CHANGELOG:** boş [Unreleased] → H2→H9 hafta-hafta retrospektif (sayılar
  journal'lardan, SHA'lar commit grafiğinden — fabrikasyon yok); proje-sürümü
  ekseni ile ADR-013 schema-set etiketinin ayrı eksenler olduğu notu.
- **CONTRIBUTING:** PR+karşılıklı-review protokolünün fiilî solo-workflow'la
  ilişkisi netleştirildi (H9 kapanışında main'e merge planı).

### F. `docs/PHASE0_CLOSEOUT.md` (yeni — bu stage'in ana teslimatı)

"Faz 0'ı bitirme"nin 6+ dokümana dağılmış kalemleri tek sıralı, sahipli
listede: H9 close → AP (ADR-009 v1.1 kararı + yazar-namespace kararı + 10
review vakası) → onarım koşuları (el-alam re-run, phantom audit) → AN →
Faz 0.5 (İSAM belge referansı = tek sert dış blokör; ontoloji bakımı; w3id;
v1.0.0; canlı Typesense; QID audit; Zenodo). ADR-013'ün atıf yaptığı ama hiç
yazılmamış "Faz 0.5 roadmap" boşluğunu doldurur.

## Bu stage ne YAPMAZ

- `docs/h8/*` mühürlü — dokunulmadı (H8'e dair düzeltmeler ADR-013 numara
  notu + H9 ledger'ları üzerinden).
- Ontoloji/context'e dokunulmadı (şema enum'uyla bağlı Tabaqa çözümü v0.4.x
  set-bump kararına bağlı — Faz 0.5 kalemi).
- Şema seti v0.3.0'da (newline byte'ı içerik değil).
- Canonical/dia_chunks.json/tag yok.

## Kabul

- [x] Kök dizinde yalnız güncel dosyalar (README, CHANGELOG, CONTRIBUTING,
      LICENSE, Makefile, requirements.txt, pytest.ini, config*).
- [x] `git status` temiz gürültüsüz (`tmp/` artık gitignore'da).
- [x] README/CHANGELOG'daki her sayı koddan/journal'dan üretildi.
- [x] `make test` yeşil (145/2/3 + CLI'lar) — taşımalar hiçbir yolu kırmadı.

## Rollback

Tek revert: mv/rm'ler geri döner (git rename-takibi), doküman güncellemeleri
ve PHASE0_CLOSEOUT birlikte kalkar. Veri riski yok (silinen 4 dosya bayt-özdeş
kopyalardı; kökteki asılları duruyor).
