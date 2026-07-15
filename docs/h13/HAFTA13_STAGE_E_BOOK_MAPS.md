# Hafta 13 · S-E — "Her kitabın kendi haritası": kitap→yer anılma çıkarımı

**Tarih:** 2026-07-15 · **Kullanıcı direktifi:** "bu 10 kitabı en derinlikli
olarak en sofistike UI ile ekleyene kadar durmak yok."

## Çıkarım (extract_book_mentions.py)

10 kitabın 3,48M kelimelik metni, mağazanın 18,380 Arapça-etiketli yer
kaydına karşı tarandı (16,862'si koordinatlı — **Yâkût'un sözlüğü öbür
kitapları haritalandırıyor**). FUZZY YOK; dia_travel'ın kanıtlı
belirsizlik-korumalı birebir deseni, Arapça sürümü + üç yeni koruma
(hepsi koşu-kanıtlı, iteratif):

1. **ة→ه normalizasyonu KALDIRILDI** — yer 'علية' ile edat 'عليه'
   birleşip her kitapta binlerce sahte anılma üretiyordu.
2. **Tip-ötesi belirsizlik koruması** — tek-kelimelik ad mağazada herhangi
   bir KİŞİ etiketiyle de çakışıyorsa sözlük dışı (عمرو/يزيد/الحسن
   vakaları); çok-kelimeli adın tüm token'ları kişi-kelimesiyse (künye:
   أبو محمد) aynı şekilde dışarıda.
3. **Şöhret-veya-yerellik kuralı** — tek-kelimelik ad ya BELİRGİN kayda
   (≥2 kaynak-curie veya otorite bağı) çıkar ya da 10 kitabın ≤3'ünde
   görülür; her kitapta geçen silik kayıt = homograf (فكان/ثلاث/أراد
   sınıfı). + 3 turda büyütülen editoryal stoplist (sayılar, günler,
   cins isimler; dökümler journal'da).

Sonuç kalitesi (top-anılmalar): Fütûh → إرمينية/السواد/ملطية (fetih
coğrafyası ✓); İstahrî → ما وراء النهر/فرغانة ✓; Ezrakî → المسجد الحرام/
دار الندوة ✓; Tarîhu Bağdâd → سر من رأى (Samarra) ✓; İbn Cübeyr →
الحجر الأسود/الحجاز ✓. Uzun kuyrukta kalan tekil homograflar harita
filtresiyle (total≥2 veya çok-kelimeli) bastırılır.

Çıktılar: reading/<pidnum>/mentions.json (UI) +
data/_state/core_canon_mentions_batch1.json (ileriki olay-mint/küratörlük
girdisi — canonical'a YAZILMAZ; anılma ≠ doğrulanmış tarihsel bağ).

## Arayüz (LibraryView güncellemesi)

- Okuyucu ortasında **📖 Metin | 🗺 Kitap Haritası (N)** geçişi; harita =
  koyu CARTO zemin + anılma-yoğunluğu ölçekli altın circleMarker'lar;
  marker popup'ında bölüm düğmeleri (§N → tıklayınca o bölümün metnine
  döner) — kitaptan haritaya, haritadan kitaba çift yönlü köprü.
- Sağ kimlik kartında "📍 Bu bölümdeki yerler" çipleri (Amiri, RTL).
- Tarayıcı doğrulaması: Fütûh haritası 356 nokta — Endülüs'ten
  Mâverâünnehir'e kitabın gerçek fetih coğrafyası; konsol temiz.

## Bilinen sınırlar

Anılma çıkarımı OTOMATİKTİR ve canonical veri DEĞİLDİR (UI katmanı +
pending girdisi). Kesinlik top-listelerde yüksek, uzun kuyrukta homograf
kalıntısı olabilir; kitap→katman gerçek dönüşümleri (Fütûh→fetih olayları
mint'i vb.) tarihçi-onaylı ayrı aşamadır.
