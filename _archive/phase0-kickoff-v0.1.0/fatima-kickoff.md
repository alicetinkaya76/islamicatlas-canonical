# Fatıma'ya Hoş Geldin — islamicatlas.org Phase 0

**Tarih:** Nisan 2026  
**Kimden:** Dr. Ali Çetinkaya  
**Kime:** Fatıma Zehra Nur Balcı  
**Konu:** Phase 0 ortak çalışma brifingi

---

## 1. Projenin Hikâyesi

islamicatlas.org, Bosworth'un *The New Islamic Dynasties* veritabanından başlayıp son 18 ayda giderek genişleyen bir dijital atlas projesi. Bugün 13 katmanda yaklaşık **58.000 entity** barındırıyor:

- **Yâkût'un Muʿcamü'l-Büldân'ı** (12.954 coğrafi giriş — klasik İslam coğrafyasının ana kaynağı)
- **Ziriklî'nin al-Aʿlām'ı** (13.940 biyografi — İslam tarihi biyografi referansı)
- **DİA** (8.528 madde — Türkiye Diyanet Vakfı İslam Ansiklopedisi)
- **Brill EI-1** (7.568 madde — ilk İngilizce ansiklopedi)
- **Le Strange, Muqaddasî, Maqrizi, Evliya Çelebi, İbn Battuta** atlasları
- **Salibiyyat** (Haçlı seferleri, 790 olay + 24 kale)
- **Science Layer** (182 âlim, 37 kurum, bilgi transfer yolları)
- **DarpIslam** (3.381 sikke basım yeri)
- **Konya + Kahire city atlas'ları** (toplam 1.384 yapı)

Proje **görselleştirme** olarak iyi bir yere ulaştı. Ama burada şöyle bir çatal var: ya bu mevcut seviyede kalmaya devam edeceğiz (güzel bir web sitesi), ya da akademik araştırma altyapısına dönüştüreceğiz (Pleiades, Perseus seviyesinde). İkincisi için atlas'ın **altında yatan veri mimarisini** baştan düşünmek gerekiyor. Phase 0 tam olarak bu — görsele hiç dokunmadan, altyapıyı sağlam bir canonical veri modeline taşımak.

## 2. Neden Sen?

Açık konuşayım: bu projede en kritik eksik bugün bende olmayan bir şey. Ben akademisyen olarak domain (İslamic studies + DH) biliyorum; Python/ETL/JSON Schema/PostgreSQL mimarisini de öğrendim — ama sistem yazılım mühendisliği disiplini için yanımda bir eş-lead'e ihtiyacım var. Kod review, CI/CD, idempotent ETL, migration disipliniyle gelen bir mühendis.

Sen BilgMüh son sınıfsın ve yetenekli bir öğrencisin. Bu projede sen mühendislik omurgasısın; ben domain otoritesi. İşbölümü tam olarak bu — ne senin akademik İslamic studies bilgisi üretmeni bekliyorum (o benim alanım), ne de benim senin yerine Alembic migration yazmamı (o senin uzmanlık yolun).

## 3. Phase 0'ın Özeti

Detaylı plan `phase0-canonical-data-foundation.md`'de — lütfen ilk toplantıdan önce baştan sona oku. Bir cümlelik özet: **Pleiades'in yer modelini, Perseus'un kişi modelini İslam medeniyeti verisine uyarla; mevcut 47 heterojen veri dosyasını tek canonical şema altında birleştir; üstüne API + search + LOD bağlantıları kur.**

Tahminî süre: 6-8 hafta. Bu senin part-time (haftalık ~20-25 saat) çalışmanı varsayıyor. Tam zamanlı olursan 4-5 haftaya iner. Sen belirle.

## 4. Senin Rolün Tam Olarak Nedir?

### Aşina olman beklenen / öğrenmen gereken araçlar

- **Python 3.11+** — pandas, pydantic v2, fastapi, sqlalchemy, jsonschema
- **PostgreSQL 16 + PostGIS 3.4** — spatial extension
- **Alembic** — DB migration framework
- **Docker Compose** — local dev
- **Git + GitHub PR workflow** — bunu zaten biliyorsun
- **GitHub Actions CI** — lint/test/validate pipeline
- **Typesense** (veya Elasticsearch) — search engine
- **JSON-LD temelleri** — sadece okuyabilecek kadar, derin uzmanlık değil

Bunlardan 3-4 tanesini zaten biliyorsundur. Diğerleri için: her biri için 1-2 saatlik bir tutorial yeterli. Aşağıda kaynak listesi var.

### Haftalık teslim edilecek işin yapısı

