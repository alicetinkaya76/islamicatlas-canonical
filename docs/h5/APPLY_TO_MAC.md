# APPLY TO MAC — Hafta 5

This guide walks you through applying the Hafta 5 deliverable to the
Mac repo at `/Volumes/LaCie/islamicatlas_canonical` (commit `5fb02a7`,
github.com/alicetinkaya76/islamicatlas-canonical).

**Audience**: solo apply by Kapsül. Each step is intentionally small
and reversible (each adds files in new namespace `pipelines/adapters/
science_works/`, `pipelines/adapters/openiti_works/`,
`pipelines/integrity/{openiti_author_resolve,work_integrity,
dia_works_h5_audit}.py` — no Hafta 4 file is overwritten).

**Estimated wall-clock** for full apply + integration test: 25–40 min
(most of it is the openiti_works mint over 9,104 records, which is
~5–10 min; the rest is fast).

---

## Pre-flight

```bash
cd /Volumes/LaCie/islamicatlas_canonical
git status                              # should be clean
git log -1 --oneline                    # ?should be 5fb02a7 or later
git checkout -b hafta5-work-namespace   # new branch
```

Verify expected source files exist:

```bash
test -f data/sources/science_layer.json && echo "OK sci"
test -f /Volumes/LaCie/openiti_pipeline/enrichment/katman1/corpus_works.json && echo "OK works"
test -f /Volumes/LaCie/openiti_pipeline/enrichment/katman1/corpus_authors.json && echo "OK authors"
test -f /Volumes/LaCie/openiti_pipeline/enrichment/katman3/corpus_genres.json && echo "OK genres"
test -f data/sources/dia/dia_works.json && echo "OK dia"
```

If OpenITI files are not under `data/sources/`, either:
- (a) `cp` them to `data/sources/openiti/{corpus_works,corpus_authors,corpus_genres}.json`, or
- (b) symlink: `mkdir -p data/sources/openiti && ln -s /Volumes/LaCie/openiti_pipeline/enrichment/katman1/corpus_works.json data/sources/openiti/corpus_works.json` (and same for authors+genres).

---

## Step 1 — Unpack the deliverable

Extract `hafta5-deliverable-v1.zip` somewhere outside the repo (e.g.
`~/Downloads/hafta5-deliverable-v1`), then copy the contents in:

```bash
cd ~/Downloads/hafta5-deliverable-v1
rsync -av pipelines/ /Volumes/LaCie/islamicatlas_canonical/pipelines/
rsync -av tests/     /Volumes/LaCie/islamicatlas_canonical/tests/
rsync -av docs/      /Volumes/LaCie/islamicatlas_canonical/docs/h5/
# sample_records and sidecar_samples are illustrative only; do NOT copy
# them into data/canonical or data/_state.
```

Quick sanity check:

```bash
cd /Volumes/LaCie/islamicatlas_canonical
ls pipelines/_lib/work_canonicalize.py
ls pipelines/adapters/science_works/ pipelines/adapters/openiti_works/
ls pipelines/integrity/{openiti_author_resolve,work_integrity,dia_works_h5_audit}.py
ls tests/integration/test_work_pilot.py
```

Expected: all paths resolve.

---

## Step 2 — Smoke-import the new modules

This catches Python-level import errors before running any pipeline:

```bash
cd /Volumes/LaCie/islamicatlas_canonical
python3 -c "from pipelines._lib import work_canonicalize as wc; print('wc OK', dir(wc)[:5])"
python3 -c "from pipelines.adapters.science_works import canonicalize, extract; print('sci OK')"
python3 -c "from pipelines.adapters.openiti_works import canonicalize, extract; print('op OK')"
python3 -c "from pipelines.integrity import work_integrity, openiti_author_resolve, dia_works_h5_audit; print('integrity OK')"
```

If `from .place_canonicalize import ...` fails in `work_canonicalize.py`,
verify Hafta 3's `pipelines/_lib/place_canonicalize.py` still exists
(`has_arabic_script`, `truncate`, `try_int`, `try_float`, `now_iso`,
`assemble_note` are imported from it).

---

## Step 3 — Run science_works adapter

The runner from Hafta 4 (`pipelines/run_adapter.py` or equivalent)
should auto-discover the new manifest. If not, here is the explicit
invocation pattern:

