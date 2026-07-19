# Hafta 14 — Parti-1 TAMAMLANDI: 10 kitap, 10 katman, 5,328 kayıt

**Tarih:** 2026-07-16 · **Direktif:** "parti 1 kitaplarının hepsini böyle
yap ve devam et" + sahip kararı: doğrudan yayın.

## Katman envanteri (hepsi UI'da, tarayıcı-doğrulamalı)

| Kitap | Tür | Kayıt | Koordinatlı | Not |
|---|---|--:|--:|---|
| İbn Cübeyr Rihlesi | 🧭 rota | 208 | 125 | %80 tarihli; rota-bağlam geocoding |
| Bekrî Mu'cem | 🗺 gazetteer | 538 | 179 | LLM'siz yapısal (madde=bölüm) |
| Fütûhu'l-Büldân | ⚔️ olay | 811 | 497 | fetih/idare olayları, tarihli |
| Vâkıdî Meğâzî | ⚔️ olay | 266 | 167 | sefer kronolojisi |
| İbn Hişâm Sîre | ⚔️ olay | 643 | 339 | 2,164 bölümden süzüldü |
| Ezrakî Ahbâru Mekke | 🏛 yapı | 808 | 205 | merkez-politikası (Mekke 120km); 90 uzak-homograf gizli |
| Târîhu Bağdâd | 🏛 yapı | 632 | 266 | 107 topografik bölüm kapsamı; 35 gizli |
| İstahrî Mesâlik | 🛤 yol | 1,203 | 281 çift-uç | +557 tek-uç; mesafe ifadeleri AYNEN |
| İbn Havkal | 🌍 bölge | 124 | 94 | şehir-listesi centroid'i |
| İdrîsî Nüzhet | 🌍 bölge | 95 | 52 | iklim-cüz tasvirleri |
| **TOPLAM** | | **5,328** | **2,205+** | |

## Yöntem (runbook, tekrarlanabilir)

Çıkarım: 314 paralel Claude ajanı toplamda (25+124+165), ~14.7M token,
0 ajan hatası. Katı kurallar: tarih/mesafe yalnız metindeki ifadeyle;
birebir pasaj + sayfa çapası zorunlu. Son-işlem: tür-bazlı jenerik boru
hattı (book_geo 3-kademeli bağlama; merkez/rota/bağlamsız politikaları;
süreklilik/yarıçap şüpheli-gizleme). UI: 5 görünüm türü (rota/olay/yapı/
madde/yol/bölge) tek jenerik bileşende; her kayıttan "bölümü oku §N".

Yayın: sahip kararıyla doğrudan (H14 Karar); confidence/geo_note/
geo_candidates alanları veride — dürüstlük veri düzeyinde.

## Faz-2 adayları (bu katmanlardan canonical'a)

Olay katmanları (Fütûh 811 + Meğâzî 266 + Sîre 643) event-mint adayı;
Ezrakî+Bağdâd yapıları institution-mint adayı (Mekke/Bağdat şehir
atlasları); İstahrî çift-uç yolları rota-kenarları. Hepsi kitap-içi
katman olarak yayında; canonical mint ayrı aşama.
