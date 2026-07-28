#!/usr/bin/env python3
"""h31_002 — Alatlı mint'lerine eksik `derived_from_layers: ["alatli"]` etiketi.

SORUN (H29'da ölçüldü): Alatlı adapter'ı 53 kişi MINT etti ve 181 mevcut kişiyi
AUGMENT etti. Augment'lerde `derived_from_layers` etiketi var, MINT'lerde YOK.
Etki: Ulema Havuzu bu kişileri "kaynak-curie'siz" sayıyor (ölçüm: 47) → havuz
arayüzünde kaynak izi/rozeti görünmüyor. Facet etkilenmiyor (projector etiketi
`alatli:` source_id ÖNEKİNDEN türetiyor), yalnız havuz/izlenebilirlik.

KAPSAM: `provenance.derived_from[].source_id` alanı `alatli:` ile başlayan AKTİF
kayıtlarda, `derived_from_layers` listesinde "alatli" yoksa eklenir. Başka hiçbir
alan değişmez. Şema `derived_from_layers` için serbest string kabul eder (enum
yok) — şema DEĞİŞTİRİLMEZ.

GERİ ALINABİLİR: ledger + `--restore`.

Kullanım:
    python3 pipelines/migrations/h31_002_alatli_layer_tag.py --dry-run
    python3 pipelines/migrations/h31_002_alatli_layer_tag.py --apply
    python3 pipelines/migrations/h31_002_alatli_layer_tag.py --restore
"""

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PERSON = REPO / "data" / "canonical" / "person"
LEDGER = REPO / "data" / "_state" / "h31_002_alatli_layer_ledger.json"
LAYER = "alatli"


def targets():
    for f in sorted(glob.glob(str(PERSON / "*.json"))):
        p = Path(f)
        txt = p.read_text(encoding="utf-8")
        if "alatli:" not in txt:
            continue
        rec = json.loads(txt)
        if rec.get("provenance", {}).get("deprecated"):
            continue
        # gerçekten alatli kaynaklı mı (metin eşleşmesi yetmez)
        srcs = [str(x.get("source_id", "")) for x in rec.get("provenance", {}).get("derived_from", [])]
        if not any(s.startswith("alatli:") for s in srcs):
            continue
        if LAYER in (rec.get("derived_from_layers") or []):
            continue
        yield p, rec


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore", action="store_true")
    a = ap.parse_args()

    if a.restore:
        if not LEDGER.is_file():
            print("ledger yok"); return
        led = json.loads(LEDGER.read_text(encoding="utf-8"))
        n = 0
        for e in led["entries"]:
            p = REPO / e["file"]
            if not p.is_file():
                continue
            rec = json.loads(p.read_text(encoding="utf-8"))
            dfl = [x for x in (rec.get("derived_from_layers") or []) if x != LAYER]
            if dfl:
                rec["derived_from_layers"] = dfl
            else:
                rec.pop("derived_from_layers", None)
            hist = rec.get("provenance", {}).get("record_history", [])
            rec["provenance"]["record_history"] = [
                h for h in hist if "h31_002" not in (h.get("note") or "")]
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            n += 1
        print(f"geri alındı: {n}")
        return

    entries = []
    for p, rec in targets():
        pref = (rec.get("labels", {}) or {}).get("prefLabel", {}) or {}
        entries.append({"pid": rec["@id"], "file": str(p.relative_to(REPO)),
                        "name": pref.get("tr") or pref.get("en") or ""})
        if a.apply:
            rec.setdefault("derived_from_layers", []).append(LAYER)
            rec["derived_from_layers"] = sorted(set(rec["derived_from_layers"]))
            rec.setdefault("provenance", {}).setdefault("record_history", []).append({
                "change_type": "update",
                "changed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "changed_by": "pipelines/migrations/h31_002_alatli_layer_tag.py",
                "note": "h31_002: eksik derived_from_layers=['alatli'] etiketi eklendi (mint kayıtları)",
            })
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'UYGULANDI' if a.apply else 'KURU KOŞU'} — etiketlenen: {len(entries)}")
    for e in entries[:5]:
        print(f"  {e['pid']} | {e['name'][:34]}")
    if a.apply:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(
            {"migration": "h31_002_alatli_layer_tag", "count": len(entries), "entries": entries},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"ledger: {LEDGER.relative_to(REPO)} — --restore ile geri alınır")


if __name__ == "__main__":
    main()
