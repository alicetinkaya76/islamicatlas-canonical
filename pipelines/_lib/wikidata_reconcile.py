"""
wikidata_reconcile.py — OpenRefine Reconciliation client for Wikidata.

Public API:

    reconciler = WikidataReconciler(cache_path=..., seed_path=..., mode='auto')
    result = reconciler.reconcile(label_en='Abbasid Caliphate',
                                  context={...}, type_qid='Q164950')
    # result is None or:
    # {
    #   'authority': 'wikidata',
    #   'id': 'Q11707',
    #   'confidence': 0.97,
    #   'method': 'openrefine_v3' | 'imported_from_source',
    #   'reviewed': False,
    #   'note': '...',
    # }

Three modes:

    'live'    — always hit the API; fail loudly on network error.
    'offline' — never hit the API; use cache + bundled seed only.
    'auto'    — try API, on network error fall through to cache + seed
                (default; what the production pipeline uses).

Caching:

    SQLite at <cache_path>. Schema:
        queries(query_key TEXT PRIMARY KEY, response_json TEXT, fetched_at TEXT)
    query_key = sha256("<label>||<type_qid>||<context_digest>"). TTL 30 days
    by default.

Threshold semantics (from manifest.yaml):
    confidence >= threshold_auto_accept  → returned as a real authority_xref
    threshold_review <= confidence < auto_accept → returned with reviewed=False
                                                   AND a review-queue entry added
    confidence < threshold_review        → None returned, no entry

Note about scores: the OpenRefine endpoint returns 'score' on a 0-100 scale.
We normalize to 0-1. The 'match: true' flag is also respected; a true match
without a high score is taken as a 1.0-confidence hit.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import requests  # type: ignore
    _HAVE_REQUESTS = True
except ImportError:  # pragma: no cover
    _HAVE_REQUESTS = False


DEFAULT_API_URL = "https://wikidata.reconci.link/en/api"
DEFAULT_TTL_DAYS = 30
DEFAULT_BATCH_SIZE = 25
DEFAULT_TIMEOUT_S = 12
DEFAULT_RETRY_PAUSE_S = 2.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


class WikidataReconciler:
    """Reconciliation client with cache, seed fallback, and threshold logic."""

    def __init__(
        self,
        cache_path: Path | str,
        seed_path: Path | str | None = None,
        mode: str = "auto",
        threshold_auto_accept: float = 0.85,
        threshold_review: float = 0.70,
        api_url: str = DEFAULT_API_URL,
        ttl_days: int = DEFAULT_TTL_DAYS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        timeout_s: int = DEFAULT_TIMEOUT_S,
        verbose: bool = False,
    ):
        if mode not in ("live", "offline", "auto"):
            raise ValueError(f"mode must be live|offline|auto, got {mode!r}")
        self.cache_path = Path(cache_path)
        self.seed_path = Path(seed_path) if seed_path else None
        self.mode = mode
        self.threshold_auto_accept = float(threshold_auto_accept)
        self.threshold_review = float(threshold_review)
        self.api_url = api_url
        self.ttl = timedelta(days=ttl_days)
        self.batch_size = batch_size
        self.timeout_s = timeout_s
        self.verbose = verbose

        self._network_disabled = False  # tripped on first network failure in 'auto' mode
        self._seed: dict[str, dict] = self._load_seed()
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.cache_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queries (
              query_key   TEXT PRIMARY KEY,
              response    TEXT NOT NULL,
              fetched_at  TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

        # Per-instance counters (caller can read for reporting)
        self.counters = {
            "queries_total": 0,
            "cache_hits": 0,
            "api_hits": 0,
            "api_failures": 0,
            "seed_hits": 0,
            "auto_accept": 0,
            "review": 0,
            "no_match": 0,
        }

    # ----- public API ----------------------------------------------------

    def reconcile(
        self,
        label_en: str | None,
        context: dict | None = None,
        type_qid: str | None = None,
        source_record_id: str | None = None,
    ) -> dict | None:
        """Reconcile a single entity. Returns an authority_xref entry or None."""
        if not label_en:
            return None
        self.counters["queries_total"] += 1

        # 1) Seed lookup (fast, deterministic, no network).
        if source_record_id and source_record_id in self._seed:
            self.counters["seed_hits"] += 1
            seeded = self._seed[source_record_id]
            return self._make_xref(
                qid=seeded["qid"],
                confidence=seeded.get("confidence", 1.0),
                method="imported_from_source",
                reviewed=seeded.get("reviewed", True),
                note=seeded.get("note", "Curated offline seed (manually verified)."),
            )

        # 2) Cache lookup.
        query_key = self._query_key(label_en, type_qid, context)
        cached = self._cache_get(query_key)
        if cached is not None:
            self.counters["cache_hits"] += 1
            return self._interpret_response(cached, label_en)

        # 3) Live API (unless mode=offline or already disabled).
        if self.mode != "offline" and not self._network_disabled:
            try:
                response = self._call_api_single(label_en, type_qid)
                self._cache_put(query_key, response)
                self.counters["api_hits"] += 1
                return self._interpret_response(response, label_en)
            except _NetworkUnavailable:
                self.counters["api_failures"] += 1
                if self.mode == "live":
                    raise
                # 'auto' mode: stop trying for the rest of this run.
                self._network_disabled = True
                if self.verbose:
                    print(
                        "[wikidata_reconcile] live API unreachable; "
                        "falling back to cache + seed only.",
                        file=sys.stderr,
                    )
            except Exception as exc:  # pragma: no cover
                self.counters["api_failures"] += 1
                if self.mode == "live":
                    raise
                if self.verbose:
                    print(f"[wikidata_reconcile] API error: {exc}", file=sys.stderr)
                self._network_disabled = True

        # 4) No match found anywhere.
        self.counters["no_match"] += 1
        return None

    def reconcile_batch(
        self,
        items: Iterable[tuple[str, str, str | None, dict | None]],
    ) -> dict[str, dict | None]:
        """Reconcile multiple entities in one go.

        Each item is (source_record_id, label_en, type_qid, context).
        Returns {source_record_id: xref-or-None}. Live calls are batched at
        self.batch_size; cache and seed hits are resolved immediately.
        """
        results: dict[str, dict | None] = {}
        pending: list[tuple[str, str, str | None, str]] = []  # (sid, label, type_qid, query_key)

        for sid, label, type_qid, context in items:
            self.counters["queries_total"] += 1
            if not label:
                results[sid] = None
                self.counters["no_match"] += 1
                continue
            if sid in self._seed:
                self.counters["seed_hits"] += 1
                seeded = self._seed[sid]
                results[sid] = self._make_xref(
                    qid=seeded["qid"],
                    confidence=seeded.get("confidence", 1.0),
                    method="imported_from_source",
                    reviewed=seeded.get("reviewed", True),
                    note=seeded.get("note", "Curated offline seed (manually verified)."),
                )
                continue
            qkey = self._query_key(label, type_qid, context)
            cached = self._cache_get(qkey)
            if cached is not None:
                self.counters["cache_hits"] += 1
                results[sid] = self._interpret_response(cached, label)
                continue
            pending.append((sid, label, type_qid, qkey))

        if pending and self.mode != "offline" and not self._network_disabled:
            for chunk_start in range(0, len(pending), self.batch_size):
                chunk = pending[chunk_start:chunk_start + self.batch_size]
                try:
                    chunk_responses = self._call_api_batch(
                        [(sid, lab, tq) for sid, lab, tq, _qk in chunk]
                    )
                    for (sid, label, type_qid, qkey), resp in zip(chunk, chunk_responses):
                        self._cache_put(qkey, resp)
                        results[sid] = self._interpret_response(resp, label)
                        self.counters["api_hits"] += 1
                except _NetworkUnavailable:
                    self.counters["api_failures"] += len(chunk)
                    if self.mode == "live":
                        raise
                    self._network_disabled = True
                    if self.verbose:
                        print(
                            "[wikidata_reconcile] live API unreachable; "
                            "remaining queries fall through.",
                            file=sys.stderr,
                        )
                    for sid, _lab, _tq, _qk in chunk:
                        results.setdefault(sid, None)
                        self.counters["no_match"] += 1
                    # Drop further pending items as misses
                    for sid, _lab, _tq, _qk in pending[chunk_start + len(chunk):]:
                        results[sid] = None
                        self.counters["no_match"] += 1
                    return results

        # Anything still missing = no match.
        for sid, _lab, _tq, _qk in pending:
            if sid not in results:
                results[sid] = None
                self.counters["no_match"] += 1

        return results

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ----- internal: HTTP -----------------------------------------------

    def _call_api_single(self, label: str, type_qid: str | None) -> dict:
        return self._call_api_batch([("q0", label, type_qid)])[0]

    def _call_api_batch(
        self,
        items: list[tuple[str, str, str | None]],
    ) -> list[dict]:
        if not _HAVE_REQUESTS:
            raise _NetworkUnavailable("requests library not installed")
        # Build the OpenRefine recon-API query envelope.
        queries: dict[str, dict] = {}
        order: list[str] = []
        for i, (_sid, label, type_qid) in enumerate(items):
            qk = f"q{i}"
            order.append(qk)
            payload: dict[str, Any] = {"query": label, "limit": 3}
            if type_qid:
                payload["type"] = type_qid
            queries[qk] = payload

        try:
            r = requests.post(
                self.api_url,
                data={"queries": json.dumps(queries, ensure_ascii=False)},
                timeout=self.timeout_s,
            )
        except requests.exceptions.RequestException as exc:
            raise _NetworkUnavailable(f"connection failed: {exc}") from exc
        if r.status_code in (403, 429, 502, 503, 504):
            raise _NetworkUnavailable(
                f"HTTP {r.status_code} from recon API: {r.text[:120]}"
            )
        if r.status_code != 200:
            raise _NetworkUnavailable(
                f"unexpected HTTP {r.status_code}: {r.text[:120]}"
            )
        try:
            data = r.json()
        except json.JSONDecodeError as exc:
            raise _NetworkUnavailable(f"invalid JSON from recon API: {exc}") from exc

        # Polite throttle between batches (the reconciliation service is free).
        time.sleep(0.4)

        return [data.get(qk, {"result": []}) for qk in order]

    # ----- internal: cache ----------------------------------------------

    def _query_key(
        self,
        label: str,
        type_qid: str | None,
        context: dict | None,
    ) -> str:
        ctx_str = ""
        if context:
            # Stable subset of context that affects matching.
            ctx_keys = ("start_ce", "end_ce", "region_primary")
            ctx_str = "||".join(f"{k}={context.get(k, '')}" for k in ctx_keys)
        return _digest(f"{label}||{type_qid or ''}||{ctx_str}")

    def _cache_get(self, qkey: str) -> dict | None:
        row = self._conn.execute(
            "SELECT response, fetched_at FROM queries WHERE query_key = ?",
            (qkey,),
        ).fetchone()
        if not row:
            return None
        response_json, fetched_at = row
        try:
            fetched = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        if datetime.now(timezone.utc) - fetched > self.ttl:
            return None
        try:
            return json.loads(response_json)
        except json.JSONDecodeError:
            return None

    def _cache_put(self, qkey: str, response: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO queries(query_key, response, fetched_at) VALUES(?, ?, ?)",
            (qkey, json.dumps(response, ensure_ascii=False), _now_iso()),
        )
        self._conn.commit()

    # ----- internal: interpretation -------------------------------------

    def _interpret_response(self, response: dict, label_for_note: str) -> dict | None:
        results = response.get("result") or []
        if not results:
            self.counters["no_match"] += 1
            return None
        top = results[0]
        qid = top.get("id")
        if not qid or not qid.startswith("Q"):
            self.counters["no_match"] += 1
            return None
        raw_score = top.get("score", 0)
        # Normalize: many recon backends return 0-100; some return 0-1.
        score = raw_score / 100.0 if raw_score > 1 else float(raw_score)
        # If the API explicitly flagged 'match=true', treat as 1.0.
        if top.get("match") is True:
            score = max(score, 1.0)
        score = max(0.0, min(1.0, score))

        if score >= self.threshold_auto_accept:
            self.counters["auto_accept"] += 1
            return self._make_xref(
                qid=qid,
                confidence=score,
                method="openrefine_v3",
                reviewed=False,
                note=f"Auto-matched via OpenRefine recon (top result for {label_for_note!r}).",
            )
        if score >= self.threshold_review:
            self.counters["review"] += 1
            return self._make_xref(
                qid=qid,
                confidence=score,
                method="openrefine_v3",
                reviewed=False,
                note=(
                    f"Medium-confidence match for {label_for_note!r}; "
                    f"score={score:.2f} (review threshold {self.threshold_review:.2f}). "
                    f"Manual review recommended."
                ),
            )
        # Below review threshold — drop.
        self.counters["no_match"] += 1
        return None

    @staticmethod
    def _make_xref(
        qid: str, confidence: float, method: str,
        reviewed: bool, note: str,
    ) -> dict:
        return {
            "authority": "wikidata",
            "id": qid,
            "confidence": round(float(confidence), 4),
            "method": method,
            "reviewed": reviewed,
            "note": note[:1000],
        }

    # ----- internal: seed -----------------------------------------------

    def _load_seed(self) -> dict[str, dict]:
        """Load curated offline QID seed file.

        Format: { "<source_record_id>": {"qid": "Q...", "confidence": 1.0,
                                          "reviewed": True, "note": "..."}, ... }
        """
        if not self.seed_path or not self.seed_path.exists():
            return {}
        try:
            with self.seed_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data


class _NetworkUnavailable(RuntimeError):
    """Internal sentinel: live API unreachable. In 'auto' mode, the caller
    catches this and stops further attempts; in 'live' mode it propagates."""


# ----- CLI for cache inspection / refresh ---------------------------------

def _cli() -> int:  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Wikidata reconciliation utility.")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--seed", type=Path, default=None)
    parser.add_argument("--mode", choices=("live", "offline", "auto"), default="auto")
    parser.add_argument("--label", type=str, help="Reconcile a single label.")
    parser.add_argument("--type", dest="type_qid", type=str, default=None)
    parser.add_argument("--inspect", action="store_true", help="Show cache stats.")
    args = parser.parse_args()

    rec = WikidataReconciler(
        cache_path=args.cache, seed_path=args.seed, mode=args.mode, verbose=True
    )
    if args.inspect:
        n = rec._conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        print(f"Cache: {n} queries cached at {args.cache}")
        if args.seed and args.seed.exists():
            with args.seed.open(encoding="utf-8") as fh:
                seed = json.load(fh)
            print(f"Seed: {len(seed)} curated entries at {args.seed}")
        return 0
    if args.label:
        result = rec.reconcile(label_en=args.label, type_qid=args.type_qid)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    rec.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
