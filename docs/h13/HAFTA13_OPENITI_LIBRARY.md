# Hafta 13 · S-A/S-B — OpenITI Kütüphanesi: gerçek başlıklar + 73 yeni kitap

**Tarih:** 2026-07-15 · **Kullanıcı kararları:** kaynak = LaCie tam-klon
pipeline'ı; tam metin = ŞİMDİLİK metadata + link.

## Keşifler (ölçülmüş)

- data/sources/openiti/* sembolik linkleri LaCie'ye işaret ediyordu ve disk
  takılı değilken KOPUKTU (replay kırık) → gerçek dosyalar repoya sabitlendi
  (corpus_works 7.7MB + authors 2.3MB + genres 5.9MB) + iki yeni katalog:
  LaCie openiti_all_books_fixed.csv (2026-07-07) ve resmî GitHub klon
  metadata'sı (2025-11-24, 13,364 sürüm).
- LaCie kataloğu 9,177 kitap (8,822 AR + 355 PER); mağaza 9,104'ünü
  kapsıyordu → +73 yeni. LaCie CSV'nin isim/başlık kolonlarının ~8,000'i
  OpenITI YML şablon placeholder'ı ("Ibn Fulān"/"Kitāb al-Muʾallif") —
  başlık otoritesi GitHub metadata'sı seçildi.
- Eserlerde authors (9,104/9,104) ve subjects ZATEN doluydu; gerçek boşluk
  BAŞLIKLARDI: Arapça başlık 0, prefLabel.tr = URI kelimesi ("BiharAnwar").

## Yapılan

- **S-B openiti_titles_augment.py:** 8,757 eser zenginleşti — 8,354 gerçek
  Arapça başlık (gap-fill), 6,987 görüntü başlığı düzeltmesi (URI kelimesi
  altLabel'a İNDİ, Latin bilimsel başlık prefLabel oldu — ezme yok),
  " :: " bileşik başlıklar bölündü (1,828), 60 tefsir etiketi, GitHub
  okuma linki note'a, 9,104 yerel tam-metin yolu
  data/_state/openiti_local_paths.json'a (site-içi okuma FAZI girdisi).
- **S-A openiti-delta adapter'ı:** 73 yeni kitap mint. Ana openiti-works
  YENİDEN KOŞULMADI — koşulsaydı S-B zenginleştirmelerini ezerdi
  (run_adapter preserve listesi label kapsamaz); delta ayrı girdi dosyası
  + aynı canonicalize (import).

## Kapı ve kanıt

Mağaza **57,250** · projeksiyon 57,250/57,250 · make test 160 · Typesense
57,250 fail=0. Kanıt sorguları: "بحار الأنوار" → Biḥār al-anwār;
"İhya" → İhyâu Ulûmi'd-Dîn (AR başlıklı). Kütüphane artık iki yazıyla
aranabilir.

## Sonraki (Kütüphane hattı)

UI "Kütüphane" görünümü (H12 S2 birleşik arama + eser sayfaları üstüne);
GitHub-klon 38 fark kitabı (LaCie'de olmayan) ileriki sürüm-tazelemesine;
site-içi okuma fazı openiti_local_paths.json'dan başlar.
