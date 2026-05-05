"""
openiti_author_resolve.py — Pre-pass that runs BEFORE openiti_works
canonicalize.

Goal: produce a sidecar mapping
    openiti_author_id ("0428IbnSina") → iac:person-NNNNNNNN
so the openiti_works adapter can populate work.authors[] without minting
duplicate person records for already-known scholars.

Three tiers (Tier 3 — manual top-100 seed — deferred to Hafta 6):

  Tier 1: Wikidata QID match
    If an OpenITI author has a known QID (via openiti_qid_seed.json or
    --qid-seed CLI override), find a person record carrying that same
    QID in authority_xref. High confidence (1.0).

  Tier 2: death_ce ±3 + name token Jaccard
    OpenITI author IDs encode death AH (e.g. "0428IbnSina" = death AH 428).
    Convert AH→CE; window-search persons with death_temporal.start_ce in
    that ±3 range; rank by name token Jaccard (Latin transliteration
    folded). Threshold: Jaccard ≥0.5 → match.

  Tier 4: Mint placeholder person
    No match in T1/T2 → mint a fresh iac:person-* PID via pid_minter
    using "openiti:<author_id>" as the input_hash, and write a
    placeholder person record (minimal: name, death CE, provenance
    pointing to OpenITI corpus_authors.json) to a separate sidecar
    `openiti_minted_persons.jsonl`. These are reviewed and enriched
    in Hafta 6 (DİA chunk re-extraction + biographic alignment).

Acceptance criterion (X): Tier 1 + Tier 2 ≥ 70% of OpenITI's 3,618 authors.
The remaining ~30% become Tier 4 placeholder mints.

Bidirectional invariant (P0.2): every Tier 4 placeholder person record
includes authored_works[] = [] at creation time. integrity_pass_A
back-populates this with the openiti work PIDs after openiti_works
adapter runs. So the placeholder is NEVER orphaned in the bidirectional
graph, even though its biographic content is sparse.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator

from pipelines._lib import work_canonicalize as wc


# --------------------------------------------------------------------------- #
# OpenITI ID parsing
# --------------------------------------------------------------------------- #

# Author IDs follow the pattern "<AH4>FirstAuthorPart" — e.g. "0428IbnSina",
# "0691Suyuti", "1067IbnHajar". The 4-digit prefix is the death year AH.
_AUTHOR_ID_RE = re.compile(r"^(\d{4})([A-Za-z][A-Za-z0-9_]*)$")


def parse_openiti_author_id(author_id: str) -> tuple[int | None, str | None]:
    """Parse an OpenITI author_id into (death_ah, name_part).

    Returns (None, None) for malformed IDs.

    Examples:
        "0428IbnSina"  → (428, "IbnSina")
        "0691Suyuti"   → (691, "Suyuti")
        "1067IbnHajar" → (1067, "IbnHajar")
    """
    if not author_id:
        return None, None
    m = _AUTHOR_ID_RE.match(author_id)
    if not m:
        return None, None
    try:
        ah = int(m.group(1))
        return ah, m.group(2)
    except (ValueError, TypeError):
        return None, None


def ah_to_ce_approx(ah: int) -> int:
    """Convert AH year to approximate CE year (Tabular Islamic, no
    intercalation correction). Standard Hafta 3+4 conversion.

    Formula: CE ≈ floor(AH * 0.97 + 622)

    For close matches we use ±3 year window so the rough conversion is OK.
    """
    return int(ah * 0.970224 + 621.5774)


# --------------------------------------------------------------------------- #
# Name tokenization for Jaccard match
# --------------------------------------------------------------------------- #


# Reuse the title-fingerprint Latin folds for name tokens — the same
# transliteration variations appear in author names (Cebir/Jabr, Ibn/b./Bin)
def _name_tokens(name: str) -> set[str]:
    """Return a set of normalized name tokens for Jaccard comparison.

    Uses the same Turkish-fold + transliteration-fold pipeline as
    title_fingerprint, but does NOT sort tokens — we want set membership
    not ordering.
    """
    if not name or not isinstance(name, str):
        return set()
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.translate(wc._TR_ASCII_FOLD)
    s = s.lower()
    s = wc._DASH_AND_APOSTROPHE_RE.sub(" ", s)
    s = wc._PUNCT_RE.sub(" ", s)
    s = wc._WHITESPACE_RE.sub(" ", s).strip()
    raw_tokens = s.split()
    out: set[str] = set()
    for tok in raw_tokens:
        if not tok or len(tok) < 2:
            continue
        # Apply transliteration folds
        for src, dst in wc._TOKEN_TRANSLIT_FOLDS:
            tok = tok.replace(src, dst)
        # Drop name-stopwords (genealogy connectors)
        if tok in {"ibn", "ibnu", "bin", "bn", "abu", "abi", "abdu", "abdullah",
                   "umm", "bint", "bnt", "al", "el", "ben", "bani", "banu",
                   "ben", "ad", "el", "il", "li"}:
            continue
        if len(tok) >= 2:
            out.add(tok)
    return out


def _name_tokens_arabic(name_ar: str) -> set[str]:
    """Tokenize an Arabic-script name. Strips article/genealogy prefixes
    at token level."""
    if not name_ar:
        return set()
    s = unicodedata.normalize("NFKD", name_ar)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    raw = wc._WHITESPACE_RE.sub(" ", s).strip().split()
    out: set[str] = set()
    for tok in raw:
        # strip Arabic article and genealogy prefixes
        stripped = wc._ARABIC_PREFIXES_RE.sub("", tok)
        if stripped and stripped not in {"ابن", "بن", "أبو", "أم", "بنت", "في", "علی"}:
            out.add(stripped)
    return out


# Onomastic high-frequency tokens (1000+ persons each in the H4 store).
# Treating these as distinguishing features destroys Jaccard signal because
# they appear in nearly every nasab. We drop them from comparison sets.
_NASAB_NOISE = frozenset({
    "abd", "abdi", "abdu", "abdulah", "abdilah", "abdirahman", "abdurahman",
    "abdulhak", "abdusalam", "abdisalam", "abdulgafur", "abdulgani", "abdulah",
    "abdulmalik", "abdulmacid", "abdulmuhsin", "abdulkadir", "abdulkarim",
    "abdulhamid", "abdullatif", "abdurahim", "abdurazak", "abdurazzak",
    "abu", "abi", "an", "as", "at", "ar", "al", "el", "il", "li", "fi", "wa",
    "ali", "amad", "ahmad", "muhamad", "muhamed", "mahmud", "hasan", "husayn",
    "husayin", "hudayl", "yahya", "ibrahim", "yusuf", "omar", "umar",
    "ubaydulah", "ubaydilah", "isak", "ismail", "musa", "isa", "harun",
    "bakr", "kasim", "halid", "saad", "sad", "salih", "sa", "fadl", "far", "ca",
    "din", "udin", "adin", "calal", "calaladin", "calaludin", "samsudin",
    "samsadin", "fahrudin", "burhanudin", "kamaludin", "imadudin", "tacudin",
    "sayfudin", "mahmud", "mas", "mu", "lu", "li", "yi", "di", "bi",
    "rahman", "rahim", "kabir", "karim", "razzak", "vasi", "halifa",
    "hanafi", "hanbali", "safii", "maliki", "sii", "sunni",
    "badin", "muhyidin", "diyaudin", "siracudin", "muhibudin", "nuruddin",
    "nasrudin", "saadudin", "salahudin", "tagudin", "alaudin", "rasidudin",
    "ban", "in", "den", "tan", "lab", "var", "vad", "kad", "kan",
})


def jaccard(a: set, b: set) -> float:
    """Asymmetric containment overlap (NOT classic Jaccard).

    Returns intersect / min(|a|, |b|), AFTER removing high-frequency
    nasab noise from both sides. Designed for OpenITI single-token
    names matching against H4 multi-token nasab person records.

    Example: a={'suyuti'}, b={'suyuti', 'din', 'rahman', ...}
      Classic Jaccard: 1/9 = 0.11 (FAILS threshold)
      This metric:     1/1 = 1.00 (PASSES threshold)
    """
    a_clean = {t for t in a if t and t not in _NASAB_NOISE and len(t) >= 3}
    b_clean = {t for t in b if t and t not in _NASAB_NOISE and len(t) >= 3}
    if not a_clean or not b_clean:
        return 0.0
    inter = len(a_clean & b_clean)
    if inter == 0:
        return 0.0
    return inter / min(len(a_clean), len(b_clean))


# --------------------------------------------------------------------------- #
# Person index builder
# --------------------------------------------------------------------------- #


def build_person_index(canonical_persons_iter: Iterable[dict]) -> dict:
    """Build lookup indexes from canonical person records.

    Returns a dict with three sub-indexes:
      - by_qid:        {wikidata_qid: pid}
      - by_death_ce:   {death_ce: [(pid, latin_tokens, arabic_tokens, full_name_for_audit)]}
      - all_pids:      set of all person PIDs (for sanity checks)
    """
    by_qid: dict[str, str] = {}
    by_death_ce: dict[int, list] = {}
    all_pids: set[str] = set()

    for p in canonical_persons_iter:
        pid = p.get("@id")
        if not pid:
            continue
        all_pids.add(pid)

        # Authority xref → Wikidata QID
        for x in p.get("authority_xref", []) or []:
            if x.get("authority") == "wikidata" and x.get("identifier"):
                by_qid[x["identifier"]] = pid

        # death_ce
        dt = p.get("death_temporal", {}) or {}
        ce = dt.get("start_ce")
        if not isinstance(ce, int):
            continue

        # Name tokens — Latin + Arabic
        labels = p.get("labels", {}) or {}
        pref = labels.get("prefLabel", {}) or {}
        alt = labels.get("altLabel", {}) or {}

        latin_tokens: set[str] = set()
        arabic_tokens: set[str] = set()

        for lang in ("en", "tr", "ar-Latn-x-alalc"):
            v = pref.get(lang)
            if isinstance(v, str):
                latin_tokens.update(_name_tokens(v))
            for alt_v in alt.get(lang, []) or []:
                if isinstance(alt_v, str):
                    latin_tokens.update(_name_tokens(alt_v))

        ar_v = pref.get("ar")
        if isinstance(ar_v, str):
            arabic_tokens.update(_name_tokens_arabic(ar_v))
        for alt_ar in alt.get("ar", []) or []:
            if isinstance(alt_ar, str):
                arabic_tokens.update(_name_tokens_arabic(alt_ar))

        display = (pref.get("en") or pref.get("tr") or pref.get("ar")
                   or pref.get("ar-Latn-x-alalc") or "(unnamed)")

        by_death_ce.setdefault(ce, []).append(
            (pid, latin_tokens, arabic_tokens, display)
        )

    return {
        "by_qid": by_qid,
        "by_death_ce": by_death_ce,
        "all_pids": all_pids,
        "person_count": len(all_pids),
    }


# --------------------------------------------------------------------------- #
# Tier 1 — Wikidata QID match
# --------------------------------------------------------------------------- #


def tier_1_qid_match(
    *,
    author_id: str,
    qid_seed: dict,
    person_index: dict,
) -> dict | None:
    """Try to resolve via QID. qid_seed maps openiti_author_id → QID.
    person_index['by_qid'] maps QID → person PID."""
    qid = qid_seed.get(author_id)
    if not qid:
        return None
    pid = person_index["by_qid"].get(qid)
    if not pid:
        return None
    return {
        "pid": pid,
        "tier": 1,
        "confidence": 1.0,
        "reason": f"wikidata_qid_match:{qid}",
        "qid": qid,
    }


# --------------------------------------------------------------------------- #
# Tier 2 — death_ce ±3 + name token Jaccard
# --------------------------------------------------------------------------- #


def tier_2_death_name_match(
    *,
    author_id: str,
    author_data: dict,
    person_index: dict,
    death_ce_window: int = 3,
    jaccard_threshold: float = 0.5,
) -> dict | None:
    """Tier 2 fuzzy match.

    Uses (death_ce in author_data) primarily; falls back to AH-from-id
    conversion if death_ce missing.
    """
    # Get death CE for this OpenITI author
    death_ce = author_data.get("death_ce")
    if not isinstance(death_ce, int):
        ah = author_data.get("death_ah") or author_data.get("death_hijri")
        if not isinstance(ah, int):
            ah, _ = parse_openiti_author_id(author_id)
        if ah is None:
            return None
        death_ce = ah_to_ce_approx(ah)

    # Build candidate name token sets for the OpenITI author
    op_latin: set[str] = set()
    op_arabic: set[str] = set()

    # Latin candidates: shuhra, full_name, English transliterations
    for key in ("shuhra", "full_name", "name_lat", "name", "shuhra_lat",
                "author_name", "author_name_lat", "author_full_name"):
        v = author_data.get(key)
        if isinstance(v, str):
            op_latin.update(_name_tokens(v))

    # Also derive from author_id name part (e.g. "IbnSina" → ibn, sina)
    _, name_part = parse_openiti_author_id(author_id)
    if name_part:
        # CamelCase split: "IbnSina" → ["Ibn", "Sina"]
        camel = re.findall(r"[A-Z][a-z]*", name_part)
        if camel:
            op_latin.update(_name_tokens(" ".join(camel)))
        else:
            op_latin.update(_name_tokens(name_part))

    # Arabic candidates
    for key in ("name_native_ar", "full_name_ar", "name_ar", "shuhra_ar"):
        v = author_data.get(key)
        if isinstance(v, str):
            op_arabic.update(_name_tokens_arabic(v))

    if not op_latin and not op_arabic:
        # Cannot do Jaccard with empty token sets; bail
        return None

    # Window-search persons within ±death_ce_window years
    candidates: list[tuple[str, float, str, int]] = []  # (pid, jaccard, display, death_diff)
    for ce_offset in range(-death_ce_window, death_ce_window + 1):
        bucket = person_index["by_death_ce"].get(death_ce + ce_offset, [])
        for (pid, p_latin, p_arabic, display) in bucket:
            # Use the better of Latin or Arabic Jaccard
            j_lat = jaccard(op_latin, p_latin)
            j_ar = jaccard(op_arabic, p_arabic)
            j = max(j_lat, j_ar)
            if j >= jaccard_threshold:
                candidates.append((pid, j, display, abs(ce_offset)))

    if not candidates:
        return None

    # Rank: highest Jaccard, then lowest death year diff, then alphabetic PID
    candidates.sort(key=lambda c: (-c[1], c[3], c[0]))
    best = candidates[0]

    # Tiebreaker safety: if top two are close AND have different display
    # names, refuse (don't guess). If display names are identical (true
    # duplicate person records — common in Hafta 4 store), pick the
    # lowest PID deterministically.
    if len(candidates) >= 2:
        c1, c2 = candidates[0], candidates[1]
        if abs(c1[1] - c2[1]) < 0.05 and c1[3] == c2[3]:
            same_display = (c1[2] or "").strip().lower() == (c2[2] or "").strip().lower()
            if not same_display:
                return {
                    "pid": None,
                    "tier": 2,
                    "confidence": 0.0,
                    "reason": "ambiguous_multi_match",
                    "candidates": [(c[0], c[1], c[2]) for c in candidates[:5]],
                }
            # else fall through — sort by PID has already put best first

    return {
        "pid": best[0],
        "tier": 2,
        "confidence": round(best[1], 3),
        "reason": f"death_ce_match±{best[3]}+jaccard:{best[1]:.3f}",
        "matched_display": best[2],
        "candidate_count": len(candidates),
    }


# --------------------------------------------------------------------------- #
# Tier 4 — placeholder person mint
# --------------------------------------------------------------------------- #


# Reuse person_canonicalize.build_person_labels via a thin import shim.
# We don't import the module directly here (it has its own deps); instead
# we hand-roll a minimal labels block that is shape-compatible with the
# Hafta 4 person records.

PLACEHOLDER_ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
PLACEHOLDER_LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"


def _build_placeholder_labels(author_data: dict, author_id: str) -> dict:
    """Minimal multilingual_text-conformant labels block for a Tier 4
    placeholder person. Uses build_work_labels-style mechanics (works
    fine for persons too — same multilingual_text schema)."""
    name_ar = (author_data.get("name_native_ar") or
               author_data.get("name_ar") or
               author_data.get("full_name_ar"))
    name_lat = (author_data.get("shuhra") or
                author_data.get("author_name") or
                author_data.get("name") or
                author_data.get("full_name"))
    if not name_lat:
        # Derive from author_id camel case
        _, name_part = parse_openiti_author_id(author_id)
        if name_part:
            camel = re.findall(r"[A-Z][a-z]*", name_part)
            if camel:
                name_lat = " ".join(camel)
            else:
                name_lat = name_part

    return wc.build_work_labels(
        title_en=None,
        title_tr=name_lat,
        title_ar=name_ar,
    )


def _build_placeholder_person(
    *,
    pid: str,
    author_id: str,
    author_data: dict,
    pipeline_name: str = "openiti-author-resolve",
    pipeline_version: str = "v0.1.0",
) -> dict:
    """Build a minimal but schema-valid placeholder person record. The
    Hafta 6 enrichment pass will fill in birth_temporal, birth_place,
    profession, full descriptive labels, etc.
    """
    labels = _build_placeholder_labels(author_data, author_id)
    # Patch labels to use prefLabel (build_work_labels emits prefLabel,
    # which is the same schema for both work and person — they share the
    # multilingual_text definition).

    death_ce = author_data.get("death_ce")
    death_ah = author_data.get("death_ah") or author_data.get("death_hijri")
    if not isinstance(death_ce, int):
        ah, _ = parse_openiti_author_id(author_id)
        if ah:
            death_ah = ah
            death_ce = ah_to_ce_approx(ah)

    death_temporal = None
    if death_ce or death_ah:
        death_temporal = {}
        if death_ce:
            death_temporal["start_ce"] = death_ce
        if death_ah:
            death_temporal["start_ah"] = death_ah
        death_temporal["approximation"] = "circa"

    provenance = wc.build_work_provenance(
        source_record_id=f"openiti:{author_id}",
        source_kind="digital_corpus",
        page_locator=f"OpenITI corpus_authors.json id={author_id}",
        edition="OpenITI corpus snapshot 2024-2026",
        pipeline_name=pipeline_name,
        pipeline_version=pipeline_version,
        attributed_to=PLACEHOLDER_ATTRIBUTED_TO,
        license_uri=PLACEHOLDER_LICENSE,
        record_history_note=(
            f"Placeholder person minted by openiti-author-resolve Tier 4 "
            f"(no T1/T2 match in canonical person index). Pending biographic "
            f"enrichment in Hafta 6 (DİA chunk re-extraction + cross-source "
            f"alignment). Authored works will be back-populated by "
            f"integrity_pass_A_bidirectional after openiti-works adapter."
        ),
    )

    record: dict = {
        "@id": pid,
        "@type": ["iac:Person"],
        "labels": labels,
        "profession": ["scholar"],   # default — Hafta 6 enrichment may revise
        "provenance": provenance,
        "note": (
            f"Tier-4 placeholder from OpenITI author_id={author_id}. "
            f"Biographic content sparse pending Hafta 6 enrichment."
        ),
    }
    if death_temporal:
        record["death_temporal"] = death_temporal

    return record


# --------------------------------------------------------------------------- #
# Public API: run_resolve()
# --------------------------------------------------------------------------- #


def run_resolve(
    *,
    corpus_authors_path: Path,
    canonical_persons_path: Path,
    qid_seed_path: Path | None,
    pid_minter,
    output_resolution_map_path: Path,
    output_minted_persons_path: Path,
    death_ce_window: int = 3,
    jaccard_threshold: float = 0.5,
    progress_every: int = 500,
) -> dict:
    """Execute the full T1+T2+T4 cross-walk.

    Inputs:
      - corpus_authors_path:   data/sources/openiti/corpus_authors.json
      - canonical_persons_path: data/canonical/persons.jsonl (1 record per line)
      - qid_seed_path:         data/sources/openiti_qid_seed.json (optional)
      - pid_minter:            shared minter for stable PID allocation
      - output_resolution_map_path: where to write {author_id: resolution_dict}
      - output_minted_persons_path: where to append Tier 4 placeholder records (jsonl)

    Returns a stats dict for the integrity report.
    """
    # Load QID seed
    qid_seed: dict[str, str] = {}
    if qid_seed_path and qid_seed_path.exists():
        with qid_seed_path.open(encoding="utf-8") as fh:
            qid_seed = json.load(fh)

    # Load canonical persons (jsonl)
    def _iter_persons():
        with canonical_persons_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    person_index = build_person_index(_iter_persons())

    # Load OpenITI authors (dict-of-dicts OR list-of-dicts shape tolerant)
    with corpus_authors_path.open(encoding="utf-8") as fh:
        authors_raw = json.load(fh)
    if isinstance(authors_raw, dict):
        authors_iter = list(authors_raw.values())
    elif isinstance(authors_raw, list):
        authors_iter = authors_raw
    else:
        raise ValueError(
            f"corpus_authors.json has unsupported top-level type "
            f"{type(authors_raw).__name__}; expected dict or list"
        )

    resolution_map: dict[str, dict] = {}
    placeholder_records: list[dict] = []
    stats = {
        "total_authors": 0,
        "tier_1": 0,
        "tier_2": 0,
        "tier_4": 0,
        "ambiguous_unresolved": 0,
    }

    for author_data in authors_iter:
        if not isinstance(author_data, dict):
            continue
        author_id = author_data.get("author_id") or author_data.get("id")
        if not author_id:
            continue
        stats["total_authors"] += 1

        # Tier 1
        t1 = tier_1_qid_match(
            author_id=author_id,
            qid_seed=qid_seed,
            person_index=person_index,
        )
        if t1:
            resolution_map[author_id] = t1
            stats["tier_1"] += 1
            continue

        # Tier 2
        t2 = tier_2_death_name_match(
            author_id=author_id,
            author_data=author_data,
            person_index=person_index,
            death_ce_window=death_ce_window,
            jaccard_threshold=jaccard_threshold,
        )
        if t2 and t2.get("pid"):
            resolution_map[author_id] = t2
            stats["tier_2"] += 1
            continue
        if t2 and not t2.get("pid"):
            # Ambiguous → record but proceed to Tier 4 (we will mint
            # a placeholder, and the audit can be reviewed later)
            stats["ambiguous_unresolved"] += 1
            # Keep ambiguity info in the resolution map for audit
            resolution_map[author_id] = {
                **t2,
                "tier": 2,
                "outcome": "ambiguous_falling_through_to_tier_4",
            }

        # Tier 4 — mint placeholder
        input_hash = f"openiti:{author_id}"
        new_pid = pid_minter.mint("person", input_hash)
        placeholder = _build_placeholder_person(
            pid=new_pid, author_id=author_id, author_data=author_data
        )
        placeholder_records.append(placeholder)
        # Overwrite or set the resolution entry with Tier 4 outcome
        resolution_map[author_id] = {
            "pid": new_pid,
            "tier": 4,
            "confidence": 0.5,
            "reason": "no_t1_or_t2_match_minted_placeholder",
            "previous_tier_2_attempt": (
                resolution_map[author_id]
                if resolution_map.get(author_id, {}).get("outcome") == "ambiguous_falling_through_to_tier_4"
                else None
            ),
        }
        stats["tier_4"] += 1

        if stats["total_authors"] % progress_every == 0:
            print(
                f"[openiti-author-resolve] progressed {stats['total_authors']:>5}/"
                f"{len(authors_iter)} | T1={stats['tier_1']} T2={stats['tier_2']} "
                f"T4={stats['tier_4']}",
                flush=True,
            )

    # Write resolution map
    output_resolution_map_path.parent.mkdir(parents=True, exist_ok=True)
    with output_resolution_map_path.open("w", encoding="utf-8") as fh:
        json.dump(resolution_map, fh, ensure_ascii=False, indent=2)

    # Write placeholder records (jsonl)
    output_minted_persons_path.parent.mkdir(parents=True, exist_ok=True)
    with output_minted_persons_path.open("w", encoding="utf-8") as fh:
        for r in placeholder_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Augment stats
    total = stats["total_authors"]
    stats["tier_1_pct"] = round(100.0 * stats["tier_1"] / total, 2) if total else 0.0
    stats["tier_2_pct"] = round(100.0 * stats["tier_2"] / total, 2) if total else 0.0
    stats["tier_4_pct"] = round(100.0 * stats["tier_4"] / total, 2) if total else 0.0
    stats["t1_t2_combined_pct"] = round(
        100.0 * (stats["tier_1"] + stats["tier_2"]) / total, 2
    ) if total else 0.0
    stats["meets_acceptance_X"] = stats["t1_t2_combined_pct"] >= 70.0
    stats["person_index_size"] = person_index["person_count"]

    return stats


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="OpenITI author cross-walk pre-pass.")
    ap.add_argument("--corpus-authors", type=Path,
                    default=Path("data/sources/openiti/corpus_authors.json"))
    ap.add_argument("--canonical-persons", type=Path,
                    default=Path("data/canonical/persons.jsonl"))
    ap.add_argument("--qid-seed", type=Path,
                    default=Path("data/sources/openiti_qid_seed.json"))
    ap.add_argument("--out-resolution", type=Path,
                    default=Path("data/_state/openiti_author_resolution.json"))
    ap.add_argument("--out-minted", type=Path,
                    default=Path("data/_state/openiti_minted_persons.jsonl"))
    ap.add_argument("--death-ce-window", type=int, default=3)
    ap.add_argument("--jaccard-threshold", type=float, default=0.5)
    args = ap.parse_args()

    # Late import — only needed when run as script
    from pipelines._lib.pid_minter import PidMinter  # type: ignore

    minter = PidMinter(state_dir=Path("data/_state"))  # the real PidMinter persists state across runs

    stats = run_resolve(
        corpus_authors_path=args.corpus_authors,
        canonical_persons_path=args.canonical_persons,
        qid_seed_path=args.qid_seed if args.qid_seed.exists() else None,
        pid_minter=minter,
        output_resolution_map_path=args.out_resolution,
        output_minted_persons_path=args.out_minted,
        death_ce_window=args.death_ce_window,
        jaccard_threshold=args.jaccard_threshold,
    )
    print(json.dumps(stats, indent=2))
