# Phase 0b Frontend Integration Spec

**Audience**: Fatıma Zehra Nur Balcı (engineering collaborator joining
post-Phase 0a)
**Author**: Dr. Ali Çetinkaya
**Date**: 2026-05 (Hafta 6 Stream 5)
**Status**: Phase 0a (data refactor) tamamlanmak üzere; Phase 0b
(frontend integration) burada başlıyor.

---

## 1 — Repo + scope

```
islamicatlas-canonical/
├── data/
│   ├── canonical/
│   │   ├── work/         (~9,330 work record + DİA mint sonrası ~17K-30K)
│   │   ├── person/       (~21,946 person record)
│   │   ├── place/        (manuscript namespace H7+'da gelecek)
│   │   └── dynasty/
│   ├── _state/           (sidecars: cluster, audit, migration journals)
│   └── sources/          (raw input dumps + seed files)
├── pipelines/
│   ├── schemas/          (work.schema.json, person.schema.json, ...)
│   ├── adapters/         (science_works, openiti_works, dia_works)
│   ├── integrity/        (Pass A bidirectional + Pass B SAME-AS)
│   ├── migrations/       (versioned schema migrations)
│   └── _lib/             (shared utilities)
└── tests/
    └── integration/
```

**Phase 0b**'nin frontend tarafı islamicatlas.org v8'in altyapısı.
v7.8'in 13 data layer'ı bu canonical store'dan beslenecek. Fatıma'nın
ilk 2 hafta'lık scope'u: **work record + person record renderer'ı + cluster
deduplication UI**.

---

## 2 — Schema v0.2.0 (Hafta 6 Stream 4 sonrası)

Frontend code şu **3 yapısal değişikliği** bilmek zorunda:

### 2.1 — `same_as_cluster_id`: first-class field

```ts
type WorkRecord = {
  "@id": string;             // "iac:work-00000006"
  "@type": ["iac:Work"];
  labels: { ... };
  authors: string[];
  // ...
  same_as_cluster_id?: string;   // "cluster-000006" | undefined
};
```

