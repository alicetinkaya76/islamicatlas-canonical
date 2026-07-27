# Hafta 28 — Analiz/Pano'nun canonical'laşması (1/n: Merkezî Defter kartı)

## Sorun (denetim KRİTİK bulgusu)
Pano "Genel Bakış" v1 db.json `.length` (186 hanedan / 450 âlim / 100 savaş) ile
v2 SOURCE_COUNTS'u (13.844) ETİKETSİZ karıştırıyordu; 67k+ kayıtlık canonical
mağaza Pano/Analiz'de HİÇ görünmüyordu. "450 âlim vs 22.777 canonical" en jarur
kopukluk.

## Çözüm: "Merkezî Defter (Canonical)" kartı — ayrı, etiketli, veri-güdümlü
`build_canonical_overview.py` → `web/src/data/canonical_overview.json` (build'de
üretilir; source_counts.json gibi bundle'lanır): mağaza namespace sayıları
(aktif = emekli değil) + Ulema Havuzu + kitap-türevi olaylar. ELLE sayı YOK —
canonical taramasından (~10 sn). Dashboard yeni kartta gösterir; v1 kürasyonlu
"Genel Bakış"tan görsel ve kavramsal olarak AYRI (altbaşlık: "v1 kürasyonlu
katmanlardan bağımsız").

## Sonuç (tarayıcı-doğrulamalı)
Pano'da yeni kart: 👤 22.824 Kişi · 📍 19.688 Yer · 📕 9.404 Eser · 📜 9.956 Olay
· 🏛️ 5.423 Kurum · 👑 186 Hanedan · 🎓 **22.777 Ulema Havuzu** (→#scholars) ·
🗄️ 5.618 Kitap Olayı (→ana harita katmanı) · toplam **67.481 aktif kayıt**.
"450 vs 22.777" kopukluğu çözüldü. Determinizm bayt-bayt. Gate 161.

## Sonraki (Analiz canonical'laşması devam)
- TimelineView'a canonical olay katmanı (5.618 olay Hicrî yıla göre — toggle,
  H26 ek-katman deseni).
- CausalView / ScholarNetwork canonical bağlama (opsiyonel).

## Değişen dosyalar
- `pipelines/frontend/build_canonical_overview.py` (yeni; üretici)
- `web/src/data/canonical_overview.json` (üretilen; bundle'lanır)
- `web/src/components/dashboard/Dashboard.jsx` (Merkezî Defter kartı)
- `Makefile`, `scripts/start_local.sh` (üretici build'e)
