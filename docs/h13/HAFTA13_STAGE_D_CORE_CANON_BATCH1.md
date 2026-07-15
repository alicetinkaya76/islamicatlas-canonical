# Hafta 13 · S-D — Çekirdek Külliyat Parti 1 CANLI (10 kitap, okuyuculu)

**Tarih:** 2026-07-15 · **Önkoşul:** parti-1 manifesti (atlas-DNA revizyonu)
+ tasarım dokümanı (derinlik çıtası).

## D1 — Okuma verisi (build_reading_data.py)

10 kitap LaCie klonundan işlendi: **3,48M kelime, 4,671 bölüm** →
web/public/reading/<pidnum>/ (gitignored; deterministik yeniden üretim).
- mARkdown çözümü: ### | hiyerarşisi; sayfa etiketleri (PageVxxPyyy)
  paragraf ÇAPASI olarak korunur; başlıksız kitap yok çıktı (Fütûh'un
  ### | seviye-1 başlıkları probe'un saydığı seviye-2'nin altındaydı).
- Düzeltilen kusurlar (tarayıcı/veri doğrulamasıyla): '**' başlık artığı;
  boş bölümler (ardışık başlık) → kırıntı-yolu birleştirme; Rafed kaynak
  çöpü (URL/görsel referansları) → Arapça-oran süzgeci (kalan çöp: 0).

## D2 — Canonical zenginleştirme (core_canon_augment.py)

10/10 kitaba: EDİTORYAL TR+EN tanıtım (kendi metnimiz, CC-BY-SA; DİA
kullanılmadı — ADR-014/İSAM) + not alanına bölüm/kelime/sürüm istatistiği
+ atlas-rolü cümlesi. İdempotent (marker); gate 160 passed; Typesense
57,250 tazelendi.

## D3 — Arayüz (LibraryView.jsx, v1 görsel dilinde)

- **Raf:** #library — altın Amiri Arapça başlıklı kitap kartları
  (bölüm/kelime + atlas rolü) — v1 koyu-altın dili.
- **Okuyucu:** 3 sütun (tasarım dokümanının birebir uygulaması):
  solda bölüm ağacı (diakritik-duyarsız arama, girinti = seviye, sayfa
  çipleri), ortada RTL Amiri okuyucu (19px/2.05 satır; sayfa-çapası
  rozetleri tıklanınca paylaşılabilir derin-link:
  #library?book=<pidnum>&sec=N&p=V01P030), sağda kimlik kartı (AR başlık,
  istatistik, PID, atlas rolü, OpenITI repo linki, kaynak kolofonu).
- App.jsx: 'library' sekmesi (📚 Kütüphane) + hash parametreleri.
- Tarayıcı doğrulaması: raf → Fütûhu'l-Büldân § "أموال بني قريظة"
  (V01P030 çapalı) uçtan uca; konsol temiz.

## Sonraki

Parti-1 kitaplarının kitap→katman dönüşümleri (Fütûh→fetih olayları,
Ezrakî→Mekke atlası...) ayrı aşamalar; parti-2 listesi manifest sonunda
onay bekliyor. Katalog araması (9,404 eser, Typesense) Kütüphane rafının
altına H12 S2 birleşik aramayla birlikte gelecek.
