"""
extract.py — Adapter template for the extraction stage.

Convert raw source artifacts into a normalized intermediate representation.

Contract:
    extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]

The yielded dicts are NOT canonical — they are an intermediate representation
specific to this adapter. canonicalize.py consumes this intermediate and
emits records conforming to schemas/<namespace>.schema.json.

Design rules:
    * Deterministic. Same inputs → same outputs (so PID minting is idempotent).
    * No network calls (reconciliation belongs in canonicalize.py).
    * No assumptions about the canonical schema.
    * Yield one record per logical source unit (entry, page, table row, NID, ...).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    """Walk source files, yield normalized records.

    Args:
        source_paths: List of input file paths (resolved by orchestrator from
            manifest.yaml input_paths).
        options: Optional adapter-specific options passed through registry config.

    Yields:
        Dict with adapter-specific fields. The shape is up to you, but consistent
        across all yields. Recommended top-level fields:
          - source_record_id : str   # stable identifier within this source
          - raw_data         : dict  # the normalized fields extracted
          - source_locator   : dict  # { page, line, section, ... } for provenance
    """
    options = options or {}

    for path in source_paths:
        if not path.exists():
            raise FileNotFoundError(f"Adapter source missing: {path}")

        if path.suffix == ".json":
            with path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
            # Adjust the iteration shape to match your source structure.
            if isinstance(payload, list):
                for i, record in enumerate(payload):
                    yield {
                        "source_record_id": record.get("id") or f"{path.stem}-{i}",
                        "raw_data": record,
                        "source_locator": {"file": path.name, "index": i},
                    }
            elif isinstance(payload, dict):
                yield {
                    "source_record_id": payload.get("id") or path.stem,
                    "raw_data": payload,
                    "source_locator": {"file": path.name},
                }
            else:
                raise ValueError(f"Unexpected JSON top-level type in {path}")
        else:
            raise NotImplementedError(
                f"Extraction for {path.suffix} not implemented in this template. "
                "Override extract() in your adapter for OCR/HTR/CSV/scraping inputs."
            )
