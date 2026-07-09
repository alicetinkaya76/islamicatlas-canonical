# dia-tdv-scrape — TDV İslâm Ansiklopedisi web metadata scraper (AO, H9)

**Source-producing** pipeline that fills the ADR-009 rich-mint gaps
`dia_chunks.json` lacks — **cilt+sayfa**, **Arabic title**, and **per-section
entry author (müellif)** — by politely scraping the DiA web edition
(`https://islamansiklopedisi.org.tr/<slug>`). Output is a parallel source file
`data/sources/dia_chunks_rich.json` (Path 3a); `dia_chunks.json` is **never
modified**. This unblocks **AP** (dia_works rich-mint, H10+).

> This is **not** a `run_adapter.py` adapter. It emits no canonical records; it
> makes network requests (which the `extract.py` contract forbids) and produces
> a *source*, not `data/canonical/*`. It lives in the adapter tree for ADR-006
> locality only. `target_namespaces` is empty on purpose so `run_adapter.py`
> refuses it. Run it via `scrape.py`.

## Compliance — read first (ADR-014)

`robots.txt` is `Allow: /`, but the İSAM **Kullanım Şartları** forbid
reproduction/işleme/derleme without **express written permission** (citation
alone is insufficient). This pipeline therefore runs **only under the İSAM
written permission** recorded in
[`docs/decisions/ADR-014-tdv-scraping-compliance.md`](../../../docs/decisions/ADR-014-tdv-scraping-compliance.md).
The permission's formal document reference is `needs_human_review` in ADR-014
until attached; **do not publish** the derived dataset before it is.

Politeness (enforced by `scrape.py`): ≤1 request / 2 s, single-threaded,
identifying User-Agent (project + ORCID + contact), conditional GET,
`Retry-After` honored, SIGINT → checkpoint + graceful stop. Raw HTML is
archived **gzipped, gitignored** (`data/sources/dia_html/`) for re-parse; the
scraped **body text is never persisted** to the rich file or canonical store —
the narrative already exists as `dia_chunks.t`.

## Files

| File | Role |
|------|------|
| `parse.py` | Pure, deterministic HTML → fields. No network, no schema. Unit-tested offline (`tests/integration/test_dia_tdv_scrape_parse.py`) against synthetic fixtures. |
| `scrape.py` | Polite, resumable CLI: fetch → `parse` → `verify` → archive → checkpoint; `--assemble` projects the sidecar to the rich file. |
| `manifest.yaml` | Adapter metadata (source-producing; politeness + verification config). |
| `tests/fixtures/*.html` | Synthetic DiA-shaped HTML (fake content; no copyrighted material). |

## DOM contract (confirmed H9 Stage 2a, 9-slug live sample)

- URL: root-level `/<slug>`, slug == `dia_chunks.s` (the `/madde/<slug>` guess 404s).
- `<h1>` = Turkish title (== `chunk.n`); `div.arabic_title` = Arabic title (== `chunk.a`).
- `div.article-part[id]` — one per section; id `_2-turk-tarihi` encodes the section.
  Each part carries its **own** `.ak-muellif span.val` (author), its own
  `"N. cildinde, M numaralı sayfa"` citation, `Baskı Tarihi: YYYY`, and
  `.m-content` (narrative). Multi-section maddes → author is a **list**.

## Verification (Stage 2a finding)

The scraped page *contains* `dia_chunks.t` but is longer (footnotes,
bibliography), so a symmetric edit ratio understates a correct fetch. The gate
is **token coverage** of `chunk.t` into the scraped body ≥ **0.95**, plus
`h1 == chunk.n` and `arabic == chunk.a`. Any failure → `verify.flags` → the
record is marked `review`, never silently accepted.

## Usage

```bash
# pilot / smoke (first N distinct slugs, or explicit)
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --limit 50
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --slugs hassaf,abaka,gazzali

# full self-resuming run (~8,093 distinct slugs ≈ 4.5 h @ 2 s) — overnight launcher:
bash pipelines/adapters/dia_tdv_scrape/run_bulk.sh    # caffeinate + nohup + log
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --all   # (equivalent, foreground)

# monitor / stop / resume
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --status   # done/remaining/coverage
pkill -INT -f dia_tdv_scrape/scrape.py                         # graceful stop; re-run to resume
# resume is automatic (completed slugs skipped); --refetch forces re-fetch

# project checkpoint → data/sources/dia_chunks_rich.json
python3 pipelines/adapters/dia_tdv_scrape/scrape.py --assemble
```

Scope note: **8,093** distinct slugs (not 19,742 chunks — that is the finer
chunk count). Progress/rich/HTML artifacts are gitignored and regenerable.

## Open items (carried to later stages)

- ADR-014 permission **document reference** (`needs_human_review`).
- Rich-file author modeling (person vs contributor namespace) is **deferred to
  AP/H10+**; AO captures the raw byline list only (proposal open Q3/Q4).
- `≥95 %` coverage gate is exercised at scale by the **2c pilot**.
