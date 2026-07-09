# H7 Master Plan Revision — formal deferral of AA/AB/AG to H8+

**Date**: 2026-05-05
**Trigger**: ADR-009 (DİA-side rich-mint-only doctrine)
**Affected criteria**: AA, AB, AG (master plan H6 scorecard)

---

## Background

H6 master plan'ın 8 acceptance kriterinden 3'ü dia_works mint scope'una
bağlıydı:

| ID | Criterion | H6 status |
|---|---|---|
| AA | dia_works mint 8K-25K | DEFERRED |
| AB | dia_works valid `provenance.source_id` | DEFERRED |
| AG | 5-10 yeni dia_works test | DEFERRED |

H6 close'da "DEFERRED" durumu **gayri resmi**'di: kapalı ama gerekçesi
sadece scope-management ("Stream 2 4-6 saatlik session'a sığmaz") idi,
kalıcı bir doktrine yaslanmıyordu.

H7 Stage 3'te yapılan empirik keşif (kaynak verinin sığlığı + Hassâf
zenginliğinin elle-transcribe edilmiş olması) **H5 Decision 1**'in
("dia_works dropped, ham re-extraction gerek") doğru olduğunu doğruladı
ve bu doğrulama ADR-009 olarak mimari kararla kalıcılaştırıldı.

Bu doküman, AA/AB/AG'nin **formal** ertelemesini master plan kayıt
düzeyinde gerçekleştirir.

---

## Revision

### AA — dia_works mint 8K-25K

**Pre-H7 form**: "H6 sonuna kadar 8K-25K dia_works canonical record
mint edilmiş olacak."

**Post-H7 form**: "Bu kriter, ADR-009 rich-mint doktrini şartlarını
sağlayan kayıt sayısı için yeniden tanımlanır. Önceki '8K-25K' hedefi,
ham `dia_works.json`'un sığlığı ve `dia_chunks.json` veya
denkleştirilmiş ham DİA encyclopedia kaynağının erişilebilirliği
varsayılarak konmuştu; bu varsayım H7 Stage 3'te yanlışlandı.

Yeni hedef: H8 oturumunda ham DİA encyclopedia kaynağı (chunk
re-extraction veya benzeri) bağlandıktan sonra, **rich-mint doktrini
karşılayan** kayıt sayısı ölçülür ve master plan'a o sayı (örn. 'H8+
ham veri pipeline'dan ≥ N rich record') yazılır. Sayı hedefi şimdilik
açık (boş)."

### AB — dia_works valid `provenance.source_id`

**Pre-H7 form**: "Mint edilen tüm dia_works kayıtları
`provenance.source_id` taşıyacak."

**Post-H7 form**: "ADR-009 rich-mint doktrini bu kriteri zaten içerir
(rich-mint şartı (c): `provenance.derived_from.page_or_locator`
spesifik cilt+sayfa). Bu nedenle AB ayrı bir acceptance kriteri olarak
gerekli değildir; ADR-009 conformance check'inin alt-koşulu olarak
absorbe edilir. AB kriteri **deprecated** edilir, master plan'dan
çıkarılır."

### AG — 5-10 yeni dia_works test

**Pre-H7 form**: "H6 sonu test suite'ine 5-10 yeni dia_works integration
test eklenecek."

**Post-H7 form**: "Test eklenmesi mint pipeline'ı ile eş-zamanlı yapılır
(ADR-006 6.1 adapter sözleşmesi gereği). Yeni hedef: H8'de rich-mint
pipeline'ı çalıştığında 5+ integration test eklenir; testler
ADR-009 conformance'ı (multilingual labels, description, page locator
mevcudiyeti) ölçer. Sayı hedefi 5-10 olarak korunur."

---

## H8 implications

ADR-009 ile uyumlu Stream 2 implementasyonu için H8'in ilk adımı:

1. **Ham DİA encyclopedia kaynağına erişim**:
   - Seçenek 1: `data/sources/dia/dia_chunks.json` (gitignored, var mı kontrol)
   - Seçenek 2: TDV İslam Ansiklopedisi web scraping (ratelimited politely)
   - Seçenek 3: Kullanıcının elindeki PDF/structured data (manual ingest)
2. **Rich-mint adapter**: `pipelines/adapters/dia_works/` klasörü
   ADR-006 6.1 sözleşmesiyle açılır (extract + resolve + canonicalize +
   manifest). ADR-009 conformance check her record write'ından önce
   uygulanır.
3. **Pilot batch**: ilk 50-100 slug için rich-mint, sample inspect,
   acceptance kalibre.
4. **Bulk run**: pilot kalitesi geçtikten sonra full 3,309 slug.
5. **Test suite**: ADR-009 conformance test'leri eklenir, AG kriteri
   karşılanır.

Tahmini H8 süre: dia_chunks erişilebilirse 6-10 saat; scraping gerekiyorsa
2 ayrı session.
