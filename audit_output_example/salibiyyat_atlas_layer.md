# Katman Denetimi: `salibiyyat_atlas_layer.json`

**Yol:** `/home/claude/Ars_iv/public/data/salibiyyat_atlas_layer.json`  
**Boyut:** 0.65 MB (679,949 bayt)  
**Son değişiklik:** 2026-04-02T09:51:42  
**İçerik hash (ilk 1 MB):** `743cfcc54a26d1919ebd581599d2de09`

## Üst-düzey yapı

- **Üst tip:** `dict`
- **Toplam kayıt:** 981
- **Alan sayısı:** 49

### Alt koleksiyonlar

| Ad | Sayı | Tür |
|---|---:|---|
| `sources` | 6 | list |
| `events` | 790 | list |
| `castles` | 24 | list |
| `boundaries` | 4 | list |
| `boundary_years` | 7 | list |
| `routes` | 11 | list |
| `clusters` | 21 | list |
| `locations` | 123 | list |
| `cross_refs` | 2 | dict |

### Metadata özü

```json
  "layer_id": "salibiyyat"
  "layer_name": "<dict>"
  "description": "<dict>"
  "version": "1.0.0"
  "created": "2026-04-01"
  "authors": "<list>"
  "source_app": "salibiyyat (github.com/alicetinkaya76/salibiyyat)"
  "schema_version": "islamicatlas_layer_v2"
  "stats": "<dict>"
```

## ID analizi

- **Birincil ID alanı:** `id`
- **Toplam ID:** 856
- **Tekil ID:** 856
- **Yinelenen:** 0 — ✅ TEKİL
- **Tip:** `str`
- **Örnek:** ibn_athir, maqrizi, usama, abu_shama, ibn_shaddad

## Koordinat kapsaması

- **Koordinatlı kayıt:** 958 (**97.7%**)
- **Kullanılan enlem alan adları:** `lat`(958)
- **Kullanılan boylam alan adları:** `lon`(958)
- **Dünya sınırı dışı:** 0

## Çok dillilik

- **Türkçe ad:** 4.6%
- **Arapça ad:** 84.0%
- **İngilizce ad:** 85.1%

## Tarih kapsaması

- **Herhangi bir tarih alanı olan:** 775 (**79.0%**)
- **Kullanılan tarih alanları:** `year`(775)

## Alan profili (ilk 40)

| Alan | Kapsama | Null-olmayan | Tipler | Örnek |
|---|---:|---:|---|---|
| `CST_002` | 0.1% | 0.1% | dict(1) | <dict> |
| `CST_018` | 0.1% | 0.1% | dict(1) | <dict> |
| `EC_0011` | 0.1% | 0.1% | dict(1) | <dict> |
| `EC_0013` | 0.1% | 0.1% | dict(1) | <dict> |
| `EC_0014` | 0.1% | 0.1% | dict(1) | <dict> |
| `EC_0016` | 0.1% | 0.1% | dict(1) | <dict> |
| `arabic_text` | 80.5% | 80.5% | str(790) | ذكر وفاة منصور بن مروان / ذكر استيلاء عسكر مصر على مدينة صور / ذكر ملك |
| `cluster_id` | 80.5% | 12.1% | str(119) | EC_0001 / EC_0002 / EC_0003 |
| `color` | 2.1% | 2.1% | str(21) | #e74c3c / #f39c12 / #2ecc71 |
| `cross_ref` | 0.6% | 0.6% | dict(6) | <dict> / <dict> / <dict> |
| `crusade_number` | 1.1% | 1.1% | int(11) | 1 / 1 / 2 |
| `crusader_state` | 2.4% | 2.3% | str(23) | County of Tripoli / Principality of Antioch / Kingdom of Jerusalem |
| `description_ar` | 2.4% | 2.4% | str(24) | أروع نماذج تصميم القلاع متحدة المركز. فناء داخلي بأبراج دائرية على صخر |
| `description_en` | 2.4% | 2.4% | str(24) | The finest example of concentric castle design. Inner ward with round  |
| `description_tr` | 2.4% | 2.4% | str(24) | Konsantrik kale tasarımının en önemli örneği. Doğal kayalık üzerine yu |
| `event_count` | 15.3% | 15.3% | int(150) | 158 / 177 / 64 |
| `events` | 2.1% | 2.1% | list(21) | <list> / <list> / <list> |
| `id` | 87.3% | 87.3% | str(856) | ibn_athir / maqrizi / usama |
| `image_url` | 2.4% | 1.4% | str(14) | https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Crac_des_che |
| `lat` | 97.7% | 97.7% | float(952), int(6) | 37.914 / 33.5 / 36.203 |
| `leaders` | 1.1% | 1.1% | str(11) | Godefroy de Bouillon, Raymond de Toulouse, Bohemond, Tancred / Raymond |
| `location` | 82.7% | 82.7% | str(811) | Diyarbakır / Şam (Suriye) / Antakya |
| `lon` | 97.7% | 97.7% | float(958) | 40.231 / 36.3 / 36.16 |
| `name` | 12.5% | 12.5% | str(123) | Diyarbakır / Şam (Suriye) / Antakya |
| `name_ar` | 3.5% | 3.5% | str(34) | ابن الأثير / المقريزي / أسامة بن منقذ |
| `name_en` | 4.6% | 4.6% | str(45) | Ibn al-Athir / al-Maqrizi / Usama ibn Munqidh |
| `name_tr` | 4.6% | 4.6% | str(45) | İbn el-Esîr / el-Makrîzî / Usâme b. Münkız |
| `outcome` | 80.5% | 80.5% | str(790) | not_applicable / inconclusive / crusader_victory |
| `ownership_history` | 2.4% | 2.4% | str(24) | Mirdasids / Kurdish garrison (1031–1099) → Muslim local lords (1099–11 |
| `period` | 1.7% | 1.7% | str(17) | 1096–1229 / 1185–1466 / ~1110–1170 |
| `perspective` | 0.6% | 0.6% | str(6) | standard_chronicle / standard_chronicle / anecdotal_eyewitness |
| `place_id` | 93.1% | 93.1% | str(913) | SAL_P0001 / SAL_P0002 / SAL_P0003 |
| `record_count` | 0.6% | 0.6% | int(6) | 163 / 224 / 93 |
| `short` | 0.6% | 0.6% | str(6) | IA / MQ / US |
| `snapshots` | 0.4% | 0.4% | list(4) | <list> / <list> / <list> |
| `source_count` | 12.5% | 12.5% | int(123) | 1 / 1 / 1 |
| `source_id` | 80.5% | 80.5% | str(790) | ibn_athir / ibn_athir / ibn_athir |
| `source_short` | 80.5% | 80.5% | str(790) | IA / IA / IA |
| `sources` | 2.1% | 2.1% | list(21) | <list> / <list> / <list> |
| `title` | 80.5% | 80.5% | str(790) | Diyarbakır — Vefat (1096) / Şam (Suriye) Olayları (1097) / Haçlıların  |
