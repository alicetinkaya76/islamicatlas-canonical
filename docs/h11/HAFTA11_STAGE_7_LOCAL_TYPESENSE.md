# Hafta 11 · Stage 7 — Yerel Typesense: 56,399 kayıt CANLI aramada

**Tarih:** 2026-07-13 · **Önkoşul:** S6 (mağaza 56,399)

Hosting kararı beklenmeden canlı arama yolu yerelde açıldı:

- Docker `typesense/typesense:29.0`, container `islamicatlas-typesense`,
  port 8108, veri `data/_local/typesense/` (gitignored), anahtar `.env`de
  (gitignored; şablon: TYPESENSE_URL + TYPESENSE_API_KEY).
- `upsert.py --recreate` → **ok=56,399 fail=0** (sessiz kayıp yok ilkesi).
- **Şema düzeltmesi:** `token_separators` içindeki ʿ (U+02BF) / ʾ (U+02BE)
  Typesense 29.0'da 400 veriyor ("array of character symbols") — canlı
  sunucuya karşı doğrulandı; ASCII'ye inildi (ayn/hamza translit
  normalizasyonunda zaten temizleniyor).
- Doğrulama sorguları: "Alâeddin Camii" ilk sonuç = iki-katmanlı birleşik
  kayıt (evliya-celebi + konya-city-atlas augment izi source_layer
  facet'inde); entity_type dağılımı = mağaza sayımlarıyla birebir
  (person 22,935 · place 19,929 · work 9,331 · institution 3,918 ·
  dynasty 186 · event 100).

Yeniden kurulum: `docker start islamicatlas-typesense` +
`set -a; source .env; set +a; python3 pipelines/search/upsert.py`.
