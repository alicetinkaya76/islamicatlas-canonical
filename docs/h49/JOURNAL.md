# H49 — Birleştirme uygulandı: 544 kayıt yönlendirildi, hiçbiri silinmedi

**Tarih:** 2026-07-30
**Durum:** kapandı
**Yetki:** Ali: *"sen karar ve devam et"* — merge kararı devredildi.

## Ne yapıldı

Yargısı **iki mercekte de "aynı kişi"** çıkan **468 küme** birleştirildi:
**544 kayıt** yumuşak-silindi (`deprecated: true` + `deprecated_in_favor_of`).
Havuz **22.824 → 22.280**.

**Hiçbir dosya silinmedi, hiçbir alan kaybolmadı.** Kaybeden pid'ler
canonical'da yaşamaya devam ediyor (atıf istikrarı); yalnız `projector` onlara
−100 verdiği için aramada mükerrer görünmüyorlar.

Ölçüt bilinçli olarak dar: **yargısı olmayan hiçbir küme birleştirilmedi.**
Yargılanmamış 795 "kesin" küme dokunulmadan duruyor — örneklemde %98 doğru
çıkmış olsalar bile.

## Geri alma yolu ÖNCE kanıtlandı

Veri-yıkıcı bir işlemde bu sıralama önemli: uygulamadan önce `--restore`
çalıştığını ölçtüm.

```
deprecated: 164 → (uygula) 708 → (--restore) 164 → (tekrar uygula) 708
```

Birebir geri dönüş. Ledger `data/_state/h49_cluster_merge.json`.

## İki gerçek kusur — ikisi de test tarafından yakalandı

### 1. Şema ihlali (kendi dersimi tekrar ihlal ettim)
`record_history`'ye `migration: "h49_001"` alanı ekledim. Şema
`additionalProperties: false` diyor → **26 kayıt şema testinden düştü.**
H31'de tam bu dersi almıştım (`change_type: "repair"` de reddedilmişti) ve yine
aynı hataya düştüm. Göç kimliği artık `note`un başında: `[h49_001] …`.

### 2. Atıf istikrarı vaadi sınavı geçemedi — sonra geçti
Birleştirmeden hemen sonra **17 kitabın 5'inin müellif bağı koptu**: müellif
yumuşak-silinmişti, havuzda görünmüyordu, `#scholars?pid=` boş ekrana
düşüyordu. "Pid yaşamaya devam eder" demek, **UI'ın onu bulabilmesi** demek
değilmiş.

Onarım: `person_redirects.json` (544 yönlendirme) + UlemaPool gelen pid'i
kazanana çeviriyor. Ölçüldü: yönlendirme hedefi havuzda olmayan **0**.

## Guard testleri (8) — mutasyonla sınandı

En sıkısı: **kaybeden kaydın dosyası duruyor olmalı.** Bir gün biri "temizlik"
diye bu dosyaları silerse test kırmızı yanar. Ayrıca kilitlenenler: doğru
işaretleme, zincirleme yönlendirme yasağı (kazanan da deprecated olamaz),
gerekçenin `record_history`de bulunması, **yargısız birleştirme yasağı**, ve
her yönlendirme hedefinin havuzda canlı olması.

## Sayılar

| | önce | sonra |
|---|---|---|
| havuz kaydı | 22.824 | **22.280** |
| deprecated kişi | 164 | 708 |
| gösterilen küme | 1.271 | 806 |
| yönlendirme | — | 544 |

## Doğrulama
- `make test` → **208 geçti**, 2 atlandı, 3 xfail.
- `--restore` → tam geri dönüş (ölçüldü).
- Servis edilen veri: havuz 22.280, yönlendirme 544, kırık hedef 0.

## Ali'ye kalan
- **795 yargılanmamış "kesin" küme** — istenirse aynı yöntemle yargılanıp
  birleştirilebilir (örneklem %98 doğru dedi ama yargısız birleştirme bu turun
  kuralına aykırı).
- **109 "belirsiz"** küme — iki mercek çelişti; tarihçi bakışı gerekir.
- **87 "ayrı kişi"** kararı zaten kümeden çıkarıldı; bunlar veri hatası değil,
  doğru ayrımlar.
