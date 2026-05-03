# GitHub Kurulum Rehberi

Bu doküman `alicetinkaya76/islamicatlas-canonical` private repo'sunu sıfırdan kurar, Fatıma'ya erişim verir ve Phase 0 iş akışını yapılandırır.

**Tahminî süre:** 20-30 dakika  
**Yapan:** Dr. Ali Çetinkaya (ilk kurulum — sadece bir kez)

---

## 1. Private Repo Oluşturma (2 dk)

### Web arayüzü ile

1. https://github.com/new adresine git
2. Aşağıdaki alanları doldur:

| Alan | Değer |
|---|---|
| **Owner** | `alicetinkaya76` |
| **Repository name** | `islamicatlas-canonical` |
| **Description** | `Phase 0: Canonical data foundation for islamicatlas.org — Pleiades/Perseus model adapted for Islamic civilization digital humanities` |
| **Visibility** | 🔒 **Private** |
| **Initialize this repository with:** | Hiçbir kutuyu işaretleme — bizim kendi README, LICENSE ve .gitignore dosyalarımız var |

3. `Create repository` tıkla

---

## 2. Yerel Paketi Push'lama (3 dk)

Zip paketini açtığın yere gir ve:

```bash
cd /path/to/islamicatlas-canonical

# Git init
git init
git branch -M main

# Kullanıcı bilgilerin (eğer global ayarlamadıysan)
git config user.name "Ali Çetinkaya"
git config user.email "senin@mail.com"

# İlk commit
git add .
git status         # Ne eklendiğini kontrol et
git commit -m "feat: Phase 0 kickoff package (v0.1.0)

- Master plan and ADR-001 (canonical + attestation model)
- 8 canonical JSON schemas (place, person, work, event, dynasty,
  route, source, attestation)
- Week 1 audit script with example output (47 legacy layers scanned)
- Fatıma onboarding + first meeting agenda
- Dual license (MIT code + CC-BY-4.0 data/docs)"

# Remote'u bağla
git remote add origin git@github.com:alicetinkaya76/islamicatlas-canonical.git

# Push
git push -u origin main
```

**Not:** SSH yerine HTTPS kullanıyorsan:
```bash
git remote add origin https://github.com/alicetinkaya76/islamicatlas-canonical.git
```

---

## 3. Repo Ayarları (5 dk)

### 3.1 Branch protection

Repo sayfasında: **Settings** → **Branches** → **Add branch protection rule**

| Ayar | Değer |
|---|---|
| **Branch name pattern** | `main` |
| **Require a pull request before merging** | ✅ |
| **Require approvals** | ✅ (1 approval) |
| **Dismiss stale pull request approvals when new commits are pushed** | ✅ |
| **Require conversation resolution before merging** | ✅ |
| **Require status checks to pass before merging** | ✅ (şimdilik boş, CI kurulunca işaretlenir) |
| **Require linear history** | ✅ (merge commit yerine squash/rebase) |
| **Do not allow bypassing the above settings** | ✅ (includes administrators) |
| **Restrict who can push to matching branches** | Boş bırak |

Bu en son maddeyi (`includes administrators`) işaretlemek disiplin için önemli — sen dahil kimse `main`'e doğrudan push yapamayacak. İkiniz de PR açacaksınız.

### 3.2 General ayarlar

**Settings** → **General**:

| Ayar | Durum |
|---|---|
| **Wikis** | ❌ kapalı (docs/ kullanıyoruz) |
| **Issues** | ✅ açık |
| **Sponsorships** | ❌ kapalı |
| **Discussions** | ✅ açık (paper draft, tartışma için) |
| **Projects** | ✅ açık (kanban için) |
| **Preserve this repository** | ✅ (Arctic Code Vault değil, GitHub'ın kendi archive'i) |
| **Allow forking** | ❌ kapalı (private) |
| **Pull Requests → Allow merge commits** | ❌ |
| **Pull Requests → Allow squash merging** | ✅ (default) |
| **Pull Requests → Allow rebase merging** | ✅ |
| **Pull Requests → Automatically delete head branches** | ✅ |

---

## 4. Fatıma'ya Erişim Verme (3 dk)

Fatıma'nın GitHub kullanıcı adı gerekli. İlk toplantıdan önce veya toplantı başında kendisinden al.

**Settings** → **Collaborators** → **Add people**

1. Fatıma'nın GitHub kullanıcı adını veya email'ini gir
2. Rol seç: **Maintain**
   - `Maintain` onun için doğru rol: issue/PR yönetir, repo ayarlarını sınırlı şekilde değiştirebilir, ama destructive aksiyonlar (repo silme, visibility değiştirme) yapamaz
   - `Admin` ver**me** — gerek yok
3. **Add to this repository**
4. Fatıma email bildirimi alacak, accept etmesi lazım

### Neden `Maintain` rolü?

| Rol | İzinler | Risk |
|---|---|---|
| Read | Okuma | Çok az iş yapabilir |
| Triage | Issue/PR triage | Kod push edemez |
| Write | Push + PR yönetim | Repo ayarı değiştiremez |
| **Maintain** | Write + label/milestone yönetim + topic editing | **ideal — destructive olmayan tam yetki** |
| Admin | Full access | Repo silebilir, gereksiz risk |

