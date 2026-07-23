# Hafta 24 — UI denetimi: canonical düzeltmelerinin ikincil tüketicilere sızdığı yerler

## Sorun (kullanıcı söyledi, ölçüldü)

Kullanıcı: *"bence arayüzü sen çok iyi bir şekilde test etmelisin sanki
problemler var"* (+ #scholars ağ ve #visits harita ekran görüntüleri).

Haklıydı. H23 görünüm verisini canonical'a bağladı ama düzeltmeler
görünümlerin **ikincil tüketicilerine** ulaşmamıştı. Mutlu-yol testi bunu
gizler; sistematik denetim 4 gerçek kritik + 1 sağlamlaştırma çıkardı.
Hepsi H22 (kuyruk eritme) / H23 (görünüm birleşmesi) düzeltmelerinin
yan tüketicilere yayılmamasından kaynaklanıyordu.

## Bulgular ve düzeltmeler (hepsi canlıda doğrulandı)

### 1. KRİTİK — Arama eski `/data`'dan besleniyordu (çift kök)
`SearchBar.jsx` `alam_lite`/`yaqut_lite`/`muqaddasi` dosyalarını hâlâ
`/data`'dan (emekli/dublet DÜŞMEMİŞ hâl) çekiyordu; görünümler ise
`/view-data`'dan. Sonuç: emekli edilmiş bir kaydı arayınca çıkıyor, ama
tıklayınca görünümde yoktu. → Arama da `/view-data`'ya alındı.
*(khitat/science henüz canonical'a bağlı değil → bilerek `/data`'da,
kod içi not düşüldü.)*

### 2. KRİTİK — Rozet sayıları görünümle çelişiyordu
`build_source_counts.py` katalog kaynaklarını `/data`'dan sayıyordu →
rozet "13.940" derken görünümde 12.476 kayıt vardı. → `prefer_view=True`
ile yaqut/alam/dia/ei1 artık `/view-data`'dan sayılıyor.
**Canlı doğrulama:** navigasyon rozetleri A'lâm **13.844**, DİA **8.491**,
EI-1 **7.538**, Büldân **12.935** — görünüm sayımıyla birebir.

### 3. KRİTİK — CityAtlas React "aynı key" uyarısı
`konya.json`'da `kp_beyşehi_r_gölü_2` id'si 3 kayıtta tekrar ediyor
(koordinatsız, farklı dönem). Kaynak v1 symlink'i → veriye dokunulamaz.
→ Liste key'i `${r.id}-${i}` ile indeksle benzersizleştirildi.
**Canlı doğrulama:** Konya sidebar render'ında React key uyarısı YOK.

### 4. KRİTİK — Âlim ağında hayalet-uçlu kenarlar
`scholar_links.js` 8 kenarı `db.json`'da olmayan âlim id'lerine (14/28/33)
bağlıyordu → ağda kopuk/asılı kenarlar. → Import-zamanı doğrulama filtresi:
her iki ucu geçerli olmayan kenar elenir, konsola bilgi basılır.
**Canlı doğrulama:** konsol *"8 hayalet-uçlu link elendi; 155 geçerli"*,
ağ tam **155 kenar** çiziyor (900 düğüm).

### 5. SAĞLAMLAŞTIRMA — Kütüphane bölüm-getirme koruması
`LibraryView.jsx` eksik `sec_NNNN.json` dosyasında sessizce boş kalıyordu.
→ `fetch` reddi yakalanır, kullanıcıya "bu bölüm yüklenemedi" notu gösterilir.

## Bilerek ERTELENEN (Faz-2, dürüstlük notu)

**Çapraz-referans parametre köprüleri** (Salibiyyât→#battles/#khitat highlight,
Le Strange→#map lat/lon): hedef görünümler `highlight`/`lat`/`lon` parametresini
UYGULAMIYOR. Ama sekme geçişi çalışıyor (zararsız degradasyon: doğru
veritabanına gidilir, yalnız vurgu uygulanmaz). Gerçek düzeltme canonical
event/institution pid ↔ v1 id eşlemesi gerektiriyor → Faz-2. Çökme yok.

## Yanlış-alarm listesi (regresyon değil, veri gerçeği)

- **ScholarNetwork seyrekliği:** 900 düğüm / 155 kenar — bu az bağ, veri
  gerçeği (isnad kenarları elle kürasyonlu, tam değil). Bug değil.
- **#visits'te çizgi yok:** Evliyâ kayıt sırası güzergâh DEĞİL
  (`sira_turu=dosya_sirasi`) → bilerek çizgi çizilmez.

## Gate
`make test` → **160 passed**, 2 skipped, 3 xfailed. 5 düzenlenen dosya
esbuild ile sözdizimi-temiz.

## Değişen dosyalar
- `web/src/components/shared/SearchBar.jsx` (→ view-data)
- `pipelines/frontend/build_source_counts.py` (prefer_view)
- `web/src/data/source_counts.json` (yeniden üretim çıktısı)
- `web/src/components/CityAtlas/CityAtlasSidebar.jsx` (key onarımı)
- `web/src/data/scholar_links.js` (hayalet-uç filtresi)
- `web/src/components/library/LibraryView.jsx` (bölüm-getirme koruması)
