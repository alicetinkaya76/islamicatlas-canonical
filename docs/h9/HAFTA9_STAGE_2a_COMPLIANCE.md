# Hafta 9 — Stage 2a: AO compliance gate + Phase-0 doğrulama

**Date:** 2026-07-06
**Branch:** hafta5-work-namespace
**Repo:** ~/Desktop/islamicatlas_canonical (belgelerdeki /Volumes/LaCie/… yolu
eski; bu kopya günceldir — HEAD 89cfd79 girişte doğrulandı)
**Entry HEAD:** 89cfd79 ("Hafta 9 Stage 1: PE-2 remediation …")
**Trigger:** AO (TDV scraping pipeline), H9 ana gövde adayı; AP'nin önkoşulu.
`docs/h8/H8_SCRAPING_PROPOSAL.md` §Phase 1 (compliance) + Phase-0 (slug
stabilite) doğrulaması.

---

## Bu stage ne yapar

AO'nun **compliance hard gate**'ini geçer ve scraper'ı yazmadan önce
feasibility'i canlı siteyle doğrular:

1. **robots.txt** çekilip incelendi → `User-agent: * / Allow: /` (YEŞİL).
2. **Kullanım Şartları** (`/kullanim_sartlari.php`, İSAM) incelendi →
   açık yazılı izin olmaksızın çoğaltma/işleme/derleme yasak, kaynak
   göstermek yetmez (KIRMIZI). Maintainer izin teyidiyle **koşullu GO**.
3. Bulgular kanıtlarıyla `docs/decisions/ADR-014-tdv-scraping-compliance.md`
   olarak yazıldı.
4. **Phase-0 canlı örneklem** (9 distinct slug) ile URL deseni, slug
   stabilitesi ve alan-selector'ları doğrulandı.

## Kanıt zinciri (çekim zaman damgaları, UTC)

| Kaynak | Zaman | Sonuç |
|---|---|---|
| `robots.txt` | 2026-07-05T20:47Z | `Allow: /`, Disallow/Crawl-delay yok |
| `/` (homepage) | 2026-07-05T20:48Z | footer'da `/kullanim_sartlari.php` linki |
| `/kullanim_sartlari.php` | 2026-07-05T20:48Z | FİKRİ MÜLKİYET: yazılı izin şart |
| `/madde/hassaf` (desen testi) | 2026-07-06T02:35Z | **404** → `/madde/<slug>` yanlış |
| `/hassaf`, `/abaka` (desen testi) | 2026-07-06T02:44Z | **200** → kök-slug deseni doğru |
| 9-slug örneklem | 2026-07-06T02:49Z | aşağıdaki tablo |

Tüm istekler tanımlayıcı UA + ≥2 sn aralıkla yapıldı.

## Phase-0 örneklem tablosu (9 distinct slug)

Seçim: sabit çapa (hassaf, abaka, abbad-b-bisr, ahidname) + en büyük
maddeler + tek-chunk+Arapça + `sec`'li maddeler.

```
slug                st  h1=n  ar_ok  cilt/sayfa  #mü  prt/chk  body~
hassaf             200     Y      Y      16/395    1      1/1   0.81
abaka              200     Y   none         1/8    1      1/1   0.84
abbad-b-bisr       200     Y      Y        1/12    1      1/1   0.81
ahidname           200     Y      Y       1/535    2      2/9   0.97
muhammed           200     Y      Y      30/406   19   19/131   0.94
gazzali            200     Y      Y      13/489    6     6/88   0.96
abbad-b-suleyman…  200     Y      Y        1/12    1      1/1   0.81
ahmed-b-hanbel     200     Y      Y        2/75    3     3/23   0.97
ali-mustafa-efendi 200     Y   none       2/414    2     2/14   0.93
```

- **h1=n**: scraped `<h1>` == `chunk.n` | **ar_ok**: `div.arabic_title` vs
  `chunk.a` (none = ikisi de boş) | **#mü**: Müellif blok sayısı (>1 =
  çok-yazar) | **prt/chk**: `.article-part` sayısı vs chunk sayısı |
  **body~**: normalize edilmiş `#m-body` benzerliği vs aggregated `chunk.t`.

## Bulgular

1. **Slug stabilitesi (proposal açık soru 2 → KAPANDI):** 9/9 slug
   `https://islamansiklopedisi.org.tr/<slug>` altında 200 ve `dia_chunks.s`
   ile birebir. Web sürümü ayrı bir slug şeması KULLANMIYOR. `/madde/<slug>`
   (proposal tahmini) 404 verir; doğru desen **kök-seviye `/<slug>`**.
