#!/usr/bin/env python3
"""
H6 Stream 3 ; Wikidata QID verification harness.

Reads `data/sources/openiti_qid_seed.json` (or `--seed-path`) and, for
each (openiti_id → qid) entry, fetches the corresponding Wikidata
entity via the public API and reports a sanity-check verdict:

  OK         The Wikidata entity exists and its label/description
             plausibly matches the expected Islamic scholar.
  MISMATCH   The entity exists but its label/description does not
             plausibly match (e.g. the QID points to a different
             person or a different kind of entity).
  NOT_FOUND  The entity ID resolves to a deleted or redirect page.
  HTTP_ERROR Transient network/HTTP failure.

Designed to be run from the repo root:

    python pipelines/_lib/verify_seed_qids.py
    python pipelines/_lib/verify_seed_qids.py --seed-path data/sources/openiti_qid_seed.json
    python pipelines/_lib/verify_seed_qids.py --output data/_state/seed_qid_verification.json

Politeness:
    - Single-threaded; one request at a time.
    - 1 sec sleep between requests (≈ 40 reqs/min).
    - Sets a User-Agent identifying islamicatlas.org.

No external dependencies (uses urllib + json from stdlib).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = (
    "islamicatlas.org QID verification harness "
    "(Hafta 6 Stream 3) ; contact: alicetinkaya@selcuk.edu.tr"
)

# Hand-picked keywords that appear in legitimate Islamic-scholar Wikidata
# descriptions in English/Turkish/Arabic. If NONE of these tokens appear in
# the entity's description (any language), we flag it for human review.
SANITY_KEYWORDS = [
    "muslim", "islamic", "islam", "muhaddith", "mufassir", "faqih",
    "jurist", "theologian", "philosopher", "scholar", "ulama", "ulema",
    "sufi", "imam", "shaykh", "qadi", "mufti", "hadith", "fiqh",
    "tafsir", "kalam", "mufessir", "mutekellim", "hanafi", "hanbali",
    "shafi", "maliki", "shia", "shi'a", "shi'i", "shi'ite", "sunni",
    "moroccan", "andalusi", "iraqi", "syrian", "yemeni", "egyptian",
    "persian", "arab", "ottoman", "byzantine", "abbasid", "umayyad",
    "translator",
    "müslüman", "islâm", "âlim", "fakih", "filozof", "şeyh",
    "ابن", "أبو", "محدث", "فقيه", "إمام",
]


def _api_get_entity(qid: str, *, timeout: float = 15.0) -> dict | None:
    """Return parsed JSON for `wbgetentities&ids=Qxxx`, or None on 404."""
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "format": "json",
        "props": "labels|descriptions|aliases",
        "languages": "en|tr|ar|fr",
    }
    url = f"{WIKIDATA_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return data.get("entities", {}).get(qid)


def _classify(entity: dict | None, expected_label: str) -> tuple[str, dict]:
    """
    Inspect a wbgetentities entity payload and return (verdict, evidence).
    """
    if entity is None:
        return "NOT_FOUND", {"reason": "wikidata returned no entity for this id"}

    if entity.get("missing", False):
        return "NOT_FOUND", {"reason": "wikidata says missing=true"}
    if "redirects" in entity:
        # The QID redirected to another QID; reportable but not fatal
        target = entity["redirects"]["to"]
        return "MISMATCH", {
            "reason": "wikidata_redirect",
            "redirect_to": target,
        }

    # Concatenate label + description across all languages we asked for
    haystack_parts = []
    for lang_block in (entity.get("labels", {}) or {}).values():
        v = lang_block.get("value", "") if isinstance(lang_block, dict) else ""
        if v:
            haystack_parts.append(v)
    for lang_block in (entity.get("descriptions", {}) or {}).values():
        v = lang_block.get("value", "") if isinstance(lang_block, dict) else ""
        if v:
            haystack_parts.append(v)
    for lang_block in (entity.get("aliases", {}) or {}).values():
        if isinstance(lang_block, list):
            haystack_parts.extend(
                a.get("value", "") for a in lang_block if isinstance(a, dict)
            )
    haystack = " || ".join(haystack_parts).lower()

    # Sanity-check 1: at least one Islamic-scholar keyword appears
    matched_kws = [kw for kw in SANITY_KEYWORDS if kw.lower() in haystack]
    if not matched_kws:
        return "MISMATCH", {
            "reason": "no_islamic_scholar_keyword_in_labels_or_descriptions",
            "labels_seen": [
                v.get("value")
                for v in (entity.get("labels", {}) or {}).values()
                if isinstance(v, dict)
            ],
            "descriptions_seen": [
                v.get("value")
                for v in (entity.get("descriptions", {}) or {}).values()
                if isinstance(v, dict)
            ],
        }

    # Sanity-check 2: the expected label (e.g. "Ibn Hazm") shares at least
    # one significant token with the labels/aliases (≥ 4 chars to skip "ibn",
    # "abu", "al" etc.)
    expected_tokens = {
        t for t in expected_label.lower().split() if len(t) >= 4
    }
    if expected_tokens:
        haystack_tokens = set(haystack.replace(",", " ").split())
        if not (expected_tokens & haystack_tokens):
            return "MISMATCH", {
                "reason": "expected_label_tokens_not_found_in_entity",
                "expected_label": expected_label,
                "expected_tokens": sorted(expected_tokens),
            }

    return "OK", {"matched_keywords": matched_kws[:6]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify openiti_qid_seed.json entries against Wikidata."
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=Path("data/sources/openiti_qid_seed.json"),
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=Path("data/sources/openiti_qid_seed_metadata.json"),
        help="Optional metadata file with expected labels per QID.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/_state/seed_qid_verification.json"),
    )
    parser.add_argument(
        "--sleep-seconds", type=float, default=1.0,
        help="Politeness delay between API requests (default 1.0).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Optional cap on entries to verify (for testing).",
    )
    args = parser.parse_args(argv)

    seeds = json.loads(args.seed_path.read_text(encoding="utf-8"))
    if not isinstance(seeds, dict):
        print(f"FATAL: seed file is not a dict: {args.seed_path}", file=sys.stderr)
        return 2
    print(f"[verify_qids] loaded {len(seeds)} seed entries from {args.seed_path}")

    expected_labels: dict[str, str] = {}
    if args.metadata_path.exists():
        meta = json.loads(args.metadata_path.read_text(encoding="utf-8"))
        for oid, entry in meta.get("entries", {}).items():
            if isinstance(entry, dict):
                expected_labels[oid] = entry.get("label", oid)
        print(f"[verify_qids] loaded {len(expected_labels)} expected labels from metadata")

    results: dict[str, dict] = {}
    counts = {"OK": 0, "MISMATCH": 0, "NOT_FOUND": 0, "HTTP_ERROR": 0}

    items = list(seeds.items())
    if args.limit:
        items = items[: args.limit]

    for i, (oid, qid) in enumerate(items, 1):
        expected = expected_labels.get(oid, oid)
        try:
            entity = _api_get_entity(qid)
        except urllib.error.URLError as e:
            verdict = "HTTP_ERROR"
            evidence = {"reason": str(e)}
        except Exception as e:
            verdict = "HTTP_ERROR"
            evidence = {"reason": f"{type(e).__name__}: {e}"}
        else:
            verdict, evidence = _classify(entity, expected)

        counts[verdict] += 1
        results[oid] = {
            "qid": qid,
            "expected_label": expected,
            "verdict": verdict,
            **evidence,
        }
        marker = {"OK": "✓", "MISMATCH": "?", "NOT_FOUND": "✗", "HTTP_ERROR": "!"}[verdict]
        print(f"  [{i:3d}/{len(items)}] {marker} {oid:35s} {qid:10s} -> {verdict}")
        if verdict != "OK":
            print(f"          {evidence.get('reason', '')}")
        time.sleep(args.sleep_seconds)

    out_path = args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "summary": counts,
                "entries": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"[verify_qids] === SUMMARY ===")
    for verdict, n in counts.items():
        print(f"  {verdict:12s} {n}")
    print(f"[verify_qids] report written to {out_path}")
    print()

    # Exit code: 0 only if all OK; 1 if any MISMATCH/NOT_FOUND; 3 if any HTTP_ERROR
    if counts["HTTP_ERROR"]:
        return 3
    if counts["MISMATCH"] or counts["NOT_FOUND"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
