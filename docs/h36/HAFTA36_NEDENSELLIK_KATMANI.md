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
