# DURAK (ziyaret) MODELİ — şema sözleşmesi + yeni seyahatnâme runbook'u

Hafta 21 / Dalga 4 · şema sürümü `durak-1.0.0` · 2026-07-20
Üretici: `pipelines/frontend/build_visits.py`
Çıktı: `web/public/books/visits.json` + `web/public/books/visits_meta.json`

> Bu belge bir **sözleşmedir**. Gelecekteki her seyahatnâme buraya bağlanacak;
> alan eklemek/çıkarmak şema sürümünü yükseltmeyi ve bu dosyayı güncellemeyi
> gerektirir.

---

## 1. Durak nedir, kaptan farkı ne?

**Kap (container, Dalga-1/2)** → "bu kitapta hangi kayıtlar var, pid'leri ne?"
`build_containers.py` → `books/<key>/manifest.json` + `pid_map.json`

**Durak (visit, Dalga-4)** → "seyyah nereye, hangi **sırayla** gitti?"
`build_visits.py` → `books/visits.json`

İkisi diktir:

* Bir kap **duraksız** olabilir — Yâkût bir coğrafya sözlüğüdür, güzergâhı yoktur.
* Bir durak **kapsız olamaz** — her durak bir kitaba aittir.

Durak modeli kabın yerine geçmez, üstüne biner. `yer_pid` üzerinden kap
`pid_map.json`'una, `(kaynak, sid, seq)` üzerinden kaynak katmanına bağlanır.

---

## 2. Şema

### 2.1 `seyahatler[]`

| alan | tip | zorunlu | anlam |
|---|---|---|---|
| `id` | string | ✔ | **kaynak önekli** seyahat kimliği (`rihla-v1`, `ibn-jubayr-v1`, `evliya-V05`) |
| `kaynak` | enum | ✔ | `rihla` \| `ibn-jubayr` \| `evliya` |
| `ad_tr` | string | ✔ | seyahatin Türkçe adı |
| `seyyah_pid` | string | ○ | `iac:person-*` |
| `work_pid` | string | ○ | `iac:work-*` |
| `n_durak` | int | ✔ | bu seyahatin durak sayısı (`duraklar[]` ile birebir doğrulanır) |
| `sira_turu` | enum | ✔ | `metin_tanikli` \| `dosya_sirasi` — **bkz. §3** |

### 2.2 `duraklar[]`

| alan | tip | zorunlu | anlam |
|---|---|---|---|
| `sid` | string | ✔ | ait olduğu seyahatin `id`'si |
| `seq` | int | ✔ | seyahat içinde **1..n kesintisiz** sıra |
| `yer_pid` | string | ○ | `iac:place-*` / `iac:institution-*` |
| `ad_ar` | string | ○ | Arapça ad |
| `ad_tr` | string | ○ | Türkçe ad |
| `lat` / `lon` | float | ○ | koordinat (ikisi birlikte ya vardır ya yoktur) |
| `varis_h` | string | ○ | hicrî varış tarihi — **yalnız kaynak tahmin olarak işaretlememişse** |
| `varis_metin` | string | ○ | metindeki varış **İFADESİ**, aynen; çevrilmez, normalleştirilmez |
| `is_stay` | bool | ○ | konaklama mı (geçiş değil) |
| `sec` | int | ○ | kitap bölümü / çapa |
| `guven` | string | ○ | **durak çıkarımının** güveni (`high`/`medium`/`low`) |
| `geo_note` | string | ○ | dup-cluster / belirsiz aday / `geo_suspect` notu |

---

## 3. `sira_turu` — bu modelin en önemli alanı

Sıra her kaynakta aynı şeyi ifade **etmez**.

| değer | anlam | UI kuralı |
|---|---|---|
| `metin_tanikli` | sıra metinden/çıkarımdan gelir, **güzergâhtır** | duraklar çizgiyle birleştirilir |
| `dosya_sirasi` | sıra yalnız kaynak dosyanın sırasıdır, **güzergâh DEĞİLDİR** | çizgi **çizilmez**, nokta bulutu |

