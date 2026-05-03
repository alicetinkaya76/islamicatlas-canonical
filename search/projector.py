#!/usr/bin/env python3
"""
projector.py — Generic search-document projector.

Reads canonical entity records, applies the YAML projection rule from
search/projections/<entity_type>.yaml, emits a search document conforming
to search/typesense_collection.schema.json.

The projector is rule-driven: adding a new entity type is a YAML edit, not a
Python edit (until a fundamentally new derivation is required).

Active in v0.1.0 (Phase 0): place, dynasty.
Forward-declared (stub derivations return None or sensible defaults): person,
work, manuscript, event — these will be filled in as their respective phases
activate (P0.2 / P0.3).

Used by:
    pipelines/search/full_reindex.py
    pipelines/search/upsert.py
    tests/test_projector.py
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml


class ProjectorError(Exception):
    """Raised when projection fails irrecoverably."""


class Projector:
    """Generic canonical-record → search-document projector."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root)
        self.canonical_dir = self.repo_root / "data" / "canonical"
        self.rules_dir = self.repo_root / "search" / "projections"
        self.iqlim_lookup_path = self.repo_root / "data" / "iqlim_labels.json"

        self._rules_cache: dict[str, dict] = {}
        self._record_cache: dict[str, dict] = {}
        self._iqlim_lookup: dict[str, str] | None = None

    # ----- public API ----------------------------------------------------

    def project(self, record: dict) -> dict:
        """Project a single canonical record into a search document."""
        entity_type = self._infer_entity_type(record)
        rule = self._load_rule(entity_type)
        doc: dict[str, Any] = {}
        for field_name, expr in (rule.get("mappings") or {}).items():
            try:
                doc[field_name] = self._eval_expr(expr, record, rule)
            except Exception as exc:
                raise ProjectorError(
                    f"Field '{field_name}' projection failed: {exc!r} (expr={expr!r})"
                ) from exc
        # Drop nulls / empties — Typesense respects optional=true
        doc = {k: v for k, v in doc.items() if v is not None and v != [] and v != ""}
        return doc

    def project_all(self) -> Iterable[dict]:
        """Walk data/canonical/, project every record, yield search docs."""
        if not self.canonical_dir.exists():
            return
        for ns_dir in sorted(self.canonical_dir.iterdir()):
            if not ns_dir.is_dir():
                continue
            for record_path in sorted(ns_dir.glob("*.json")):
                with record_path.open(encoding="utf-8") as fh:
                    record = json.load(fh)
                try:
                    yield self.project(record)
                except Exception as exc:
                    raise ProjectorError(
                        f"Projection failed for {record_path.relative_to(self.repo_root)}: {exc}"
                    ) from exc

    # ----- expression evaluation ----------------------------------------

    def _eval_expr(self, expr: Any, record: dict, rule: dict) -> Any:
        if expr is None:
            return None
        if not isinstance(expr, str):
            return expr
        s = expr.strip()
        if s == "~":
            return None
        if s.startswith("@const:"):
            return s[len("@const:"):]
        if s.startswith("$"):
            return self._jsonpath(record, s)
        if s.startswith("@derived:"):
            return self._call_derived(s[len("@derived:"):], record, rule)
        if s.startswith("@lookup:"):
            return self._call_lookup(s[len("@lookup:"):], record)
        return s

    def _jsonpath(self, record: dict, path: str) -> Any:
        if not path.startswith("$"):
            return None
        body = path[1:].lstrip(".")
        cur: Any = record
        for tok in self._tokenize_path(body):
            if cur is None:
                return None
            if tok.startswith("[") and tok.endswith("]"):
                inner = tok[1:-1].strip()
                if inner.startswith(("'", '"')):
                    key = inner.strip("\"'")
                    cur = cur.get(key) if isinstance(cur, dict) else None
                else:
                    try:
                        idx = int(inner)
                        cur = cur[idx] if isinstance(cur, list) and -len(cur) <= idx < len(cur) else None
                    except ValueError:
                        cur = None
            else:
                cur = cur.get(tok) if isinstance(cur, dict) else None
        return cur

    def _tokenize_path(self, path: str) -> list[str]:
        toks: list[str] = []
        cur = ""
        i = 0
        while i < len(path):
            c = path[i]
            if c == ".":
                if cur:
                    toks.append(cur); cur = ""
            elif c == "[":
                if cur:
                    toks.append(cur); cur = ""
                end = path.index("]", i)
                toks.append(path[i:end + 1])
                i = end
            else:
                cur += c
            i += 1
        if cur:
            toks.append(cur)
        return toks

    def _call_derived(self, call: str, record: dict, rule: dict) -> Any:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(\((.*)\))?$", call)
        if not m:
            return None
        name = m.group(1)
        args_raw = m.group(3) or ""
        args = [a.strip() for a in args_raw.split(",")] if args_raw else []
        fn = self._derivations().get(name)
        if not fn:
            return None  # forward-declared rules tolerated
        if name.startswith("score_"):
            return fn(record, rule, *args)
        return fn(record, *args)

    def _call_lookup(self, call: str, record: dict) -> Any:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", call)
        if not m:
            return None
        name = m.group(1)
        args_raw = m.group(2)
        fn = self._lookups().get(name)
        if not fn:
            return None
        return fn(record, args_raw)

    # ----- derivations registry -----------------------------------------

    def _derivations(self) -> dict[str, Callable]:
        return {
            "subtypes_from_type_array": self._d_subtypes,
            "translit_ascii_fold": self._d_translit_fold,
            "flatten_altLabels": self._d_flatten_altLabels,
            "flatten_altLabels_plus_kunya_nisba_laqab": self._d_flatten_altLabels,
            "flatten_altLabels_plus_rulers": self._d_flatten_altLabels_plus_rulers,
            "flatten_altLabels_plus_shelf_variants": self._d_flatten_altLabels,
            "geopoint": self._d_geopoint,
            "century_from_temporal": self._d_century_ce,
            "century_from_temporal_ah": self._d_century_ah,
            "iqlim_labels": self._d_iqlim_labels,
            "iqlim_labels_via_place": lambda rec, *a: [],
            "iqlim_labels_via_places": lambda rec, *a: [],
            "iqlim_labels_via_authors": lambda rec, *a: [],
            "source_layers_union": self._d_source_layers,
            "source_layers_from_provenance": self._d_source_layers,
            "languages_from_labels": self._d_languages,
            "languages_union": self._d_languages,
            "bool_field_present": self._d_bool_field_present,
            "bool_authority_present": self._d_bool_authority_present,
            "authority_id": self._d_authority_id,
            "union": self._d_union,
            "bool_default": self._d_bool_default,
            "bool_geo_resolved": self._d_bool_dynasty_geo,
            "bool_geo_resolved_work": lambda rec, *a: False,
            "bool_geo_resolved_manuscript": lambda rec, *a: False,
            "bool_geo_resolved_event": lambda rec, *a: False,
            "unix_timestamp": self._d_unix_ts,
            "dynasty_geo": self._d_dynasty_geo,
            "person_geo": lambda rec, *a: None,
            "work_geo_via_authors_or_composition_place": lambda rec, *a: None,
            "person_century_ce": lambda rec, *a: None,
            "person_century_ah": lambda rec, *a: None,
            "person_start_year": lambda rec, *a: None,
            "person_end_year": lambda rec, *a: None,
            "subtype_first_specific": self._d_subtype_first_specific,
            "score_place": self._score_place,
            "score_dynasty": self._score_dynasty,
            "score_person": self._score_default,
            "score_work": self._score_default,
            "score_manuscript": self._score_default,
            "score_event": self._score_default,
        }

    def _lookups(self) -> dict[str, Callable]:
        return {
            "prefLabels": self._l_prefLabels,
            "place_coords": self._l_place_coords,
            "prefLabel_en": self._l_prefLabel_en,
        }

    # ----- derivation implementations -----------------------------------

    def _d_subtypes(self, record: dict, *_) -> list[str]:
        types = record.get("@type", []) or []
        if len(types) <= 1:
            return []
        return [t.split(":", 1)[-1].lower() for t in types[1:]]

    def _d_subtype_first_specific(self, record: dict, *_) -> str | None:
        subs = self._d_subtypes(record)
        return subs[0] if subs else None

    def _d_translit_fold(self, record: dict, *args) -> str | None:
        for arg in args:
            arg = arg.strip()
            if not arg:
                continue
            v = self._jsonpath(record, "$." + arg)
            if isinstance(v, str) and v:
                return self._ascii_fold(v)
        return None

    def _ascii_fold(self, s: str) -> str:
        repl = {
            "ʿ": "", "ʾ": "", "ʻ": "", "ʼ": "", "'": "",
            "ā": "a", "ī": "i", "ū": "u", "ē": "e", "ō": "o",
            "Ā": "A", "Ī": "I", "Ū": "U", "Ē": "E", "Ō": "O",
            "â": "a", "î": "i", "û": "u",
            "ḍ": "d", "ḥ": "h", "ḳ": "k", "ḷ": "l", "ṃ": "m",
            "ṇ": "n", "ṛ": "r", "ṣ": "s", "ṭ": "t", "ẓ": "z",
            "Ḍ": "D", "Ḥ": "H", "Ḳ": "K", "Ṣ": "S", "Ṭ": "T", "Ẓ": "Z",
            "ġ": "g", "ǧ": "j", "Ġ": "G",
        }
        out = s
        for k, v in repl.items():
            out = out.replace(k, v)
        return out

    def _d_flatten_altLabels(self, record: dict, *_) -> list[str]:
        labels = record.get("labels", {}) or {}
        out: list[str] = []
        for arr in (labels.get("altLabel", {}) or {}).values():
            if isinstance(arr, list):
                out.extend(s for s in arr if isinstance(s, str))
        for v in (labels.get("transliteration", {}) or {}).values():
            if isinstance(v, str) and v:
                out.append(v)
        return list(dict.fromkeys(out))

    def _d_flatten_altLabels_plus_rulers(self, record: dict, *_) -> list[str]:
        out = self._d_flatten_altLabels(record)
        for r in record.get("rulers", []) or []:
            for k in ("name", "regnal_title", "name_ar"):
                v = r.get(k)
                if isinstance(v, str) and v:
                    out.append(v)
        return list(dict.fromkeys(out))

    def _d_geopoint(self, record: dict, *args) -> list[float] | None:
        if len(args) < 2:
            return None
        lat = self._jsonpath(record, "$." + args[0].strip())
        lon = self._jsonpath(record, "$." + args[1].strip())
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return [float(lat), float(lon)]
        return None

    def _d_century_ce(self, record: dict, *args) -> int | None:
        if not args:
            return None
        v = self._jsonpath(record, "$." + args[0].strip())
        if isinstance(v, int):
            return v // 100 + 1 if v >= 0 else v // 100
        return None

    def _d_century_ah(self, record: dict, *args) -> int | None:
        if not args:
            return None
        v = self._jsonpath(record, "$." + args[0].strip())
        if isinstance(v, int) and v >= 1:
            return (v - 1) // 100 + 1
        return None

    def _d_iqlim_labels(self, record: dict, *args) -> list[str]:
        if not args:
            return []
        pids = self._jsonpath(record, "$." + args[0].strip()) or []
        if not isinstance(pids, list):
            return []
        lookup = self._iqlim_table()
        return [lookup[p] for p in pids if p in lookup]

    def _iqlim_table(self) -> dict[str, str]:
        if self._iqlim_lookup is None:
            if self.iqlim_lookup_path.exists():
                with self.iqlim_lookup_path.open(encoding="utf-8") as fh:
                    self._iqlim_lookup = json.load(fh)
            else:
                self._iqlim_lookup = {}
        return self._iqlim_lookup

    def _d_source_layers(self, record: dict, *_) -> list[str]:
        prefix_map = {
            "yaqut": "yaqut", "le-strange": "le-strange",
            "bosworth-nid": "bosworth", "makdisi": "makdisi",
            "evliya": "evliya-celebi", "ibn-battuta": "ibn-battuta",
            "openiti": "openiti", "manual": "manual",
        }
        layers: set[str] = set()
        for entry in (record.get("provenance", {}).get("derived_from") or []):
            sid = entry.get("source_id", "")
            if ":" in sid:
                prefix = sid.split(":", 1)[0]
                layers.add(prefix_map.get(prefix, prefix))
        for layer in (record.get("derived_from_layers") or []):
            layers.add(layer)
        return sorted(layers)

    def _d_languages(self, record: dict, *_) -> list[str]:
        known = {"ar", "fa", "ota", "tr", "en", "la", "el", "fr", "de"}
        langs: set[str] = set()
        labels = record.get("labels", {}) or {}
        for field in ("prefLabel", "altLabel", "description", "originalScript"):
            data = labels.get(field, {}) or {}
            if isinstance(data, dict):
                for tag in data:
                    base = tag.split("-", 1)[0]
                    if base in known:
                        langs.add(base)
        if isinstance(record.get("original_language"), str):
            langs.add(record["original_language"].split("-")[0])
        if isinstance(record.get("language"), list):
            for tag in record["language"]:
                if isinstance(tag, str):
                    langs.add(tag.split("-")[0])
        return sorted(langs)

    def _d_bool_field_present(self, record: dict, *args) -> bool:
        if not args:
            return False
        v = self._jsonpath(record, "$." + args[0].strip())
        return v not in (None, [], {}, "")

    def _d_bool_authority_present(self, record: dict, *args) -> bool:
        if len(args) < 2:
            return False
        xrefs = self._jsonpath(record, "$." + args[0].strip()) or []
        target = args[1].strip().strip("'\"")
        return isinstance(xrefs, list) and any(x.get("authority") == target for x in xrefs)

    def _d_authority_id(self, record: dict, *args) -> str | None:
        if len(args) < 2:
            return None
        xrefs = self._jsonpath(record, "$." + args[0].strip()) or []
        target = args[1].strip().strip("'\"")
        if not isinstance(xrefs, list):
            return None
        for x in xrefs:
            if x.get("authority") == target:
                return x.get("id")
        return None

    def _d_union(self, record: dict, *args) -> list[str]:
        out: list[str] = []
        for arg in args:
            arg = arg.strip()
            # Handle wildcard pattern: "field[].subkey" → iterate field array, pluck subkey
            m = re.match(r"^(.+?)\[\]\.(.+)$", arg)
            if m:
                base, sub = m.group(1), m.group(2)
                arr = self._jsonpath(record, "$." + base)
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, dict) and sub in item:
                            v = item[sub]
                            if isinstance(v, str):
                                out.append(v)
                continue
            v = self._jsonpath(record, "$." + arg)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, dict) and "place" in item:
                        out.append(item["place"])
            elif isinstance(v, str):
                out.append(v)
        return list(dict.fromkeys(out))

    def _d_bool_default(self, record: dict, *args) -> bool:
        if not args:
            return False
        v = self._jsonpath(record, "$." + args[0].strip())
        if v is None:
            return len(args) > 1 and args[1].strip().lower() == "true"
        return bool(v)

    def _d_bool_dynasty_geo(self, record: dict, *_) -> bool:
        return bool(record.get("had_capital") or record.get("territory"))

    def _d_unix_ts(self, record: dict, *args) -> int | None:
        if not args:
            return None
        v = self._jsonpath(record, "$." + args[0].strip())
        if not isinstance(v, str):
            return None
        try:
            return int(datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return None

    def _d_dynasty_geo(self, record: dict, *_) -> list[float] | None:
        capitals = record.get("had_capital") or []
        if not capitals:
            return None
        first = capitals[0]
        pid = first.get("place") if isinstance(first, dict) else None
        if not pid:
            return None
        place = self._lookup_record(pid)
        if not place:
            return None
        coords = place.get("coords") or {}
        lat, lon = coords.get("lat"), coords.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return [float(lat), float(lon)]
        return None

    # ----- scorers -------------------------------------------------------

    def _score_default(self, record: dict, rule: dict, *_) -> float:
        c = rule.get("score_components", {}) or {}
        s = float(c.get("base", 1.0))
        if record.get("provenance", {}).get("deprecated"):
            s += c.get("deprecated_penalty", -100)
        return round(s, 4)

    def _score_place(self, record: dict, rule: dict, *_) -> float:
        c = rule.get("score_components", {}) or {}
        s = float(c.get("base", 1.0))
        if self._d_bool_authority_present(record, "authority_xref", "wikidata"):
            s += c.get("has_wikidata_bonus", 0)
        if self._d_bool_field_present(record, "coords"):
            s += c.get("has_coords_bonus", 0)
        if record.get("had_capital_of"):
            s += c.get("is_capital_bonus", 0)
        if "iac:Iqlim" in (record.get("@type") or []):
            s += c.get("is_iqlim_bonus", 0)
        if any(e.get("source_type") == "manual_editorial"
               for e in (record.get("provenance", {}).get("derived_from") or [])):
            s += c.get("manual_curation_bonus", 0)
        if record.get("provenance", {}).get("deprecated"):
            s += c.get("deprecated_penalty", -100)
        return round(s, 4)

    def _score_dynasty(self, record: dict, rule: dict, *_) -> float:
        c = rule.get("score_components", {}) or {}
        s = float(c.get("base", 1.0))
        if self._d_bool_authority_present(record, "authority_xref", "wikidata"):
            s += c.get("has_wikidata_bonus", 0)
        if record.get("had_capital"):
            s += c.get("has_coords_bonus", 0)
        if "iac:Caliphate" in (record.get("@type") or []):
            s += c.get("is_caliphate_bonus", 0)
        if record.get("bosworth_id"):
            s += c.get("has_bosworth_id_bonus", 0)
        t = record.get("temporal", {})
        if t.get("start_ce") and t.get("end_ce") and t["end_ce"] > t["start_ce"]:
            s += c.get("duration_log_bonus", 0) * math.log10(t["end_ce"] - t["start_ce"])
        if any(e.get("source_type") == "manual_editorial"
               for e in (record.get("provenance", {}).get("derived_from") or [])):
            s += c.get("manual_curation_bonus", 0)
        if record.get("provenance", {}).get("deprecated"):
            s += c.get("deprecated_penalty", -100)
        return round(s, 4)

    # ----- lookups -------------------------------------------------------

    def _l_prefLabels(self, record: dict, args_expr: str) -> list[str]:
        pids: list[str] = []
        for term in [t.strip() for t in args_expr.split("+")]:
            # Handle wildcard pattern: "field[].subkey"
            m = re.match(r"^(.+?)\[\]\.(.+)$", term)
            if m:
                base, sub = m.group(1), m.group(2)
                arr = self._jsonpath(record, "$." + base)
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, dict) and isinstance(item.get(sub), str):
                            pids.append(item[sub])
                continue
            v = self._jsonpath(record, "$." + term)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str):
                        pids.append(item)
                    elif isinstance(item, dict) and "place" in item:
                        pids.append(item["place"])
            elif isinstance(v, str):
                pids.append(v)
        labels: list[str] = []
        seen: set[str] = set()
        for pid in pids:
            if pid in seen:
                continue
            seen.add(pid)
            other = self._lookup_record(pid)
            if not other:
                continue
            pl = (other.get("labels", {}) or {}).get("prefLabel", {}) or {}
            for lang in ("en", "ar", "tr"):
                if pl.get(lang):
                    labels.append(pl[lang])
        return labels

    def _l_place_coords(self, record: dict, args_expr: str) -> list[float] | None:
        pid = self._jsonpath(record, "$." + args_expr.strip())
        if not isinstance(pid, str):
            return None
        other = self._lookup_record(pid)
        if not other:
            return None
        coords = other.get("coords", {}) or {}
        lat, lon = coords.get("lat"), coords.get("lon")
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return [float(lat), float(lon)]
        return None

    def _l_prefLabel_en(self, record: dict, args_expr: str) -> str | None:
        pid = self._jsonpath(record, "$." + args_expr.strip())
        if not isinstance(pid, str):
            return None
        other = self._lookup_record(pid)
        if not other:
            return None
        return ((other.get("labels", {}) or {}).get("prefLabel", {}) or {}).get("en")

    def _lookup_record(self, pid: str) -> dict | None:
        if pid in self._record_cache:
            return self._record_cache[pid]
        m = re.match(r"^iac:([a-z]+)-([0-9]{8})$", pid)
        if not m:
            return None
        ns, ord_ = m.groups()
        path = self.canonical_dir / ns / f"iac_{ns}_{ord_}.json"
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as fh:
            rec = json.load(fh)
        self._record_cache[pid] = rec
        return rec

    # ----- helpers -------------------------------------------------------

    def _infer_entity_type(self, record: dict) -> str:
        types = record.get("@type") or []
        if not types:
            raise ProjectorError("Record has no @type")
        first = types[0]
        if first.startswith("iac:"):
            return first.split(":", 1)[1].lower()
        return first.lower()

    def _load_rule(self, entity_type: str) -> dict:
        if entity_type in self._rules_cache:
            return self._rules_cache[entity_type]
        rule_path = self.rules_dir / f"{entity_type}.yaml"
        if not rule_path.exists():
            raise ProjectorError(f"No projection rule for entity_type={entity_type}")
        with rule_path.open(encoding="utf-8") as fh:
            rule = yaml.safe_load(fh)
        self._rules_cache[entity_type] = rule
        return rule


def main() -> int:
    """CLI smoke test: project all canonical records, print summary."""
    import sys
    repo = Path(__file__).resolve().parent.parent
    proj = Projector(repo)
    n = 0
    for doc in proj.project_all():
        n += 1
        print(json.dumps(doc, ensure_ascii=False, sort_keys=True)[:200])
    print(f"Projected {n} records.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
