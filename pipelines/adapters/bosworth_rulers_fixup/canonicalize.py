"""
canonicalize.py — Convert each Bosworth inline ruler into an iac:person- record.

Logic:
  1. PID minted from input_hash = bosworth-nid:<NID>:ruler:<index> (idempotent).
  2. labels.prefLabel.en = ruler['name'] (already ALA-LC romanised).
  3. labels.prefLabel.ar = ruler['name_ar'] if present.
  4. @type = ['iac:Person', 'iac:Ruler'].
  5. profession = ['ruler']; second pass may add 'patron' from regnal_title.
  6. laqab = [regnal_title] if regnal_title is set.
  7. death_temporal = parsed from ruler.note's "Death:" section if explicit;
     otherwise inferred as approximation='before' anchored at reign_end_ce + 1.
     (A ruler died at-or-after the reign end in the typical case; reign_end
     is often year-of-death itself.)
  8. floruit_temporal = built from reign_start_ce / reign_start_ah.
  9. affiliated_dynasties = [dynasty_pid].
  10. Sidecar `bosworth_rulers_pending`: maps dynasty_pid →
      [{ruler_index, person_pid, name}] for the dynasty integrity pass.
  11. Sidecar `rulers_to_dynasty_xref`: maps person_pid → dynasty_pid for
      cross-source resolver lookup (later: when DİA encounters a ruler name,
      can match to existing person via this index).
"""

from __future__ import annotations

import re
from typing import Iterator

from pipelines._lib import person_canonicalize as pc

ATTRIBUTED_TO = "https://orcid.org/0000-0002-7747-6854"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
EDITION = "Bosworth, New Islamic Dynasties (Edinburgh University Press 2004)."


# Note format from Hafta 2: "<bio> || İlişki: <relation> || Death: <code> [(...)]"
_NOTE_PARTS_RE = re.compile(r"\s*\|\|\s*")
_DEATH_DATE_RE = re.compile(r"d\.\s*(\d{1,4})/(\d{1,4})")


def _parse_ruler_note(note: str) -> tuple[str, str, dict]:
    """Split the inline ruler note into (bio, relation, death_info_dict)."""
    if not note:
        return "", "", {}
    parts = _NOTE_PARTS_RE.split(note)
    bio = parts[0].strip() if parts else ""
    relation = ""
    death_info: dict = {}
    for p in parts[1:]:
        p = p.strip()
        if p.lower().startswith("ilişki:") or p.startswith("İlişki:"):
            relation = p.split(":", 1)[1].strip() if ":" in p else ""
        elif p.lower().startswith("death:"):
            txt = p.split(":", 1)[1].strip()
            # Look for explicit "d. AH/CE" or "k. AH/CE"
            m = _DEATH_DATE_RE.search(txt)
            if m:
                ah = int(m.group(1))
                ce = int(m.group(2))
                death_info["start_ah"] = ah
                death_info["start_ce"] = ce
                death_info["approximation"] = "exact"
            # Death code (d./k./o.) as note
            death_info["code"] = txt
    return bio, relation, death_info


def _build_temporal_floruit(reign_start_ce, reign_end_ce, reign_start_ah, reign_end_ah):
    """Build a floruit temporal from reign dates.

    Schema temporal anyOf requires at least one of start_ce / start_ah / iso_start_date.
    If only end_* fields are available (8 rulers in the Mac dataset like Yahyā III with
    reign_end_ce=905 but no reign_start_*), promote end_ce to start_ce with
    approximation='before' as a safe fallback (the ruler died in or before that year,
    so they were certainly active before that year too).
    """
    out: dict = {}
    if reign_start_ce is not None:
        out["start_ce"] = int(reign_start_ce)
    if reign_end_ce is not None:
        out["end_ce"] = int(reign_end_ce)
    if reign_start_ah is not None:
        out["start_ah"] = int(reign_start_ah)
    if reign_end_ah is not None:
        out["end_ah"] = int(reign_end_ah)
    if not out:
        return None
    has_start = "start_ce" in out or "start_ah" in out
    if not has_start:
        if "end_ce" in out:
            out["start_ce"] = out["end_ce"]
            out["approximation"] = "before"
            out["note"] = "Bosworth ruler with only reign_end_* fields; start_ce promoted from end_ce."
            return out
        if "end_ah" in out:
            out["start_ah"] = out["end_ah"]
            out["approximation"] = "before"
            out["note"] = "Bosworth ruler with only reign_end_* fields; start_ah promoted from end_ah."
            return out
        return None
    out["approximation"] = "floruit"
    return out


def _build_temporal_death(death_info, reign_end_ce, reign_end_ah, reign_start_ce):
    """Build death_temporal. If explicit dates parsed from note, use them.
    Otherwise infer from reign_end_ce as a 'before' approximation."""
    if "start_ce" in death_info or "start_ah" in death_info:
        out = {}
        if "start_ce" in death_info:
            out["start_ce"] = death_info["start_ce"]
        if "start_ah" in death_info:
            out["start_ah"] = death_info["start_ah"]
        out["approximation"] = death_info.get("approximation", "exact")
        if death_info.get("code"):
            out["note"] = f"Bosworth death code: {death_info['code']}"
        return out

    # Inferred: ruler died at or shortly after reign_end_ce. Use 'circa'
    # since many Bosworth rulers died in the year their reign ended.
    if reign_end_ce is not None:
        out = {"start_ce": int(reign_end_ce), "approximation": "circa"}
        if reign_end_ah is not None:
            out["start_ah"] = int(reign_end_ah)
        out["note"] = "Inferred from Bosworth reign_end (often ≈ year of death)."
        return out

    # No reign_end: use reign_start_ce as floruit anchor instead — but death
    # temporal is unknown, return None.
    return None


