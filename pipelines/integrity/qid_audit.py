#!/usr/bin/env python3
"""
qid_audit.py — Wikidata QID örneklem denetimi (H10 Stage 11).

H7 close'un H8'e vaat edip hiç yapılmadığı iş (PHASE0_CLOSEOUT §4): store'daki
wikidata xref'lerinin yanlış-pozitif oranını ADR-002'nin ≤%5 hedefine karşı
ÖLÇER. Store'a yazmaz; çıktı data/_state/qid_audit_report.json + özet.

Yöntem:
  * Katmanlı örneklem (seed=42): dynasty TÜMÜ (25) + person ≤150 + place ≤200.
  * wbgetentities (50'lik batch, tanımlayıcı UA, ~1 istek/sn) → labels/aliases
    (en/ar/tr) + P570 ölüm yılı + P625 koordinat.
  * Karar kuralları (kayıt-tarafı kanıtla karşılaştırma):
      person : isim-benzerliği (token_set ≥85, normalize) VEYA ölüm ±3 yıl → OK
      place  : koordinat ≤25 km → OK; yoksa isim-benzerliği ≥85 → OK
      dynasty: isim-benzerliği ≥85 → OK
      entity silinmiş/redirect → UNRESOLVED (ayrı sayılır)
      hiçbiri → MISMATCH (yanlış-pozitif adayı; İNSAN incelemesine listelenir)

Usage: python3 pipelines/integrity/qid_audit.py [--per-ns N]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from rapidfuzz import fuzz  # noqa: E402

OUT = REPO_ROOT / "data" / "_state" / "qid_audit_report.json"
UA = ("islamicatlas-canonical/0.3 (+https://islamicatlas.org; "
      "ORCID 0000-0002-7747-6854; mailto:ali.cetinkaya@selcuk.edu.tr)")
API = "https://www.wikidata.org/w/api.php"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _record(pid: str) -> dict | None:
    ns = pid.split(":")[1].split("-")[0]
    p = REPO_ROOT / "data" / "canonical" / ns / f"iac_{ns}_{pid.rsplit('-', 1)[1]}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _hav_km(a, b, c, d):
    p = math.pi / 180
    x = 0.5 - math.cos((c - a) * p) / 2 + math.cos(a * p) * math.cos(c * p) * (1 - math.cos((d - b) * p)) / 2
    return 12742 * math.asin(math.sqrt(x))


def fetch_entities(qids: list[str]) -> dict:
    out = {}
    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        r = sess.get(API, params={
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "labels|aliases|claims", "languages": "en|ar|tr",
            "format": "json"}, timeout=60)
        r.raise_for_status()
        out.update(r.json().get("entities", {}))
        time.sleep(1.0)
    return out


def wd_names(ent: dict) -> list[str]:
    names = []
    for lang in ("en", "ar", "tr"):
        lab = (ent.get("labels") or {}).get(lang, {}).get("value")
        if lab:
            names.append(lab)
        for al in (ent.get("aliases") or {}).get(lang, []):
            names.append(al.get("value", ""))
    return [n for n in names if n]


def wd_death_year(ent: dict):
    for cl in (ent.get("claims") or {}).get("P570", []):
        try:
            t = cl["mainsnak"]["datavalue"]["value"]["time"]  # +1111-00-00T...
            return int(t[1:5])
        except Exception:
            continue
    return None


def wd_coords(ent: dict):
    for cl in (ent.get("claims") or {}).get("P625", []):
        try:
            v = cl["mainsnak"]["datavalue"]["value"]
            return v["latitude"], v["longitude"]
        except Exception:
            continue
    return None


def rec_names(rec: dict) -> list[str]:
    out = []
    labels = rec.get("labels") or {}
    for v in (labels.get("prefLabel") or {}).values():
        if isinstance(v, str):
            out.append(v)
    for arr in (labels.get("altLabel") or {}).values():
        if isinstance(arr, list):
            out.extend(a for a in arr if isinstance(a, str))
    return out


def name_sim(rec: dict, ent: dict) -> int:
    rn = [_norm(x) for x in rec_names(rec)]
    wn = [_norm(x) for x in wd_names(ent)]
    if not rn or not wn:
        return 0
    return max(fuzz.token_set_ratio(a, b) for a in rn for b in wn)


def verdict(ns: str, rec: dict, ent: dict) -> tuple[str, dict]:
    ev: dict = {"name_sim": name_sim(rec, ent)}
    if ns == "person":
        ry = (rec.get("death_temporal") or {}).get("start_ce")
        wy = wd_death_year(ent)
        ev["death_rec"], ev["death_wd"] = ry, wy
        if ev["name_sim"] >= 85 or (isinstance(ry, int) and isinstance(wy, int)
                                    and abs(ry - wy) <= 3):
            return "OK", ev
    elif ns == "place":
        rc = rec.get("coords") or {}
        wc = wd_coords(ent)
        if wc and isinstance(rc.get("lat"), (int, float)):
            ev["km"] = round(_hav_km(rc["lat"], rc["lon"], wc[0], wc[1]), 1)
            if ev["km"] <= 25:
                return "OK", ev
        if ev["name_sim"] >= 85:
            return "OK", ev
    else:
        if ev["name_sim"] >= 85:
            return "OK", ev
    return "MISMATCH", ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-ns", type=int, default=None,
                    help="ns başına örnek üst sınırı (varsayılan: dynasty tümü, person 150, place 200)")
    args = ap.parse_args()
    caps = {"dynasty": 10 ** 9, "person": 150, "place": 200}
    if args.per_ns:
        caps = {k: args.per_ns for k in caps}

    import sqlite3
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")
    rows = conn.execute(
        "SELECT authority_id, pid FROM authority_xref WHERE authority='wikidata'"
    ).fetchall()
    conn.close()

    rng = random.Random(42)
    by_ns: dict[str, list] = {}
    for qid, pid in rows:
        ns = pid.split(":")[1].split("-")[0]
        by_ns.setdefault(ns, []).append((qid, pid))
    sample = []
    for ns, items in sorted(by_ns.items()):
        rng.shuffle(items)
        sample.extend((ns, q, p) for q, p in items[:caps.get(ns, 100)])
    print(f"[qid_audit] evren={len(rows)} örneklem={len(sample)} "
          f"({ {ns: min(len(v), caps.get(ns, 100)) for ns, v in by_ns.items()} })")

    entities = fetch_entities(sorted({q for _, q, _ in sample}))
    stats: dict = {}
    mismatches, unresolved = [], []
    for ns, qid, pid in sample:
        ent = entities.get(qid)
        st = stats.setdefault(ns, {"OK": 0, "MISMATCH": 0, "UNRESOLVED": 0})
        if not ent or "missing" in ent or ent.get("id") != qid:
            st["UNRESOLVED"] += 1
            unresolved.append({"qid": qid, "pid": pid,
                               "redirect_to": (ent or {}).get("id")})
            continue
        rec = _record(pid)
        if rec is None:
            st["UNRESOLVED"] += 1
            unresolved.append({"qid": qid, "pid": pid, "note": "record missing"})
            continue
        v, ev = verdict(ns, rec, ent)
        st[v] += 1
        if v == "MISMATCH":
            mismatches.append({"qid": qid, "pid": pid, "ns": ns,
                               "rec_label": rec_names(rec)[:1],
                               "wd_label": wd_names(ent)[:1], **ev})

    report = {
        "_meta": {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "universe": len(rows), "sampled": len(sample), "seed": 42,
                  "target": "ADR-002 false-positive <= 5%",
                  "rules": "person: name>=85 OR death±3 · place: coords<=25km "
                           "OR name>=85 · dynasty: name>=85"},
        "stats": stats,
        "mismatches": mismatches,
        "unresolved": unresolved,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    for ns, st in sorted(stats.items()):
        tot = sum(st.values())
        print(f"  {ns}: OK={st['OK']} MISMATCH={st['MISMATCH']} "
              f"UNRESOLVED={st['UNRESOLVED']}  (FP-oranı ~{st['MISMATCH']/tot:.1%})")
    print(f"[qid_audit] → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
