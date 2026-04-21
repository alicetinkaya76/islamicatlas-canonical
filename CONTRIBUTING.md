# Contributing

Bu doküman `islamicatlas-canonical` repo'sunda gündelik çalışma protokolünü açıklar. Her iki katkı sağlayıcı (Ali + Fatıma) bu kuralları takip eder.

---

## Temel prensipler

1. **Her değişiklik PR ile:** `main`'e doğrudan push yok (branch protection zaten zorluyor).
2. **Her PR en az 1 review alır:** karşılıklı review — Fatıma'nın PR'ını Ali, Ali'nin PR'ını Fatıma onaylar.
3. **Her büyük karar ADR'ye yazılır:** `docs/decisions/` altında.
4. **Issue'suz PR olabilir** ama **önemli iş için önce issue** — tartışmanın yeri.
5. **Commit ve branch isimleri konvansiyona uyar** (aşağıda).

---

## Branch adlandırma

```
<tip>/<kısa-açıklama>
```

Tipler:
- `feat/` — yeni özellik
- `fix/` — hata düzeltme
- `docs/` — sadece doküman
- `refactor/` — davranış değişmeden kod yeniden düzenleme
- `chore/` — bağımlılık, config, build
- `test/` — test ekleme/güncelleme
- `adr/` — yeni ADR yazımı

**Örnekler:**
```
feat/er-pipeline-blocking
fix/audit-script-dict-iteration
docs/fatima-kickoff-update
refactor/schema-dir-reorganize
chore/requirements-bump-pydantic
adr/004-uri-scheme
```

---

## Commit mesajları — Conventional Commits

Format:

```
<tip>(<scope>): <kısa açıklama>

<opsiyonel uzun açıklama>

<opsiyonel footer: closes #NN, refs #NN, BREAKING CHANGE: ...>
```

Tipler `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`, `build`, `ci`.

Scope — ilgili modül (opsiyonel):
- `audit`, `schema`, `er`, `etl`, `api`, `search`, `infra`, `docs`

**İyi commit örnekleri:**

```
feat(audit): handle dict-of-dicts JSON layouts

darpislam_detail_*.json and yaqut_detail.json use ID-keyed dict
format. iter_records now detects this pattern and yields each
value as a record with the original key preserved as `_key`.

Closes #12
```

```
fix(schema): loosen person.chronology.century_ce upper bound

Was 15 (medieval cap), extended to 21 for modern Ottoman-era
biographies in al-Aʿlām that extend into the 20th century.

Refs #5
```

```
docs(setup): add gh CLI bulk label creation

Saves ~5 min of clicking when setting up a fresh clone.
```

**Kaçınılacak commit mesajları:**
- ❌ `fix`
- ❌ `update README`
- ❌ `çalışmıyor düzelttim`
- ❌ `wip`
- ❌ `final version v2 really`

---

## PR açma akışı

1. **İssue'yu seç veya aç.** Büyük iş → önce issue'da tartışma; küçük düzeltme → doğrudan PR OK.

2. **Branch oluştur:**
   ```bash
   git checkout main
   git pull
   git checkout -b feat/er-pipeline-blocking
   ```

3. **Değişikliği yap.** Küçük, odaklı commit'ler — "monster PR" yapma.

4. **Push:**
   ```bash
   git push -u origin feat/er-pipeline-blocking
   ```

5. **PR aç:** GitHub CLI veya web. PR template sana rehberlik edecek.

6. **Review iste.** Reviewer ata (diğer ekip üyesi). Labels ekle.

7. **Review feedback'e yanıt ver.** Commit ekle (force-push yerine ek commit — review izi korunur).

