# Hafta 23 — Veri akışı birleşmesi: v1 görünümleri canonical'a bağlandı

## Sorun (kullanıcı sordu, ölçüldü)

v1–v2 birleşmesi kabuk + köprü düzeyinde tamamdı ama **veri akışı ikiliydi**:
yeni görünümler (Kütüphane, Havuz, Seyahatnâmeler) merkezî defterden
besleniyordu, ESKİ görünümler (Yâkût, A'lâm, DİA, EI-1, Makdisî, Evliyâ)
hâlâ kendi v1 dosyalarını okuyordu. Sonuç: bir kaydı düzeltince/emekli
edince ekranda görünmüyordu (27 hayalet, 372 dublet deftere işlendi ama
v1 dosyaları eski hâldeydi). Yayına çıkmadan kapatılması gereken açık.

## Çözüm: iki-katmanlı görünüm üreticisi

`build_view_data.py` (Makefile: `make view-data`): canonical mağazadan
v1 ŞEMASINDA görünüm dosyası üretir. UI kodu DEĞİŞMEZ — yalnız fetch yolu
`/data` → `/view-data`, render birebir aynı (piksel parite).

**İki katman** (canonical v1'in kürasyonlu zenginliğini taşımadığı için):
- OTORİTE (canonical): liste, ad, koordinat, DEPRECATED durumu, pid köprüsü
- ZENGİNLİK (v1 lite): geo tip, etiket, dönem, ülke, DİA slug — curie
  üzerinden korunur; v1 kürasyonu kaybolmaz

## Görünüm başına sonuç

| Görünüm | Tür | v1 | canonical-aktif | emekli-işlem | eşleşmeyen |
|---|---|---|---|---|---|
| Yâkût | katalog place | 12.954 | 12.935 | 19 **düştü** | 0 |
| A'lâm | katalog person | 13.940 | 12.476 | 96 **düştü** | 1.368 |
| DİA | katalog person | 8.528 | 7.346 | 37 **düştü** | 1.145 |
| EI-1 | katalog person | 7.568 | 1.144 | 30 **düştü** | 6.394 |
| Makdisî | atlas place | 2.049 | 1.835 | 214 **listede kaldı** | 0 |
| Evliyâ | atlas place+inst | 5.444 | 4.806 | 1 **listede kaldı** | 637 |

Emekli sayıları ekrana yansıyor: DİA 8.528→8.491, EI-1 7.568→7.538
(27 hayalet OTOMATİK düştü — H21 triyajının meyvesi).

## İlk koşunun 3 sorunu → 3 karar (ölçümle)

İlk (kaba) koşu üç gerçek sorun çıkardı; hepsi kanıtla çözüldü:

### KARAR H23-1: Açıklama/özet canonical'dan lite'a TAŞINMAZ
İki sebep birden: **(a) Boyut** — canonical `description` tam makale
(DİA'da ort. 5.026 karakter), v1 teaser'ı 44 karakter; taşıyınca
`dia_lite` 3 → **49 MB** (16×), `alam_lite` 5 → 14 MB. "lite" dosya amacı
hafif liste; canlı 49 MB fetch performansı öldürür. **(b) İSAM** — tam
DİA makale metnini lite'a koymak, izne bağlı metni yaymaktır ve B planını
(DİA metnini çıkar, olgusal katman bırak) BOZAR. Düzeltme sonrası dia
49→3 MB, alam 14→5 MB. Teaser v1'de kalır (zenginlik).

### KARAR H23-2: Kaynak-sadık atlas katmanlarında emekli DÜŞÜRÜLMEZ
Makdisî ve Evliyâ'nın `places[]` listesi "o kitabın andığı yerler" =
tarihsel metin. Canonical'ın "bu iki kayıt aynı yer" merge kararı bu
listeyi DEĞİŞTİRMEMELİ (ayrıca `routes[]` düşen yerlere referans veriyor,
sarkan uç olurdu). Emekli kayıt LİSTEDE KALIR, `merged_into` ile
işaretlenir; yalnız kimlik+koordinat tazelenir. Makdisî'nin %10 kaybı
(214 yer) böyle önlendi. **Ayrım:** katalog görünümleri (Yâkût/A'lâm/DİA)
kişi/yer kataloğudur — orada mükerrer katalog kaydı gerçekten fazlalık,
emekli DÜŞER.

### KARAR H23-3: EI-1'de isim tazelenmez
EI-1↔person eşleşmesi %33,7 yanlış-pozitif (H10 QID audit). Ajan "eşleşen
1.144 kaydın 743'ünde isim değişti, gözden geçir" uyarısı verdi → hiç
tazeleme yapmadım; yalnız emekli-düşürme (30) + pid köprüsü. v1 başlığı
kalır.

## Mimari kural (korundu)

`web/public/data` bir SYMLINK'tir, v1 projesinin dizinine işaret eder ve
v1 CANLI YAYINDADIR. Oraya HİÇ yazılmadı (doğrulandı). Görünüm dosyaları
`web/public/view-data/` (symlink DIŞI, gerçek dizin, gitignored türev —
`make view-data` ile yeniden üretilir). v1 zenginlik kaynağı symlink'te
dokunulmadan durur.

## Kapı + kalan

Determinizm bayt-bayt; esbuild 6/6 OK; `make test` 160 passed.
Commit'ler: `bc73840` (Yâkût pilotu), `5cc2e4a` (5 görünüm + 3 karar).

**Veri akışı birleşmesi BİTTİ** — tüm eski görünümler artık canonical
otorite. Bir düzeltme yapılınca `make view-data` ile ekrana yansır.
Kalan: yayın paketi (İSAM'a bağlı), parti-3 kitapları, referans göçü
(emekli kayıtlara işaret eden alanlar — kırık bağ yok, dolaylı).
