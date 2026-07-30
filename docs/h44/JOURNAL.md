# H44 — Âlimler ekseni denetimi: "havuzda artırınca ne elde ediyoruz?"

**Tarih:** 2026-07-30
**Durum:** ilk dalga kapandı (kalan maddeler aşağıda)
**Tetikleyen:** Ali: *"âlimlerle ilgili tüm siteyi gözden geçirmen lazım, site
hâlâ birbirinden çok kopuk gidiyor; mesela havuzda artırınca ne elde ediyoruz,
bunu kapsamlı olarak incelemelisin."*

6 eksende paralel denetim koşturuldu (veri değeri, UI yüzeyleri, bağlantı
grafiği, arama, kimlik tekilliği, tasarım eleştirisi) → **60 bulgu, 35 kritik**.

## Sorunun cevabı

**Bir dizin kazandırdı, bir âlim veritabanı kazandırmadı.**

Kazanç ölçüldü ve gerçek: adreslenebilir kişi 450 → **18.564** (havuzun %81'i
çalışan bir kaynak maddesine gidiyor), 22.624 kayıtta ölüm tarihi, 16.305'inde
Arapça ad var. Ama havuz **7 alan** yayınlıyordu (`id, ad_tr, ad_ar, oh, om, k,
m`); mağazada duran **7.919 hoca**, **7.926 talebe**, **8.298 yer bağı** ve
21.883 notun **hiçbiri** arayüze çıkmıyordu. Yani büyüme kayıt **sayısını**
artırmış, kayıt **derinliğini** ekrana taşımamıştı.

## Kök neden

Denetimin teşhisi üç başlıkta toplanıyor; ikisini bu turda kapattım:

1. **Yayın sözleşmesi (LITE) ilişkileri bilerek düşürüyordu.** Kopukluk veri
   eksikliğinden değil, publish katmanının darlığından. Aynı desen her yerde:
   17/17 kitap manifestinde `author.pid` var ama LibraryView okumuyor;
   `scholar_network.json`'un 3.393 düğümünün tamamında pid var ama çıkış düğmesi
   **ada göre** arama yapıyor.
2. **Köprü tablosu tek eksenli** (alam↔dia); EI-1 haritası yok, havuza dönüş
   bağı hiçbir kartta yok.
3. **Kimlik ekseni geride kaldı** — aynı kişinin 2-3 canlı pid'i var. *(Bu tur
   kapsamı dışında; Ali'nin dup-merge oturumuna bağlı.)*

## Bu turda onarılanlar

### 1. Arama tümüyle ölüydü — en kritik bulgu
`normalize()`'ın Arapça sınıfı `[ؐ-ٰٟ]` "hareke aralığı"
sanılmıştı. Gerçekte **U+061B–U+064A arasında 43 Arap HARFİ** var
(ا ب ت ث ج ح خ … ي). Ölçüldü:

- `normalize('الغزالي')` → `''`
- Havuzdaki 16.305 Arapça adın **16.146'sı (%99)** boşa düşüyordu.

Ayrıca `'İ'.toLowerCase()` → `'i' + U+0307`; bileşik nokta kalınca "İbn Sînâ"
araması "ibn sina" ile eşleşmiyordu — H31'de **veri tarafında** onarılan aynı
sınıf hatanın arayüz karşılığı.

Onarım: harekeler iki ayrı blokta (`ؐ-ؚ`, `ً-ٟ`, `ٰ`),
harf bloğu dışarıda; NFKD + birleşik işaret temizliği; tatvîl silme.
Regex'ler `\u` kaçışıyla yazıldı — **çıplak Arapça sınıf kaynak dosyada bidi
ile yer değiştirip sessizce başka bir aralığa dönüşebiliyor; kusurun kökeni bu.**

Doğrulama (tarayıcı): `الغزالي` → 6 sonuç, `ibn sina` → 6 sonuç. Öncesinde ikisi
de sıfırdı. Guard test mutasyonla sınandı.

### 2. Ana haritanın 450 âlim popup'ı "undefined — undefined" basıyordu
`PopupFactory.buildScholarPopup` `s.field` / `s.sub` okuyordu; db.json'da bu
adlarda alan **yok** (0/450). Doğru adlar `disc_tr` (450/450) ve `works_tr`
(246/450) — veri hep oradaydı, alan adı tutmuyordu. LayerManager ham kaydı
gönderiyor, `scholar_meta.js`'te de bu adlar yok; yani değer hiçbir yoldan
dolmuyordu. Ölçüm: **450/450 bozuk → 450/450 dolu**. Veri yoksa artık satır
hiç basılmıyor ("undefined" yazmaktansa yazmamak).

### 3. Havuz kartı mağazanın zenginliğiyle beslendi
İki yan dosya (LITE endeksi bozulmadan, tembel yüklenir):
- `ulema_pool_links.json` (659 KB) — hoca/talebe/yer, **8.928 kişi**
- `ulema_pool_notes.json` (1,5 MB) — nottan **ayıklanmış** bilgi, ilk seçimde

**`note` alanı biyografi DEĞİLDİR** — ölçüldü: %84'ü üretim izi
("cross-reference", "slug=", "Chunk count", "Promoted from iac:…"). Ham
göstermek yanıltıcı olurdu. Bu yüzden içine gömülü gerçek bilgi ayıklanıyor:
doğum yeri (3.848), uzmanlık kategorisi (6.129), kaynağın kendi ölüm ifadesi
(7.199), serbest not (12.008 — etiket önekleri temizlenmiş).

Sonuç, Hillî örneğinde: *Doğum yeri: Hille · Uzmanlık: fıkıh·kelâm·fetva ·
Kaynakta: (ö. 676/1277) · Talebeleri (2): TÛSÎ, Nasîrüddin*.

İsnâd uçlarının 15.738'i havuz içinde, 107'si dışında; dışarıdakiler ham pid
yerine "(havuz dışı)" etiketiyle, tıklanamaz gösteriliyor.

### 4. Rota onarımları
- `CanonicalIsnadNetwork`: `?q=<ad>` → `?pid=` (3.393 düğümün hepsinde pid var).
- `ScholarView`: `initialSearch` ile gelen eski `?q=` bağları da havuza düşüyor.

## Doğrulama
- `make test` → **182 geçti**, 2 atlandı, 3 xfail (+4 yeni guard).
- Tarayıcı: arama, popup, havuz paneli, isnâd bağı tek tek ölçüldü; konsol temiz.
- Yeni üretici iki zincire de eklendi (`Makefile` ↔ `start_local.sh` `diff` ile
  aynı doğrulandı).

## Kalan (denetimden, bu tura girmedi)
1. **person_bridge'e EI-1 yönü** — 972 EI-1 rozeti ölü (`person_bridge.json`
   anahtarları yalnız `alam`/`dia`).
2. **`b` rozetini alt-kodlara ayır** (openiti/bosworth/dia-chunks) — 3.105
   kişinin tek rozeti "Kitap/diğer" ve `href` sabit `null`.
3. **LibraryView yazar kutusu → `#scholars?pid=`** — 17/17 manifestte pid var.
4. **Alam/Dia/Ei1 kartlarına "Havuzda gör"** — dönüş bağı hiçbir kartta yok.
5. **Kimlik tekilliği** — Ali'nin dup-merge oturumuna bağlı; "22.824" bir kişi
   sayısı değil kayıt sayısı (denetim tekil tavanı ≤20.956 ölçtü).
