# Audit Output — Example

Bu dizin `scripts/week1_audit.py`'nın **gerçek islamicatlas verisinde** koşturulmuş örnek çıktısıdır. Amaç: ekibin aracın ne ürettiğini görmesi ve Week 1 hedefinin somut örneğini incelemesi.

**Koşturulma tarihi:** 2026-04-21  
**Kapsama:** 47 dosya (JSON + CSV), 129.3 MB, ~105.802 kayıt

## Dosya listesi

| Dosya | İçerik |
|---|---|
| `summary.md` | Tüm katmanların üst-düzey tablosu + otomatik tespit edilen kritik bulgular |
| `summary.json` | Aynı bilgi makine okunur |
| `cross_reference.md` | Mevcut xref haritası + tespit edilen boşluklar |
| `duplicates.md` | Yedek/tekrar dosya tespiti |
| `<layer_name>.md` × 47 | Her katman için ayrıntılı rapor |

## İnceleme önerisi

1. Önce `summary.md`'ye bak — genel resim
2. "Kritik bulgular" bölümünü oku — scriptin otomatik tespit ettiği sorunlar
3. Büyük katmanlara odaklan: `yaqut_lite.md`, `alam_lite.md`, `dia_lite.md`, `konya.md`
4. Karşılaştırma yap: `yaqut_lite` vs `le_strange_eastern_caliphate` — ikisi de "yer" katmanı ama şemaları tamamen farklı. Canonical `Place` modelinin kapsaması gereken heterojenlik budur.

## Regenerate

Çıktı lokal olarak yeniden üretilebilir:

```bash
python3 scripts/week1_audit.py \
    --data-dir /path/to/islamicatlas/public/data \
    --csv-dir  /path/to/islamicatlas/data \
    --extra    /path/to/islamicatlas/public/data/city-atlas \
    --out      ./audit_output     # .gitignore'da — lokal çalışma için
```
