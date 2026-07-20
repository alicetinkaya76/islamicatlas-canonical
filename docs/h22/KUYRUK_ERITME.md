# Hafta 22 — Kuyruk Eritme (kova A)

**Durum:** TASLAK — Claude başlattı (2026-07-20), Ali üzerine ekleyecek.
**Kapsam:** H19-H21'in "Ali kuyruğu"na bıraktığı kalemlerin kanıtla karara
bağlanması + inceleme yükünün eritilmesi.

Bu belge H22'de **verilmiş kararların** defteri. Her kalem: ne karar verildi,
hangi kanıtla, hangi commit'te. Sayılar commit gövdelerinden ve koddan alındı;
tahmin yok.

---

## Karar 1 — 27 EI-1 hayalet kaydı yumuşak-silindi

**Commit:** `140366f` (H22 kova-A #1)

H21 triyajının bulduğu 27 hayalet kişi kaydı — gerçek kişi değil, çıkarım
artığı: `Lxxxix` (Roma rakamı), `Zdpv` (dergi kısaltması),
`Ai-KArlSlVA KADJAR` (sayfa üstbilgisi) gibi.

**Karar: SİLME DEĞİL, yumuşak-silme.** `provenance.deprecated = true`.
- PID korunur → atıf istikrarı bozulmaz.
- Kayıt yerinde durur; search/projector `deprecated`'a **-100 skor cezası**
  verdiği için aramada dibe düşer.
- Geri alma: `--restore`; defter `data/_state/ei1_ghost_deprecated.json`
  (`n: 27`, `deprecated_at: 2026-07-20T11:29:16Z`). İdempotent doğrulandı.

**Koşuda öğrenilen iki şema dersi:**
1. `record_history` **kök alan değil** — `provenance` içinde (kök şema
   `additionalProperties: false`).
2. `_common/provenance.schema.json` de kapalı: `deprecated_reason` /
   `deprecated_at` alanları YOK. **Şema bunun için değiştirilmedi** — gerekçe
   `record_history` note'una yazıldı (zaten "ne oldu, neden" alanı).
   *Şema müdahalesi = son çare.*

---

## Karar 2 — KARAR H22-1: kapsam yüzdesi vs crosswalk ayrımı

**Commit:** `8ad0e43` (H22 kova-A #2)

H20'de "Ali'ye" bırakılan kalem; kanıtla karara bağlandı.

**Karar: kapsam yüzdesi YÜKSELTİLMEYECEK.**

Gerekçe: `pid_coverage`, "bu kaynaktan kaç kayıt **MİNT EDİLDİ**" sorusunun
cevabıdır. H20 eşleştirmesinde bulunan kayıtlar (le-strange 117, darp 753)
mağazada **zaten vardı** — başka kaynaktan mint edilmişlerdi, bu kaynaktan
türemediler. `provenance.derived_from` yazmak **sahte köken iddiası** olur ve
metriği yalanlardı. Doğru temsil zaten uygulanmıştı: `derived_from_layers` (H20).

**Çözüm:** yüzdeyi şişirmek yerine ayrı ve dürüst sayı — manifest'e
`"crosswalk": {matched, note}` + `index.json`'a `crosswalk_matched`. Kap artık
iki şeyi ayrı söylüyor: kaçı bizden türedi (mint), kaçı eşleşti (crosswalk).

**Yan ürün:** lestrange + darpislam kapları ilk kez üretildi (10 → 12 kap;
H20'de eşleştirme yapılmış ama kap açılmamıştı).
- lestrange: mint 215/434 (%49,54) + crosswalk 117
- darpislam: mint 2.338/3.381 (%69,15) + crosswalk 753
- Determinizm bayt-bayt doğrulandı. Gate 160.

---

## Karar 3 — xref kopukluğu: yarış koşulu (bilinçli kapı DEĞİL)

**Commit:** `6b6477d` (H22 kova-A #3)

H19'da "Ali kuyruğu"na yazılan bulgu: `dia_alam_xref`'in 1.400 alam id'sinden
yalnız 88'i mağaza curie evreninde. **Teşhis: yarış koşulu.**

**Üç bağımsız kanıt:**
- (a) `el_alam_augment_pending` durum haritası **mükemmel bölünüyor** — ilk 69
  pozisyon uygulanmış, 70-1280 arası tamamı atlanmış, iç içe geçme SIFIR.
- (b) Eksiklerin alan profilinde ayırt edici fark YOK → *zenginlik-kapısı*
  hipotezi çürütüldü (md %99,7, hd %99,4, ds %97,0).
- (c) Sistematiklik kaynak id'de değil **hedef pid ordinalinde**.

Yani `pass_augment_alam`, DİA adapter'ı kayıtları **hâlâ yazarken** koşmuş;
1.193 augment "dosya yok" diye **sessizce düşmüş**.

**Düzeltme:** pass yeniden koşuldu → `applied=1193, fail=0`. Türev katmanlar
yeniden üretildi:
- alam kap kapsamı %81,63 → **%90,19** (11.379 → 12.572)
- kişi köprüsü ortak 67 → **1.260** (19 kat)
- lookup index + kaplar + person_bridge + ulema_pool güncellendi

**Kalıcı koruma:** `pass_augment_alam`'a **atlama-oranı kapısı** eklendi —
pending'in >%10'u atlanırsa uyarı, `--strict`'te hata. 2026-07-10'da %93
atlanmış ve kimse fark etmemişti; bir daha sessiz geçemez.

---

## Ek koşular (karar değil, icra)

| # | İş | Commit | Sonuç |
|---|---|---|---|
| 4 | 241 birebir yer dubleti birleştirildi | `0a2a14c` | 238 grup / 479 kayıt → 238 kazanan; 8/8 elle denetim doğru; yumuşak-silme + yönlendirme |
| 5 | Kuyruk hijyeni (yalnız sıralama + mükerrer ayıklama) | `c37cf29` | inceleme yükü **5.561 → 3.865**; hiçbir eşleşme kabul/ret edilmedi, hiçbir satır silinmedi |

**#5 alt kırılımı:** süperseding 1.305 satır (ei1→h21-ei1 1.134 + darp-islam→h20
171) · low_info 391 ayrı dosyaya *kopyalandı* (≤6 karakter eşiği REDDEDİLDİ:
846 yakalıyordu, Fes/Kûfe/Rey gibi gerçek toponimleri yiyordu) · fast_track 505
· tie 1.613 (ilk iki aday skoru birebir eşit — ayırt edici sinyal matematiksel
olarak yok, tarihçi toplu ele alsın).

**Açık uç teşhis edildi:** "354 kayıp aday" iddiası ölçümle çürütüldü —
yalnız-eski 440 kaydın 349'u h21 turunun **bilerek** dışladığı evren (belirsiz
300 + artifact 49). Kalan 91'in 86'sının kararı `decision_cache`'te var
(7 match, 79 new), store'a henüz uygulanmamış. **Kayıp yok.**

---

## Phantom PID + indeks bakımı (2026-07-20)

Ayrıntı: `docs/PHASE0_CLOSEOUT.md` §2'ye iki yeni madde eklendi. Özet:

- **1.615 phantom sınıflandırıldı:** (a) index artığı 1.595 · (b) canlı
  referans **0** (kırık bağ yok) · (c) belirsiz 20 (yalnız bekleyen kuyruk
  dosyalarında hedef).
- **Sayı çelişkisi kapandı:** belge 2.779 diyordu, sidecar 1.615 veriyordu;
  fark = H10 S9'da repoint edilen 1.167 openiti − artı person-only taramanın
  görmediği 3 darp-islam.
- **`build_lookup.py` phantom kaynağı DEĞİL** (0/1615 indekste) — phantom'lar
  `pid_index.json` mint defterinde yaşayan rezervasyonlar; **silinmedi ve
  silinmemeli** (ordinal determinizmi / atıf istikrarı).
- **Gerçek indeks kusuru bulundu ve düzeltildi:** `label`/`label_fts` bare
  INSERT yüzünden her `--rebuild`siz koşuda mükerrerleniyordu (211.800
  benzersiz demet için 635.257 satır = 3 geçiş). Tier-2 blocking'in
  `LIMIT`'ini aynı pid'in kopyaları doldurduğu için **aday çeşitliliği ~1/3'e
  düşüyordu**. Artık idempotent + bayat satır budama (stale-row GC) + FTS toplu
  yeniden üretim; koşu 8dk25sn → **9,4 sn**. Suite 160.

---

## Sırada (Ali onayına)

- [ ] Kalan **3.865** satırlık inceleme yükü — tarihçi oturumu. Hijyen turu
      bunları `fast_track` / `tie` / `low_info` kovalarına ayırdı; toplu ele
      alınabilir.
- [ ] (c) sınıfı 20 phantom hedefi: `el_alam_*_pending` kuyrukları eritilirken
      atlama-oranı kapısının bunları yakalaması beklenir — doğrulanacak.
- [ ] *(Ali: buraya ekle)*
