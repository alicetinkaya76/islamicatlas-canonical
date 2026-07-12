# Hafta 10 — Stage 2: darp-islam adapter'ı (Tier-2'nin ilk gerçek tüketicisi)

**Date:** 2026-07-10
**Branch:** hafta5-work-namespace
**Entry:** H10 Stage 1 (`0eb6a3b`, Tier-2 resolver) üstüne.
**Kaynak:** DarpIslam v1.1 (2026-03-27) — 3.458 İslam darphanesi (3.381
geokodlu; fark metadata'dan, tahmin değil). Lisans: Diler/Hamburg-ERC (MIT) +
nomisma.org. İlk kez bir adapter EntityResolver'a bağlandı (ADR-006 v1.1
resolve aşaması fiilen çalışıyor).

---

## Tasarım: iki-track + küratör-sinyalli demotion

- **Track A (match):** Tier-2 mevcut place'i bulursa YENİ KAYIT YOK —
  augment sidecar'ı (`darp_islam_augment_pending.json`; le-strange deseni),
  `apply_darp_augments.py` uygular: `derived_from_layers += "darp-islam"` +
  record_history update. Append-only; label/coords/temporal'a dokunulmaz.
- **Track B (new):** yeni place: @type [Place, Settlement], coords
  (centroid, 10km), temporal_coverage (emisyon yılları CE), üç-dilli label,
  provenance `digital_corpus` (ADR-010). `nomisma_uri` → page_or_locator +
  note (v0.3.0 authority enum'unda 'nomisma' yok — **v0.4.x enum adayı**).
- **Review:** kuyruğa (`data/review_queue/darp-islam.jsonl`) + sidecar
  `_review_skipped`; MINT YOK (muhtemel dublör asla basılmaz).
- **Guard:** lookup.sqlite yoksa adapter ÇALIŞMAYI REDDEDER (indekssiz
  resolve = her bilinen şehir için dublör basmak).

## Pilot bulguları (2 düzeltme)

1. `detail.yakut_tr` **isim değil açıklama metni** ("Kazvin ve Zanjan
   arası...") — altLabel olarak resolver'a verilince FTS kirleniyor;
   labels'tan çıkarıldı, yalnız küratör-sinyali olarak kullanılıyor.
2. **Hinted-new demotion:** 402 yakut-ipuçlu mint'in sağlamasında 101'i
   "new" çıktı — küratör "Yâqūt'ta var" diyor, resolver uzak transliterasyonu
   bulamıyor. Bunları mint etmek dublör üretirdi → ipuçlu-new artık mint
   edilmez, review'a düşer (North Star: küratör-sinyali + resolver-kaçırması
   = borderline = insan).
3. İlk bulk'ta augment sözlüğü pid-başına TEK girişti — aynı şehre düşen 85
   eşleşme sessizce eziliyordu; liste yapısına çevrilip yeniden koşuldu.

**Sağlama örneklemi** (186 auto-match'ten 10): Ankara↔Anqarah 2km 0.99,
Antalya↔Attalia 3km 0.97, Erdebil↔Ardabīl 1km 0.99, Aden 2km 0.98 — tümü
şüphesiz doğru. place auto-eşiği 0.90'da kaldı (bu kaynak için yeterli kanıt;
kişi-uzayının adaş problemi yerlerde koordinat sinyaliyle bastırılıyor).

## Kesin bulk (cache+kuyruk sıfırlanarak; 56 sn)

| Sonuç | Sayı |
|---|---:|
| eşleşme-olayı → augment | **706** (621 benzersiz yer; `apply` 621/621, idempotent) |
| yeni place mint | **2.338** (0 validasyon hatası) |
| review (kuyruk + ipuçlu-demotion) | **337** = 218 band + 119 ipuçlu |
| TOPLAM | **3.381** ✓ (=geokodlu evren; muhasebe tam) |

place: 15.239 → **17.577** · `full_reindex --dry-run` **49.040/49.040, 0
fail** · lookup index yeniden kuruldu (yeni yerler sonraki adapter'lara
görünür).

## Rezerve PID istisnası (3 adet — dürüst kayıt)

Pilot 87 Track-B PID mint'ledi; düzeltilmiş sorgu şekliyle 3'ü (darp-islam:
24, 85, 95) review'a düştü → index'te kayıtsız "rezerve" PID. Bilinçli
bırakıldı: tarihçi onaylarsa idempotent mint AYNI PID'i kullanır.
`test_i_pid_minter_idempotent` bu kategoriyi tanır — ancak sidecar
`_review_skipped`'ta belgeli rid'ler mazur görülür; belgesiz index-hayaleti
hâlâ kırmızı yapar.

## Test güncellemeleri (bilinçli, belgeli)

- `test_a1` hacim bandı 14-16K → **17-19K** (+darp-islam; band tarihi test
  yorumunda).
- `test_i` rezerve-PID kategorisi (yukarıda).
- Suite: `make test` **156 passed** / 2 skipped / 3 xfailed.

## Kalan işler (bu kaynaktan)

- 337 review vakası → tarihçi (kuyruk + sidecar'da aday listeleriyle).
- detail.battles/emissions/dynasty_meta → event/coin katmanı (P1.5,
  INVENTORY'deki plan; bu stage place-only).
- 'nomisma' authority enum'u → v0.4.x set bump adayı (ADR-013).

## Rollback

Kod+docs tek revert. Veri: 2.338 kayıt `derived_from[].source_id`
`darp-islam:*` ile seçilip silinebilir; augment'lar record_history
girdisinden geri alınabilir; pid_index kalır (ordinal determinizmi).
