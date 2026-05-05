#!/usr/bin/env python3
"""
H6 Stream 3 — Resolver seed-path diagnostic.

Stream 3 ana riski: 9 H5 seed'i corpus key'i ile birebir eşleşmesine
rağmen Tier 1'e değil Tier 2 / Tier 4'e gitti. Bu, resolver'ın
openiti_qid_seed.json'ı T1 fast-path olarak kullanmadığını gösterir.
Stream 3'ten önce bu davranışı doğrulamak gerekir, aksi takdirde
seed file'a 25 yeni entry eklemek metric'i değiştirmeyebilir.

Bu script üç şeyi inceler:

  1. Mevcut openiti_qid_seed.json içeriği vs gerçek corpus
     key'leri (mismatched seeds raporlanır).
  2. Mevcut openiti_author_resolution.json'da seed-key'leri olan
     entry'lerin tier dağılımı (eğer hepsi T2/T4'e gidiyorsa
     resolver seed'i kullanmıyor).
  3. Canonical person store'da QID alanı varlığı (T1 mantığı QID
     karşılaştırmasına dayanıyorsa, person'larda QID yoksa T1
     hiçbir zaman tetiklenemez).

Usage (repo root'tan):

    python pipelines/_lib/diagnose_seed_path.py

Çıktıda "DIAGNOSIS" bölümü doğrudan ne yapılması gerektiğini söyler.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DEFAULT_SEED = Path("data/sources/openiti_qid_seed.json")
DEFAULT_RESOLUTION = Path("data/_state/openiti_author_resolution.json")
DEFAULT_PERSON_DIR = Path("data/canonical/person")
DEFAULT_CORPUS_AUTHORS = Path("data/sources/openiti/corpus_authors.json")  # adjust if path differs


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def diag_seed_keys_in_corpus(seeds: dict, corpus_keys: set[str]) -> dict:
    """How many seed keys map to a real OpenITI author id?"""
    in_corpus = {k for k in seeds if k in corpus_keys}
    not_in_corpus = {k for k in seeds if k not in corpus_keys}
    return {
        "seed_total": len(seeds),
        "in_corpus": sorted(in_corpus),
        "not_in_corpus": sorted(not_in_corpus),
        "in_corpus_count": len(in_corpus),
        "not_in_corpus_count": len(not_in_corpus),
    }


def diag_seed_tier_distribution(seeds: dict, resolution: dict) -> dict:
    """For each seed-key that's in the resolver output, what tier did it get?"""
    out: dict = {"per_seed": {}, "tier_counts": Counter()}
    for k in seeds:
        if k in resolution:
            t = resolution[k].get("tier")
            reason = resolution[k].get("reason", "")
            out["per_seed"][k] = {"tier": t, "reason": reason}
            out["tier_counts"][str(t)] += 1
        else:
            out["per_seed"][k] = {"tier": None, "reason": "key_not_in_resolution_output"}
            out["tier_counts"]["missing"] += 1
    out["tier_counts"] = dict(out["tier_counts"])
    return out


