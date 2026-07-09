#!/usr/bin/env python3
"""
scrape.py — polite, resumable TDV DiA madde-metadata scraper (AO, H9).

SOURCE-PRODUCING pipeline (NOT a run_adapter.py adapter — it emits no canonical
records). It fills the ADR-009 gaps that dia_chunks.json lacks — cilt+sayfa,
Arabic title, per-section entry author — into a checkpoint sidecar, and (on
--assemble) projects them to data/sources/dia_chunks_rich.json (Path 3a).

Compliance (ADR-014): İSAM written permission; robots.txt Allow:/. Polite
budget: 1 request / RATE seconds, single-threaded, identifying User-Agent,
conditional GET (If-Modified-Since / If-None-Match), Retry-After respected,
cease-on-request (SIGINT → checkpoint + graceful exit). Raw HTML is archived
gzipped under data/sources/dia_html/ (gitignored, ADR-014 §4) for re-parse;
scraped body text is NEVER persisted to the rich file or canonical store —
only factual fields (cilt, sayfa, title_ar, author).

Usage:
    # pilot / smoke
    python3 pipelines/adapters/dia_tdv_scrape/scrape.py --limit 50
    python3 pipelines/adapters/dia_tdv_scrape/scrape.py --slugs hassaf,abaka,gazzali
    # full self-resuming run (overnight) — see README for the caffeinate command
    python3 pipelines/adapters/dia_tdv_scrape/scrape.py --all
    # already-completed slugs are skipped by default; force re-fetch:
    python3 pipelines/adapters/dia_tdv_scrape/scrape.py --all --refetch
    # project the checkpoint sidecar → data/sources/dia_chunks_rich.json
    python3 pipelines/adapters/dia_tdv_scrape/scrape.py --assemble
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import signal
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from pipelines.adapters.dia_tdv_scrape import parse as P  # noqa: E402

CHUNKS_PATH = REPO_ROOT / "data" / "sources" / "dia_chunks.json"
RICH_PATH = REPO_ROOT / "data" / "sources" / "dia_chunks_rich.json"
HTML_DIR = REPO_ROOT / "data" / "sources" / "dia_html"
PROGRESS_PATH = REPO_ROOT / "data" / "_state" / "h9_scrape_progress.json"

USER_AGENT = ("islamicatlas-canonical/0.3 (+https://islamicatlas.org; "
              "ORCID 0000-0002-7747-6854; mailto:ali.cetinkaya@selcuk.edu.tr)")
DEFAULT_RATE = 2.0          # seconds between network requests (>= 1/2s budget)
CHECKPOINT_EVERY = 25       # persist progress every N processed slugs
COVERAGE_MIN = 0.95         # body-coverage verification gate (ADR-014 / 2c)

_STOP = {"flag": False}     # set by SIGINT handler → cease-on-request


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_chunks_index() -> dict:
    """slug → {'n': primary title, 'a': primary arabic, 't': aggregated body}."""
    with CHUNKS_PATH.open(encoding="utf-8") as fh:
        chunks = json.load(fh)
    by_slug = defaultdict(list)
    for c in chunks:
        by_slug[c["s"]].append(c)
    idx = {}
    for slug, cs in by_slug.items():
        cs = sorted(cs, key=lambda c: c.get("c", 0))
        prim_n = next((c["n"] for c in cs if c.get("n", "").strip()), "")
        prim_a = next((c["a"] for c in cs if c.get("a", "").strip()), "")
        idx[slug] = {"n": prim_n, "a": prim_a,
                     "t": "\n".join(c.get("t", "") for c in cs)}
    return idx


def _load_progress() -> dict:
    if PROGRESS_PATH.exists():
        with PROGRESS_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    return {"meta": {}, "slugs": {}}


def _save_progress(progress: dict) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROGRESS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(progress, fh, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, PROGRESS_PATH)   # atomic


def _select_slugs(args, chunk_index: dict) -> list:
    if args.slugs:
        return [s.strip() for s in args.slugs.split(",") if s.strip()]
    if args.slugs_file:
        return [ln.strip() for ln in Path(args.slugs_file).read_text(encoding="utf-8").splitlines()
                if ln.strip()]
    slugs = sorted(chunk_index)          # all 8,093 distinct slugs, deterministic
    if args.limit:
        slugs = slugs[:args.limit]
    return slugs


def plan_fetch(selected, progress_slugs, refetch=False):
    """Which selected slugs still need fetching (pure → enables resume tests).

    A slug is 'done' if a prior record marked it ok / review / unchanged.
    'error' records are NOT done → retried on the next run. Returns (todo, done).
    """
    done = {s for s, v in progress_slugs.items()
            if v.get("status") in ("ok", "review", "unchanged")}
    todo = [s for s in selected if refetch or s not in done]
    return todo, done


def _retry_after_seconds(ra: str | None, attempt: int) -> float:
    """Delay for a 429/503. Honors both RFC 9110 Retry-After forms —
    delta-seconds AND HTTP-date (the old parser only knew digits, so a
    date-form header fell through to exponential backoff, violating the
    manifest's respect_retry_after promise). Server-specified delays are
    honored up to 300 s; without a header, exponential backoff capped at 60 s."""
    if ra:
        if ra.strip().isdigit():
            return min(float(ra.strip()), 300.0)
        try:
            dt = parsedate_to_datetime(ra)
            delta = (dt - datetime.now(timezone.utc)).total_seconds()
            if delta > 0:
                return min(delta, 300.0)
        except (TypeError, ValueError):
            pass
    return min(float(2 ** attempt), 60.0)


class RateLimiter:
    def __init__(self, rate: float):
        self.rate = rate
        self._last = 0.0

    def wait(self):
        dt = time.time() - self._last
        if dt < self.rate:
            time.sleep(self.rate - dt)
        self._last = time.time()


def _fetch(session, slug, prior, rl):
    """Conditional GET one madde. Returns (status, html_or_None, headers)."""
    headers = {}
    if prior:
        if prior.get("etag"):
            headers["If-None-Match"] = prior["etag"]
        elif prior.get("fetched_at"):
            try:
                headers["If-Modified-Since"] = format_datetime(
                    parsedate_to_datetime(prior["fetched_at"])
                    if "," in prior["fetched_at"]
                    else datetime.fromisoformat(prior["fetched_at"]))
            except Exception:
                pass
    for attempt in range(3):
        rl.wait()
        try:
            r = session.get(P.madde_url(slug), headers=headers, timeout=30,
                            allow_redirects=True)
        except requests.RequestException as exc:
            if attempt == 2:
                return ("error", None, {"error": str(exc)[:200]})
            time.sleep(min(2 ** attempt, 8))
            continue
        if r.status_code in (429, 503):
            time.sleep(_retry_after_seconds(r.headers.get("Retry-After"), attempt))
            continue
        return (r.status_code, r.text if r.status_code == 200 else None, dict(r.headers))
    return ("error", None, {"error": "retry_exhausted"})


def _archive_html(slug: str, html: str) -> str:
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    path = HTML_DIR / f"{slug}.html.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(html)
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def _extracted(parsed):
    """Metadata-only projection of a parsed madde (NO body text; ADR-014 §4)."""
    parts = [{k: p.get(k) for k in (
        "part_id", "part_index", "total_parts", "section_slug",
        "author_raw", "cilt", "sayfa_baslangic", "sayfa_bitis", "baski_yili")}
        for p in parsed["parts"]]
    return {"title_tr": parsed["title_tr"], "title_ar": parsed["title_ar"],
            "n_parts": parsed["n_parts"], "parts": parts}


def _record(slug, parsed, verdict, status, headers, sha):
    """Metadata-only record for the checkpoint sidecar (NO body text)."""
    return {
        "status": "review" if verdict["flags"] else "ok",
        "http": status,
        "fetched_at": _now(),
        "etag": headers.get("ETag"),
        "last_modified": headers.get("Last-Modified"),
        "content_sha256": sha,
        "verify": verdict,
        "extracted": _extracted(parsed),
    }


def run_scrape(args) -> int:
    chunk_index = _load_chunks_index()
    slugs = _select_slugs(args, chunk_index)
    progress = _load_progress()
    progress.setdefault("slugs", {})
    # Spread FIRST so current-run values win (H9 Stage 3 fix: the old order
    # let stale meta from the first run shadow rate/user_agent forever).
    progress["meta"] = {**progress.get("meta", {}),
                        "adapter": "dia-tdv-scrape", "compliance": "ADR-014",
                        "rate": args.rate, "user_agent": USER_AGENT,
                        "updated": _now(), "last_run": _now()}
    todo, done = plan_fetch(slugs, progress["slugs"], args.refetch)
    print(f"[scrape] {len(slugs)} selected · {len(done)} already done · "
          f"{len(todo)} to fetch · rate={args.rate}s")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    rl = RateLimiter(args.rate)
    n_ok = n_review = n_unchanged = n_err = 0
    for i, slug in enumerate(todo, 1):
        if _STOP["flag"]:
            print("[scrape] cease-on-request — checkpointing and exiting.")
            break
        prior = progress["slugs"].get(slug)
        status, html, headers = _fetch(session, slug, prior, rl)
        if status == 304 and prior:
            prior["status"] = "unchanged"
            prior["fetched_at"] = _now()
            n_unchanged += 1
        elif status == 200 and html:
            sha = _archive_html(slug, html)
            parsed = P.parse_madde(html, slug)
            ci = chunk_index.get(slug, {})
            verdict = P.verify(parsed, ci.get("n"), ci.get("a"), ci.get("t"),
                               coverage_min=COVERAGE_MIN)
            progress["slugs"][slug] = _record(slug, parsed, verdict, status, headers, sha)
            if verdict["flags"]:
                n_review += 1
            else:
                n_ok += 1
        else:
            progress["slugs"][slug] = {"status": "error", "http": status,
                                       "fetched_at": _now(), "error": headers.get("error")}
            n_err += 1
        if i % CHECKPOINT_EVERY == 0:
            progress["meta"]["updated"] = _now()
            _save_progress(progress)
            print(f"[scrape] {i}/{len(todo)}  ok={n_ok} review={n_review} "
                  f"unchanged={n_unchanged} err={n_err}")
    progress["meta"]["updated"] = _now()
    _save_progress(progress)
    print(f"[scrape] DONE processed={n_ok + n_review + n_unchanged + n_err} "
          f"ok={n_ok} review={n_review} unchanged={n_unchanged} err={n_err}")
    print(f"[scrape] progress → {PROGRESS_PATH.relative_to(REPO_ROOT)}")
    return 0


def project_rich(progress_slugs):
    """Project the checkpoint sidecar → lean rich records (pure; Path 3a).

    Slug-keyed, metadata-only (NO scraped body text; ADR-014 §4). Only ok/review
    records are included. Returns (rich_dict, n_review_flagged).
    """
    rich = {}
    n_flagged = 0
    for slug, rec in sorted(progress_slugs.items()):
        if rec.get("status") not in ("ok", "review"):
            continue
        ex = rec.get("extracted", {})
        if rec.get("verify", {}).get("flags"):
            n_flagged += 1
        rich[slug] = {
            "title_ar": ex.get("title_ar"),
            "n_parts": ex.get("n_parts"),
            "parts": ex.get("parts", []),
            "verify": rec.get("verify", {}),
            "source": {"fetched_at": rec.get("fetched_at"), "http": rec.get("http"),
                       "content_sha256": rec.get("content_sha256"),
                       "provenance": "dia-tdv-scrape (ADR-014)"},
        }
    return rich, n_flagged


def run_assemble(args) -> int:
    """Write project_rich() → data/sources/dia_chunks_rich.json. dia_chunks.json untouched."""
    progress = _load_progress()
    rich, n_flagged = project_rich(progress.get("slugs", {}))
    RICH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RICH_PATH.open("w", encoding="utf-8") as fh:
        json.dump({"_meta": {"adapter": "dia-tdv-scrape", "compliance": "ADR-014",
                             "assembled": _now(), "n_records": len(rich),
                             "n_review_flagged": n_flagged}, "records": rich},
                  fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"[assemble] {len(rich)} records ({n_flagged} review-flagged) "
          f"→ {RICH_PATH.relative_to(REPO_ROOT)}")
    return 0


def run_reverify(args) -> int:
    """Re-parse archived gz HTML + recompute verify verdicts with the CURRENT
    parse.py logic (offline; NO network). Updates the sidecar in place. Use
    after a parse/verify refinement (e.g. Stage 2d.1 arabic-advisory) so the
    checkpoint reflects current policy without re-fetching."""
    progress = _load_progress()
    chunk_index = _load_chunks_index()
    n = n_changed = n_missing = 0
    for slug, rec in progress.get("slugs", {}).items():
        if rec.get("status") not in ("ok", "review"):
            continue
        gz = HTML_DIR / f"{slug}.html.gz"
        if not gz.exists():
            n_missing += 1
            continue
        with gzip.open(gz, "rt", encoding="utf-8") as fh:
            parsed = P.parse_madde(fh.read(), slug)
        ci = chunk_index.get(slug, {})
        verdict = P.verify(parsed, ci.get("n"), ci.get("a"), ci.get("t"),
                           coverage_min=COVERAGE_MIN)
        if rec.get("verify", {}).get("flags") != verdict["flags"]:
            n_changed += 1
        rec["verify"] = verdict
        rec["extracted"] = _extracted(parsed)
        rec["status"] = "review" if verdict["flags"] else "ok"
        n += 1
    progress.setdefault("meta", {})["reverified"] = _now()
    _save_progress(progress)
    print(f"[reverify] recomputed={n} flags_changed={n_changed} gz_missing={n_missing}")
    return 0


def run_status(args) -> int:
    """Print a progress summary from the checkpoint sidecar (no fetching).

    Handy during the ~4.5 h bulk run: shows done / remaining / coverage / flags.
    """
    import statistics
    s = _load_progress().get("slugs", {})
    universe = len(_load_chunks_index())
    counts = Counter(v.get("status") for v in s.values())
    done = sum(counts.get(k, 0) for k in ("ok", "review", "unchanged"))
    flagged = sum(1 for v in s.values() if v.get("verify", {}).get("flags"))
    covs = [v["verify"]["coverage"] for v in s.values()
            if isinstance(v.get("verify"), dict) and "coverage" in v["verify"]]
    print(f"[status] universe={universe} processed={len(s)} "
          f"done={done} remaining={universe - done}")
    print(f"[status] by_status={dict(counts)} review_flagged={flagged}")
    if covs:
        print(f"[status] coverage median={statistics.median(covs):.3f} "
              f"min={min(covs):.3f} ge0.95={sum(c >= 0.95 for c in covs)}/{len(covs)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="Fetch all distinct dia_chunks slugs (~8,093).")
    g.add_argument("--limit", type=int, help="Fetch the first N distinct slugs (smoke/pilot).")
    g.add_argument("--slugs", help="Comma-separated explicit slug list.")
    g.add_argument("--slugs-file", help="Path to a newline-delimited slug list.")
    g.add_argument("--assemble", action="store_true",
                   help="Project checkpoint sidecar → dia_chunks_rich.json (no fetching).")
    g.add_argument("--status", action="store_true",
                   help="Print progress summary from the checkpoint sidecar (no fetching).")
    g.add_argument("--reverify", action="store_true",
                   help="Re-parse archived gz HTML + recompute verify verdicts (no network).")
    ap.add_argument("--refetch", action="store_true", help="Re-fetch even completed slugs.")
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE,
                    help=f"Seconds between requests (default {DEFAULT_RATE}; never below 2).")
    args = ap.parse_args()

    if args.status:
        return run_status(args)
    if args.reverify:
        return run_reverify(args)
    if args.assemble:
        return run_assemble(args)
    if not (args.all or args.limit or args.slugs or args.slugs_file):
        ap.error("choose one of --all / --limit / --slugs / --slugs-file / --assemble / --status")
    if args.rate < DEFAULT_RATE:
        print(f"[scrape] rate {args.rate}s below budget; clamping to {DEFAULT_RATE}s.",
              file=sys.stderr)
        args.rate = DEFAULT_RATE
    return run_scrape(args)


def _on_sigint(signum, frame):
    _STOP["flag"] = True


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigint)
    raise SystemExit(main())
