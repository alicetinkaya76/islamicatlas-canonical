# H41 — "Alatlı yok, âlimler hâlâ 450": görünürlük kusuru

**Tarih:** 2026-07-30
**Durum:** kapandı
**Tetikleyen:** Ali, yerel siteye bakıp *"alatlı yok bir mesela alimler hala 450
vb.. senin yaptığın birçok şey yok"* dedi.

## Bulgu — her şey oradaydı, hiçbiri görünmüyordu

Ölçüm (tarayıcı DOM'u, tahmin değil):

| Ekran | Açılışta görünen | v2 işi nerede |
|---|---|---|
| Âlimler | 🕸 Hoca-Öğrenci Ağı (v1, 450) | **4. sekmede** 🕌 Havuz (22.824) |
| Zaman Çizelgesi | 🏛 Hanedanlar (v1) | 2. sekmede ⇄ Senkronik — **"Alatlı" adı hiç geçmiyordu** |

Veri dosyalarının hepsi sorunsuz servis ediliyordu (ulema_pool 2.1 MB,
alatli_synchronic 276 KB, scholar_network 950 KB — hepsi HTTP 200). Yani sorun
erişim değil **keşfedilebilirlikti**.

Ali "Alatlı yok" derken haklıydı: ekranda o ad **hiçbir yerde yazmıyordu**.
Kaynak adı, katmanın keşfedilebilirliğinin kendisidir.

Bu, en baştaki "v1 ve v2 ayrık duruyor" şikâyetinin devamı. H33–H38'de
**menüleri** birleştirmiştim; ekranların **içi** hâlâ v1-varsayılandı ve v2'nin
işi isimsiz sekmelerde duruyordu.

## Yapılanlar

1. **Sayı rozetleri** — 🕌 Havuz `22.824`, 🔗 Canonical Ağ `3.393`. v1 render
   yoluna dokunulmadı (ek katman deseni).
2. **Alatlı adıyla anılıyor** — `⇄ Senkronik (Doğu↔Batı)` →
   `⇄ Senkronik — Alatlı (670)`.
3. **Pano'nun iki kartı arasındaki kopukluk kapandı** — "Genel Bakış" başlığına
   *"— elle kürasyonlu çekirdek set (v1)"* etiketi ve *"Defterin TAMAMI için
   aşağıdaki Merkezî Defter kartına bakın (67.481 kayıt)"* satırı. 450 sayısı
   yanlış değildi; **etiketi** eksikti.

### Kendi kuralımı ihlal ettim, düzelttim
Rozet sayılarını önce **sabit kodladım** (22.824 / 3.393 / 670) — tam olarak
H27 denetiminin eleştirdiği "elle recordCount" hatası; veri değişince sessizce
yanlış olurdu. `build_source_counts.py`'a dört üretici eklendi
(`ulemapool`, `scholarnet`, `alatli`, `causal`) ve bileşenler `fmtCount()` ile
oradan okuyor. `causal` rozeti **onaylanan** bağı sayar — onaysız bağ hiçbir
yere girmediği gibi sayılmaz da.

## Yan bulgu — Pano bütün sayılarını 0 gösterebiliyordu

Ölçerken Pano `🏛 0 · 📚 0 · ⚔ 0` döndürdü. Bunu daha önce "CountUp artefaktı"
diye geçmiştim; bu kez sebebi ölçtüm: `document.hidden = true`, rAF **500 ms'de
0 kare**. Tarayıcı gizli/arka plan sekmede rAF'ı kısıyor → sayaç mount olursa
**"0"da kalıyordu**. Veri yerindeydi; animasyon hiç başlamıyordu.

Benim ölçüm ortamımın artefaktıydı, ama gerçek bir dayanıklılık kusurudur:
arka planda açılan bir sekmede kullanıcı da 0 görür.

**Kural: animasyon SÜSTÜR, sayı VERİDİR.** `CountUp` artık gizli sekmede son
değeri doğrudan yazıyor, sekme görünür olunca animasyonu bir kez oynatıyor, ve
`duration + 400 ms` emniyet kemeriyle rAF hiç ateşlenmese bile sayı yazılıyor.
(H17'de aynı rAF kısıtlaması kaydırmada öğrenilmişti; sayaç düzeltilmemişti.)

## Aynı turda: kuyruktaki 22 bağ (H40 hattı)

Alıntı pencereleri ~**10 kat** genişletildi (142 → 1.411 karakter; 11 kayıtta
bölümün tamamı pencereye girdi) ve iki bağımsız mercekle yeniden yargılandı:
**16 onay · 3 red · 3 kuyrukta** (çelişenler kuyrukta bırakıldı).

Onaylananlarda ajan yeni alıntı sınırını da verdi; **16'sının 16'sı kaynakta
birebir doğrulandı** (`verify_quote`, apply hattında). 15 kayıtta okuma da
düzeltildi — eskisi `*_original` alanlarında duruyor.

Örnek: `00000331:678` — dar alıntıda `ذلك`'in mercii yoktu; geniş pencere
gösterdi ki kaynağın kurduğu bağ *"İbnü'z-Zübeyr'in Mekke'de biat alması →
Yezîd'in Amr b. Saîd'i azledip Velîd b. Utbe'yi tayin etmesi"*; önceki okuma
sebep-sonucu bir halka geriye kaydırmıştı.

**Nedensellik katmanı nihai: 170 bağ → onay 163 · red 4 · kuyrukta 3.**
Okuyucu köprüsü: 163 bağ · 6 kitap · 159 bölüm.

## Ayrıca: iki vite süreci

Port 3000'i **iki gün önce** başlatılmış bir vite tutuyordu, ikincisi de
ayaktaydı. Bayat süreç + `.vite` dep cache temizlendi, tek sunucudan yeniden
başlatıldı. Bu, Ali'nin gördüğü tablonun bir kısmını açıklıyor olabilir.

## Doğrulama

- `make test` → **178 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: rozetler `🕌 Havuz 22.824`, `🔗 Canonical Ağ 3.393`,
  `⇄ Senkronik — Alatlı (670)`; Pano gizli sekmede bile 186/450/830 gösteriyor;
  Analiz menüsünde ⚖️ Nedensellik Onayı; konsol hatasız.
- Görünürlük denetimi (7 kalem): H25 Şehir Atlası ✓, H26 harita canonical
  katmanı ✓, H28 Pano canonical kartı ✓, H35 kürasyon rafı ✓, H37 onay
  ekranı ✓, H30 Alatlı ✓ (adıyla), H34 canonical ağ ✓ (rozetli).

## Ders

**"Var" ile "görünür" aynı şey değildir.** Bir katmanı eklemek, onu
erişilebilir kılmaz; adı ekranda geçmiyorsa ve sayısı görünmüyorsa, kullanıcı
için yoktur. Bundan sonra her yeni katman için üç soru: (1) adı ekranda geçiyor
mu, (2) büyüklüğü rozetle görünüyor mu, (3) rozet üretimden mi geliyor?
