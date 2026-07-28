#!/usr/bin/env python3
"""h31_001 — "noktalı i" artefaktı onarımı (canonical etiketlerde).

SORUN (H29'da ölçüldü, kökü H31'de bulundu): mağazada 1.567 kayıt "i"+U+0307
(COMBINING DOT ABOVE) taşıyor. Kök neden: Türkçe-duyarsız `str.title()` —
"ABDÜLLATİF".title() → "Abdüllati̇f". Küçük "i+nokta"nın BİRLEŞİK hâli Unicode'da
YOK, dolayısıyla NFC bunu düzeltmez. Etki: artefakt kelime ORTASINDAysa arama
token'ı kırılıyordu ("Fatma Aliye" aktif kaydı bulunamıyordu).

Kök neden H31'de kapatıldı: `.title()` çağrıları `tr_title()` ile değiştirildi
(ei1/canonicalize.py, h21_ei1_triage.py, an_cat_b_resolve.py). Bu migration
GEÇMİŞ veriyi onarır.

KAPSAM (dar ve güvenli):
    Yalnız `"i" + U+0307` dizisi → `"i"`. U+0307 genel olarak SİLİNMEZ
    (bilimsel transliterasyonda anlamlı: "ṁ", "ṅ"). Yalnız etiket/metin
    alanlarında (labels.*, note, nisba/laqab/kunya/nasab) çalışır; pid, curie,
    tarih, koordinat alanlarına DOKUNMAZ.

GERİ ALINABİLİR: her değişiklik `data/_state/h31_001_dotted_i_ledger.json`'a
(pid, alan yolu, önce, sonra) yazılır; `--restore` ledger'dan geri alır.
provenance.record_history'ye "repair" girdisi eklenir (append-only defter).

Kullanım:
    python3 pipelines/migrations/h31_001_dotted_i_repair.py --dry-run
    python3 pipelines/migrations/h31_001_dotted_i_repair.py --apply
    python3 pipelines/migrations/h31_001_dotted_i_repair.py --restore
"""

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "data" / "canonical"
LEDGER = REPO / "data" / "_state" / "h31_001_dotted_i_ledger.json"

DOTTED = "i̇"          # "i" + COMBINING DOT ABOVE
NAMESPACES = ["person", "place", "work", "dynasty", "event", "institution"]

# Yalnız METİN alanları onarılır. pid/curie/tarih/koordinat asla.
TEXT_KEYS = {"labels", "note", "nisba", "laqab", "kunya", "nasab", "profession"}


def fix_text(v):
    """Bir değeri (str/list/dict) onarır; (yeni_değer, değişti_mi) döner."""
    if isinstance(v, str):
        nv = v.replace(DOTTED, "i")
        return nv, nv != v
    if isinstance(v, list):
        out, ch = [], False
        for x in v:
            nx, c = fix_text(x)
            out.append(nx); ch = ch or c
        return out, ch
    if isinstance(v, dict):
        out, ch = {}, False
        for k, x in v.items():
            nx, c = fix_text(x)
            out[k] = nx; ch = ch or c
        return out, ch
    return v, False


def iter_records():
    for ns in NAMESPACES:
        for f in sorted(glob.glob(str(CANON / ns / "*.json"))):
            p = Path(f)
            txt = p.read_text(encoding="utf-8")
            if DOTTED not in txt:
                continue
            yield p, json.loads(txt)


def run(apply_changes: bool):
    entries, touched = [], 0
    for path, rec in iter_records():
        changed_fields = {}
        for key in list(rec.keys()):
            if key not in TEXT_KEYS:
                continue
            nv, ch = fix_text(rec[key])
            if ch:
                changed_fields[key] = {"before": rec[key], "after": nv}
                rec[key] = nv
        if not changed_fields:
            continue
        touched += 1
        entries.append({
            "pid": rec.get("@id"),
            "file": str(path.relative_to(REPO)),
            "fields": list(changed_fields),
            "changes": changed_fields,
        })
        if apply_changes:
            hist = rec.setdefault("provenance", {}).setdefault("record_history", [])
            # ŞEMA UYUMU (H22 dersi tekrarı): change_type enum'u 'repair'
            # İÇERMEZ (create/update/merge/split/deprecate/revive) ve
            # 'changed_by' ZORUNLU. Şemayı genişletmek son çaredir → mevcut
            # sözleşmeye uyuluyor: type='update', gerekçe note'ta.
            hist.append({
                "change_type": "update",
                "changed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "changed_by": "pipelines/migrations/h31_001_dotted_i_repair.py",
                "note": ("h31_001: 'i'+U+0307 (Türkçe .title() artefaktı) → 'i'; "
                         "alanlar: " + ", ".join(changed_fields)),
            })
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return entries, touched


def restore():
    if not LEDGER.is_file():
        print("ledger yok — geri alınacak bir şey bulunamadı"); return
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    n = 0
    for e in led["entries"]:
        p = REPO / e["file"]
        if not p.is_file():
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        for k, ch in e["changes"].items():
            rec[k] = ch["before"]
        hist = rec.get("provenance", {}).get("record_history", [])
        rec["provenance"]["record_history"] = [
            h for h in hist if "h31_001" not in (h.get("note") or "")
        ]
        p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        n += 1
    print(f"geri alındı: {n} kayıt")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore", action="store_true")
    a = ap.parse_args()

    if a.restore:
        restore(); return

    entries, touched = run(apply_changes=a.apply)
    print(f"{'UYGULANDI' if a.apply else 'KURU KOŞU'} — onarılan kayıt: {touched}")
    for e in entries[:6]:
        k = e["fields"][0]
        b = json.dumps(e["changes"][k]["before"], ensure_ascii=False)[:70]
        af = json.dumps(e["changes"][k]["after"], ensure_ascii=False)[:70]
        print(f"  {e['pid']}\n    önce : {b}\n    sonra: {af}")
    if a.apply:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(
            {"migration": "h31_001_dotted_i_repair", "count": touched, "entries": entries},
            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"ledger: {LEDGER.relative_to(REPO)} ({touched} kayıt) — --restore ile geri alınır")


if __name__ == "__main__":
    main()
