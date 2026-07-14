# Hafta 11 · Stage 9-11 — data.zip bonus katmanları (mağaza 57,177)

**Tarih:** 2026-07-14 · **Önkoşul:** S8 (web v0) · **Envanter:** 14 aday
dosya, 14 paralel profil ajanıyla tarandı (tam sonuçlar workflow journal'da).

## Envanter kararları

| Dosya | Karar |
|---|---|
| yaqut_detail / dia_works / ei1_works / le_strange_xref / ei1_geo / yaqut_graph / yaqut_crossref | **BAYT-BAYT mağaza kopyası** — iş yok (yeniden dönüştürme = mükerrer sayım riski) |
| salibiyyat_atlas_layer | **S9: event+institution adapter** (aşağıda) |
| alam_detail | **S10: 13,940 kişi augment** (aşağıda) |
| dia_relations / dia_travel | **S11: kenar dönüşümleri** (aşağıda) |
| ei1_relations | 68 gerçek kenar (%91'i SAME_AUTHOR yazar-imzası gürültüsü) — Faz 2 |
| muqaddasi_xref | kısmen yeni sameAs bağları — Faz 2 (dup-merge oturumuyla) |
| dia_geo | kişiye ham koordinat ŞEMAYA AYKIRI (doğru olan da bu) — birth/death_place çözüm aşamasının DOĞRULAMA kanıtı olarak bekliyor |

## S9 — Salibiyyât (754 olay + 24 kale)

6 Müslüman vekāyi'nâmecisi (İbn el-Esîr, Makrîzî, Üsâme, Ebû Şâme, İbn
Şeddâd, İmâdüddîn) → 754 tanıklık-olayı mint (`primary_textual`; Arapça
kronik pasajı description.ar'da). Yılsız 36 kayıt MINT EDİLMEDİ (temporal
şemada zorunlu) → sidecar. outcome kaynak enum'u şema enum'una çevrilMEDİ
(yorum olurdu) → ham değer note'ta. 24 Haçlı kalesi → institution subtype
"other" (kale ≠ palace, S6 doktrini). 4 küme ↔ mevcut canonical olay
(Hıttîn, Kudüs 1187, Ayn Câlût, Mansûre) eşlemesi sidecar'da — otomatik
birleştirme YOK. Konum: 251/754 Tier-2 bağlı; 71 gazetteer yeri çözülmedi
(çoğu mağazada olmayan küçük Haçlı mevzileri; adı note'ta).

## S10 — el-Aʿlâm detay augment (11,379 kişi)

alam_detail.json gap-fill-only: ALA-LC tam isim zinciri →
transliteration["ar-Latn-x-alalc"] (şema kalıbı tuzağı: "ala-lc" GEÇMEZ),
TR/AR tam zincirler → altLabel, EN/TR kısa tanımlar → description
(EN ilk kez!), künye. dia URL alanı KULLANILMADI (küratörlü xref'le %54
çelişki). 11,412 başlıklı eser MINT EDİLMEDİ (ADR-009) →
alam_works_pending; bp/dp+mc yer verileri → alam_places_pending (kişi-yer
bağlama aşamasına). İdempotans kusuru yakalandı+düzeltildi: yeniden-koşu
pending dosyalarını daraltıp eziyordu (toplama marker-öncesine alındı).

## S11 — DİA kenarları

- **dia_relations → teachers/students:** 7,965 kenar / 3,400 kişi. YÖN v1
  KAYNAK KODUNDAN TEYİTLİ (DiaIdCard.jsx: `[teacher, student, count]`).
  41 çift-yönlü çift = çelişki → İKİSİ DE uygulanmadı (kuyruk); 3,390 co
  (çağdaşlık) şemasız → pending.
- **dia_travel → active_in_places:** 1,741 kenar / 1,360 kişi.
  İsim-tek-sinyal auto-match yasağı delinmedi: fuzzy YOK, belirsizlik-
  korumalı BİREBİR eşleme (norm eşit + mağazada TEKİL aday) + el-/al-
  artikel eşdeğerliği (Kahire 209 kenar bu yüzden takılıyordu). 155
  belirsiz ad = MAĞAZA MÜKERRER KÜMELERİ görünür oldu (Mekke×8, Nişabur×6,
  Buhara×5, Bağdat×3...) → dup-merge oturumunun somut kanıt listesi;
  748 eşleşmeyen ad (Halep/Haleb b-p, Semerkant/Samarqand ekzonimleri)
  bilerek pending — mükerrerler birleşmeden alias yazılamaz.

## Resolver: name_evidence (ADR-008 revizyonu, kanıtlı)

`name_evidence: max` (YAML, tip-bazlı; place+institution açık, person
KAPALI — 0.95 kalibrasyonu eski formülle): label ve alt TEK isim kanıtına
katlanır, max(label, alt). Kanıt: zengin-altLabel'lı aday sorgu alt
vermeyince CEZALANIYORDU (Musul: label 1.0 + spatial 1.0, alt 0.38 → 0.876
review'a düşüyordu; Urfa'yı alt 'Edessa' 1.0 kurtardı). Ayrıca salibiyyat
gazetteer'inin "Urfa (Edessa)" biçimli adları pref+alt'a ayrıldı; konum
bağlama 166→251'e çıktı.

## Kapı

- `full_reindex --dry-run`: **57,177/57,177** · `make test`: **160 passed**
- Typesense canlı: **57,177/57,177 upsert fail=0**; "Hıttîn" araması yeni
  tanıklık + mevcut olayı birlikte getiriyor.
- Web: arama sayfasına Liste/Harita geçişi (250 geo-nokta, tür-renkli).
