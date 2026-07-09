"""
parse.py — Deterministic, offline HTML → normalized fields for dia-tdv-scrape.

NO network, NO canonical-schema knowledge (ADR-006 extract-side contract).
Given a madde's HTML (already fetched by scrape.py) and its slug, extract the
metadata that dia_chunks.json lacks: cilt+sayfa, Arabic title, and the
per-section entry author(s). Body text is captured only to VERIFY the fetch
against the already-owned dia_chunks `t` field (coverage metric) — it is not
persisted to canonical (ADR-014 §4: no scraped-body redistribution).

DOM contract (confirmed against the live site, H9 Stage 2a):
    <h1>                      → Turkish title (== dia_chunks.n)
    <div class="arabic_title">→ Arabic-script title (== dia_chunks.a), doc-level
    <div class="article-part" id="_1" | "_2-<section-slug>">   (1..N per madde)
        <div class="atif-kutusu">          citation box:
            <div class="ak-muellif"><span class="val">AUTHOR</span></div>
            <div class="ak-ilkyayin">Baskı Tarihi: YYYY</div>
            "... basılan <cilt>. cildinde, <sayfa> numaralı sayfada ..."
        <div class="m-content">            the clean narrative body
Multi-section maddes carry ONE article-part per section, each with its own
author + cilt/sayfa (H9 Stage 2a finding → author is a per-part list).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from bs4 import BeautifulSoup

BASE_URL = "https://islamansiklopedisi.org.tr"

# "... basılan 16. cildinde, 395 numaralı sayfada ..." (single)
# "... basılan 2. cildinde, 40-42 numaralı sayfalarda ..." (range)
CILT_SAYFA_RE = re.compile(
    r"(\d+)\.\s*cildinde,\s*(\d+)(?:-(\d+))?\s*numaral[ıi]\s*sayfa"
)
# "6 bölümden oluşan maddenin 2. bölümüdür."
BOLUM_RE = re.compile(r"(\d+)\s*bölümden\s+oluşan\s+maddenin\s+(\d+)\.\s*bölüm")
# "Baskı Tarihi: 1988"
BASKI_RE = re.compile(r"Bask[ıi]\s*Tarihi\s*:\s*(\d{4})")
# part id "_2-turk-tarihi" → section slug "turk-tarihi"; "_1" → no section
PART_SECTION_RE = re.compile(r"^_\d+-(.+)$")

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def madde_url(slug: str) -> str:
    """Public web-edition URL for a madde slug (root-level, per Stage 2a)."""
    return f"{BASE_URL}/{slug}"


def _txt(el) -> Optional[str]:
    return el.get_text(" ", strip=True) if el is not None else None


def normalize_text(t: Optional[str]) -> str:
    if not t:
        return ""
    t = unicodedata.normalize("NFC", t)
    return re.sub(r"\s+", " ", t).strip()


def token_set(t: Optional[str]) -> set:
    return set(_TOKEN_RE.findall(normalize_text(t).casefold()))


def coverage(reference: Optional[str], candidate: Optional[str]) -> float:
    """Fraction of `reference` tokens present in `candidate`.

    Verification metric (H9 Stage 2a): the scraped page legitimately CONTAINS
    more than dia_chunks.t (footnotes, bibliography), so a symmetric edit ratio
    understates a correct match. Coverage of the known chunk narrative INTO the
    scraped body is the sound discriminator: ~1.0 = right page, low = mismatch.
    """
    ref = token_set(reference)
    if not ref:
        return 0.0
    return len(ref & token_set(candidate)) / len(ref)


def parse_cilt_sayfa(text: Optional[str]):
    """Return (cilt, sayfa_baslangic, sayfa_bitis) ints, or (None, None, None)."""
    m = CILT_SAYFA_RE.search(text or "")
    if not m:
        return (None, None, None)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None)


def section_slug_from_part_id(part_id: Optional[str]) -> Optional[str]:
    if not part_id:
        return None
    m = PART_SECTION_RE.match(part_id)
    return m.group(1) if m else None


def parse_part(part) -> dict:
    # Search the whole part text: the "N. cildinde, M numaralı sayfada yer
    # almıştır" print-location line and "Baskı Tarihi: YYYY" live in the part's
    # citation/print blocks (near the top, before .m-content), not always inside
    # .atif-kutusu. `.search` returns the first (own-part) match.
    part_id = part.get("id")
    part_txt = _txt(part) or ""
    cilt, sayfa, sayfa_end = parse_cilt_sayfa(part_txt)
    baski = BASKI_RE.search(part_txt)
    bolum = BOLUM_RE.search(part_txt)
    body_el = part.find(class_="m-content")
    return {
        "part_id": part_id,
        "part_index": int(bolum.group(2)) if bolum else None,
        "total_parts": int(bolum.group(1)) if bolum else None,
        "section_slug": section_slug_from_part_id(part_id),
        "author_raw": _txt(part.select_one(".ak-muellif span.val")),
        "cilt": cilt,
        "sayfa_baslangic": sayfa,
        "sayfa_bitis": sayfa_end,
        "baski_yili": int(baski.group(1)) if baski else None,
        "body": _txt(body_el) or "",
    }


def parse_madde(html: str, slug: str) -> dict:
    """Parse a madde page into normalized fields. Deterministic; no network."""
    soup = BeautifulSoup(html, "lxml")
    parts = [parse_part(p) for p in soup.select(".article-part")]
    if not parts:
        # Fallback: no .article-part wrapper — treat #m-body as one unlabeled part.
        mb = soup.find(id="m-body") or soup.find("div", class_="article-parts")
        if mb is not None:
            cilt, sayfa, sayfa_end = parse_cilt_sayfa(_txt(mb))
            parts = [{
                "part_id": None, "part_index": 1, "total_parts": 1,
                "section_slug": None,
                "author_raw": _txt(soup.select_one(".ak-muellif span.val")),
                "cilt": cilt, "sayfa_baslangic": sayfa, "sayfa_bitis": sayfa_end,
                "baski_yili": None,
                "body": _txt(mb.find(class_="m-content") or mb) or "",
            }]
    # Single part with no explicit "N bölümden" marker → it is part 1 of 1.
    if len(parts) == 1 and parts[0]["part_index"] is None:
        parts[0]["part_index"] = 1
        parts[0]["total_parts"] = 1
    ar = soup.find("div", class_="arabic_title")
    return {
        "slug": slug,
        "title_tr": _txt(soup.find("h1")),
        "title_ar": _txt(ar),
        "n_parts": len(parts),
        "parts": parts,
    }


def madde_body(parsed: dict) -> str:
    """Concatenated narrative across parts (for coverage verification only)."""
    return "\n".join(p.get("body") or "" for p in parsed.get("parts", []))


_HARAKAT = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
                          "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه", "ء": ""})


def rasm(t: Optional[str]) -> str:
    """Arabic consonantal skeleton for lenient comparison: drop harakat/tatweel,
    fold hamza/alif/ya/ta-marbuta variants, strip the definite article `ال`."""
    t = unicodedata.normalize("NFKC", t or "")
    t = _HARAKAT.sub("", t).translate(_AR_FOLD)
    t = re.sub(r"\bال", "", t)
    return re.sub(r"\s+", " ", t).strip()


def arabic_matches(a: Optional[str], b: Optional[str]) -> bool:
    ra, rb = rasm(a), rasm(b)
    return bool(ra) and ra == rb


def verify(parsed: dict, chunk_n: Optional[str], chunk_a: Optional[str],
           chunk_t: Optional[str], coverage_min: float = 0.95) -> dict:
    """Cross-check a parsed madde against its dia_chunks record.

    Review-BLOCKING flags establish that the RIGHT madde was fetched:
      * title_mismatch — scraped <h1> != chunk.n (exact Turkish title)
      * low_coverage   — chunk.t not ⊆ scraped body (< coverage_min)
      * no_cilt_sayfa  — no locator parsed
    The Arabic title is ADVISORY: dia_chunks `a` is a reduced normalization
    (no definite article, hamza stripped) of the DiA's fully-vocalized title,
    so string inequality is COMMON for correct pages (H9 Stage 2d.1 finding —
    every early arabic_mismatch had h1_match + coverage 1.0). `ar_match` is
    rasm-compared and recorded for spot-checking, but does NOT gate review when
    h1 + coverage already confirm identity. North Star: flags = genuine doubt.
    """
    flags = []
    h1_match = None
    if chunk_n:
        h1_match = normalize_text(parsed.get("title_tr")).casefold() == normalize_text(chunk_n).casefold()
        if not h1_match:
            flags.append("title_mismatch")
    cov = coverage(chunk_t, madde_body(parsed))
    if cov < coverage_min:
        flags.append("low_coverage")
    if not any(p.get("cilt") for p in parsed.get("parts", [])):
        flags.append("no_cilt_sayfa")
    ar_match = arabic_matches(parsed.get("title_ar"), chunk_a) if chunk_a else None
    return {"h1_match": h1_match, "ar_match": ar_match,
            "coverage": round(cov, 4), "flags": flags}
