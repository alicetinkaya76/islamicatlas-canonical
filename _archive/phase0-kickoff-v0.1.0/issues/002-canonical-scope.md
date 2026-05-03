---
title: "[Phase 0 — Week 1] Canonical scope — which layers are in/out/auxiliary"
labels: ["phase0-w1", "type:docs", "decision-needed"]
milestone: "Week 1: Audit & Inventory"
assignees: ["alicetinkaya76"]
---

## Hedef

`audit_output/summary.md`'deki 47 dosyanın her birini 4 kategoriye yerleştirmek:

- **in-scope canonical** — canonical store'a migrate edilecek
- **auxiliary** — ETL'de yardımcı lookup (xref, geo), canonical değil
- **backup-delete** — yedek/duplicate, silinecek
- **defer-to-phase-1** — Phase 0'da bekletilir, Phase 1'de değerlendirilir

Bu karar Week 5 ETL'in "hangi kaynak canonical'a nereden giriyor" haritasıdır.

## Arka plan

`docs/canonical_scope.md` template olarak hazırlandı — kategori tabloları + ilk önerilerim orada. Bu issue o dokümanı bitirmenin kaydı.

## Adımlar

- [ ] `docs/canonical_scope.md`'deki tüm hücreleri doldur (karar + gerekçe)
- [ ] 5 açık sorunun her birine ilk görüş ver:
  1. `darpislam_detail_*.json` attestation mı Place detail mi?
  2. Cairo + Maqrizi overlap — ER stratejisi
  3. Science Layer vs al-Aʿlām vs scholars.csv overlap — ER stratejisi
  4. DİA madde karışıklığı — `c1` alanı yeterli mi yoksa sınıflandırıcı mı?
  5. Konyapedia reliability tier — silver mi bronze mı?
- [ ] Source registry için 13 kaynağın tam bibliyografik kaydını hazırla (ISBN/DOI dahil)
- [ ] PR olarak aç, Fatıma'dan review al
- [ ] Varsa ADR gerektiren sorular için yeni ADR issue'ları aç

## Karar kriterleri

- **in-scope** kararı verilirken:
  - Kaynak canonical entity (Place/Person/Work/Event/Dynasty/Route) tipinde mi?
  - Kayıt sayısı ≥ ~30 mı? (Çok küçük setler için Phase 1'e ertelemek makul)
  - Veri kalitesi makul mü? (audit'teki ID tekilliği, koordinat kapsaması, vs.)

- **auxiliary** kararı:
  - Xref/mapping dosyası mı? (`*_xref.json`)
  - Yalnız geo veya yalnız ilişki mi? (`dia_geo`, `dynasty_analytics`)
  - Dict-of-arrays edge listesi mi? (`dia_relations`, `ei1_relations`)

- **backup-delete**:
  - İsimde `_backup`, `.bak`, `_old` kalıbı varsa
  - İçerik hash çakışması varsa (audit'in tespit ettiği)
  - `src/data/` ve `public/data/` de aynı dosya varsa biri

## Definition of done

- [ ] `docs/canonical_scope.md` tam dolu, PR merge edildi
- [ ] Source registry taslağı çıktı
- [ ] Açık sorular ya cevaplandı ya ADR'ye havale edildi
- [ ] 5+ in-scope canonical katman net — Week 5 ETL'in başlama hazırlığı

## İlgili

- `docs/canonical_scope.md` (bu issue'nun deliverable'ı)
- `audit_output/summary.md` (karar dayanağı)
- ADR-001 §3.2 canonical entity tipleri
