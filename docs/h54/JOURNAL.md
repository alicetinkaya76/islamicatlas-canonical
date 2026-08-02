# H54 — Yer olguları yayına çıktı; şemaya dokunulmadı

**Tarih:** 2026-08-02
**Durum:** kapandı — H51 yer denetiminin son maddeleri

## Şema kararı ve gerekçesi

Denetim iki bulguyu birlikte ortaya koymuştu:

1. Canonical yer alanlarının **hiçbiri** arayüze çıkmıyordu — `place_subtype`,
   `located_in`, `temporal_coverage`, `authority_xref`, `yaqut_id` için
   `grep web/src` **sıfır** isabet.
2. Deponun en zengin yer katmanı `note` içinde **string olarak hapisti**:
   modern ülke 11.237 · bölge 8.531 · geo_type 6.999 · DİA 6.776 · etimoloji
   6.000 · dönem 2.320. Ve `place_subtype` yalnız **üç** kaba değer taşırken
   note'ta **64 ince tip** duruyordu (mountain 1.215, water 703, river 352…).

Cazip olan `place.schema.json`'a `place_subtype_fine` eklemekti. **Yapmadım.**
ADR-013 gereği şema seti atomik değişir (v0.4.0 → v0.5.0, tüm fixture ve
reçeteler) ve H31 ile H49'da iki kez öğrenildi: şemayı zorlamak yerine mevcut
yapıyı kullanmak ucuz. **Yayın katmanı şemaya tabi değil** — zenginlik oraya
taşındı, canonical olduğu gibi kaldı. Şemaya alan eklenip eklenmeyeceği Ali'nin
ADR kararı; bu tur o kararı beklemeden değeri veriyor ve kararı da
kolaylaştırıyor (ayrıştırmanın çalıştığını sayıyla gösteriyor).

## Üretilen

`build_place_facets.py` → `view-data/place_facets.json` (3,1 MB):
**19.929 kayıt → 18.843'ünde olgu**; yumuşak-silinmiş 241 kayda facet
üretilmedi (yayında görünmüyorlar).

| kaynak | olgu |
|---|---|
| **alan** (doğrulanmış canonical) | subtype 11.860 · located_in 1.429 · temporal 709 · xref 2.774 |
| **note** (ayıklanmış) | tip 6.982 · ülke 11.209 · bölge 8.518 · etimoloji 5.988 · dönem 755 |

Her olgu `_kaynak` taşıyor. **Ham `note` metni taşınmıyor** — kişi tarafında
note'un %84'ü üretim iziydi (H44) ve ham göstermek yanıltıcıydı.

## Ekrana çıkarken kendi işimi kestim

İlk sürüm ülke/bölge/tip rozetlerini de basıyordu. Ölçtüm: **`yaqut_lite` bunları
zaten taşıyor** — ct 10.997, rg 8.519, gt 12.935 — ve tipi canonical'dan **daha
ince** (`city` ↔ `settlement`). Yani rozetlerim kartı tekrarla şişiriyordu.

Ekrana yalnız **v1'de karşılığı olmayan** olgular çıkıyor: etimoloji, tarihsel
dönem, otorite bağlantısı, üst konum. Ülke/bölge/tip yan dosyada duruyor —
oradaki değerleri "canonical v1'den fakir" bulgusunun ölçüsü olmak.

Bağdat kartı artık şunu gösteriyor:
`🔗 1 otorite` · `🏷 Farsça: bāgh (bahçe) + dād (verme) = "bahçe hediyesi"`
— **etimoloji ilk kez görünüyor.**

## Kaynak ayrımı görsel

`_kaynak: "note"` olan rozetler **kesik çerçeveyle** çiziliyor, `alan` olanlar
düz çerçeveyle. Ayıklanmış bilgi, doğrulanmış alan gibi durmamalı; başlık
metni de bunu yazıyor.

## Guard (+2)
- Her olgu `_kaynak` taşımalı, UI ayrımı görsel olarak göstermeli.
- v1'de zaten olan alanlar (`fac.ulke/bolge/tip`) ekrana basılamaz.

## Doğrulama
- `make test` → **216 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: Bağdat kartında otorite + etimoloji; ülke/bölge tekrarı yok.

## Ali'ye kalan (tek madde)
`place.schema.json`'a ince tip alanı (`place_subtype_fine`, 64 değerlik kapalı
sözlük) eklenecek mi? Ayrıştırma çalışıyor ve ölçüldü; karar şema sürümünü
v0.5.0'a taşımaya değer mi sorusudur. Bugün yayın katmanı bu boşluğu kapatıyor,
yani acil değil.
