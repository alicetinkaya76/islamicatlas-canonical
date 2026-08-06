# H57 — Canonical hanedan katmanı ekrana çıktı

**Tarih:** 2026-08-06
**Durum:** kapandı
**Commit:** `2eb780cc`

H56 denetimi bir boşluk ölçmüştü ve o turda onarılmamıştı: **canonical
`dynasty` namespace'inin hiçbir öz alanı arayüze çıkmıyordu.**
`grep web/src` → `bosworth_id` 0 · `had_capital` 0 · `had_ruler` 0 ·
`patron_dynasty` 0 isabet. 186 kayıt, 828 hükümdar ucu, 129 başkent girdisi,
100 ardıllık kenarı ve 457 kurum-himaye bağı yalnızca diskte duruyordu.

---

## Ne yayınlandı — ve neden yalnız bunlar

Kural (H54 dersi): **v1'de zaten olanı tekrarlama.** Yayınlanan şey ya v1'de
hiç yok ya da v1'de tıklanamıyor.

| | durum | ölçüm |
|---|---|---|
| **Ardıllık** | v1'de **hiç yok** (`ctx_b`/`ctx_a` serbest anlatıdır, bağ değil) | 100 kenar, hepsi gezilebilir |
| **Başkent** | v1'de `cap` **metin** olarak var; canonical'ın bağı **yere gider** | 129 girdi, çözülemeyen 0 |
| **Himaye** | v1'de **hiç yok** | 457 kurum → 11 hanedan |

Ardıllık zinciri artık tıklanabilir: **Râşidûn → Emevî → Abbâsî**.

Himayedeki kurumların **kendisine bağ verilmedi** — canonical institution
pid'i v1 görünümlerinde mint edilmemiş (H56 üçüncü dalganın kararı: hedefsiz
bağ üretilmez). Yalnız sayı gösteriliyor.

## Ne yayınlanmadı — `dynasty_subtype`

Ölçüldü: değer kaynağın kendi ayrımından **kaba**.

```
canonical 'sultanate' (35 kayıt)  →  v1 'Sultanlık' 12 · 'Hanlık' 12 · 'Şahlık' 7 · karma 4
```

Bir hanlık sultanlık değildir. v1'in `gov` alanı hem daha ince hem **zaten
ekranda**. Bilinerek kaba bir etiketi yaymaktansa hiç yaymamak doğru.

---

## Çözümün nasıl yapıldığı saklanmıyor

**64 başkent girdisi** birden çok aday arasından **insan onayı olmadan**
seçilmiş (`status=ambiguous-picked`). Arayüz bunu söylüyor.

Ve daha önemlisi: **çözücünün başladığı ad, vardığı addan farklıysa ikisi de
gösteriliyor** (74 girdi).

### Doğrulanmış vaka: `Sâm ← Şam`

Emevîler'in başkenti kaynakta **'Şam'**. Çözüm:

```
iac:place-00006217   tr='Sâm'  ar='سام'  en='Sām'
   33.5138, 36.2765 · centroid · ±50 km
   note: Modern region: Dımaşk (Gûta bölgesi)
```

Bu, Gûta'da **ayrı bir yerleşim** — Dımaşk değil (`iac:place-00014039`,
33.51843/36.30199). Üstelik `status=unique` damgalı, yani çözücü **emindi**.

Bu sapmayı **genel bir kuralla yakalayamıyorum**: TR katlamasında 'Şam' ve
'Sâm' aynı dizeye iniyor — resolver'ı yanıltan şey tam olarak bu. O yüzden
hüküm vermiyorum; ekranda `Sâm ← Şam` yazıyor ve **hükmü okuyan veriyor.**

> Yakalayamadığım bir hatayı "yok" saymak yerine, görünür kılmak.

---

## Zamanlama kusuru: tembel veri + statik popup

Popup HTML'i bir **dize** olarak kuruluyor. Facet'ler tembel indiği için temiz
yüklemede blok **hiç basılmıyordu** — ölçüldü: `.p-canon` yok, ancak katman
başka bir sebeple yeniden çizilince çıkıyor.

Veri indiğinde bir kez yeniden çizim tetikleyen abonelik eklendi.

*Aynı gecikme `ensurePlaceIndex` için de geçerli* — kitap köprüsü de ilk
yüklemede kaçırılabilir. Ayrı bir tur.

---

## H56 dördüncü dalganın doğrulama borcu kapandı

O turda *"sınıflandırma şüpheli rozetini ekranda göremedim"* diye yazmıştım.
Evliyâ haritasında filtreleyip uzaklaşarak kümeyi çözdüm:

> **Üç Kule (Cetatea Tricule)** — `Kale · sınıflandırma şüpheli (0.40)`

Görsel doğrulama tamam.

---

## Doğrulama

- Canlı: `#dynasty/2` popup'ı → *"Öncülü: Râşidûn Halifeleri · Ardılı: Abbâsî
  Halifeleri · Başkent kaydı: Sâm ← Şam · Himayesindeki yapı: 14"*
- Üç kusur da mutasyonla doğrulandı
- **Test 280 → 289**, `vite build` yeşil

## Kalan

- `ensurePlaceIndex` aynı tembel-veri gecikmesini taşıyor.
- 64 onaysız başkent çözümü ve `Sâm ← Şam` sınıfı sapmalar **tarihçi
  kuyruğuna** aday — ama otomatik tespit edilemedikleri için kuyruk üretilmedi;
  ekranda görünür kılındılar. Bu bir Ali kararıdır: kuyruğa alınsın mı?
