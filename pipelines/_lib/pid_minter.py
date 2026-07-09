"""
pid_minter.py — Atomic, idempotent PID allocation for the canonical store.

Design (see ADR-001 URI scheme):

  * Each canonical entity carries an @id of the form 'iac:<namespace>-NNNNNNNN'
    (eight zero-padded digits, ordinal allocation per namespace).

  * mint(namespace, input_hash) is idempotent: the same (namespace, input_hash)
    pair always returns the same PID, even across processes / re-runs. This is
    what makes 'python3 pipelines/run_adapter.py --id bosworth' deterministic
    and what lets the integrity check be a separate-pass operation.

  * Persistence lives under data/_state/:
      pid_counter.json   { "<namespace>": <next_ordinal_int>, ... }
      pid_index.json     { "<namespace>:<input_hash>": "iac:<ns>-NNNNNNNN", ... }

  * File-locking via fcntl on POSIX (which is sufficient for the Phase 0
    single-host pipeline). No coordination across machines is required at
    this stage.

  * 'input_hash' is a free-form string from the caller — typically a CURIE
    such as 'bosworth-nid:42' or 'yaqut:7842'. It is the caller's contract
    to make this string deterministic and globally unique for the entity it
    represents within the source. The minter never inspects the contents.

Used by:
    pipelines/adapters/<id>/canonicalize.py (via run_adapter.py)
    pipelines/integrity/check_all.py
    tests/integration/test_bosworth_pilot.py
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# fcntl is POSIX-only; fall back to a no-op lock on Windows for dev convenience.
try:
    import fcntl  # type: ignore
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover
    _HAVE_FCNTL = False


_PID_PATTERN_TEMPLATE = "iac:{ns}-{ord:08d}"
_VALID_NAMESPACES = {"place", "dynasty", "person", "work", "manuscript", "event"}


class PidMinterError(Exception):
    """Raised when the minter cannot allocate or persist a PID."""


class PidMinter:
    """Allocate persistent identifiers in iac:<namespace>-NNNNNNNN form.

    Concurrency model: a single process holds an exclusive lock on the state
    file during read-modify-write. Multiple processes are serialized by the OS.
    """

    def __init__(self, state_dir: Path | str):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.counter_path = self.state_dir / "pid_counter.json"
        self.index_path = self.state_dir / "pid_index.json"
        self.lock_path = self.state_dir / ".pid_minter.lock"
        # Batch-session state (see session()); None = per-call persistence.
        self._session_counter: dict[str, int] | None = None
        self._session_index: dict[str, str] | None = None
        self._session_dirty = False

    # ----- public API ----------------------------------------------------

    def mint(self, namespace: str, input_hash: str) -> str:
        """Return (or allocate) the canonical PID for (namespace, input_hash).

        Idempotent: the same input always yields the same PID, regardless of
        how many times this is called or by how many processes.
        """
        if namespace not in _VALID_NAMESPACES:
            raise PidMinterError(
                f"Unknown namespace {namespace!r}; expected one of {sorted(_VALID_NAMESPACES)}"
            )
        if not isinstance(input_hash, str) or not input_hash:
            raise PidMinterError(f"input_hash must be non-empty str, got {input_hash!r}")

        index_key = f"{namespace}:{input_hash}"

        # Inside a session(): mint against the in-memory copy; persist on exit.
        if self._session_index is not None:
            if index_key in self._session_index:
                return self._session_index[index_key]
            pid = self._allocate(self._session_counter, namespace)
            self._session_index[index_key] = pid
            self._session_dirty = True
            return pid

        with self._exclusive_lock():
            counter = self._load_counter()
            index = self._load_index()

            if index_key in index:
                # Idempotent hit — return the previously-minted PID without
                # touching the counter.
                return index[index_key]

            pid = self._allocate(counter, namespace)
            index[index_key] = pid

            self._save_counter(counter)
            self._save_index(index)
            return pid

    @staticmethod
    def _allocate(counter: dict[str, int], namespace: str) -> str:
        next_ord = counter.get(namespace, 0) + 1
        if next_ord > 99_999_999:
            raise PidMinterError(
                f"Namespace {namespace!r} ordinal exhausted (>99,999,999). "
                f"Schema PID pattern must be widened before continuing."
            )
        counter[namespace] = next_ord
        return _PID_PATTERN_TEMPLATE.format(ns=namespace, ord=next_ord)

    def lookup(self, namespace: str, input_hash: str) -> str | None:
        """Return the PID for (namespace, input_hash) without minting a new one.

        Useful for second-pass operations (e.g., predecessor resolution) where
        the caller knows the entity should already exist and wants to bail
        loudly if not.
        """
        if self._session_index is not None:
            return self._session_index.get(f"{namespace}:{input_hash}")
        with self._exclusive_lock():
            index = self._load_index()
        return index.get(f"{namespace}:{input_hash}")

    @contextmanager
    def session(self) -> Iterator["PidMinter"]:
        """Batch-mint context: load state once, mint in memory, persist once.

        mint()/lookup() calls inside the block operate on an in-memory copy;
        the exclusive lock is held for the whole block and the index/counter
        are written exactly once on exit (atomic, fsynced). Semantics match
        per-call minting — same PIDs, same idempotency — but a bulk pass
        (e.g. AP dia_works, 8-25K mints) does one read+write instead of N
        full-index rewrites (~31 ms/mint measured → minutes saved).

        The state is persisted EVEN IF the block raises (finally-path): a
        caller may already have written canonical records carrying PIDs
        minted in this session, and dropping those allocations would let the
        next run hand the same ordinal to a different entity. A persisted-
        but-unused allocation is merely a phantom index entry — harmless by
        comparison, and disk-existence guards (see el_alam Track A) already
        tolerate phantoms. (Review-proven failure mode, H9 Stage 3.)

        Nesting is not supported; the inner call raises.
        """
        if self._session_index is not None:
            raise PidMinterError("PidMinter.session() does not nest")
        with self._exclusive_lock():
            self._session_counter = self._load_counter()
            self._session_index = self._load_index()
            self._session_dirty = False
            try:
                yield self
            finally:
                counter, index, dirty = (
                    self._session_counter, self._session_index, self._session_dirty)
                self._session_counter = None
                self._session_index = None
                self._session_dirty = False
                if dirty:
                    self._save_counter(counter)
                    self._save_index(index)

    def stats(self) -> dict[str, int]:
        """Return the current high-water-mark per namespace."""
        # Inside a session() the lock is already held by this instance —
        # re-acquiring flock on a fresh fd self-deadlocks (review-proven).
        if self._session_counter is not None:
            return dict(self._session_counter)
        with self._exclusive_lock():
            return dict(self._load_counter())

    # ----- internal ------------------------------------------------------

    def _load_counter(self) -> dict[str, int]:
        if not self.counter_path.exists():
            return {}
        try:
            with self.counter_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("counter state is not a JSON object")
            return {k: int(v) for k, v in data.items()}
        except (OSError, ValueError, TypeError) as exc:
            raise PidMinterError(f"Cannot read {self.counter_path}: {exc}") from exc

    def _load_index(self) -> dict[str, str]:
        if not self.index_path.exists():
            return {}
        try:
            with self.index_path.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("index state is not a JSON object")
            return {str(k): str(v) for k, v in data.items()}
        except (OSError, ValueError, TypeError) as exc:
            raise PidMinterError(f"Cannot read {self.index_path}: {exc}") from exc

    def _save_counter(self, counter: dict[str, int]) -> None:
        self._atomic_write(self.counter_path, json.dumps(counter, sort_keys=True, indent=2))

    def _save_index(self, index: dict[str, str]) -> None:
        # The index can grow large (one entry per canonical record across
        # all sources). We sort for diff-friendliness.
        self._atomic_write(self.index_path, json.dumps(index, sort_keys=True, indent=2))

    @staticmethod
    def _atomic_write(path: Path, contents: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(contents)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        """OS-level exclusive lock on the state directory.

        On non-POSIX systems the lock is a no-op. The Phase 0 pipeline does
        not require cross-platform concurrent access; this is good enough.
        """
        if not _HAVE_FCNTL:
            yield
            return
        # Use a separate lock file so we don't conflict with reads of the
        # JSON files themselves.
        with self.lock_path.open("a+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


# ----- module-level helpers ------------------------------------------------


def parse_pid(pid: str) -> tuple[str, int]:
    """Split an iac PID into (namespace, ordinal)."""
    if not pid.startswith("iac:"):
        raise ValueError(f"Not an iac PID: {pid!r}")
    body = pid[len("iac:"):]
    ns, _, ord_str = body.partition("-")
    if not ord_str.isdigit():
        raise ValueError(f"Not an iac PID: {pid!r}")
    return ns, int(ord_str)


def filename_for_pid(pid: str) -> str:
    """Return the canonical on-disk filename for a PID.

    iac:dynasty-00000003 → iac_dynasty_00000003.json
    """
    ns, ord_int = parse_pid(pid)
    return f"iac_{ns}_{ord_int:08d}.json"


if __name__ == "__main__":
    # Tiny self-check: mint a few PIDs in a tmpdir and re-mint to confirm idempotency.
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        m = PidMinter(tmp)
        a = m.mint("dynasty", "bosworth-nid:1")
        b = m.mint("dynasty", "bosworth-nid:2")
        c = m.mint("dynasty", "bosworth-nid:1")  # re-mint
        assert a == "iac:dynasty-00000001", a
        assert b == "iac:dynasty-00000002", b
        assert c == a, f"idempotency broken: {a} vs {c}"
        # Cross-namespace counter independence
        d = m.mint("place", "test:1")
        assert d == "iac:place-00000001", d
        # filename round-trip
        assert filename_for_pid(a) == "iac_dynasty_00000001.json"
        print("pid_minter self-check OK:", m.stats())
        sys.exit(0)
