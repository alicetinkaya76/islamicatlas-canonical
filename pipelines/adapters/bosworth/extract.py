"""
extract.py — Bosworth dynasties → normalized intermediate records.

Walks three CSVs (all_dynasties_enriched, all_rulers_merged, dynasty_relations),
yields one normalized record per NID. The intermediate keeps all 52 source
columns (the data dictionary advertises 44 but the live CSV ships 52, with
narrative_tr/en, key_contribution_tr/en, rise_reason_tr, fall_reason_tr,
context_before_tr, context_after_tr appended); canonicalize.py decides which
columns to map to the canonical schema and which to drop.

Output shape per record:

    {
      "source_record_id": "bosworth-nid:42",
      "raw_data": {
        "dynasty": { ...44+ fields from all_dynasties_enriched... },
        "rulers":  [ { ...38 fields from all_rulers_merged... }, ... ],
        "relations": {
          "predecessors_dynasty_ids": ["3"],   # raw 'selef' rows where id_2 == this
          "successors_dynasty_ids":   ["27"],
          "rivals_dynasty_ids":       [...],
          "vassals_of_dynasty_ids":   [...],   # 'vasal' rows where id_2 == this
          "branches_of_dynasty_ids":  [...],   # 'dal/kol' rows where id_2 == this
        },
      },
      "source_locator": {
        "file": "all_dynasties_enriched.csv",
        "row":  42,
        "chapter": "Chapter 1: The Caliphs",
      }
    }

Note: extract is deterministic and network-free. Reconciliation,
PID-allocation, schema validation all happen downstream in canonicalize.py.

The relations payload is symmetric (id_2 is the entity these relations
attach to: predecessor_of_me / successor_of_me / etc.). Canonicalize.py
maps predecessor/successor to canonical PIDs in a second pass.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterator


def extract(source_paths: list[Path], options: dict | None = None) -> Iterator[dict]:
    options = options or {}
    paths = {p.name: p for p in source_paths}

    dynasties_path = paths.get("all_dynasties_enriched.csv")
    rulers_path = paths.get("all_rulers_merged.csv")
    relations_path = paths.get("dynasty_relations.csv")

    if dynasties_path is None or not dynasties_path.exists():
        raise FileNotFoundError(
            "all_dynasties_enriched.csv missing from source_paths."
        )
    if rulers_path is None or not rulers_path.exists():
        raise FileNotFoundError("all_rulers_merged.csv missing from source_paths.")
    if relations_path is None or not relations_path.exists():
        raise FileNotFoundError("dynasty_relations.csv missing from source_paths.")

    rulers_by_dyn = _index_rulers(rulers_path)
    relations_by_dyn = _index_relations(relations_path)

    with dynasties_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row_idx, row in enumerate(reader, start=1):
            dynasty_id = (row.get("dynasty_id") or "").strip()
            if not dynasty_id:
                continue
            # Normalize to int-string for key consistency
            try:
                dynasty_id = str(int(dynasty_id))
            except ValueError:
                # leave as-is; canonicalize will reject malformed records
                pass

            dynasty_record = {k: (v or "").strip() for k, v in row.items() if k}
            attached_rulers = sorted(
                rulers_by_dyn.get(dynasty_id, []),
                key=_ruler_sort_key,
            )
            attached_relations = relations_by_dyn.get(dynasty_id, _empty_relations())

            yield {
                "source_record_id": f"bosworth-nid:{dynasty_id}",
                "raw_data": {
                    "dynasty": dynasty_record,
                    "rulers": attached_rulers,
                    "relations": attached_relations,
                },
                "source_locator": {
                    "file": dynasties_path.name,
                    "row": row_idx,
                    "chapter": dynasty_record.get("chapter", ""),
                    "dynasty_id_padded": _pad_nid(dynasty_id),
                },
            }


# ----- helpers -------------------------------------------------------------


def _index_rulers(path: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            dyn = (row.get("dynasty_id") or "").strip()
            if not dyn:
                continue
            try:
                dyn = str(int(dyn))
            except ValueError:
                pass
            cleaned = {k: (v or "").strip() for k, v in row.items() if k}
            out[dyn].append(cleaned)
    return dict(out)


def _index_relations(path: Path) -> dict[str, dict]:
    """Pivot dynasty_relations.csv so each dynasty sees its inbound + outbound edges.

    For each row (id_1, id_2, type):
        type 'selef' (predecessor):
            entity at id_2 has predecessor id_1
            entity at id_1 has successor   id_2
        type 'vasal' (vassal):
            entity at id_2 has overlord    id_1
            entity at id_1 has vassal      id_2
        type 'dal/kol' (branch / sub-line):
            entity at id_2 is branch_of    id_1
            entity at id_1 has branch_to   id_2
        type 'rakip' (rival): symmetric
    """
    edges: dict[str, dict] = defaultdict(_empty_relations)
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            id_1 = (row.get("dynasty_id_1") or "").strip()
            id_2 = (row.get("dynasty_id_2") or "").strip()
            rtype = (row.get("relation_type") or "").strip().lower()
            period = (row.get("period") or "").strip()
            notes = (row.get("notes") or "").strip()
            if not id_1 or not id_2 or not rtype:
                continue
            # Normalize ids
            try:
                id_1 = str(int(id_1))
            except ValueError:
                pass
            try:
                id_2 = str(int(id_2))
            except ValueError:
                pass

            edge = {"counterpart_dynasty_id": None, "period": period, "notes": notes}

            if rtype == "selef":
                edges[id_2]["predecessors_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_1}
                )
                edges[id_1]["successors_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_2}
                )
            elif rtype == "vasal":
                edges[id_2]["overlords_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_1}
                )
                edges[id_1]["vassals_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_2}
                )
            elif rtype == "dal/kol":
                edges[id_2]["branch_of_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_1}
                )
                edges[id_1]["branched_into_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_2}
                )
            elif rtype == "rakip":
                edges[id_1]["rivals_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_2}
                )
                edges[id_2]["rivals_dynasty_ids"].append(
                    {**edge, "counterpart_dynasty_id": id_1}
                )
            # Unknown types: silently dropped (canonicalize.py won't see them)

    return dict(edges)


def _empty_relations() -> dict:
    return {
        "predecessors_dynasty_ids": [],
        "successors_dynasty_ids": [],
        "overlords_dynasty_ids": [],
        "vassals_dynasty_ids": [],
        "branch_of_dynasty_ids": [],
        "branched_into_dynasty_ids": [],
        "rivals_dynasty_ids": [],
    }


def _ruler_sort_key(r: dict) -> tuple:
    """Sort rulers chronologically for inline emission."""
    rorder = (r.get("reign_order") or "").strip()
    try:
        rorder_int = int(rorder)
    except ValueError:
        rorder_int = 9_999
    rsce_raw = (r.get("reign_start_ce") or "").strip()
    rsce = _try_parse_year(rsce_raw)
    if rsce is None:
        rsce = 9_999
    return (rorder_int, rsce, r.get("short_name", ""))


def _try_parse_year(s: str) -> int | None:
    """Parse loose year strings like 'c. 1012', '1056?', '755/56'."""
    if not s:
        return None
    s = s.strip()
    # Strip common adornments
    for prefix in ("c.", "C.", "ca.", "CA.", "ca ", "circa "):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    s = s.rstrip("?")
    s = s.replace("–", "-").replace("—", "-")
    # Take the first integer token
    head = []
    for ch in s:
        if ch.isdigit() or (ch == "-" and not head):
            head.append(ch)
        else:
            if head:
                break
    candidate = "".join(head)
    if candidate in ("", "-"):
        return None
    try:
        return int(candidate)
    except ValueError:
        return None


def _pad_nid(dynasty_id: str) -> str:
    try:
        return f"{int(dynasty_id):03d}"
    except ValueError:
        return dynasty_id