---

## 5. Labels (5 dk)

**Issues** → **Labels** → **New label** ile aşağıdakileri oluştur. Default label'ları (`bug`, `enhancement` vs.) tutabilirsin veya silebilirsin.

### Phase etiketleri (renk: mavi tonları)

| Label | Renk (hex) | Açıklama |
|---|---|---|
| `phase0-w1` | `#0366d6` | Week 1 — Audit & Inventory |
| `phase0-w2` | `#0353c1` | Week 2 — Canonical Schema |
| `phase0-w3-4` | `#0240a0` | Week 3-4 — Entity Resolution |
| `phase0-w5` | `#022d80` | Week 5 — Canonical Store + ETL |
| `phase0-w6` | `#021b60` | Week 6 — API + Derivatives |
| `phase0-w7-8` | `#010a30` | Week 7-8 — Search + Tests + Zenodo |

### Tür etiketleri (renk: yeşil/sarı tonları)

| Label | Renk | Açıklama |
|---|---|---|
| `type:audit` | `#c2e0c6` | Veri tarama, rapor |
| `type:schema` | `#0e8a16` | Canonical şema işi |
| `type:er` | `#fbca04` | Entity resolution |
| `type:etl` | `#d4c5f9` | Migration, data load |
| `type:api` | `#1d76db` | FastAPI endpoints |
| `type:infra` | `#5319e7` | Docker, DB, CI/CD |
| `type:docs` | `#bfd4f2` | Dokümantasyon |
| `type:adr` | `#ededed` | Architecture decision |

### Durum etiketleri (renk: sarı/kırmızı)

| Label | Renk | Açıklama |
|---|---|---|
| `needs-discussion` | `#d93f0b` | Toplantıda konuşulmalı |
| `blocked` | `#b60205` | Başka iş beklenir |
| `good-first-issue` | `#7057ff` | Fatıma'nın ilk PR'ına uygun |
| `decision-needed` | `#e99695` | Ali'nin domain kararı lazım |

### Hızlı yol: API ile bulk create

Yukarıdakileri tek tek tıklayarak eklemek sıkıcı. GitHub CLI ile:

```bash
# gh CLI kurulu olmalı: brew install gh (macOS) / winget install GitHub.cli (Windows)
gh auth login
cd /path/to/islamicatlas-canonical

# Phase labels
gh label create "phase0-w1" --color "0366d6" --description "Week 1 — Audit & Inventory"
gh label create "phase0-w2" --color "0353c1" --description "Week 2 — Canonical Schema"
gh label create "phase0-w3-4" --color "0240a0" --description "Week 3-4 — Entity Resolution"
gh label create "phase0-w5" --color "022d80" --description "Week 5 — Canonical Store + ETL"
gh label create "phase0-w6" --color "021b60" --description "Week 6 — API + Derivatives"
gh label create "phase0-w7-8" --color "010a30" --description "Week 7-8 — Search + Tests"

# Type labels
gh label create "type:audit" --color "c2e0c6" --description "Veri tarama, rapor"
gh label create "type:schema" --color "0e8a16" --description "Canonical şema işi"
gh label create "type:er" --color "fbca04" --description "Entity resolution"
gh label create "type:etl" --color "d4c5f9" --description "Migration, data load"
gh label create "type:api" --color "1d76db" --description "FastAPI endpoints"
gh label create "type:infra" --color "5319e7" --description "Docker, DB, CI/CD"
gh label create "type:docs" --color "bfd4f2" --description "Dokümantasyon"
gh label create "type:adr" --color "ededed" --description "Architecture decision"

# Status labels
gh label create "needs-discussion" --color "d93f0b" --description "Toplantıda konuşulmalı"
gh label create "blocked" --color "b60205" --description "Başka iş beklenir"
gh label create "good-first-issue" --color "7057ff" --description "Fatıma'nın ilk PR'ına uygun"
gh label create "decision-needed" --color "e99695" --description "Ali'nin domain kararı lazım"
```

---

## 6. Milestones (2 dk)

**Issues** → **Milestones** → **New milestone**

| Milestone | Due date (önerilen) | Description |
|---|---|---|
| `Week 1: Audit & Inventory` | +1 hafta | Veri kalitesi envanteri, canonical scope kararı |
| `Week 2: Canonical Schema` | +2 hafta | Pydantic modelleri, vocab, 3 ADR |
| `Week 3-4: Entity Resolution` | +4 hafta | ER pipeline, verified gold concordance |
| `Week 5: Canonical Store + ETL` | +5 hafta | PostgreSQL canlı, 5+ katman migrate |
| `Week 6: API + Derivatives` | +6 hafta | FastAPI live, frontend canonical'dan besleniyor |
| `Week 7-8: Search + Tests + Zenodo` | +8 hafta | Typesense live, regression green, DOI |

Due date'leri ilk toplantıda kesinleştir.

---

## 7. GitHub Projects (Kanban) (3 dk)

