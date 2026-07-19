#!/usr/bin/env python3
"""
openiti_titles_augment.py — OpenITI eserlerine GERÇEK başlıklar + okuma
linki + dil/tefsir düzeltmeleri (H13 S-B).

Ölçülen boşluk: 9,104 OpenITI eserinin TAMAMI Arapça başlıksız ve
prefLabel.tr'si URI kelimesi ("BiharAnwar") — kütüphane görünümü bunlarla
kurulamaz.

Kaynak-1  data/sources/openiti/openiti_github_metadata_light_20261124.csv
          (resmî GitHub klon metadata'sı, 24 Kas 2025; sürüm-düzeyi
          title_ar/title_lat; 'pri' sürüm tercih edilir).
Kaynak-2  data/sources/openiti/openiti_all_books_fixed.csv (LaCie tam-klon
          kataloğu, 2026-07-07; lang AR/PER, tafsir_flag, n_versions,
          yerel book_path). DİKKAT: bu dosyanın author_name/title_ar
          kolonlarının ~8,000'i OpenITI YML şablon placeholder'ıdır
          ("Ibn Fulān", "Kitāb al-Muʾallif") — başlık için KULLANILMAZ;
          başlık otoritesi Kaynak-1'dir.

Uygulanan (kayıt başına, history notlu):
  - prefLabel.ar  = title_ar          (gap-fill)
  - prefLabel.tr  : mevcut değer URI-kelimesiyse ve title_lat varsa →
                    eski değer altLabel.tr'ye İNER, prefLabel.tr=title_lat
                    (görüntü-düzeltmesi; eski değer KORUNUR, ezilmez)
  - original_language: LaCie lang=PER ise 'ar'→'fa' DÜZELTMESİ (355 kitap)
  - subjects     += 'tafsir'          (tafsir_flag=1 ise ve yoksa)
  - note         += sürüm sayısı + GitHub okuma linki (kullanıcı kararı:
                    "metadata + link"; tam metin sitede değil)
  - yerel book_path → data/_state/openiti_local_paths.json (ileriki
    site-içi okuma fazının girdisi; canonical'a yazılmaz)

Idempotent: marker notu görülen kayıt atlanır.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
MARKER = "openiti-titles augment"

_PLACEHOLDER_TITLES = {"Kitāb al-Muʾallif", "Kitab al-Muallif"}


def load_github_titles() -> dict[str, dict]:
    """book_uri → {title_ar, title_lat, read_url} ('pri' sürüm öncelikli)."""
    out: dict[str, dict] = {}
    path = REPO_ROOT / "data/sources/openiti/openiti_github_metadata_light_20261124.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            book = row.get("book") or ""
            if not book:
                continue
            cand = {
                "title_ar": (row.get("title_ar") or "").strip(),
                "title_lat": (row.get("title_lat") or "").strip(),
                "url": (row.get("url") or "").strip(),
                "pri": (row.get("status") or "") == "pri",
            }
            cur = out.get(book)
            if cur is None or (cand["pri"] and not cur["pri"]) \
                    or (not cur["title_ar"] and cand["title_ar"]):
                out[book] = cand
    return out


def load_lacie() -> dict[str, dict]:
    out: dict[str, dict] = {}
    path = REPO_ROOT / "data/sources/openiti/openiti_all_books_fixed.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            b = row.get("book_uri") or ""
            if b:
                out[b] = row
    return out


def split_title(v: str) -> tuple[str, list[str]]:
    """GitHub başlıkları ' :: ' ayraçlı bileşik olabilir (kısa :: uzun) —
    ilki görüntü başlığı, kalanlar altLabel."""
    parts = [s.strip() for s in v.split(" :: ") if s.strip()]
    return (parts[0], parts[1:]) if parts else (v, [])


def read_link(raw_url: str) -> str:
    """raw.githubusercontent.com/OpenITI/<repo>/master/… → insan-okur blob."""
    m = re.match(r"https://raw\.githubusercontent\.com/OpenITI/([^/]+)/master/(.+)", raw_url)
    if not m:
        return raw_url
    return f"https://github.com/OpenITI/{m.group(1)}/blob/master/{m.group(2)}"


def main() -> int:
    gh = load_github_titles()
    lacie = load_lacie()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    stats = {"applied": 0, "already": 0, "no_meta": 0,
             "ar_filled": 0, "tr_swapped": 0, "fa_fixed": 0, "tafsir": 0}
    local_paths: dict[str, str] = {}

    for path in sorted((REPO_ROOT / "data/canonical/work").glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        uri = rec.get("openiti_uri")
        if not uri:
            continue
        hist = rec.get("provenance", {}).get("record_history", [])
        if any(MARKER in (h.get("note") or "") for h in hist):
            stats["already"] += 1
            continue
        meta = gh.get(uri)
        lc = lacie.get(uri) or {}
        if lc.get("book_path"):
            local_paths[rec["@id"]] = lc["book_path"]
        if not meta and not lc:
            stats["no_meta"] += 1
            continue

        labels = rec.setdefault("labels", {})
        pref = labels.setdefault("prefLabel", {})
        changed = []

        if meta and meta["title_ar"] and meta["title_ar"] not in _PLACEHOLDER_TITLES \
                and not pref.get("ar"):
            main, rest = split_title(meta["title_ar"])
            pref["ar"] = main[:500]
            if rest:
                alt_ar = labels.setdefault("altLabel", {}).setdefault("ar", [])
                for rr in rest[:3]:
                    if rr not in alt_ar:
                        alt_ar.append(rr[:500])
            changed.append("ar-title")
            stats["ar_filled"] += 1

        # URI-kelimesi görüntü düzeltmesi: eski değer altLabel'a İNER (korunur)
        cur_tr = pref.get("tr") or ""
        uri_word = uri.split(".", 1)[1] if "." in uri else ""
        if meta and meta["title_lat"] and cur_tr == uri_word \
                and meta["title_lat"] != cur_tr:
            alt = labels.setdefault("altLabel", {}).setdefault("tr", [])
            if cur_tr and cur_tr not in alt:
                alt.append(cur_tr)
            main, rest = split_title(meta["title_lat"])
            pref["tr"] = main[:500]
            for rr in rest[:3]:
                if rr not in alt:
                    alt.append(rr[:500])
            changed.append("tr-display")
            stats["tr_swapped"] += 1

        if lc.get("lang") == "PER" and rec.get("original_language") == "ar":
            rec["original_language"] = "fa"
            changed.append("lang-fa")
            stats["fa_fixed"] += 1

        if lc.get("tafsir_flag") == "1":
            subs = rec.setdefault("subjects", [])
            if "tafsir" not in subs:
                subs.append("tafsir")
                changed.append("tafsir")
                stats["tafsir"] += 1

        if meta and meta["url"]:
            link = read_link(meta["url"])
            nv = lc.get("n_versions") or ""
            tag = f"OpenITI{' ' + nv + ' sürüm' if nv else ''} · Okuma: {link}"
            note = rec.get("note") or ""
            if "github.com/OpenITI" not in note:
                rec["note"] = (note + (" · " if note else "") + tag)[:2000]
                changed.append("read-link")

        if not changed:
            continue
        hist.append({
            "change_type": "update", "changed_at": now,
            "changed_by": ATTRIBUTED_TO, "release": "v0.1.0-phase0",
            "note": f"{MARKER} (H13 S-B): {'+'.join(changed)} — GitHub klon "
                    f"metadata 2025-11-24 + LaCie katalog 2026-07-07.",
        })
        rec["provenance"]["modified"] = now
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        stats["applied"] += 1

    (REPO_ROOT / "data/_state/openiti_local_paths.json").write_text(
        json.dumps({"_doc": "Yerel tam-metin yolları (LaCie klonu) — site-içi "
                            "okuma FAZI girdisi; canonical'a yazılmaz.",
                    "paths": local_paths}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"[openiti_titles] applied={stats['applied']} already={stats['already']} "
          f"no-meta={stats['no_meta']} | ar-filled={stats['ar_filled']} "
          f"tr-swapped={stats['tr_swapped']} fa-fixed={stats['fa_fixed']} "
          f"tafsir+={stats['tafsir']} local-paths={len(local_paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
