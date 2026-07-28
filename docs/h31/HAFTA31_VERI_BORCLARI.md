# Hafta 31 — Devralınan veri borçlarının kapatılması

Paralel backend oturumundan devralınan üç borç; hepsi **kök nedene inilerek**
kapatıldı (semptom yaması değil).

## 1) "Noktalı i" — kök neden + 1.274 kayıt onarımı + guard

**H29'da yalnız aramayı yamamıştım** (projector'da NFC + hedefli değiştirme).
Görünümler hâlâ `Ali̇ye` gösteriyordu ve hata üretimde tekrar üreyecekti.

**KÖK NEDEN:** Türkçe-duyarsız `str.title()`.
`"ABDÜLLATİF".title()` → `"Abdüllati̇f"` (`i` + U+0307). Küçük "i+nokta"nın
BİRLEŞİK hâli Unicode'da yok → NFC bunu düzeltemez.
Projede **zaten Türkçe-güvenli `tr_title()` vardı** (`_lib/institution_common`);
3 üretim noktası ona çevrildi: `ei1/canonicalize`, `h21_ei1_triage`,
`an_cat_b_resolve`.

**VERİ ONARIMI:** `h31_001_dotted_i_repair.py` → **1.274 kayıt**.
Dar kapsam: yalnız metin alanları (labels/note/nisba/laqab/kunya/nasab/
profession). `pid`, tarih, koordinat DOKUNULMADI. U+0307 **genel olarak
silinmez** (bilimsel transliterasyonda anlamlı: "ṁ"). Ledger + `--restore`.

**ŞEMA UYUMU (H22 dersinin tekrarı):** `record_history.change_type` enum'unda
`repair` YOK ve `changed_by` ZORUNLU → `type="update"`, gerekçe `note`'ta.
**Şema değiştirilmedi** (son çare ilkesi).

**GUARD (2 test):** (a) canonical etiketlerde artefakt yok; (b) pipelines'ta
çıplak `.title()` **çağrısı** yok — **AST ile** (ilk sürümüm regex'ti ve
docstring'lerdeki `.title()` metnini yanlış-pozitif yakalıyordu).

**Sonuç:** view-data 8 dosyada **0 artefakt** (H29'da görünümler bozuktu);
Typesense'te "Fatma Aliye Hanim" temiz.

## 2) Alatlı mint'lerinde eksik `derived_from_layers` — ve ASIL kök neden

Görünen sorun: 47 aktif Alatlı mint'inde `derived_from_layers` etiketi yoktu →
`h31_002_alatli_layer_tag.py` ile eklendi (geri alınabilir).

**AMA etiket eklemek havuzu düzeltmedi** — "kaynak-curie'siz: 47" aynı kaldı.
Ölçüm asıl nedeni gösterdi: **Ulema Havuzu kaynak izlerini canonical
dosyalardan değil `data/_index/lookup.sqlite`'ın `source_curie` tablosundan
okuyor** ve **indeks 2026-07-20'den beri bayattı** — içinde **0** alatli curie'si
vardı.

`build_lookup.py --rebuild` → alatli curie **0 → 234**; havuz yeniden üretildi:
**kaynak-curie'siz 47 → 0**. Kaynak dağılımı: a 12.476 · d 7.346 · b 8.712 ·
e 1.144 · sc 279 · s 182.

## 3) Bayatlama sınıfının kalıcı çözümü (oto-uyum)

Bu oturumda **iki ayrı bayatlama** yakalandı (havuz, indeks). İkisi de artık
build zincirinde, doğru sırayla:

```
make view-data →  build_view_data → build_book_city_atlas → build_canonical_map_layer
               →  build_lookup(--quiet) → build_alatli_synchronic → build_ulema_pool
               →  build_canonical_overview
```
Sıra önemli: **indeks** havuzdan önce (havuz indeksi okur), **havuz**
overview'dan önce (overview havuzu okur).

## Gate
`make test` → **163 passed** (2 yeni guard dahil).

## Not
`data/canonical` ve `data/_state` **gitignore'da** (proje kuralı: türetilmiş/
lisanslı veri commit edilmez). Onarımlar diskte; **migration script'leri
commit'li** → her makinede yeniden üretilebilir, `--restore` ile geri alınabilir.
