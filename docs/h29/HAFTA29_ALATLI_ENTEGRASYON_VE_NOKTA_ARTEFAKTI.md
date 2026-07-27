# Hafta 29 — Alatlı füzyonu UI-entegrasyonu + "noktalı i" arama artefaktı

## A) Paralel oturumun devri: doğrulama + tazeleme
Backend oturumu H25'te Alatlı senkronik atlas füzyonunu işledi ve UI tarafına
`make view-data` + `make upsert-live` bıraktı. **İddialar bağımsız ölçüldü:**

| İddia | Ölçüm | Sonuç |
|---|---|---|
| 234 kişi (53 mint + 181 augment) | `alatli:` prefix'li 234 kayıt; `derived_from_layers=alatli` 181 | ✅ (aşağıdaki nota bak) |
| quarantine 387→421 | `qid_quarantine.json` = 421 | ✅ |
| 7 aşırı-mint deprecated | store deprecated toplam 405; indekste 405 | ✅ |
| facet "Tarihe Yön Veren Metinler (Alatlı)" | Typesense facet `alatli` = **234** | ✅ |

**Tazeleme yapıldı:** `make view-data` (tüm türev veri) + `upsert` (67.886 dok,
fail=0). Dedup canlı doğrulandı: "Ziya Gökalp" → aktif kayıt score 1.0 üstte,
emekli dublesi −99 dipte.

**NOT (küçük tutarsızlık):** 53 mint edilen Alatlı kaydında `derived_from_layers`
etiketi YOK (yalnız 181 augment'te var). Facet `alatli:` source_id prefix'inden
türediği için arama etkilenmiyor; ama Ulema Havuzu bu 47 kişiyi
"kaynak-curie'siz" sayıyor → havuz UI'ında kaynak izi görünmez. Backend işi.

## B) Bayatlama onarımı: Ulema Havuzu build'e bağlandı
Havuz `make view-data`'da DEĞİLDİ → yeni kişi mint'lerinden sonra bayatlıyordu
(ölçüm: person aktif 22.824 ↔ havuz 22.777 = **47 fark**). Havuz yeniden üretildi
(22.824) ve `Makefile` + `start_local.sh`'a eklendi (canonical_overview'dan ÖNCE
koşar; overview havuzu okur). Artık yeni kaynak eklendiğinde otomatik tazelenir.

## C) KRİTİK BULGU: "noktalı i" arama artefaktı (1.567 kayıt)
Dedup doğrulaması sırasında yakalandı: "Fatma Aliye" araması **yalnız emekli
dubleyi** buluyordu; aktif kayıt (`person-00002691`) bulunamıyordu.

**Kök neden (ölçümle, varsayım değil):** aktif kaydın adı `Fatma Ali̇ye Hanim` —
içinde `"i" + U+0307 (COMBINING DOT ABOVE)`. Bu, Türkçe "İ" (U+0130) harfinin
**Türkçe-duyarsız `.lower()`** ile küçültülmesinden doğan bir üretim artefaktı.
İlk hipotezim (NFD/normalizasyon) **çürütüldü**: indekste `NFC == True` olduğu
hâlde bozukluk sürüyordu — çünkü küçük "i+nokta"nın birleşik hâli Unicode'da YOK.

**Yaygınlık:** mağazada **1.567 kayıt** (person/place/work/…; 40'ı alatli).
**Etki:** artefakt kelime ORTASINDAYSA token eşleşmesi kırılıyor → kayıt aranamaz.
Sondaysa tolere ediliyor (ör. "Şeyhî Mehmed Efendi" bulunuyordu).

**Düzeltme (dar kapsamlı, arama katmanı):** `search/projector.py` → `_nfc_deep()`:
NFC + **yalnız** `"i"+U+0307 → "i"`. U+0307 genel olarak silinmez (bilimsel
transliterasyonda anlamlı, ör. "ṁ"). Canonical dosyalara DOKUNULMADI.

**Kanıt (upsert sonrası canlı):**
- "Fatma Aliye" → `found=2`: aktif "Fatma Aliye Hanim" (1.0) + emekli duble (−99) ✅
- "Abdürrahim Karahisârî", "Gazzîzâde Abdüllatif Efendi", "Hocazâde Muslihuddin
  Efendi" → üçü de birebir bulunuyor (önce bulunmuyordu) ✅

## Kalan (devir)
1. **Kalıcı veri onarımı** — 1.567 kaydın prefLabel'ı kaynakta düzeltilmeli
   (görünüm/view-data hâlâ `Ali̇ye` gösteriyor; arama düzeldi). Üretim hattındaki
   `.lower()` çağrısı Türkçe-duyarlı yapılmalı ki tekrar üremesin. → backend
2. **53 mint'e `derived_from_layers: [alatli]`** → havuzda kaynak izi.
3. **Telif kapısı** (`source_layer=alatli` kamu dump'tan çıkarılacak): kamu-dump
   hattı henüz YOK (`pipelines/publish/` yok) → yayın kurulduğunda uygulanacak;
   `docs/h25/ALATLI_TELIF_KAPISI.md` kaydı duruyor.
4. **Track-3 senkronik timeline** (Doğu/Batı yan yana) — UI fırsatı, sırada.

## Süreç
Paralel oturumun önerisi kabul: aynı working-tree'de git yarışı yaşandı;
bundan sonra `git worktree` ile izolasyon. Commit'ler dosya-listesiyle
(`git add -A` YOK) — karşı tarafın dosyaları süpürülmesin.

Gate 161.
