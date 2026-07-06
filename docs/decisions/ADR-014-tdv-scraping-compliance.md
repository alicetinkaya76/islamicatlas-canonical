# ADR-014: TDV İslâm Ansiklopedisi web sürümü — scraping uyum (compliance) duruşu

**Status:** Accepted (koşullu — İSAM yazılı izin *belge referansı* eklenmek üzere;
bkz. Karar §Koşul)
**Date:** 2026-07-06
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (ORCID 0000-0002-7747-6854)
**Related:** ADR-006 (adapter pattern), ADR-009 (DiA rich-mint doktrini),
ADR-011 (dia_chunks scope), `docs/h8/H8_SCRAPING_PROPOSAL.md` (AO spec),
`docs/h9/HAFTA9_STAGE_2a_COMPLIANCE.md` (bu ADR'nin kanıt journal'ı)

> **Numara notu:** H8 proposal'ı uyum ADR'sini "ADR-012" diye anar; o numara
> sonradan `description` maxLength bump'ına (ADR-012) harcandı, ADR-013 de
> schema-set versiyonlamaya. Uyum ADR'sinin doğru numarası **ADR-014**'tür.

---

## Bağlam

AO (H9) pipeline'ı, ADR-009'un rich-mint eşiklerini — (a) çok dilli
prefLabel'ın Arapça ayağı, (c) cilt+sayfa locator'ı — doldurabilmek için
`https://islamansiklopedisi.org.tr` üzerinden madde-başı metadata toplar.
Bu akademik bir projedir; TDV verisi ancak atıf **ve meşruiyetle**
kullanılabilir. Bu yüzden compliance-first **hard gate**: robots.txt + ToS
doğrulaması yapılmadan ve bu ADR yazılmadan tek bir scrape isteği atılmaz.

## Kanıt 1 — robots.txt (çekim: 2026-07-05T20:47Z)

Tanımlayıcı User-Agent ile çekildi (`islamicatlas-canonical/0.3
(+https://islamicatlas.org; ORCID 0000-0002-7747-6854;
mailto:ali.cetinkaya@selcuk.edu.tr)`). HTTP 200, 22 bayt, `last-modified:
Wed, 29 Apr 2026 22:31:26 GMT`. Tam içerik:

```
User-agent: *
Allow: /
```

→ Disallow yok, Crawl-delay yok. Otomatik erişim tüm yollar için (madde
sayfaları dâhil) **serbest**.

## Kanıt 2 — Kullanım Şartları (çekim: 2026-07-05T20:48Z)

Kaynak: `https://islamansiklopedisi.org.tr/kullanim_sartlari.php`
("İnternet Kullanıcı Sözleşmesi"; sahibi Türkiye Diyanet Vakfı İslâm
Araştırmaları Merkezi — İSAM). **FİKRİ MÜLKİYET HAKLARI** maddesi, iki
belirleyici cümle (birebir alıntı):

> "İşbu akitte açık bir şekilde beyan edilmeyen ve **İSAM tarafından açık ve
> yazılı bir izin olmaksızın** işbu web sitesinden yapılan herhangi bir
> kullanım; **çoğaltma**, yayma, umuma iletim, temsil, **işleme**, değiştirme,
> çevirme, tahrifat, kamuya gösterim, sergileme, web sitesine yükleme,
> internette yayınlama, iletim, yeniden iletim ve dağıtım veya diğer
> şekillerde web sitesini veya onun herhangi bir içeriğini bir bütün olarak
> veya **kısmî bir şekilde kullanmak ve ondan yararlanmak yasaklanmıştır**."

> "İSAM … **FSEK m. 36** kapsamındaki telif haklarını saklı tutmuştur.
> Belirtilen unsurlar, **kaynak gösterilse dahi izin alınmadan
> kullanılamaz**."

Metnin tamamı tarandı: **araştırma/akademik/eğitim istisnası yoktur**;
kişisel-kullanım ruhsatı yalnızca *yazılım programları* için ve
ağ-bağlantısız + ticari-olmayan koşuluyla tanımlıdır (içeriği kapsamaz).
"İşleme ve derleme eserler" açıkça anılır → türetilmiş
`dia_chunks_rich.json` bir derlemedir; "kısmî kullanım" cilt+sayfa gibi
*olgusal* alanların çıkarımını bile sözleşme düzeyinde yasaklar; ham HTML
arşivi ise düpedüz "çoğaltma"dır.

## Değerlendirme

İki katman ayrıdır: **robots.txt erişimi**, **ToS kullanımı/telifi**
düzenler. robots.txt YEŞİL; ToS ise **açık yazılı izin olmaksızın KIRMIZI**.
robots.txt'nin izin vermesi, ToS'un telif kısıtını **kaldırmaz**. Atıf
(kaynak gösterme) tek başına yetersizdir — ToS bunu açıkça reddeder.

