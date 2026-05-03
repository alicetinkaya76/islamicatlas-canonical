---
title: "[ADR] ADR-001 review — canonical entity + attestation model"
labels: ["type:adr", "needs-discussion", "phase0-w1"]
milestone: "Week 1: Audit & Inventory"
assignees: ["alicetinkaya76", "<fatima-github-username>"]
---

## Özet

`docs/decisions/ADR-001-canonical-attestation-model.md` şu anda **Proposed** durumda. İkimiz de okuyup tartıştıktan sonra **Accepted** veya **revize** olarak işaretleyeceğiz.

## ADR neyi savunuyor?

Pleiades / Perseus modelinden uyarlanmış bir **canonical entity + attestation ayrımı**:

- Canonical entity (Place/Person/Work/Event/Dynasty/Route) → otoriter, stable URI
- Attestation → bir entity'nin bir kaynakta geçişi, surface form + locator + confidence

Bu iki tabaka, şu an dağınık olan 13 katmanı tek bir canonical model altında birleştirmek için temel yapıdır.

Değerlendirilen 3 alternatif:
- **A:** Tek tablo + source columns → yeterince genişlemez
- **B:** Triple store (RDF) + SPARQL → tool zinciri ağır, Phase 0 için fazla
- **C:** Xref dosyalarını geliştirme → çekirdek sorunu çözmez, yama

## Tartışma noktaları

Fatıma için:

- [ ] Engineering açısından attestation modelinin performans tradeoff'larını kabul ediyor musun? (58K entity + ~100K attestation PostgreSQL için ağır değil, ama sorgu karmaşıklığı artıyor)
- [ ] "Canonical coordinates" hesaplaması hangi stratejiyle olmalı? (Birden fazla kaynak farklı koordinat verirse — median, highest-reliability_tier, manual override?) → ADR-006 gerekebilir
- [ ] Attestation granularity: bir kaynaktaki "BAĞDAT" maddesi = 1 attestation (madde başına). Ama bir kronoloji metninde Bağdat 50 kere geçiyorsa — bunlar 50 attestation mı, 1 mi? Kabul: şimdilik 1 madde = 1 attestation. Manuscript IIIF eklendiğinde revize.

Ali için:

- [ ] Domain açısından attestation confidence modelinin yeterli olduğunu düşünüyor musun? (match_score + verification_status)
- [ ] Place ↔ modern yer (modern_country) bağlantısı kritik mi, yoksa Phase 1'e ertelenebilir mi?
- [ ] İhtilaf görselleştirmesi Phase 0 sonunda API'da olabilir mi, yoksa sadece data modelde mi?

## Karar

Bu issue'da tartışma → onay → ADR status güncelleme (`Proposed` → `Accepted`).

Karar sonrası:
- [ ] PR ile ADR dosyasındaki status satırı güncellenir
- [ ] İlgili issue'lar (tüm Week 2+ şema işi) bu ADR'ye referansla ilerler

## İlgili

- `docs/decisions/ADR-001-canonical-attestation-model.md`
- Master plan §3.1-3.3
- Referanslar: Pleiades conceptual overview, Syriaca.org model
