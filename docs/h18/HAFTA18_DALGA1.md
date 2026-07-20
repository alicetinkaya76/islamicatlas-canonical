# Hafta 18 — Dalga 1: Tam-PID Çekirdek, Kabın İspatı (2026-07-19)

## Yapılanlar

**S1 — Kitap Kabı üreticisi** (`pipelines/frontend/build_containers.py`):
5 tam-pid kaynak için `web/public/books/<key>/manifest.json` (künye +
sayılmış record_count + entity dağılımı + yetenekler + pid kapsaması) +
`pid_map.json` (yerel id → iac pid, lookup.sqlite source_curie'den) +
`books/index.json`. DÜRÜST KAPSAMLAR: yaqut 12.954/12.954 (%100),
khitat 801/801, science 406/406 (182 kişi + 224 eser), muqaddasi
2.049/2.070 (%98,99 — 21 iklimin frontend id'si yok, coverage_note),
battles **50/100** (mağazada yalnız battle:1..50; gerçek boşluk).
YENİ DUBLET KEŞFİ: Ahsen work-00000154 ↔ work-00001533 (Mucem
00000111↔00000407'ye ek; dup-merge oturumu listesine).

**S2 — yer→kitap köprüsü**: `build_place_index.py` → `place_index.json`
(17 kitap, 4.566 tekil pid, 11.487 yer×kitap çifti, names 4.595) +
`placeBooks.js` + şehir popup'ında "📚 Bu yeri kitaplarda oku" bloğu
(bindPopup İÇERİK FONKSİYONU — tembel indeks sonrası her açılışta).
Kanıt: بغداد → Târîhu Bağdâd (2.789) / Kâmil (1.484) / İbn Asâkir (888);
القاهرة → Sülûk (2.296). Ders: 1.6MB indeks tarayıcıda BAYATLADI →
fetch cache:'no-cache'.

**S3 — Kütüphane 📊 İstatistik** (`1d924fb`): kitap başına sayı kutuları
+ LAYER_COLORS tür dağılımı + en-çok-anılan-20 bar listesi; tamamı
istemcide mevcut veriden.

**S4 — Arama 5 kaynağı buluyor**: SearchBar indeksi 16.006 → **31.992**
kayıt (yaqut 12.954 + muqaddasi 2.049 + khitat 801 + science 182;
battles zaten DB'deydi). Veriler İLK ODAKTA yüklenir (sayfa yükü
şişmez); 'Kaynaklar' çipi 4 tipin şemsiyesi; sonuç tıklaması S2 derin-
link sözleşmeleriyle kayda gider (alam→#alam?id, yaqut→#yaqut?search
oto-seçim; kanıt: "Hankam" → Yâkût görünümü tek girişle açıldı).

## KARAR H18-1: Çıkarım korumalarının veri-kalibrasyonu (3 değişiklik)

Canlı keşif: **بغداد hiçbir kitap haritasında yoktu.** Kökler ve onarımlar
(hepsi ölçümle, `extract_book_mentions.py`):

1. **Dup-küme kuralı** (H14 build_stop_lexicon deseninin genellemesi):
   tekil-pid şartı, mağaza mükerrerleri yüzünden en ünlü şehirleri
   düşürüyordu (بغداد 2 kayıt ~5km). Artık <50km kümelenen çok-pid adlar
   en belirgin (en çok curie'li) kayda bağlanır; dağınık adaşlar yine
   dışarıda. 439 ad çözüldü.
2. **Tip-ötesi koruma frekans-eşikli**: "herhangi bir kişi etiketinde
   token" kuralı بغداد'ı (kişi etiketlerinde 2 kez) عمرو'yla (313) aynı
   kefeye koyuyordu. Ölçüm: kişi adları 173-800, şehirler 0-9 → eşik 25.
3. **ALLOW_SHORT = {مكة}**: 3-harf koruması kalır (1.218 kısa adın çoğu
   اذن/ابا sınıfı homograf); yalnız مكة editoryal istisna (stoplist'in
   aynası — elle, gerekçeli).

+ **Stoplist 4. ve 4b turu** (döküm kanıtlı): دينار/سنين/معروف/الزهري/
سهيل/مناف/لبني/البربر/البحيرة/العزي/مناة/اراك/عبلة/دودان/زناتة/يكسوم +
خارجة/حاطب/عوانة/رباح. 5. tur adayları (marjinal, bekliyor): حمير, مكحول.

SONUÇ: 17 kitabın TÜM top-4'leri artık gerçek coğrafya — Meğâzî/Sîre/
Bekrî top'u مكة; Tarîhu Bağdâd/Kâmil/Ya'kûbî top'u بغداد; Sülûk top'u
القاهرة; İstahrî/İbn Havkal top'u شيراز/كرمان. Anılma çıkarımı ilk kez
17 kitabın 17'sinde (parti-2'nin 7 kitabı mentions'sız kalmıştı — S2
ajanının keşfi). Bilinen dürüst sınır: دمشق silik-tekil kayıt olduğundan
df-kuralına takılıyor (dup-merge oturumu çözecek; İbn Asâkir'in kendi
şehri top listesinde الشآم üzerinden görünüyor).

## Kapı

`make test` 160 passed. Commit'ler: a58ac46 (kaplar, ajan) + 1d924fb
(S3) + bu kapanış. Sıradaki: Dalga 2 (%80+ beşlisi + dublet temizliği)
— dup-merge tarihçi oturumu ÖNCESİNDE Mucem/Ahsen/Seyahatnâme work
dubletleri ve Mekke×8/Bağdat×2 yer kümeleri artık somut listede.
