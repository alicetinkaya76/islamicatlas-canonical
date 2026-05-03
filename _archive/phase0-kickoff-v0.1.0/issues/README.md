# Issues — Ready to Paste

Bu klasördeki dosyalar **GitHub'da açılacak issue'ların gövdeleridir**. Her dosyanın başındaki YAML frontmatter issue title/labels/milestone/assignees bilgisini taşır.

## Kullanım (2 seçenek)

### Seçenek A: Manuel kopyala-yapıştır

1. GitHub'da **Issues** → **New Issue**
2. Template seç (opsiyonel) veya `Open a blank issue`
3. Başlığı `title:` satırından kopyala
4. Gövdeyi `---` bloğundan sonrası (yani YAML sonrası metin)
5. Labels, milestone, assignees alanlarını sağ sidebar'dan seç

### Seçenek B: GitHub CLI (toplu, hızlı)

```bash
gh auth login

# Issue #1
gh issue create \
    --title "[Phase 0 — Week 1] Week 1 audit — local run and initial findings" \
    --body-file issues/001-week1-audit.md \
    --label "phase0-w1,type:audit,good-first-issue" \
    --milestone "Week 1: Audit & Inventory" \
    --assignee <fatima-github-username>

# Issue #2
gh issue create \
    --title "[Phase 0 — Week 1] Canonical scope — which layers are in/out/auxiliary" \
    --body-file issues/002-canonical-scope.md \
    --label "phase0-w1,type:docs,decision-needed" \
    --milestone "Week 1: Audit & Inventory" \
    --assignee alicetinkaya76

# Issue #3
gh issue create \
    --title "[ADR] ADR-001 review — canonical entity + attestation model" \
    --body-file issues/003-adr-001-review.md \
    --label "type:adr,needs-discussion,phase0-w1" \
    --milestone "Week 1: Audit & Inventory" \
    --assignee alicetinkaya76 \
    --assignee <fatima-github-username>
```

**Not:** YAML frontmatter blokunu gövde olarak gönderirsen GitHub görmezden gelir — CLI body-file akışında sorun yok. Manuel kopyalıyorsan `---`'dan sonrasını al.

## Açılış sırası

1. **Issue #1** → Fatıma'ya atanır (Week 1 audit lokal koşu)
2. **Issue #2** → Ali'ye atanır (canonical scope kararı)
3. **Issue #3** → İkimize de (ADR-001 review)

## Sonraki issue'lar

Week 2 başında Fatıma ile birlikte Week 2 issue'larını açarsınız. Onlar için bu `issues/` klasöründe template yok — master plan §4 Week 2 deliverable listesi yönlendirici.
