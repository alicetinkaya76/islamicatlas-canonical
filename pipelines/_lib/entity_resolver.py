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

import math
import re
import sqlite3
import sys
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

try:
    from rapidfuzz import fuzz as _fuzz
    _HAVE_RAPIDFUZZ = True
except ImportError:  # pragma: no cover — requirements.txt lists rapidfuzz
    _HAVE_RAPIDFUZZ = False


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
        # H10 final-review: karar cache'i lookup.sqlite'tan AYRILDI —
        # `build_lookup --rebuild` indeks dosyasını silip yeniden kurar ve
        # cache'i (5 adapter'ın idempotency hafızasını) yanında götürüyordu.
        # Cache artık data/_state'te yaşar; indeks istendiği kadar rebuild edilir.
        self.cache_path = self.repo_root / "data" / "_state" / "decision_cache.sqlite"
        self.review_queue_dir = self.repo_root / "data" / "review_queue"
        self.review_decisions_path = self.repo_root / "data" / "review_decisions.jsonl"
        self.weights_path = Path(weights_path) if weights_path else self.repo_root / "pipelines" / "_lib" / "resolver_weights.yaml"
        self._conn: Optional[sqlite3.Connection] = None
        self._cache_conn: Optional[sqlite3.Connection] = None
        self._queued_rids: dict[str, set] = {}   # adapter_id → kuyruktaki rid'ler
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
        if self._cache_conn is not None:
            self._cache_conn.close()
            self._cache_conn = None

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
        """Blocking + multi-feature similarity per ADR-008 §8.2 (H10 Stage 1;
        replaces the H2 stub that returned "new" unconditionally).

        Blocking: FTS5 over label_fts (query tokens OR-ed), joined to
        entity_bracket for the entity_type filter, bm25-ranked, capped at
        BLOCK_LIMIT. A candidate whose bracket year contradicts the query by
        > HARD_YEAR_BLOCK years is dropped (namesakes centuries apart).

        Scoring: weighted mean over the features PRESENT on both sides
        (weights from resolver_weights / _load_weights; absent features
        renormalize away rather than diluting the score):
            label    max token_set_ratio over candidate pref labels
            alt      same over alt/translit labels
            temporal 1 - min(|Δyear|, YEAR_DECAY) / YEAR_DECAY
            spatial  1 - min(haversine_km, KM_DECAY) / KM_DECAY

        Decision: score >= auto_accept_threshold AND >= 2 corroborating
        features → "match"; >= review_threshold → "review" (top candidates
        attached for the queue); else "new". A name-only score can never
        auto-match — single-feature hits cap at "review" (North Star: no
        auto-merge on a bare name; namesakes are the norm in this corpus).
        """
        if not _HAVE_RAPIDFUZZ:
            return ResolutionDecision(kind="new", confidence=0.0,
                                      feature_scores={"tier2_disabled": 1.0})
        conn = self._connect()
        if conn is None:
            return ResolutionDecision(kind="new", confidence=0.0)

        query_texts = self._query_label_texts(labels, nisba, kunya)
        if not query_texts:
            return ResolutionDecision(kind="new", confidence=0.0)

        candidates = self._block_candidates(conn, entity_type, query_texts)
        if not candidates:
            return ResolutionDecision(kind="new", confidence=0.0)

        q_year = self._primary_year(temporal)
        q_lat, q_lon = coords.get("lat"), coords.get("lon")
        weights = (self._weights or {}).get(entity_type) or {}
        auto_thr = float(weights.get("auto_accept_threshold", 0.90))
        review_thr = float(weights.get("review_threshold", 0.70))

        scored: list[Candidate] = []
        for pid, bracket in candidates.items():
            feats = self._score_features(
                conn, pid, query_texts, q_year, q_lat, q_lon, bracket,
                entity_type=entity_type,
                km_decay=float(weights.get("spatial_km_decay", self.KM_DECAY)))
            if feats is None:
                continue  # hard year-block
            score, n_feats = self._weighted_score(feats, weights)
            scored.append(Candidate(pid=pid, score=round(score, 4),
                                    feature_scores={**feats, "n_features": float(n_feats)}))
        if not scored:
            return ResolutionDecision(kind="new", confidence=0.0)

        scored.sort(key=lambda c: -c.score)
        best = scored[0]
        n_feats = int(best.feature_scores.get("n_features", 1))

        if best.score >= auto_thr and n_feats >= 2:
            return ResolutionDecision(
                kind="match", matched_pid=best.pid, confidence=best.score,
                candidates=scored[:5], feature_scores=best.feature_scores)
        # review_min_signals (YAML, tip-bazlı; öntanımlı 1 = eski davranış):
        # tek-sinyal (yalnız etiket-benzerliği) adaylar review bandına
        # giremez — koordinatsız placeholder kayıtlar FTS mıknatısına dönüyor
        # ((Meçhul Cami) 632 sahte kuyruk girdisi çekti, H11 S6 kanıtı).
        # İSTİSNA: skor auto eşiğinde/üstündeyse tek sinyalle bile kuyruğa
        # düşer — isim-birebir çakışma insan görmeli ("name-only asla
        # auto-match olmaz" doktrininin öbür yüzü).
        min_sig = int(weights.get("review_min_signals", 1))
        review_ok = n_feats >= min_sig or best.score >= auto_thr
        if best.score >= review_thr and review_ok:
            return ResolutionDecision(
                kind="review", confidence=best.score,
                candidates=scored[:5], feature_scores=best.feature_scores)
        return ResolutionDecision(kind="new", confidence=best.score,
                                  candidates=scored[:3])

    # ----- Tier 2 helpers -------------------------------------------------

    BLOCK_LIMIT = 200          # ADR-008: 50-200 candidates after blocking
    HARD_YEAR_BLOCK = 150      # bracket-year contradiction > this → drop
    YEAR_DECAY = 50.0          # |Δyear| at which temporal score reaches 0
    KM_DECAY = 50.0            # haversine km at which spatial score reaches 0

    _TR_FOLD = str.maketrans({
        "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
        "ç": "c", "Ç": "c", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u",
    })
    _NAME_PUNCT_RE = re.compile(r"[-‐‑‒–—―''ʼʻʾʿ‘’\.\,\(\)\[\]«»\"]+")
    _WS_RE = re.compile(r"\s+")

    @classmethod
    def _normalize_name(cls, text: str) -> str:
        """Diacritic-stripped, TR-folded, punctuation-split lowercase form.
        Deliberately LIGHTER than work_canonicalize's title fingerprint (no
        generic-word dropping — 'Kitāb' matters in a title, not in a name);
        rapidfuzz token_set_ratio absorbs token order and subset effects."""
        nfkd = unicodedata.normalize("NFKD", text)
        s = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
        s = s.translate(cls._TR_FOLD).lower()
        s = cls._NAME_PUNCT_RE.sub(" ", s)
        return cls._WS_RE.sub(" ", s).strip()

    def _query_label_texts(self, labels: dict, nisba: list[str],
                           kunya: str | None) -> list[str]:
        texts: list[str] = []
        pref = labels.get("prefLabel") or {}
        for v in pref.values():
            if isinstance(v, str) and v.strip():
                texts.append(v)
        for arr in (labels.get("altLabel") or {}).values():
            if isinstance(arr, list):
                texts.extend(t for t in arr if isinstance(t, str) and t.strip())
        extras = " ".join([kunya or ""] + [n for n in nisba if n]).strip()
        if extras and texts:
            texts.append(f"{texts[0]} {extras}")
        elif extras:
            texts.append(extras)
        norm = [self._normalize_name(t) for t in texts]
        return [t for t in dict.fromkeys(norm) if t]  # dedupe, keep order

    def _block_candidates(self, conn: sqlite3.Connection, entity_type: str,
                          query_texts: list[str]) -> dict[str, tuple]:
        """FTS5 token-OR match → {pid: (start_year_ce, end_year_ce, lat, lon)}."""
        tokens: list[str] = []
        for t in query_texts:
            tokens.extend(tok for tok in t.split() if len(tok) >= 2)
        tokens = list(dict.fromkeys(tokens))[:12]
        if not tokens:
            return {}
        fts_query = " OR ".join(f'"{tok}"' for tok in tokens)
        try:
            rows = conn.execute(
                """
                SELECT f.pid, b.start_year_ce, b.end_year_ce, b.lat, b.lon
                  FROM label_fts f
                  JOIN entity_bracket b ON b.pid = f.pid
                 WHERE label_fts MATCH ? AND b.entity_type = ?
                 ORDER BY bm25(label_fts)
                 LIMIT ?
                """,
                (fts_query, entity_type, self.BLOCK_LIMIT * 4),
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
        out: dict[str, tuple] = {}
        for pid, sy, ey, lat, lon in rows:
            if pid not in out:
                out[pid] = (sy, ey, lat, lon)
            if len(out) >= self.BLOCK_LIMIT:
                break
        return out

    def _primary_year(self, temporal: dict) -> Optional[int]:
        for k in ("start_ce", "end_ce"):
            v = (temporal or {}).get(k)
            if isinstance(v, int):
                return v
        return None

    def _candidate_labels(self, conn: sqlite3.Connection, pid: str) -> dict[str, list[str]]:
        rows = conn.execute(
            "SELECT kind, text FROM label WHERE pid = ?", (pid,)).fetchall()
        out: dict[str, list[str]] = {"pref": [], "alt": []}
        for kind, text in rows:
            out["pref" if kind == "pref" else "alt"].append(text)
        return out

    def _score_features(self, conn, pid, query_texts, q_year, q_lat, q_lon,
                        bracket, entity_type: str = "person",
                        km_decay: float | None = None) -> Optional[dict[str, float]]:
        # km_decay: tip-bazlı YAML spatial_km_decay (H11 S6) — YERLER şehir
        # ölçeğinde (50 km) doğru; YAPILARDA aynı şehrin iki ayrı camisi
        # 1-2 km arayla spatial≈1.0 verip yanlış auto-match üretti (Almâs
        # Camii'ne 3 farklı Evliyâ camisi, kanıtlı). Bina kimliği bina
        # ölçeği ister.
        sy, ey, c_lat, c_lon = bracket
        c_year = sy if isinstance(sy, int) else (ey if isinstance(ey, int) else None)

        # Hard year block — PERSONS ONLY (H10 final-review düzeltmesi):
        # kişilerde iki taraf da ölüm-yılıdır ve yüzyıllar-ötesi fark adaş
        # demektir; YERLERDE ise sorgu yılı çoğunlukla TANIKLIK yılıdır
        # (sikke basımı, Evliyâ'nın uğrama tarihi) — yer varlığını sürdürür,
        # bu blok aynı şehri kendi pid'inden düşürüp mükerrer mint üretti
        # (kanıtlı: Aydhab/Sehwan/Kûlam). Yer/eser için yıl yalnız SKOR
        # sinyalidir, elek değildir.
        if entity_type == "person" and q_year is not None and c_year is not None \
                and abs(q_year - c_year) > self.HARD_YEAR_BLOCK:
            return None

        cand = self._candidate_labels(conn, pid)
        feats: dict[str, float] = {}

        pref_norm = [self._normalize_name(t) for t in cand["pref"]]
        if pref_norm and query_texts:
            feats["label"] = max(
                _fuzz.token_set_ratio(q, c) for q in query_texts for c in pref_norm
            ) / 100.0
        alt_norm = [self._normalize_name(t) for t in cand["alt"]]
        if alt_norm and query_texts:
            feats["alt"] = max(
                _fuzz.token_set_ratio(q, c) for q in query_texts for c in alt_norm
            ) / 100.0

        if q_year is not None and c_year is not None:
            feats["temporal"] = 1.0 - min(abs(q_year - c_year), self.YEAR_DECAY) / self.YEAR_DECAY

        if None not in (q_lat, q_lon, c_lat, c_lon):
            decay = km_decay if km_decay else self.KM_DECAY
            feats["spatial"] = 1.0 - min(
                self._haversine_km(q_lat, q_lon, c_lat, c_lon), decay
            ) / decay

        return feats if feats else None

    @staticmethod
    def _weighted_score(feats: dict[str, float], weights: dict) -> tuple[float, int]:
        """Weighted mean over PRESENT features; weights renormalize so a
        missing feature neither helps nor hurts. Returns (score, n_features)
        where n_features counts corroborating signals (label+alt = one name
        signal — they are not independent evidence).

        name_evidence: "max" (YAML, tip-bazlı; öntanımlı "weighted" = eski
        davranış): label ve alt TEK isim kanıtına katlanır — max(label, alt),
        ağırlığı w_label+w_alt. Gerekçe (H11 S9, kanıtlı): zengin altLabel'lı
        aday, sorgu alt vermediğinde CEZALANIYORDU (Musul: label 1.0 +
        spatial 1.0, alt 0.38 → 0.876 < 0.9 review); alt bazen de kurtarır
        (Urfa: label 0.62, alt 'Edessa' 1.0). İsim kanıtının iki görünümü
        birbirinin aleyhine ortalanmaz. Person kalibrasyonu (auto 0.95,
        prec %99.2) ESKİ formülle ölçüldü → person'da açılmaz
        (yeniden kalibrasyon gerektirir)."""
        if weights.get("name_evidence") == "max" and ("label" in feats or "alt" in feats):
            name = max(feats.get("label", 0.0), feats.get("alt", 0.0))
            feats = {k: v for k, v in feats.items() if k not in ("label", "alt")}
            feats["label"] = name
            weights = {**weights,
                       "w_label": weights.get("w_label", 0.0) + weights.get("w_alt", 0.0),
                       "w_alt": 0.0}
        # H10 final-review: eksik anahtar = 0 ağırlık (YAML kontratı sızdırmaz
        # — person'da w_spatial tanımlı değilse spatial skora HİÇ girmez;
        # eski kod default'la diriltiyordu).
        w_map = {"label": weights.get("w_label", 0.0),
                 "alt": weights.get("w_alt", 0.0),
                 "temporal": weights.get("w_temporal", 0.0),
                 "spatial": weights.get("w_spatial", 0.0)}
        total_w = sum(w_map[f] for f in feats if f in w_map)
        if total_w <= 0:
            return 0.0, 0
        score = sum(feats[f] * w_map[f] for f in feats if f in w_map) / total_w
        signals = sum(1 for f in ("temporal", "spatial") if f in feats)
        signals += 1 if ("label" in feats or "alt" in feats) else 0
        return score, signals

    @staticmethod
    def _haversine_km(lat1, lon1, lat2, lon2) -> float:
        rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
        dlat, dlon = rlat2 - rlat1, rlon2 - rlon1
        a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(a))

    # ----- Tier 3: review queue -----------------------------------------

    def _review_enqueue(
        self,
        adapter_id: str,
        extracted_record_id: str,
        decision: ResolutionDecision,
        extracted_summary: dict,
    ) -> None:
        """Append a review-queue entry as JSONL (rid-dedup'lu — H10 final-
        review: cache kaybı + re-run eski kayıtları MÜKERRER kuyruklıyordu;
        aynı extracted_record_id bir kuyruk dosyasına bir kez girer)."""
        import json
        self.review_queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = self.review_queue_dir / f"{adapter_id}.jsonl"
        if adapter_id not in self._queued_rids:
            seen: set = set()
            if queue_path.exists():
                for line in queue_path.read_text(encoding="utf-8").splitlines():
                    try:
                        seen.add(json.loads(line).get("extracted_record_id"))
                    except json.JSONDecodeError:
                        continue
            self._queued_rids[adapter_id] = seen
        if extracted_record_id in self._queued_rids[adapter_id]:
            return
        self._queued_rids[adapter_id].add(extracted_record_id)
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

    def _cache_connect(self) -> sqlite3.Connection:
        if self._cache_conn is None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_conn = sqlite3.connect(self.cache_path)
            self._cache_conn.execute("PRAGMA journal_mode = WAL")
            # v2 şeması: tier + queue_id taşınır (H10 final-review — replay
            # eskiden tier/queue_id düşürüp kanıt zincirini bozuyordu).
            self._cache_conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_cache (
                  adapter_id TEXT NOT NULL,
                  extracted_record_id TEXT NOT NULL,
                  decision_kind TEXT NOT NULL,
                  matched_pid TEXT,
                  confidence REAL,
                  tier INTEGER,
                  queue_id TEXT,
                  decided_at TEXT NOT NULL,
                  PRIMARY KEY (adapter_id, extracted_record_id)
                )""")
            self._cache_conn.commit()
        return self._cache_conn

    def _cache_lookup(self, adapter_id: str, extracted_record_id: str) -> ResolutionDecision | None:
        row = self._cache_connect().execute(
            """
            SELECT decision_kind, matched_pid, confidence, tier, queue_id
              FROM decision_cache
             WHERE adapter_id = ? AND extracted_record_id = ?
            """,
            (adapter_id, extracted_record_id),
        ).fetchone()
        if not row:
            return None
        return ResolutionDecision(
            kind=row[0], matched_pid=row[1], confidence=row[2],
            tier=row[3] or 0, queue_id=row[4],
        )

    def _cache_store(self, adapter_id: str, extracted_record_id: str, decision: ResolutionDecision) -> None:
        conn = self._cache_connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO decision_cache
              (adapter_id, extracted_record_id, decision_kind, matched_pid,
               confidence, tier, queue_id, decided_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adapter_id, extracted_record_id, decision.kind,
                decision.matched_pid, decision.confidence, decision.tier,
                decision.queue_id,
                datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            ),
        )
        conn.commit()

    # ----- weights config ------------------------------------------------

    def _in_code_default_weights(self) -> dict:
        return self._load_weights(_defaults_only=True)

    def _load_weights(self, _defaults_only: bool = False) -> dict:
        if _defaults_only or not self.weights_path.exists():
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
                loaded = yaml.safe_load(fh)
            if not isinstance(loaded, dict) or not loaded:
                raise ValueError("resolver_weights.yaml boş/tip-dışı")
            return loaded
        except Exception as exc:
            # H10 final-review: sessiz {} dönüşü tüm ağırlıkları sıfırlayıp
            # her şeyi 'new' yapardı. Sesli uyar + in-code default'lara düş
            # (davranış öngörülebilir kalır; kalibre 0.95 kaybolur — uyarı
            # bunu açıkça söyler).
            print(f"[resolver] WARNING: resolver_weights.yaml yüklenemedi ({exc}); "
                  f"in-code default'lara düşülüyor (person auto=0.90 — "
                  f"KALİBRESİZ).", file=sys.stderr)
            return self._in_code_default_weights()

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