```bash
cd /Volumes/LaCie/islamicatlas_canonical
python3 -m pipelines.run_adapter \
    --adapter pipelines/adapters/science_works/manifest.yaml \
    --recon-mode offline \
    --output data/canonical/work
```

Expected outputs:
- `data/canonical/work/iac_work_*.json` — ~220–300 new files
- `data/_state/science_works_authors_pending.json` — work_pid → [author_pid]
- `data/_state/science_works_discovery_drops.json` — concept-only entries
  (target: ≤90 entries; rest of the 129 discoveries pass the regex)
- `data/_state/science_works_orphan_works.json` — should be empty or ≤5

**Sanity check**:

```bash
ls data/canonical/work/iac_work_*.json | wc -l                 # ≥220
jq '.["@id"]' data/canonical/work/iac_work_00000001.json       # exists
jq '.authors' data/canonical/work/iac_work_00000001.json       # ["iac:person-..."]
```

---

## Step 4 — Run openiti_author_resolve pre-pass

This MUST run before openiti_works canonicalize. It produces the
resolution map that the openiti_works adapter consumes.

Optional but recommended: create `data/sources/openiti_qid_seed.json`
with curated top-author Wikidata QIDs for Tier 1. Even an empty `{}`
works — Tier 2 carries most of the weight.

```bash
cd /Volumes/LaCie/islamicatlas_canonical

# If the qid_seed file does not exist yet, create an empty one
test -f data/sources/openiti_qid_seed.json || echo '{}' > data/sources/openiti_qid_seed.json

# Optionally seed top-15 famous authors (boosts Tier 1 hits)
cat > data/sources/openiti_qid_seed.json <<'EOF'
{
  "0428IbnSina":      "Q11424",
  "0232Khwarizmi":    "Q9438",
  "0911Suyuti":       "Q300366",
  "0852IbnHajar":     "Q466993",
  "0505Ghazali":      "Q9181",
  "0204Shafii":       "Q199517",
  "0241IbnHanbal":    "Q193710",
  "0150AbuHanifa":    "Q166876",
  "0179Malik":        "Q124671",
  "0322Tabari":       "Q173637",
  "0606FakhrRazi":    "Q319082",
  "0728IbnTaymiyya":  "Q133229",
  "0751IbnQayyim":    "Q1369055",
  "0808IbnKhaldun":   "Q9682",
  "0256Bukhari":      "Q105580"
}
EOF

# First, ensure the canonical persons store is consolidated as a jsonl
# stream the resolver can read. If you already have data/canonical/persons.jsonl
# from the Hafta 4 build, skip this step.
find data/canonical/person -name "iac_person_*.json" -print0 | \
    xargs -0 -n50 cat | \
    jq -c '.' > data/canonical/persons.jsonl
wc -l data/canonical/persons.jsonl     # should match person count (~19,684)

# Run the pre-pass
python3 -m pipelines.integrity.openiti_author_resolve \
    --corpus-authors    data/sources/openiti/corpus_authors.json \
    --canonical-persons data/canonical/persons.jsonl \
    --qid-seed          data/sources/openiti_qid_seed.json \
    --out-resolution    data/_state/openiti_author_resolution.json \
    --out-minted        data/_state/openiti_minted_persons.jsonl \
    --death-ce-window   3 \
    --jaccard-threshold 0.5
```

Expected output (stdout JSON):
```json
{
  "total_authors": 3618,
  "tier_1": ~50-200,
  "tier_2": ~2200-2800,
  "tier_4": ~600-1300,
  "t1_t2_combined_pct": 70-85,
  "meets_acceptance_X": true
}
```

If `meets_acceptance_X` is false (T1+T2 < 70%), see "Tuning" at the
end of this guide.

**Critical**: Tier 4 placeholder persons are now in
`data/_state/openiti_minted_persons.jsonl`. Append them to the
canonical person store BEFORE Pass A runs, otherwise bidirectional
back-write will fail for Tier 4 author works:

```bash
# Append placeholder persons to per-record canonical store
python3 - <<'PYEOF'
import json
from pathlib import Path
src = Path("data/_state/openiti_minted_persons.jsonl")
dst_dir = Path("data/canonical/person")
dst_dir.mkdir(parents=True, exist_ok=True)
n = 0
for line in src.read_text().splitlines():
    line = line.strip()
    if not line: continue
    rec = json.loads(line)
    pid = rec["@id"]
    suffix = pid.split("-")[1]
    target = dst_dir / f"iac_person_{suffix}.json"
    if target.exists():
        # Tier 4 collision with an existing record — should not happen
        # if pid_minter was idempotent. Investigate.
        print(f"COLLISION: {pid} already in canonical store")
        continue
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    n += 1
print(f"Appended {n} Tier 4 placeholder persons.")
PYEOF
```

