#!/usr/bin/env python3
"""
dia_travel_places.py — DİA seyahat kenarları → person.active_in_places
(H11 S11b).

dia_travel.json: 4,241 kişi (dia slug) → 8,052 {p: yer adı, a: travel_to|
stayed_at, s: sıra}. Yer adları TR serbest metin, koordinatsız ve tarihsiz.

İsim-tek sinyalle Tier-2 auto-match YASAK (ADR-008 doktrini) — bu yüzden
fuzzy değil, BELİRSİZLİK-KORUMALI BİREBİR eşleme kullanılır:
  norm(ad) == norm(store prefLabel|altLabel)  VE  aday pid TEKİL
İki+ pid'e çıkan ad (Şam×2 gibi mağaza mükerrerleri) ya da hiç çıkmayan ad
→ pending. travel_to/stayed_at ayrımı active_in_places'te taşınamaz (şema
düz pid dizisi) → tip detayı pending dosyasında korunur.

Append-only + idempotent (uniqueItems doğal koruma; marker notu bir kez).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipelines._lib.entity_resolver import EntityResolver  # noqa: E402  (normalize)

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
MARKER = "dia-travel augment"


def main() -> int:
    travel = json.loads((REPO_ROOT / "data/sources/dia/dia_travel.json")
                        .read_text(encoding="utf-8"))
    conn = sqlite3.connect(REPO_ROOT / "data/_index/lookup.sqlite")

    norm = EntityResolver._normalize_name
    # Artikel eşdeğerliği (H11 S11b kanıtı): 'Kahire' 209 kenarla eşleşmedi
    # çünkü mağaza etiketi 'El-Kâhire' — el-/al- orthografik artikeldir,
    # anlam taşımaz; İKİ TARAFTA da soyulmuş varyant eklenir. (Halep/Haleb
    # b-p, Semerkant/Samarqand gibi ses-değişimli TR ekzonimleri BİLEREK
    # kapsam dışı: fuzzy'ye kayar; mağaza mükerrerleri birleşmeden alias da
    # yazılamaz — pending'de kalırlar.)
    _ARTICLES = ("el ", "al ", "es ", "as ", "en ", "an ", "ez ", "et ")

    def variants(n: str):
        yield n
        for art in _ARTICLES:
            if n.startswith(art):
                yield n[len(art):]

    name_to_pids: dict[str, set] = defaultdict(set)
    for text, pid in conn.execute(
            "SELECT l.text, l.pid FROM label l "
            "JOIN entity_bracket b ON b.pid = l.pid "
            "WHERE b.entity_type = 'place'"):
        for v in variants(norm(text)):
            name_to_pids[v].add(pid)

    slug_to_pid: dict[str, str] = {}
    for prefix in ("dia:", "dia-chunks:"):
        for sid, pid in conn.execute(
                "SELECT source_id, pid FROM source_curie WHERE source_id LIKE ?",
                (prefix + "%",)):
            slug_to_pid.setdefault(sid.split(":", 1)[1], pid)
    conn.close()

    # 1) ayrık yer adlarını sınıflandır
    distinct: dict[str, int] = defaultdict(int)
    for edges in travel.values():
        for e in edges:
            if e.get("p"):
                distinct[e["p"]] += 1
    resolved: dict[str, str] = {}
    ambiguous: dict[str, list] = {}
    unmatched: dict[str, int] = {}
    for name, cnt in distinct.items():
        pids: set = set()
        for v in variants(norm(name)):
            pids |= name_to_pids.get(v, set())
        if len(pids) == 1:
            resolved[name] = next(iter(pids))
        elif len(pids) > 1:
            ambiguous[name] = sorted(pids)
        else:
            unmatched[name] = cnt

    # 2) kişi kayıtlarına uygula
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"persons_touched": 0, "edges_applied": 0, "edges_pending": 0,
             "person_unresolved": 0}
    pending_edges: dict[str, list] = {}

    for slug, edges in sorted(travel.items()):
        pid = slug_to_pid.get(slug)
        if not pid:
            stats["person_unresolved"] += 1
            continue
        place_pids, kept = [], []
        for e in edges:
            tgt = resolved.get(e.get("p") or "")
            if tgt and tgt != pid:
                place_pids.append(tgt)
                stats["edges_applied"] += 1
            else:
                kept.append(e)
                stats["edges_pending"] += 1
        if kept:
            pending_edges[pid] = kept
        if not place_pids:
            continue

        path = REPO_ROOT / "data/canonical/person" / f"iac_person_{pid.rsplit('-', 1)[1]}.json"
        rec = json.loads(path.read_text(encoding="utf-8"))
        cur = rec.get("active_in_places") or []
        new = [p for p in dict.fromkeys(place_pids) if p not in cur]
        if not new:
            continue
        rec["active_in_places"] = cur + new
        hist = rec.setdefault("provenance", {}).setdefault("record_history", [])
        if not any(MARKER in (h.get("note") or "") for h in hist):
            hist.append({
                "change_type": "update", "changed_at": now,
                "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
                "note": f"{MARKER} (H11 S11b): active_in_places from "
                        f"dia_travel.json (belirsizlik-korumalı birebir "
                        f"etiket eşlemesi; fuzzy yok).",
            })
        rec["provenance"]["modified"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        stats["persons_touched"] += 1

    out = {
        "_doc": "dia_travel dönüşüm artıkları (H11 S11b): belirsiz/eşleşmeyen "
                "adlar + tip detayı (travel_to/stayed_at).",
        "ambiguous_names": ambiguous,
        "unmatched_names": dict(sorted(unmatched.items(), key=lambda kv: -kv[1])),
        "pending_edges": pending_edges,
    }
    (REPO_ROOT / "data/_state/dia_travel_pending.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[dia_travel_places] names: resolved={len(resolved)} "
          f"ambiguous={len(ambiguous)} unmatched={len(unmatched)} | "
          f"edges: applied={stats['edges_applied']} pending={stats['edges_pending']} | "
          f"persons touched={stats['persons_touched']} "
          f"unresolved-person={stats['person_unresolved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
