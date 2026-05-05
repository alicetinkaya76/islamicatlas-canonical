"""
work_integrity.py — Two integrity passes for the work namespace (Hafta 5).

Pass A — pass_a_bidirectional:
    P0.2 hard invariant. For every work record's authors[] entry,
    ensure the corresponding person record's authored_works[] field
    contains the work PID. Idempotent set semantics: re-running the
    pass does not duplicate entries.

    Inputs:
      - works.jsonl      (concatenated output of science_works + openiti_works)
      - persons.jsonl    (Hafta 4 canonical persons + Tier 4 placeholders)
    Outputs:
      - persons.jsonl    (rewritten with authored_works[] populated)
      - integrity_report (stats dict)

Pass B — pass_b_same_as:
    Cross-source SAME-AS clustering between science_works and
    openiti_works. Two works are clustered iff BOTH:
      (1) their fingerprint_all_labels() sets share ≥1 common fingerprint
      (2) their authors[] PID sets share ≥1 common author PID

    The dual-gate strongly suppresses false-positives even though the
    fingerprint algorithm is intentionally aggressive on Latin
    transliteration variants.

    Inputs:
      - works.jsonl      (concatenated output)
    Outputs:
      - work_same_as_clusters.json   (cluster_id → metadata)
      - works.jsonl                  (rewritten with note += "Same-as ..." lines)
      - integrity_report (stats dict)

Both passes are designed to be idempotent and to run in O(N) over
their inputs.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator

from pipelines._lib import work_canonicalize as wc


# --------------------------------------------------------------------------- #
# JSONL streaming helpers
# --------------------------------------------------------------------------- #


def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _write_jsonl(records: Iterable[dict], path: Path) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1
    return count


# --------------------------------------------------------------------------- #
# Pass A — bidirectional authors ↔ authored_works
# --------------------------------------------------------------------------- #


def pass_a_bidirectional(
    *,
    works_jsonl_paths: list[Path],
    persons_jsonl_path: Path,
    output_persons_jsonl_path: Path,
    progress_every: int = 5000,
) -> dict:
    """Propagate work.authors[] → person.authored_works[].

    Step 1: Stream all works, build {person_pid: set(work_pids)} index.
    Step 2: Stream persons; for each, merge index entries with existing
            authored_works[] using set semantics; write out.
    Step 3: Detect orphans (work.authors[X] but no person X) and
            unauthored persons (person but no incoming work).

    Returns stats dict.
    """
    # Step 1 — build the index from all works
    person_to_works: dict[str, set[str]] = defaultdict(set)
    works_processed = 0
    works_with_authors = 0
    total_author_links = 0

    for path in works_jsonl_paths:
        for w in _iter_jsonl(path):
            works_processed += 1
            wid = w.get("@id")
            if not wid:
                continue
            authors = w.get("authors") or []
            if isinstance(authors, list) and authors:
                works_with_authors += 1
                for a in authors:
                    if isinstance(a, str):
                        person_to_works[a].add(wid)
                        total_author_links += 1
            if works_processed % progress_every == 0:
                print(
                    f"[pass_a] indexed {works_processed:>6} works | "
                    f"with_authors={works_with_authors} | links={total_author_links}",
                    flush=True,
                )

    # Step 2 — process persons
    persons_seen: set[str] = set()
    persons_modified = 0
    persons_unchanged = 0
    bidirectional_links_written = 0
    bidirectional_links_already_present = 0
    persons_with_zero_works = 0

    output_records: list[dict] = []

    for p in _iter_jsonl(persons_jsonl_path):
        pid = p.get("@id")
        if not pid:
            output_records.append(p)
            continue
        persons_seen.add(pid)

        existing = p.get("authored_works") or []
        # Tolerate both shapes: list of strings or list of dicts with @id
        existing_pids: set[str] = set()
        for e in existing:
            if isinstance(e, str):
                existing_pids.add(e)
            elif isinstance(e, dict) and isinstance(e.get("@id"), str):
                existing_pids.add(e["@id"])

        new_pids = person_to_works.get(pid, set())
        merged = existing_pids | new_pids

        added = merged - existing_pids
        already = existing_pids & new_pids
        bidirectional_links_already_present += len(already)
        bidirectional_links_written += len(added)

        if added:
            # Write back as sorted string list (deterministic ordering helps
            # diff review and replay testing)
            p["authored_works"] = sorted(merged)
            persons_modified += 1
        else:
            # Preserve existing authored_works as-is, even if empty
            if existing:
                # Re-emit as string list (normalize shape)
                p["authored_works"] = sorted(existing_pids)
            persons_unchanged += 1

        if not p.get("authored_works"):
            persons_with_zero_works += 1

        output_records.append(p)

    # Step 3 — detect orphans (work.authors[X] but no person X record)
    orphan_author_pids = sorted(set(person_to_works.keys()) - persons_seen)

    # Write output persons
    persons_written = _write_jsonl(output_records, output_persons_jsonl_path)

    stats = {
        "pass_name": "pass_a_bidirectional",
        "works_processed": works_processed,
        "works_with_authors": works_with_authors,
        "total_author_links": total_author_links,
        "persons_processed": len(persons_seen),
        "persons_modified": persons_modified,
        "persons_unchanged": persons_unchanged,
        "persons_with_zero_works": persons_with_zero_works,
        "bidirectional_links_written": bidirectional_links_written,
        "bidirectional_links_already_present": bidirectional_links_already_present,
        "orphan_author_pids_count": len(orphan_author_pids),
        "orphan_author_pids_sample": orphan_author_pids[:20],
        "persons_written": persons_written,
    }

    # Acceptance criterion R: ≥95% of (work, author) pairs have
    # bidirectional link. Numerator: links written or already present
    # for non-orphan authors. Denominator: total_author_links (all
    # work,author pairs across the input works).
    non_orphan_links = (
        bidirectional_links_written + bidirectional_links_already_present
    )
    if total_author_links > 0:
        stats["bidirectional_coverage_pct"] = round(
            100.0 * non_orphan_links / total_author_links, 2
        )
    else:
        stats["bidirectional_coverage_pct"] = 100.0
    stats["meets_acceptance_R"] = stats["bidirectional_coverage_pct"] >= 95.0

    return stats


# --------------------------------------------------------------------------- #
# Pass B — SAME-AS clustering with author dual-gate
# --------------------------------------------------------------------------- #


class _UnionFind:
    """Minimal disjoint-set / union-find for cluster building."""

    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            return x
        # Path compression
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        # Walk again, setting each ancestor to root
        node = x
        while self.parent[node] != root:
            nxt = self.parent[node]
            self.parent[node] = root
            node = nxt
        return root

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[ra] = rb
        return True

    def clusters(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for node in self.parent:
            root = self.find(node)
            out[root].append(node)
        return dict(out)


def _provenance_source_kind(work: dict) -> str | None:
    """Return the work's source kind (e.g. 'manual_editorial' for
    science_works, 'digital_corpus' for openiti_works), to detect cross-
    source matches vs intra-source duplicates."""
    prov = work.get("provenance") or {}
    df = prov.get("derived_from") or []
    if df and isinstance(df, list) and isinstance(df[0], dict):
        return df[0].get("source_type") or df[0].get("source_id", "").split(":", 1)[0]
    return None


def pass_b_same_as(
    *,
    works_jsonl_paths: list[Path],
    output_clusters_path: Path,
    output_works_jsonl_path: Path,
    cross_source_only: bool = True,
    progress_every: int = 5000,
) -> dict:
    """SAME-AS cluster build with dual-gate (fingerprint + author overlap).

    Args:
      cross_source_only: if True, only cluster works whose source kinds
          differ (typical use case: science_works ↔ openiti_works). If
          False, also cluster intra-source duplicates (e.g. two OpenITI
          versions of the same work) — useful for dedup but rare in
          practice.
    """
    # Pass 1 — load all works into memory (we need full record for
    # rewrite). 9K works × ~2KB/record ≈ 18MB; fits comfortably.
    all_works: list[dict] = []
    work_by_pid: dict[str, dict] = {}
    work_fps: dict[str, set[str]] = {}      # work_pid → fingerprints
    work_authors: dict[str, set[str]] = {}  # work_pid → author PIDs
    work_source: dict[str, str] = {}        # work_pid → source kind

    for path in works_jsonl_paths:
        for w in _iter_jsonl(path):
            wid = w.get("@id")
            if not wid:
                continue
            all_works.append(w)
            work_by_pid[wid] = w
            labels = w.get("labels") or {}
            fps = wc.fingerprint_all_labels(labels)
            work_fps[wid] = fps
            work_authors[wid] = set(w.get("authors") or [])
            src = _provenance_source_kind(w)
            if src:
                work_source[wid] = src
            if len(all_works) % progress_every == 0:
                print(f"[pass_b] loaded {len(all_works)} works", flush=True)

    print(f"[pass_b] total works loaded: {len(all_works)}", flush=True)

    # Pass 2 — build inverted index fingerprint → list[work_pid]
    fp_index: dict[str, list[str]] = defaultdict(list)
    for wid, fps in work_fps.items():
        for fp in fps:
            fp_index[fp].append(wid)

    # Pass 3 — for each fingerprint key with ≥2 works, evaluate dual-gate
    # for each pair and union if both gates pass.
    uf = _UnionFind()
    candidate_pairs_evaluated = 0
    fingerprint_match_only_pairs = 0     # passed gate 1 but failed gate 2
    dual_gate_passed_pairs = 0
    cross_source_filtered_pairs = 0      # eliminated by cross_source_only

    # Track gate-1-only pairs for audit (cluster candidates that the
    # author check rejected). These are valuable for human review.
    gate1_only_audit: list[dict] = []

    for fp, members in fp_index.items():
        if len(members) < 2:
            continue
        # Evaluate every pair within this fingerprint bucket
        n = len(members)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = members[i], members[j]
                candidate_pairs_evaluated += 1

                # Cross-source filter
                if cross_source_only:
                    sa = work_source.get(a)
                    sb = work_source.get(b)
                    if sa and sb and sa == sb:
                        cross_source_filtered_pairs += 1
                        continue

                # Gate 1 already passed (same fingerprint bucket).
                # Gate 2 — author overlap.
                authors_a = work_authors.get(a, set())
                authors_b = work_authors.get(b, set())
                if not (authors_a & authors_b):
                    fingerprint_match_only_pairs += 1
                    if len(gate1_only_audit) < 200:  # cap audit list
                        gate1_only_audit.append({
                            "fingerprint": fp,
                            "work_a": a,
                            "work_b": b,
                            "authors_a": sorted(authors_a),
                            "authors_b": sorted(authors_b),
                            "title_a_tr": (work_by_pid[a].get("labels", {})
                                           .get("prefLabel", {}).get("tr")),
                            "title_b_tr": (work_by_pid[b].get("labels", {})
                                           .get("prefLabel", {}).get("tr")),
                        })
                    continue

                # Both gates passed → union
                if uf.union(a, b):
                    dual_gate_passed_pairs += 1

    # Pass 4 — collect clusters with ≥2 members
    raw_clusters = uf.clusters()
    cluster_sidecar: dict[str, dict] = {}
    cluster_id_seq = 0
    work_to_cluster: dict[str, str] = {}

    for root, members in raw_clusters.items():
        if len(members) < 2:
            continue
        cluster_id_seq += 1
        cid = f"cluster-{cluster_id_seq:06d}"
        members_sorted = sorted(members)
        sources_seen = sorted({
            work_source.get(m) or "unknown" for m in members_sorted
        })
        # Pick a "canonical" representative: prefer the lowest PID from the
        # source we trust most (manual_editorial > digital_corpus).
        canonical = None
        for src_pref in ("manual_editorial", "digital_corpus", None):
            for m in members_sorted:
                if work_source.get(m) == src_pref or src_pref is None:
                    canonical = m
                    break
            if canonical:
                break

        # Compute shared fingerprints + author overlaps for audit
        shared_fps: set[str] = set()
        shared_authors: set[str] = set()
        for i, m in enumerate(members_sorted):
            for n in members_sorted[i + 1:]:
                shared_fps |= (work_fps.get(m, set()) & work_fps.get(n, set()))
                shared_authors |= (work_authors.get(m, set())
                                   & work_authors.get(n, set()))

        cluster_sidecar[cid] = {
            "members": members_sorted,
            "canonical": canonical,
            "size": len(members_sorted),
            "sources_seen": sources_seen,
            "is_cross_source": len(sources_seen) > 1,
            "shared_fingerprints": sorted(shared_fps),
            "shared_authors": sorted(shared_authors),
        }
        for m in members_sorted:
            work_to_cluster[m] = cid

    # Pass 5 — rewrite works with note line + structured cluster pointer
    # Approach: append a single note line "Same-as cluster:<cid>; members
    # iac:work-AAA, iac:work-BBB". The structured info lives in the
    # sidecar; consumers needing the cluster look up cid in the sidecar.
    works_modified = 0
    output_records: list[dict] = []
    for w in all_works:
        wid = w.get("@id")
        cid = work_to_cluster.get(wid) if wid else None
        if cid:
            cluster = cluster_sidecar[cid]
            other_members = [m for m in cluster["members"] if m != wid]
            note_line = (
                f"Same-as cluster:{cid} (size={cluster['size']}, "
                f"cross_source={cluster['is_cross_source']}); "
                f"members: {', '.join(other_members[:5])}"
            )
            existing_note = w.get("note") or ""
            note_changed = False
            if note_line not in existing_note:
                if existing_note:
                    w["note"] = existing_note + " || " + note_line
                else:
                    w["note"] = note_line
                note_changed = True
            # Structural field (v0.2.0+ schema). Source-of-truth for
            # cluster membership; backwards-compat note line above is
            # kept for pre-v0.2.0 frontend readers.
            existing_cid = w.get("same_as_cluster_id")
            if existing_cid is not None and existing_cid != cid:
                raise RuntimeError(
                    f"{wid} already in cluster {existing_cid!r}; "
                    f"refusing to overwrite with {cid!r}. "
                    f"Manual review required (work_same_as_clusters.json)."
                )
            field_changed = (existing_cid != cid)
            if field_changed:
                w["same_as_cluster_id"] = cid
            if note_changed or field_changed:
                works_modified += 1
        output_records.append(w)

    # Write outputs
    output_clusters_path.parent.mkdir(parents=True, exist_ok=True)
    with output_clusters_path.open("w", encoding="utf-8") as fh:
        json.dump({
            "clusters": cluster_sidecar,
            "audit_gate1_only_pairs": gate1_only_audit,
            "stats": {
                "candidate_pairs_evaluated": candidate_pairs_evaluated,
                "cross_source_filtered_pairs": cross_source_filtered_pairs,
                "fingerprint_match_only_pairs": fingerprint_match_only_pairs,
                "dual_gate_passed_pairs": dual_gate_passed_pairs,
                "cluster_count": len(cluster_sidecar),
            },
        }, fh, ensure_ascii=False, indent=2)

    works_written = _write_jsonl(output_records, output_works_jsonl_path)

    # Compute precision proxy: dual-gate-passed / (dual-gate + gate1-only)
    # Higher = more selective; we expect ≥0.4 since author gate is
    # strict but Pass B is conservative-by-design.
    if dual_gate_passed_pairs + fingerprint_match_only_pairs > 0:
        precision_proxy = round(
            dual_gate_passed_pairs /
            (dual_gate_passed_pairs + fingerprint_match_only_pairs),
            3,
        )
    else:
        precision_proxy = None

    # Acceptance V: SAME-AS merge precision ≥0.90 on a 30-record hand-
    # curated overlap set. We don't have that hand-curated set here; the
    # precision_proxy above is a different metric. Acceptance V will be
    # measured by a separate test in tests/integration/test_work_pilot.py.

    cross_source_clusters = sum(
        1 for c in cluster_sidecar.values() if c["is_cross_source"]
    )

    stats = {
        "pass_name": "pass_b_same_as",
        "total_works_loaded": len(all_works),
        "fingerprint_buckets_with_2plus": sum(
            1 for fp_list in fp_index.values() if len(fp_list) >= 2
        ),
        "candidate_pairs_evaluated": candidate_pairs_evaluated,
        "cross_source_filtered_pairs": cross_source_filtered_pairs,
        "fingerprint_match_only_pairs": fingerprint_match_only_pairs,
        "dual_gate_passed_pairs": dual_gate_passed_pairs,
        "cluster_count": len(cluster_sidecar),
        "cross_source_cluster_count": cross_source_clusters,
        "works_modified": works_modified,
        "works_written": works_written,
        "precision_proxy_dual_gate_share": precision_proxy,
        "audit_gate1_only_sample_count": len(gate1_only_audit),
    }

    return stats


# --------------------------------------------------------------------------- #
# CLI entry point — runs both passes in order
# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Work-namespace integrity passes (Hafta 5).")
    ap.add_argument("--works", type=Path, nargs="+", required=True,
                    help="One or more works.jsonl paths (science_works + openiti_works)")
    ap.add_argument("--persons", type=Path, required=True,
                    help="persons.jsonl input (canonical Hafta 4 + Tier 4 placeholders)")
    ap.add_argument("--out-persons", type=Path, required=True,
                    help="persons.jsonl output (with authored_works[] populated)")
    ap.add_argument("--out-clusters", type=Path,
                    default=Path("data/_state/work_same_as_clusters.json"))
    ap.add_argument("--out-works", type=Path, required=True,
                    help="works.jsonl output (with SAME-AS note lines)")
    ap.add_argument("--no-cross-source-only", action="store_true",
                    help="Allow intra-source SAME-AS clustering (default: cross-source only)")
    ap.add_argument("--report", type=Path,
                    default=Path("data/_state/work_integrity_report.json"))
    args = ap.parse_args()

    pass_a_stats = pass_a_bidirectional(
        works_jsonl_paths=args.works,
        persons_jsonl_path=args.persons,
        output_persons_jsonl_path=args.out_persons,
    )

    pass_b_stats = pass_b_same_as(
        works_jsonl_paths=args.works,
        output_clusters_path=args.out_clusters,
        output_works_jsonl_path=args.out_works,
        cross_source_only=not args.no_cross_source_only,
    )

    report = {
        "pass_a": pass_a_stats,
        "pass_b": pass_b_stats,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, indent=2))