**Behavior**:
- Bir work record `same_as_cluster_id` taşıyorsa, başka work record'larla
  aynı tarihsel eseri temsil ediyor demektir (farklı kaynaklardan farklı
  attestation'lar).
- Aynı cluster'daki diğer üyelere ulaşmak için
  `data/_state/work_same_as_clusters.json` sidecar'ından **canonical
  member'ı** ve **member listesini** oku.
- **Render önceliği**: Cluster üyesiyse, canonical member'ın metadata'sını
  primary olarak göster, diğerlerini "Also attested in:" ek listesi
  olarak.

```ts
type ClusterSidecar = {
  clusters: {
    [cluster_id: string]: {
      members: string[];       // ["iac:work-00000006", ...]
      canonical: string;       // "iac:work-00000006"
      sources_seen: string[];  // ["manual_editorial", "primary_textual"]
      shared_authors: string[];
      shared_fingerprints: string[];
    }
  };
  audit_gate1_only_pairs: Array<{ ... }>;  // signal-only, NOT canonical
};
```

> **Backwards-compat note**: H5 versiyonunda cluster info sadece
> work record'un `note` string'inde
> `"|| same_as_cluster: cluster-000006 ..."` olarak vardı. v0.2.0'dan
> sonra **structural field source-of-truth**. Geçiş süresi boyunca her
> ikisi de yazılıyor; frontend yeni field'a geçtikten sonra Pass B'den
> note line yazımı kaldırılacak (H7'de cleanup).

### 2.2 — `composition_temporal.approximation`: "before"

Persian/Arabic medieval works için ölüm yılına dayalı tahmini
composition window:

```ts
type CompositionTemporal = {
  start_ah?: number;
  end_ah?: number;
  start_ce?: number;
  end_ce?: number;
  approximation: "circa" | "before" | "exact" | "range";
};
```

`approximation: "before"` — author ölüm yılından önce yazılmıştır,
**daha kesin tarih bilinmiyor**. Frontend bunu `"~ 1699 ce'den önce"`
veya `"d. 1111 AH'dan önce"` şeklinde rendere edebilir.

> 9,104 OpenITI work'unun çoğu bu kategoride.

### 2.3 — Tier 4 author placeholders

OpenITI'den ithal edilen ~2,262 author Tier 4 placeholder olarak mint
edildi (death year + name, ama canonical scholarly attestation yok).
Person record'larda şu işaret var:

```json
{
  "@id": "iac:person-00024707",
  "labels": { "prefLabel": { "tr": "Majlisi" } },
  "provenance": {
    "record_history": [
      {
        "note": "...author resolution: tier_4_pid=iac:person-00024707; openiti-works adapter (Hafta 5)."
      }
    ]
  }
}
```

**UI hint**: Tier 4 placeholder person'ları, cardlerinde küçük bir
"Tier 4 / placeholder" badge ile göster (örn. açık-gri rozet:
"name attested but not yet linked to canonical biographical record").
Bu, kullanıcıya transparency verir; bilgi tamlığı yanılsaması yaratmaz.

Tier resolution kuralları:
- **Tier 1**: Wikidata QID match (şu an yok; Stream 3 sonrası limited)
- **Tier 2**: death+jaccard match (~1,356 author)
- **Tier 4**: placeholder mint (~2,262 author)
- (**Tier 3** mevcut implementasyonda kullanılmıyor)

### 2.4 — Wikidata QID display policy (H7 quality gate)

**Bağlam.** `data/canonical/person/*.json` dosyalarındaki `authority_xref`
listesinde 607 person record'unun Wikidata QID'i mevcut. Bu QID'lerin
büyük bir kısmı H4 OpenRefine v3 reconciliation pipeline'ından gelmiş ve
kalitesi denetlenmemiş. H7 Stage 1'de **doğrulanmış-yanlış 4 QID** flag'lendi
(Khwarizmi → Aquinas, al-Qāsim → Hz. Muhammed, Badr → modern botanist,
'Alī II → Shah Alam II). Geri kalan ~603 xref'in audit'i H8'e ertelendi.

**Phase 0b kuralı (zorunlu).** Frontend Wikidata QID'lerini şu durumlarda
**gizlemelidir**:

```ts
// Tüm authority_xref consumer kodu bu predikatı uygulamalı:
function isWikidataXrefDisplayable(entry: AuthorityXref): boolean {
  if (entry.authority !== "wikidata") return true; // bu kural sadece wikidata için
  if (entry.confidence === undefined) return false;     // kalibre edilmemiş
  if (entry.confidence < 0.85) return false;            // düşük güven
  if (entry.note?.startsWith("h7_audit_confirmed_wrong_target:")) return false;
  if (entry.reviewed === false && entry.method === "openrefine_v3") return false;
  return true;
}
```

**Sonuçları**:
- `confidence == 0.0` + `note startswith "h7_audit_confirmed_wrong_target:"`
  → **görünür Wikidata link YOK**, başka kalıntı UI da yok
  (PersonCard "Wikidata'da incele" butonu render edilmez).
- `confidence < 0.85` veya `reviewed: false` + OpenRefine kaynaklı entry'ler
  → **görünür Wikidata link YOK** (Phase 0b'de). Phase 0c'de H8 audit
  sonrası `confidence ≥ 0.85` ve `reviewed: true` olanlar açılır.
- `method == "manual"` ve `reviewed: true` ve `confidence ≥ 0.85` olanlar
  → görünür (şu an person store'da bu profile uyan ~28 record var,
  Rashidun caliphs gibi yüksek-importance figures).

**Neden bu sıkı?** Şu an UI'da görünen rastgele bir Wikidata link **yanlış
Wikipedia/Wikidata sayfasına götürebilir**. "Khwarizmi → Aquinas" tarzı
hatalar academic credibility'yi doğrudan vurur. Quality gate, Phase 0b
sonu için "0 yanlış Wikidata link sızıntısı" güvencesi sağlar. H8 audit
sonrası gate gevşetilir, daha fazla link açılır.

**Frontend test ölçütü.** PersonCard render testlerinde `iac:person-00000184`
(Khwarizmi) **wikidata link butonu içermemeli**. Storybook fixture olarak
4 H7-flagged PID kullanılabilir.

---

## 3 — File access pattern

Frontend canonical store'a 3 yoldan erişebilir:

### 3.1 — Static prebuild (önerilen)

Build time'da pipeline tüm data'yı static JSON'lara compile eder, frontend
fetch ile okur. islamicatlas.org v7'de zaten bu pattern var.

```ts
// pages/works/[id].astro veya benzer
const work = await fetch(`/api/works/${pid}.json`).then(r => r.json());
if (work.same_as_cluster_id) {
  const clusters = await fetch('/api/clusters.json').then(r => r.json());
  const cluster = clusters.clusters[work.same_as_cluster_id];
  // ... fetch other members, render together
}
```

### 3.2 — GraphQL gateway (Phase 0c+)

H7+'da. Şimdilik scope dışı.

### 3.3 — Direct file read (dev/preview)

Dev preview için `data/canonical/work/iac_work_*.json` direkt okunabilir.
Production için tavsiye edilmez (binary fetch overhead).

---

## 4 — Phase 0b deliverables (önerilen ilk 2 hafta)

| ID | Deliverable | Done when |
|---|---|---|
| F1 | `WorkCard` component (single record, no cluster) | 100 random work random sample render eder |
| F2 | `PersonCard` component (Tier 4 badge + Wikidata gate) | Tier 4 placeholder açık göster; **§2.4 Wikidata gate uygulandı** (Khwarizmi/Q9438 fixture'da link YOK) |
| F3 | `ClusterView` component | cluster-000001…000006 doğru render |
| F4 | `WorkPage` route (`/works/:pid`) | both single + cluster member case |
| F5 | Storybook fixtures | her component için 3+ story |

---

## 5 — Tools + onboarding

### 5.1 — Local dev setup

```bash
git clone <repo-url> islamicatlas-canonical
cd islamicatlas-canonical
git checkout hafta5-work-namespace        # ya da Hafta 6 sonrası ana branch
git log --oneline | head -5               # Hafta 6 commitleri görünmeli
```

```bash
# Schema validation hızlı sanity:
python pipelines/migrations/h6_001_schema_v0_2_0.py --validate-only
```

### 5.2 — Schema dokümantasyonu

`pipelines/schemas/work.schema.json` ve `person.schema.json` ile birlikte:
- `pipelines/schemas/SCHEMA_v0_2_0_PATCH.md` (Hafta 6 Stream 4) —
  v0.1.0 → v0.2.0 değişikliklerinin gerekçesi.
- `tests/integration/test_work_pilot.py` — şema invariantları.

### 5.3 — Acceptance ölçütleri

Phase 0b sonu için:
- Frontend her work record'u render edebilir, schema-conform.
- Cluster üyeleri otomatik dedup ediliyor (canonical primary, diğerleri
  alternative attestation).
- Tier 4 placeholder badge görünür ama nazik.
- 9,330 random sample dummy run hatasız.

---

## 6 — Açık konular Fatıma'nın brain dump etmesi için

- Cluster canonical member seçim kuralı (şu an heuristic): bizim için
  yeterli mi, yoksa frontend kendi kuralını mı uygulamalı?
- Tier 4 author'ın görünürlük seviyesi: arama dahil edilsin mi yoksa
  "yalnızca provenance trail için" mi?
- OpenITI manuscript URI'leri (note string'inde fold edilmiş) Phase 0c'de
  manuscript namespace açıldığında nasıl render edilecek?
- Çok dilli labels (`labels.prefLabel.{ar,tr,en}`): RTL/LTR mixed
  rendering test plan?
- Wikidata QID gating (§2.4): Phase 0b boyunca sadece manuel-verified
  yüksek-confidence link'ler görünecek; H8'de gate gevşetildiğinde UI
  contract değişir mi (yeni "verified" badge gerekir mi)?

> Bu konular Faz 0b kickoff toplantısında konuşulacak.

---

## Contact

- Schema/data sorunları: Ali (ÖrcID 0000-0002-7747-6854)
- Domain sorunları (Hassaf? Lebli? Tier 4 ne demek?): Hüseyin Gökalp
  (ÖrcID 0000-0002-7954-083X)
- Pipeline orchestration: bu repo'nun `pipelines/` dizininin git
  history'si self-explanatory; commit message'lar her aşamayı anlatır.
