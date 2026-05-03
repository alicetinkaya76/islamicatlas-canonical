"""
canonicalize.py — Adapter template for the canonicalization stage.

Convert extracted records (from extract.py) into canonical entity records that
conform to schemas/<namespace>.schema.json. Each yielded record is independently
schema-valid and writable to data/canonical/<namespace>/iac_<namespace>_NNNNNNNN.json.

Contract:
    canonicalize(
        extracted_records: Iterator[dict],
        pid_minter: PidMinter,
        reconciler: WikidataReconciler | None,
        options: dict | None = None,
    ) -> Iterator[dict]

Design rules:
    * Each output record carries a fully-populated provenance block.
    * @id is always allocated via pid_minter (never hand-assigned).
    * Cross-record references (predecessor, successor, ...) MAY use placeholders;
      pipelines/integrity/resolve_refs.py performs a second-pass linking.
    * Reconciliation is best-effort: failures fall through to authority_xref entries
      with reviewed=false rather than blocking the record.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator


def canonicalize(
    extracted_records: Iterator[dict],
    pid_minter,
    reconciler=None,
    options: dict | None = None,
) -> Iterator[dict]:
    """Yield canonical entity records, each conforming to its target schema.

    Args:
        extracted_records: Iterator of dicts produced by extract.py.
        pid_minter: Object with .mint(namespace: str, input_hash: str) -> str
                    that returns a stable PID like 'iac:work-00000042'.
        reconciler: Optional Wikidata reconciler. If None, authority_xref entries
                    are seeded but not actively populated.
        options: Adapter-specific options (e.g., strict_mode, default_lang).

    Yields:
        Canonical entity records (dicts), each conforming to a schema in schemas/.
    """
    options = options or {}
    strict = options.get("strict_mode", True)
    namespace = options.get("namespace", "work")  # MUST set in your adapter
    pipeline_name = options.get("pipeline_name", "canonicalize_template")
    pipeline_version = options.get("pipeline_version", "v0.1.0")
    attributed_to = options.get("attributed_to", "https://orcid.org/0000-0002-7747-6854")
    license_uri = options.get("license_uri", "https://creativecommons.org/licenses/by-sa/4.0/")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    for extracted in extracted_records:
        try:
            record = _build_canonical_record(
                extracted=extracted,
                namespace=namespace,
                pid_minter=pid_minter,
                reconciler=reconciler,
                pipeline_name=pipeline_name,
                pipeline_version=pipeline_version,
                attributed_to=attributed_to,
                license_uri=license_uri,
                now=now,
            )
            if record:
                yield record
        except Exception as exc:
            if strict:
                raise
            # Lenient mode: log and continue
            print(f"[canonicalize] failed on {extracted.get('source_record_id')}: {exc}")


def _build_canonical_record(
    *,
    extracted: dict,
    namespace: str,
    pid_minter,
    reconciler,
    pipeline_name: str,
    pipeline_version: str,
    attributed_to: str,
    license_uri: str,
    now: str,
) -> dict | None:
    """Map a single extracted record to a canonical record.

    Adapter authors: override this function with your source-specific mapping.
    The skeleton below is illustrative — fill in entity-type-specific fields.
    """
    raw = extracted.get("raw_data", {}) or {}
    locator = extracted.get("source_locator", {}) or {}
    source_record_id = extracted["source_record_id"]

    # 1. Mint a PID (idempotent: same input → same PID).
    pid = pid_minter.mint(namespace=namespace, input_hash=source_record_id)

    # 2. Build labels.
    #    Adapter-specific: extract titles, names, transliterations from raw_data.
    labels = {
        "prefLabel": {
            # Fill at least one language. Required by multilingual_text.schema.json.
            "en": raw.get("title_en") or raw.get("title") or "<UNTITLED>",
        }
    }
    for lang_key, label_key in (("ar", "title_ar"), ("tr", "title_tr")):
        if raw.get(label_key):
            labels["prefLabel"][lang_key] = raw[label_key]

    # 3. Build authority_xref (best-effort reconciliation).
    authority_xref = []
    if reconciler is not None:
        match = reconciler.reconcile(label_en=labels["prefLabel"].get("en"), context=raw)
        if match:
            authority_xref.append(match)

    # 4. Build provenance block.
    provenance = {
        "derived_from": [
            {
                "source_id": f"{namespace}-template:{source_record_id}",
                "source_type": "secondary_scholarly",  # adjust per adapter
                "page_or_locator": str(locator),
                "extraction_method": "structured_json",
                "edition_or_version": "TBD",
            }
        ],
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
                "note": f"Initial canonicalization by {pipeline_name} {pipeline_version}.",
            }
        ],
        "deprecated": False,
    }

    # 5. Compose the canonical record. Type-specific fields go here.
    record = {
        "@id": pid,
        "@type": [_supertype_for_namespace(namespace)],
        "labels": labels,
        "provenance": provenance,
    }
    if authority_xref:
        record["authority_xref"] = authority_xref

    # Adapter-specific fields go AFTER the core block. Examples:
    # if namespace == "work":
    #     record["authors"] = [...]                 # PID references; may use placeholders
    #     record["composition_temporal"] = {...}
    #     record["genre"] = [...]
    #     record["original_language"] = "ar"

    return record


def _supertype_for_namespace(namespace: str) -> str:
    return {
        "place": "iac:Place",
        "dynasty": "iac:Dynasty",
        "person": "iac:Person",
        "work": "iac:Work",
        "manuscript": "iac:Manuscript",
        "event": "iac:Event",
    }[namespace]