8. **Merge:** 1 approval geldikten sonra merge. Tercih: **squash merge** (tek commit `main`'e düşer).

9. **Branch sil:** GitHub otomatik silecek (ayar bunu sağlıyor).

---

## Review rehberi

Reviewer olarak:

### Teknik olarak bak
- Kod okunur mu?
- Testler var mı? (yeri varsa)
- Edge case düşünülmüş mü?
- Performance implication var mı?
- Security implication var mı?

### Mimari olarak bak
- ADR'lere uyuyor mu?
- Canonical model'e uyuyor mu?
- Schema değişiyorsa versiyonlama doğru mu?

### Pratik olarak bak
- README/docs güncellenmesi gerekiyor mu?
- CHANGELOG güncellenmesi gerekiyor mu?
- `requirements.txt` güncellenmesi gerekiyor mu?

### İletişim şekli

- **Onay:** `LGTM 👍` veya spesifik övgü
- **Küçük öneri:** inline yorum, `nit:` prefix ("nit: belki `parse_int` daha uygun")
- **Blok eden sorun:** `⛔ blocker:` prefix, gerekçe ile
- **Soru / anlamak istiyorum:** `❓` veya `question:` prefix
- **İdeal değil ama merge edilebilir:** "Non-blocking: ileriki PR'da şunu düşün..."

Fatıma'ya özel not: Ali'nin kodunda şüphelendiğin şey varsa **sormak** — "Bu neden böyle?" demekten çekinme. Ali'nin domain arkaplanı Python idiomatic'ten bazen uzak olabilir; senin mühendislik perspektifin tam olarak bunu yakalamak için.

Ali'ye özel not: Fatıma'nın kodunda domain hatası gördüğünde sadece `ş` koyma — **neden yanlış** olduğunu ve **doğrusunun ne** olduğunu gerekçele. İlk 2-3 review'da bu pedagojik olmalı.

---

## Kod stili

### Python

- **Formatter:** `ruff format` (konfig: `pyproject.toml`)
- **Linter:** `ruff check` — `E`, `F`, `W`, `I`, `B`, `UP`, `N`, `PL`, `RUF` kural setleri
- **Type checker:** `mypy --strict` — yeni yazılan modüllerde strict; legacy script'lerde kademeli (audit script şimdilik gevşek)
- **Docstring stili:** Google veya NumPy stili; Türkçe yorum ✅ (bu proje için Türkçe daha doğal)
- **Line length:** 100 karakter (ruff default)

### JSON / JSON Schema

- 2 space indent
- Trailing comma yok (JSON standart)
- `$schema`, `$id`, `title`, `description` her şemada zorunlu
- CIDOC-CRM veya schema.org mapping'i description'da yazılır

### Markdown

- Başlıklar ATX stili (`#`, `##`)
- Tablo alignment tutarlı
- Link'ler reference-style olmasa da olur; inline link kabul
- Türkçe yazım: `-` ile bullet (ASCII), exotic karakter yok

---

## Testing (Phase 0 boyunca geliştirilecek)

- **Week 2+:** `pytest` kurulur, `tests/` klasörü oluşur
- **Week 5+:** ETL için smoke test (kayıt sayısı, ID tekilliği)
- **Week 6+:** API integration test (`httpx` ile)
- **Week 7-8:** Regression test suite — Phase 0 öncesi frontend davranışını koruyor mu?

Şimdilik (Week 1) test yok — audit script'i stdlib kullanıyor, manuel doğrulama yeterli.

---

## Lisans ve atıf

Katkı yaptığında:
- Kod katkın **MIT** lisansı altında
- Doküman/veri katkın **CC-BY-4.0** lisansı altında

Paper'da yazarlık:
- Substantive katkı (methodology, ER pipeline, schema design) → **ikinci yazar / yazar**
- Minör katkı (docs, bug fix) → **acknowledgments** bölümü

Büyük publication kararlarında birlikte oturup tartışıyoruz.

---

## Sorular / yardım

- **Teknik soru:** issue aç, `needs-discussion` label'ı
- **Anlık soru:** WhatsApp/Slack
- **Mimari soru:** GitHub Discussions (Design kategorisi)
- **Domain sorusu (İslamic studies):** Ali'ye özel sor — WhatsApp veya issue mention `@alicetinkaya76`

---

Hoş geldin ve iyi çalışmalar.
