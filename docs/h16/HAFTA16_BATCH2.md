# Hafta 16 — Parti 2: kroniklerin kaynak metinleri (12,4M kelime)

**Tarih:** 2026-07-17 · **Direktif:** "devam bitmeden durmak yok".

## Kitaplar (7/7 klonda doğrulandı, okuma verisi kuruldu)

| Kitap | Bölüm | Kelime | Katman türü |
|---|--:|--:|---|
| el-Kâmil (İbn el-Esîr) | 3,859 | 1,336,805 | ⚔️ olay (Salibiyyât KAYNAK metni) |
| Târîhu't-Taberî | 2,487 | 1,444,023 | ⚔️ olay (tarih yazımının omurgası) |
| es-Sülûk (Makrîzî) | 553 | 827,719 | ⚔️ olay (Memlük-Haçlı) |
| Mürûcü'z-Zeheb (Mes'ûdî) | 1,607 | 379,326 | ⚔️ olay |
| Târîhu Dımaşk (İbn Asâkir) | 1,291 | **8,290,229** | 🏛 DIMAŞK şehir atlası (142 topografik bölüm kapsamı) |
| Takvîmü'l-Büldân (Ebü'l-Fidâ) | 872 | 89,436 | 📐 KOORDİNAT tabloları (boylam/enlem) |
| el-Büldân (Ya'kûbî) | 102 | 31,311 | 🛤 yol/mesafe |
| **TOPLAM** | **10,771** | **12,398,849** | |

Kütüphane rafı: 10 → **17 kitap**. Editoryal TR+EN tanıtımlar 7/7 (DİA
kullanılmadı, ADR-014).

## Notlar

- **Sandbox dersi:** LaCie takılıyken bile bash-sandbox /Volumes erişimini
  engelliyor; okuma verisi `dangerouslyDisableSandbox` ile kuruldu.
- **Kümülatif raf:** build_reading_data artık mevcut kitapları korur
  (parti-2 koşusu parti-1'i ezmişti — düzeltildi, ders).
- Kronik çıkarımında yıl başlıkları ("ثم دخلت سنة ...") date_h'ye taşınır —
  tarihli olay oranı parti-1'den yüksek olmalı (mint edilebilirlik).

## Çıkarım sonuçları ve mint (2026-07-18)

365 ajan / 26,2M token / 1 hata (API). **Workflow VM dersi:** dönüş dizisi
4096 sınırını aştı (el-Kâmil tek başına 5,133) → workflow "failed" dedi ama
364 ajanın verisi journal'daydı; sonuçlar AJAN PROMPT'undaki pid'e göre
kitaplara ayrıştırılıp kurtarıldı (agent-*.jsonl'de prompt var).

| Kitap | Katman | Kayıt | Koordinatlı |
|---|---|--:|--:|
| el-Kâmil | ⚔️ olay | 5,133 | 2,914 |
| Taberî | ⚔️ olay | 2,282 | 1,410 |
| es-Sülûk | ⚔️ olay | 1,519 | 935 |
| Mürûc | ⚔️ olay | 599 | 351 |
| Ebü'l-Fidâ | 🗺 madde | 338 | 112 (+312 TARİHÎ koordinat) |
| İbn Asâkir | 🏛 Dımaşk yapısı | 314 | 128 |
| Ya'kûbî | 🛤 yol | 188 | 55 çift-uç |

**Canonical mint:** book-events 9,102 tarihli olay (kronikler yıl-başlıklı
→ tarihli-oran parti-1'in çok üstünde; 2,132 tarihsiz katmanda kalır) +
book-structures 1,481 yapı (Dımaşk eklendi) + Ya'kûbî 84 yer augment.
**Mağaza 58,744 → 67,833** (event 854→9,956!). Ebü'l-Fidâ'nın ortaçağ
enlem/boylamı MODERN KOORDİNATA ÇEVRİLMEDİ (farklı başlangıç meridyeni —
"tûl/arz" değerleri metindeki yazılı haliyle popup'ta gösterilir).

Kanıt: "Hıttîn" araması artık ÜÇ kaynaktan döner — salibiyyat tanıklığı +
editoryal kayıt + İbn el-Esîr'in kendi anlatısı (kamil).
