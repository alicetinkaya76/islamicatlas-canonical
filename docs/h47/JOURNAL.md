# H47 — Kimlik parçalanması görünür kılındı (birleştirilmeden)

**Tarih:** 2026-07-30
**Durum:** kapandı
**Yetki:** Ali: *"devam sen bunu yapabilirsin"* — H44 denetiminin son maddesi.

## İlke: birleştirmeden görünür kılmak

Denetim ölçmüştü: **"22.824" bir kişi sayısı değil KAYIT sayısıdır.** Aynı kişi
2-3 ayrı pid'e dağılmış ve bedeli sayı değil **zenginlik parçalanması** —
biyografi bir kayıtta, eserleri başka kayıtta, ağ düğümü üçüncüsünde. Kullanıcı
hiçbir ekranda "bütün Gazzâlî"yi göremiyordu.

Bu turda **hiçbir pid silinmedi, hiçbir kayıt birleştirilmedi.** Birleştirme
geri alınması zor, veri-yıkıcı bir işlemdir ve iki farklı tarihsel şahsı tek
kayda indirme riski taşır. Yapılan: kanıtı katmanlayıp **küme** önermek ve
parçalanmayı arayüzde göstermek. Merge kararı tarihçinin (ADR-008 Tier-3).

## Kanıt katmanları

Mevcut aday listesi (rapidfuzz ≥0.95 ad benzerliği, 3.199 çift) üzerine iki
katman daha kondu:

| güven | ölçüt | kenar |
|---|---|---|
| **kesin** | ölüm yılı **birebir** + kaynaklar **ayrık** | 1.248 |
| olası | biri sağlanmıyor | 674 |
| zayıf | ±2 yıl ve kaynaklar örtüşüyor | 246 |
| (elendi) | ölüm yılı **farklı** → küme kurulmaz | 862 |

Ad benzerliği tek başına yetmez: `Abū Bakr`, `'Alī`, `al-Mansūr` gibi adlarda
skor 1.0 hiçbir şey söylemez. Kaynak ayrıklığı ise gerçek bir sinyal —
Bosworth/450-tohum ile el-Aʿlâm/DİA **ayrı mint edilmiş**, aynı kişi iki kez
kaydedilmiş.

Union-Find ile transitif kapanma → **1.635 küme, 3.574 kayıt.**

## Yargı turu ve kalibrasyon

120 kümelik örneklem (seed=42; 60 kesin + 30 olası + 30 zayıf) iki bağımsız
mercekle yargılandı: **prosopografi** (isim + nesep + künye + nisbe çözümlemesi)
ve **çürütme** (ayrı kişi olduklarını göstermeye çalışan). Mutabakat yoksa
"belirsiz".

| girdi güveni | aynı kişi | **ayrı kişi** | belirsiz |
|---|---|---|---|
| kesin (60) | 58 | **0** | 2 |
| olası (30) | 16 | 7 | 7 |
| zayıf (30) | 3 | **15** | 12 |

**Ölçütüm kesin katmanda %97 isabetli ve sıfır yanlış verdi.** Ama zayıf
katmanın **yarısı yanlıştı** — bu, katmanın kendisinin bir sonucu:

> `b. Artuk` (Artuklu, Hısnıkeyfâ) ↔ `el-Kutbî` (Ahlatşahlar) — aynı yıl ölmüş,
> adı benzeyen, **ayrı hanedanlardan iki kişi**.

## Bunun iki sonucu, ikisi de uygulandı

1. **Zayıf katman arayüzde gösterilmiyor** (`goster: false`). Yarısı yanlış olan
   bir uyarı, kullanıcıyı yanlış birleştirmeye teşvik eder. Kümeler dosyada
   kalıyor — aday listesi olarak değerli.
2. **Yargı "ayrı kişi" demiş 22 küme çıkarıldı.** Arayüzde gösterilen: **1.401**.

## Arayüz

Havuz panelinde kişinin adının altında:

> 👤 **Aynı kişinin başka kaydı (1) · ✓ incelendi: aynı kişi**
> ölüm yılı birebir + kaynaklar ayrık
> → Mehtedî el-Abbâsî · a
> *Kayıtlar BİRLEŞTİRİLMEDİ — birleştirme kararı tarihçinindir.*

Yargılanmış kümeler yeşil ve "✓ incelendi", yargılanmamışlar mor ve "güçlü
kanıt / olası". Öbür kayda tek tıkla geçiliyor; kullanıcı artık her iki kaydı da
görüyor ve hangisinde ne olduğunu anlıyor.

## Guard testleri (6) — mutasyonla sınandı

En sıkısı: **hiçbir küme üyesi havuzdan kaybolmamalı** — yani bir gün biri
gerçekten birleştirme yaparsa test kırmızı yanar. Ayrıca zayıf katmanın
sızmaması, "ayrı kişi" denen kümenin dosyada kalmaması, ölüm yılı farklı küme
kurulmaması ve **kalibrasyon ölçümünün kaydının kaybolmaması** kilitlendi.

## Doğrulama
- `make test` → **200 geçti**, 2 atlandı, 3 xfail.
- Tarayıcı: al-Muhtadī ↔ Mehtedî el-Abbâsî kümesi yeşil "✓ incelendi" ile
  görünüyor; öbür kayda bağ çalışıyor; konsol temiz.

## Ali'ye kalan
Gerçek **birleştirme** hâlâ tarihçi kararı. Artık elde şunlar var: 945 kesin +
478 olası küme, 120'sinin yargısı gerekçeleriyle kayıtlı
(`data/_state/person_cluster_judgments.json`), ve kalibrasyon eğrisi. Kalan
1.515 kümeyi aynı yöntemle yargılatmak mümkün — ama **uygulama** (kayıtları
gerçekten birleştirmek, hangisinin "kazanan" pid olacağına karar vermek)
sizin oturumunuz.
