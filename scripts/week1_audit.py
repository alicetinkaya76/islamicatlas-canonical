#!/usr/bin/env python3
"""
islamicatlas-canonical — Phase 0, Week 1
Data Layer Audit Script

Amaç: public/data/ altındaki tüm JSON ve CSV veri katmanlarını tarayıp
her biri için şema, kapsama, veri kalitesi ve çapraz referans raporu üretir.

Çıktı:
  audit_output/summary.md            — Tüm katmanların üst-düzey tablosu
  audit_output/<layer_name>.md       — Katman başına ayrıntılı rapor
  audit_output/summary.json          — Makine okunur özet (Phase 1 ETL için)
  audit_output/cross_reference.md    — Çapraz referans haritası
  audit_output/duplicates.md         — Yineleme/yedek dosya tespiti

Kullanım:
  python3 week1_audit.py --data-dir /path/to/Ars_iv/public/data \\
                         --csv-dir  /path/to/Ars_iv/data \\
                         --out      ./audit_output

Gereksinimler: Python 3.9+, sadece standart kütüphane (ek paket yok)
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# 1. Koordinat ve ID kalıpları — veri katmanları arasında farklı adlar taşıyor
# ─────────────────────────────────────────────────────────────────────────────

LAT_KEYS = {"lat", "latitude", "capital_lat", "region_center_lat"}
LON_KEYS = {"lon", "lng", "longitude", "capital_lon", "region_center_lon"}
ID_KEYS = {"id", "dynasty_id", "battle_id", "ruler_id", "event_id",
           "scholar_id", "monument_id", "place_id", "person_id"}
NAME_KEYS_TR = {"name_tr", "ht", "t", "dynasty_name_tr", "h",
                "title_tr", "label_tr"}
NAME_KEYS_AR = {"name_ar", "h", "dynasty_name_ar", "title_ar", "label_ar"}
NAME_KEYS_EN = {"name_en", "he", "dynasty_name_en", "title_en", "label_en"}
DATE_KEYS = {"date", "year", "date_ce", "date_hijri",
             "date_start_ce", "date_end_ce",
             "date_start_hijri", "date_end_hijri",
             "birth_year", "death_year", "hd", "md", "dh", "dc"}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Profil çıkarma
# ─────────────────────────────────────────────────────────────────────────────

def iter_records(data: Any):
    """Heterojen üst yapıyı (liste/dict/nested) kayıt akışına normalize eder."""
    if isinstance(data, list):
        for r in data:
            if isinstance(r, dict):
                yield r
    elif isinstance(data, dict):
        # Durum A: ID-keyed dict (ör. darpislam_detail_0.json, yaqut_detail.json)
        # Anahtarlar tümü dict değerine işaret ediyorsa, bu bir kayıt tablosudur.
        vals = list(data.values())
        if vals and all(isinstance(v, dict) for v in vals):
            # 'metadata'/'enums'/'statistics' yan başlıkları varsa Durum B'ye düş
            skip_keys = {"metadata", "enums", "statistics"}
            if not any(k in data for k in skip_keys):
                for key, val in data.items():
                    # key'i kayıt içine enjekte et (ID olarak)
                    rec = dict(val)
                    rec.setdefault("_key", key)
                    yield rec
                return

        # Durum B: Tipik altyapı {'metadata': {...}, 'places': [...], 'routes': [...]}
        for key, val in data.items():
            if key in {"metadata", "enums", "statistics"}:
                continue
            if isinstance(val, list):
                for r in val:
                    if isinstance(r, dict):
                        yield r
            elif isinstance(val, dict):
                for rk, rv in val.items():
                    if isinstance(rv, dict):
                        yield rv


def iter_sub_collections(data: Any):
    """dict altı koleksiyonların adlarını ve sayımını döndürür."""
    results = []
    if isinstance(data, dict):
        for key, val in data.items():
            if key in {"metadata", "enums", "statistics"}:
                continue
            if isinstance(val, list):
                results.append((key, len(val), "list"))
            elif isinstance(val, dict):
                results.append((key, len(val), "dict"))
    return results


def profile_field(records: list, field: str) -> dict:
    """Tek bir alan için kapsama + tip dağılımı."""
    n = len(records)
    if n == 0:
        return {"presence": 0, "coverage": 0.0, "types": {}, "null_rate": 1.0}

    present = 0
    non_null = 0
    type_counter = Counter()
    sample_values = []

    for r in records:
        if field in r:
            present += 1
            v = r[field]
            if v is None or v == "" or v == []:
                continue
            non_null += 1
            type_counter[type(v).__name__] += 1
            if len(sample_values) < 3:
                repr_v = v if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>"
                sample_values.append(str(repr_v)[:80])

    return {
        "presence": present,
        "coverage": round(present / n, 3),
        "non_null": non_null,
        "non_null_rate": round(non_null / n, 3),
        "null_rate": round(1 - non_null / n, 3),
        "types": dict(type_counter.most_common()),
        "sample": sample_values,
    }


def analyze_layer(path: Path) -> dict:
    """Tek bir JSON/CSV dosyasını analiz eder."""
    size_bytes = path.stat().st_size
    result = {
        "file": path.name,
        "path": str(path),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / 1024 / 1024, 2),
        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "md5_sample": "",
        "errors": [],
    }

    # İçerik özeti (md5 — duplicate detection için)
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            h.update(f.read(1024 * 1024))  # ilk 1 MB yeterli
        result["md5_sample"] = h.hexdigest()
    except Exception as e:  # noqa: BLE001
        result["errors"].append(f"hash: {e}")

    if path.suffix == ".csv":
        return _analyze_csv(path, result)
    if path.suffix == ".json":
        return _analyze_json(path, result)

    result["errors"].append(f"unsupported format: {path.suffix}")
    return result


def _analyze_csv(path: Path, result: dict) -> dict:
    import csv

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    result["type"] = "csv"
    result["record_count"] = len(rows)
    result["columns"] = reader.fieldnames or []
    result["column_count"] = len(result["columns"])

    if rows:
        result["field_profiles"] = {
            col: profile_field(rows, col) for col in result["columns"]
        }
        result["coord_coverage"] = _coord_coverage(rows)
        result["id_analysis"] = _id_analysis(rows)
    return result


def _analyze_json(path: Path, result: dict) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result["errors"].append(f"json parse: {e}")
        return result

    result["type"] = "json"
    result["top_level_type"] = type(data).__name__

    # Alt-koleksiyonları listele
    sub_collections = iter_sub_collections(data)
    if sub_collections:
        result["sub_collections"] = [
            {"name": n, "count": c, "kind": k} for n, c, k in sub_collections
        ]

    # Metadata varsa sakla
    if isinstance(data, dict) and "metadata" in data and isinstance(data["metadata"], dict):
        meta = data["metadata"]
        result["metadata"] = {
            k: (v if not isinstance(v, (dict, list)) else f"<{type(v).__name__}>")
            for k, v in list(meta.items())[:15]
        }

    records = list(iter_records(data))
    result["record_count"] = len(records)

    if records:
        # Alan kapsaması — tüm kayıtlarda hangi alanlar ne sıklıkla görünüyor?
        field_frequency = Counter()
        for r in records:
            field_frequency.update(r.keys())
        all_fields = sorted(field_frequency.keys())
        result["field_count"] = len(all_fields)
        result["fields"] = all_fields

        # Her alan için profil (ilk 40 alan — aşırı geniş şemalarda özet)
        result["field_profiles"] = {
            field: profile_field(records, field)
            for field in all_fields[:40]
        }

        result["coord_coverage"] = _coord_coverage(records)
        result["id_analysis"] = _id_analysis(records)
        result["name_coverage"] = _name_coverage(records)
        result["date_coverage"] = _date_coverage(records)

    return result


def _coord_coverage(records: list) -> dict:
    """Kaç kayıt koordinat taşıyor? Hangi alan adıyla?"""
    n = len(records)
    lat_fields_seen = Counter()
    lon_fields_seen = Counter()
    with_coord = 0
    out_of_range = 0
    coords_sample = []

    for r in records:
        # Düz alanlar
        lat = _find_coord(r, LAT_KEYS, lat_fields_seen)
        lon = _find_coord(r, LON_KEYS, lon_fields_seen)
        # location alt-nesne (Konya/Cairo kalıbı)
        if (lat is None or lon is None) and isinstance(r.get("location"), dict):
            loc = r["location"]
            if lat is None:
                lat = _find_coord(loc, LAT_KEYS, lat_fields_seen)
            if lon is None:
                lon = _find_coord(loc, LON_KEYS, lon_fields_seen)

        if lat is not None and lon is not None:
            with_coord += 1
            # Dünya sınırları dışında mı?
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                out_of_range += 1
            if len(coords_sample) < 3:
                coords_sample.append({"lat": lat, "lon": lon})

    return {
        "with_coord": with_coord,
        "coverage": round(with_coord / n, 3) if n else 0,
        "lat_field_names": dict(lat_fields_seen),
        "lon_field_names": dict(lon_fields_seen),
        "out_of_range": out_of_range,
        "sample": coords_sample,
    }


def _find_coord(obj: dict, keys: set, counter: Counter):
    for k in keys:
        if k in obj:
            v = obj[k]
            try:
                fv = float(v)
                counter[k] += 1
                return fv
            except (TypeError, ValueError):
                continue
    return None


def _id_analysis(records: list) -> dict:
    """ID tekil mi? Hangi alan adı kullanılıyor?"""
    id_field_counts = Counter()
    id_values_per_field = defaultdict(list)
    for r in records:
        for k in ID_KEYS:
            if k in r and r[k] not in (None, ""):
                id_field_counts[k] += 1
                id_values_per_field[k].append(r[k])
                break

    result = {"id_fields": dict(id_field_counts)}

    if id_field_counts:
        primary_id_field = id_field_counts.most_common(1)[0][0]
        values = id_values_per_field[primary_id_field]
        result["primary_id_field"] = primary_id_field
        result["id_total"] = len(values)
        result["id_unique"] = len(set(values))
        result["id_duplicates"] = len(values) - len(set(values))
        result["id_type"] = type(values[0]).__name__ if values else None
        # Örnek değerler
        result["sample_ids"] = [str(v)[:40] for v in values[:5]]

    return result


def _name_coverage(records: list) -> dict:
    """Her kayıt için kaç dilde ad var?"""
    n = len(records)
    tr = ar = en = 0
    for r in records:
        if any(r.get(k) for k in NAME_KEYS_TR):
            tr += 1
        if any(r.get(k) for k in NAME_KEYS_AR):
            ar += 1
        if any(r.get(k) for k in NAME_KEYS_EN):
            en += 1
    return {
        "turkish": round(tr / n, 3) if n else 0,
        "arabic": round(ar / n, 3) if n else 0,
        "english": round(en / n, 3) if n else 0,
    }


def _date_coverage(records: list) -> dict:
    """Tarih alanları kapsaması."""
    n = len(records)
    if n == 0:
        return {}
    dates = 0
    date_field_counts = Counter()
    for r in records:
        found = False
        for k in DATE_KEYS:
            if r.get(k) not in (None, ""):
                date_field_counts[k] += 1
                found = True
        if found:
            dates += 1
    return {
        "with_any_date": dates,
        "coverage": round(dates / n, 3),
        "date_fields_used": dict(date_field_counts.most_common(10)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Rapor üretimi
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def write_layer_report(result: dict, out_dir: Path):
    """Katman başına ayrıntılı Markdown raporu."""
    name = Path(result["file"]).stem
    report_path = out_dir / f"{name}.md"

    lines = [
        f"# Katman Denetimi: `{result['file']}`",
        "",
        f"**Yol:** `{result['path']}`  ",
        f"**Boyut:** {result['size_mb']} MB ({result['size_bytes']:,} bayt)  ",
        f"**Son değişiklik:** {result['modified']}  ",
        f"**İçerik hash (ilk 1 MB):** `{result.get('md5_sample','')}`",
        "",
    ]

    if result.get("errors"):
        lines += [
            "## ⚠️ Hatalar",
            "",
            *[f"- {e}" for e in result["errors"]],
            "",
        ]

    if result.get("type") == "json":
        lines += [
            "## Üst-düzey yapı",
            "",
            f"- **Üst tip:** `{result.get('top_level_type')}`",
            f"- **Toplam kayıt:** {result.get('record_count', 0):,}",
            f"- **Alan sayısı:** {result.get('field_count', 0)}",
            "",
        ]

        if result.get("sub_collections"):
            lines += ["### Alt koleksiyonlar", ""]
            lines += ["| Ad | Sayı | Tür |", "|---|---:|---|"]
            for sc in result["sub_collections"]:
                lines.append(f"| `{sc['name']}` | {sc['count']:,} | {sc['kind']} |")
            lines.append("")

        if result.get("metadata"):
            lines += ["### Metadata özü", "", "```json"]
            for k, v in result["metadata"].items():
                lines.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}')
            lines.append("```")
            lines.append("")

    elif result.get("type") == "csv":
        lines += [
            "## CSV özeti",
            "",
            f"- **Toplam satır:** {result.get('record_count', 0):,}",
            f"- **Sütun sayısı:** {result.get('column_count', 0)}",
            "",
        ]

    # ID analizi
    if result.get("id_analysis", {}).get("primary_id_field"):
        ida = result["id_analysis"]
        status = "✅ TEKİL" if ida["id_duplicates"] == 0 else "❌ ÇAKIŞMA VAR"
        lines += [
            "## ID analizi",
            "",
            f"- **Birincil ID alanı:** `{ida['primary_id_field']}`",
            f"- **Toplam ID:** {ida['id_total']:,}",
            f"- **Tekil ID:** {ida['id_unique']:,}",
            f"- **Yinelenen:** {ida['id_duplicates']} — {status}",
            f"- **Tip:** `{ida['id_type']}`",
            f"- **Örnek:** {', '.join(ida['sample_ids'])}",
            "",
        ]

    # Koordinat analizi
    if result.get("coord_coverage", {}).get("with_coord") is not None:
        cc = result["coord_coverage"]
        lines += [
            "## Koordinat kapsaması",
            "",
            f"- **Koordinatlı kayıt:** {cc['with_coord']:,} "
            f"(**{_fmt_pct(cc['coverage'])}**)",
            f"- **Kullanılan enlem alan adları:** "
            f"{', '.join(f'`{k}`({v})' for k,v in cc['lat_field_names'].items())}",
            f"- **Kullanılan boylam alan adları:** "
            f"{', '.join(f'`{k}`({v})' for k,v in cc['lon_field_names'].items())}",
            f"- **Dünya sınırı dışı:** {cc['out_of_range']}",
            "",
        ]

    # Ad kapsaması
    if result.get("name_coverage"):
        nc = result["name_coverage"]
        lines += [
            "## Çok dillilik",
            "",
            f"- **Türkçe ad:** {_fmt_pct(nc['turkish'])}",
            f"- **Arapça ad:** {_fmt_pct(nc['arabic'])}",
            f"- **İngilizce ad:** {_fmt_pct(nc['english'])}",
            "",
        ]

    # Tarih kapsaması
    if result.get("date_coverage", {}).get("coverage") is not None:
        dc = result["date_coverage"]
        lines += [
            "## Tarih kapsaması",
            "",
            f"- **Herhangi bir tarih alanı olan:** {dc['with_any_date']:,} "
            f"(**{_fmt_pct(dc['coverage'])}**)",
            f"- **Kullanılan tarih alanları:** "
            f"{', '.join(f'`{k}`({v})' for k,v in dc['date_fields_used'].items())}",
            "",
        ]

    # Alan profilleri — tablo
    if result.get("field_profiles"):
        lines += [
            "## Alan profili (ilk 40)",
            "",
            "| Alan | Kapsama | Null-olmayan | Tipler | Örnek |",
            "|---|---:|---:|---|---|",
        ]
        for field, prof in result["field_profiles"].items():
            types_str = ", ".join(f"{t}({n})" for t, n in prof["types"].items())
            sample = " / ".join(prof.get("sample", []))[:70].replace("|", "/")
            lines.append(
                f"| `{field}` | {_fmt_pct(prof['coverage'])} | "
                f"{_fmt_pct(prof['non_null_rate'])} | "
                f"{types_str} | {sample} |"
            )
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def write_summary(all_results: list, out_dir: Path):
    """Toplam özet Markdown + JSON."""
    summary_md = out_dir / "summary.md"
    summary_json = out_dir / "summary.json"

    total_size = sum(r.get("size_bytes", 0) for r in all_results)
    total_records = sum(r.get("record_count", 0) for r in all_results)
    total_coords = sum(
        r.get("coord_coverage", {}).get("with_coord", 0) for r in all_results
    )

    lines = [
        "# islamicatlas.org — Phase 0 Week 1 Audit Raporu",
        "",
        f"**Tarih:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Taranan dosya sayısı:** {len(all_results)}",
        f"**Toplam boyut:** {total_size / 1024 / 1024:.1f} MB",
        f"**Toplam kayıt (tahminî):** {total_records:,}",
        f"**Koordinatlı kayıt:** {total_coords:,}",
        "",
        "---",
        "",
        "## Katman özet tablosu",
        "",
        "| Dosya | Boyut (MB) | Kayıt | Alan | Koord. | ID Tekil | Son Değ. |",
        "|---|---:|---:|---:|---:|:-:|---|",
    ]

    for r in sorted(all_results, key=lambda x: x.get("size_bytes", 0), reverse=True):
        rec = r.get("record_count", 0)
        fc = r.get("field_count", r.get("column_count", "-"))
        cov = r.get("coord_coverage", {}).get("coverage")
        cov_str = _fmt_pct(cov) if cov is not None else "-"
        ida = r.get("id_analysis", {})
        if ida.get("primary_id_field"):
            id_status = "✅" if ida["id_duplicates"] == 0 else "❌"
        else:
            id_status = "-"
        lines.append(
            f"| `{r['file']}` | {r['size_mb']} | {rec:,} | {fc} | "
            f"{cov_str} | {id_status} | {r['modified'][:10]} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Kritik bulgular (otomatik çıkarıldı)",
        "",
    ]

    # Kritik bulguları çıkar
    findings = []

    for r in all_results:
        # Schema tekilliği: lat/lon alan adları
        cc = r.get("coord_coverage", {})
        lat_names = set(cc.get("lat_field_names", {}).keys())
        lon_names = set(cc.get("lon_field_names", {}).keys())
        if len(lat_names) > 1 or len(lon_names) > 1:
            findings.append(
                f"- `{r['file']}`: birden fazla koordinat alan adı kullanıyor "
                f"(lat: {lat_names}, lon: {lon_names})"
            )

        # ID çakışması
        ida = r.get("id_analysis", {})
        if ida.get("id_duplicates", 0) > 0:
            findings.append(
                f"- `{r['file']}`: **{ida['id_duplicates']} yinelenen ID** "
                f"(alan: `{ida['primary_id_field']}`)"
            )

        # Koordinat dışı
        if cc.get("out_of_range", 0) > 0:
            findings.append(
                f"- `{r['file']}`: **{cc['out_of_range']} kayıt dünya sınırları dışında**"
            )

        # Parse hatası
        if r.get("errors"):
            findings.append(f"- `{r['file']}`: parse hataları: {r['errors']}")

    if findings:
        lines += findings
    else:
        lines.append("- (Kritik düzeyde şema çakışması tespit edilmedi.)")

    lines += [
        "",
        "---",
        "",
        "## Sonraki adımlar (Week 2'ye aktarılacak)",
        "",
        "1. Yinelenen ID'lerin çözümü (varsa)",
        "2. Alan adı standardizasyonu (`lat/lng/latitude` → canonical `lat`)",
        "3. Canonical schema'da zorunlu/opsiyonel alan kararları",
        "4. Yedek/tekrar dosyaların temizlenmesi",
        "",
    ]

    summary_md.write_text("\n".join(lines), encoding="utf-8")

    # JSON çıktısı (Phase 1 ETL'in okuyacağı)
    summary_json.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "total_files": len(all_results),
                "total_size_bytes": total_size,
                "total_records": total_records,
                "layers": [
                    {
                        "file": r["file"],
                        "record_count": r.get("record_count", 0),
                        "field_count": r.get("field_count", r.get("column_count", 0)),
                        "coord_coverage": r.get("coord_coverage", {}).get("coverage", 0),
                        "primary_id_field": r.get("id_analysis", {}).get(
                            "primary_id_field"
                        ),
                        "id_duplicates": r.get("id_analysis", {}).get("id_duplicates", 0),
                    }
                    for r in all_results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_cross_ref_report(all_results: list, data_dir: Path, out_dir: Path):
    """Çapraz referans dosyalarını analiz et."""
    xref_files = [
        "dia_alam_xref.json",
        "yaqut_crossref.json",
        "le_strange_xref.json",
        "muqaddasi_xref.json",
    ]
    lines = [
        "# Çapraz Referans Haritası",
        "",
        "Bu rapor katmanlar arası mevcut köprüleri ve boşlukları gösterir.",
        "",
    ]

    for xf in xref_files:
        p = data_dir / xf
        if not p.exists():
            lines.append(f"## `{xf}` — ❌ bulunamadı")
            lines.append("")
            continue

        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # noqa: BLE001
            lines.append(f"## `{xf}` — ⚠️ parse hatası: {e}")
            lines.append("")
            continue

        lines.append(f"## `{xf}`")
        lines.append("")
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, dict):
                    lines.append(f"- `{key}`: **{len(val):,}** eşleşme (sözlük formu)")
                elif isinstance(val, list):
                    lines.append(f"- `{key}`: **{len(val):,}** kayıt (liste formu)")
        elif isinstance(data, list):
            lines.append(f"- liste, **{len(data):,}** kayıt")
        lines.append("")

    lines += [
        "---",
        "",
        "## Boşluk analizi",
        "",
        "- **Bilinen çapraz referanslar:** yukarıdaki dosyalar",
        "- **Eksik olası köprüler:**",
        "  - Science Layer scholars ↔ al-Aʿlām — mevcut xref yok",
        "  - Salibiyyat events ↔ Yâkût yerleri — mevcut xref yok",
        "  - Maqrizi yapıları ↔ Yâkût (Kahire girişi) — mevcut xref yok",
        "  - Konya yapıları ↔ Yâkût (Konya girişi) — mevcut xref yok",
        "  - Evliya places ↔ Yâkût — mevcut xref yok",
        "  - Ibn Battuta stops ↔ Yâkût / Muqaddasî — mevcut xref yok",
        "",
        "**Week 3-4 Entity Resolution pipeline'ının hedefi:** bu köprüleri otomatik+yarı-otomatik kurmak.",
        "",
    ]

    (out_dir / "cross_reference.md").write_text("\n".join(lines), encoding="utf-8")


def write_duplicates_report(all_results: list, out_dir: Path):
    """Olası yineleme/yedek dosyaları tespit et."""
    lines = [
        "# Yinelenen / Yedek Dosya Tespiti",
        "",
        "İsmi `_backup`, `.bak`, `_old`, `_v1` gibi kalıpları taşıyan dosyalar veya "
        "boyut/hash olarak aynı görünen dosyalar burada raporlanır.",
        "",
    ]

    # İsim kalıbı
    suspicious = []
    for r in all_results:
        n = r["file"].lower()
        if any(p in n for p in ("_backup", ".bak", "_old", "_v1", "_v2", ".tmp")):
            suspicious.append(r)

    lines += ["## İsim kalıbı temelli şüpheli dosyalar", ""]
    if suspicious:
        for s in suspicious:
            lines.append(f"- `{s['file']}` ({s['size_mb']} MB) → prod dışına alınmalı")
    else:
        lines.append("- (yok)")
    lines.append("")

    # Hash çakışması
    hash_groups = defaultdict(list)
    for r in all_results:
        if r.get("md5_sample"):
            hash_groups[r["md5_sample"]].append(r["file"])

    dupes = {h: files for h, files in hash_groups.items() if len(files) > 1}
    lines += ["## İçerik hash çakışması (ilk 1 MB)", ""]
    if dupes:
        for h, files in dupes.items():
            lines.append(f"- `{h[:12]}...` → {', '.join(files)}")
    else:
        lines.append("- (yok)")
    lines.append("")

    (out_dir / "duplicates.md").write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Ana akış
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", required=True, type=Path,
                        help="public/data dizini (JSON katmanları)")
    parser.add_argument("--csv-dir", type=Path, default=None,
                        help="data/ dizini (CSV katmanları), opsiyonel")
    parser.add_argument("--out", type=Path, default=Path("./audit_output"))
    parser.add_argument("--extra", nargs="*", default=[],
                        help="Ek dizinler (ör. public/data/city-atlas)")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    # Taranan dosyaları topla
    files = []
    if args.data_dir.exists():
        files += sorted(args.data_dir.glob("*.json"))
    if args.csv_dir and args.csv_dir.exists():
        files += sorted(args.csv_dir.glob("*.csv"))
    for extra in args.extra:
        p = Path(extra)
        if p.exists():
            files += sorted(p.glob("*.json"))

    if not files:
        print(f"❌ {args.data_dir} altında dosya bulunamadı", file=sys.stderr)
        sys.exit(1)

    print(f"→ {len(files)} dosya tarandı")
    all_results = []
    for f in files:
        print(f"  · {f.name} ...", end=" ", flush=True)
        res = analyze_layer(f)
        write_layer_report(res, args.out)
        all_results.append(res)
        print(f"{res.get('record_count', 0):,} kayıt")

    write_summary(all_results, args.out)
    write_cross_ref_report(all_results, args.data_dir, args.out)
    write_duplicates_report(all_results, args.out)

    print(f"\n✅ Rapor yazıldı: {args.out}/")
    print(f"   - summary.md  (üst-düzey tablo)")
    print(f"   - summary.json (makine okunur)")
    print(f"   - cross_reference.md  (köprü haritası)")
    print(f"   - duplicates.md  (yedek/tekrar tespiti)")
    print(f"   - <layer_name>.md × {len(all_results)}")


if __name__ == "__main__":
    main()
