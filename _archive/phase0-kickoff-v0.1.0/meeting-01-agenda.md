# İlk Toplantı Gündemi

**Proje:** islamicatlas.org Phase 0  
**Katılımcılar:** Dr. Ali Çetinkaya, Fatıma Zehra Nur Balcı  
**Tahmini süre:** 75-85 dakika  
**Önkoşul:** `docs/fatima-kickoff.md` + `docs/phase0-canonical-data-foundation.md` önceden okunmuş olmalı

---

## Zamanlama (dakika)

### 0-5 · Açılış

- Kısa tanışma (teknik background, projeyle tanışma seviyesi)
- Toplantı şeklinin onayı (bundan sonrası haftalık, 1 saat, Pazartesi)

### 5-20 · Phase 0 özet ve soru-cevap

- Ali: Phase 0'ın **neden şimdi** yapıldığının 5 dakikalık özeti (mevcut durum → hedef)
- Fatıma: doküman okumadan sonra aklına takılan **ilk sorular**
- Tartışma: timeline, scope, "bu fazla mı az mı?"

### 20-35 · Teknik mimari netleştirme

Bu bölümde aşağıdaki sorularda **açıkça karar** vermeye çalışıyoruz. Karar vermediğiniz soruları ADR olarak açıyoruz:

1. **PostgreSQL mi başka DB mi?** — Varsayım: PostgreSQL + PostGIS. Alternatif: SQLite + SpatiaLite (single-node, zero-ops). Fatıma'nın tercihi?
2. **Python framework:** FastAPI mı Django mı? — Varsayım: FastAPI (lighter, OpenAPI auto-gen)
3. **Search engine:** Typesense mi Elasticsearch mi? — Varsayım: Typesense (Türkçe/Arapça analyzer daha iyi, lighter)
4. **Deployment planı:** Phase 0 için local-only mi, yoksa staging server?
5. **Canonical store read path:** Frontend doğrudan PostgreSQL'den mi sorgulayacak, yoksa FastAPI üzerinden mi? (Varsayım: sadece API üzerinden — güvenlik + cache)

### 35-50 · Roller ve süre

- **Haftalık müsaitlik:** Fatıma'nın haftada kaç saat ayırabildiği
- **Bitirme projesi:** teslim tarihi + Phase 0 ile overlap imkânı
- **Ücret/paket:**
  - Seçenek A: Saatlik RA ücreti (örn. _____ TL/saat × _____ saat/hafta)
  - Seçenek B: Bitirme + co-authorship + referans paketi (ücret yok veya sembolik)
  - Seçenek C: Karışım
- **Bu repo bitirme projesi olabilir mi?** — Bölüm danışmanı onayı gerekli
- **İki taraflı taahhüt:** Ali'nin cevap hızı beklentisi, Fatıma'nın teslim hızı beklentisi

### 50-60 · Bu hafta ve repo erişimi

GitHub kurulumu Ali tarafından toplantı öncesi tamamlanmış olmalı (bkz. `docs/setup-github.md`). Toplantıda yapılacaklar:

- [ ] Fatıma'nın GitHub kullanıcı adı alınır → `.github/CODEOWNERS` güncellenir (sonraki PR'da Fatıma kendisi yapar)
- [ ] Fatıma davet aldıysa erişimi onaylandığı teyit edilir
- [ ] Repo birlikte gezilir (5 dk): README → `docs/` → `schema/canonical/` → `scripts/` → `audit_output_example/`
- [ ] Issue #1 birlikte açılır (veya Ali tarafından önceden açılmışsa gözden geçirilir):
  - **"Week 1 audit — local run and initial findings"** (Assignee: Fatıma)
  - Fatıma: repo'yu klonla, `week1_audit.py`'yı kendi makinende koş (`--data-dir` parametresiyle mevcut atlas repo'sunun `public/data` klasörünü göster)
  - Çıktıyı incele, `audit_output_example/` ile karşılaştır, 3-5 ilgi çekici bulgu tespit et
  - Bunu issue comment'ı olarak yaz
- [ ] Issue #2 gözden geçirilir: **"Canonical scope — which layers are in/out/auxiliary"** (Assignee: Ali)
- [ ] Issue #3 gözden geçirilir: **"ADR-001 review"** — ikimiz birlikte review ederiz

### 60-70 · Pazartesi teslim hedefi

- Fatıma: Week 1 audit issue'sunda ilk bulgular (Issue #1 comment)
- Ali: Canonical scope taslağı (Issue #2 comment veya PR)
- Gerekirse: ek issue açma (bulgulardan çıkan follow-up'lar)

### 70-80 · Son sorular ve toparlama

- Fatıma'nın geride kalmış soruları
- Ali'nin geride kalmış soruları
- Bir sonraki toplantı tarihi (default: bir hafta sonra)

---

## Kararlar dokümanı

Toplantı sonunda Ali toplantı notlarını yazacak ve `docs/meeting-01-notes.md` olarak commit edecek. Bu notlar içinde:

1. Alınan kararlar (madde madde)
2. Karara bağlanmamış, ADR'ye havale edilen sorular
3. Aksiyon maddeleri (kim, ne, ne zaman)

---

## Önceden cevaplanması yararlı olacak sorular

Fatıma bunları toplantıdan önce düşünebilirse toplantı daha verimli geçer:

1. Bu projede kafana takılan 3 soru ne?
2. Doküman okuduktan sonra endişe duyduğun 1 şey var mı?
3. Phase 0 scope'unu sadeleştirmek (trim) gerekirse hangi aşamayı ilk feda edersin?
4. Sen şimdiye kadar en büyük ölçekte hangi Python/SQL projesinde çalıştın? (Gerçekçi beklenti için)
5. Bitirme projen net mi? Yoksa bu repo o rolü üstlenebilir mi?

---

## Gerekirse not alınacak yer

```
(toplantı sırasında doldurulur)

Kararlar:
1. ___________________________________
2. ___________________________________
3. ___________________________________

ADR'ye havale:
- ___________________________________

Aksiyon maddeleri:
- [ ] @fatima — __________________ (tarih: ___)
- [ ] @ali — _____________________ (tarih: ___)
```