Also rebuild the persons.jsonl stream so Pass A sees them:

```bash
find data/canonical/person -name "iac_person_*.json" -print0 | \
    xargs -0 -n50 cat | \
    jq -c '.' > data/canonical/persons.jsonl
```

---

## Step 5 — Run openiti_works adapter

```bash
python3 -m pipelines.run_adapter \
    --adapter pipelines/adapters/openiti_works/manifest.yaml \
    --recon-mode offline \
    --output data/canonical/work
```

Expected output: `iac_work_*.json` count grows by ~9,000 (so total
becomes ~9,200–9,400 after both adapters).

**Sanity check**:

```bash
ls data/canonical/work | wc -l                  # ≥ 9,000
jq -r '.openiti_uri // "none"' data/canonical/work/iac_work_00000300.json
jq -r '.original_language' data/canonical/work/iac_work_00000300.json
```

If openiti_works adapter complains about missing
`openiti_author_resolution` sidecar, ensure Step 4 ran successfully and
the runner is loading sidecars from `data/_state/`.

---

## Step 6 — Run integrity passes

```bash
# Combine works.jsonl from both adapters' outputs
find data/canonical/work -name "iac_work_*.json" -print0 | \
    xargs -0 -n50 cat | \
    jq -c '.' > data/canonical/works.jsonl
wc -l data/canonical/works.jsonl    # ≥9,000

# Run both passes
python3 -m pipelines.integrity.work_integrity \
    --works    data/canonical/works.jsonl \
    --persons  data/canonical/persons.jsonl \
    --out-persons   data/canonical/persons.h5_post_a.jsonl \
    --out-clusters  data/_state/work_same_as_clusters.json \
    --out-works     data/canonical/works.h5_post_b.jsonl \
    --report        data/_state/work_integrity_report.json
```

Expected report shape (stdout):

```json
{
  "pass_a": {
    "works_processed": ~9300,
    "works_with_authors": ~9100-9300,
    "total_author_links": ~9100-9300,
    "bidirectional_coverage_pct": ≥95.0,
    "meets_acceptance_R": true
  },
  "pass_b": {
    "total_works_loaded": ~9300,
    "dual_gate_passed_pairs": 30-100,
    "fingerprint_match_only_pairs": 0-50,
    "cluster_count": 30-80,
    "cross_source_cluster_count": 30-80,
    "precision_proxy_dual_gate_share": ≥0.5
  }
}
```

**Now scatter back to per-record JSON files**:

```bash
# Persons (replace the existing per-record files with Pass-A-augmented versions)
python3 - <<'PYEOF'
import json
from pathlib import Path
src = Path("data/canonical/persons.h5_post_a.jsonl")
dst = Path("data/canonical/person")
n = 0
for line in src.read_text().splitlines():
    line = line.strip()
    if not line: continue
    rec = json.loads(line)
    pid = rec["@id"]; suffix = pid.split("-")[1]
    (dst / f"iac_person_{suffix}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    n += 1
print(f"Updated {n} person records.")
PYEOF

# Works (replace with Pass-B note-augmented versions)
python3 - <<'PYEOF'
import json
from pathlib import Path
src = Path("data/canonical/works.h5_post_b.jsonl")
dst = Path("data/canonical/work")
n = 0
for line in src.read_text().splitlines():
    line = line.strip()
    if not line: continue
    rec = json.loads(line)
    pid = rec["@id"]; suffix = pid.split("-")[1]
    (dst / f"iac_work_{suffix}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    n += 1
print(f"Updated {n} work records.")
PYEOF
```

---

## Step 7 — Generate Hafta 6 hand-off audit

```bash
python3 -m pipelines.integrity.dia_works_h5_audit \
    --dia-works  data/sources/dia/dia_works.json \
    --work-dir   data/canonical/work \
    --person-dir data/canonical/person \
    --out        data/_state/dia_works_h5_audit.json
```

Expected output (stdout summary): a stats block with
`confidence_band_counts`. Inspect the bands for the dia_works
distribution:

