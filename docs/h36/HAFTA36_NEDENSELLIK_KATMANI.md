# Hafta 36 — Nedensellik katmanı: pilot, denetim ve döngüsellik onarımı

Kullanıcı "nedensellik katmanını sen yapabilirsin" dedi. Bu, projenin **en
hassas** işi: nedensellik bir **yorumdur**, koordinat ya da tarih gibi olgu
değildir. Kurduğum ilke:

> Kendi tarihsel yorumumu ÜRETMEM. Yalnız **kaynağın kendisinin kurduğu**
> nedensel bağı, **birebir pasajıyla** çıkarırım.

## 1) Ölçüm — malzeme var
7 kronikte **11.253 olay** (Fütûh, Meğâzî, Sîre, el-Kâmil, Sülûk, Taberî,
Mürûc). İlk taramada 2.938'inde nedensel işaret bulundu.

## 2) Pilot (398 aday, Fütûh + Vâkıdî tamamı) → **DENETİMDEN KALDI**
4 çıkarım ajanı + 1 bağımsız denetçi. Kabul: 139/398 (%34,9).
Denetçi 40 kabulü kaynak metinle karşılaştırdı ve **ölçeklenmemeli** dedi.

### En ciddi bulgu: DÖNGÜSELLİK
Filtrem `summary_tr`'ye de bakıyordu — ama **`summary_tr` önceki bir LLM
adımının ürünü**. Havuzun **%58,3'ü yalnız Türkçe işaretle** giriyordu. Yani
"kaynağın kurduğu bağ" ölçütüm pratikte **"önceki LLM'in kurduğu bağ"a**
dönüşmüştü — CLAUDE.md'nin yorum-üretme yasağının en ciddi ihlal riski.

**Kanıt (kendi "en iyi örneğim" çürüdü):** `seq 13` Türkçe özette
*"…yüzünden… bunun üzerine…"* diyor; Arapça asılda yalnız `من … حتى` var.

