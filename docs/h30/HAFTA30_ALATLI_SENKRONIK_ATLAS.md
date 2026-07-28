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

## H31 DÜZELTMESİ — keşif iki hatamı ortaya çıkardı, ikisi de giderildi

Paralel keşif (4 ajan) ilk sürümdeki **iki ciddi hatayı** buldu:

**(1) ETİKETLEME HATASI (dürüstlük).** İlk sürüm "DOĞU / BATI" yazıyordu.
Upstream'in kendi notu: **"canon = Alatlı'nın editöryel çerçevesi (COĞRAFYA
DEĞİL)"**. Yani ayrım coğrafi/etnik değil, antolojinin kendi terimleri:
`bize` (bize yön veren metinler) / `batiya` (Batı'ya yön verenler).
→ UI artık "BİZE / BATIYA" diyor ve ekranda **"coğrafi ya da etnik bir ayrım
DEĞİLDİR"** uyarısı duruyor.

**(2) KAYNAK HATASI (kapsam).** İlk sürüm iki ayrı yerden besleniyordu
(canonical=Doğu, yan-tablo=Batı). Ölçüm bunun ÇARPIK olduğunu gösterdi:
canonical'daki Alatlı izli kayıtlar `bize` kanonunun **ALT KÜMESİ** (232/359 —
kalanı inceleme kuyruğunda) ve canonical'da **6 `batiya` kaydı** da var, yani
"canonical = Doğu" varsayımı yanlıştı.
→ Artık TEK KAYNAK `data/sources/alatli/main.json` (677 kayıt, `canon` etiketi
kaynağın kendisinden). Canonical yalnız **bağlantı katmanı**: alatli id → pid
eşlenirse kayıt tıklanabilir.

**Yeni sayılar (ölçüm):** "bize" **358** · "batiya" **308** · her iki kanonda
**4** (iki şeritte de görünür, `both` işaretli) · tarihsiz **15** çizilmedi ·
merkezî deftere bağlı **231**. Önceki sürüm 227+274 idi → kapsam genişledi,
üyelik artık kaynağın kendi etiketinden.

**Yerleşim onarımı:** 358+308 kayıt lane-paketlenince "BATIYA" şeridi ekrandan
taşıyordu; lane tavanı (42) + ince lane (4px) ile ikisi de aynı ekranda. Tavanı
aşan lane modulo ile sarılır — çizgiler üst üste binebilir, **kayıt kaybolmaz**.

**Doğrulama:** 1033 çubuk; 1274 → Bize 11 / Batıya 8; 1600 → 12 / 21;
Mevlânâ (1273, pid'li) ↔ Thomas Aquinas (1274) duruyor; editöryel-çerçeve ve
coğrafi-değil uyarıları ekranda; **0 konsol hatası**.

## Kalan
- Referans HTML'deki **harita** bileşeni (yıl→coğrafya) bu sürümde YOK — repoda
  koordinat yok (uydurulmaz). Upstream `app_data.json`'da `place.lat/lon` 522/677
  dolu → aktarılırsa harita mümkün (Faz-2).
- "tıkla-kaynağa-in" (Alatlı cilt/sayfa): repoda `cites` alanı yok; upstream'de
  677/677 dolu → aktarım gerekir. Store'da pasaj tutulmaz (telif).
- Doküman tutarsızlığı: augment sayısı ALATLI_TELIF_KAPISI.md'de 183, HANDOVER'da
  181; dosyadan sayım **181** (234−53).

---

## H32 — Harita + "kaynağa in" eklendi (kalan iki eksik kapandı)

H30/H31'de "koordinat repoda yok, cilt/sayfa atfı yok" diye dürüstçe
işaretlenmişti. Upstream'de ikisi de vardı; **yalnız bu iki alan** aktarıldı.

**Aktarım** `pipelines/adapters/alatli/enrich_geo_cites.py` →
`data/sources/alatli/_alatli_geo_cites.json` (677 kayıt · **522 koordinat** ·
**677 atıf**).

**TELİF SINIRI (bilinçli):**
- ALINDI: `place.lat/lon` (olgu) + `cites[].vol/book_page/pdf_page/role/text`
  (bibliyografik künye — olgusal atıf).
- **ALINMADI: `desc`** (açıklama düzyazısı olabilir). ALATLI_TELIF_KAPISI.md'nin
  *"store'da Alatlı düzyazısı YOK — hiç pasaj alınmadı"* ilkesi korundu.
  Doğrulandı: aktarılan kayıtlarda `desc` alanı **0**.
- Sidecar da `alatli` katmanındadır → yayın kapısı aynen geçerli.

**UI (SynchronicStrips):**
- Hover künyesine **📖 cilt · sayfa** + künye metni + "(+N)" ek atıf sayısı.
- **🗺 Harita** toggle: seçili YILDA yaşayan + koordinatlı kişiler
  (bize=altın, batıya=camgöbeği), popup'ta ad/yıl/yer + cilt-sayfa.
- Ekranda: *"Haritada yalnız KOORDİNATLI kayıtlar var (526/666); koordinatsız
  olanlar uydurulmadı."*

**Doğrulama (canlı):** 1274 → haritada **14 kişi**; altın noktalar Anadolu/İran/
Orta Asya, mavi noktalar Batı Avrupa — senkroniklik coğrafi olarak da görünüyor.
Şerit sayaçları Bize 11 / Batıya 8. 0 konsol hatası. Gate 163.

**Not:** `enrich_geo_cites.py` upstream'e (repo dışı) bağlı olduğu için build
zincirine EKLENMEDİ; sidecar repoda durur, upstream değişirse elle çalıştırılır.