| Hafta | Senin ana işin |
|---|---|
| 1 | `week1_audit.py` çalıştır, kendi makinende veriyi tara, çıktı rapor PR'ı aç |
| 2 | Canonical schema'ları tamamla (4 ek schema + pydantic modelleri) |
| 3-4 | Entity resolution pipeline + manuel doğrulama UI (Streamlit) |
| 5 | Docker compose + PostgreSQL/PostGIS + Alembic migrations + ETL runner |
| 6 | FastAPI endpoints + derivative builder (geri uyumluluk) |
| 7 | Typesense indexer + facet config |
| 8 | Regression test suite + Zenodo dump hazırlığı |

Her haftanın sonunda bir deliverable var; her deliverable bir GitHub issue olarak yazılı olacak.

### Senin yapmayacağın şeyler

- Domain kararları (hangi kaynak canonical, nasıl transliterasyon, madhab taksonomi). Bunlar bende.
- Mevcut React frontend'e dokunma. Phase 0 pure backend/veri.
- Yeni veri katmanı ekleme. 13 mevcut katman zaten yeterli iş.
- Yayın (paper) yazımı — çekirdek yazarlık bende, ama sen ikinci yazar olarak methodology section'a katkı yapacaksın (bkz. §7).

## 5. Çalışma Protokolü

### Repo

`alicetinkaya76/islamicatlas-canonical` — private. Ben owner + admin, sen **Maintain** rolü (PR yönetim, issue/label triage, repo ayarlarını sınırlı düzeyde değiştirme yetkisi; destructive aksiyon yok). Bu rol mühendislik olarak tam yetki demek; bir öğrenciye verilebilecek en üst seviye güven rolü. Ana atlas repo'suna **hiç dokunmuyoruz** — Phase 0 bittiğinde canonical derivative'lar oraya merge olur.

İkimiz de `main`'e direct push yapamayacağız — admin dahil herkes için branch protection aktif.

### PR disiplini

