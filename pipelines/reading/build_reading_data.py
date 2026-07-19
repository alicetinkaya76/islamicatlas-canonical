#!/usr/bin/env python3
"""
build_reading_data.py — Çekirdek Külliyat okuma verisi üreticisi (H13 S-D D1).

Girdi : data/sources/openiti/core_batches/batch_NN.yaml (kitap listesi)
        + data/_state/openiti_local_paths.json (pid → LaCie yolu)
Çıktı : web/public/reading/<pidnum>/manifest.json + sec_NNNN.json
        + web/public/reading/core_shelf.json (raf konfigürasyonu)

TAM METİN CANONICAL'A GİRMEZ (tasarım kararı, HAFTA13_CORE_CANON_DESIGN.md).
Çıktı gitignored — LaCie klonundan deterministik yeniden üretilir; deploy'da
statik varlık olarak yüklenir.

mARkdown işleme:
  - #META# bloğu atılır; '### |+' başlıkları bölüm sınırı (seviye = | sayısı)
  - başlıksız kitaplar (Fütûh, İbn Havkal): 25 PageV etiketinde bir bölümleme
  - PageVxxPyyy etiketleri paragraf ÇAPASI olarak korunur (atıf yeteneği —
    derinlik çıtasının 1. öğesi); '# ' paragraf, '~~' devam satırı birleşir
  - ms/milestone/editorial belirteçleri temizlenir
Sürüm seçimi (Ghazali-RAG dersi): .completed > .mARkdown > en büyük dosya.

Kullanım: python3 pipelines/reading/build_reading_data.py [--batch 1]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_ROOT = REPO_ROOT / "web/public/reading"

PAGE_RE = re.compile(r"PageV(\d+)P(\d+)")
HDR_RE = re.compile(r"^### (\|+)\s*(.*)")
CLEAN_RES = [
    (re.compile(r"\bms\d+\b"), ""),               # milestone belirteci
    (re.compile(r"Milestone\d+"), ""),
    (re.compile(r"@[A-Z][A-Za-z_]*@?\d*"), ""),   # @QUOTE@ vb. editoryal
    (re.compile(r"%~%"), ""),
    (re.compile(r"\s+"), " "),
]


def pick_version(book_path: str) -> str | None:
    files = [f for f in glob.glob(book_path + "/*")
             if os.path.isfile(f) and not f.endswith((".yml", ".md"))]
    if not files:
        return None

    def rank(f: str):
        return (2 if f.endswith(".completed") else
                1 if f.endswith(".mARkdown") else 0, os.path.getsize(f))
    return max(files, key=rank)


def clean_text(s: str) -> str:
    for rex, rep in CLEAN_RES:
        s = rex.sub(rep, s)
    return s.strip()


AR_RE = re.compile(r"[\u0600-\u06FF]")


def is_junk_para(s: str) -> bool:
    """Kaynak-site ön-madde çöpü (Rafed URL'leri, görsel referansları) ve
    Arapça içermeyen sözde-paragraflar (H13 S-D tarayıcı doğrulama bulgusu)."""
    if "http://" in s or "https://" in s or re.search(r"\.(gif|jpe?g|png)\b", s):
        return True
    if len(s) > 20:
        ar = len(AR_RE.findall(s))
        if ar / max(len(s), 1) < 0.15:
            return True
    return False


def clean_title(s: str) -> str:
    """Başlıklardaki mARkdown artıkları: '** ...', önden noktalama."""
    return s.lstrip("*-–— ").strip()


def parse_book(path: str) -> tuple[list[dict], int]:
    """[(title, level, paras[{t, p}]), ...], toplam kelime."""
    sections: list[dict] = []
    cur = {"title": None, "level": 0, "paras": []}
    buf: list[str] = []
    cur_page: str | None = None
    total_words = 0
    in_meta = True

    def flush_para():
        nonlocal total_words
        if not buf:
            return
        raw = " ".join(buf)
        pages = PAGE_RE.findall(raw)
        text = clean_text(PAGE_RE.sub(" ", raw))
        if text and len(text) > 1 and not is_junk_para(text):
            total_words += len(text.split())
            cur["paras"].append(
                {"t": text, "p": f"V{pages[0][0]}P{pages[0][1]}" if pages else cur_page})
        buf.clear()

    def flush_section():
        flush_para()
        if cur["paras"] or cur["title"]:
            sections.append(dict(cur))
        cur["paras"] = []

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if in_meta:
                if line.startswith("#META#Header#End#"):
                    in_meta = False
                continue
            m = HDR_RE.match(line)
            if m:
                flush_section()
                cur["title"] = clean_title(clean_text(PAGE_RE.sub(" ", m.group(2)))) or None
                cur["level"] = len(m.group(1))
                continue
            pg = PAGE_RE.search(line)
            if pg:
                cur_page = f"V{pg.group(1)}P{pg.group(2)}"
            if line.startswith("# "):
                flush_para()
                buf.append(line[2:].rstrip("\n"))
            elif line.startswith("~~"):
                buf.append(line[2:].rstrip("\n"))
            elif line.strip():
                buf.append(line.rstrip("\n"))
    flush_section()
    # Boş bölümler (ardışık başlıklar): başlık bir SONRAKİ dolu bölüme
    # kırıntı-yolu olarak eklenir — bölüm menüsünde boş satır kalmaz.
    merged: list[dict] = []
    pending_titles: list[str] = []
    for sec in sections:
        if not sec["paras"]:
            if sec["title"]:
                pending_titles.append(sec["title"])
            continue
        if pending_titles:
            crumb = " › ".join(pending_titles[-2:])
            sec["title"] = f"{crumb} › {sec['title']}" if sec["title"] else crumb
            pending_titles = []
        merged.append(sec)
    return merged, total_words


def paginate_headerless(sections: list[dict], pages_per_sec: int = 25) -> list[dict]:
    """Tek dev 'bölüm'ü sayfa-esaslı parçalara böler."""
    paras = [p for s in sections for p in s["paras"]]
    out, chunk, first_page = [], [], None
    count = 0
    for p in paras:
        if p["p"] and (first_page is None):
            first_page = p["p"]
        chunk.append(p)
        if p["p"]:
            count += 1
        if count >= pages_per_sec:
            out.append({"title": f"{first_page} – {p['p']}", "level": 1, "paras": chunk})
            chunk, first_page, count = [], None, 0
    if chunk:
        last = next((p["p"] for p in reversed(chunk) if p["p"]), "")
        out.append({"title": f"{first_page or '...'} – {last}", "level": 1, "paras": chunk})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=1)
    args = ap.parse_args()

    batch = yaml.safe_load(
        (REPO_ROOT / f"data/sources/openiti/core_batches/batch_{args.batch:02d}.yaml")
        .read_text(encoding="utf-8"))
    local = json.loads((REPO_ROOT / "data/_state/openiti_local_paths.json")
                       .read_text(encoding="utf-8"))["paths"]
    # pid → uri haritası canonical'dan
    uri_to_pid = {}
    for p in (REPO_ROOT / "data/canonical/work").glob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("openiti_uri"):
            uri_to_pid[rec["openiti_uri"]] = (rec["@id"], rec)

    shelf = []
    for book in batch["books"]:
        uri = book["uri"]
        if uri not in uri_to_pid:
            print(f"✗ {uri}: canonical kayıt yok — atlandı")
            continue
        pid, rec = uri_to_pid[uri]
        pidnum = pid.rsplit("-", 1)[1]
        bp = local.get(pid)
        if not bp or not os.path.isdir(bp):
            print(f"✗ {uri}: yerel yol yok ({bp}) — LaCie takılı mı?")
            continue
        vf = pick_version(bp)
        if not vf:
            print(f"✗ {uri}: sürüm dosyası yok")
            continue

        sections, total_words = parse_book(vf)
        real_headers = [s for s in sections if s["title"]]
        if len(real_headers) < 3:  # başlıksız kitap → sayfa-esaslı
            sections = paginate_headerless(sections)

        out_dir = OUT_ROOT / pidnum
        out_dir.mkdir(parents=True, exist_ok=True)
        toc = []
        for i, sec in enumerate(sections):
            n_words = sum(len(p["t"].split()) for p in sec["paras"])
            first_p = next((p["p"] for p in sec["paras"] if p["p"]), None)
            toc.append({"i": i, "title": sec["title"] or f"Bölüm {i+1}",
                        "level": sec["level"] or 1, "words": n_words, "page": first_p})
            (out_dir / f"sec_{i:04d}.json").write_text(
                json.dumps({"i": i, "title": sec["title"], "paras": sec["paras"]},
                           ensure_ascii=False), encoding="utf-8")

        labels = rec.get("labels", {}).get("prefLabel", {})
        desc = rec.get("labels", {}).get("description", {}) or {}
        # yazar bloğu: canonical kişi kaydından ad + tarih + katman-ötesi bağlar
        author = None
        apid = (rec.get("authors") or [None])[0]
        if apid:
            ap = REPO_ROOT / "data/canonical/person" / f"iac_person_{apid.rsplit('-', 1)[1]}.json"
            if ap.exists():
                arec = json.loads(ap.read_text(encoding="utf-8"))
                al = arec.get("labels", {}).get("prefLabel", {})
                dt = arec.get("death_temporal") or {}
                sids = [d.get("source_id", "") for d in
                        arec.get("provenance", {}).get("derived_from", [])]
                author = {
                    "pid": apid,
                    "name_tr": al.get("tr"), "name_ar": al.get("ar"),
                    "death_ah": dt.get("start_ah"), "death_ce": dt.get("start_ce"),
                    "dia_slug": next((s.split(":", 1)[1] for s in sids
                                      if s.startswith("dia:")), None),
                    "alam_id": next((s.split(":", 1)[1] for s in sids
                                     if s.startswith("el-alam:")), None),
                }
        comp = rec.get("composition_temporal") or {}
        manifest = {
            "pid": pid, "uri": uri,
            "title_tr": labels.get("tr"), "title_ar": labels.get("ar"),
            "description_tr": desc.get("tr"), "description_en": desc.get("en"),
            "composition": {"ah": comp.get("start_ah"),
                            "ce": comp.get("start_ce") or comp.get("end_ce"),
                            "approx": comp.get("approximation")},
            "author": author,
            "author_pid": apid,
            "version_file": os.path.basename(vf),
            "sections": toc,
            "total_words": total_words,
            "n_sections": len(toc),
            "atlas_role": book.get("atlas_role"),
            "name_tr": book.get("name_tr"),
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        shelf.append({"pid": pid, "pidnum": pidnum, "uri": uri,
                      "name_tr": book.get("name_tr"), "title_ar": labels.get("ar"),
                      "atlas_role": book.get("atlas_role"),
                      "n_sections": len(toc), "total_words": total_words,
                      "author_pid": (rec.get("authors") or [None])[0]})
        print(f"✓ {uri:42s} bölüm:{len(toc):5d} kelime:{total_words:9,d} → reading/{pidnum}/")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    # KÜMÜLATİF raf: mevcut kitapları koru, bu partinin kitaplarını ekle/güncelle
    # (parti-2 koşusu parti-1'i ezmesin — H16 dersi).
    shelf_path = OUT_ROOT / "core_shelf.json"
    existing = []
    if shelf_path.exists():
        try:
            existing = json.loads(shelf_path.read_text(encoding="utf-8")).get("books", [])
        except (OSError, json.JSONDecodeError):
            existing = []
    new_pids = {b["pid"] for b in shelf}
    kept = [b for b in existing if b["pid"] not in new_pids]
    merged = kept + shelf
    shelf_path.write_text(
        json.dumps({"batches": sorted({b.get("batch", 1) for b in [batch]} |
                                      {1}), "theme": batch.get("theme"),
                    "books": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nraf: +{len(shelf)} kitap (toplam {len(merged)}) → core_shelf.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
