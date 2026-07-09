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

## Karar 4 — Pilot: coverage metriği doğrulandı, ≥%95 gate %100 geçildi

**Tarih:** 2026-07-06
**Stage:** 2c
**İlgili ADR:** ADR-014

### Bağlam

2b scaffold'u 100 slug'lık canlı pilotla ölçekte doğrulanmalı: hash-match
≥%95, cilt/sayfa parse başarımı, resume. 2a, ham simetrik Levenshtein'ın
büyük çok-parçalı maddelerde yanıltıcı düştüğünü (web ⊇ chunk) bulmuş ve
metriği token-coverage'a rafine etmişti.

### Karar

Coverage metriği (chunk.t token'ları ⊆ scraped `.m-content`) ≥0.95 gate'i
kabul edildi ve pilotta doğrulandı. `scrape.py` iki saf fonksiyona ayrıldı
(`plan_fetch`, `project_rich`) → resume ve lean-projeksiyon network'süz test
edilebilir. Pilot'un run-artifact'ları (gitignore'lu) korunur; 2d bunları
atlar.

### Gerekçe

Coverage, "doğru madde mi çekildi" sorusunu simetrik edit-ratio'dan çok daha
sağlam yanıtlar (dipnot/bibliyografya web'i uzatır ama chunk anlatısını içerir).
Pilot ampirik olarak doğruladı: 100/100 madde coverage medyan 1.000 (min 0.998),
%100'ü ≥0.95; cilt/sayfa ve müellif parça-başına %100; 0 review-flag.

### Sonuç

- Pilot 100/100 ok; coverage %100 ≥0.95; cilt/sayfa %100; title_ar %67
  (chunk oranıyla tutarlı); 0 flag.
- Resume canlı re-run'da 0.55 sn'de sıfır-istekle doğrulandı + 3 saf test.
- `pytest tests/integration/` 93→**98 passed** (additive); schema 15/15.
- Sıradaki: 2d — tam koşu CLI'ı + gece başlatma komutu (koşu kullanıcıda).

## Karar 5 — Bulk teslim edildi; koşu kullanıcıda; kapsam 8.093 (≈4,5 saat)

**Tarih:** 2026-07-06
**Stage:** 2d
**İlgili ADR:** ADR-014

### Bağlam

Tam koşu ~11 saatlik, kesintiye dayanıklı bir gece işidir; handoff §4 bunu
kullanıcının başlatmasını, oturumun yalnız kendi kendine devam eden aracı +
komutu teslim etmesini şart koşar.

### Karar

`scrape.py --all` (resumable, 2c'de doğrulandı) + yeni `--status` izleme
subcommand'i + `run_bulk.sh` gece başlatıcısı (caffeinate+nohup+log) teslim
edildi. **Bulk oturum içinde BAŞLATILMADI.** Kapsam **8.093 distinct slug ≈
4,5 saat** olarak düzeltildi (handoff'un "19.742 madde / 11 saat"i chunk
sayısıdır; fetch birimi maddedir). Pilotun 100 slug'ı sidecar'da → `--all`
kalan 7.993'ü çeker.

### Gerekçe

Kesintiye dayanıklılık (checkpoint/atomik yazım + resume) 2c'de kanıtlı;
`--status` 4,5 saatlik koşuyu network'süz izlemeyi sağlar. Süre düzeltmesi
North Star'ın "sayımı koddan üret, tahmin etme" ilkesinin gereği.

### Sonuç

- `run_bulk.sh` (`bash -n` temiz) + `--status` + izleme/durdurma/assemble
  talimatları teslim.
- Kod additive → `pytest tests/integration/` 98 passed; schema 15/15.
- Bulk kullanıcıda; bitince 2e (assemble + kapsam istatistikleri + journal).

## Karar 6 — Arapça başlık doğrulaması advisory (rasm); review = title+coverage

**Tarih:** 2026-07-06
**Stage:** 2d.1 (bulk koşarken keşfedildi)
**İlgili ADR:** ADR-014

### Bağlam

Bulk'ın ilk ~625 maddesindeki 6 review-flag'in hepsi `arabic_mismatch`'ti ve
hepsinde `h1_match=True` + `coverage=1.0` idi. Neden: `dia_chunks.a` DiA'nın
tam harekeli başlığının indirgenmiş bir normalizasyonu (`ال`'siz, hamza'sız),
dolayısıyla ham string eşitliği doğru sayfalarda bile başarısız.

### Karar

Arapça başlık **advisory**: review-blocking flag'ler yalnız `title_mismatch`,
`low_coverage`, `no_cilt_sayfa` (kimliği bunlar kesinleştirir). `ar_match`
**rasm** normalizasyonuyla (harakat/tatweel at, hamza/alif/ya/ta-marbuta katla,
`ال` sıyır) hesaplanıp kaydedilir ama review'a sokmaz.

### Gerekçe

Yanlış sayfa zaten h1 (birebir Türkçe başlık) + coverage ile yakalanır; Arapça
ortografi farkı kimliği değiştirmez. Scraped tam-harekeli başlık zaten
istediğimiz (rich-mint için chunk.a'dan iyi) veridir. North Star: flag = gerçek
şüphe, gürültü değil.

### Sonuç

- 6 flagged kayıt yeni mantıkla `flags=[]`, `ar_match=True`.
- Parser test 8→10; `pytest tests/integration/` 98→**100 passed**; schema 15/15.
- Koşan bulk eski mantıkta; 2e verdict'leri offline yeniden hesaplar (re-scrape
  yok).

## Karar 7 — AO tamamlandı: rich dosya üretildi, AP bloğu kalktı

**Tarih:** 2026-07-06
**Stage:** 2e
**İlgili ADR:** ADR-009, ADR-014

### Bağlam

Kullanıcı bulk koşusunu ve 2e'yi bana devretti ("izin konusuna takılma, tüm
işleri bitir"). Tam koşu (8.093/8.093, 0 error, ~4,5 saat) tamamlandıktan sonra
verdict'ler 2d.1 mantığıyla düzeltilip rich dosya üretilecek.

### Karar

`--reverify` (gzip arşivden offline yeniden hesap, re-scrape yok) ile 8.093
verdict düzeltildi; `--assemble` ile `dia_chunks_rich.json` (Path 3a, lean,
gövdesiz) üretildi. 10 review vakası insan denetimine bırakıldı; AO
H9_KNOWN_ISSUES'ta kapatıldı.

### Gerekçe

Bulk eski verify mantığında koştuğu için (arapça strict) 16 review vardı;
extracted VERİ zaten doğruydu, yalnız verdict bayattı. Offline reverify
re-scrape'i gereksiz kıldı. ar_match True=5412/False=0 → 2d.1'in "arapça
advisory" kararı ampirik olarak doğru.

### Sonuç

- `dia_chunks_rich.json`: 8.093 kayıt; cilt+sayfa %99.94, title_ar %66.9,
  müellif %99.9 (1.423 distinct yazar — chunk'larda yoktu), 44 cilt, coverage
  ≥0.95 %99.96.
- Review 10: 5 online-only (web-locator → AP), 3 low-coverage, 3 title-varyant.
- `pytest tests/integration/` 100→**101 passed**; schema 15/15.
- **AP (dia_works rich-mint) bloğu kalktı** — ADR-009 (a)+(c) eşikleri artık
  besleniyor. Yazar namespace modellemesi (açık soru 3/4) AP'de karara bağlanır.

## Karar 8 — Tüm-repo incelemesi: 56-ajanlık tarama + adversarial doğrulama; kod remediation'ı Stage 3

**Tarih:** 2026-07-07
**Stage:** 3
**İlgili ADR:** ADR-009 (gate implementasyonu), ADR-014 (scraper düzeltmeleri)

### Bağlam

Kullanıcı "tüm projeyi incele ve iyileştir; daha smart ve hızlı bitirmemi
sağla" dedi. 6 paralel derin okuyucu (lib, adapters, tests, schema+search,
docs+roadmap, hijyen+CI) 81 ham bulgu üretti; her bug/perf bulgusu 2 bağımsız
çürütücüye verildi → **16 doğrulanmış, 9 çürütülüp elendi**, 56'sı
test/hijyen/docs/roadmap kategorisinde.

### Karar

Doğrulanmış bulgular üç stage'e bölünerek kapatılır: Stage 3 = kod (veri
güvenliği + AP-hazırlık + arama katmanı), Stage 4 = test/CI altyapısı,
Stage 5 = hijyen/docs/roadmap. Canonical KAYITLARA dokunulmaz; tek istisna
data/_state PID onarımıdır (h9_001 migration'ı — H6 Hassâf elle mint'inin
counter/index dışında kalması AP'nin ilk mint'inde `iac:work-00009331`
çakışması üretecekti). Davranış düzeltmelerinin mevcut kayıtlara yansıtılması
(el-alam re-run, phantom audit) ayrı, journal'lı koşulara devredilir
(PHASE0_CLOSEOUT §2).

### Gerekçe

Çürütücü katmanı 9 yanlış-pozitifi (ör. "pipeline_version hardcode",
"Tier-1 alan adı bug'ı") uygulamaya girmeden eledi. Kod-önce sıralaması:
AP H10'da bu kütüphanelerin üstüne biniyor; state onarımı geciktirilirse
her gün riskli.

### Sonuç

- 16/16 bulgunun kod ayağı kapalı; `full_reindex --dry-run` 46.702/46.702
  (768 fail'den); fingerprint 4 çeviri-yazı çifti kilitli; `adr009_rich_gate`
  + PidMinter `session()` (31 ms → 0.001 ms/mint) AP'ye hazır.
- test_b2 bekçisi xfail'den çıkarıldı; drift sınıfı kalıcı kırmızı.

## Karar 9 — Suite hızlandırma: paylaşılan cache EVET, multiprocessing HAYIR; slow_fullstore marker'ı

**Tarih:** 2026-07-07
**Stage:** 4

### Bağlam

Ölçüm: person store 3×, place ~9× diskten yükleniyor; 3 tüm-store validasyon
testi 16 sn; suite 31 sn; iç-döngü modu yok. CI ise çifte bozuk (var olmayan
script'e kırmızı + boş glob'la sahte-yeşil şema adımı) ve `main`-only.

### Karar

(1) `conftest.py` lru_cache yükleyicileri + modül fixture delegasyonu.
(2) Multiprocessing fan-out DENENDİ, benchmark REDDETTİ (macOS spawn'da
jsonschema import maliyeti person geçişini 5.5→7.3 sn'ye yavaşlattı) —
sıralı `validate_all` kaldı; karar conftest docstring'inde kalıcı.
(3) Tüm-store testleri `slow_fullstore` marker'ı → `make test-fast` (~9 sn);
tam kapı `make test` (CI aynısını koşar — tek doğruluk kaynağı).
(4) Sessiz kapsam açıldı: 15 şema fixture'ı pytest'e; truncate fuzz (H8
TODO); rich-dosya invariant'ları; g3 skip→xfail; bosworth rmtree guard'ı;
yaqut bootstrap'ı opt-in. Hiçbir eşik esnetilmedi.

### Sonuç

`pytest` 101→**147 passed** / 21 sn; iç döngü ~9 sn; CI gerçek suite'i
`hafta*` dahil koşuyor; requirements.txt/Makefile/pytest.ini kökte.

## Karar 10 — Dış yüz gerçeğe eşitlendi + PHASE0_CLOSEOUT tek yol haritası

**Tarih:** 2026-07-07
**Stage:** 5
**İlgili ADR:** ADR-013 (xref düzeltmesi + numara notu)

### Bağlam

README/CHANGELOG/CONTRIBUTING H4/v0.1.0'da donmuştu (7 ADR / 18 test / ~59K
iddiası vs gerçek: 14 ADR / 145 test / 46.702 koddan-sayılı kayıt); kökte 10
bayat dosya; 13,3 MB bayt-özdeş kopya; ADR-013'te yanlış ADR-002 atfı; ve
ADR-013'ün referans verdiği "Faz 0.5 roadmap" hiç yazılmamıştı.

### Karar

Kök arşivi `git mv` ile `docs/h2..h4/` + `_archive/root/`e; kopyalar `git rm`;
README/CHANGELOG/CONTRIBUTING koddan-üretilen sayılarla güncellendi (North
Star: sayı fabrikasyonu yok); ADR-013 düzeltmeleri revision-history'li;
`docs/PHASE0_CLOSEOUT.md` kalan işlerin tek sahipli/sıralı listesi olarak
yazıldı (H9 close → AP → onarım koşuları → AN → Faz 0.5 → v1.0.0/Zenodo;
tek sert dış blokör: İSAM izin belge referansı, ADR-014 §Koşul).

### Sonuç

- Kök temiz; dış yüz H9 gerçeğinde; sonraki oturumların giriş noktası
  PHASE0_CLOSEOUT.
- dynasty.schema.json newline'ı + PE2.5 bekçisi; şema seti v0.3.0 değişmedi.

## Karar 11 — H9 close: close-state + tag + main merge; AP sınırı netleştirildi

**Tarih:** 2026-07-09
**Stage:** 6 (close)

### Bağlam

H9 (schema v0.3.0 + AO scraper + 56-ajanlık review remediation) bitti; kapanış
töreni gerekiyor. Kapatmadan önce AP'nin gerçek veri modeli incelendi.

### Karar

`HAFTA9_CLOSE_STATE.md` yazıldı; `hafta9-close` tag'i; `hafta5-work-namespace`
→ `main` merge (no-ff; PHASE0_CLOSEOUT §0). **AP kapsamı düzeltildi:** AO (c)
locator'ını verdi ama per-work (a)/(b) 42K DiA-only başlık için mevcut değil →
AP **sınırlı zengin-mint** (dış-eşleşmeli alt küme ~1.519), toplu değil. Ali'nin
2 kararı (ADR-009 (a) eşiği + katkıcı namespace'i) `docs/h10/HAFTA10_AP_KICKOFF.md`'de
sayılarla çerçevelendi; öneri A1+B1.

### Gerekçe

North Star "explicit boundaries": AP'yi "8-25K work toplu mint" diye bırakmak,
projenin reddedilme sebebi olan doğrulanmamış-atıf hatasını davet ederdi.
Bantların (42.449 dia_only) koddan okunması bu sınırı kanıtladı.

### Sonuç

- H9 kapandı: 11 stage commit + close-state + tag; main'e merge.
- AP teçhiz edildi (kickoff + gate + session + state onarımı); Ali kararı +
  onarım koşuları sonrası çalıştırılabilir. Suite 147; canonical 46.702 (mint yok).

<!-- Sonraki H9 kararları burada eklenecek -->