**Neden var:** Evliyâ katmanının dosya sırası seyahatler arasında örülüdür —
5.444 kayıt `voyage_id`'ye göre **343 ayrı bloğa** dağılmış durumda
(V05×4 → V07×3 → V05×1 → …). Yani `EC_` id sırası bir güzergâh değil,
Başaran Google Maps dışa aktarımının liste sırasıdır. Bunu sessizce
`seq: 1..N` yazmak veriye **olmayan bir güzergâh iddiası** eklemek olurdu.

> **Kural:** Yeni bir kitap eklerken sıranın gerçekten metinden gelip
> gelmediğini **kanıtla** (blok sayısı / seq alanının varlığı / çıkarımın
> bölüm çapası). Kanıtlayamıyorsan `dosya_sirasi` yaz. Şüphe hâlinde
> `metin_tanikli` **yazılmaz**.

---

## 4. Değişmez kurallar

1. **Null şişirme yok.** Alan yoksa anahtar hiç yazılmaz. `"lat": null` diye bir
   şey yoktur; `lat` ya vardır ya yoktur. `false` ve `0.0` gerçek değerdir.
2. **Sıra korunur.** `seq` her seyahatte 1..n kesintisiz; üretici bunu
   çalışma anında doğrular ve tutmazsa **hata verip durur**.
3. **Koordinatsız durak atılmaz.** `yer_pid`/`lat`/`lon` olmadan girer.
   "Seyyah oraya gitti" ile "biz nokta koyabildik" iki ayrı olgudur; ikincisi
   birincisini kısaltamaz.
4. **`geo_suspect` silinmez, gizlenir.** Şüpheli koordinat `geo_note` ön ekiyle
   veride kalır; gizleme UI'ın işidir, boru hattının değil.
5. **Tarih tahmini yasak.** `varis_metin` metnin ifadesidir. `varis_h` yalnız
   kaynağın *kendisinin* tahmin olarak işaretlemediği hicrî tarihlerde yazılır.
   Türetilmiş milâdî tarihler şemaya hiç girmez.
6. **Anahtarlar daima kaynak önekli.** `sid` asla çıplak `V05` ya da `1`
   değildir. (H19 dersi: Salibiyyât `clusters[].id` = `EC_NNNN`, Evliyâ
   `EC_NNNNN` ile çakışıyordu.)
7. **Anlamı kaymış alan eşlenmez.** Evliyâ'nın `category_confidence` alanı
   *sınıflandırma* güvenidir, durak güveni değil → `guven`'e **eşlenmedi**.
   Aynı adı farklı anlama vermek sessiz bir yalandır.
8. **Rota omurgası ilkesi.** `visits.json` kaynak katmanların yerine geçmez;
   zengin alanlar (alıntı, anlatı, kişiler, açıklama, kategori) kaynakta kalır
   ve JOIN edilir. "Ortak şemaya alan ekleme" refleksi yerine
   "kaynak katmanında bırak" refleksi esastır.
9. **Determinizm.** Timestamp yok, `generated` alanı yok, sıralama sabit,
   `sort_keys=True`. `--check-determinism` bunu iki koşuyla kanıtlar.

---

## 5. Bölme kuralı (5 MB tavanı)

`visits.json` **5 MB**'ı aşarsa üretici hata verip durur ve Evliyâ
seyahat-bazlı ayrı dosyalara bölünür:

```
web/public/books/visits.json              → seyahatler[] + küçük kaynakların duraklar[]
web/public/books/visits/evliya-V01.json   → {"duraklar": [...]}
...
```

`visits_meta.json.toplam.bolme_gerekti_mi` bu durumu bildirir.
**Şu an:** 1.281.197 bayt (1,22 MB) → bölme **gerekmedi**.

---

## 6. RUNBOOK — yeni bir seyahatnâme nasıl eklenir (5 adım)

### Adım 1 — Kaynağın şeklini KEŞFET (varsayma)

```bash
python3 - <<'PY'
import json
from collections import Counter
d = json.load(open('web/public/data/<yeni>_layer.json'))
print(list(d))
print(Counter(k for s in d['<stops>'] for k in s).most_common())
PY
```