def canonicalize(extracted_iter, pid_minter, reconciler, options):
    namespace = options["namespace"]  # "person"
    sidecars = options.get("sidecars", {})
    pending_sc = sidecars.get("bosworth_rulers_pending", {})  # type: ignore
    xref_sc = sidecars.get("rulers_to_dynasty_xref", {})       # type: ignore

    pipeline_name = options.get("pipeline_name", "canonicalize_person_bosworth_rulers")
    pipeline_version = options.get("pipeline_version", "v0.1.0")

    for record in extracted_iter:
        ruler = record["ruler"]
        idx = record["ruler_index"]
        dynasty_pid = record["dynasty_pid"]
        dynasty_label = record["dynasty_label"]
        bosworth_id = record.get("bosworth_id") or "NID-???"

        # Idempotent PID
        # bosworth_id is like "NID-001"; strip prefix
        nid_num_match = re.search(r"(\d+)", bosworth_id or "")
        nid_num = int(nid_num_match.group(1)) if nid_num_match else 0
        input_hash = f"bosworth-nid:{nid_num}:ruler:{idx}"
        pid = pid_minter.mint(namespace, input_hash)

        name = ruler.get("name", "").strip()
        name_ar = ruler.get("name_ar", "").strip() if ruler.get("name_ar") else None
        regnal_title = ruler.get("regnal_title", "").strip() if ruler.get("regnal_title") else None
        bio, relation, death_info = _parse_ruler_note(ruler.get("note", "") or "")

        # labels
        labels = pc.build_person_labels(
            name_en=name,
            name_ar=name_ar,
            description_tr=bio if bio else None,
        )

        # temporal
        floruit = _build_temporal_floruit(
            ruler.get("reign_start_ce"),
            ruler.get("reign_end_ce"),
            ruler.get("reign_start_ah"),
            ruler.get("reign_end_ah"),
        )
        death = _build_temporal_death(
            death_info,
            ruler.get("reign_end_ce"),
            ruler.get("reign_end_ah"),
            ruler.get("reign_start_ce"),
        )

        # @type and profession
        professions = ["ruler"]
        # Heuristic: regnal titles like "Sultan", "Khalīfa" already imply ruler;
        # patronage etc. is not reliably encoded in Bosworth. Stay minimal.
        types = pc.build_type_array(professions)

        # Schema $comment Phase 0.2 hard rule: at least one of birth/death/floruit
        # MUST be present. JSON Schema doesn't enforce this in v0.1.0 but
        # the test suite does (test_a4). Some Bosworth rulers (e.g. minor
        # branch dynasts in NID-080 Bāwandid Ispahbadhs) lack any reign_*
        # fields entirely — these are skipped and the corresponding
        # rulers[i].person_pid back-write does not happen.
        if not (floruit or death):
            continue

        # provenance
        provenance = pc.build_provenance(
            source_record_id=f"bosworth-nid:{nid_num}:ruler:{idx}",
            source_kind="secondary_scholarly",
            page_locator=f"Bosworth, New Islamic Dynasties, NID-{nid_num:03d}, ruler #{idx+1}",
            edition=EDITION,
            pipeline_name=pipeline_name,
            pipeline_version=pipeline_version,
            attributed_to=ATTRIBUTED_TO,
            license_uri=LICENSE,
            record_history_note=(
                f"Promoted from inline rulers[{idx}] of {dynasty_pid} ({dynasty_label}) "
                f"by bosworth-rulers-fixup adapter (Hafta 4). dual-write: original "
                f"rulers[] retained on dynasty record; rulers[{idx}].person_pid + "
                f"had_ruler[] populated by integrity/promote_rulers.py."
            ),
        )

        # Optional Wikidata recon (Tier-b high-value: all rulers go through)
        authority_xref = []
        recon_label = pc.label_for_recon(labels)
        if reconciler is not None and recon_label:
            try:
                hit = reconciler.reconcile(
                    label_en=recon_label,
                    type_qid=options.get("reconciliation_type_qid", "Q5"),
                    source_record_id=input_hash,
                    context={"death_year_ce": (death or floruit or {}).get("start_ce")},
                )
                if hit:
                    authority_xref.append(hit)
            except Exception:
                pass  # offline mode swallows API errors

        # Build the person record
        person: dict = {
            "@id": pid,
            "@type": types,
            "labels": labels,
            "profession": professions,
            "provenance": provenance,
            "affiliated_dynasties": [dynasty_pid],
        }
        if regnal_title:
            person["laqab"] = [pc.truncate(regnal_title, 200)]
        if floruit:
            person["floruit_temporal"] = floruit
        if death:
            person["death_temporal"] = death
        if authority_xref:
            person["authority_xref"] = authority_xref

        # Note: relation + ruler_note pieces
        note_bits = []
        if relation:
            note_bits.append(f"Bosworth relation note: {relation}")
        if death_info.get("code"):
            note_bits.append(f"Bosworth death code: {death_info['code']}")
        note_bits.append(
            f"Promoted from {dynasty_pid} rulers[{idx}] (Bosworth NID-{nid_num:03d})."
        )
        person["note"] = pc.assemble_note(note_bits)

        # Sidecar entries
        pending_sc.setdefault(dynasty_pid, []).append({
            "ruler_index": idx,
            "person_pid": pid,
            "name": name,
        })
        xref_sc[pid] = {
            "dynasty_pid": dynasty_pid,
            "name": name,
            "ruler_index": idx,
            "bosworth_id": f"NID-{nid_num:03d}",
        }

        yield person
