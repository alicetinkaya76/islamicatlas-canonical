# Hafta 17 — Birleşme Yol Haritası + Dalga 0 (2026-07-19)

## Bağlam ve onay

Kullanıcı #yaqut (v1 temsili) ile #library (v2) farkını sordu; iki analiz
turu koşuldu (10 ajan: 4 okuyucu + 3 tasarım + 3 jüri; sonra 5 ajan:
16-kaynak envanteri + dalga sentezi). Sonuç yol haritası teknik olmayan
dille sunuldu ve **onaylandı** ("Başla"):

- **Mimari yön (jüri kararı):** "Evrimsel iskelet + veri-önce aşılar" —
  sevilen v1 UI'lara dokunulmaz (yalnız import kaynakları `bookkit`e
  döner, ekran-karşılaştırma kapısıyla); veri kademeli olarak pid'li
  ortak **Kitap Kabı** şemasına bağlanır.
- **Kitap Kabı:** 3 zorunlu bölme (künye / içindekiler / bağlantılar) +
  opsiyonel yetenek bölmeleri (harita, küre, tam metin, rota, istatistik,
  analitik…). Raf manifest'e bakar; yeni OpenITI kitabı kaba girip rafta
  kendiliğinden belirir.
- **Dalga planı:** D0 temel + onarım → D1 tam-pid beşlisi (yaqut,
  muqaddasi, khitat, battles, science) → D2 %80+ beşlisi + dublet
  temizliği (alam, dia, evliya, salibiyyat, cityatlas) → D3 eşleştirme
  (darpislam, lestrange, Ulema Havuzu) → D4 özel modeller (rihla durak
  şablonu, ei1 triyaj). Yol haritası artifact'ı (kalıcı):
  https://claude.ai/code/artifact/78db1a7f-9565-4fa1-a808-eb6bf1572e02

## KARAR H17-1 (sahip): Ulema Havuzu

"450 Âlim" statik set olarak entegre EDİLMEZ. Âlimler bölümü, merkezî
defterdeki BÜTÜN kişi kayıtlarının (A'lâm 13.940 + DİA 8.528 + EI-1
sağlam alt kümesi + Bilim Atlası + kitap çıkarımları) süzüldüğü dinamik
agrega endeks olur; her yeni kitabın âlimleri havuza kendiliğinden akar.
450'lik set isnad katmanıyla "tohum"dur (D3'te, alam/dia çakışma
denetiminden sonra).

## KARAR H17-2: bookkit anayasası

Bir parça ancak İKİNCİ tüketici de isteyince `shared/bookkit`e terfi
eder; ilk kullanımda kitaba-özel dosyasında doğar. Eski hash'ler
(#yaqut, #library?book=&sec=&p=) kalıcı sözleşmedir, asla kırılmaz.

## Dalga 0 icrası (5 aşama, 4 commit, hepsi push'lu)

| Aşama | Commit | İçerik |
|---|---|---|
| S1 bookkit | `1a94260` | `web/src/components/shared/bookkit/` (geoPalette 21-tip TEK kaynak + türev sayısal palet, jenerik VirtualList, normalize, ErrorBoundary). Yâkût'un 5 bileşeni bağlandı; 4 palet kopyası + gömülü liste + normalize + EB kopyası silindi. Tarayıcı: filtre/çip/kart birebir; "Hankam"→"Hankâm" normalize canlı. |
| S5 Yer Grafı | `1a94260` | `pipelines/frontend/build_yaqut_graph.py` → 606 düğüm / 1.338 kenar (crossref ortak-kişi kenarları; deterministik, bayt-bayt tekrarlanabilir). v1'den beri BOŞ olan sekme ilk kez dolu. KRİTİK: bileşen dosyayı `/data/` altından değil KÖKTEN çekiyor (tek istisna) — iki eş kopya yazıldı. i18n açıklaması 3 dilde gerçek kaynağa düzeltildi ("parent_locations" iddiası kaldırıldı). |
| S2 rotalar | `b48fe61` | darpislam VALID_TABS'a; parseHash `#dia/<slug>` segmenti; AlamView `initialId` (#alam?id= 3 çağıran vardı, okuyan yoktu); navigateToView entityId; salibiyyat `#tab=` biçimi standarda. +2 miras çökme onarımı (aşağıda). |
| S3 rozetler | `3b15d43` | `build_source_counts.py` → `source_counts.json` → `sourceCounts.js`; App(15) + Dashboard(23) + Landing(8) bağlandı. Düzelen yalanlar: cityatlas 219/'1,020'→**1.384**, science 186→**182**, darpislam 3.458→**3.381** (haritada gösterilen), yaqut '13K'→12.954. |
| S4 Kütüphane | `43157de` | İki bölümlü raf (Kürasyonlu Atlas Görünümleri şeridi: 7 kart, yetenek ikonları, gerçek rozetler + Külliyat 17); "parti undefined"; popup duplike blok; openBook hata mesajı; **&p= çapası ilk kez çalışıyor**. |

Kapı: `make test` **160 passed** (2 skip, 3 xfail).

## Onarılan miras çökmeleri (derin-link testinin ortaya çıkardığı)

1. **AlamView hook-sıra çökmesi:** yükleme-koruması hook'ların ORTASINDA
   idi; hover-preload'suz soğuk açılış (doğrudan URL) "Rendered more
   hooks" ile çöküyordu. Koruma tüm hook'ların altına taşındı (DiaView'un
   "ALL hooks above conditional return" kuralı — YaqutView zaten uyumlu).
2. **AlamMap NaN LatLng:** gizli (0-boyut) konteynerde flyTo animasyonu
   NaN üretiyordu (mobil kart açıkken derin-link seçimi). Görünmez
   haritada animasyonsuz setView.

## Üç yeni kalıcı ders

1. **rAF gömülü/arka-plan sekmede kısılır** — kaydırma/zamanlama işleri
   için setTimeout zinciri kullan (çapa kaydırması canlıda kanıtlandı).
2. **StrictMode'un ikinci effect koşusu yeniden-fetch + scrollTo(0,0)
   yarışı doğurur** — tek-seferlik "tüket" yerine "kullanıcı gezinince
   düşür" deseni.
3. **macOS TCC kesintisi oturum ortasında gelebilir** (Masaüstü/Belgeler
   izni): tüm dosya işlemleri EPERM olur, sandbox'sız da. Belirti: git
   "Unable to read cwd". Çözüm kullanıcıda (Tam Disk Erişimi). Push'lu
   commit'ler sayesinde risk sıfırdı — sık commit+push disiplini kendini
   ödedi.

## Bilinen, dokunulmayan miras sorunları (Dalga kapsamları)

- Pano üst sayaçları test viewport'unda 0 (animasyon tetikleyicisi;
  stash A/B ile Dalga-0 ÖNCESİ de aynı — D1'de bakılacak).
- Landing fallback'leri artık 0 (DB importu varken ölü kod).
- Diğer 5 görünümün ErrorBoundary kopyaları kendi dalgalarında bookkit'e
  göçer (S1'de yalnız Yâkût — piksel kapısı tek görünümde tutuldu).
- Vite dev sunucusu oturumda 3 kez öldü (harici); `preview_start` ile
  yeniden kalkıyor, veri kaybı yok.

## Sıradaki: Dalga 1

Tam-pid beşlisi kaba girer: books/index + manifest şeması, yaqut
pid-map'in frontend'e yansıtılması (mağazada 1:1 hazır), Kütüphane'ye
İstatistik/Küre modları (bookkit), arama indeksine 5 kaynak, yer
popup'ına "bu yeri kitaplarda oku" köprüsü (place_index ters indeksi).