Cevaplanacaklar:

* Sıra alanı var mı? Global mi, seyahat-içi mi, kesintisiz mi?
* **Dosya sırası seyahatler arasında örülü mü?** (blok say → §3)
* Koordinat alanının adı ne? (`lon` mu `lng` mi — Evliyâ `lng` kullanıyor)
* Hangi alanlar **ölü**? (Evliyâ'da `volume` ve `year_approx` 5444/5444 null)
* Varış tarihi metin ifadesi mi, hesaplanmış tarih mi? Tahmin bayrağı var mı?

### Adım 2 — Kimlik pid'lerini çöz ve **dubletleri listele**

```bash
sqlite3 data/_index/lookup.sqlite \
  "SELECT l.pid, b.entity_type, l.text FROM label l
   JOIN entity_bracket b ON b.pid=l.pid WHERE l.text LIKE '%<seyyah>%';"
```

Dublet çıkarsa: **en küçük pid yazılır, adayların tamamı `IDENTITY`
sözlüğünde listelenir, otomatik birleştirme YAPILMAZ.** Dublet temizliği ayrı
bir insan kararıdır. (`build_containers.py` precedent'i.)

### Adım 3 — `yer_pid` kaynağını belirle

İki yol vardır, karıştırma:

* **Mağaza curie'si** (Battûta, Evliyâ):
  `SELECT source_id, pid FROM source_curie WHERE source_id LIKE '<önek>:%'`
  → yerel id'nin kaynak dosyadaki bir kayda **birebir oturduğu doğrulanır**.
* **Katmanın kendi `place_pid` alanı** (İbn Cübeyr):
  → `entity_bracket`'te var olduğu **doğrulanır**, doğrulanamayan raporlanır.

Curie yoksa `yer_pid` yazılmaz — uydurulmaz. Curie üretmek ayrı bir iştir
(`pipelines/integrity/h20_layer_curie_resolve.py`, Tier-2 resolver).

### Adım 4 — `build_visits.py`'ye bir `build_<kaynak>(cur)` ekle

```python
def build_<kaynak>(cur):
    layer = load_json(DATA / "<dosya>.json")
    ident = IDENTITY["<kaynak>"]
    voyages, stops = [], []
    for v in sorted(...):                      # sabit sıralama ŞART
        sid = "<kaynak>-{}".format(...)        # kaynak önekli
        for i, s in enumerate(sorted(...), 1): # sabit sıralama ŞART
            rec = {"sid": sid, "seq": i}
            put(rec, "ad_ar", s.get(...))      # put() = null şişirme koruması
            ...
            stops.append(rec)
        voyages.append({..., "sira_turu": SIRA_METIN | SIRA_DOSYA})
    report = {... , **geo_report(stops)}       # SAYILMIŞ sayılar, tahmin yok
    return voyages, stops, report
```

Sonra `BUILDERS` listesine, `IDENTITY` sözlüğüne ve
`visits_meta.json.sozlesme.kaynak_enum`'a (kod içinde) ekle.

Üreticinin kendi bekçileri seni koruyacak — biri patlarsa **düzeltilecek olan
senin dönüşümündür, bekçi değil**:

* `check_keys()` — şema dışı alan kaçağı
* yetim `sid` kontrolü
* `n_durak` ↔ gerçek sayım
* `seq` 1..n kesintisizliği
* `seyyah_pid`/`work_pid` mağazada var mı

### Adım 5 — Koş, determinizmi kanıtla, sayıları rapor et

```bash
python3 pipelines/frontend/build_visits.py
python3 pipelines/frontend/build_visits.py --check-determinism   # → EVET
```

`visits_meta.json.kaynak_basina.<kaynak>` altına şunlar **sayılmış** olarak
yazılır (hiçbiri tahmin değildir): `n_seyahat`, `n_durak`, `koordinatli`,
`koordinatsiz`, `yer_pid_li`, `yer_pid_siz`, `yer_pid_li_ama_koordinatsiz`,
`geo_suspect`, `tasinmayan_alanlar` + **gerekçesi**, ve varsa
`kapsam_uyarisi` / `olu_alanlar`.

Dürüst sınırlar `visits_meta.json.durust_sinirlar` listesine eklenir.
Bilinmeyen bilinmiyor diye yazılır; doldurulmaz.

---

## 7. Şu anki durum (2026-07-20, sayılmış)

| kaynak | seyahat | durak | koordinatlı | koordinatsız | şüpheli | `yer_pid` | kapsam | sıra |
|---|---|---|---|---|---|---|---|---|
| rihla (İbn Battûta) | 7 | 317 | 317 | 0 | 0 | 120 | %37,85 | `metin_tanikli` |
| ibn-jubayr (İbn Cübeyr) | 1 | 208 | 124 | 84 | 7 | 125 | %60,10 | `metin_tanikli` |
| evliya (Evliyâ Çelebi) | 10 | 5.444 | 5.444 | 0 | 0 | 4.807 | %88,30 | `dosya_sirasi` |
| **TOPLAM** | **18** | **5.969** | **5.885** | **84** | **7** | **5.052** | **%84,64** | — |

Dosya: `visits.json` 1.281.197 bayt (1,22 MB) · `visits_meta.json` 10.392 bayt

`sha256(visits.json)      = 88c171c87c2248368ba97c5a597735621f90e0733a3980448f93b32593ad5b8a`
`sha256(visits_meta.json) = e49f457870c88adaa3992efa1a1839400cfe71ae80c0ef5b00b5ea877c9cb611`

### Bilinen dürüst sınırlar

* **Evliyâ'nın sırası güzergâh değildir** (§3). Ayrıca kayıtlarının çoğu
  şehir içi **yapıdır** (cami 1.097, türbe 456, hamam 303, medrese 99…),
  güzergâh durağı değil; ayrım kaynak katmanın `category` alanındadır.
* **İbn Battûta**'da metindeki varış İFADESİ alanı yok → `varis_metin` hiçbir
  rihla durağında yazılmadı. `date_uncertain` işaretli **110** hicrî tarih
  bastırıldı; yazılan 65. `disputed: true` işaretli 10 durak visits.json'da
  ayrıca işaretlenmez — ihtilaf bilgisi kaynak katmandadır.
* **İbn Cübeyr**'in hicrî tarihlerinde yıl basamağı **tutarsız**
  (`578-10-26` ile `0578-12-08` bir arada). Düzeltilmedi, aynen taşındı;
  onarım kaynak boru hattının (`postprocess_ibn_jubayr.py`) işidir.
* **1 durak pid'li ama koordinatsız**: `ibn-jubayr-v1` seq 26 سبك/Sebk →
  `iac:place-00006269` mağazada var, `entity_bracket`'te lat/lon boş.
  Kimlik çözümü ile konum bilgisi ayrı olgulardır.
* **834 durak koordinatlı ama pid'siz** — çoğu Battûta ve Evliyâ'nın
  curie'lenmemiş kuyruğu. Bu bir eşleştirme işidir (Dalga-3 dersi:
  "eksikler mint değil eşleştirme sorunu"), durak modelinin değil.
* Seyyah/eser pid'lerinde **mağaza dubletleri var** (İbn Cübeyr kişi ×3,
  Evliyâ kişi ×3, her iki eser ×2); en küçük pid yazıldı, adayların tamamı
  `visits_meta.json.kimlik` altında listelendi, **birleştirme yapılmadı**.

---

## 8. Değiştirilmeyenler

* Hiçbir `.jsx` dosyasına dokunulmadı.
* Kaynak katmanların hiçbiri (`ibn_battuta_atlas_layer.json`,
  `stops_draft.json`, `evliya_atlas_layer.json`) değiştirilmedi — bu boru
  hattı **yalnız okur**.
* `build_containers.py` ve `books/<key>/` kap çıktıları değiştirilmedi.
* Hiçbir borderline karar otomatik bağlanmadı; inceleme kuyrukları
  (`data/review_queue/ibn-jubayr-stops.jsonl`) yerinde duruyor.
