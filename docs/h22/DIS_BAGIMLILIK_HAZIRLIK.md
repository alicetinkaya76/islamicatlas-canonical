# H22 kova-C — Dış bağımlılıklı kalemler: hazırlık paketleri

Bu iki kalem **karar** değil **eylem** gerektiriyor ve ikisi de benim
yetkim dışında: biri kurumla yazışma, diğeri hesap/alan adı sahipliği.
Kararı ben verdim (aşağıda), uygulaması Ali'de. Hazırlığı yapıldı ki
Ali'nin işi imza/tıklama seviyesine insin.

---

## C1 — İSAM/TDV yayın izni (ADR-014 §Koşul)

### KARARIM
**Yayın adımları İSAM belgesi gelene kadar BLOKE kalır.** Zenodo DOI,
w3id kalıcı adres, kamuya açık veri indirme — hiçbiri başlamaz. Gerekçe:
ADR-014 bu izni yayının ön şartı olarak yazmış; belge olmadan atılan her
adım geri alınamaz bir yayın eylemi olur (DOI iptal edilemez, arşiv
kopyaları dolaşıma girer).

**Ama hazırlık işleri İSAM'sız yürür** ve yürütüldü: ontoloji taslağı,
sürüm etiketi, veri paketleme script'leri, dokümantasyon. İzin geldiği
gün yayın tek koşu olur.

### ETKİLENEN VERİ ENVANTERİ (ölçüldü)
| Katman | Kayıt | İSAM'a bağımlı mı |
|---|---|---|
| DİA maddeleri (dia_lite) | 8.528 | **EVET** — metin TDV telifli |
| DİA tam-metin parçaları (dia_chunks) | 19.742 | **EVET** — en hassas |
| dia: curie'li canonical kişi kayıtları | 7.383 | KISMEN — pid/ad/tarih bizim, açıklama metni TDV'den |
| dia_relations / dia_travel kenarları | 9.706 | HAYIR — türetilmiş olgu (kim kimin hocası) telif konusu değil |
| Diğer her şey (Yâkût, A'lâm, EI-1, OpenITI, kitap katmanları) | ~59.000 | HAYIR |

**Not:** EI-1 (1913-36) ve OpenITI kamu malı; Yâkût/A'lâm gibi klasik
metinler zaten kamu malı. Yani İSAM izni gelmezse bile **mağazanın
%87'si yayınlanabilir** — DİA metinleri çıkarılıp yalnız olgusal
katmanlar (pid, ad, tarih, ilişki) bırakılarak. Bu bir B planıdır ve
teknik olarak uygulanabilir (dia_chunks + ds/açıklama alanları filtresi).

### İSAM'A GİDECEK TALEP — hazır taslak
Konu: TDV İslâm Ansiklopedisi maddelerinden türetilmiş yapılandırılmış
verinin akademik atlas projesinde kullanımı ve yayını hk.

İçerik iskeleti (Ali doldurup gönderecek):
1. Proje kimliği: islamicatlas.org, Selçuk Üniversitesi, yürütücüler
   Dr. Hüseyin Gökalp – Dr. Ali Çetinkaya (ORCID 0000-0002-7747-6854)
2. Kullanılan veri: 8.528 madde başlığı + biyografik olgular (doğum/ölüm
   tarihi, yer, ilim dalı, hoca-talebe ilişkisi) + madde bağlantısı
   (islamansiklopedisi.org.tr'ye geri link)
3. **Kullanılmayacağı taahhüdü**: madde tam metni kamuya açık arayüzde
   YAYINLANMAYACAK (şu an yalnız yerel arama motorunda; izin gelmezse
   tamamen çıkarılacak)
4. Atıf biçimi: her kayıtta kaynak = "TDV İslâm Ansiklopedisi", madde
   URL'si, erişim tarihi
5. Lisans talebi: olgusal veri için CC BY-SA 4.0 uyumlu kullanım izni
6. Karşılık: TDV'ye geri bağlantı, proje künyesinde kurumsal anma

---

## C2 — Hosting / DNS

### KARARIM
**v1 yayında kalır, v2'ye geçiş İSAM belgesinden SONRA.** İki gerekçe:
(1) yayın izni olmadan v2'nin DİA katmanı kamuya açılamaz; (2) v1 şu an
çalışıyor ve ziyaretçisi var — çalışan bir siteyi izin belirsizken
değiştirmek gereksiz risk.

### ÖNERİLEN MİMARİ (hazır, uygulanmayı bekliyor)
| Bileşen | Öneri | Gerekçe |
|---|---|---|
| Statik site | mevcut Vercel hesabı (v1 zaten orada) | ek maliyet yok, alan adı bağlı |
| Arama | Typesense Cloud **veya** self-host (Hetzner/DO ~5-10 €/ay) | mevcut docker imajı birebir taşınır; şema `search/facets.yaml`'da |
| Kalıcı adres | w3id.org/islamicatlas/ (GitHub PR ile ücretsiz) | şema açıklamalarında ZATEN bu adres yazılı |
| Veri arşivi | Zenodo (DOI, sürümlü) | akademik atıf için şart |

### UYGULAMA RUNBOOK (Ali tıklayacak, ~2 saat)
1. Typesense servisi aç → admin + search-only anahtar üret
2. `web/config.js`'e **yalnız search-only** anahtarı koy (admin anahtarı
   asla tarayıcıya gitmez — mevcut kural)
3. `make typesense-upsert` (67.833 kayıt, ~2 dk)
4. `npm --prefix web run build` → statik çıktı
5. Vercel'e deploy, önce **preview URL** ile doğrula
6. w3id PR'ı aç (yönlendirme kuralları hazır)
7. DNS'i ancak 1-6 yeşilse çevir

### ŞU AN HAZIR OLANLAR
- Typesense şeması + upsert script'i (H11 S7'de test edildi, fail=0)
- Statik build zinciri (Vite; H12'den beri çalışıyor)
- Search-only anahtar ayrımı (config.js gitignored)
- 67.833 kayıt projeksiyon testi geçiyor

### EKSİK OLAN TEK ŞEY
İSAM belgesi (C1) + Ali'nin hesap erişimi. Teknik hiçbir engel yok.
