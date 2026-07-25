#!/usr/bin/env python3
"""detect_alatli_mint_dups.py — Alatlı mint'lerinin mevcut store kişileriyle
mükerrerliğini AD-SIRASINDAN BAĞIMSIZ tespit et (H25).

Sorun: resolver ad-sırası duyarlı ("Ali Ekrem Bolayır" mint ≠ "BOLAYIR, Ali Ekrem"
DİA) → 53 mint'in bir kısmı mevcut kişinin dublesi. Token-kümesi Jaccard (sıra-
bağımsız) + tarih (±5y) ile eşleştir.

--apply: IRONCLAD dupları (Jaccard=1.0 + tarih eşit) temizle:
  mint SOFT-DEPRECATE (provenance.deprecated + deprecated_in_favor_of=mevcut_pid;
  projector -100, geri alınabilir) — kendi aşırı-mint'imi geri alıyorum.
  (Zenginleştirme kaybı yok: Alatlı augment'i ayrı adımda mevcut kişiye eklenebilir.)
Bulanık (0.8≤J<1.0) → dedup kuyruğu, tarihçi (store'un 'merge=human' ilkesi).
"""
from __future__ import annotations
import argparse, glob, json, re, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

R = Path(__file__).resolve().parent.parent.parent
TR = str.maketrans("âîûÂÎÛıİşŞğĞçÇöÖüÜ", "aiuAIUiIsSgGcCoOuU")
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
STOP = {"el", "al", "es", "et", "ez", "en", "er", "ul", "ibn", "bin", "b", "ebu",
        "abu", "hz", "aziz", "el-", "bey", "pasa", "efendi", "sultan", "hanim",
        "hatun", "aga", "molla", "seyh", "haci"}


def toks(s):
    s = (s or "").translate(TR).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s)
    return frozenset(w for w in s.split() if w and w not in STOP and len(w) > 1)


def year_of(d):
    dt = d.get("death_temporal") or d.get("birth_temporal") or d.get("floruit_temporal") or {}
    return dt.get("start_ce")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    mints, allp = [], []
    tokidx = defaultdict(list)   # token -> [allp index] (yalnız non-mint adaylar)
    for f in glob.glob(str(R / "data" / "canonical" / "person" / "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        df = d.get("provenance", {}).get("derived_from") or []
        is_mint = df and all(str(x.get("source_id", "")).startswith("alatli:") for x in df)
        if (d.get("provenance", {}) or {}).get("deprecated"):
            continue
        y = year_of(d)
        t = toks((d.get("labels", {}).get("prefLabel", {}) or {}).get("tr")
                 or (d.get("labels", {}).get("prefLabel", {}) or {}).get("en"))
        entry = {"pid": d["@id"], "path": f, "name": (d.get("labels", {}).get("prefLabel", {})),
                 "y": y, "t": t}
        if is_mint and t:
            mints.append(entry)
        elif t:
            idx = len(allp); allp.append(entry)
            for tok in t:
                tokidx[tok].append(idx)

    ironclad, fuzzy = [], []
    for m in mints:
        cand = set()
        for tok in m["t"]:
            cand.update(tokidx.get(tok, []))
        best = None
        for ci in cand:
            c = allp[ci]
            j = len(m["t"] & c["t"]) / max(1, len(m["t"] | c["t"]))
            if best is None or j > best[1]:
                best = (c, j)
        if not best or best[1] < 0.8:
            continue
        c, j = best
        dy = (abs(m["y"] - c["y"]) if (m["y"] is not None and c["y"] is not None) else None)
        rec = {"mint_pid": m["pid"], "mint_name": m["name"].get("tr") or m["name"].get("en"),
               "existing_pid": c["pid"], "existing_name": c["name"].get("en") or c["name"].get("tr"),
               "jaccard": round(j, 2), "year": m["y"], "existing_year": c["y"],
               "year_delta": dy}
        # IRONCLAD: birebir token kümesi + ≥2 AYIRT EDİCİ token (title'lar stop'lu)
        # + tarih farkı bir ömür içinde (≤100; doğum/ölüm ekseni farkına izin —
        # Bolayır 1867/1937). Tek-token (Rabgûzî) ve Δ>100 (Mustafa Sâfî) bulanıkta.
        is_iron = (j >= 0.999 and len(m["t"]) >= 2 and dy is not None and dy <= 100)
        (ironclad if is_iron else fuzzy).append((rec, m))

    print(f"53 mint tarandı | IRONCLAD dup (J=1.0, tarih eşit): {len(ironclad)} | "
          f"bulanık (0.8≤J<1.0): {len(fuzzy)}")
    for rec, _ in ironclad:
        print(f"  DUP {rec['mint_name'][:24]:26} ⟷ {str(rec['existing_name'])[:24]:26} "
              f"({rec['existing_pid']}) J={rec['jaccard']}")
    for rec, _ in fuzzy[:10]:
        print(f"  ~   {rec['mint_name'][:24]:26} ⟷ {str(rec['existing_name'])[:24]:26} "
              f"J={rec['jaccard']} Δyıl={rec['year_delta']}")

    if args.apply:
        n = n_qid = 0
        for rec, m in ironclad:
            d = json.load(open(m["path"], encoding="utf-8"))
            # QID transfer: mint'in Alatlı QID'ini mevcut kişiye taşı (mevcut QID'siz ise)
            mint_qids = [x for x in (d.get("authority_xref") or [])
                         if x.get("authority") == "wikidata"]
            ex_path = (R / "data" / "canonical" / "person" /
                       f"iac_person_{rec['existing_pid'].rsplit('-', 1)[1]}.json")
            if mint_qids and ex_path.exists():
                ed = json.loads(ex_path.read_text(encoding="utf-8"))
                ex_has = any(x.get("authority") == "wikidata"
                             for x in (ed.get("authority_xref") or []))
                if not ex_has:
                    xr = dict(mint_qids[0])
                    xr["note"] = (xr.get("note", "") + " [mint-dedup: dublesinden taşındı]")[:250]
                    ed.setdefault("authority_xref", []).append(xr)
                    ed.setdefault("provenance", {}).setdefault("record_history", []).append({
                        "change_type": "update", "changed_at": NOW, "changed_by": ATTRIBUTED_TO,
                        "release": "v0.1.0-phase0",
                        "note": f"Alatlı QID {xr.get('id')} dublesi {m['pid']}'den taşındı (mint-dedup)."})
                    ed["provenance"]["modified"] = NOW
                    ex_path.write_text(json.dumps(ed, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
                    n_qid += 1
            # mint SOFT-DEPRECATE (kendi aşırı-mint'imi geri al)
            prov = d.setdefault("provenance", {})
            prov["deprecated"] = True
            prov["deprecated_in_favor_of"] = rec["existing_pid"]
            prov.setdefault("record_history", []).append({
                "change_type": "deprecate", "changed_at": NOW, "changed_by": ATTRIBUTED_TO,
                "release": "v0.1.0-phase0",
                "note": (f"Alatlı aşırı-mint geri alındı (H25): ad-sırası farkı yüzünden "
                         f"resolver kaçırmıştı; {rec['existing_pid']} ile aynı kişi "
                         f"(token-kümesi J={rec['jaccard']}, yıl {rec['year']}).")})
            prov["modified"] = NOW
            Path(m["path"]).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
            n += 1
        (R / "data" / "review_queue" / "alatli-mint-dups-fuzzy.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r, _ in fuzzy) + "\n", encoding="utf-8")
        print(f"\n[apply] soft-deprecate={n} | QID-taşındı={n_qid} | fuzzy→kuyruk={len(fuzzy)}")


if __name__ == "__main__":
    main()
