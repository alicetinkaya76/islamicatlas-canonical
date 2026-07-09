#!/bin/bash
# mac_h5_context_zip.sh
# Hafta 5 oturumuna geçmeden önce Mac'te çalıştır.
# Recon zinciri bittikten sonra (COMPLETE.txt varsa) çağır.
#
# Kullanım:
#   cd /Volumes/LaCie/islamicatlas_canonical
#   bash mac_h5_context_zip.sh
#
# Çıktı: /tmp/h5-mac-context.zip (Hafta 5 oturumuna yükle)

set -e

REPO=/Volumes/LaCie/islamicatlas_canonical
OUT=/tmp/h5-mac-context

cd "$REPO"

mkdir -p "$OUT"
mkdir -p "$OUT/source_samples"

# 1. Repo durumu
{
    echo "=== Git log (son 10) ==="
    git log --oneline -10
    echo
    echo "=== Branch + remote ==="
    git branch -vv
    echo
    echo "=== File counts ==="
    echo "person:  $(ls data/canonical/person/*.json 2>/dev/null | wc -l | tr -d ' ')"
    echo "place:   $(ls data/canonical/place/*.json 2>/dev/null | wc -l | tr -d ' ')"
    echo "dynasty: $(ls data/canonical/dynasty/*.json 2>/dev/null | wc -l | tr -d ' ')"
    echo
    echo "=== Disk usage ==="
    du -sh data/canonical/* 2>/dev/null
    echo
    echo "=== _state sidecars ==="
    ls -la data/_state/
} > "$OUT/repo-snapshot.txt"

# 2. Recon logları
if [ -d /tmp/h4-recon-logs ]; then
    cp /tmp/h4-recon-logs/*.log "$OUT/" 2>/dev/null || true
    cp /tmp/h4-recon-logs/COMPLETE.txt "$OUT/" 2>/dev/null || true
fi

# 3. Wikidata QID coverage raporu
python3 << 'PYEOF' > "$OUT/wikidata_coverage_report.txt" 2>&1
import json, glob
from collections import Counter

src_to_qid = Counter()
src_to_total = Counter()
total_with_qid = 0
total = 0

for fp in glob.glob('data/canonical/person/*.json'):
    total += 1
    try:
        with open(fp) as f:
            rec = json.load(f)
    except Exception:
        continue

    # Birincil kaynak
    primary = None
    for d in rec.get('provenance', {}).get('derived_from', []):
        sid = d.get('source_id', '')
        if sid.startswith('bosworth-nid:'):
            primary = 'bosworth'
        elif sid.startswith('science-layer:'):
            primary = 'science_layer'
        elif sid.startswith('dia:'):
            primary = 'dia'
        elif sid.startswith('el-alam:'):
            primary = 'el-alam'
        if primary:
            break
    primary = primary or 'unknown'
    src_to_total[primary] += 1

    # QID kontrolü
    has_qid = any(
        x.get('authority') == 'wikidata'
        for x in (rec.get('authority_xref') or [])
    )
    if has_qid:
        total_with_qid += 1
        src_to_qid[primary] += 1

print(f"Total person records: {total:,}")
print(f"With Wikidata QID:    {total_with_qid:,} ({100*total_with_qid/max(1,total):.1f}%)")
print()
print("Per primary source:")
print(f"  {'source':<20} {'total':>8} {'qid':>8} {'pct':>6}")
for k in sorted(src_to_total, key=lambda x: -src_to_total[x]):
    t = src_to_total[k]
    q = src_to_qid[k]
    pct = 100 * q / max(1, t)
    print(f"  {k:<20} {t:>8,} {q:>8,} {pct:>5.1f}%")
PYEOF

# 4. Acceptance test (mevcut state üzerinde)
pytest tests/integration/test_dia_pilot.py -v > "$OUT/test_dia_pilot_final.txt" 2>&1 || true

# 5. Hafta 4 doc'ları
cp HAFTA4_DELIVERABLE.md "$OUT/" 2>/dev/null || true
cp HAFTA4_PATCH_NOTES.md "$OUT/" 2>/dev/null || true
cp HAFTA4_SESSION_NOTES.md "$OUT/" 2>/dev/null || true
cp NEXT_SESSION_PROMPT_HAFTA5.md "$OUT/" 2>/dev/null || true

# 6. Source dosya listeleri (Hafta 5 work seed kararı için)
ls -la data/sources/ > "$OUT/source_samples/sources_dir_listing.txt" 2>&1
ls data/sources/dia/ > "$OUT/source_samples/dia_dir_listing.txt" 2>&1 || true
ls data/sources/dia-scholars/ > "$OUT/source_samples/dia_scholars_listing.txt" 2>&1 || true

# Science_layer'dan key_works alanına bir bakış
python3 << 'PYEOF' > "$OUT/source_samples/science_layer_key_works_preview.txt" 2>&1
import json
try:
    with open('data/sources/science_layer.json') as f:
        sl = json.load(f)
    scholars = sl.get('scholars', [])
    print(f"Scholars: {len(scholars)}")

    n_with_kw = sum(1 for s in scholars if s.get('key_works'))
    print(f"With key_works: {n_with_kw}")

    # Total work mention'ları
    total_works = sum(len(s.get('key_works') or []) for s in scholars)
    print(f"Total work mentions: {total_works}")

    print("\nFirst 5 scholar key_works:")
    for s in scholars[:5]:
        kw = s.get('key_works') or []
        nm = (s.get('name') or {}).get('en') or s.get('id')
        print(f"  {nm}: {kw[:3]}")

    # Discoveries
    discoveries = sl.get('discoveries', [])
    print(f"\nDiscoveries: {len(discoveries)}")
    if discoveries:
        print(f"First discovery shape: {list(discoveries[0].keys())}")
        print(f"Sample: {json.dumps(discoveries[0], ensure_ascii=False, indent=2)[:500]}")
except Exception as e:
    print(f"Error: {e}")
PYEOF

# 7. OpenITI / Kashf al-Zunûn varlık aramaları
{
    echo "=== OpenITI search ==="
    find ~ -iname "*openiti*" -type d 2>/dev/null | head -10
    find /Volumes/LaCie -iname "*openiti*" 2>/dev/null | head -10

    echo
    echo "=== Kashf al-Zunûn search ==="
    find ~ -iname "*kashf*" 2>/dev/null | head -10
    find /Volumes/LaCie -iname "*kashf*" 2>/dev/null | head -10
} > "$OUT/openiti_kashf_search.txt"

# 8. Zip
cd /tmp
rm -f h5-mac-context.zip
zip -rq h5-mac-context.zip h5-mac-context/

ls -lh /tmp/h5-mac-context.zip
echo
echo "✓ Mac context zip hazır: /tmp/h5-mac-context.zip"
echo "  Bu dosyayı yeni Hafta 5 Claude oturumuna yükle"