- Her değişiklik feature branch'te. `feat/er-pipeline`, `fix/uri-slugify`, `docs/readme-update` gibi.
- En az 1 review zorunlu (ikimiz varız, karşılıklı review zorunlu).
- CI pipeline (GitHub Actions) her PR'da şunları koşar:
  - `ruff format --check` (Week 1 soft, Week 2'den itibaren strict)
  - `ruff check` (lint)
  - JSON Schema dosyalarının doğruluğu
  - `pytest` (Week 2'den itibaren)
  - `mypy --strict` (Week 2'den itibaren yeni modüller)
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `test:`. Ayrıntı → `CONTRIBUTING.md`
- Merge: **squash merge** (tek commit main'e düşer)

Davranış rehberi, branch adlandırma, commit mesaj örnekleri — tümü `CONTRIBUTING.md`'de. Lütfen ilk PR'dan önce göz at.

### GitHub altyapısı

- **Labels:** `phase0-w1..w8`, `type:audit/schema/er/etl/api/infra/docs/adr`, `needs-discussion`, `blocked`, `good-first-issue`, `decision-needed`
- **Milestones:** Week 1 → Week 7-8 (senin teslim tarihlerin)
- **Kanban:** GitHub Projects — `Backlog → This Week → In Progress → Review → Done`
- **Discussions:** açık (paper tartışması, büyük mimari soru)
- **ADR'ler:** `docs/decisions/` altında — büyük kararlar burada yazılı kalıyor

### İletişim

- **Haftada 1 saat senkron** — Pazartesi sabah 10:00 Konya saati (esnek). Google Meet.
- **Async** — WhatsApp/Slack kısa sorular için.
- **Büyük kararlar GitHub'da** — Issue veya PR yorumu. Mesajlaşmada kalan karar kayıp karardır.

### Saat/ücret

Bunu birinci toplantıda netleştirelim. Seçeneklerimiz:
- **Saatlik ücret** — bir RA ücreti (Konya şartlarına göre tartışırız)
- **Bitirme projesi + yazarlık paketi** — bu repo senin bitirme projen olur; senin CS danışmanın Ali (bitirme projesi danışmanlığı akademik formalite), paper'da ikinci yazar, referans mektubu

İkinci seçenek uzun vadede daha değerli olabilir (portfolio + yayın + network). Ama senin durumun senin bildiğin şey; mali gereksiniminiz birinci seçeneği zorunlu kılıyorsa onu ayarlarız.

## 6. Öğrenme Kaynakları

Toplantı öncesi (2-3 saat yatırım, opsiyonel ama çok tavsiyeli):

### Temel okuma (zorunlu, ~45 dk)

- **Pleiades Place model:** https://pleiades.stoa.org/help/conceptual-overview
- **Perseus Digital Library about page** (kısa) — nasıl atıf veriyorlar, neden "editable"
- `phase0-canonical-data-foundation.md` (bu repo)

### Teknik tutorial'lar (gerektikçe, Week 2'den itibaren)

- **Pydantic v2 docs** — https://docs.pydantic.dev/
- **FastAPI tutorial** — https://fastapi.tiangolo.com/tutorial/
- **Alembic tutorial** — https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **Typesense quickstart** — https://typesense.org/docs/guide/

### Kavramsal (bonus, Week 3+ için)

- **Entity resolution — Winkler'in "Overview of Record Linkage" makalesi** (8 sayfa, klasik)
- **JSON-LD 1.1 primer** (W3C, 30 dk okuma)
- **CIDOC-CRM quick intro** — https://www.cidoc-crm.org/

Bunların tümünü okuman şart değil; ihtiyacın oldukça dön. Önemli olan Phase 0'ın genel çerçevesini kavramak — detaylar koşarken çözülür.

## 7. Yayın Perspektifi

Phase 0 iyi yapılırsa bir **infrastructure paper** çıkıyor. Hedef dergiler: ACM JOCCH, Digital Scholarship in the Humanities, ACM TALLIP, Digital Humanities Quarterly.

Senin katkın substantive olduğu için **ikinci yazar** olarak yer alacaksın. Bu bir öğrenci için **ciddi bir şey**: BilgMüh lisans aşamasında SCI-indexed journal'da ikinci yazar olarak yayın — akademiye devam etmek istiyorsan ilk önemli publication line'ın. Endüstriye gidecek olsan bile, mühendislik pozisyonları için impact'i var.

Paper'ın methodology section'ını (Entity Resolution pipeline, canonical schema design, migration ETL) yazmak sana düşecek. Intro + related work + conclusion bende. Ortak yazılacak bölümler de olacak. Paper draft'ı Week 7-8'de başlayacak.

## 8. Bitirme Projesi Bağlantısı

Eğer bitirme projesi 2026 Mayıs/Haziran'a kadar teslim ediliyorsa (bunu confirm et), Phase 0'ın scope'u senin bitirme projenin de omurgası olabilir:

**Proje adı önerisi:** "Türkçe-Arapça dijital kültür mirası için kanonik veri modeli ve varlık çözümleme hattı"

**Alt başlıklar:**
- Heterojen kaynaklarda Arapça/Osmanlıca isim normalizasyonu
- Fuzzy matching + LLM-assisted entity resolution
- Pleiades benzeri attestation modelinin TK-AR bağlamına adaptasyonu
- Açık veri altyapısı ve FAIR ilkeleri

Senin danışmanın (bölümündeki resmi danışman) bu scope'u onaylarsa, bu ikimiz için de kazan-kazan. Ben senin de facto bitirme eş-danışmanı olurum; formal danışman bölümündeki hocan olur. Bu bir protocol meselesi, toplantıda konuşalım.

## 9. Kickoff Checklist

Toplantıdan önce:

- [ ] GitHub collaboration davetiyesini kabul et (email'ine düşecek — `alicetinkaya76/islamicatlas-canonical`)
- [ ] `README.md`'ye göz at (projenin 1 sayfalık özeti)
- [ ] `phase0-canonical-data-foundation.md`'yi baştan sona oku (20-30 dk)
- [ ] `CONTRIBUTING.md`'yi oku (gündelik iş akışı — 10 dk)
- [ ] `schema/canonical/*.schema.json` dosyalarına bak (5 dk) — yapıyı gör
- [ ] `scripts/week1_audit.py`'yı göz at (10 dk) — kod stili ve yorumlar hakkında fikir edin
- [ ] `audit_output_example/summary.md`'ye bak (5 dk) — scriptin ne ürettiğini gör
- [ ] Pleiades'e 10 dakika bak — https://pleiades.stoa.org/ — bir yer kaydına tıkla, nasıl organize ettiklerini incele
- [ ] İlk toplantı gündemini (`meeting-01-agenda.md`) oku

Toplantıya getir:

- GitHub kullanıcı adın (CODEOWNERS dosyasına ekleyeceğim)
- Sorular (mimari, teknoloji seçimleri, timeline, senin endişelerin)
- Saat müsaitliğin (hangi günler/saatler çalışabiliyorsun)
- Bitirme projesi teslim tarihi
- Tercihler (çalışma saati, ücret/paket seçimi, kod stili)

## 10. Son Söz

Bu proje beni aşan ölçüde; tek başıma Phase 0'ı yapabilirim ama yanlış yapacak veya çok yavaş yapacağım. Senin girişimin kritik. Karşılığında ben de sana anlamlı bir domain + publication deneyimi vereceğim. Bu bir **öğrenci işi** değil — gerçek bir DH altyapı projesinde eş-lead olarak çalışacaksın.

Sorular, endişeler, "bu olmaz bence" dediğin şeyler — her şeyi açıkça söyle. Ben domain otoritesiyim; sen mühendislik otoritesisin. Orada senin `no` dediğin şey `no`'dur.

Görüşmek üzere.

— Ali