## Karar

1. **AO ancak İSAM'ın açık yazılı izniyle koşar.** Maintainer (ORCID
   0000-0002-7747-6854), 2026-07-06 tarihinde İSAM yazılı izninin mevcut
   olduğunu teyit etmiştir → **GO**.
2. **§Koşul (needs_human_review: pending).** İznin **resmî belge referansı**
   — izni veren merci, tarih, kapsam (hangi maddeler / hangi kullanım /
   yeniden dağıtım hakkı), belge veya e-posta kimliği — bu ADR'ye
   eklenecektir. Referans eklenene dek bu ADR "koşullu accepted"tır ve
   türetilmiş veri setinin **yayımı** bu referans olmadan yapılamaz. (North
   Star: kanıtsız iddia edilmez; belge fabrikasyonu yasak — bu yüzden
   referans burada boş bırakılıp `needs_human_review` işaretlenmiştir.)
3. **Nezaket sınırı (değişmez):** ≤ 1 istek / 2 sn, paralel istek yok;
   tanımlayıcı UA (proje + ORCID + iletişim e-postası); `If-Modified-Since`;
   `Retry-After`'a saygı; cease-on-request.
4. **Veri asgariliği:** Ham HTML `data/sources/dia_html/<slug>.html.gz`
   olarak yalnız yerelde arşivlenir (git'e ve canonical'a **girmez**);
   canonical'a scraped gövde metni yazılmaz — yalnız olgusal normalize
   alanlar (cilt, sayfa, `title_ar`, müellif). Gövde metni zaten elde
   bulunan `dia_chunks.json`'un `t` alanından gelir.
5. **İzin geri çekilir/reddedilirse:** scraper durur; pivot (İSAM'a resmî
   veri talebi / basılı nüsha re-extraction) bu ADR'ye işlenir ve AO
   askıya alınır. H8 dia_person_enrichment işi bundan bağımsızdır,
   geçerliliğini korur.

## Phase-0 canlı doğrulama (özet; tam kanıt journal'da)

10-slug örneklem (fiilen 9 distinct slug), 2026-07-06T02:49Z, ≥2 sn aralık:

- **URL deseni:** `https://islamansiklopedisi.org.tr/<slug>` (proposal'ın
  `/madde/<slug>` tahmini **yanlış** — 404 döner).
- **Slug stabilitesi:** 9/9 örnek slug `dia_chunks.s` ile birebir, hepsi 200.
- **Alan çıkarımı:** `h1` = `chunk.n` (9/9); `div.arabic_title` = `chunk.a`
  (dolu olan 7/7, 2'si doğru-boş); cilt/sayfa "N. cildinde, M numaralı
  sayfa" deseniyle 9/9 (hassaf 16/395 = ADR-009 doğrulaması);
  `.ak-muellif span.val` = müellif. **Çok-parçalı maddeler birden çok müellif
  + birden çok cilt/sayfa gösterir** (muhammed 19, gazzali 6) → yazar
  **article-part granülaritesinde liste** olarak toplanır.
- **Gövde-hash:** ham `#m-body` benzerliği 0.81–0.97; küçük maddelerde
  <%95, çünkü konteyner bibliyografya/künye/ilişkili-madde "chrome"'u içerir.
  Gövde bölgesi 2b parser'ında daraltılacak; **≥%95 eşiği 2c pilot
  kapısıdır**, bu aşamada iddia edilmez.

## Sonuçlar

**Olumlu:** Hedef alanların (cilt, sayfa, `title_ar`, müellif) tümü
çıkarılabilir; slug'lar stabil; feasibility doğrulandı; gate GEÇTİ.
**Koşul:** İzin belge referansı bekliyor (§Koşul) — yayından önce zorunlu.
**Risk/İzlenecek:** gövde-hash ≥%95 eşiği parser daraltmasına bağlı (2b→2c).

## References

- `https://islamansiklopedisi.org.tr/robots.txt` (2026-07-05T20:47Z)
- `https://islamansiklopedisi.org.tr/kullanim_sartlari.php` (2026-07-05T20:48Z)
- `docs/h8/H8_SCRAPING_PROPOSAL.md` (AO spec)
- `docs/decisions/ADR-009-dia-works-rich-vs-shallow-mint.md`
- `docs/h9/HAFTA9_STAGE_2a_COMPLIANCE.md` (kanıt journal + örneklem tablosu)

---

**Revision history:**

- 2026-07-06: İlk sürüm — H9 Stage 2a; robots.txt YEŞİL + ToS yazılı-izin
  kısıtı + maintainer izin teyidiyle koşullu GO. İzin belge referansı
  `needs_human_review`.
