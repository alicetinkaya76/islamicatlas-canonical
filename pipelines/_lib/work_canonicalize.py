"""
work_canonicalize.py — Shared helpers for work-namespace adapters (Hafta 5).

Two adapters seed iac:work-* in Hafta 5:
  - science-works   (~300 multilingual key_works + filtered discoveries from
                     the 182-scholar science_layer.json)
  - openiti-works   (~9,104 work entries from corpus_works.json with author
                     cross-walk to the existing person namespace via
                     openiti_author_resolve.py pre-pass)

Each adapter passes raw normalized data; helpers produce a schema-valid
canonical work record. The adapter is responsible for source-specific
provenance (source_id pattern, edition string, page locator).

Design constraints inherited from Hafta 4:
  - The schema-valid `authority_xref.authority` enum in v0.1.0 includes
    'wikidata', 'openiti_uri', 'gnd', etc. — so OpenITI URIs CAN be stored
    structurally (work.schema has a dedicated `openiti_uri` field too).
    DİA / El-Aʿlām work cross-references go in `note` (mirroring person).
  - Composition dates: stored CE in composition_temporal. AH dates (e.g.
    "h. 822") kept in `note` when paired.
  - Work titles are typically multilingual; `labels.prefLabel.ar` carries
    the Arabic-script title, `labels.prefLabel.tr` the Turkish/Latinized
    transliteration, `labels.prefLabel.en` the English gloss when curated.

Bidirectional invariant (P0.2 hard rule):
  - work.authors[] points to existing iac:person-* PIDs (sticky pattern in
    work.schema: `^iac:person-[0-9]{8}$`).
  - person.authored_works[] is back-written by integrity_pass_A_bidirectional
    after all work adapters have minted their records.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable

# Reuse helpers from place_canonicalize for consistency with H3+H4 codebase.
# Direct relative import; matches the pattern person_canonicalize.py uses.
from .place_canonicalize import (
    has_arabic_script,
    truncate,
    try_int,
    try_float,
    now_iso,
    assemble_note,
)


# --------------------------------------------------------------------------- #
# Article + connector strip set (multilingual)
# --------------------------------------------------------------------------- #

# Arabic article variants (after diacritic strip, lowered): "al-", "el-",
# "li-", "fi-", "wa-", "bi-". Used by title_fingerprint() to strip leading
# article tokens that vary across editions/transliterations of the same work.
#
# Examples that should fingerprint identically:
#   "al-Qānūn fī al-Ṭibb"
#   "el-Kânûn fi't-Tıb"
#   "Kanun fi't-Tıb"
#   "القانون في الطب"          (after Arabic→Latin xlit then strip)
_TITLE_STOPWORDS = frozenset({
    # Arabic articles + connectors (post-diacritic-strip, post-lower).
    # We include common variants both as standalone tokens (after apostrophe
    # split) and as proclitic-attached forms ("fil", "fii"). Single-letter
    # orphans created by apostrophe-split (t, l, n, s) are also dropped here.
    "al", "el", "il", "li", "fi", "fii", "fil", "wa", "va", "ve", "bi", "ila", "ala",
    "an", "min", "ibn", "abu", "abi", "umm", "bint",
    # Single-letter orphan tokens from apostrophe-splits (e.g. "fi't-Tıb" → "fi t tıb")
    "t", "l", "n", "s", "h", "b", "k", "y",
    # Turkish equivalents
    "ile", "icin", "ki",
    # English connectors
    "the", "of", "in", "on", "and", "for", "to", "a", "or", "by",
    # Often-elided generic title-prefixes (we drop these so "Kitāb al-X"
    # and "X" produce the same fingerprint — defensible because most
    # multi-volume bibliographic works are referred to by their distinctive
    # noun, not the generic "Kitāb" prefix)
    "kitab", "kitabu", "kitap", "kitabi", "risala", "risale", "muqaddima",
    "muqaddimah", "diwan",
})

# Token-level Arabic ARTICLE prefix strip — applied AFTER tokenization to
# catch attached forms like "alqanun" → "qanun" that the dash-replacement
# step doesn't reach (because the source text had no dash).
# H9 Stage 3: narrowed to the article forms only. The old list also stripped
# attached proclitics (li/fi/wa/bi), which mangled roots that merely START
# with those letters: "Wafayāt"→"fayat" (breaking the Vefeyât match),
# "Fihrist"→"hrist", "Bidāya"→"daya". Standalone proclitic tokens are still
# dropped via _TITLE_STOPWORDS after the apostrophe/dash split.
_TOKEN_ARABIC_PREFIXES = ("al", "el", "il")

# Turkish-specific single-character ASCII folds. NFKD decomposition does
# NOT split these because they are precomposed codepoints, not letter+
# combining-diacritic sequences. Without this fold, Turkish "tıb" never
# matches Arabic-Latin "tib".
_TR_ASCII_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ç": "c", "Ç": "c", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u",
    # Turkish softening ↔ Arabic emphatic — controversial fold, but in
    # practice tabakat literature interchanges:
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
    "ā": "a", "Ā": "a", "ī": "i", "Ī": "i", "ū": "u", "Ū": "u",
    "ē": "e", "Ē": "e", "ō": "o", "Ō": "o",
})

# Latin-script transliteration variants that cross-walk Arabic <-> Turkish
# orthography. These are applied per-token to fold them to a single form.
# These folds are intentionally aggressive — false-positives are caught
# by Pass B's "must share at least one author PID" gate.
_TOKEN_TRANSLIT_FOLDS = [
    ("kh", "h"),    # Khalifa ↔ Halife
    ("dh", "d"),    # Dhahabi ↔ Zehebi (after z→d)
    ("th", "t"),    # Thaqāfa ↔ Sakāfe
    ("gh", "g"),    # Ghazālī ↔ Gazali
    ("sh", "s"),    # Sharh ↔ Şerh
    ("z", "d"),     # Dhahabi/Zehebi normalization
    ("j", "c"),     # Jabr ↔ Cebr
    ("w", ""),      # Khwarizmi/Hârizmî — drop w entirely (Latin trans variants split unpredictably)
    ("v", ""),      # H9 Stage 3: drop v symmetrically with w — Turkish
                    # transliteration renders Arabic wāw as v (Hayawān↔Hayevân,
                    # Wafayāt↔Vefeyât); dropping only w left the pairs apart
                    # ("hayan" vs "hayav"). Aggressive, per the Pass-B gate note.
    ("q", "k"),     # Qānūn ↔ Kânûn
    ("e", "a"),     # Turkish e ↔ Arabic a (Cebr/Jabr, Hayevan/Hayawan,
                    # Mes'udi/Mas'udi). False-positive risk mitigated by
                    # Pass B's author-PID overlap gate.
    ("aa", "a"),    # double-vowel collapse (must be after e→a so that
    ("ee", "a"),    # double-e also collapses to single a)
    ("ii", "i"),
    ("oo", "o"),
    ("uu", "u"),
    ("bb", "b"),    # double-consonant collapse
    ("dd", "d"),
    ("nn", "n"),
    ("ll", "l"),
    ("mm", "m"),
    ("rr", "r"),
    ("ss", "s"),
    ("tt", "t"),
]

# Punctuation we strip during fingerprint normalization.
# Note: we keep the apostrophe-like marker "'" out of strip_punct so that
# "fi't-Tıb" reduces correctly via the dash and apostrophe are handled
# separately in normalize_title_for_fingerprint().
_PUNCT_RE = re.compile(r"[\.,;:\!\?\(\)\[\]\{\}\"\u201c\u201d\u2018\u2019\u00ab\u00bb<>\\/\u02bc\u02bb\u02be\u02bf\u02c8]")
# H9 Stage 3: \u02be/\u02bf (02be/02bf) and curly quotes (2018/2019) joined this class \u2014
# they are apostrophe-equivalent SEPARATORS in transliteration ("a\u02bfy\u0101n" must
# split like "a'y\u00e2n"), not strippable punctuation (stripping glued the halves:
# "ayan" vs "a yan" \u2192 fingerprint mismatch on Wafay\u0101t/Vefey\u00e2t pairs).
_DASH_AND_APOSTROPHE_RE = re.compile(
    r"[-\u2010\u2011\u2012\u2013\u2014\u2015'\u02bc\u02bb\u02be\u02bf\u2018\u2019]")
_WHITESPACE_RE = re.compile(r"\s+")

# Arabic case-endings stripped from token tails (after consonant-skeleton folding).
# These are nominative/genitive/accusative + tāʾ marbūṭa-derived endings.
_TRAILING_CASE_ENDINGS = ("un", "an", "in", "uu", "ii")


def _strip_trailing_case_ending(tok: str) -> str:
    """Strip a trailing Arabic case-ending if the token would still be 4+
    chars long. Conservative: only strips two-letter endings, not single
    vowels (those false-trigger on legitimate -i/-a/-u stem-finals)."""
    if len(tok) < 6:
        return tok
    for end in _TRAILING_CASE_ENDINGS:
        if tok.endswith(end) and len(tok) - len(end) >= 4:
            return tok[: -len(end)]
    # Single trailing 'i' or 'u' is ALSO common as case ending; only strip
    # if token is 5+ chars to preserve roots like "ali" (the name).
    if len(tok) >= 6 and tok[-1] in ("i", "u") and tok[-2] not in "aeiou":
        return tok[:-1]
    return tok


# --------------------------------------------------------------------------- #
# Title fingerprint — for SAME-AS clustering in integrity_pass_B
# --------------------------------------------------------------------------- #


def _is_arabic_script_char(ch: str) -> bool:
    """Check if a character is in Arabic Unicode blocks."""
    return ('\u0600' <= ch <= '\u06FF') or ('\u0750' <= ch <= '\u077F')


# Arabic-script article + connector strip patterns. Applied to token
# starts after lowercasing/diacritic strip but BEFORE Latin transliteration
# folds (so Arabic-only titles get cleaned in their own script first).
_ARABIC_PREFIXES_RE = re.compile(r"^(?:ال|و|ف|ب|ل)")  # al-, wa-, fa-, bi-, li-

# Common Arabic-script stopwords (kept short; aggressive fold catches more)
_ARABIC_STOPWORDS = frozenset({"في", "على", "إلى", "من", "عن", "كتاب", "رسالة", "ديوان", "مقدمة"})


def normalize_title_for_fingerprint(title: str) -> str:
    """Return a normalized form of a work title suitable for cross-source
    SAME-AS matching.

    Operations (in order):
      1. NFKD diacritic strip (catches combining-mark forms)
      2. Turkish ASCII fold (ı→i, ş→s, etc. — these are precomposed
         codepoints that NFKD does NOT split)
      3. Lowercase
      4. Replace dashes / apostrophes with spaces
      5. Strip remaining punctuation
      6. Collapse whitespace
      7. Tokenize
      8. Per-token: strip Arabic script articles (ال, و, ف, ب, ل prefixes)
                    apply Latin transliteration folds (kh→h, j→c, w→v, etc.)
                    apply double-letter collapse
      9. Drop stopwords (articles, single-char orphans, generic prefixes,
         Arabic-script stopwords)
     10. Sort tokens (order-insensitive)
     11. Rejoin with single space

    The folds in step 8 are intentionally aggressive because Pass B
    layers an "author PID overlap" gate on top of fingerprint match,
    making false-positive merges very unlikely.

    Examples (locked by tests/integration/test_work_canonicalize_lib.py):
        "al-Qānūn fī al-Ṭibb"        → "kanun tib"
        "el-Kânûn fi't-Tıb"          → "kanun tib"
        "Kitāb al-Ḥayawān"           → "hayan"  (w AND v dropped, aa→a)
        "Kitabu'l-Hayevan"           → "hayan"
        "Wafayāt al-aʿyān"           → "acyan afayat"-style match with "Vefeyâtü'l-a'yân"
    """
    if not title or not isinstance(title, str):
        return ""

    # 1. NFKD diacritic strip
    nfkd = unicodedata.normalize("NFKD", title)
    s = "".join(ch for ch in nfkd if not unicodedata.combining(ch))

    # 2. Turkish ASCII fold (precomposed Turkish letters)
    s = s.translate(_TR_ASCII_FOLD)

    # 3. Lowercase
    s = s.lower()

    # 4. Replace dashes / apostrophes with spaces
    s = _DASH_AND_APOSTROPHE_RE.sub(" ", s)

    # 5. Strip remaining punctuation
    s = _PUNCT_RE.sub(" ", s)

    # 6. Collapse whitespace
    s = _WHITESPACE_RE.sub(" ", s).strip()

    # 7. Tokenize
    raw_tokens = s.split()

    # 8. Per-token normalization
    norm_tokens: list[str] = []
    for tok in raw_tokens:
        if not tok:
            continue

        # 8a. Arabic script handling — check stopwords BEFORE the prefix
        #     strip (H9 Stage 3: stripping first turned the stopword "في"
        #     into the garbage token "ي"), then strip the article prefix and
        #     re-check; single-letter leftovers are dropped.
        if any(_is_arabic_script_char(ch) for ch in tok):
            if tok in _ARABIC_STOPWORDS:
                continue
            stripped = _ARABIC_PREFIXES_RE.sub("", tok)
            if len(stripped) >= 2 and stripped not in _ARABIC_STOPWORDS:
                norm_tokens.append(stripped)
            continue

        # 8b. Latin script: strip leading Arabic-style articles attached
        #     without separator (e.g. "alqanun" → "qanun")
        for prefix in _TOKEN_ARABIC_PREFIXES:
            if tok.startswith(prefix) and len(tok) > len(prefix) + 2:
                tok = tok[len(prefix):]
                break

        # 8c. Latin transliteration folds
        for src, dst in _TOKEN_TRANSLIT_FOLDS:
            tok = tok.replace(src, dst)

        # 8d. Strip trailing Arabic case-ending (Makamatu → Makamat, Hisabi → Hisab)
        tok = _strip_trailing_case_ending(tok)

        # 8e. Drop very short / stopword tokens
        if not tok or len(tok) < 2:
            continue
        if tok in _TITLE_STOPWORDS:
            continue
        norm_tokens.append(tok)

    # 9. Sort tokens (order-insensitive)
    norm_tokens.sort()

    # 10. Rejoin
    return " ".join(norm_tokens)


def title_fingerprint(title: str) -> str:
    """16-character SHA1 prefix of the normalized title; suitable as a dict key.

    Empty title returns an empty string (callers should skip these in
    clustering — empty fingerprint is not a valid match key).
    """
    norm = normalize_title_for_fingerprint(title)
    if not norm:
        return ""
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def fingerprint_all_labels(labels: dict) -> set[str]:
    """Compute fingerprints for every label variant (prefLabel + altLabel),
    so cross-source SAME-AS matching can succeed even when only one
    transliteration matches.

    Returns a set of 16-char fingerprints; excludes the empty fingerprint.
    """
    fps: set[str] = set()
    pref = labels.get("prefLabel", {}) or {}
    for lang, val in pref.items():
        if isinstance(val, str):
            fp = title_fingerprint(val)
            if fp:
                fps.add(fp)
    alt = labels.get("altLabel", {}) or {}
    for lang, val_list in alt.items():
        if isinstance(val_list, list):
            for v in val_list:
                if isinstance(v, str):
                    fp = title_fingerprint(v)
                    if fp:
                        fps.add(fp)
    return fps


# --------------------------------------------------------------------------- #
# Label builder for works
# --------------------------------------------------------------------------- #


def _safe_truncate(s, n=500):
    if not s or not isinstance(s, str):
        return None
    return truncate(s, n)


def build_work_labels(
    *,
    title_ar: str | None = None,
    title_tr: str | None = None,
    title_en: str | None = None,
    alternate_titles: list[str] | None = None,
    description_tr: str | None = None,
    description_en: str | None = None,
    description_ar: str | None = None,
) -> dict:
    """Build a multilingual_text-conformant labels block for a work.

    `title_*` go to prefLabel.
    `alternate_titles` is a flat list dispatched by Arabic-script vs Latin.
    Dedup is case- and diacritic-insensitive within each language bucket.

    Note: Labels match person.schema's pattern (prefLabel/altLabel/originalScript/
    description). work.schema reuses the same multilingual_text definition.
    """
    pref: dict[str, str] = {}
    title_en_clean = _safe_truncate(title_en, 500)
    title_tr_clean = _safe_truncate(title_tr, 500)
    title_ar_clean = _safe_truncate(title_ar, 500)

    if title_en_clean:
        pref["en"] = title_en_clean
    if title_tr_clean:
        pref["tr"] = title_tr_clean
    if title_ar_clean:
        if has_arabic_script(title_ar_clean):
            pref["ar"] = title_ar_clean
        else:
            pref["ar-Latn-x-alalc"] = title_ar_clean
    if not pref:
        pref["en"] = "(untitled work)"

    labels: dict = {"prefLabel": pref}

    if title_ar_clean and has_arabic_script(title_ar_clean):
        labels["originalScript"] = {"ar": title_ar_clean}

    # altLabel: alternate titles, dedup against prefLabel within each bucket
    alt: dict[str, list[str]] = {}
    seen_in_lang: dict[str, set[str]] = {}

    def _add(lang_key: str, value: str):
        if not value or not value.strip():
            return
        v_clean = truncate(value, 500)
        if not v_clean:
            return
        # Dedup against prefLabel of same lang bucket
        existing_pref = pref.get(lang_key, "")
        norm_pref = strip_diacritics_lower(existing_pref) if existing_pref else ""
        norm_new = strip_diacritics_lower(v_clean)
        if norm_new == norm_pref:
            return
        seen = seen_in_lang.setdefault(lang_key, set())
        if norm_new in seen:
            return
        seen.add(norm_new)
        alt.setdefault(lang_key, []).append(v_clean)

    if alternate_titles:
        for at in alternate_titles:
            if not at or not str(at).strip():
                continue
            ac = str(at).strip()
            if has_arabic_script(ac):
                _add("ar", ac)
            else:
                # Latin-script alts → 'tr' bucket (curated dataset is Turkish-anchored)
                _add("tr", ac)

    if alt:
        # Cap each language to 20 alts (consistent with person labels)
        labels["altLabel"] = {k: v[:20] for k, v in alt.items()}

    desc: dict = {}
    if description_tr:
        desc["tr"] = truncate(description_tr, 5000)
    if description_en:
        desc["en"] = truncate(description_en, 5000)
    if description_ar:
        desc["ar"] = truncate(description_ar, 5000)
    if desc:
        labels["description"] = desc

    return labels


def strip_diacritics_lower(s: str) -> str:
    """Strip combining diacritical marks + lowercase. Used for label dedup."""
    if not s:
        return s
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower().strip()


# --------------------------------------------------------------------------- #
# Composition temporal builder
# --------------------------------------------------------------------------- #


def build_composition_temporal(
    *,
    year_ce: int | None = None,
    year_ah: int | None = None,
    end_year_ce: int | None = None,
    approximation: str = "circa",
) -> dict | None:
    """Build a composition_temporal block satisfying temporal.schema's anyOf.

    Most science_layer key_works carry a single CE year (`year: 820`). DİA
    and Kashf-style works often carry "h. NNN" AH-only dates, which we
    accept as start_ah-only.

    Returns None if no usable date axis is supplied.
    """
    out: dict = {}
    if year_ce is not None:
        ce = try_int(year_ce)
        if ce is not None and 100 <= ce <= 2100:
            out["start_ce"] = ce
    if year_ah is not None:
        ah = try_int(year_ah)
        if ah is not None and 1 <= ah <= 1700:
            out["start_ah"] = ah
    if end_year_ce is not None:
        ec = try_int(end_year_ce)
        if ec is not None and 100 <= ec <= 2100:
            out["end_ce"] = ec
    if not out:
        return None
    out["approximation"] = approximation if approximation in {
        "exact", "circa", "before", "after"
    } else "circa"
    return out


# --------------------------------------------------------------------------- #
# Subjects taxonomy — unified across science_layer + OpenITI
# --------------------------------------------------------------------------- #

# Free-string subjects[] field; map known source vocabularies to a small
# unified token set. work.schema does NOT close subjects to an enum (per
# pre-flight inspection), so this stays open for future taxonomies.

# science_layer "field" → unified subject token
SCIENCE_FIELD_TO_SUBJECT = {
    "mathematics": "mathematics",
    "astronomy": "astronomy",
    "geography": "geography",
    "philosophy": "philosophy",
    "medicine": "medicine",
    "history": "history",
    "literature": "literature",
    "religious_sciences": "religious_sciences",
    "theology": "theology",
    "natural_sciences": "natural_sciences",
    "social_sciences": "social_sciences",
    "music": "music",
    "navigation": "navigation",
    "optics": "optics",
    "engineering": "engineering",
    "architecture": "architecture",
    "chemistry": "chemistry",
    "culture": "culture",
    "translation": "translation",
}

# OpenITI llm-tagged primary_genre → unified subject token. The OpenITI
# katman3 LLM emits a small canonical set; we keep the original token as
# primary subject. The first block is identity (pass-through); the second
# block performs light renames for consistency with the science taxonomy.
OPENITI_GENRE_PASSTHROUGH = {
    # Pass-through (identity):
    "poetry": "poetry",
    "history": "history",
    "biography": "biography",
    "geography": "geography",
    "philosophy": "philosophy",
    "medicine": "medicine",
    "astronomy": "astronomy",
    "mathematics": "mathematics",
    "music": "music",
    "fiqh": "fiqh",
    "hadith": "hadith",
    "tafsir": "tafsir",
    "theology": "theology",
    "kalam": "kalam",
    "lexicography": "lexicography",
    "grammar": "grammar",
    "rhetoric": "rhetoric",
    "literature": "literature",
    "adab": "adab",
    "sufism": "sufism",
    # Light renames for consistency:
    "tasawwuf": "sufism",
    "law": "fiqh",
    "hadith_collection": "hadith",
    "biographical_dictionary": "biography",
}


# --------------------------------------------------------------------------- #
# Provenance builder for work records
# --------------------------------------------------------------------------- #


def build_work_provenance(
    *,
    source_record_id: str,
    source_kind: str,
    page_locator: str,
    edition: str | None,
    pipeline_name: str,
    pipeline_version: str,
    attributed_to: str,
    license_uri: str,
    record_history_note: str,
    extraction_method: str = "structured_json",
    now: str | None = None,
) -> dict:
    """Build a provenance-schema-conformant provenance block for a work.

    Mirrors the person provenance builder; same field set since the
    provenance schema is shared across namespaces.
    """
    now = now or now_iso()
    derived_entry = {
        "source_id": source_record_id,
        "source_type": source_kind,
        "page_or_locator": truncate(page_locator, 1000),
        "extraction_method": extraction_method,
    }
    if edition:
        derived_entry["edition_or_version"] = truncate(edition, 500)

    return {
        "derived_from": [derived_entry],
        "generated_by": {
            "pipeline_name": pipeline_name,
            "pipeline_version": pipeline_version,
        },
        "generated_at": now,
        "attributed_to": attributed_to,
        "created": now,
        "modified": now,
        "license": license_uri,
        "record_history": [
            {
                "change_type": "create",
                "changed_at": now,
                "changed_by": attributed_to,
                "release": "v0.1.0-phase0",
                "note": truncate(record_history_note, 1000),
            }
        ],
        "deprecated": False,
    }


# --------------------------------------------------------------------------- #
# @type array builder for works
# --------------------------------------------------------------------------- #

# Closed enum from work.schema.json v0.3.0 @type.items (H9 Stage 3: the H5
# draft carried subtypes — LegalManual, HistoricalChronicle, Encyclopedia,
# Commentary, Translation, DivanCollection — that never entered the frozen
# enum; an early `return` hid the mismatch as dead code). Any drift is caught
# by test_work_canonicalize_lib.py::test_work_subtypes_match_schema_enum.
WORK_SUBTYPES = {
    "iac:Work",            # base type — always present
    "iac:Book",
    "iac:Treatise",
    "iac:Poem",
    "iac:Fatwa",
    "iac:Letter",
    "iac:Map",
    "iac:Compendium",
    "iac:Dictionary",
    "iac:HadithCollection",
    "iac:Tafsir",
    "iac:Tarikh",
    "iac:Sira",
    "iac:Tabaqa",
    "iac:Geography",
}


# Heuristic mapping: subjects → suggested subtypes (v0.3.0 enum values)
_SUBJECT_TO_SUBTYPE = {
    "hadith": "iac:HadithCollection",
    "fiqh": "iac:Treatise",          # enum has no LegalManual; treatise is the honest fit
    "history": "iac:Tarikh",
    "lexicography": "iac:Dictionary",
    "biography": "iac:Tabaqa",       # tabaqat-style works
    "tafsir": "iac:Tafsir",
    "poetry": "iac:Poem",
    "geography": "iac:Geography",
    "sira": "iac:Sira",
}


def build_work_type_array(
    subjects: list[str] | None = None,
    *,
    is_translation: bool = False,
    is_commentary: bool = False,
    extra_subtypes: list[str] | None = None,
) -> list[str]:
    """Build the @type array for a work record (v0.3.0 enum, maxItems=3).

    Always includes 'iac:Work'. Additional subtypes derived from subjects[].
    `is_translation` / `is_commentary` are accepted for API compatibility but
    contribute nothing: the frozen v0.3.0 enum has no Translation/Commentary
    class (candidates for a future v0.4.x set bump, ADR-013 R2/R3).
    Unknown extra_subtypes are silently dropped (enum-guarded).
    """
    types: set[str] = {"iac:Work"}
    if subjects:
        for s in subjects:
            sub = _SUBJECT_TO_SUBTYPE.get(s)
            if sub and sub in WORK_SUBTYPES:
                types.add(sub)
    if extra_subtypes:
        for t in extra_subtypes:
            if t in WORK_SUBTYPES:
                types.add(t)
    out = sorted(types)
    if len(out) > 3:  # schema @type maxItems=3
        non_base = [t for t in out if t != "iac:Work"]
        out = ["iac:Work"] + sorted(non_base)[:2]
    return out


# --------------------------------------------------------------------------- #
# Authority xref helpers
# --------------------------------------------------------------------------- #


def make_xref(
    *,
    authority: str,
    identifier: str,
    confidence: float = 1.0,
    obtained_via: str = "imported_from_source",
    url: str | None = None,
) -> dict:
    """Construct a single authority_xref entry conformant to xref.schema.

    `authority` must be a value already accepted by the v0.1.0 enum
    (wikidata, openiti_uri, gnd, viaf, isni, orcid, etc.). For sources NOT
    in the enum (DİA, El-Aʿlām, EI1, Kashf), use the note formatters in
    person_canonicalize.py instead.
    """
    # Schema work.authority_xref.items is closed: only authority/id/confidence.
    # obtained_via and url were dropped to satisfy additionalProperties=False.
    return {
        "authority": authority,
        "id": identifier,
        "confidence": float(confidence),
    }


def make_openiti_xref(uri: str, confidence: float = 1.0) -> dict:
    """OpenITI URI → authority_xref entry. The URI also goes into the
    dedicated work.openiti_uri field; we duplicate to authority_xref so
    SAME-AS resolution can use the unified xref index."""
    return make_xref(
        authority="openiti",
        identifier=uri,
        confidence=confidence,
    )


# --------------------------------------------------------------------------- #
# Note formatters — for v0.1.0 schema enum gap (DİA, Kashf, etc.)
# --------------------------------------------------------------------------- #


def format_dia_work_note(dia_slug: str | None, raw_title: str | None = None) -> str | None:
    """Format a DİA work cross-reference for the note field.
    Used by Hafta 6+ dia_works adapter; defined here for forward-compat."""
    if not dia_slug:
        return None
    bits = [f"DİA work cross-reference: slug={dia_slug}"]
    if raw_title:
        bits.append(f"raw_title={raw_title}")
    return ", ".join(bits)


def format_science_layer_work_note(
    scholar_id: str | None,
    field: str | None = None,
    significance_tr: str | None = None,
) -> str | None:
    """Format a science_layer key_works cross-reference for the note field."""
    if not scholar_id:
        return None
    bits = [f"science_layer key_work: scholar_id={scholar_id}"]
    if field:
        bits.append(f"field={field}")
    if significance_tr:
        bits.append(f"significance: {significance_tr[:300]}")
    return ", ".join(bits)


def format_openiti_work_note(
    uri: str | None,
    word_count: int | None = None,
    version_count: int | None = None,
) -> str | None:
    """Format an OpenITI cross-reference summary line for the note field."""
    if not uri:
        return None
    bits = [f"OpenITI corpus URI: {uri}"]
    if word_count is not None:
        bits.append(f"word_count={word_count:,}")
    if version_count is not None and version_count > 1:
        bits.append(f"versions={version_count}")
    return ", ".join(bits)


# --------------------------------------------------------------------------- #
# Label-for-recon picker
# --------------------------------------------------------------------------- #


def label_for_recon(labels: dict) -> str | None:
    """Pick the best Latin-script label for Wikidata reconciliation of a work.

    Preference: en > ar-Latn-x-alalc > tr. Strips leading articles
    ("al-", "el-", "the ") to improve OpenRefine match scoring. Returns
    None when no Latin-script label is available — Arabic-only works
    are not reconciled in Hafta 5 (Tier-b filter).
    """
    pref = labels.get("prefLabel", {})
    candidate = pref.get("en") or pref.get("ar-Latn-x-alalc") or pref.get("tr")
    if not candidate:
        return None
    cleaned = candidate.strip()
    for prefix in ("al-", "Al-", "el-", "El-", "AL-", "the ", "The "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    return cleaned or candidate


# --------------------------------------------------------------------------- #
# Author resolver — tries to map an arbitrary author identifier to an
# existing iac:person-* PID via the pid_minter's reverse index.
# --------------------------------------------------------------------------- #


def try_resolve_author_pid(
    *,
    pid_minter,
    candidate_input_hashes: Iterable[str],
) -> str | None:
    """Try a list of `input_hash` patterns to locate an existing person PID.

    The pid_minter is idempotent: calling mint(namespace, input_hash) with
    a previously-seen input_hash returns the existing PID. So we can use
    it as a reverse-index lookup, BUT only if we don't want to MINT a new
    PID for unmatched candidates. The minter's `lookup_only` mode returns
    None instead of minting; if not available, we fall back to the
    pid_index.json file.

    Returns the first matching PID, or None if none of the candidates
    resolve.
    """
    if pid_minter is None:
        return None
    for cand in candidate_input_hashes:
        if not cand:
            continue
        # lookup() reads without minting (PidMinter guarantees the method;
        # the old `_index` fallback here targeted an attribute that never
        # existed, with a key shape that was wrong even if it had — removed
        # in H9 Stage 3).
        pid = pid_minter.lookup("person", cand)
        if pid:
            return pid
    return None


# --------------------------------------------------------------------------- #
# Validation helper
# --------------------------------------------------------------------------- #


REQUIRED_WORK_FIELDS = {"@id", "@type", "labels", "provenance"}


def quick_validate_work(record: dict) -> list[str]:
    """Lightweight pre-flight validator. Returns a list of error strings
    (empty == OK). The full schema validation happens downstream via
    jsonschema in run_adapter.py; this is a fast smoke check.
    """
    errors: list[str] = []
    for f in REQUIRED_WORK_FIELDS:
        if f not in record:
            errors.append(f"missing required field: {f}")
    pid = record.get("@id", "")
    if not isinstance(pid, str) or not re.match(r"^iac:work-[0-9]{8}$", pid):
        errors.append(f"invalid PID: {pid!r}")
    types = record.get("@type", [])
    if not isinstance(types, list) or "iac:Work" not in types:
        errors.append(f"@type must contain 'iac:Work': {types!r}")
    labels = record.get("labels", {})
    if not isinstance(labels, dict) or "prefLabel" not in labels:
        errors.append("labels missing prefLabel")
    elif not labels["prefLabel"]:
        errors.append("labels.prefLabel is empty")
    authors = record.get("authors", [])
    if authors and not isinstance(authors, list):
        errors.append(f"authors must be a list: {type(authors).__name__}")
    for a in authors:
        if not isinstance(a, str) or not re.match(r"^iac:person-[0-9]{8}$", a):
            errors.append(f"invalid author PID: {a!r}")
    return errors


# DiA print locator ("TDV DiA cilt 16 s. 395") or a dated web locator for the
# 5 online-only maddes (H9 Stage 2e finding) — both satisfy ADR-009 (c).
_ADR009_PRINT_LOCATOR_RE = re.compile(r"cilt\s*\d+.{0,20}s(?:ayfa)?\.?\s*\d+", re.IGNORECASE)
_ADR009_WEB_LOCATOR_RE = re.compile(r"https?://islamansiklopedisi\.org\.tr/\S+.{0,40}\d{4}")


def adr009_rich_gate(record: dict) -> list[str]:
    """ADR-009 rich-mint doctrine gate — the pre-write check AP (dia_works,
    H10+) MUST run on every DiA-side work record. Returns failure strings
    (empty == record may be written to canonical).

    Doctrine (ADR-009 §Karar): a DiA-side work record may be written IFF
      (a) labels.prefLabel carries >= 2 languages,
      (b) labels.description carries >= 1 non-empty language,
      (c) provenance.derived_from[].page_or_locator has a specific cilt+sayfa
          reference (or, per H9 Stage 2e, a dated web locator for the five
          online-only maddes).
    Failures route to a review sidecar — never a silent write.
    """
    failures: list[str] = []
    labels = record.get("labels") or {}

    pref = labels.get("prefLabel") or {}
    langs = [k for k, v in pref.items() if isinstance(v, str) and v.strip()]
    if len(langs) < 2:
        failures.append(f"adr009(a): prefLabel has {len(langs)} language(s), need >=2")

    desc = labels.get("description") or {}
    if not any(isinstance(v, str) and v.strip() for v in desc.values()):
        failures.append("adr009(b): no non-empty description in any language")

    derived = (record.get("provenance") or {}).get("derived_from") or []
    locators = [e.get("page_or_locator") or "" for e in derived]
    if not any(_ADR009_PRINT_LOCATOR_RE.search(loc) or _ADR009_WEB_LOCATOR_RE.search(loc)
               for loc in locators):
        failures.append("adr009(c): no cilt+sayfa (or dated web) locator in derived_from")

    return failures
