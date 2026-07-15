# Çekirdek Külliyat Programı — OpenITI'ye Yâkût muamelesi (10'ar kitap)

**Tarih:** 2026-07-15 · **Kullanıcı talebi:** "OpenITI corpus'u Yâkût gibi
detaylı eklemek; corpus çok büyük → aşamalı: must olan 10 kitap, sonra 10
daha..."

## Program

Katalog (9,404 kitap) GENİŞ-SIĞ kalır (başlık+yazar+link — H13 S-B bitti).
Seçilmiş çekirdek kitaplar 10'arlı partilerle DERİNLEŞİR; her parti
bağımsız kapanır (kapı+journal+commit), liste onayı Ali'de.

## Parti runbook'u (kitap başına)

1. LaCie klonundan tam metin; birincil sürüm seçimi (Ghazali-RAG dersi:
   İhyâ → Shamela .completed) + mARkdown yapı çözümü (### | hiyerarşisi —
   İhyâ probu: 40 kitâb `### ||` + 227 bâb `### |||`, 69,626 satır).
2. Canonical zenginleştirme: EDİTORYAL TR/EN tanıtım (DİA metni
   KULLANILMAZ — İSAM izni yayın şartı, ADR-014; kendi 2-3 cümlelik
   tanıtımımız), yapı istatistiği, baskı bilgisi.
3. Okuma verisi: web/public/reading/<pid>/toc.json + bölüm JSON'ları
   (gitignored — LaCie'den script'le yeniden üretilir; deploy'da statik
   varlık olarak yüklenir). Tam metin CANONICAL'A GİRMEZ.
4. İlişkiler: OpenITI book_relations (şerh/muhtasar) + katman köprüleri
   (Mu'cem→place, Rihle→ibn-battuta durakları, Taberî/Kâmil→olaylar).
5. UI: Kütüphane'de "Çekirdek Külliyat" rafı + bölüm-bölüm okuyucu.

## Parti 1 (data/sources/openiti/core_batches/batch_01.yaml)

10 kitap: Buhârî, Müslim, Muvatta, İhyâ, İbn Haldûn, Kânûn, Taberî
Tefsir+Tarih, Mu'cemü'l-Büldân, Rihle. Tamamı klonda doğrulandı
(sürümleriyle). Tema: mutlak klasikler + atlas katmanlarının kaynak
metinleri (kitap↔harita kenetlenmesi programın kilit fikri).

**Durum (2026-07-15):** Parti 1 CANLI — okuma verisi + canonical augment +
Kütüphane/okuyucu arayüzü tamam (HAFTA13_STAGE_D_CORE_CANON_BATCH1.md).
