# ADR-016: Yer ince-tipi — şema alanı DEĞİL, yayın katmanı

**Status:** Accepted (uygulandı, H54)
**Date:** 2026-08-02
**Phase:** 0
**Decision-makers:** Ali Çetinkaya (kararı devretti: "sen karar ver")
**Related:** ADR-013 (şema seti atomik sürümleme), ADR-006 (adapter deseni),
H51 yer ekseni denetimi, H54 uygulaması

---

## Context

H51 yer denetimi iki bulguyu birlikte ölçtü:

1. **`place_subtype` yalnız ÜÇ kaba değer taşıyor** — `settlement` 11.150,
   `region` 747, `iqlim` 21.
2. **`note` alanında 64 İNCE TİP duruyor** — mountain 1.215, water 703,
   river 352, valley 344, well 237, monastery 171, spring 128, pass 86,
   island 73, desert 67, wadi 33 …

İlk kaydın `note`'u sebebi de yazıyor:

> `Yâqūt geo_type: 'well' (no schema subtype mapping in v0.1.0; place_subtype omitted)`

Yani adapter, şemada karşılığı olmayan tipi **bilinçli olarak** note'a yazmış.

Sonuç: canonical, bu boyutta **v1'in `yaqut_lite`'ından fakir.** v1 `gt/gtt/gte`
üçlüsünü %100 dolulukla taşıyor ve `YaqutIdCard` bunları `GEO_ICONS` ile zaten
çiziyor — hatta canonical'dan daha ince (`city` ↔ `settlement`).

Doğal öneri: `place.schema.json`'a `place_subtype_fine` eklemek (64 değerlik
kapalı sözlük) ve note'tan doldurmak.

## Decision

**Şemaya alan EKLENMEYECEK.** İnce tip, yayın katmanında
(`view-data/place_facets.json`) sunulur; canonical kayıt olduğu gibi kalır.

## Rationale

**1. Maliyet asimetrik.** ADR-013 gereği şema seti **atomik** değişir: v0.4.0 →
v0.5.0 demek, tüm fixture'lar, reçeteler ve doğrulama döngüsü demek. Kazanç ise
tek bir görüntüleme alanı — ve o alan v1'de **zaten var**.

**2. Depo bu dersi iki kez verdi.** H31'de `change_type: "repair"` şemadan
geçmedi ve `"update"` kullanıldı; H49'da `record_history`'ye `migration` alanı
eklendi, şema `additionalProperties: false` ile reddetti ve bilgi `note`a
gömüldü. Her ikisinde de **şemayı zorlamak yerine mevcut yapıyı kullanmak**
doğru çıktı.

**3. Yayın katmanı şemaya tabi değil.** `view-data/` üretilen bir katman;
zenginlik oraya taşınabilir, canonical'ın sözleşmesi bozulmaz. H54 bunu yaptı:
18.843 kayıtta olgu, her biri `_kaynak` işaretiyle (`alan` = doğrulanmış
canonical alan, `note` = metinden ayıklandı).

**4. Asıl kusur burada değil.** `place_subtype`'ın fakir olması bir **semptom**;
kök neden Yâkût adapter'ının şemada karşılık bulamayınca tipi note'a yazması.
Gerçek çözüm adapter'ı düzeltip yeniden mint etmek olurdu — ama bu 12.954 kaydı
yeniden yazmak, `provenance.created` alanlarını ezmek demektir (H10'da el-Aʿlâm
tam yeniden koşusu tam bu gerekçeyle reddedilmişti). Şema alanı eklemek o kök
nedeni **çözmez**, üstüne bir katman daha koyar.

## Consequences

**Olumlu**
- Canonical sözleşmesi ve şema sürümü sabit kalır; fixture/reçete döngüsü açılmaz.
- Kullanıcı bugün etimoloji, dönem, otorite bağı ve üst konumu görüyor (H54).
- Ayıklama gerçekten çalışıyor ve ölçüldü — ileride şema kararı verilirse
  besleyecek veri hazır (`place_facets.json`, 64 tekil tip).

**Olumsuz / kabul edilen**
- Canonical `place_subtype` kaba kalmaya devam eder. Dışa aktarımda (Zenodo,
  LOD dump) ince tip **bulunmayacak** — yalnız yayın katmanında var.
- Bu, ileride bir yayın paketi hazırlanırken yeniden gündeme gelecektir; o zaman
  karar **adapter onarımı + yeniden mint** ekseninde ele alınmalı, tek bir alan
  eklemek olarak değil.

**Geri dönüş**
Bu karar tersine çevrilebilir: `place_facets.json` üreticisi (`_kaynak: "note"`
olan `tip` alanı) doldurulacak şema alanının veri kaynağıdır. Karar değişirse
göç girdisi hazırdır.

## Notes

Kararın kapsamı **yalnız yer ince-tipidir.** Aynı desendeki başka boşluklar
(ör. kişi tarafında `note`'a gömülü meslek ayrımları) ayrı ayrı değerlendirilir;
bu ADR onlara emsal teşkil etmez — yalnız gerekçe kalıbı ortaktır: *şemayı
zorlamadan önce yayın katmanının yeterli olup olmadığını ölç.*
