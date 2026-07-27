# H25 Alatlı füzyonu → UI oturumuna HANDOVER

Merhaba 👋 — paralel oturumda (H27 UI: menü kaynaşması / mobil parite / Kitap Kabı)
çalışıyorsun. Ben H25'te **Alatlı senkronik atlas füzyonunu** backend'e (canonical
store + Typesense) işledim. İkimiz aynı repo'dayız; commit'ler temiz merge'lendi
(`417ba9e`), hiçbir işin kaybolmadı. Bu doc: ne eklendi + **UI tarafında ne gerekiyor**.

---

## Ne eklendi (backend, hepsi committed + reproducible)

`~/Desktop/alev_alatlı/corpus_json/` atlasından (677 kişi, tarih-teyitli Wikidata
QID + koordinat) yeni `alatli` adapter ile füzyon:

- **234 kişi** `source_layer=alatli` (53 mint + 181 augment). 6 mint dedup'la
  **deprecated** (aşağıda).
- **98 tarih-teyitli QID** mevcut kişilere eklendi (Gazzâlî, Taberî… ), hepsi
  `reviewed:false` → **display-gate ardında** (senin mevcut kuralın).
- **34 FP-QID quarantine** edildi (`qid_quarantine.json` 387→421): Q39619 (Halife
  Ali) 6 yanlış kişide → 0, Q9458 (Muhammed) → 0 vb. (store'un %33,7 FP'sine katkı).
- **Batı kanonu (280 figür) MINT EDİLMEDİ** — telif+kapsam kararı (scope-b) →
  `data/sources/alatli/_alatli_western_held.json` yan-tablosunda.
- Facet + projector kaydı yapıldı: `search/facets.yaml` (source_layer=alatli →
  "Tarihe Yön Veren Metinler (Alatlı)") + `search/projector.py` prefix_map.

Detay: `docs/h25/ALATLI_QID_AUDIT.md` + `ALATLI_TELIF_KAPISI.md`.

---

## UI tarafında GEREKENLER

### 1. Index tazeleme (ÖNCELİK) ⚠️
Füzyon + temizlik canonical'da ama **canlı görünmesi için tazeleme şart**:
```
make view-data      # canonical → v1 görünüm dosyaları (senin akışın)
make upsert-live    # Typesense (67.886 kayıt, ~2dk)  [TYPESENSE_* env / .env]
```
Ben bir kez upsert ettim ama **dedup + quarantine ÖNCESİ** → tekrar gerek.
Bu, deprecated 6 mint'i −100'e çeker ve 34 quarantine'i yansıtır.
(Ben eşzamanlı çalıştığın için şimdi upsert etmedim, karışmasın diye — sen yap.)

### 2. Kaynak facet'i doğrula
`Kaynak` filtresi `facets.yaml`'den okuyorsa **otomatik** ("Tarihe Yön Veren
Metinler (Alatlı)" görünür, 234 kayıt süzer). Hardcoded liste kullanıyorsan
`source_layer: alatli` değerini ekle.

### 3. Deprecated 6 mint gizlensin
Aşırı-mint dedup'ı (ad-sırası farkı yüzünden resolver kaçırmıştı): Bolayır,
Bayburtlu Zihni, Grunebaum, Ziya Gökalp, Louis Bazin, Fatma Aliye → her biri
`provenance.deprecated=true` + `deprecated_in_favor_of=<mevcut pid>` (projector
−100). H23'teki **27 EI-1 hayaleti gibi** — `build_view_data` deprecated'ı zaten
filtreliyorsa otomatik düşer; değilse aynı filtreyi uygula. QID'leri mevcut
kişiye TAŞINDI, kaybolmadı.

### 4. Telif kapısı (public build) 🔒
`source_layer=alatli` **kamu CC-BY-SA dump'ından çıkarılmalı** (İSAM deseni,
`ALATLI_TELIF_KAPISI.md`). Olgular (ad/tarih/koordinat, Wikidata CC0+TDV
kaynaklı) yayınlanabilir; yalnız **seçim** (derleme-telifi) izne-bağlı. Store'da
Alatlı **düzyazısı YOK** → DİA'dan az hassas. Lite/public build'de `dia`
gate'ine `alatli` da ekle.

---

## FIRSAT — Track-3: Senkronik Timeline görünümü (senin alanın) ✨

Alatlı'nın **biricik** değeri: "aynı tarihte Doğu'da kim, Batı'da kim" —
İslami (Bize) + Batı (Batıya) kanonu **yan yana zaman ekseninde**. islamicatlas
harita-merkezli; bu **zaman-merkezli** bir mercek katar (visits/scholars gibi
yeni bir view).

- İslami taraf: canonical'da (`source_layer=alatli`, tarih+koordinat hazır).
- Batı tarafı: `_alatli_western_held.json` (canonical değil, karşılaştırmalı mercek).
- **ÇALIŞAN TAM REFERANS**: `~/Desktop/alev_alatlı/corpus_json/timeline_standalone.html`
  — yıl kaydırıcı + iki paralel şerit + harita + senkronik-kesit + tıkla-kaynağa-in.
  Framework'süz, tek dosya; v1 diline uyarlanabilir. Açıp bak, tasarım hazır.

İstersen bunu bir sonraki dilimde ele alırız; almazsan füzyon zaten canlı,
sadece 1-2-3-4 yeterli.

---

## Süreç notu 🔧
İkimiz **aynı working-tree'deyiz** → git yarışı + geçici working-tree
tutarsızlığı yaşandı (benim genişletilmiş audit script'im bir ara working-tree'de
eski göründü ama HEAD'de doğru). Öneri: `git worktree add` ile izole çalışırsak
bu risk sıfırlanır.

— H25 (Alatlı füzyonu). Sorular için commit'ler: adapter `ddcdb37`, augment
`98233b9`, triyaj+audit `78a7785`, QID-genişletme `af13049`, mint-dedup `040c12c`.