```bash
jq '.summary' data/_state/dia_works_h5_audit.json
jq '.summary.confidence_band_counts' data/_state/dia_works_h5_audit.json
```

You should see roughly:
- `low_likely_misattribution`: 5,000-15,000 entries (this is the
  raw signal; Hafta 6 will validate further)
- `no_external_match_dia_only`: largest band (DİA-unique attributions)
- `high_validated_both_sources`: small band (≤500), these are your
  most confident future mints

---

## Step 8 — Run the test suite

```bash
cd /Volumes/LaCie/islamicatlas_canonical
pytest tests/integration/test_work_pilot.py -v
```

**Expected**: 29 tests, all green. If any fail, see "Common failure
modes" below.

---

## Step 9 — Commit + push

```bash
git add pipelines/_lib/work_canonicalize.py
git add pipelines/adapters/science_works/ pipelines/adapters/openiti_works/
git add pipelines/integrity/{openiti_author_resolve,work_integrity,dia_works_h5_audit}.py
git add pipelines/integrity/__init__.py    # if missing
git add tests/integration/test_work_pilot.py
git add tests/__init__.py tests/integration/__init__.py    # if missing
git add docs/h5/

git add data/canonical/work/                # ~9,300 new files
git add data/canonical/person/iac_person_*.json   # Tier 4 placeholders + post-Pass-A persons
git add data/_state/openiti_author_resolution.json
git add data/_state/openiti_minted_persons.jsonl
git add data/_state/work_same_as_clusters.json
git add data/_state/work_integrity_report.json
git add data/_state/dia_works_h5_audit.json
git add data/_state/science_works_*.json
git add data/_state/openiti_works_*.json    # if any sidecars produced
git add data/sources/openiti_qid_seed.json

git commit -m "Hafta 5: work namespace seed (science_works + openiti_works)

- ~9,300 iac:work-* canonical records
- 3,618 OpenITI authors cross-walked (Tier 1+2+4)
- Bidirectional invariant enforced (Pass A)
- SAME-AS clustering with author dual-gate (Pass B)
- 29 acceptance tests
- Hafta 6 hand-off: dia_works_h5_audit.json"

git push origin hafta5-work-namespace
```

---

## Common failure modes

### F1 fails (work count < 9,000)

Either the openiti_works adapter didn't process all 9,104 records, or
records were rejected at write time. Check:

```bash
jq 'keys | length' data/_state/openiti_works_unresolved.json
ls data/canonical/work | wc -l
```

If `openiti_works_unresolved` is large, the resolution map didn't
cover those authors. Re-run Step 4 after verifying corpus_authors.json
is the right snapshot.

### D1/D2 fails (bidirectional < 95%)

Almost always means Pass A read stale persons.jsonl that doesn't
include Tier 4 placeholders. Verify with:

```bash
grep -c "openiti:" data/canonical/persons.jsonl   # should be ≥ Tier 4 count
```

If low, rebuild persons.jsonl per Step 4's last command.

### C1 fails (Tier 1+2 < 70%) — Tuning

Try (in order of safety):

1. Loosen `--death-ce-window` to 5 (default 3) — captures more T2 matches
2. Loosen `--jaccard-threshold` to 0.4 (default 0.5) — accepts weaker name matches
3. Add more entries to `openiti_qid_seed.json` for known top authors

If still under 70%, the OpenITI corpus_authors.json's `name_native_ar`
field may be sparse; T2 falls back to camelCase split of author_id
which is brittle.

### G3 fails (Canon SAME-AS cluster not found)

The Canon may exist in only one source, OR the title fingerprint
diverged. Inspect:

```bash
jq -r '.[] | select(.title_lat // .title_ar | tostring | test("Qanun|Kanun|Canon"; "i"))' \
    data/sources/openiti/corpus_works.json | head -5
```

If "QanunFiTibb" exists but no SAME-AS cluster, fingerprint mismatch
between sci and openiti versions. Inspect the audit:

```bash
jq '.audit_gate1_only_pairs[] | select(.title_a_tr | test("Kanun|Canon"; "i"))' \
    data/_state/work_same_as_clusters.json
```

---

## Rollback

If anything goes catastrophically wrong:

```bash
cd /Volumes/LaCie/islamicatlas_canonical
git reset --hard 5fb02a7     # Hafta 4 final state
git checkout main
git branch -D hafta5-work-namespace
```

All Hafta 5 outputs (work records, sidecars) are in directories that
the `git reset` cleans up.
