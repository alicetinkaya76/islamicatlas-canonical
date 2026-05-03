"""
entity_resolver.py — Cross-adapter entity resolution.

Three-tier strategy (see ADR-008):
  Tier 1: Deterministic key match  — authority IDs (Wikidata QID, VIAF, Pleiades, ...)
                                     and source CURIEs (yaqut:7842, bosworth-nid:3, ...)
                                     Active in v0.1.0 (Hafta 2).
  Tier 2: Blocking + similarity     — fuzzy match for entities without authority IDs.
                                     Skeleton in v0.1.0; full implementation P0.2.
  Tier 3: Manual review queue       — confidence 0.70..0.90 deferred to maintainer.
                                     CLI in v0.1.0; full UX P0.2.

Resolver is canonical-store-internal: it consults the lookup index
(data/_index/lookup.sqlite), NOT the public Typesense collection.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


@dataclass
class Candidate:
    pid: str
    score: float
    feature_scores: dict[str, float] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionDecision:
    kind: str                                # "match" | "new" | "review"
    matched_pid: Optional[str] = None
    confidence: float = 0.0
    candidates: list[Candidate] = field(default_factory=list)
    feature_scores: dict[str, float] = field(default_factory=dict)
    queue_id: Optional[str] = None           # set when kind="review"
    tier: int = 0                            # which tier produced this decision

    def to_log_entry(self, adapter_id: str, extracted_record_id: str) -> dict:
        return {
            "adapter_id": adapter_id,
            "extracted_record_id": extracted_record_id,
            "kind": self.kind,
            "matched_pid": self.matched_pid,
            "confidence": self.confidence,
            "tier": self.tier,
            "queue_id": self.queue_id,
            "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }


class EntityResolver:
    """Resolve extracted records against the canonical store's lookup index.

    Usage:
        resolver = EntityResolver(repo_root="/path/to/repo")
        for extracted in extracts:
            decision = resolver.resolve(
                entity_type="person",
                authority_xref=[{"authority": "wikidata", "id": "Q41183"}],
                labels={"prefLabel": {"en": "Aleppo", ...}, ...},
                temporal={"start_ce": 637},
                coords={"lat": 36.2, "lon": 37.13},
                adapter_id="dia",
                extracted_record_id="dia:5847",
            )
    """

    def __init__(self, repo_root: Path | str, weights_path: Path | str | None = None):
        self.repo_root = Path(repo_root)
        self.index_path = self.repo_root / "data" / "_index" / "lookup.sqlite"
        self.review_queue_dir = self.repo_root / "data" / "review_queue"
        self.review_decisions_path = self.repo_root / "data" / "review_decisions.jsonl"
        self.weights_path = Path(weights_path) if weights_path else self.repo_root / "pipelines" / "_lib" / "resolver_weights.yaml"
        self._conn: Optional[sqlite3.Connection] = None
        self._weights = self._load_weights()

    # ----- public API ----------------------------------------------------

    def resolve(
        self,
        entity_type: str,
        adapter_id: str,
        extracted_record_id: str,
        authority_xref: list[dict] | None = None,
        source_curies: list[str] | None = None,
        labels: dict | None = None,
        temporal: dict | None = None,
        coords: dict | None = None,
        nisba: list[str] | None = None,
        kunya: str | None = None,
    ) -> ResolutionDecision:
        """Run the three-tier resolution strategy. Returns a ResolutionDecision."""
        # Check decision cache first (idempotent re-runs).
        cached = self._cache_lookup(adapter_id, extracted_record_id)
        if cached is not None:
            return cached

        # Tier 1: deterministic key match
        decision = self._tier1_authority_match(authority_xref or [], source_curies or [])
        if decision.kind == "match":
            decision.tier = 1
            self._cache_store(adapter_id, extracted_record_id, decision)
            return decision

        # Tier 2: blocking + similarity (stubbed in v0.1.0; returns kind="new" until P0.2)
        decision = self._tier2_blocking_similarity(
            entity_type=entity_type,
            labels=labels or {},
            temporal=temporal or {},
            coords=coords or {},
            nisba=nisba or [],
            kunya=kunya,
        )
        decision.tier = 2 if decision.kind != "new" else 0

        # Tier 3: review queue if 0.70 <= confidence < 0.90
        if decision.kind == "review":
            decision.queue_id = str(uuid.uuid4())
            self._review_enqueue(
                adapter_id=adapter_id,
                extracted_record_id=extracted_record_id,
                decision=decision,
                extracted_summary={"labels": labels, "temporal": temporal, "coords": coords},
            )

        self._cache_store(adapter_id, extracted_record_id, decision)
        return decision

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ----- Tier 1: deterministic match ----------------------------------

    def _tier1_authority_match(
        self,
        authority_xref: list[dict],
        source_curies: list[str],
    ) -> ResolutionDecision:
        """Look up by Wikidata QID, VIAF, Pleiades, OpenITI, Bosworth NID, source CURIEs.

        Returns kind="match" with confidence=1.0 on hit; kind="new" sentinel otherwise.
        """
        conn = self._connect()
        if conn is None:
            return ResolutionDecision(kind="new", confidence=0.0)

        # Try authority IDs first
        for xref in authority_xref:
            authority = xref.get("authority")
            authority_id = xref.get("id")
            if not authority or not authority_id:
                continue
            row = conn.execute(
                "SELECT pid FROM authority_xref WHERE authority = ? AND authority_id = ?",
                (authority, authority_id),
            ).fetchone()
            if row:
                return ResolutionDecision(
                    kind="match",
                    matched_pid=row[0],
                    confidence=1.0,
                    feature_scores={"tier1_authority": 1.0, "authority": authority},
                )

        # Try source CURIEs (cross-source xref crosswalks)
        for curie in source_curies:
            row = conn.execute(
                "SELECT pid FROM source_curie WHERE source_id = ?",
                (curie,),
            ).fetchone()
            if row:
                return ResolutionDecision(
                    kind="match",
                    matched_pid=row[0],
                    confidence=1.0,
                    feature_scores={"tier1_source_curie": 1.0, "curie": curie},
                )

        # No deterministic hit
        return ResolutionDecision(kind="new", confidence=0.0)

    # ----- Tier 2: blocking + similarity (stubbed in v0.1.0) ------------

    def _tier2_blocking_similarity(
        self,
        entity_type: str,
        labels: dict,
        temporal: dict,
        coords: dict,
        nisba: list[str],
        kunya: str | None,
    ) -> ResolutionDecision:
        """Fuzzy match against blocked candidates.

        STUB in v0.1.0: returns kind="new" unconditionally. Bosworth Hafta 2
        canonical store is empty for the dynasty namespace before this adapter
        runs, so Tier 2 is unreachable in practice; the stub is sufficient for
        Hafta 2 deliverable.

        Full implementation in P0.2 with the A'lam + DIA + EI1 person seed,
        which is when Tier 2 first encounters non-empty canonical store and
        non-trivial deduplication challenges.
        """
        # Placeholder: future blocking + similarity scoring goes here.
        # See ADR-008 §8.2 Tier 2 for the full algorithm.
        return ResolutionDecision(kind="new", confidence=0.0)

    # ----- Tier 3: review queue -----------------------------------------

    def _review_enqueue(
        self,
        adapter_id: str,
        extracted_record_id: str,
        decision: ResolutionDecision,
        extracted_summary: dict,
    ) -> None:
        """Append a review-queue entry as JSONL."""
        import json
        self.review_queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = self.review_queue_dir / f"{adapter_id}.jsonl"
        entry = {
            "queue_id": decision.queue_id,
            "adapter_id": adapter_id,
            "extracted_record_id": extracted_record_id,
            "extracted_summary": extracted_summary,
            "candidates": [
                {
                    "pid": c.pid,
                    "score": c.score,
                    "feature_scores": c.feature_scores,
                    "summary": c.summary,
                }
                for c in decision.candidates
            ],
            "deferred_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        with queue_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ----- decision cache (idempotent re-runs) --------------------------

    def _cache_lookup(self, adapter_id: str, extracted_record_id: str) -> ResolutionDecision | None:
        conn = self._connect()
        if conn is None:
            return None
        row = conn.execute(
            """
            SELECT decision_kind, matched_pid, confidence
              FROM decision_cache
             WHERE adapter_id = ? AND extracted_record_id = ?
            """,
            (adapter_id, extracted_record_id),
        ).fetchone()
        if not row:
            return None
        return ResolutionDecision(
            kind=row[0],
            matched_pid=row[1],
            confidence=row[2],
            tier=0,  # cache hit; original tier preserved in log only
        )

    def _cache_store(self, adapter_id: str, extracted_record_id: str, decision: ResolutionDecision) -> None:
        conn = self._connect()
        if conn is None:
            return
        conn.execute(
            """
            INSERT OR REPLACE INTO decision_cache
              (adapter_id, extracted_record_id, decision_kind, matched_pid, confidence, decided_at)
              VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                adapter_id,
                extracted_record_id,
                decision.kind,
                decision.matched_pid,
                decision.confidence,
                datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            ),
        )
        conn.commit()

    # ----- weights config ------------------------------------------------

    def _load_weights(self) -> dict:
        if not self.weights_path.exists():
            # Default weights baked in. Override by writing the YAML file.
            return {
                "person": {
                    "w_label": 0.35, "w_alt": 0.15, "w_temporal": 0.20,
                    "w_authority": 0.20, "w_kunya": 0.10,
                    "auto_accept_threshold": 0.90, "review_threshold": 0.70,
                },
                "place": {
                    "w_label": 0.30, "w_alt": 0.15, "w_temporal": 0.05,
                    "w_spatial": 0.30, "w_authority": 0.20,
                    "auto_accept_threshold": 0.90, "review_threshold": 0.70,
                },
                "dynasty": {
                    "w_label": 0.40, "w_temporal": 0.30, "w_authority": 0.20, "w_alt": 0.10,
                    "auto_accept_threshold": 0.90, "review_threshold": 0.80,
                },
                "work": {
                    "w_label": 0.40, "w_temporal": 0.10, "w_author": 0.30, "w_genre": 0.10, "w_authority": 0.10,
                    "auto_accept_threshold": 0.90, "review_threshold": 0.70,
                },
                "manuscript": {
                    "w_shelf_mark": 0.50, "w_library": 0.30, "w_dating": 0.20,
                    "auto_accept_threshold": 0.95, "review_threshold": 0.80,
                },
                "event": {
                    "w_label": 0.30, "w_temporal": 0.40, "w_spatial": 0.30,
                    "auto_accept_threshold": 0.90, "review_threshold": 0.70,
                },
            }
        try:
            import yaml
            with self.weights_path.open(encoding="utf-8") as fh:
                return yaml.safe_load(fh)
        except Exception:
            return {}

    # ----- SQLite connection management ---------------------------------

    def _connect(self) -> sqlite3.Connection | None:
        if self._conn is not None:
            return self._conn
        if not self.index_path.exists():
            # Index not yet built. Resolver returns "new" for everything,
            # which is correct for bootstrap (no entities yet to resolve against).
            return None
        self._conn = sqlite3.connect(self.index_path)
        self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn
