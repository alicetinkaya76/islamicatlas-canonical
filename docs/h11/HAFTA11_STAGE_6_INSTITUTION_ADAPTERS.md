# Hafta 11 · Stage 6 — Institution adapter'ları (3,918 kayıt)

**Tarih:** 2026-07-13 · **Önkoşul:** S5 (şema seti v0.4.0, ADR-015)

## Ne yapıldı

Üç yeni adapter INSTITUTION namespace'ini doldurdu (mağaza 52,481 → 56,399):

| Adapter | Kaynak | Mint | Augment | Review | Not |
|---|---|--:|--:|--:|---|
| konya-city-atlas | konya.json (583) | **542** | — | — | 39 sınır kaydı kuyruğa (aşağıda), 2 mükerrer-id atlandı |
| maqrizi-khitat | cairo.json (801) | **801** | — | — | cairo.json = maqrizi layer'ın zengin formu (aynı 801; İKİ kaynak değil) |
| evliya-institutions | evliya layer'ın 12 yapı kategorisi (2,608) | **2,575** | 9 olay/8 pid | 24 | H10 institution_pending havuzu kapandı |

- **located_in:** Konya yapıları → `iac:place-00016243` (Tier-2 deterministik;
  Iconium/darp-islam), Kahire yapıları → `iac:place-00009399` (EDİTORYAL
  SABİT — Tier-2 conf 0.8615'te review'a düştü: label 1.0 + spatial 1.0,
  alt-tahmin cezası artefaktı; kimlik şüphesiz, kanıt canonicalize.py'de).
  Evliyâ yapılarına located_in YOK (kayıtta şehir adı yok; koordinattan
  çıkarım = tahmin, ADR-008'e aykırı — harita coords'tan çalışır).
- **patron_dynasty:** AÇIK alias tablolarıyla 457 bağ (Konya 94 + Kahire 363).
  Fuzzy değil — mağazada iki 'Karaman' hanedanı var (00000023 Trablusgarp!
  vs 00000124 Konya); 'Selçuklu' Konya bağlamında 00000107 (Rûm).
- **Alt-tip eşlemesi muhafazakâr:** kale/sinagog/kuyu/konak/arsa → `other`
  + v1 kategorisi note'ta (anlam esnetilmez). subtype-other: Konya 73,
  Kahire 181, Evliyâ 0 (12 kategori birebir).

## İnsan-inceleme kuyrukları (otomatik çözülmedi)

1. `data/_state/konya_institutions_pending.json` → 39 `borderline_review`:
   'turizm' (göl/tepe/modern otel karışık) + 'kultur_varligi' (içinde
   Ereğli=KASABA ve Çatalhöyük var) kategorileri MINT EDİLMEDİ.
2. `data/review_queue/evliya-institutions.jsonl` → 24 girdi (11'i Evliyâ'nın
   adsız "Camii" kayıtları — isim-birebir istisnası; hızla elenebilir).
3. `data/review_queue/h11-s6-curation.jsonl` → Konya 3'lü place-dup kümesi
   (16243 Iconium / 16505 Madinat Quniyah / 16952 Quniyah — son ikisi AYNI
   koordinatta). Merge kararı tarihçiye; merge sonrası 542 yapının
   located_in çapası migre edilmeli.

## Resolver düzeltmeleri (ADR-008 §8.2 revizyonu, kanıtlı)

İlk Evliyâ koşusu 850 review + 16 auto-match verdi; ikisi de kirliydi:

- **`review_min_signals: 2`** (tip-bazlı YAML): koordinatsız placeholder
  kayıt **"(Meçhul Cami)"** (Makrîzî'de adı kayıp cami, «3» = yazma boşluğu)
  label-only 0.8 ile **632 sahte review** çekti — token_set alt-küme etkisi
  ("X Camii" ⊇ "cami"). Tek-sinyal aday artık kuyruğa giremez; İSTİSNA:
  skor ≥ auto eşiği ise girer ("name-only asla auto-match olmaz"
  doktrininin öbür yüzü).
- **`spatial_km_decay: 2.0`** (tip-bazlı): 50 km şehir-decay'i aynı şehrin
  iki AYRI yapısına spatial≈1.0 verdi → **3 farklı Evliyâ camisi Almâs
  Camii'ne auto-match oldu** (0.92; ayrıca yanlış Sadreddin-Konevî ve
  Ümmü's-Sultân bağları). Bina kimliği bina ölçeği ister: 2 km decay ile
  kontamine 6 eşleşme öldü, kalan 9'un tamamı temiz (Amr 0.996, Ezher
  0.996, Alâeddin 0.963, Hân el-Halîlî 0.991, Mevlâna külliyesi ×2, ...).

Her iki parametre öntanımlıda eski davranışı korur (diğer tiplerin
kalibrasyonu değişmedi).

## Kapı

- `full_reindex --dry-run`: **56,399/56,399** projeksiyon (3,918 institution;
  `_geo` + related_pids located_in/patron zinciriyle çözülüyor).
- `make test`: **160 passed, 2 skipped, 3 xfailed**.
- pid_minter: `institution` namespace kaydı; build_lookup temporal zincirine
  `founded_temporal`; facets+projector prefix_map `maqrizi-khitat`.
