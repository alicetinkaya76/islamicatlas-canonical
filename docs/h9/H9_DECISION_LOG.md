# Hafta 9 — Karar Logu

Hafta 9 boyunca alınan mimari/operasyonel kararların kaydı. Yapı, H8
karar logu ile aynıdır: her karar Bağlam / Karar / Gerekçe / Sonuç
bölümleriyle yazılır. ADR gerektiren kararlar ayrıca
`docs/decisions/` altında ADR olarak formalize edilir.

---

## Karar 1 — Schema setini tek versiyon etiketine (v0.3.0) atomik bump

**Tarih:** 2026-06-11
**Stage:** 1
**İlgili ADR:** ADR-013

### Bağlam

PE-2 (H8 Stage 1'de loglandı): 11 dosyalık schema setinde `$id`
versiyon etiketleri tutarsız — 10 dosya v0.1.0'da, `work.schema.json`
H6'dan beri v0.2.0'da; üstelik h8_001 (digital_corpus enum) ve h8_002
(maxLength 50K) `_common` şemalarının *davranışını* değiştirdiği halde
v0.1.0 etiketi donmuş durumda. Tüm `$ref`'ler v0.1.0 URI'lerine işaret
ediyor (work dahil — v0.2.0'lık dosya v0.1.0 bileşen ref'liyor).
Doğrulama davranışını etkilemiyor (ADR-002 registry diskten `$id` ile
eşliyor) ama dokümantasyon, reproducibility iddiası ve Faz 0.5 w3id
yayını açısından `$id`'ler yalan söylüyor.

### Karar

Set-düzeyi semver (ADR-013): 11 `$id` + 27 `$ref` = 38 URI geçişi tek
commit'te v0.3.0'a yazılır. Hedef etiket v1.0.0 **değil** v0.3.0.
Kalıcı koruma olarak `tests/integration/test_h9_schema_set_coherence.py`
(PE2.1–PE2.4) eklenir; beklenen etiket testte sabitlenir (ADR-013 R4).
PE-2 girdisinin önerdiği tek-seferlik `h9_001` doğrulama script'i
yerine pytest-kalıcı invariant seçilmiştir ("test-as-documentation"
disiplini — koruma her suite koşusunda yeniden kanıtlanır).

### Gerekçe

v1.0.0 stabilite taahhüdüdür: `manuscript`/`event` forward-declared
iskelet, AP (H10+) `work.schema`'ya dokunacak, roadmap v1.0.0'ı zaten
Faz 0.5'e ayrı milestone olarak koymuş. v0.3.0, herhangi bir dosyanın
şimdiye dek taşıdığı her etiketten (v0.1.0, v0.2.0 ve h8_001/h8_002'nin
ima ettiği v0.2.1/v0.2.2) kesin büyük olan en küçük etiket. Cerrahî
metin değişimi (re-dump değil) diff'i yalnızca `$id`/`$ref` satırlarına
sınırlar; dosya başına beklenen-eski-durum probe'u + yazım öncesi
11-dosya ön taraması atomikliği garanti eder.

### Sonuç

- 11 schema dosyası v0.3.0'da, `$ref` grafiği `$id` setiyle birebir.
- ADR-013 yazıldı; v1.0.0 yolu tanımlı bir eylem haline geldi.
- Suite +4 (PE2.1–PE2.4); beklenen toplam 85 passed / 3 skipped /
  3 xfailed.
- PE-2 KAPANDI (`docs/h9/H9_KNOWN_ISSUES.md`); H8 dokümanları mühürlü
  kapanış kaydı olarak dokunulmadan bırakıldı.

## Karar 2 — AO scraping: compliance hard gate + Phase-0 doğrulama

**Tarih:** 2026-07-06
**Stage:** 2a
**İlgili ADR:** ADR-014

### Bağlam

AO, `dia_chunks_rich.json` (cilt+sayfa, Arapça başlık, müellif) üretmek için
`islamansiklopedisi.org.tr`'den madde-başı metadata scrape eder. Proje
akademik; TDV verisi meşruiyetle kullanılmalı. Compliance-first hard gate:
robots.txt + ToS doğrulanmadan ve ADR yazılmadan tek istek atılmaz.

### Karar

robots.txt YEŞİL (`Allow: /`, Disallow/Crawl-delay yok). Kullanım Şartları
(İSAM) açık yazılı izin olmadan çoğaltma/işleme/derlemeyi yasaklıyor ve
"kaynak gösterilse dahi" yetersiz sayıyor → ToS, izinsiz KIRMIZI. Maintainer
(ORCID 0000-0002-7747-6854) İSAM yazılı izninin mevcut olduğunu teyit etti →
**koşullu GO** (ADR-014). Koşul: iznin resmî belge referansı ADR-014'e
eklenecek, o ana dek `needs_human_review`; türetilmiş veri seti yayımı
referanssız yapılamaz. Nezaket ≤1 istek/2 sn, tanımlayıcı UA; ham HTML
git'e/canonical'a girmez.

Ek olarak Phase-0 canlı örneklem (9 distinct slug) feasibility'i doğruladı:
URL deseni kök-seviye `/<slug>` (proposal'ın `/madde/<slug>` tahmini 404);
slug'lar `dia_chunks.s` ile birebir stabil; selector'lar (`h1`,
`div.arabic_title`, `.ak-muellif span.val`, cilt/sayfa künye deseni)
sağlam; hassaf 16/395 = ADR-009. Çok-parçalı maddeler article-part başına
müellif+cilt/sayfa taşıyor → yazar liste olarak toplanacak.

### Gerekçe

robots erişimi, ToS ise kullanım/telifi düzenler; robots'un izni ToS
kısıtını kaldırmaz. İzinsiz scraping akademik meşruiyeti ve dataset'in
yayımlanabilirliğini riske atardı (predecessor dersleriyle uyumlu). Belge
referansının `needs_human_review` bırakılması North Star'ın "kanıtsız iddia
etme / fabrikasyon yok" ilkesinin gereği. Phase-0'ın önden yapılması, 2b
parser'ının doğru URL deseni ve selector'lar üzerine kurulmasını sağlar.

### Sonuç

- ADR-014 yazıldı (robots + ToS + izin dayanağı + Phase-0 özeti).
- Gate GEÇTİ; 2b (scaffold) açıldı. Kod/veri dokunulmadı → suite 85/3/3,
  schema 15/15 değişmedi.
- Açık koşul: izin belge referansı (kullanıcı, yayından önce).

## Karar 3 — AO scaffold: source-üreten adapter (run_adapter'a bağlı değil)

**Tarih:** 2026-07-06
**Stage:** 2b
**İlgili ADR:** ADR-006 (sapma gerekçesi), ADR-009, ADR-014

### Bağlam

Proposal §Phase 2 AO'yu "ADR-006-uyumlu manifest+extract+resolve+canonicalize
dört dosya" olarak tarif eder. Ancak (a) `extract.py` sözleşmesi açıkça "No
network calls; deterministic" der; (b) `run_adapter.py` `target_namespaces` +
`schemas/<ns>.schema.json` + `data/canonical/<ns>/` yazımı zorunlu kılar. AO
ise ağ isteği yapan ve canonical değil **source** (`dia_chunks_rich.json`)
üreten bir iştir → bu iki sözleşmeyle uyumsuz. (Kullanıcı önerimi onayladı.)

### Karar

- AO, `pipelines/adapters/dia_tdv_scrape/` klasöründe **bağımsız `scrape.py`
  CLI**'ı olarak yaşar; `run_adapter.py`'ye bağlanmaz. `parse.py` ağdan ayrık
  ve offline test edilir. `manifest.target_namespaces: []` bilinçlidir →
  `run_adapter` reddeder (kazayla çağrılma guard'ı). Registry'ye priority 330,
  enabled:false (görünürlük/provenance için).
- **Kapsam: 8.093 distinct slug** (19.742 chunk değil). Tüm slug'lar çekilir
  (yalnız Cat A değil) — cilt+sayfa madde-başıdır ve hem person-locator
  boşluğunu hem gelecekteki work-mint'i besler.
- **Rich dosya = yalın sidecar** (Path 3a): slug-anahtarlı, yalnız yeni
  olgusal alanlar (`title_ar`, per-part `cilt/sayfa/author_raw/section/baski`),
  gövde `t` TEKRARLANMAZ (AP'de slug ile join; ADR-014 §4 gövde dağıtmama).
  `dia_chunks.json` değiştirilmez.
- **Doğrulama = token coverage ≥ 0.95** (`chunk.t` ⊆ scraped `.m-content`) +
  `h1==chunk.n` + `arabic==chunk.a`. Simetrik edit-ratio değil, çünkü scraped
  sayfa chunk anlatısını kapsar ama daha uzundur (dipnot/bibliyografya).
  Sapma → `review` flag, sessiz yazım yok.
- **Yazar = liste** (`[{section, author_raw}]`); modelleme (person vs
  contributor namespace) AP/H10+'ya ertelenir (proposal açık soru 3+4).

### Gerekçe

ADR-006 lokalitesi (bir klasör = bir kaynak) korunur; `extract`/canonical
sözleşmeleri ihlal edilmez. Yalın sidecar hem küçük hem de "structured-from-
source" vs "scraped" provenance ayrımını korur. Coverage metriği, 2a'da ampirik
olarak (cov(chunk→web)=1.000 iken simetrik Levenshtein 0.15–0.85) doğrulandı.

### Sonuç

- Adapter iskeleti + 8 offline parser testi + registry + gitignore hazır.
- `pytest tests/integration/` 85→**93 passed** (additive), `run_schema_tests`
  15/15 değişmedi. Smoke (2 slug) fetch/resume/assemble'ı doğruladı.
- Canonical/şema/`dia_chunks.json` dokunulmadı. Sıradaki: 2c pilot.

<!-- Sonraki H9 kararları burada eklenecek -->
