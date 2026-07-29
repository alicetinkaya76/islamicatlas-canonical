# H39 — Devredilmiş yargı: 170 bağın 147'si onaylandı, 22'si kuyrukta kaldı

**Tarih:** 2026-07-28/29
**Durum:** kapandı
**Yetki:** Ali "sen çalıştır" dedi → karar devri (H22'nin "bana hiç karar bırakma,
kanıtla sen karar ver" ilkesinin bu katmana uygulanması).

## Yöntem — üç tur, hepsi Arapça asıl üzerinden

Doktrin gereği kararı bir script veremez; **kanıta bakan yargı** vermeli. Üç tur:

**1. tur — iki bağımsız mercek (24 ajan).** 170 bağ, 12 parti. Her parti iki ayrı
akıl tarafından *sıfırdan* okundu; ikinci mercek birincinin kararını **görmedi**
(pipeline'da `prevResult` bilerek kullanılmadı).
- Mercek A: klasik Arapça filolojisi — bağlaç gerçekten ta'lîl mi, yoksa
  zaman/gaye mi (`فلما/لما/حتى/إذ`)? Kelime sınırında mı, yoksa başka kelimenin
  içine mi düşmüş?
- Mercek B: kaynak tenkidi — `cause_tr`/`effect_tr` alıntının İÇİNDE var mı? Yön
  doğru mu? Sonuç gerçekleşmiş mi? Bağı kronikçi mi kuruyor?

Sonuç: 149 mutabık, 20 çelişki (hakeme), 1 tek-mercekli. → onay 159, red 1, skip 10.

**2. tur — GEÇERSİZ (yöntem hatası, aşağıda).**

**3. tur — çürütme (20 ajan, 60 kayıt).** Onay oranı %94 çıkınca kendi yargımın
gevşek olup olmadığını sınadım. Hedef iki kümeydi: 30 **riskli** kayıt (H36'nın
bayrakları, düşük güven, zayıf bağlaç tipi) + 30 **kör kontrol** (temiz
onaylananlardan `seed=42` ile rastgele). Çürütücülere `link_type`, `confidence`
ve risk bayrakları **verilmedi** — yalnız Arapça metin ve doğrulanacak iddia.

## 2. turun geçersizliği — ve nasıl yakalandığı

Çürütücülere kayıtları `python3 -c "…"` ile okutmuştum; escape yüzünden komut
çalışmadı, ajanlar `00000331_events.json` katmanına bakıp *"bu kayıt
causal_links.json'da yok"* diye **48 sahte çürütme** üretti.

İki bağımsız sinyal yakaladı:

| Kontrol | Ölçüm |
|---|---|
| 1. tur anahtarları ↔ `causal_links.json` | 170/170 birebir |
| Çürütme hedefleri ↔ aynı dosya | 60/60 birebir |
| Kör kontrolde devrilen | 25/30 |
| Risk kümesinde devrilen | 23/30 |

İkinci tablo tek başına yeterliydi: **gerçek bir çürütme turunda risk kümesi kör
kontrolden daha çok devrilir.** Tersinin çıkması, çürütücülerin ayrım
yapmadığını — sinyal değil gürültü ürettiğini — gösteriyordu.

**Onarım:** kayıtlar prompt'a GÖMÜLDÜ, ajan hiç dosya okumuyor. "Yanlış dosyaya
bakma" hata sınıfı yapısal olarak imkânsız hale geldi.

Düzeltilmiş tur: devrilen **12/60** — risk kümesi **9/30 (%30)**, kör kontrol
**3/30 (%10)**. Asimetri artık doğru yönde ve 3 katı; kalibrasyon sağlıklı.

## Çürütmelerin ne bulduğu — H36'nın bayrağı haklıydı

Devrilen 12 kaydın gerekçeleri tek bir sınıfta yoğunlaşıyor: **`بسبب`'den sonra
bir olay değil çıplak bir ad geliyor.**

> `هدم الرشيد سور الموصل بسبب العطاف بن سفيان الأزدي`
> — Attâf'ın *ne yaptığı* alıntıda yok; sebep ucu metinde kurulmuyor.

Bu tam olarak H36'nın `cause_is_proposition=false` bayrağıdır. 1. turun
yargıçları bu bayraklı 23 kaydın 22'sini geçirmişti; çürütme turu onların bir
kısmını geri aldı. **H36'nın kendi denetimi haklıydı, benim yargıçlarım gevşekti.**
Onay kapısının üç turlu olmasının somut karşılığı bu.

Diğer çürütme sınıfları: `ها`/`ذلك` zamirinin mercii alıntı dışında (bağın bir
ucu metinde yok); alıntı gerekçe cümlesinin ortasında kesik (işleyen sebep
girmemiş); metnin zinciri A→B→C iken kayıt A→C demiş.

## Nihai karar

| | |
|---|---|
| **Onay** | **147** |
| Red | 1 |
| Kuyrukta (skip) | 22 |

Çürütme **red değil skip** üretir: "bağ yanlış" değil "kanıt yetersiz" demektir,
kayıt insan kuyruğunda kalır. Her karar gerekçesiyle birlikte `review` alanına
yazıldı (`basis`, `reason_a`, `reason_b`, `reason_arb`, `evidence`) — gerekçesiz
karar denetlenemez ve bilinçli olarak geri alınamaz.

Karar dosyası repoda: `data/sources/causal/causal_review_decisions.json`.

## Onaylananlar artık metnin yanında

Onay kapısının anlamı, onaylanan bağın okunduğu yerde görünmesi:

- `build_causal_review.py` ikinci bir çıktı üretir: `causal_reader_links.json` —
  **yalnız onaylı bağlar**, kitap→bölüm indeksinde. Kapı veri düzeyinde uygulanır,
  UI'da değil. Ölçüm: **147 bağ · 6 kitap · 143 bölüm**.
- `LibraryView` okurken bölümde onaylı bağ varsa "⚖️ Kaynağın bu bölümde kurduğu
  sebep–sonuç" kutusunu gösterir. Ek katman deseni: dosya boşsa bölüm eskisi gibi
  görünür, v1 okuma yolu değişmez.

## Ölçümle yakalanan iki kusur daha

1. **Onay ekranı veriye işlenmiş kararları görmüyordu.** Yalnız `localStorage`'a
   bakıyordu → 148 karar işlenmişken ekran "170 kaldı" diyordu. Artık kalıcı
   karar (`review.verdict`) ile yerel taslak birlikte okunuyor, hangisinin
   nerede olduğu ekranda yazıyor ("veride" / "yerel") ve kararın gerekçesi
   kartta görünüyor.
2. **`start_local.sh` kendi zincirini ayrı tutuyordu** — `build_causal_review`
   Makefile'da vardı, orada yoktu. Aynı bayatlama sınıfı; hizalandı ve iki
   zincirin aynı üreticileri koşturduğu `diff` ile doğrulandı.

## Doğrulama

- `make test` → **177 geçti**, 2 atlandı, 3 xfail.
- Yerel yığın ayakta: Typesense sağlıklı, vite :3000.
- Onay ekranı: `147 onay · 1 red · 22 kuyrukta · 148 veriye işlenmiş`, gerekçe
  kartta görünür — tarayıcıda ölçüldü, konsol hatasız.
- Okuyucu: el-Kâmil §2628'de iki bağ metnin üstünde, bağlaç + sayfa çapasıyla.

## Ali'ye kalan

22 kayıt hâlâ insan kuyruğunda — hepsi "kanıt yetersiz" sınıfından, çoğu
**alıntı sınırı** sorunu: bağ kaynakta var olabilir ama pasaj o bağı taşıyacak
kadar geniş alınmamış. Bunları çözmenin yolu yeniden yargı değil, **alıntı
pencerelerini genişletmek** (H36 hattına dönüş). Ayrıca kronikler arası
tekrarlar (~%14): farklı kronikçilerin aynı olaya farklı sebep atfetmesi
tarihyazımsal olarak değerlidir — silinmez, bağlanır.