**Projects** (repo sekmesinden veya https://github.com/users/alicetinkaya76/projects/new)

1. **New project** → **Board** template
2. **Name:** `islamicatlas-canonical — Phase 0`
3. **Visibility:** Private
4. Kolonlar:
   - `📋 Backlog` (yeni issue'lar)
   - `🎯 This Week` (haftalık hedef)
   - `🚧 In Progress` (aktif iş)
   - `👀 Review` (PR açılmış, bekleyen)
   - `✅ Done` (merge edilmiş)
5. **Settings** → Repo'yu bağla: `alicetinkaya76/islamicatlas-canonical`
6. **Workflows** → `Auto-add to project`: yeni issue'lar otomatik Backlog'a düşsün

---

## 8. İlk Issue'ları Açma (5 dk)

Toplantıdan önce veya toplantıda birlikte açılabilir. Örnekler:

### Week 1 issue'ları

**Issue #1 — Week 1 audit — local run and initial findings**
- Assignee: Fatıma
- Labels: `phase0-w1`, `type:audit`, `good-first-issue`
- Milestone: Week 1
- Body:
  ```
  ## Hedef
  `scripts/week1_audit.py`'yı kendi makinende koş, çıktıyı incele, 3-5 ilgi çekici
  bulgu veya anormallik issue yorumu olarak buraya yaz.
  
  ## Adımlar
  - [ ] Repo'yu klonla
  - [ ] `pip install -r scripts/requirements.txt`
  - [ ] Ana atlas repo'sunu yan klasöre klonla
  - [ ] Audit'i koş (README'deki komut)
  - [ ] `audit_output/summary.md`'yi oku, kendi `audit_output_example/`'la karşılaştır
  - [ ] En dikkat çekici 3-5 bulguyu bu issue'ya yorum olarak yaz
  
  ## Definition of done
  Fatıma bulguları yorumladı, Ali 👍 verdi.
  ```

**Issue #2 — Canonical scope — which layers are in/out/auxiliary**
- Assignee: Ali
- Labels: `phase0-w1`, `type:docs`, `decision-needed`
- Milestone: Week 1
- Body: Audit çıktısına dayanarak 47 dosyanın her birini kategorize et: `in-scope canonical`, `auxiliary` (ör. xref sözlükleri), `backup-delete`, `defer-to-phase-1`

**Issue #3 — ADR-001 review**
- Assignee: Fatıma
- Labels: `type:adr`, `needs-discussion`
- Body: ADR-001'i oku, engineering perspektifinden soru/itiraz varsa bu issue'da tartışılsın. Onaylanırsa status `Proposed` → `Accepted` güncellenir.

### Week 2+ issue'ları

Week 1 sonunda ikiniz birlikte Week 2'yi planlarsınız. Şimdilik placeholder olarak açabilirsin.

---

## 9. Fatıma'ya İlk Davet Mesajı (taslak)

Repo hazır olunca, Fatıma'yı davet ettikten sonra ona şu mesajı gönder (WhatsApp/email):

---

> Selam Fatıma,
>
> `alicetinkaya76/islamicatlas-canonical` repo'suna seni maintainer olarak ekledim. Davetiyeyi GitHub email'inde göreceksin — kabul edince erişim açılır.
>
> İlk toplantıdan önce yapman gerekenler:
>
> 1. `docs/fatima-kickoff.md`'yi oku (sana yazdığım onboarding dokümanı)
> 2. `docs/phase0-canonical-data-foundation.md`'yi oku (master plan)
> 3. `docs/meeting-01-agenda.md`'yi oku (toplantı gündemi)
> 4. Vaktin olursa `scripts/week1_audit.py`'yı kendi makinende koş — ana atlas repo'sunun yerini `--data-dir` ile göstermen yeterli
>
> Toplantı zamanı: [tarih/saat]  
> Google Meet / Zoom: [link]
>
> Sorun olursa yaz — görüşmek üzere.
>
> Ali

---

## 10. Checklist

İlk toplantıdan önce tamamlanacaklar:

- [ ] Repo oluşturuldu (`alicetinkaya76/islamicatlas-canonical`, private)
- [ ] Local paket push'landı (`main` branch, v0.1.0 commit)
- [ ] Branch protection aktif (`main` korumalı, 1 approval required)
- [ ] Wikis/Sponsorships kapalı; Discussions açık
- [ ] Fatıma collaborator olarak eklendi (rol: Maintain)
- [ ] Fatıma daveti kabul etti
- [ ] Labels oluşturuldu (14 label — `gh label create` veya manuel)
- [ ] Milestones oluşturuldu (6 milestone)
- [ ] GitHub Project (kanban) kuruldu ve repo'ya bağlandı
- [ ] Issue #1, #2, #3 açıldı
- [ ] Davet mesajı Fatıma'ya gönderildi
- [ ] Toplantı tarihi/saati kararlaştırıldı

Toplantı sonrası güncellemeler:

- [ ] `docs/meeting-01-notes.md` commit edildi
- [ ] ADR-001 → `Accepted` güncellendi (onaylanırsa)
- [ ] Week 1 milestone due date kesinleştirildi
- [ ] Ücret/paket kararı belgelendi (özel dosya, `docs/` dışında veya encrypted)
