#!/usr/bin/env python3
"""H22 — inceleme kuyruklarının MEKANİK hijyeni.

BU SCRIPT HİÇBİR EŞLEŞMEYİ KABUL VEYA RET ETMEZ.
Yaptığı tek şey SIRALAMA (triage lane işaretleme) ve MÜKERRER AYIKLAMA'dır.
Hiçbir satır silinmez; yalnızca kayıtlara bilgilendirici alanlar eklenir.

Adımlar
-------
1) SÜPERSEDİNG  — aynı kaynağın yeniden koşulmuş (rerun) kuyruğu otoritedir.
   Eski dosya önce `_archive/` altına zaman damgalı kopyalanır; sonra kesişen
   satırlara `superseded_by` eklenir. ZORUNLU ÖN DOĞRULAMA: yalnız-eski
   kayıtların akıbeti `data/_index/lookup.sqlite:source_curie` üzerinden
   denetlenir; doğrulama yapılmadan süperseding UYGULANMAZ.
2) DÜŞÜK BİLGİLİ ETİKET — en uzun etiketi <=4 karakter olan kayıtlar
   `low_info_label: true` ile işaretlenir ve `_low_information_labels.jsonl`e
   KOPYALANIR (orijinalden silinmez). 2 harflik dizgeden gelen 1.0 skorun
   ayırt edici değeri yoktur. (<=6 eşiği Fes/Kûfe/Rey gibi gerçek toponimleri
   yediği için bilinçli olarak KULLANILMAZ.)
3) GÜÇLÜ KANIT KULVARI — `fast_track: true`. ONAY DEĞİLDİR; yalnızca
   tarihçinin önce bakacağı kulvardır.
4) BERABERLİK — ilk iki adayın skoru eşitse `tie: true`. Ayırt edici sinyal
   matematiksel olarak yoktur; tarihçi toplu ele alabilsin diye işaretlenir.

Kullanım
--------
    python3 pipelines/integrity/h22_queue_hygiene.py --dry-run
    python3 pipelines/integrity/h22_queue_hygiene.py

Idempotenttir: ikinci koşu hiçbir dosyayı değiştirmez.
Yalnız `data/review_queue/` altında ve `data/_state/` içindeki rapor
dosyasında yazar; `data/canonical/` ve diğer pipeline dosyalarına dokunmaz.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUEUE_DIR = REPO / "data" / "review_queue"
ARCHIVE_DIR = QUEUE_DIR / "_archive"
LOW_INFO_PATH = QUEUE_DIR / "_low_information_labels.jsonl"
LOOKUP_DB = REPO / "data" / "_index" / "lookup.sqlite"
REPORT_PATH = REPO / "data" / "_state" / "h22_queue_hygiene_report.json"

# (eski dosya, yeni/otorite dosya) — yeni tur eskisini süperseder.
SUPERSEDE_PAIRS = [
    ("ei1.jsonl", "h21-ei1.jsonl"),
    ("darp-islam.jsonl", "h20-darpislam.jsonl"),
]

# Adım 2 eşiği. 6'ya ÇIKARMAYIN: gerçek kısa toponimleri (Fes, Kûfe, Rey) yer.
LOW_INFO_MAX_LABEL_LEN = 4

FAST_TRACK_MIN_FEATURES = 2.0
FAST_TRACK_MIN_SCORE = 0.85
FAST_TRACK_MIN_MARGIN = 0.05

# Bu dosyalar "deferred şablonu" değildir (farklı şema) — dokunulmaz.
REQUIRED_KEYS = {"extracted_record_id", "extracted_summary", "candidates"}


# --------------------------------------------------------------------------
# yardımcılar
# --------------------------------------------------------------------------

def dumps(obj) -> str:
    """Kuyruk dosyalarındaki mevcut serileştirmeyle bayt-bayt aynı çıktı."""
    return json.dumps(obj, ensure_ascii=False)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_deferred_template(records: list[dict]) -> bool:
    return bool(records) and REQUIRED_KEYS.issubset(records[0].keys())


def deferred_queue_files() -> list[Path]:
    out = []
    for path in sorted(QUEUE_DIR.glob("*.jsonl")):
        if path.name.startswith("_"):
            continue
        try:
            records = read_jsonl(path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if is_deferred_template(records):
            out.append(path)
    return out


def longest_label_len(record: dict) -> int:
    """extracted_summary.labels içindeki en uzun dizginin uzunluğu."""
    labels = (record.get("extracted_summary") or {}).get("labels") or {}
    best = 0
    for value in labels.values():
        if not isinstance(value, dict):
            continue
        for entry in value.values():
            items = entry if isinstance(entry, list) else [entry]
            for text in items:
                if isinstance(text, str):
                    best = max(best, len(text.strip()))
    return best


def candidate_signals(record: dict) -> tuple[bool, bool]:
    """(fast_track, tie) — saf, yan etkisiz ölçüt değerlendirmesi."""
    candidates = record.get("candidates") or []
    if not candidates:
        return False, False

    top = candidates[0] if isinstance(candidates[0], dict) else {}
    score0 = top.get("score")
    if not isinstance(score0, (int, float)):
        return False, False

    n_features = (top.get("feature_scores") or {}).get("n_features", 0) or 0

    if len(candidates) < 2:
        margin = 1.0  # tek aday varsa fark = 1.0 sayılır
        tie = False
    else:
        second = candidates[1] if isinstance(candidates[1], dict) else {}
        score1 = second.get("score")
        if isinstance(score1, (int, float)):
            margin = score0 - score1
            tie = score0 == score1
        else:
            margin = 1.0
            tie = False

    fast_track = (
        float(n_features) >= FAST_TRACK_MIN_FEATURES
        and float(score0) > FAST_TRACK_MIN_SCORE
        and margin > FAST_TRACK_MIN_MARGIN
    )
    return fast_track, tie


# --------------------------------------------------------------------------
# adım 1 — zorunlu ön doğrulama
# --------------------------------------------------------------------------

def verify_supersede_pairs() -> dict:
    """Yalnız-eski kayıtların akıbetini doğrula.

    Süperseding UYGULANMADAN ÖNCE koşulması zorunludur. lookup.sqlite
    okunamazsa doğrulama başarısız sayılır ve süperseding atlanır.
    """
    result: dict = {"ok": False, "pairs": {}, "error": None}

    if not LOOKUP_DB.exists():
        result["error"] = f"lookup.sqlite yok: {LOOKUP_DB}"
        return result

    try:
        conn = sqlite3.connect(f"file:{LOOKUP_DB}?mode=ro", uri=True)
        try:
            curies = {row[0] for row in conn.execute("SELECT source_id FROM source_curie")}
        finally:
            conn.close()
    except sqlite3.Error as exc:  # pragma: no cover
        result["error"] = f"source_curie okunamadı: {exc}"
        return result

    for old_name, new_name in SUPERSEDE_PAIRS:
        old_path, new_path = QUEUE_DIR / old_name, QUEUE_DIR / new_name
        if not old_path.exists() or not new_path.exists():
            result["error"] = f"eksik dosya: {old_name} / {new_name}"
            return result

        old_ids = [r["extracted_record_id"] for r in read_jsonl(old_path)]
        new_ids = {r["extracted_record_id"] for r in read_jsonl(new_path)}
        overlap = sorted({i for i in old_ids if i in new_ids})
        only_old = sorted({i for i in old_ids if i not in new_ids})
        in_curie = sorted(i for i in only_old if i in curies)
        no_curie = sorted(i for i in only_old if i not in curies)

        result["pairs"][old_name] = {
            "superseded_by": new_name,
            "old_total": len(old_ids),
            "new_total": len(new_ids),
            "overlap": len(overlap),
            "only_old": len(only_old),
            "only_old_in_source_curie": len(in_curie),
            "only_old_no_curie": len(no_curie),
            "only_old_no_curie_sample": no_curie[:10],
            "overlap_ids": overlap,
            "no_curie_ids": no_curie,
        }

    result["ok"] = True
    return result


# --------------------------------------------------------------------------
# ana akış
# --------------------------------------------------------------------------

def archive_old_file(path: Path, stamp: str, dry_run: bool) -> dict:
    """Eski dosyayı zaman damgalı olarak arşivle.

    Arşiv, hijyen ÖNCESİ tek seferlik enstantanedir. Bu yüzden idempotans
    ölçütü içerik karşılaştırması DEĞİL, arşivin varlığıdır: ilk koşudan
    sonra dosya işaretlenmiş olacağı için içerik zorunlu olarak değişir;
    içerik karşılaştırılsaydı her koşu yeni bir kopya üretirdi.
    """
    digest = sha256_file(path)
    existing = sorted(ARCHIVE_DIR.glob(f"{path.stem}.*{path.suffix}"))
    if existing:
        return {
            "action": "already_archived",
            "path": str(existing[0]),
            "sha256": sha256_file(existing[0]),
        }

    target = ARCHIVE_DIR / f"{path.stem}.{stamp}{path.suffix}"
    if not dry_run:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return {"action": "archived", "path": str(target), "sha256": digest}


def run(dry_run: bool) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    verification = verify_supersede_pairs()
    if not verification["ok"]:
        print(f"HATA: ön doğrulama başarısız — {verification['error']}", file=sys.stderr)
        print("Süperseding UYGULANMADI (ön doğrulama zorunludur).", file=sys.stderr)
        return {"aborted": True, "verification": verification}

    # süperseding haritası: eski dosya adı -> (yeni ad, kesişen id kümesi, orphan id kümesi)
    supersede_map = {
        old: (
            info["superseded_by"],
            set(info["overlap_ids"]),
            set(info["no_curie_ids"]),
        )
        for old, info in verification["pairs"].items()
    }

    archive_actions: dict[str, dict] = {}
    if not dry_run:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for old_name in supersede_map:
        archive_actions[old_name] = archive_old_file(QUEUE_DIR / old_name, stamp, dry_run)

    per_file: dict[str, dict] = {}
    low_info_rows: list[str] = []
    files_changed: list[str] = []

    for path in deferred_queue_files():
        records = read_jsonl(path)
        original = [dumps(r) for r in records]

        new_name, overlap_ids, orphan_ids = supersede_map.get(path.name, (None, set(), set()))

        counts = {
            "total": len(records),
            "superseded": 0,
            "orphan_no_curie": 0,
            "low_info": 0,
            "fast_track": 0,
            "tie": 0,
        }

        for record in records:
            rid = record.get("extracted_record_id")

            # 1) süperseding — satır SİLİNMEZ, yalnız işaretlenir
            if new_name and rid in overlap_ids:
                record["superseded_by"] = new_name
                counts["superseded"] += 1
            elif new_name and rid in orphan_ids:
                record["orphan_check"] = "no_curie"
                counts["orphan_no_curie"] += 1

            # 2) düşük bilgili etiket
            is_low_info = longest_label_len(record) <= LOW_INFO_MAX_LABEL_LEN
            if is_low_info:
                record["low_info_label"] = True
                counts["low_info"] += 1

            # 3) + 4) güçlü kanıt kulvarı / beraberlik
            fast_track, tie = candidate_signals(record)
            if fast_track:
                record["fast_track"] = True
                counts["fast_track"] += 1
            if tie:
                record["tie"] = True
                counts["tie"] += 1

            # Kopya, TÜM işaretler eklendikten SONRA alınır; aksi halde ikinci
            # koşuda disk'ten okunan kayıt fazladan alan taşır ve idempotans bozulur.
            if is_low_info:
                low_info_rows.append(dumps({"_source_queue": path.name, **record}))

        updated = [dumps(r) for r in records]
        changed = updated != original
        counts["changed"] = changed
        per_file[path.name] = counts

        if changed:
            files_changed.append(path.name)
            if not dry_run:
                path.write_text("".join(line + "\n" for line in updated), encoding="utf-8")

    # düşük bilgili etiket dosyası — deterministik, tam yeniden üretim
    low_info_blob = "".join(line + "\n" for line in low_info_rows)
    low_info_changed = (
        not LOW_INFO_PATH.exists()
        or sha256_file(LOW_INFO_PATH) != sha256_bytes(low_info_blob.encode("utf-8"))
    )
    if low_info_changed and not dry_run:
        LOW_INFO_PATH.write_text(low_info_blob, encoding="utf-8")

    totals = {
        key: sum(f[key] for f in per_file.values())
        for key in ("total", "superseded", "orphan_no_curie", "low_info", "fast_track", "tie")
    }

    # "İnceleme yükü": süperseden ve düşük bilgili satırlar tarihçinin ana
    # kuyruğundan düşer (SİLİNMEZ — yalnızca ayrı kulvara alınır).
    review_load = {
        "definition": (
            "before = tüm deferred kuyruk satırları; "
            "after = süperseden VEYA düşük-bilgili olmayan satırlar "
            "(hiçbir satır silinmedi, yalnızca kulvara ayrıldı)"
        ),
        "before": totals["total"],
        "after": totals["total"] - totals["superseded"] - totals["low_info"],
        "lanes": {
            "superseded": totals["superseded"],
            "low_info_label": totals["low_info"],
            "fast_track": totals["fast_track"],
            "tie": totals["tie"],
        },
    }

    report = {
        "_doc": (
            "H22 kuyruk hijyeni — MEKANİK sıralama ve mükerrer ayıklama. "
            "Hiçbir eşleşme kabul/ret edilmedi, hiçbir satır silinmedi. "
            "fast_track bir ONAY DEĞİLDİR, yalnızca inceleme sırasıdır."
        ),
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "thresholds": {
            "low_info_max_label_len": LOW_INFO_MAX_LABEL_LEN,
            "low_info_threshold_rejected": 6,
            "fast_track_min_n_features": FAST_TRACK_MIN_FEATURES,
            "fast_track_min_score": FAST_TRACK_MIN_SCORE,
            "fast_track_min_margin": FAST_TRACK_MIN_MARGIN,
        },
        "supersede_verification": {
            "ok": verification["ok"],
            "pairs": {
                old: {k: v for k, v in info.items() if not k.endswith("_ids")}
                for old, info in verification["pairs"].items()
            },
        },
        "archive": archive_actions,
        "per_file": per_file,
        "totals": totals,
        "review_load": review_load,
        "files_changed": files_changed,
        "low_information_labels_file": {
            "path": str(LOW_INFO_PATH.relative_to(REPO)),
            "rows": len(low_info_rows),
            "changed": low_info_changed,
        },
    }

    if not dry_run:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return report


def print_summary(report: dict) -> None:
    if report.get("aborted"):
        return

    mode = "DRY-RUN" if report["dry_run"] else "UYGULANDI"
    print(f"=== H22 kuyruk hijyeni [{mode}] ===")

    print("\n-- ön doğrulama (yalnız-eski kayıtların akıbeti) --")
    for old, info in report["supersede_verification"]["pairs"].items():
        print(
            f"  {old} -> {info['superseded_by']}: "
            f"eski={info['old_total']} yeni={info['new_total']} "
            f"kesişim={info['overlap']} yalnız-eski={info['only_old']} "
            f"(curie'de var={info['only_old_in_source_curie']}, "
            f"YOK={info['only_old_no_curie']})"
        )

    print("\n-- arşiv --")
    for old, act in report["archive"].items():
        print(f"  {old}: {act['action']} -> {act['path']}")

    print("\n-- dosya başına --")
    header = f"  {'dosya':28} {'toplam':>7} {'süpers':>7} {'orphan':>7} {'düşük':>7} {'hızlı':>7} {'berab':>7}  değişti"
    print(header)
    for name, f in report["per_file"].items():
        print(
            f"  {name:28} {f['total']:7} {f['superseded']:7} {f['orphan_no_curie']:7} "
            f"{f['low_info']:7} {f['fast_track']:7} {f['tie']:7}  {f['changed']}"
        )

    t = report["totals"]
    print(
        f"  {'TOPLAM':28} {t['total']:7} {t['superseded']:7} {t['orphan_no_curie']:7} "
        f"{t['low_info']:7} {t['fast_track']:7} {t['tie']:7}"
    )

    rl = report["review_load"]
    print(f"\n-- inceleme yükü -- önce={rl['before']} sonra={rl['after']}")
    print(f"-- değişen dosya sayısı: {len(report['files_changed'])}")
    li = report["low_information_labels_file"]
    print(f"-- {li['path']}: {li['rows']} satır (değişti={li['changed']})")


def main() -> int:
    parser = argparse.ArgumentParser(description="H22 — inceleme kuyruğu mekanik hijyeni")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="hiçbir şey yazma, yalnızca ne olacağını raporla",
    )
    args = parser.parse_args()

    report = run(dry_run=args.dry_run)
    if report.get("aborted"):
        return 1
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
