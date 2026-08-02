# H53 — Darphane katmanı merkezî deftere bağlandı

**Tarih:** 2026-08-02
**Durum:** kapandı

H51 yer denetiminin ölçtüğü kusur: **`darpislam_lite.json` 3.381 darphane
taşıyor ama pid alanı olan kayıt sayısı 0.** Oysa `lookup.sqlite`'ta 2.338
`darp-islam:*` curie'si zaten `iac:place-*`'e bağlıydı. Yani bağ verideydi,
yayına hiç çıkmamıştı.

Bu, denetimin *"2.481 aktif yer hiçbir görünümde yok"* bulgusunun en büyük
parçasıydı (2.226 darp-islam yeri).

## Yapılan

`build_darp_pids.py` → `view-data/darp_pids.json`: darphane id → yer pid.
v1'in `darpislam_lite.json` dosyasına **dokunulmadı** (o dizin v1'e symlink;
oraya yazılmaz). Kart, pid'i olan darphaneden Yâkût kaydına geçiyor:
`🌍 Mu'cemü'l-Büldân'da →`.

| | |
|---|---|
| darphane | 3.381 |
| **pid bulunan** | **2.335 (%69)** |
| pid yok (dürüst) | 1.046 |
| yumuşak-silinmiş yere bağ verilmedi | **3** |

## İki dürüstlük kararı

**1. Ad benzerliğiyle eşleştirme YAPILMADI.** 1.046 darphanenin curie'si yok;
onlara ad benzerliğinden pid türetmek cazipti (oranı %69'dan %90'a çıkarırdı)
ama aynı adı taşıyan farklı darphaneler olağandır ve yanlış eşleşme kullanıcıyı
**başka bir şehre** götürür. Rozet o kayıtlarda hiç çıkmıyor.

**2. Yumuşak-silinmiş yere bağ verilmedi.** 3 curie, H50'de birleştirilmiş bir
yere işaret ediyordu. Kayıt canonical'da yaşıyor ama yayınlanan katmanlarda
görünmüyor — bağ boş ekrana götürürdü. H49'da kişi tarafında öğrenilen kural
burada da geçerli: **"pid yaşar" ile "UI onu bulur" aynı şey değildir.**

## Guard
Köprüde lite'ta bulunmayan id olamaz; hedefler yumuşak-silinmiş olamaz.

## Doğrulama
- `make test` → **214 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: darphane ekranı açılıyor, konsol temiz; köprü 2.335 kayıt.

## H51 denetiminden kalan
- Canonical yer alanları arayüzde yok (`place_subtype`, `located_in`,
  `authority_xref`, `temporal_coverage` → grep 0)
- `note` yapısal alana dönüştürülmedi — **şema değişikliği gerektiriyor**
  (`place_subtype` 3 kaba değerde; 69 ince tip note'ta ayrıştırılabilir hâlde
  bekliyor: mountain 1.214, water 704, valley 342…). Bu bir ADR kararı.
- Kalan ~146 yetim yer (le-strange 180, ibn-battuta 116 vb. — bir kısmı
  darphane köprüsüyle zaten çözüldü)