### 8 yanlış-pozitif deseni (denetçinin tipolojisi)
| # | Desen | Örnek seq |
|---|---|---|
| D1 | fa-lammâ/lammâ **zaman çerçevesi** sebep sanılması (en yaygın) | 32, 45, 82, 229 |
| D2 | Anlatısal fâ (ta'kīb) ≠ fâ sebebiyye | 102, 107, 253 |
| D3 | Sebep alıntı DIŞINDAN anaforayla dolduruluyor | 105, 113, 150 |
| D4 | Onomastik gerekçe olay nedenselliği sanılması | 60, 208 |
| D5 | Aktörün iddiası = vakanüvisin iddiası sayılması | 122 |
| D6 | Sonuç gerçekleşmemiş (niyet) ama olmuş gibi | 250 |
| D7 | Alıntı dışına taşan sonuç halkası | 29, 122, 256 |
| D8 | Prosedürel totoloji ("sulh istediler → sulh oldu") | 253 |

### Denetçinin doğruladığı iyi yan
`quote_ar` **40/40 bayt-bayt** kaynakla aynı; uydurma alıntı YOK. İki kusur:
`"..."` elisyonu nedensel açıdan kritik metni atıyor (47, 122) ve `connector_ar`
sessizce imlâ düzeltmiş (`فزدهم` → `فردهم`) — denetlenebilirliği bozar.

### Recall boşluğu
Aday **olmayan** 1.054 kayıt Arapça nedensel kalıp taşıyor (حتى 733, لما 225,
**وذلك أن 6, خوفا 12, عصبية 5**) — yani **en güçlü kanıt tipi havuz dışında
kalıyordu**.

## 3) Onarım (bu turda uygulandı)
`extract_causal_candidates.py` yeniden yazıldı:
- **Kanıt yalnız Arapça asıldan** (`quote_ar`). Türkçe işaret artık aday
  YAPMAZ, yalnız `tr_hint` olarak kaydedilir → döngüsellik kırıldı.
- İşaretler **güç sınıfına** ayrıldı:

| Sınıf | Sayı | Anlam |
|---|---|---|
| `ar_strong` | **415** | açık ta'lîl (وذلك أن، لأن، بسبب…) veya mef'ûlün leh (خوفا، طمعا، عصبية…) |
| `ar_weak` | 2.288 | çok anlamlı (فلما، حتى، إذ…) — çıkarımda **varsayılan RED** |
| *(atlandı)* | 195 | Türkçe özet nedensellik diyor, Arapça asılda işaret YOK |

## 4) Sıkı ikinci tur (çalışıyor)
Yalnız **415 `ar_strong`** aday; prompt'a denetçinin 8 red deseni + zorunlu
alanlar eklendi: `link_type` (explicit_talil | motive_reported |
fa_consequential | temporal_only | onomastic), `asserted_by` (chronicler |
quoted_actor | isnad_report), `effect_realized` (gerçekleşti | niyet |
reddedildi), `evidence_complete` (sebep+sonuç ikisi de alıntıda mı).
`high` güven yalnız ilk iki `link_type`'a verilebilir. Elisyon ve imlâ
düzeltmesi yasak.

## 5) Mimari karar: sidecar, canonical'a yazma YOK
Şemada `causes`/`consequences` **zaten var** — ama tipleri **olay→olay PID
bağı** (`^iac:event-\\d{8}$`). Benim çıkardığım ise **kayıt-içi** nedensellik
("sel yüzünden sedd yapıldı") — tek olayın içinde. Şemayı zorlamak yanlış veri
üretirdi. Bu yüzden çıktı **sidecar**da tutulur; `causes` alanı ancak sebep
ifadesi başka bir canonical olayla eşleştirilirse (tarihçi onayıyla) dolar.

## 6) Yayın kuralı
Bu katman **iddia değil kayıt**tır: varsayılan `needs_human_review`; tarihçi
onayı olmadan atlas/analiz görünümüne bağlanmaz.

---

## 7) İkinci tur + ikinci denetim — belirgin ilerleme, iki yeni bulgu

Sıkı tur (415 aday, 4 ajan): **111 kabul (%26,7)**, 304 red. Kabul örnekleri
sağlam: `بسبب ابنين له أخذهما` · `بعلة الخوانيق` (hunnâk hastalığından öldü) ·
`خوفا من العار` (ardan korkup kendini boğdu) · `عصبية للحجاج` ·
`وذلك أنهم كانوا خالفوا عليه`.

### Denetimin doğruladıkları
| Desen | Durum |
|---|---|
| D1 fa-lammâ zaman çerçevesi | **TEMİZLENDİ** (70/70 kabulde yok) |
| D5 aktör-iddiası | **TEMİZLENDİ** (`asserted_by` 70/70 doldurulmuş) |
| D3 anafora dolgusu | Büyük ölçüde temiz; kalan 3 kayıt `evidence_complete=false`+`low` |
| `link_type`→`confidence` kuralı | **%100 tutuyor** — `high` yalnız explicit_talil/motive_reported |
| `quote_ar` sadakati | **70/70 bayt-bayt** kaynakla aynı; sıfır parafraz |
| D6 (gerçekleşmemiş sonuç) | `seq 250` doğru: `effect_realized=intent_only` |

### İki yeni bulgu (bu turun ürünü)
**(a) KODUMDA BUG — sahte eşleşme.** `MARKERS_AR` düz **substring** aranıyordu:
`لأن` işareti **الأنهار / الأنبار / الأنصار / الأندلس** içinde eşleşiyordu.
415 "güçlü" adayın **308'i sahteydi** (gerçek 107). Kelime-sınırlı regex'e
geçildi. Ayrıca kabul edilenlerin **24'ü** hasatçının hiç aramadığı kalıplardan
geliyordu (`وكان سبب`, `وسبب ذلك`, lâm-i ta'lîl + muzâri) → eklendi.
**Sonuç: ar_strong 415 → 195** (denetçinin "+80-90 aday" tahminiyle birebir).

**(b) Kararın kararlılığı kanıtlandı.** Gerçek-işaretli adaya göre kabul oranı
partiler arası **0,93 · 1,04 · 1,41 · 0,93** — yani B4'ün göze batan %41 kabulü
gevşeklik değil, **girdi bileşimi**. Düzeltmenin tuttuğunun en güçlü kanıtı.

### Kalan kusurlar (dürüstçe)
- **D4 onomastik/çıplak-ad:** `بسبب ابنة خاقان` gibi sebep bir *önerme* değil
  çıplak ad; yine de `high` verilmişti → `cause_is_proposition` alanı eklendi.
- **`effect_realized` sözlüğü bozuktu** (bir parti "true" yazmış, 29 kayıt
  makineyle denetlenemez) → şema `enum`'a bağlandı.
- **B4 partisinin 41 kabulü diskte yok** → CLAUDE.md'nin "her sayı `data/`den
  yeniden üretilebilir" kuralını ihlal ediyordu.
- Kronikler arası **mükerrerlik**: aynı olay 5 çift (%14) — "111 bağ" ≠ 111 olay.

### Denetimin nihai kararı — UYULDU
> **A. `ar_weak`'e ölçeklenmemeli.** 2.288 adayın %98,6'sı tam da D1/D2/D8
> üreten edatlar; beklenen hasat 2.288 okuma → ~10 bağ (bağ başına ~60 kat
> pahalı). **Uygulandı: ölçeklenmedi.**
> **B. Bugünkü hâliyle yayına uygun değil.** → Bu yüzden **temiz havuzla
> (195 aday) final koşusu** yapıldı: hem kirli adaylar elendi, hem B4'ün
> "çıktı diskte yok" sorunu ortadan kalktı (çıktı doğrudan alınıyor).

---

## 8) Final koşu ve kapanış

Temiz havuzla (195 `ar_strong`) son koşu — iki denetimin **tüm** kurallarıyla:

| | |
|---|---|
| İncelenen | 195 |
| **Kabul** | **170** |
| Red | 25 |

Kabul oranı %87; bu **kalite gevşemesi değil**, havuzun temizlenmesinin sonucu.
Denetçi zaten "gerçek-işaretli adayda kabul/işaret ≈ 1,0" ölçmüştü — birebir tuttu.

### Kalite dağılımı
- **link_type:** explicit_talil 144 · motive_reported 21 · onomastic 2 ·
  fa_consequential 2 · state_description 1
- **güven:** high 97 · medium 59 · low 14
- **kanıt tam** (sebep+sonuç ikisi de alıntıda): 144/170
- **sebep bir önerme** (çıplak ad değil): 147/170
- **effect_realized:** realized 169 · intent_only 1

Kuralların uygulandığının kanıtı (örnek kayıtlar):
- `seq 53` — sebep yalnız hastalık **adı** (`بعلة الخوانيق`) →
  `cause_is_proposition=false`, güven düşürülmüş (D4 kilidi çalışıyor).
- `seq 32` — çıkarımcı kendisi yazmış: *"gerçek suç halkası alıntıda yok"* →
  `evidence_complete=false`, `low`.
- `seq 254`, `seq 259` — sonucun zamiri alıntı dışına gönderiyor →
  `evidence_complete=false` (D3 kilidi).
- `seq 13`, `seq 142` — "bu yüzden ona X adı verildi" → `onomastic` (D4 ayrımı).

### Çıktı
`data/sources/causal/causal_links.json` — **sidecar**, canonical DEĞİL.
Her kayıt `needs_human_review: true`.

### Yapılmayanlar (bilinçli)
- **`ar_weak`'e ölçeklenmedi** (denetim kararı A). 2.110 adayın ~%98'i D1/D2/D8
  üreten edatlar; beklenen hasat ~10 bağ, bağ başına ~60 kat maliyet.
- **UI'a bağlanmadı.** Bu katman tarihçi onayı olmadan görünmez. CausalView
  db.json'daki 200 küratörlü bağla çalışmaya devam eder.
- **canonical'a yazılmadı** — `causes` alanı olay→olay PID bağı bekler.

### Devir (tarihçi kuyruğu)
1. 170 bağın onayı — öncelik: 97 `high` + `evidence_complete=true` olanlar.
2. 23 kayıt `cause_is_proposition=false` (sebep çıplak ad) — ayrı gözden geçirme.
3. Kronikler arası mükerrerlik (2. denetim: ~%14) — aynı olayın iki kaynakta
   farklı sebep atfı **tarihyazımsal olarak değerlidir**, silinmemeli, eşlenmeli.
4. Onaylananlar için sebep ifadesi başka bir canonical olayla eşleşirse
   `causes`/`consequences` alanı gerçek anlamıyla doldurulabilir.