def diag_canonical_person_qids(person_dir: Path, sample_size: int = 200) -> dict:
    """Sample a few hundred canonical person records, see if any carry QIDs."""
    if not person_dir.exists():
        return {"error": f"person dir not found: {person_dir}"}
    files = sorted(person_dir.glob("iac_person_*.json"))[:sample_size]
    have_qid = 0
    have_authority_xref = 0
    examples_with_qid: list[str] = []
    for fp in files:
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        ax = d.get("authority_xref") or []
        if ax:
            have_authority_xref += 1
            for entry in ax:
                if isinstance(entry, dict) and entry.get("authority") == "wikidata":
                    have_qid += 1
                    if len(examples_with_qid) < 3:
                        examples_with_qid.append(d.get("@id"))
                    break
    return {
        "sample_size": len(files),
        "have_authority_xref": have_authority_xref,
        "have_wikidata_qid": have_qid,
        "examples_with_qid": examples_with_qid,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stream 3 seed-path diagnosis.")
    parser.add_argument("--seed-path", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--resolution-path", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--person-dir", type=Path, default=DEFAULT_PERSON_DIR)
    parser.add_argument("--corpus-authors-path", type=Path, default=DEFAULT_CORPUS_AUTHORS)
    args = parser.parse_args(argv)

    print("=" * 70)
    print("H6 Stream 3 diagnostic: why is OpenITI Tier 1 == 0?")
    print("=" * 70)
    print()

    # --- Step 1: load seeds, resolution, corpus author keys
    seeds = _load_json(args.seed_path)
    if not isinstance(seeds, dict):
        print(f"FATAL: seed file shape unexpected: {type(seeds).__name__}", file=sys.stderr)
        return 2

    if not args.resolution_path.exists():
        print(
            f"FATAL: resolution file not found: {args.resolution_path}\n"
            f"Run the resolver once before diagnosing.",
            file=sys.stderr,
        )
        return 2
    resolution = _load_json(args.resolution_path)

    # corpus_authors_path is best-effort; if it doesn't exist, fall back to
    # the resolution file's keys (every author the resolver saw)
    corpus_keys: set[str]
    if args.corpus_authors_path.exists():
        ca = _load_json(args.corpus_authors_path)
        if isinstance(ca, dict):
            corpus_keys = set(ca.keys())
        elif isinstance(ca, list):
            corpus_keys = set(
                item.get("author_id") if isinstance(item, dict) else item
                for item in ca
            )
            corpus_keys.discard(None)
        else:
            corpus_keys = set()
        print(f"[step1] corpus_authors_path = {args.corpus_authors_path} ({len(corpus_keys)} authors)")
    else:
        corpus_keys = set(resolution.keys()) if isinstance(resolution, dict) else set()
        print(f"[step1] corpus_authors_path missing; falling back to resolution keys ({len(corpus_keys)} authors)")
    print()

    # --- Step 2: seed-key vs corpus
    print("[step2] Seed key membership in corpus")
    s2 = diag_seed_keys_in_corpus(seeds, corpus_keys)
    print(f"  seed_total:           {s2['seed_total']}")
    print(f"  in_corpus_count:      {s2['in_corpus_count']}")
    print(f"  not_in_corpus_count:  {s2['not_in_corpus_count']}")
    if s2["not_in_corpus"]:
        print(f"  NOT_IN_CORPUS examples: {s2['not_in_corpus'][:5]}")
    print()

    # --- Step 3: tier distribution for in-corpus seeds
    print("[step3] Resolver tier outcome for seed-keyed authors")
    s3 = diag_seed_tier_distribution(seeds, resolution if isinstance(resolution, dict) else {})
    print(f"  tier_counts: {s3['tier_counts']}")
    for k, v in s3["per_seed"].items():
        if v["tier"] is not None:
            print(f"    {k:35s} tier={v['tier']}  ({v['reason'][:55]})")
    print()

    # --- Step 4: canonical persons with QID
    print("[step4] Canonical person store: do any persons carry QIDs?")
    s4 = diag_canonical_person_qids(args.person_dir)
    if "error" in s4:
        print(f"  ERROR: {s4['error']}")
    else:
        print(f"  sampled:                  {s4['sample_size']}")
        print(f"  have_authority_xref:      {s4['have_authority_xref']}")
        print(f"  have_wikidata_qid:        {s4['have_wikidata_qid']}")
        if s4["examples_with_qid"]:
            print(f"  examples_with_qid:        {s4['examples_with_qid']}")
    print()

    # --- Diagnosis
    print("=" * 70)
    print("DIAGNOSIS")
    print("=" * 70)
    print()

    tier_counts = s3["tier_counts"]
    tier_1_hits = tier_counts.get("1", 0)
    seeds_in_corpus = s2["in_corpus_count"]

    if tier_1_hits >= max(1, seeds_in_corpus // 2):
        print("✓ The resolver IS using openiti_qid_seed.json as a Tier 1 fast-path.")
        print("  Adding more seed entries WILL increase Tier 1 count.")
        print("  → Stream 3 path: just add more seeds and re-resolve.")
    elif seeds_in_corpus > 0 and tier_1_hits == 0:
        print("✗ DIAGNOSIS: Resolver is NOT using the seed file as a Tier 1 fast-path.")
        print(
            f"  {seeds_in_corpus} seed keys are in corpus, but ZERO of them got Tier 1."
        )
        print(
            "  Adding more seed entries alone will NOT lift the Tier 1 metric."
        )
        print()
        print("  Likely cause + fix options:")
        print("    (A) Resolver only consults the seed for QID-to-canonical-person")
        print("        match. Canonical persons need authority_xref entries with")
        print("        wikidata QIDs first. Step4 above tells you whether that's")
        print("        the bottleneck.")
        print("    (B) Resolver doesn't consult openiti_qid_seed.json at all.")
        print("        Grep the resolver source for the filename to confirm:")
        print("            grep -rn 'openiti_qid_seed' pipelines/")
        print("    (C) Resolver consults the seed but only for Tier 3 (a separate")
        print("        path), and Tier 3 is currently disabled or unimplemented.")
        print()
        print("  → Stream 3 path: investigate resolver code BEFORE adding more")
        print("    seeds. Then either implement Option A (enrich canonical")
        print("    persons with QIDs from seed) or Option B/C (patch resolver to")
        print("    use seeds as Tier 1 fast-path).")
    else:
        print("⚠ Inconclusive — too few seed keys are in corpus to draw conclusion.")
        print(f"  in_corpus = {seeds_in_corpus}, tier_1 = {tier_1_hits}")
        print("  Apply the H6 corrected seed file (data/sources/openiti_qid_seed.json")
        print("  from this deliverable) and re-run this diagnostic.")

    print()

    if s4.get("have_wikidata_qid", 0) == 0 and tier_1_hits == 0:
        print("Additional finding:")
        print("  Step 4 found ZERO canonical persons carrying wikidata QIDs in")
        print("  authority_xref. If the resolver's Tier 1 logic compares QIDs")
        print("  between seed file and canonical persons, T1 is structurally")
        print("  unreachable. This is a hard blocker for AE acceptance metric.")
        print()
        print("  Fix path: Either enrich canonical persons with QIDs (separate")
        print("  pipeline; H6+) OR patch the resolver to mint a NEW canonical")
        print("  person with the seed's QID when there's no existing T2 match")
        print("  (smaller patch, achievable in H6 if Stream 3 is extended).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
