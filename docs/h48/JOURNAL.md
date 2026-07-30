# H48 — Küme yargısı tamamlandı: 87 yanlış birleşme önlendi

**Tarih:** 2026-07-30
**Durum:** kapandı

H47'de kurulan küme katmanının yargısı tamamlandı. İkinci tur: **545 küme**
(olası katmanın **tamamı** + kesin katmanda 90'lık doğrulama örneklemi), 32 ajan,
aynı iki mercek (prosopografi + çürütme).

## Birleşik kalibrasyon (664 karar)

| güven | n | aynı kişi | **ayrı kişi** | belirsiz |
|---|---|---|---|---|
| **kesin** | 150 | 147 (%98) | **0 (%0)** | 3 |
| olası | 484 | 318 (%65) | **72 (%14)** | 94 |
| zayıf | 30 | 3 (%10) | **15 (%50)** | 12 |

**"Kesin" ölçütü iki bağımsız turda, 150 kümede toplam SIFIR yanlış verdi.**
Ölçüt (ölüm yılı birebir + kaynaklar ayrık) sağlam. Buna karşılık "olası"
katmanda %14, "zayıf" katmanda %50 yanlış — ikisi de arayüz kararlarını
doğruladı.

Toplam **87 küme** yargıyla çıkarıldı; arayüzde gösterilen **1.271**.

## Yakalanan gerçek prosopografi hataları

Otomatik kümelemenin asla yakalayamayacağı türden. Örnekler:

- **Hz. Ali kümesine kızı karışmış:** `ÜMMÜ KÜLSÛM bint ALİ` — ad benzerliği
  yalnız `bint Alî` nesep ekinden geliyordu.
- **Halife el-Mehdî ↔ oğlu el-Hâdî** (ö. 785 / 786): lakaplar birbirine
  karışmış, doğum yerleri Îzec ≠ Rey.
- **Filozof el-Kindî ↔ muhaddis Ebû Saîd el-Eşec el-Kindî** (ö. 873/871):
  ortak olan yalnız **kabile nisbesi**; biri matematik-felsefe, öbürü hadis.
- **Halife Hişâm ↔ oğlu Muhammed b. Hişâm** (ö. 743/744).
- **Sâlim mevlâ Ebî Huzeyfe ↔ efendisi Ebû Huzeyfe b. Utbe:** âzatlı ile
  efendisi aynı kümeye düşmüş.
- **"b. Artuk" (Artuklu) ↔ "el-Kutbî" (Ahlatşahlar):** ayrı hanedanlar.
- **"Mehmed III" (Osmanlı regnal adı) ↔ "Muharrem b. Muhammed".**

Bunların hepsi ölüm yılı aynı ya da ±2 olan, adı benzeyen **ayrı kişilerdi**.
Otomatik birleştirilseydi tarihsel olarak yanlış kayıtlar üretilecekti.

## Çelişki kuralı işledi

İki mercek 54 kümede çelişti; hepsi **"belirsiz"e** düştü — hiçbirinde kesinlik
iddia edilmedi. `apply_cluster_judgments.py` ayrıca turlar arası çelişkiyi de
aynı şekilde ele alıyor: önceki tur "evet", yeni tur "hayır" derse karar
sessizce değişmez, "belirsiz"e iner ve raporlanır.

## Doğrulama
- `make test` → 200 geçti, 2 atlandı, 3 xfail.
- Guard'lar yeşil; kalibrasyon testi (`kesin` katmanda `hayir == 0`) hâlâ
  geçiyor — yani eşik ölçümle destekleniyor.

## Kalan
- **Yargılanmamış:** 795 kesin küme (örneklemle %98 doğrulandı) + 175 zayıf
  (zaten gizli). Kesin katmanı tam taramak düşük getirili: iki turda 0 yanlış.
- **Gerçek birleştirme** hâlâ Ali'nin oturumu: hangi pid "kazanan" olacak,
  hangi alanlar taşınacak, kaybeden pid nasıl yumuşak-silinecek. Elde artık 664
  gerekçeli karar ve iki turlu kalibrasyon var.
