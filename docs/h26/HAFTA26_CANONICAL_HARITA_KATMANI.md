# Hafta 26 — Ana haritaya canonical olay katmanı (frontend→mağaza, EK)

## Sorun (kullanıcı "önerinle git")
Ana #map (MapView) yalnız bundle'daki `db.json`'dan besleniyor (100 savaş +
200 olay). Canonical mağazadaki **9.956 kitap-türevi olay** (Fütûh fetihleri,
Vâkıdî gazveleri, Taberî/İbn Esîr/İbn Asâkir kronik olayları…) ana haritada
**hiç görünmüyordu** — "v1-v2 birleşmedi"nin en büyük kalan boşluğu. Ana React
uygulaması Typesense'i HİÇ kullanmıyor (yalnız ayrı `lite/` sitesi kullanıyor).

## Çözüm: opsiyonel EK katman (v1'e dokunmadan)
MapView'de zaten var olan overlay deseni (HeatmapLayer/ScholarMigrationMap
toggle'ları) izlendi. **CanonicalLayer** eklendi — varsayılan KAPALI toggle
("📜 Kitap Olayları"); açılınca canonical olayları camgöbeği (v1 altınından
ayrışan) marker olarak bindirir, kapanınca temizler. v1 render'ına DOKUNMAZ.

**Üretici** `build_canonical_map_layer.py` → `view-data/canonical_events.json`
(gitignored, build'de üretilir): 9.956 olaydan `location` alanı koordinatlı bir
canonical PLACE'e çözülen **5.618'i** alınır; **yer başına toplanır** (721
marker) — pile-up (Bağdat 388 olay) tek üstüne yığılmasın. Her yer: sayı +
alt-tür dökümü + ilk 25 olay (başlık tr/ar + Hicrî yıl + kitap pid + bölüm).

**Dürüstlük:** koordinat olayın değil, işaret ettiği PLACE'in (gazetteer) —
uydurma değil, ama place belirsizliğini taşır; popup bunu "yer" olarak sunar.

## Çift yönlü köprü (kapanan döngü)
Marker popup'ındaki her olayda **"§N↗" derin-linki** → `#library?book=<pid>&sec=N`:
ana harita → canonical olay → **Kitap Kabı okuyucu** (kaynak pasaj). H25'in
kitap↔atlas köprüsüyle birlikte artık: kitap ↔ şehir atlası ↔ ana harita ↔
kaynak pasaj hepsi birbirine bağlı.

## Tarayıcı-doğrulamalı
- v1 harita default'ta AYNEN çalışıyor (401 marker); toggle açınca **+721**
  camgöbeği marker (1122); kapatınca temiz **401'e döner** (cleanup OK).
- Popup örneği: "Âlîn · 1 canonical olay · Battle · H.129 …" + `§1501↗` →
  `#library?book=00000338&sec=1501` (Taberî). 0 konsol hatası.
- Üretim: 721 yer · 5.618 olay (Bağdat 388 · Dımaşk 238 · Mekke 183 · Kûfe 166 ·
  el-Medîne 148). Deterministik. Gate 160.

## Bilerek YAPILMAYAN (sonraki)
- Yıl-kaydırıcısına bağlama (katman şu an tüm olayları gösterir; opt-in).
- Institution/place katmanları (event en yüksek değer/dürüstlük dengesi).
- Kümeleme (721 marker performansı iyi; 5.618 tek tek çizilmiyor — yer başına
  toplandı).

## Değişen dosyalar
- `pipelines/frontend/build_canonical_map_layer.py` (yeni; üretici)
- `web/src/components/map/CanonicalLayer.jsx` (yeni; overlay bileşeni)
- `web/src/components/map/MapView.jsx` (import + state + toggle + render)
- `Makefile`, `scripts/start_local.sh` (üretici build'e)
- `web/public/view-data/canonical_events.json` (üretilen; gitignored)
