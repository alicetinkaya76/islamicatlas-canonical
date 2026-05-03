# Scripts

Phase 0 boyunca yazılacak tüm otomasyon scriptleri.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.9+ gerekli.

---

## `week1_audit.py`

**Amaç:** Mevcut islamicatlas `public/data/` (JSON katmanları) ve `data/` (CSV katmanları) dizinlerini sistematik tarayarak her dosya için kapsamlı bir rapor üretir.

**Bağımlılık:** yok — yalnız standart kütüphane (Python 3.9+)

**Kullanım:**

```bash
python3 week1_audit.py \
    --data-dir /path/to/islamicatlas/public/data \
    --csv-dir  /path/to/islamicatlas/data \
    --extra    /path/to/islamicatlas/public/data/city-atlas \
    --out      ./audit_output
```

Parametreler:

| Parametre | Zorunlu | Açıklama |
|---|:-:|---|
| `--data-dir` | ✅ | JSON katmanlarının olduğu dizin (`public/data`) |
| `--csv-dir` | ○ | CSV katmanları (`data/`) |
| `--extra` | ○ | Ek dizinler, birden fazla: `--extra a/ b/ c/` |
| `--out` | ○ | Çıktı dizini (varsayılan: `./audit_output`) |

**Çıktılar:**

| Dosya | İçerik |
|---|---|
| `summary.md` | Üst-düzey tablo + otomatik tespit edilen kritik bulgular |
| `summary.json` | Aynı bilgi makine okunur (Phase 1 ETL'in okuyacağı) |
| `cross_reference.md` | Mevcut xref haritası + boşluk analizi |
| `duplicates.md` | Yedek/tekrar dosya tespiti (isim kalıbı + içerik hash) |
| `<layer_name>.md` | Her katman için ayrıntılı rapor (alan profili, ID/koord/ad/tarih kapsaması) |

**Ne bulabilir (gerçek koşudan örnek):**

- Yinelenen ID'ler: `ei1_geo.json` 47 adet, `konya.json` 2 adet
- Yedek dosyalar: `salibiyyat_atlas_layer_backup.json`
- Dünya sınırları dışı koordinatlar (schema constraint ihlali)
- Çok dilli ad kapsaması (TR/AR/EN — her katmanda ne kadar?)
- Tarih alanı çeşitliliği (`date_ce`, `hd`, `dc`, `birth_year`... — standardizasyon ihtiyacı)

**Bilinen sınırlamalar:**

- `ID_KEYS` listesindeki alan adları foreign key'leri de ID olarak yakalayabilir (örn. `dynasty_id` scholars tablosunda FK'dir). Bu raporlanan "yinelenen ID" uyarıları manuel doğrulama gerektirir.
- Edge-list formatındaki yardımcı dosyalar (`dia_relations.json`, `ei1_relations.json`) entity tablosu olarak sayılamaz, 0 kayıt olarak raporlanır. Bu yapısal — hata değil.

---

## Week 2+ için planlanan scriptler

Aşağıdakiler Week 2 başlangıcında eklenecek:

- **`validate.py`** — Canonical schema'lara göre JSON dosyalarını doğrular
- **`slugify.py`** — Arapça/Osmanlı adı → URI-safe canonical slug üretir (transliterasyon + diacritic + çakışma çözümü)
- **`vocab_check.py`** — Controlled vocabulary uyumu kontrol eder (madhab, field, genre...)

Week 3-4:

- **`er_pipeline.py`** — Entity resolution (blocking + similarity + LLM tiebreaker)
- **`er_verify_ui.py`** — Streamlit tabanlı manuel doğrulama UI'ı

Week 5:

- **`etl/run.py`** — Legacy katmandan canonical store'a idempotent migration

Week 6:

- **`derivatives/build.py`** — Canonical store'dan eski `*_lite.json` format derivative'ları üretir (frontend geri uyumluluğu)

---

## Kod stili

- **Formatter:** `ruff format`
- **Linter:** `ruff check`
- **Type checker:** `mypy --strict` (yeni yazılan modüllerde)
- **Test framework:** `pytest`

CI pipeline (GitHub Actions) her PR'da bu dördünü de koşacak — bkz. (eklenecek) `.github/workflows/ci.yml`.
