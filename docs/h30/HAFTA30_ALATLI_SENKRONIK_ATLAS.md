# Hafta 30 — Track-3: Alatlı senkronik atlası (Doğu ↔ Batı yan yana)

## Neden
Alatlı'nın (*Tarihe Yön Veren Metinler*) biricik katkısı **senkronik bakış**:
bir yılda İslam dünyasında kim yaşıyordu, aynı anda Batı'da kim? Backend oturumu
234 kaydı canonical'a işledi ve bu görünümü UI tarafına fırsat olarak bıraktı.

## Veri gerçekliği (ölçüldü — hipotez ÇÜRÜTÜLDÜ)
İlk ölçümüm "Doğu tarafının %0'ı tarihli" dedi → **yanlış alana bakmışım**
(`temporal` yok; şema `birth_temporal`/`death_temporal`/`floruit_temporal`).
Doğru ölçüm:

| Şerit | Kaynak | Kayıt | Tarihli | CE aralığı |
|---|---|---|---|---|
| **DOĞU** | canonical mağaza (`alatli:` izli, aktif) | 227 | **%100** | −551 → 2007 |
| **BATI** | `_alatli_western_held.json` (MINT DEĞİL) | 280 | 274 çizilebilir | −814 → 1985 |

Senkronik gösterim **bugün mümkün**. Kanıt kesiti (~1300):
**Mevlânâ ö.1273 ↔ Thomas Aquinas ö.1274** — tam da antolojinin vaadi.

## Telif kararı (mevcut karara dayandı, yeniden yorumlanmadı)
`docs/h25/ALATLI_TELIF_KAPISI.md`: telif-hassas olan tek şey Alatlı'nın **SEÇİMİ**
(düzyazı hiç alınmadı); karar → Alatlı-türevli kayıtlar "**kişisel/araştırma
sürümünde kalır**", kamuya açık CC-BY-SA dump'a izin gelene kadar girmez.
Bu görünüm yerel araştırma arayüzündedir → **gösterilebilir**. Çıktı JSON'u
`publication_gate: "alatli"` ile işaretlendi; UI kapıyı **ekranda yazıyor**;
yayın hattı kurulunca tek filtreyle dışlanır.

## Yerleşim kararı: ayrı sekme DEĞİL, mod
Denetim (H27) yeni sekmenin **8 dokunuşluk fan-out** gerektirdiğini ve sessiz
kırıldığını göstermişti (VALID_TABS/nav/dispatch/SWIPE/i18n/BottomTabBar/drawer).
Bu yüzden Zaman Çizelgesi'ne **mod** eklendi: `🏛 Hanedanlar | ⇄ Senkronik`.
App.jsx'e HİÇ dokunulmadı. Hanedan SVG'si DOM'da kalır (D3 ref kopmasın), yalnız
gizlenir.

## Ne yapıldı
- `pipelines/frontend/build_alatli_synchronic.py` → `view-data/alatli_synchronic.json`
  (deterministik; tarihsiz kayıt ÇİZİLMEZ — uydurma yok; AH→CE dönüşümü meşru,
  koordinat dönüşümü değil). Makefile + start_local'e bağlandı.
- `web/src/components/timeline/SynchronicStrips.jsx` (yeni): iki paralel şerit,
  lane-paketleme (çakışma yığılması), yıl kaydırıcı + dikey imleç, o yılda
  yaşayanlar parlak/diğerleri soluk, hover künye, tıkla → Doğu: havuzda ara,
  Batı: Wikidata (pid YOK, çünkü mint edilmedi).
- `TimelineView.jsx`: mod düğmeleri + koşullu render (v1 çizimi bozulmadı).

## Dürüstlük notu (ekranda yazıyor)
Sayaçlar **antolojinin seçim dağılımıdır, tarihsel üretkenlik ölçüsü değildir.**
Ölçülen: 1273 → Doğu 8 / Batı 7; 1500 → 14/20; 1850 → **5/41**. Bu eğilim
Alatlı'nın modern dönem için daha çok Batılı metin seçmesini yansıtır; "Doğu
geriledi" diye okunamaz. UI bunu ⚠ ile açıkça söyler.

## Doğrulama
Tarayıcı: mod düğmesi çalışıyor, 868 şerit çubuğu, kaydırıcı 1273/1500/1850'de
sayaçları doğru güncelliyor, telif+seçim notu ekranda, **0 konsol hatası**.
Gate 161.

## Kalan
- Referans HTML'deki **harita** bileşeni (yıl→coğrafya) bu sürümde YOK — Batı
  kayıtlarında `place_label` var ama koordinat yok (uydurulmaz); Faz-2.
- "tıkla-kaynağa-in" (Alatlı cilt/sayfa) — store'da pasaj tutulmuyor (telif),
  yalnız `record_count` var.
