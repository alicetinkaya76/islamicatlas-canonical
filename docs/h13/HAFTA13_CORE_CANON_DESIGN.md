# Çekirdek Külliyat — Parti 1 tasarımı: canonicalization + arayüz

**Tarih:** 2026-07-15 · **Girdi:** 6 katman-denetimi (yaqut/rihla/evliya/
khitat/muqaddasi+lestrange/salibiyyat, paralel ajan taraması) + 10 kitabın
metin-yapı probu + canonical kayıt durumu.

## 1. Derinlik çıtası — v1'de "çok detaylı"nın anatomisi (ölçüldü)

Altı öğe her zengin katmanda tekrarlıyor; kitap sayfası bu çıtayı tutturmalı:

1. **Birebir kaynak pasajı** kayıt başına: Arapça RTL (Amiri font) + çeviri,
   SAYFA/SATIR atfıyla (Rihla "V01P163", Hıtat satır no) — birincil metin
   birinci sınıf vatandaş.
2. **Üç dilli adlandırma** (tr/en/ar) + RTL tipografi.
3. **Çift takvim (H/M) + güven rozetleri** — belirsizlik görsel boyut
   (Le Strange 9 kesinlik seviyesi → 4 rozet → harita opaklığı).
4. **3 sütun düzen:** sanal-kaydırmalı sidebar listesi (diakritik-normalize
   arama, filtreler) + koyu harita/içerik + uzun kimlik kartı (rozet +
   etiket-değer satırları + sayılı katlanır bölümler).
5. **lite/detail JSON ayrımı** (kısa anahtarlar; ilk seçimde detay fetch) —
   Yâkût 12,954 kaydı böyle taşıyor.
6. **Katman-ötesi xref blokları** + tur/anlatı modları (voyage renkleri).

## 2. Parti-1 kitapları nasıl canonize edilecek

Mevcut durum (ölçüldü): 10/10 kitabın canonical kaydı VAR (S-B gerçek
başlıkları verdi), yazar bağlı; eksik = tanıtım + okuma verisi.

**Canonical'a giren (append-only augment, kitap başına):**
- labels.description.tr/en — EDİTORYAL 2-4 cümle tanıtım (DİA metni
  KULLANILMAZ: İSAM izni yayın şartı; kendi metnimiz).
- note += yapı istatistiği (bölüm/sayfa/kelime) + baskı-sürüm özeti.
- subjects normalize (conquest/geography/travel/city-history).
- mentions_places/cites_works → İLERİDE, kitap→katman dönüşümünde
  (Fütûh→fetih olayları vb.); şimdilik pending.

**Canonical'a GİRMEYEN (statik okuma verisi; gitignored, script'le üretilir):**
- web/public/reading/<pid>/manifest.json — bölüm ağacı (AR başlık, sıra,
  sayfa aralığı) + sürüm/kaynak bilgisi.
- web/public/reading/<pid>/sec_NNN.json — bölüm içeriği: paragraflar,
  mARkdown temizlenmiş, **PageVxxPyyy etiketleri sayfa-çapası olarak
  KORUNUR** (çıtanın 1. öğesi: atıf yeteneği).
- Üretici: pipelines/reading/build_reading_data.py (LaCie yolu →
  openiti_local_paths.json; deterministik, yeniden üretilebilir).
- Yapı probu: 8/10 kitapta ### başlık hiyerarşisi var; Fütûh (444 s.) ve
  İbn Havkal (498 s.) başlıksız → SAYFA-esaslı bölümleme (50 s./parça).
- "Çekirdek raf" üyeliği VERİYE YAZILMAZ — batch manifest'i (core_batches/
  batch_01.yaml) UI'nin build-time konfigürasyonudur (canonical temiz kalır).

## 3. Arayüz (v1 görsel dilinde)

**a) Kütüphane görünümü** (navbar → #library):
- Üstte "Çekirdek Külliyat" rafı: 10 kart (AR başlık büyük + TR + yazar +
  dönem + tür rozetleri + "atlas rolü" cümlesi — manifest'ten).
- Altta tüm katalog: Typesense araması (9,404 eser; iki yazıyla), yüzyıl/
  tür/dil facet'leri (çıta öğesi 4'ün sidebar deseni).

**b) Kitap sayfası** (#book?id=iac:work-XXXXXXXX) — 3 sütun:
- SOL: bölüm ağacı (sanal liste + diakritik arama; manifest.json'dan).
- ORTA: **OKUYUCU** — AR metin RTL/Amiri, sayfa çapası rozetleri
  (tıklanınca URL'e #book?id=..&sec=12&p=V02P0163 — paylaşılabilir atıf),
  bölüm ileri/geri.
- SAĞ: kimlik kartı — üç dilli başlık; YAZAR KARTI (canonical kişiye
  link: doğum-ölüm, harita); çift takvimli telif dönemi; sürüm/baskı
  rozetleri (klondaki N sürüm, seçilen birincil); tür etiketleri;
  "bu kitaptan türeyen katman" xref bloğu (Fütûh→[gelecek] fetih
  olayları; Bekrî→yer zenginleştirme); OpenITI GitHub linki; aynı
  yazarın öbür eserleri.

**c) Harita köprüsü:** kitap sayfasında "Haritada" sekmesi kitap→katman
dönüşümü yapıldıkça açılır (parti kitapları sırayla); o güne dek yazar
kartı üzerinden harita bağlantısı.

## 4. Uygulama sırası (S-D alt aşamaları)

D1 build_reading_data.py + 10 kitabın okuma verisi → D2 editoryal
tanıtımlar + canonical augment (kapı) → D3 UI Kütüphane + kitap sayfası +
okuyucu (tarayıcı doğrulaması) → D4 journal + commit. Her parti aynı
runbook'u tekrarlar.
