"""Offline dictionary build tooling for German flashcards.

Implements build stage 01 (ADR-0001 §12, ADR-0004 D36/D45/D47):
Deterministic offline JSONL-to-SQLite transform from Kaikki/Wiktextract dumps
to the read-only dictionary core (lemma, surface_form, sense, sense_meaning,
and sense_meaning_derivation tables).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Sequence

# Ensure repository root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.resolve import (  # noqa: E402
    LemmaRecord,
    LookupProtocol,
    SenseRecord,
    resolve_token,
)
from tools.resolver_hash import get_resolver_hash  # noqa: E402

POS_MAP: Final[dict[str, str]] = {
    "noun": "NOUN",
    "proper_noun": "PROPN",
    "name": "PROPN",
    "verb": "VERB",
    "aux": "AUX",
    "adj": "ADJ",
    "adv": "ADV",
    "prep": "ADP",
    "postp": "ADP",
    "pron": "PRON",
    "det": "DET",
    "num": "NUM",
    "conj": "CCONJ",
    "particle": "PART",
    "intj": "INTJ",
}

GENDER_CANONICAL_ORDER: Final[tuple[str, ...]] = ("der", "die", "das")
GENDER_ORDER_MAP: Final[dict[str | None, int]] = {
    None: 0,
    "der": 1,
    "die": 2,
    "das": 3,
}

STAGE01_SCHEMA_SQL: Final[str] = """
-- Numeric IDs (lemma.id, sense.id, etc.) are local per-asset keys only.
-- Durable cross-version identity is defined by semantic_ref.
CREATE TABLE IF NOT EXISTS lemma (
  id            INTEGER PRIMARY KEY,
  semantic_ref  TEXT NOT NULL UNIQUE,
  lemma         TEXT NOT NULL,
  pos           TEXT NOT NULL,
  gender        TEXT,
  plural        TEXT,
  plural_none   INTEGER NOT NULL DEFAULT 0 CHECK (plural_none IN (0,1)),
  genitive_sg   TEXT,
  aux           TEXT,
  separable     INTEGER DEFAULT 0,
  particle      TEXT,
  reflexive     INTEGER DEFAULT 0,
  praesens_3sg  TEXT,
  praeteritum_3sg TEXT,
  partizip_ii   TEXT,
  governs       TEXT,
  comparative   TEXT,
  superlative   TEXT,
  ipa           TEXT,
  ipa_source    TEXT,
  freq_rank     INTEGER,
  source        TEXT,
  license       TEXT,
  CHECK (plural_none = 0 OR plural IS NULL),
  UNIQUE(lemma, pos, gender)
);
CREATE INDEX IF NOT EXISTS ix_lemma_lookup ON lemma(lemma, pos);

