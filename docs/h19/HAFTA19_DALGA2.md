# Hafta 19 — Dalga 2: Büyük kütleler kaba, kişi köprüsü canlı (2026-07-19/20)

## S1 — 5 kısmi kaynak Kitap Kabı'na girdi (kap sayısı 5 → 10)

`build_containers.py` genişletildi (ayrı script YOK). Kapsamlar sayıldı,
her kapta `unmatched_curies = 0`:

| kap | record_count | mapped | pct | entity_kind_counts |
|---|---|---|---|---|
| alam | 13.940 | 11.379 | %81,63 | person |
| dia | 8.528 | 7.383 | %86,57 | person |
| evliya | 5.444 | 4.807 | %88,30 | institution 2.575 + place 2.232 |
| salibiyyat | 814 | 778 | %95,58 | event 754 + institution 24 |
| cityatlas (Konya) | 583 | 542 | %92,97 | institution |

**Keşifler:** `dia` ailesinin YANINDA `dia-chunks` (2.243) ve
`dia-chunks-v8` (3.309) person curie aileleri var — pid_map'e ALINMADI,
manifest'te `related_curie_families` olarak sayıldı (ayrı kimlik evreni;
İbn Teymiyye 4054/8671 dersi). `salibiyyat:` kümelerinin frontend
`clusters[].id` biçimi (EC_NNNN) **Evliyâ'nın EC_ önekiyle çakışıyor** →
kap anahtarı daima kaynak-önekli, çıplak id asla (manifest'te
id_collision_note). Konya'da 583 kayıt / 581 benzersiz id (kp_beyşehi_r_
gölü_2 ×3 dubleti; curie'ler etkilenmiyor, notlu).

**work_pid:** alam `iac:work-00000333` BULUNDU (el-A'lâm, dublet yok);
evliya 00000062 + dup_note (00000210 aynı eser); dia/salibiyyat/cityatlas
null + work_missing (label taraması 0 — UYDURULMADI).

**Kahire çifte temsili dürüstlüğü:** cityatlas manifest'inde
`cities.cairo = {pointer: "khitat", note: "AYNI 801 yapı"}`; ayrıca
`build_source_counts.py` detail'ine `overlap: {cairo: khitat}` eklendi —
kaynaklar-arası toplam alınırken çifte sayım engellenir.

## S2 — Kişi köprüsü: "kayıtlar birbirini tanıyor"

`build_person_bridge.py` → `person_bridge.json` (19.694 kişi; alam 11.379
+ dia 7.383 anahtar; 1,15 MB; deterministik sha256 kanıtlı).
`skipped_multi = 0` (SQL ile bağımsız doğrulandı: person namespace'te
hiçbir pid aynı kaynaktan iki curie taşımıyor). dia-chunks aileleri
tamamen dışarıda.

UI: `personBridge.js` + A'lâm kartı (ds boşken köprüden DİA slug'ı,
yeni 📕 EI-1 düğmesi) + DİA kartı (xref boşken pid-merge'den A'lâm,
yeni EI-1 düğmesi) + `#ei1/<id>` derin linki (Ei1View initialId — bu
sözleşme de ilk kez çalışıyor).

**CANLI KANIT (zincir):** `#dia/nabi` → NÂBÎ kartı → "📕 EI-1'de Aç" →
`#ei1/4138` → "NABI, Yûsuf, Osmanlı şairi (Vol. 3)". Aynı kişinin iki
ansiklopedideki maddesi ilk kez tek tıkla bağlı.

## KARAR H19-1: köprünün gerçek değeri ölçüldü — ve bir tutarsızlık bulundu

Beklenti alam↔dia'yı zenginleştirmekti; **ölçüm bunu çürüttü**:
- Köprünün ürettiği alam↔dia çifti: 67 — **67'si de** mevcut
  `dia_alam_xref.json`'da zaten var → **yeni çift 0**, çelişki 0.
- Asıl değer başka katmanda: **alam↔ei1 106**, **dia↔ei1 70** çift ve
  üçlü (alam+dia+ei1) 1 kişi — bunlar xref'te HİÇ yoktu.
- **Tutarsızlık keşfi (insan incelemesi):** xref'in 1.400 A'lâm id'sinden
  yalnız **88'i** mağazanın 11.379 el-alam curie'sinde mevcut; 1.312'sinde
  A'lâm id'si mağaza evreninde hiç yok (her iki evren de 1–13.940
  aralığında, yani aynı numaralandırma). "İkisi de mağazada ama farklı
  pid" (birleştirilebilir) vakası **0**. Örüntü sistematik — el-alam
  ingest'ine girmemiş / curie'si düşmüş bir küme. Sebep kararı Ali'ye:
  PHASE0 kuyruğuna "xref↔store id-evreni kopukluğu (1.312)" eklendi.

Ders (H10 S11 ve H11 S11'in üçüncü tekrarı): **beklenti değil popülasyon
ölçümü hakemdir** — köprü "alam↔dia'yı zenginleştirir" varsayımıyla
yapıldı, ölçüm değeri EI-1 ekseninde gösterdi.

## Kapı

`make test` 160 passed. Sıradaki: Dalga 3 (darpislam %69, lestrange %50,
**Ulema Havuzu** — 450'lik set tohum, havuz alam+dia+ei1+kitap
çıkarımlarından beslenir; person_bridge bu işin altyapısı olarak hazır).