2. **Alan selector'ları stabil:** `h1` (TR başlık), `div.arabic_title`
   (Arapça başlık — `chunk.a` ile eşleşir), `.ak-muellif span.val`
   (müellif), künye cümlesi `(\d+)\. cildinde, (\d+) … numaralı sayfa`
   (cilt/sayfa). hassaf → 16/395, ADR-009'un locator'ıyla birebir.
3. **Çok-parça = çok-yazar (proposal açık soru 3+4 → doğrulandı):**
   Uzun maddeler (`muhammed` 19 parça, `gazzali` 6) her `.article-part`
   için ayrı müellif **ve** ayrı cilt/sayfa taşır. → rich şemada yazar,
   article-part granülaritesinde **liste** olarak toplanır (`chunk.a`
   Arapça başlıktır, yazar DEĞİL — ADR-011 v1.1'i canlı site doğruluyor:
   yazar chunk'larda yok, yalnız scraping'le gelir).
4. **Gövde-hash — henüz ham:** `#m-body` benzerliği 0.81–0.97. Küçük
   maddelerde düşük çünkü ham konteyner bibliyografya/künye/ilişkili-madde
   "chrome"unu da içerir (küçük maddede oransal olarak büyük). Bu bir slug
   veya selector hatası DEĞİL; gövde bölgesinin daraltılması gerektiğini
   gösterir. **≥%95 eşiği 2c pilot kapısıdır; bu aşamada iddia edilmez.**
5. **article-part << chunk:** Chunk'lar `.article-part`'lardan daha ince
   granüler (`muhammed` 19 parça / 131 chunk). Scraper granülaritesi =
   article-part; part↔chunk join'i 2b/2e işidir.

## Bu stage ne YAPMAZ

- Canonical store'a hiçbir kayıt yazmaz/mutasyona uğratmaz.
- `dia_chunks.json`'a dokunmaz. Şema dosyalarına dokunmaz.
- Scraper kodu yazmaz (2b). Toplu/pilot koşu yapmaz (2c/2d).
- İzin belgesini fabrike etmez — ADR-014 §Koşul `needs_human_review`.
- git invoke etmez; önerilen commit sekansı aşağıda (Stage 1 konvansiyonu).
- Tag atmaz (hafta kapanışı değil). `docs/h8/*` düzenlemez.

## Kabul kriterleri

- [x] ADR-014 mevcut; robots.txt kanıtı + ToS duruşu + izin dayanağı içerir.
- [x] 10-slug (fiilen 9 distinct) örneklem sonucu journal'da; slug
      stabilite kararı dâhil.
- [x] Örneklem HTML'leri yalnız scratchpad'de (git'e/canonical'a girmez).
- [x] Kod değişikliği yok → `pytest tests/integration/` 85/3/3 değişmez;
      `run_schema_tests` 15/15 değişmez.
- [ ] İzin belge referansı ADR-014'e eklenecek (kullanıcı; yayından önce).

## Önerilen commit sekansı (git'i orchestrator invoke etmez)

```
git add docs/decisions/ADR-014-tdv-scraping-compliance.md \
        docs/h9/HAFTA9_STAGE_2a_COMPLIANCE.md \
        docs/h9/H9_DECISION_LOG.md
git commit   # mesaj: aşağıdaki "Expected commit message"
```

### Expected commit message

```
Hafta 9 Stage 2a: AO compliance gate + Phase-0 doğrulama — ADR-014

- docs/decisions/ADR-014: robots.txt (Allow: /) YEŞİL; Kullanım Şartları
  açık yazılı izin şartı (kaynak göstermek yetmez) — maintainer izin
  teyidiyle koşullu GO; izin belge referansı needs_human_review
- Phase-0 canlı örneklem (9 distinct slug): URL deseni /<slug> (proposal'ın
  /madde/<slug> tahmini 404); slug==dia_chunks.s stabil 9/9; selector'lar
  doğrulandı (h1, div.arabic_title, .ak-muellif span.val, "N. cildinde M
  numaralı sayfa"); hassaf=16/395 = ADR-009; çok-parçalı maddeler
  article-part başına müellif+cilt/sayfa taşır → yazar liste kararı
- docs/h9/HAFTA9_STAGE_2a_COMPLIANCE.md + H9_DECISION_LOG Karar 2
- Gövde-hash ≥%95: 2b parser gövde-daraltma + 2c pilot kapısına ertelendi

Gate:  GREEN (robots ok; ToS ok — yazılı izin altında)
Test:  kod yok; tests/integration 85/3/3, run_schema_tests 15/15 değişmedi
Refs:  AO / H8_SCRAPING_PROPOSAL Phase 1+0; ADR-009
```

## Rollback

Docs-only. Tek `git revert <commit>` ADR-014 + journal + Karar 2'yi birlikte
geri alır; kod/veri dokunulmadığı için yan etkisiz. Revert, compliance
gate'ini yeniden açar (AO tekrar 2a'dan başlamalı).