CREATE TABLE IF NOT EXISTS surface_form (
  form      TEXT NOT NULL,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  PRIMARY KEY (form, lemma_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sense (
  id                INTEGER PRIMARY KEY,
  lemma_id          INTEGER NOT NULL REFERENCES lemma(id),
  semantic_ref      TEXT NOT NULL UNIQUE,
  source_namespace  TEXT NOT NULL,
  source_ref        TEXT NOT NULL,
  ord               INTEGER NOT NULL DEFAULT 0,
  register          TEXT,
  source            TEXT,
  license           TEXT
);
CREATE INDEX IF NOT EXISTS ix_sense_lemma ON sense(lemma_id, ord);

CREATE TABLE IF NOT EXISTS sense_meaning (
  id        INTEGER PRIMARY KEY,
  sense_id  INTEGER NOT NULL REFERENCES sense(id) ON DELETE CASCADE,
  language  TEXT NOT NULL,
  kind      TEXT NOT NULL CHECK (kind IN ('definition', 'synonym', 'translation')),
  ord       INTEGER NOT NULL DEFAULT 0,
  text      TEXT NOT NULL,
  source    TEXT NOT NULL,
  license   TEXT NOT NULL,
  UNIQUE(sense_id, language, kind, ord)
);
CREATE INDEX IF NOT EXISTS ix_sense_meaning ON sense_meaning(sense_id, language, ord);

CREATE TABLE IF NOT EXISTS sense_meaning_derivation (
  generated_meaning_id INTEGER NOT NULL
      REFERENCES sense_meaning(id) ON DELETE CASCADE,
  source_meaning_id INTEGER NOT NULL
      REFERENCES sense_meaning(id) ON DELETE RESTRICT,
  PRIMARY KEY (generated_meaning_id, source_meaning_id),
  CHECK (generated_meaning_id <> source_meaning_id)
) WITHOUT ROWID;
"""

STAGE02_EXAMPLE_SCHEMA_SQL: Final[str] = """
CREATE TABLE IF NOT EXISTS example (
  id           INTEGER PRIMARY KEY,
  de           TEXT NOT NULL,
  en           TEXT,
  source       TEXT,
  source_ref   TEXT,
  license      TEXT,
  token_count  INTEGER,
  has_proper   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS example_lemma (
  lemma_id   INTEGER NOT NULL REFERENCES lemma(id),
  example_id INTEGER NOT NULL REFERENCES example(id),
  PRIMARY KEY (lemma_id, example_id)
) WITHOUT ROWID;
"""


INCLUDED_SENSE_DISTINCTION_FIELDS: Final[tuple[str, ...]] = (
    "glosses",
    "tags",
    "topics",
    "form_of",
    "alt_of",
    "compound_of",
    "qualifier",
    "taxonomic",
)

GENERATED_SOURCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^llm_generated_v[1-9][0-9]*$"
)


class BuildDictError(Exception):
    """Base error for dictionary build failures."""


def canonicalize_pos(raw_pos: str) -> str:
    """Map Wiktextract POS tag to canonical Universal POS tag or uppercase raw POS."""
    return POS_MAP.get(raw_pos, raw_pos.upper())


def compute_lemma_semantic_ref(word: str, pos: str, gender: str | None) -> str:
    """Compute deterministic lemma semantic ref (ADR-0004 D47 / A2)."""
    nfc_lemma_text = unicodedata.normalize("NFC", word)
    gender_token = gender if gender is not None else "<null>"
    payload = json.dumps(
        ["de", nfc_lemma_text, pos, gender_token],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"lemma:v1:{hashlib.sha256(payload).hexdigest()}"


LINKAGE_FIELDS: Final[frozenset[str]] = frozenset({
    "form_of",
    "alt_of",
    "compound_of",
    "taxonomic",
})


def canonicalize_string_projection(s: str) -> str | None:
    """Canonicalize string for non-linkage sense fallback fingerprint projection (A4)."""
    s = unicodedata.normalize("NFC", s).casefold()
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    s = " ".join(s.split())
    return s if s else None


def canonicalize_string_linkage(s: str) -> str | None:
    """Canonicalize string for identity-bearing linkage fields (Failure-2 amendment / v2)."""
    s = unicodedata.normalize("NFC", s)
    s = " ".join(s.split())
    return s if s else None


def canonicalize_projection_value(val: object, is_linkage: bool = False) -> object:
    """Canonicalize any value (string, list, dict, scalar) for fallback fingerprint."""
    if val is None:
        return None
    if isinstance(val, str):
        return (
            canonicalize_string_linkage(val)
            if is_linkage
            else canonicalize_string_projection(val)
        )
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, list):
        canon_items: list[Any] = []
        for item in val:
            c = canonicalize_projection_value(item, is_linkage=is_linkage)
            if c is not None:
                canon_items.append(c)
        if not canon_items:
            return None
        # Deduplicate and sort by canonical JSON encoding
        seen: dict[str, Any] = {}
        for item in canon_items:
            encoded = json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            if encoded not in seen:
                seen[encoded] = item
        sorted_items = [seen[k] for k in sorted(seen.keys())]
        return sorted_items if sorted_items else None
    if isinstance(val, dict):
        canon_dict: dict[str, Any] = {}
        for k in sorted(val.keys()):
            if not isinstance(k, str):
                continue
            c_val = canonicalize_projection_value(val[k], is_linkage=is_linkage)
            if c_val is not None:
                canon_dict[k] = c_val
        return canon_dict if canon_dict else None
    return None


def compute_sense_fallback_projection_payload(
    raw_sense: dict[str, Any],
) -> tuple[str, bytes]:
    """Compute fallback version and canonical projection UTF-8 payload bytes."""
    projection: dict[str, Any] = {}
    has_surviving_linkage = False
    for f in INCLUDED_SENSE_DISTINCTION_FIELDS:
        if f in raw_sense and raw_sense[f] is not None:
            is_linkage = f in LINKAGE_FIELDS
            c = canonicalize_projection_value(raw_sense[f], is_linkage=is_linkage)
            if c is not None:
                projection[f] = c
                if is_linkage:
                    has_surviving_linkage = True
    payload = json.dumps(
        projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    version = "v2" if has_surviving_linkage else "v1"
    return version, payload


def compute_sense_fallback_ref(raw_sense: dict[str, Any]) -> str:
    """Compute cosmetic-stable fallback sense source_ref fingerprint (A4 / Failure-2 amendment)."""
    version, payload = compute_sense_fallback_projection_payload(raw_sense)
    digest = hashlib.sha256(payload).hexdigest()
    return f"fingerprint:{version}:{digest}"


def deduplicate_record_senses(senses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Coalesce same-record canonical-equivalent fallback senses (Failure-3 amendment).

    Preserves the first occurrence in raw source order and skips later canonical-equivalent
    fallback senses whose canonical projection bytes are identical under the existing
    fallback fingerprint implementation.
    Explicit senseid/wikidata senses are never coalesced.
    """
    retained: list[dict[str, Any]] = []
    seen_fallback_keys: set[tuple[str, bytes]] = set()

    for sense in senses:
        source_ref = compute_sense_source_ref(sense)
        if source_ref.startswith("fingerprint:v1:") or source_ref.startswith("fingerprint:v2:"):
            version, payload = compute_sense_fallback_projection_payload(sense)
            key = (version, payload)
            if key in seen_fallback_keys:
                continue
            seen_fallback_keys.add(key)
        retained.append(sense)

    return retained


def compute_senseid_candidate(raw_sense: dict[str, Any]) -> str | None:
    """Compute the cleaned senseid candidate source_ref for one raw sense (A4).

    Returns None when the sense has no usable senseid. Multiple usable IDs in
    one raw sense serialize deterministically as senseids:v1:<sha256>.
    """
    senseids_raw = raw_sense.get("senseid")
    if senseids_raw is None:
        senseids_raw = raw_sense.get("senseids")
    if senseids_raw is None:
        return None
    if isinstance(senseids_raw, str):
        senseids_list = [senseids_raw]
    elif isinstance(senseids_raw, list):
        senseids_list = [s for s in senseids_raw if isinstance(s, str)]
    else:
        senseids_list = []
    clean_senseids: list[str] = []
    for s in senseids_list:
        s_norm = unicodedata.normalize("NFC", s).strip()
        if s_norm and s_norm not in clean_senseids:
            clean_senseids.append(s_norm)
    if len(clean_senseids) == 1:
        return f"senseid:{clean_senseids[0]}"
    if len(clean_senseids) > 1:
        sorted_senseids = sorted(clean_senseids)
        payload = json.dumps(
            sorted_senseids, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return f"senseids:v1:{hashlib.sha256(payload).hexdigest()}"
    return None


def compute_wikidata_candidate(raw_sense: dict[str, Any]) -> str | None:
    """Compute the cleaned Wikidata candidate source_ref for one raw sense (A4).

    Returns None when the sense has no usable Wikidata QID. Multiple usable
    QIDs in one raw sense serialize deterministically as wikidata-set:v1:<sha256>.
    """
    wikidata_raw = raw_sense.get("wikidata")
    if wikidata_raw is None:
        return None
    if isinstance(wikidata_raw, str):
        qids_list = [wikidata_raw]
    elif isinstance(wikidata_raw, list):
        qids_list = [q for q in wikidata_raw if isinstance(q, str)]
    else:
        qids_list = []
    clean_qids: list[str] = []
    for q in qids_list:
        q_norm = unicodedata.normalize("NFC", q).strip()
        if q_norm and q_norm not in clean_qids:
            clean_qids.append(q_norm)
    if len(clean_qids) == 1:
        return f"wikidata:{clean_qids[0]}"
    if len(clean_qids) > 1:
        sorted_qids = sorted(clean_qids)
        payload = json.dumps(
            sorted_qids, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return f"wikidata-set:v1:{hashlib.sha256(payload).hexdigest()}"
    return None


def compute_sense_source_ref(raw_sense: dict[str, Any]) -> str:
    """Compute the single-sense source_ref using the A4 priority ladder.

    This greedy helper remains the reference for same-record fallback dedupe
    routing (Failure-3) and for isolated lookups. Final lemma-identity
    source_ref assignment uses resolve_sense_source_refs (Failure-4), which
    demotes explicit identifiers that are ambiguous within the lemma identity.
    """
    senseid_candidate = compute_senseid_candidate(raw_sense)
    if senseid_candidate is not None:
        return senseid_candidate
    wikidata_candidate = compute_wikidata_candidate(raw_sense)
    if wikidata_candidate is not None:
        return wikidata_candidate
    return compute_sense_fallback_ref(raw_sense)


def resolve_sense_source_refs(raw_senses: Sequence[dict[str, Any]]) -> list[str]:
    """Resolve source_refs for all raw senses at final lemma-identity scope.

    Failure-4 amendment: an explicit upstream identifier (senseid, then
    Wikidata) is usable for a raw sense only when its canonical candidate ref
    is unambiguous within the lemma identity. Resolution is set/count based,
    so the outcome does not depend on source record order.

    Effective priority: unique senseid -> unique Wikidata -> fallback fingerprint.
    """
    senseid_candidates = [compute_senseid_candidate(s) for s in raw_senses]
    wikidata_candidates = [compute_wikidata_candidate(s) for s in raw_senses]

    senseid_counts: Counter[str] = Counter(
        c for c in senseid_candidates if c is not None
    )

    resolved: list[str | None] = [None] * len(raw_senses)

    # Senseid pass: a candidate occurring exactly once is usable.
    for i, candidate in enumerate(senseid_candidates):
        if candidate is not None and senseid_counts[candidate] == 1:
            resolved[i] = candidate

    # Wikidata pass: only senses without a unique usable senseid participate.
    wikidata_stage = [i for i in range(len(raw_senses)) if resolved[i] is None]
    wikidata_counts: Counter[str] = Counter()
    for i in wikidata_stage:
        candidate = wikidata_candidates[i]
        if candidate is not None:
            wikidata_counts[candidate] += 1
    for i in wikidata_stage:
        candidate = wikidata_candidates[i]
        if candidate is not None and wikidata_counts[candidate] == 1:
            resolved[i] = candidate

    # Fallback pass.
    final_refs: list[str] = []
    for i, ref in enumerate(resolved):
        if ref is None:
            final_refs.append(compute_sense_fallback_ref(raw_senses[i]))
        else:
            final_refs.append(ref)
    return final_refs


def compute_sense_semantic_ref(
    lemma_semantic_ref: str, source_namespace: str, source_ref: str
) -> str:
    """Compute deterministic sense semantic ref (A5)."""
    payload = json.dumps(
        [lemma_semantic_ref, source_namespace, source_ref],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sense:v1:{hashlib.sha256(payload).hexdigest()}"


def validate_sense_meaning_derivations(conn: sqlite3.Connection) -> None:
    """Validate sense_meaning_derivation edges according to ADR-0004 D45 / A8."""
    cur = conn.execute("""
        SELECT d.generated_meaning_id, d.source_meaning_id,
               gm.id AS gm_id, gm.sense_id AS gm_sense_id,
               gm.source AS gm_source, gm.license AS gm_license,
               sm.id AS sm_id, sm.sense_id AS sm_sense_id,
               sm.source AS sm_source, sm.license AS sm_license
        FROM sense_meaning_derivation d
        LEFT JOIN sense_meaning gm ON d.generated_meaning_id = gm.id
        LEFT JOIN sense_meaning sm ON d.source_meaning_id = sm.id
    """)
    for (
        gen_mid,
        src_mid,
        gm_id,
        gm_sense_id,
        gm_source,
        gm_license,
        sm_id,
        sm_sense_id,
        sm_source,
        sm_license,
    ) in cur.fetchall():
        if gm_id is None:
            raise BuildDictError(
                f"Derivation edge references nonexistent generated meaning {gen_mid}"
            )
        if sm_id is None:
            raise BuildDictError(
                f"Derivation edge references nonexistent source meaning {src_mid}"
            )
        if gm_id == sm_id:
            raise BuildDictError(f"Derivation self-edge forbidden on meaning {gm_id}")

        gm_src_str = str(gm_source) if gm_source is not None else ""
        if not GENERATED_SOURCE_PATTERN.match(gm_src_str):
            raise BuildDictError(
                f"Generated meaning {gm_id} source '{gm_src_str}' does not match "
                f"versioned generated marker"
            )

        sm_src_str = str(sm_source) if sm_source is not None else ""
        if GENERATED_SOURCE_PATTERN.match(sm_src_str):
            raise BuildDictError(
                f"Source meaning {sm_id} cannot be generated (generated->generated forbidden)"
            )
        if not sm_src_str.strip():
            raise BuildDictError(f"Source meaning {sm_id} has blank source")

        sm_lic_str = str(sm_license) if sm_license is not None else ""
        if not sm_lic_str.strip():
            raise BuildDictError(f"Source meaning {sm_id} has blank license")

        if gm_sense_id != sm_sense_id:
            raise BuildDictError(
                f"Cross-sense derivation forbidden: generated meaning {gm_id} "
                f"(sense {gm_sense_id}) != source meaning {sm_id} (sense {sm_sense_id})"
            )


@dataclass
class LemmaAccumulator:
    """In-memory accumulator for a single merged lemma identity."""

    word: str
    pos: str
    gender: str | None
    ipa: str | None = None
    ipa_source: str | None = None
    plural_candidates: set[str] = field(default_factory=set)
    plural_none: bool = False
    genitive_sg_candidates: set[str] = field(default_factory=set)
    praesens_3sg_candidates: set[str] = field(default_factory=set)
    praeteritum_3sg_candidates: set[str] = field(default_factory=set)
    partizip_ii_candidates: set[str] = field(default_factory=set)
    comparative_candidates: set[str] = field(default_factory=set)
    superlative_candidates: set[str] = field(default_factory=set)
    surface_forms: set[str] = field(default_factory=set)
    raw_senses_en: list[dict[str, Any]] = field(default_factory=list)


def _validate_type(
    val: object,
    expected_type: type | tuple[type, ...],
    field_name: str,
    path: Path,
    line_no: int,
) -> None:
    """Validate JSON value type, raising BuildDictError on mismatch."""
    if not isinstance(val, expected_type):
        if isinstance(expected_type, tuple):
            type_name = "/".join(t.__name__ for t in expected_type)
        else:
            type_name = expected_type.__name__
        raise BuildDictError(
            f"Invalid type for field '{field_name}' in {path}:{line_no}: "
            f"expected {type_name}, got {type(val).__name__}"
        )


def process_jsonl_file(
    file_path: Path,
    is_en_edition: bool,
    accumulators: dict[tuple[str, str, str | None], LemmaAccumulator],
) -> None:
    """Process a single Wiktextract JSONL dump file line-by-line."""
    if not file_path.is_file():
        raise BuildDictError(f"Input JSONL file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except Exception as e:
                raise BuildDictError(f"Malformed JSON in {file_path}:{line_no}: {e}") from e

            if not isinstance(record, dict):
                raise BuildDictError(
                    f"Invalid record format in {file_path}:{line_no}: expected JSON object"
                )

            # C2: Only records with lang_code == "de", non-empty string word, and non-empty pos
            lang_code = record.get("lang_code")
            word = record.get("word")
            pos = record.get("pos")

            if (
                lang_code != "de"
                or not isinstance(word, str)
                or not word
                or not isinstance(pos, str)
                or not pos
            ):
                # Deliberately ignored per C2
                continue

            # Normalize participating lemma text to NFC
            word = unicodedata.normalize("NFC", word)

            # Participating record: validate participating fields (C8)
            # 1. Tags and Gender / Plural-none
            has_no_plural_tag = False
            found_genders: set[str] = set()
            if "tags" in record and record["tags"] is not None:
                tags = record["tags"]
                _validate_type(tags, list, "tags", file_path, line_no)
                for tag in tags:
                    _validate_type(tag, str, "tags[]", file_path, line_no)

                if "masculine" in tags:
                    found_genders.add("der")
                if "feminine" in tags:
                    found_genders.add("die")
                if "neuter" in tags:
                    found_genders.add("das")

                if "no-plural" in tags:
                    has_no_plural_tag = True

            target_genders: list[str | None]
            if found_genders:
                target_genders = [g for g in GENDER_CANONICAL_ORDER if g in found_genders]
            else:
                target_genders = [None]

            canonical_pos = canonicalize_pos(pos)
            target_accs: list[LemmaAccumulator] = []
            for g in target_genders:
                lemma_key = (word, canonical_pos, g)
                if lemma_key not in accumulators:
                    accumulators[lemma_key] = LemmaAccumulator(
                        word=word, pos=canonical_pos, gender=g
                    )
                acc = accumulators[lemma_key]
                if has_no_plural_tag:
                    acc.plural_none = True
                target_accs.append(acc)

            # 2. Sounds and IPA
            if "sounds" in record and record["sounds"] is not None:
                sounds = record["sounds"]
                _validate_type(sounds, list, "sounds", file_path, line_no)
                first_ipa: str | None = None
                for sound in sounds:
                    _validate_type(sound, dict, "sounds[]", file_path, line_no)
                    if "ipa" in sound and sound["ipa"] is not None:
                        ipa_val = sound["ipa"]
                        _validate_type(ipa_val, str, "sounds[].ipa", file_path, line_no)
                        if ipa_val.strip() and first_ipa is None:
                            first_ipa = ipa_val.strip()

                if first_ipa is not None:
                    for acc in target_accs:
                        if acc.ipa is None:
                            acc.ipa = first_ipa
                            acc.ipa_source = "wiktionary"

            # 3. Senses (owned by English edition, C5)
            if "senses" in record and record["senses"] is not None:
                senses = record["senses"]
                _validate_type(senses, list, "senses", file_path, line_no)
                for sense in senses:
                    _validate_type(sense, dict, "senses[]", file_path, line_no)
                if is_en_edition:
                    deduped_senses = deduplicate_record_senses(senses)
                    for acc in target_accs:
                        for sense in deduped_senses:
                            acc.raw_senses_en.append(dict(sense))

            # 4. Forms (Surface forms and Form-derived fields, C6 & C7)
            if "forms" in record and record["forms"] is not None:
                forms = record["forms"]
                _validate_type(forms, list, "forms", file_path, line_no)
                parsed_forms: list[tuple[str, set[str]]] = []
                for form_item in forms:
                    _validate_type(form_item, dict, "forms[]", file_path, line_no)
                    form_str = form_item.get("form")
                    if form_str is not None:
                        _validate_type(form_str, str, "forms[].form", file_path, line_no)

                    form_tags = form_item.get("tags")
                    if form_tags is not None:
                        _validate_type(form_tags, list, "forms[].tags", file_path, line_no)
                        for t in form_tags:
                            _validate_type(t, str, "forms[].tags[]", file_path, line_no)

                    if form_str is not None:
                        clean_form = form_str.strip()
                        if clean_form and clean_form != "-":
                            clean_form = unicodedata.normalize("NFC", clean_form)
                            tags_set = set(form_tags) if form_tags is not None else set()
                            parsed_forms.append((clean_form, tags_set))

                for clean_form, tags_set in parsed_forms:
                    for acc in target_accs:
                        if clean_form != word:
                            acc.surface_forms.add(clean_form)

                        if "plural" in tags_set:
                            acc.plural_candidates.add(clean_form)
                        if "genitive" in tags_set and "singular" in tags_set:
                            acc.genitive_sg_candidates.add(clean_form)
                        if (
                            "present" in tags_set
                            and "third-person" in tags_set
                            and "singular" in tags_set
                        ):
                            acc.praesens_3sg_candidates.add(clean_form)
                        if (
                            "past" in tags_set
                            and "third-person" in tags_set
                            and "singular" in tags_set
                            and "participle" not in tags_set
                        ):
                            acc.praeteritum_3sg_candidates.add(clean_form)
                        if "past" in tags_set and "participle" in tags_set:
                            acc.partizip_ii_candidates.add(clean_form)
                        if "comparative" in tags_set:
                            acc.comparative_candidates.add(clean_form)
                        if "superlative" in tags_set:
                            acc.superlative_candidates.add(clean_form)


def build_stage01(
    en_jsonl_path: Path | str,
    de_jsonl_path: Path | str,
    output_path: Path | str,
) -> None:
    """Execute build stage 01 deterministic transform to SQLite."""
    en_path = Path(en_jsonl_path)
    de_path = Path(de_jsonl_path)
    out_path = Path(output_path)

    if out_path.exists():
        raise BuildDictError(f"Output path already exists: {out_path}")

    # Process EN then DE into accumulators
    accumulators: dict[tuple[str, str, str | None], LemmaAccumulator] = {}
    process_jsonl_file(en_path, is_en_edition=True, accumulators=accumulators)
    process_jsonl_file(de_path, is_en_edition=False, accumulators=accumulators)

    # Sort lemma identities deterministically before assigning IDs (C4)
    sorted_keys = sorted(
        accumulators.keys(),
        key=lambda k: (k[0], k[1], GENDER_ORDER_MAP.get(k[2], 99), k[2] or ""),
    )

    # Prepare temporary sibling file for fail-closed atomic publish (C1 & C8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        dir=out_path.parent,
        prefix=f".{out_path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(temp_file.name)
    temp_file.close()

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(temp_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(STAGE01_SCHEMA_SQL)

        seen_lemma_semantic_refs: set[str] = set()
        seen_sense_semantic_refs: set[str] = set()

        with conn:
            sense_id_counter = 1
            meaning_id_counter = 1

            for lemma_id, key in enumerate(sorted_keys, start=1):
                acc = accumulators[key]

                # Contradictory plural check (A9)
                if acc.plural_none and acc.plural_candidates:
                    raise BuildDictError(
                        f"Contradictory plural evidence for '{acc.word}': 'no-plural' tag present "
                        f"along with plural form {sorted(acc.plural_candidates)}"
                    )

                if acc.plural_candidates:
                    plural = min(acc.plural_candidates)
                    plural_none = 0
                elif acc.plural_none:
                    plural = None
                    plural_none = 1
                else:
                    plural = None
                    plural_none = 0

                genitive_sg = (
                    min(acc.genitive_sg_candidates) if acc.genitive_sg_candidates else None
                )
                praesens_3sg = (
                    min(acc.praesens_3sg_candidates) if acc.praesens_3sg_candidates else None
                )
                praeteritum_3sg = (
                    min(acc.praeteritum_3sg_candidates)
                    if acc.praeteritum_3sg_candidates
                    else None
                )
                partizip_ii = (
                    min(acc.partizip_ii_candidates)
                    if acc.partizip_ii_candidates
                    else None
                )
                comparative = (
                    min(acc.comparative_candidates)
                    if acc.comparative_candidates
                    else None
                )
                superlative = (
                    min(acc.superlative_candidates)
                    if acc.superlative_candidates
                    else None
                )

                lemma_semantic_ref = compute_lemma_semantic_ref(
                    acc.word, acc.pos, acc.gender
                )
                if lemma_semantic_ref in seen_lemma_semantic_refs:
                    raise BuildDictError(
                        f"Duplicate lemma semantic_ref '{lemma_semantic_ref}' for '{acc.word}'"
                    )
                seen_lemma_semantic_refs.add(lemma_semantic_ref)

                conn.execute(
                    """
                    INSERT INTO lemma (
                        id, semantic_ref, lemma, pos, gender, plural, plural_none, genitive_sg,
                        aux, separable, particle, reflexive, praesens_3sg, praeteritum_3sg,
                        partizip_ii, governs, comparative, superlative, ipa, ipa_source,
                        freq_rank, source, license
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lemma_id,
                        lemma_semantic_ref,
                        acc.word,
                        acc.pos,
                        acc.gender,
                        plural,
                        plural_none,
                        genitive_sg,
                        None,  # aux
                        0,  # separable
                        None,  # particle
                        0,  # reflexive
                        praesens_3sg,
                        praeteritum_3sg,
                        partizip_ii,
                        None,  # governs
                        comparative,
                        superlative,
                        acc.ipa,
                        acc.ipa_source,
                        None,  # freq_rank
                        "wiktionary",
                        "CC BY-SA",
                    ),
                )

                # Insert surface forms sorted
                for sf in sorted(acc.surface_forms):
                    conn.execute(
                        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
                        (sf, lemma_id),
                    )

                # Senses and English localized meanings (A6 / A7)
                # Resolve source_refs at final lemma-identity scope BEFORE the
                # A6 learner-meaning cap so identifier ambiguity is set/count
                # based over every participating raw sense (Failure-4).
                resolved_source_refs = resolve_sense_source_refs(acc.raw_senses_en)

                retained_senses: list[tuple[dict[str, Any], list[str], str]] = []
                total_en_meanings = 0
                seen_gloss_texts: set[str] = set()

                for raw_sense, source_ref in zip(acc.raw_senses_en, resolved_source_refs):
                    retained_glosses_for_this_sense: list[str] = []
                    if "glosses" in raw_sense and raw_sense["glosses"] is not None:
                        for g in raw_sense["glosses"]:
                            if isinstance(g, str):
                                clean_g = g.strip()
                                if clean_g and clean_g not in seen_gloss_texts:
                                    if total_en_meanings < 3:
                                        seen_gloss_texts.add(clean_g)
                                        retained_glosses_for_this_sense.append(clean_g)
                                        total_en_meanings += 1

                    if retained_glosses_for_this_sense:
                        retained_senses.append(
                            (raw_sense, retained_glosses_for_this_sense, source_ref)
                        )

                for ord_idx, (raw_sense, gloss_list, source_ref) in enumerate(retained_senses):
                    source_namespace = "wiktextract:enwiktionary"
                    sense_semantic_ref = compute_sense_semantic_ref(
                        lemma_semantic_ref, source_namespace, source_ref
                    )
                    if sense_semantic_ref in seen_sense_semantic_refs:
                        raise BuildDictError(
                            f"Duplicate sense semantic_ref '{sense_semantic_ref}' "
                            f"for lemma '{acc.word}'"
                        )
                    seen_sense_semantic_refs.add(sense_semantic_ref)

                    conn.execute(
                        """
                        INSERT INTO sense (
                            id, lemma_id, semantic_ref, source_namespace, source_ref,
                            ord, register, source, license
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sense_id_counter,
                            lemma_id,
                            sense_semantic_ref,
                            source_namespace,
                            source_ref,
                            ord_idx,
                            None,  # register
                            "wiktionary",
                            "CC BY-SA",
                        ),
                    )

                    for meaning_ord, gloss_text in enumerate(gloss_list):
                        conn.execute(
                            """
                            INSERT INTO sense_meaning (
                                id, sense_id, language, kind, ord, text, source, license
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                meaning_id_counter,
                                sense_id_counter,
                                "en",
                                "translation",
                                meaning_ord,
                                gloss_text,
                                "wiktionary",
                                "CC BY-SA",
                            ),
                        )
                        meaning_id_counter += 1

                    sense_id_counter += 1

            # Validate derivations
            validate_sense_meaning_derivations(conn)

        conn.close()
        conn = None

        if out_path.exists():
            raise BuildDictError(f"Output path already exists: {out_path}")

        temp_path.replace(out_path)

    except Exception:
        if conn is not None:
            conn.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def sha256_file(path: Path | str) -> str:
    """Compute SHA-256 hex digest of file raw bytes."""
    p = Path(path)
    if not p.is_file():
        raise BuildDictError(f"File not found for SHA-256 calculation: {p}")
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_stage02_cache_key(
    stage01_path: Path | str,
    de_tsv_path: Path | str,
    en_tsv_path: Path | str,
    links_tsv_path: Path | str,
    license_label: str,
    spacy_model: str,
) -> str:
    """Compute deterministic Stage-02 cache key including canonical resolver hash (A8)."""
    resolver_sha = get_resolver_hash()
    stage01_sha = sha256_file(stage01_path)
    de_sha = sha256_file(de_tsv_path)
    en_sha = sha256_file(en_tsv_path)
    links_sha = sha256_file(links_tsv_path)

    payload = json.dumps(
        {
            "format": "stage02:v1",
            "resolver_sha256": resolver_sha,
            "stage01_sha256": stage01_sha,
            "de_tsv_sha256": de_sha,
            "en_tsv_sha256": en_sha,
            "links_tsv_sha256": links_sha,
            "spacy_model": spacy_model,
            "license": license_label,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"stage02:v1:{hashlib.sha256(payload).hexdigest()}"


class Stage02LookupOracle(LookupProtocol):
    """Bounded-memory, read-only dictionary lookup oracle for Stage 02.

    Stage 01 deliberately has no expression indexes for the runtime's
    ``lower(lemma)`` and ``lower(surface_form)`` predicates.  Build a temporary
    Stage-02-only accelerator once, using SQLite's own ``lower`` implementation,
    then use indexed equality lookups throughout the NLP pass.  Keeping SQLite
    responsible for case folding is essential: it preserves the runtime
    Dictionary's exact SQLite/Python case behaviour without materialising the
    dictionary in Python memory.
    """

    _CACHE_SIZE: Final[int] = 100_000

    def __init__(
        self, db_path: Path | str, accelerator_path: Path | str | None = None
    ) -> None:
        self._source_path = Path(db_path).resolve()
        self._owns_accelerator = accelerator_path is None
        if accelerator_path is None:
            temp_file = tempfile.NamedTemporaryFile(
                prefix="stage02-lookup-", suffix=".sqlite", delete=False
            )
            self._accelerator_path = Path(temp_file.name)
            temp_file.close()
            self._accelerator_path.unlink()
        else:
            self._accelerator_path = Path(accelerator_path)
            if self._accelerator_path.exists():
                raise BuildDictError(
                    f"Stage-02 lookup accelerator already exists: {self._accelerator_path}"
                )

        self._conn: sqlite3.Connection | None = None
        try:
            self._conn = sqlite3.connect(self._accelerator_path)
            self._conn.execute(
                "ATTACH DATABASE ? AS source",
                (f"file:{self._source_path}?mode=ro",),
            )
            self._conn.executescript(
                """
                CREATE TABLE exact_lookup (
                    lookup_key TEXT NOT NULL,
                    id INTEGER NOT NULL,
                    lemma TEXT NOT NULL,
                    pos TEXT NOT NULL,
                    gender TEXT,
                    semantic_ref TEXT NOT NULL,
                    freq_rank INTEGER,
                    PRIMARY KEY (lookup_key, id)
                ) WITHOUT ROWID;
                CREATE TABLE surface_lookup (
                    lookup_key TEXT NOT NULL,
                    lemma_id INTEGER NOT NULL,
                    PRIMARY KEY (lookup_key, lemma_id)
                ) WITHOUT ROWID;

                INSERT INTO exact_lookup
                SELECT lemma, id, lemma, pos, gender, semantic_ref, freq_rank
                FROM source.lemma;
                INSERT OR IGNORE INTO exact_lookup
                SELECT lower(lemma), id, lemma, pos, gender, semantic_ref, freq_rank
                FROM source.lemma;

                INSERT INTO surface_lookup
                SELECT form, lemma_id FROM source.surface_form;
                INSERT OR IGNORE INTO surface_lookup
                SELECT lower(form), lemma_id FROM source.surface_form;
                """
            )
        except Exception:
            if self._conn is not None:
                self._conn.close()
            self._accelerator_path.unlink(missing_ok=True)
            raise

    @property
    def accelerator_path(self) -> Path:
        """Return the ephemeral accelerator path for execution instrumentation."""
        return self._accelerator_path

    def lookup_query_plans(self, lemma: str, form: str) -> tuple[str, str]:
        """Return query plans proving lookup queries avoid source-table scans."""
        if self._conn is None:
            raise BuildDictError("Stage-02 lookup oracle is closed")
        exact_plan = self._conn.execute(
            "EXPLAIN QUERY PLAN "
            "SELECT id, lemma, pos, gender, semantic_ref, freq_rank "
            "FROM exact_lookup WHERE lookup_key IN (?, ?) GROUP BY id "
            "ORDER BY freq_rank ASC NULLS LAST, pos ASC, gender ASC NULLS LAST, "
            "semantic_ref ASC",
            (lemma, lemma.lower()),
        ).fetchall()
        surface_plan = self._conn.execute(
            "EXPLAIN QUERY PLAN "
            "SELECT l.id, l.lemma, l.pos, l.gender, l.semantic_ref, l.freq_rank "
            "FROM surface_lookup sl JOIN source.lemma l ON l.id = sl.lemma_id "
            "WHERE sl.lookup_key IN (?, ?) "
            "ORDER BY l.freq_rank ASC NULLS LAST, l.pos ASC, l.gender ASC NULLS LAST, "
            "l.semantic_ref ASC",
            (form, form.lower()),
        ).fetchall()
        return (
            "\n".join(str(row[-1]) for row in exact_plan),
            "\n".join(str(row[-1]) for row in surface_plan),
        )

    @staticmethod
    def _record(row: tuple[Any, ...]) -> LemmaRecord:
        return LemmaRecord(
            id=row[0], lemma=row[1], pos=row[2], gender=row[3],
            semantic_ref=row[4], freq_rank=row[5],
        )

    @lru_cache(maxsize=_CACHE_SIZE)
    def _exact_records(self, lemma: str) -> tuple[LemmaRecord, ...]:
        if self._conn is None:
            raise BuildDictError("Stage-02 lookup oracle is closed")
        rows = self._conn.execute(
            "SELECT id, lemma, pos, gender, semantic_ref, freq_rank FROM exact_lookup "
            "WHERE lookup_key IN (?, ?) GROUP BY id "
            "ORDER BY freq_rank ASC NULLS LAST, pos ASC, gender ASC NULLS LAST, "
            "semantic_ref ASC",
            (lemma, lemma.lower()),
        ).fetchall()
        return tuple(map(self._record, rows))

    @lru_cache(maxsize=_CACHE_SIZE)
    def _surface_records(self, form: str) -> tuple[LemmaRecord, ...]:
        if self._conn is None:
            raise BuildDictError("Stage-02 lookup oracle is closed")
        rows = self._conn.execute(
            "SELECT l.id, l.lemma, l.pos, l.gender, l.semantic_ref, l.freq_rank "
            "FROM surface_lookup sl JOIN source.lemma l ON l.id = sl.lemma_id "
            "WHERE sl.lookup_key IN (?, ?) "
            "ORDER BY l.freq_rank ASC NULLS LAST, l.pos ASC, l.gender ASC NULLS LAST, "
            "l.semantic_ref ASC",
            (form, form.lower()),
        ).fetchall()
        seen: set[int | None] = set()
        records: list[LemmaRecord] = []
        for row in rows:
            record = self._record(row)
            if record.id not in seen:
                seen.add(record.id)
                records.append(record)
        return tuple(records)

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaRecord]:
        matches = list(self._exact_records(lemma))
        if pos is not None:
            matches = [m for m in matches if m.pos == pos]
        if gender is not None:
            matches = [m for m in matches if m.gender == gender]
        return matches

    def lookup_surface_form(self, form: str) -> Sequence[LemmaRecord]:
        return self._surface_records(form)

    @lru_cache(maxsize=_CACHE_SIZE)
    def lookup_senses(self, lemma_id: int) -> Sequence[SenseRecord]:
        if self._conn is None:
            raise BuildDictError("Stage-02 lookup oracle is closed")
        rows = self._conn.execute(
            "SELECT id, lemma_id, ord, semantic_ref FROM source.sense "
            "WHERE lemma_id = ? ORDER BY ord ASC, semantic_ref ASC, id ASC",
            (lemma_id,),
        ).fetchall()
        return tuple(SenseRecord(*row) for row in rows)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        self._accelerator_path.unlink(missing_ok=True)


def parse_sentence_tsv(tsv_path: Path, lang_name: str) -> dict[int, str]:
    """Parse and strictly validate Tatoeba sentence projection TSV (A3)."""
    if not tsv_path.is_file():
        raise BuildDictError(f"{lang_name} projection file not found: {tsv_path}")
    sentences: dict[int, str] = {}
    with tsv_path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\r\n")
            parts = line.split("\t")
            if len(parts) != 2:
                raise BuildDictError(
                    f"Malformed sentence row in {tsv_path}:{line_no}: "
                    f"expected exactly 2 tab-separated fields, got {len(parts)}"
                )
            id_str, text = parts
            if not id_str.isdigit() or int(id_str) <= 0:
                raise BuildDictError(
                    f"Invalid sentence id '{id_str}' in {tsv_path}:{line_no}: "
                    f"must be a positive integer"
                )
            if not text.strip():
                raise BuildDictError(
                    f"Blank sentence text in {tsv_path}:{line_no}"
                )
            sid = int(id_str)
            if sid in sentences:
                raise BuildDictError(
                    f"Duplicate {lang_name} sentence id {sid} in {tsv_path}:{line_no}"
                )
            sentences[sid] = text
    return sentences


def parse_links_tsv(
    links_path: Path,
    de_sentence_ids: set[int],
    en_sentence_ids: set[int],
) -> dict[int, list[int]]:
    """Parse and strictly validate Tatoeba DE->EN link projection TSV (A3)."""
    if not links_path.is_file():
        raise BuildDictError(f"Links projection file not found: {links_path}")
    links_by_de: dict[int, list[int]] = {}
    seen_pairs: set[tuple[int, int]] = set()
    with links_path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\r\n")
            parts = line.split("\t")
            if len(parts) != 2:
                raise BuildDictError(
                    f"Malformed link row in {links_path}:{line_no}: "
                    f"expected exactly 2 tab-separated fields, got {len(parts)}"
                )
            de_id_str, en_id_str = parts
            if not de_id_str.isdigit() or int(de_id_str) <= 0:
                raise BuildDictError(
                    f"Invalid German sentence id '{de_id_str}' in links {links_path}:{line_no}"
                )
            if not en_id_str.isdigit() or int(en_id_str) <= 0:
                raise BuildDictError(
                    f"Invalid English sentence id '{en_id_str}' in links {links_path}:{line_no}"
                )
            de_id = int(de_id_str)
            en_id = int(en_id_str)
            pair = (de_id, en_id)
            if pair in seen_pairs:
                raise BuildDictError(
                    f"Duplicate link pair ({de_id}, {en_id}) in {links_path}:{line_no}"
                )
            seen_pairs.add(pair)
            if de_id not in de_sentence_ids:
                raise BuildDictError(
                    f"Dangling German sentence id {de_id} in {links_path}:{line_no}"
                )
            if en_id not in en_sentence_ids:
                raise BuildDictError(
                    f"Dangling English sentence id {en_id} in {links_path}:{line_no}"
                )
            links_by_de.setdefault(de_id, []).append(en_id)
    return links_by_de


class Stage02ProjectionStore:
    """Disk-backed validated Tatoeba projections for the real Stage-02 pass.

    The public parsing helpers intentionally return dictionaries for concise
    unit tests.  Real projections are substantially larger, so the build uses
    this temporary SQLite store to validate uniqueness and referential
    integrity without retaining the sentence corpora or link graph in memory.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.executescript(
            """
            CREATE TABLE de_sentence (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE en_sentence (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE de_en_link (
                de_id INTEGER NOT NULL,
                en_id INTEGER NOT NULL,
                PRIMARY KEY (de_id, en_id)
            ) WITHOUT ROWID;
            """
        )

    @staticmethod
    def _parse_sentence_rows(
        path: Path, table: str, language: str, conn: sqlite3.Connection
    ) -> None:
        if not path.is_file():
            raise BuildDictError(f"{language} projection file not found: {path}")
        batch: list[tuple[int, str]] = []
        try:
            with path.open("r", encoding="utf-8") as source:
                for line_no, raw_line in enumerate(source, 1):
                    parts = raw_line.rstrip("\r\n").split("\t")
                    if len(parts) != 2:
                        raise BuildDictError(
                            f"Malformed sentence row in {path}:{line_no}: "
                            f"expected exactly 2 tab-separated fields, got {len(parts)}"
                        )
                    id_str, text = parts
                    if not id_str.isdigit() or int(id_str) <= 0:
                        raise BuildDictError(
                            f"Invalid sentence id '{id_str}' in {path}:{line_no}: "
                            "must be a positive integer"
                        )
                    if not text.strip():
                        raise BuildDictError(f"Blank sentence text in {path}:{line_no}")
                    batch.append((int(id_str), text))
                    if len(batch) == 10_000:
                        conn.executemany(
                            f"INSERT INTO {table} (id, text) VALUES (?, ?)", batch
                        )
                        batch.clear()
                if batch:
                    conn.executemany(
                        f"INSERT INTO {table} (id, text) VALUES (?, ?)", batch
                    )
        except sqlite3.IntegrityError as exc:
            raise BuildDictError(
                f"Duplicate {language} sentence id in {path}"
            ) from exc

    @staticmethod
    def _parse_links(path: Path, conn: sqlite3.Connection) -> None:
        if not path.is_file():
            raise BuildDictError(f"Links projection file not found: {path}")
        batch: list[tuple[int, int]] = []
        try:
            with path.open("r", encoding="utf-8") as source:
                for line_no, raw_line in enumerate(source, 1):
                    parts = raw_line.rstrip("\r\n").split("\t")
                    if len(parts) != 2:
                        raise BuildDictError(
                            f"Malformed link row in {path}:{line_no}: "
                            f"expected exactly 2 tab-separated fields, got {len(parts)}"
                        )
                    de_id_str, en_id_str = parts
                    if not de_id_str.isdigit() or int(de_id_str) <= 0:
                        raise BuildDictError(
                            f"Invalid German sentence id '{de_id_str}' in links {path}:{line_no}"
                        )
                    if not en_id_str.isdigit() or int(en_id_str) <= 0:
                        raise BuildDictError(
                            f"Invalid English sentence id '{en_id_str}' in links {path}:{line_no}"
                        )
                    batch.append((int(de_id_str), int(en_id_str)))
                    if len(batch) == 10_000:
                        conn.executemany(
                            "INSERT INTO de_en_link (de_id, en_id) VALUES (?, ?)", batch
                        )
                        batch.clear()
                if batch:
                    conn.executemany(
                        "INSERT INTO de_en_link (de_id, en_id) VALUES (?, ?)", batch
                    )
        except sqlite3.IntegrityError as exc:
            raise BuildDictError(f"Duplicate link pair in {path}") from exc

    @classmethod
    def create(
        cls, path: Path, de_tsv: Path, en_tsv: Path, links_tsv: Path
    ) -> "Stage02ProjectionStore":
        store = cls(path)
        try:
            with store.conn:
                store._parse_sentence_rows(de_tsv, "de_sentence", "German", store.conn)
                store._parse_sentence_rows(en_tsv, "en_sentence", "English", store.conn)
                store._parse_links(links_tsv, store.conn)
                dangling_de = store.conn.execute(
                    "SELECT de_id FROM de_en_link "
                    "WHERE de_id NOT IN (SELECT id FROM de_sentence) LIMIT 1"
                ).fetchone()
                if dangling_de:
                    raise BuildDictError(
                        f"Dangling German sentence id {dangling_de[0]} in {links_tsv}"
                    )
                dangling_en = store.conn.execute(
                    "SELECT en_id FROM de_en_link "
                    "WHERE en_id NOT IN (SELECT id FROM en_sentence) LIMIT 1"
                ).fetchone()
                if dangling_en:
                    raise BuildDictError(
                        f"Dangling English sentence id {dangling_en[0]} in {links_tsv}"
                    )
        except Exception:
            store.close()
            raise
        return store

    def german_rows(self) -> Any:
        return self.conn.execute(
            """
            SELECT d.id, d.text, e.text
            FROM de_sentence d
            LEFT JOIN (
                SELECT de_id, MIN(en_id) AS en_id
                FROM de_en_link GROUP BY de_id
            ) chosen ON chosen.de_id = d.id
            LEFT JOIN en_sentence e ON e.id = chosen.en_id
            ORDER BY d.id ASC
            """
        )

    def close(self) -> None:
        self.conn.close()
        self.path.unlink(missing_ok=True)


def validate_stage01_database(stage01_path: Path) -> None:
    """Validate Stage-01 database input read-only before copying (A2)."""
    if not stage01_path.is_file():
        raise BuildDictError(f"Stage 01 database file not found: {stage01_path}")
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{stage01_path.resolve()}?mode=ro", uri=True)
        check = conn.execute("PRAGMA quick_check").fetchall()
        if check != [("ok",)]:
            raise BuildDictError(f"Stage 01 database PRAGMA quick_check failed: {check}")
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {
            "lemma",
            "surface_form",
            "sense",
            "sense_meaning",
            "sense_meaning_derivation",
        }
        missing = required_tables - tables
        if missing:
            raise BuildDictError(f"Stage 01 database missing required tables: {sorted(missing)}")
        if "example" in tables:
            tatoeba_count = conn.execute(
                "SELECT count(*) FROM example WHERE source = 'tatoeba'"
            ).fetchone()[0]
            if tatoeba_count > 0:
                raise BuildDictError(
                    f"Stage 01 database contains {tatoeba_count} pre-existing Tatoeba examples"
                )
    finally:
        if conn is not None:
            conn.close()


def validate_stage02_database(stage02_path: Path) -> None:
    """Validate Stage-02 database structure, attribution, and integrity (A2, A6, A7)."""
    if not stage02_path.is_file():
        raise BuildDictError(f"Stage 02 database file not found: {stage02_path}")
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{stage02_path.resolve()}?mode=ro", uri=True)
        check = conn.execute("PRAGMA quick_check").fetchall()
        if check != [("ok",)]:
            raise BuildDictError(f"Stage 02 database PRAGMA quick_check failed: {check}")
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {
            "lemma",
            "surface_form",
            "sense",
            "sense_meaning",
            "sense_meaning_derivation",
            "example",
            "example_lemma",
        }
        missing = required_tables - tables
        if missing:
            raise BuildDictError(f"Stage 02 database missing required tables: {sorted(missing)}")

        bad_attribution = conn.execute(
            "SELECT count(*) FROM example "
            "WHERE source='tatoeba' AND "
            "(source_ref IS NULL OR trim(source_ref)='' OR license IS NULL OR trim(license)='')"
        ).fetchone()[0]
        if bad_attribution > 0:
            raise BuildDictError(f"Stage 02 database has {bad_attribution} bad attribution rows")

        orphan_index = conn.execute(
            "SELECT count(*) FROM example_lemma el "
            "LEFT JOIN lemma l ON l.id=el.lemma_id "
            "LEFT JOIN example e ON e.id=el.example_id "
            "WHERE l.id IS NULL OR e.id IS NULL"
        ).fetchone()[0]
        if orphan_index > 0:
            raise BuildDictError(f"Stage 02 database has {orphan_index} orphan example_lemma rows")
    finally:
        if conn is not None:
            conn.close()


def build_stage02(
    stage01_path: Path | str,
    de_tsv_path: Path | str,
    en_tsv_path: Path | str,
    links_tsv_path: Path | str,
    output_path: Path | str,
    cache_dir: Path | str,
    license_label: str,
    spacy_model: str = "de_core_news_md",
    n_process: int = 8,
) -> None:
    """Execute build stage 02 deterministic Tatoeba example indexing with caching."""
    stage01 = Path(stage01_path).resolve()
    de_tsv = Path(de_tsv_path).resolve()
    en_tsv = Path(en_tsv_path).resolve()
    links_tsv = Path(links_tsv_path).resolve()
    output = Path(output_path)
    cache_root = Path(cache_dir).resolve()

    if not license_label or not license_label.strip():
        raise BuildDictError("License label must be nonblank")

    if output.exists():
        raise BuildDictError(f"Output path already exists: {output}")

    # Validate Stage 01 read-only before copying
    validate_stage01_database(stage01)

    # Compute cache key (calls canonical get_resolver_hash)
    cache_key = compute_stage02_cache_key(
        stage01_path=stage01,
        de_tsv_path=de_tsv,
        en_tsv_path=en_tsv,
        links_tsv_path=links_tsv,
        license_label=license_label,
        spacy_model=spacy_model,
    )
    cache_file = cache_root / f"{cache_key.replace(':', '_')}.sqlite"

    # Check cache HIT
    if cache_file.is_file():
        # Validate cached asset fail-closed
        try:
            validate_stage02_database(cache_file)
        except Exception as e:
            raise BuildDictError(f"Corrupt matching cache artifact '{cache_file}': {e}") from e

        sys.stdout.write(f"Cache key: {cache_key}\n")
        sys.stdout.write("Cache result: HIT\n")

        # Atomically publish copy to output
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        )
        temp_out_path = Path(temp_file.name)
        temp_file.close()
        try:
            shutil.copyfile(cache_file, temp_out_path)
            if output.exists():
                raise BuildDictError(f"Output path already exists: {output}")
            temp_out_path.replace(output)
            return
        finally:
            if temp_out_path.exists():
                temp_out_path.unlink(missing_ok=True)

    # Cache MISS
    sys.stdout.write(f"Cache key: {cache_key}\n")
    sys.stdout.write("Cache result: MISS\n")

    # Build Stage 02 in a temporary sibling file
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_out_path = Path(temp_file.name)
    temp_file.close()

    conn: sqlite3.Connection | None = None
    projection_store: Stage02ProjectionStore | None = None
    oracle: Stage02LookupOracle | None = None
    projection_temp = tempfile.NamedTemporaryFile(
        dir=output.parent,
        prefix=f".{output.name}.stage02-projections.",
        suffix=".sqlite.tmp",
        delete=False,
    )
    projection_path = Path(projection_temp.name)
    projection_temp.close()
    lookup_temp = tempfile.NamedTemporaryFile(
        dir=output.parent,
        prefix=f".{output.name}.stage02-lookup-",
        suffix=".sqlite.tmp",
        delete=False,
    )
    lookup_path = Path(lookup_temp.name)
    lookup_temp.close()
    lookup_path.unlink()
    try:
        # Validate inputs into a disk-backed store before opening the output.
        # This keeps the multi-million-row projections out of Python memory.
        projection_store = Stage02ProjectionStore.create(
            projection_path, de_tsv, en_tsv, links_tsv
        )

        # Copy Stage 01 to temp_out_path
        shutil.copyfile(stage01, temp_out_path)

        # Connect to temp output DB and ensure example / example_lemma schemas
        conn = sqlite3.connect(temp_out_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(STAGE02_EXAMPLE_SCHEMA_SQL)

        # Build a bounded-memory, disk-backed lookup accelerator alongside the
        # other Stage-02 temporary artifacts.  It is deleted in ``finally``.
        oracle = Stage02LookupOracle(stage01, lookup_path)

        # Load spaCy
        try:
            import spacy
            nlp = spacy.load(spacy_model)
        except Exception as e:
            raise BuildDictError(f"Failed to load spaCy model '{spacy_model}': {e}") from e

        example_id_counter = conn.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM example"
        ).fetchone()[0]
        example_batch: list[tuple[Any, ...]] = []
        index_batch: list[tuple[int, int]] = []
        BATCH_SIZE = 25000

        def flush_batches() -> None:
            if not example_batch:
                return
            if conn is None:
                raise BuildDictError("Stage 02 output connection unexpectedly closed")
            output_conn = conn
            output_conn.executemany(
                """
                INSERT INTO example (
                    id, de, en, source, source_ref, license, token_count, has_proper
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                example_batch,
            )
            output_conn.executemany(
                "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)",
                index_batch,
            )
            output_conn.commit()
            example_batch.clear()
            index_batch.clear()

        projection_items = (
            (de_text, (de_id, de_text, en_text))
            for de_id, de_text, en_text in projection_store.german_rows()
        )
        for doc, (de_id, de_text, en_text) in nlp.pipe(
            projection_items,
            as_tuples=True,
            n_process=n_process,
            batch_size=2000,
        ):
            non_space_tokens = [tok for tok in doc if not tok.is_space]
            token_count = len(non_space_tokens)
            has_proper = 1 if any(tok.pos_ == "PROPN" for tok in non_space_tokens) else 0

            resolved_lemma_ids: set[int] = set()
            for tok in doc:
                refs = resolve_token(tok, oracle)
                for ref in refs:
                    if ref.lemma_id is not None:
                        resolved_lemma_ids.add(ref.lemma_id)

            if not resolved_lemma_ids:
                continue

            example_id = example_id_counter
            example_id_counter += 1

            example_batch.append((
                example_id,
                de_text,
                en_text,
                "tatoeba",
                str(de_id),
                license_label,
                token_count,
                has_proper,
            ))

            for lid in sorted(resolved_lemma_ids):
                index_batch.append((lid, example_id))

            if len(example_batch) >= BATCH_SIZE:
                flush_batches()

        flush_batches()

        conn.close()
        conn = None

        # Validate built database
        validate_stage02_database(temp_out_path)

        # Atomically publish to cache directory
        cache_root.mkdir(parents=True, exist_ok=True)
        temp_cache = tempfile.NamedTemporaryFile(
            dir=cache_root,
            prefix=f".{cache_file.name}.",
            suffix=".tmp",
            delete=False,
        )
        temp_cache_path = Path(temp_cache.name)
        temp_cache.close()
        try:
            shutil.copyfile(temp_out_path, temp_cache_path)
            temp_cache_path.replace(cache_file)
        finally:
            if temp_cache_path.exists():
                temp_cache_path.unlink(missing_ok=True)

        # Atomically publish to output_path
        if output.exists():
            raise BuildDictError(f"Output path already exists: {output}")
        temp_out_path.replace(output)

    finally:
        if oracle is not None:
            oracle.close()
        if projection_store is not None:
            projection_store.close()
        else:
            projection_path.unlink(missing_ok=True)
        lookup_path.unlink(missing_ok=True)
        if conn is not None:
            conn.close()
        if temp_out_path.exists():
            temp_out_path.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for dictionary build tools."""
    parser = argparse.ArgumentParser(description="German Flashcards Dictionary Build Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage01_parser = subparsers.add_parser(
        "stage01",
        help="Stage 01: Build dictionary core from Wiktextract JSONL dumps",
    )
    stage01_parser.add_argument(
        "--en-jsonl",
        type=Path,
        required=True,
        help="Path to Wiktextract English edition JSONL dump",
    )
    stage01_parser.add_argument(
        "--de-jsonl",
        type=Path,
        required=True,
        help="Path to Wiktextract German edition JSONL dump",
    )
    stage01_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to target output SQLite database file",
    )

    stage02_parser = subparsers.add_parser(
        "stage02",
        help="Stage 02: Deterministic Tatoeba example indexing",
    )
    stage02_parser.add_argument(
        "--stage01",
        type=Path,
        required=True,
        help="Path to accepted Stage-01 SQLite dictionary database",
    )
    stage02_parser.add_argument(
        "--de-tsv",
        type=Path,
        required=True,
        help="Path to German Tatoeba sentence projection TSV",
    )
    stage02_parser.add_argument(
        "--en-tsv",
        type=Path,
        required=True,
        help="Path to English Tatoeba sentence projection TSV",
    )
    stage02_parser.add_argument(
        "--links-tsv",
        type=Path,
        required=True,
        help="Path to DE->EN Tatoeba links projection TSV",
    )
    stage02_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to target output SQLite database file",
    )
    stage02_parser.add_argument(
        "--cache-dir",
        type=Path,
        required=True,
        help="Path to Stage-02 cache directory",
    )
    stage02_parser.add_argument(
        "--license",
        type=str,
        required=True,
        help="Verified Tatoeba license label",
    )
    stage02_parser.add_argument(
        "--spacy-model",
        type=str,
        default="de_core_news_md",
        help="spaCy model for German sentence processing (default: de_core_news_md)",
    )
    stage02_parser.add_argument(
        "--n-process",
        type=int,
        default=8,
        help="Number of worker processes for spaCy nlp.pipe (default: 8)",
    )

    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))

    if args.command == "stage01":
        try:
            build_stage01(
                en_jsonl_path=args.en_jsonl,
                de_jsonl_path=args.de_jsonl,
                output_path=args.output,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Error during stage 01 build: {e}\n")
            return 1

    if args.command == "stage02":
        try:
            build_stage02(
                stage01_path=args.stage01,
                de_tsv_path=args.de_tsv,
                en_tsv_path=args.en_tsv,
                links_tsv_path=args.links_tsv,
                output_path=args.output,
                cache_dir=args.cache_dir,
                license_label=args.license,
                spacy_model=args.spacy_model,
                n_process=args.n_process,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Error during stage 02 build: {e}\n")
            return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
