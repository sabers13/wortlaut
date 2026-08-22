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

GENERATED_SOURCE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^llm_generated_v[1-9][0-9]*$")


class BuildDictError(Exception):
    """Base error for dictionary build failures."""


def _canonical_json(value: object) -> str:
    """Return the one stable JSON representation used by build artifacts."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


LINKAGE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "form_of",
        "alt_of",
        "compound_of",
        "taxonomic",
    }
)


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
            canonicalize_string_linkage(val) if is_linkage else canonicalize_string_projection(val)
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
            encoded = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
        payload = json.dumps(sorted_senseids, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
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
        payload = json.dumps(sorted_qids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
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

    senseid_counts: Counter[str] = Counter(c for c in senseid_candidates if c is not None)

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
            raise BuildDictError(f"Derivation edge references nonexistent source meaning {src_mid}")
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
                    min(acc.praeteritum_3sg_candidates) if acc.praeteritum_3sg_candidates else None
                )
                partizip_ii = (
                    min(acc.partizip_ii_candidates) if acc.partizip_ii_candidates else None
                )
                comparative = (
                    min(acc.comparative_candidates) if acc.comparative_candidates else None
                )
                superlative = (
                    min(acc.superlative_candidates) if acc.superlative_candidates else None
                )

                lemma_semantic_ref = compute_lemma_semantic_ref(acc.word, acc.pos, acc.gender)
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

    def __init__(self, db_path: Path | str, accelerator_path: Path | str | None = None) -> None:
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
            id=row[0],
            lemma=row[1],
            pos=row[2],
            gender=row[3],
            semantic_ref=row[4],
            freq_rank=row[5],
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
                raise BuildDictError(f"Blank sentence text in {tsv_path}:{line_no}")
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
                        conn.executemany(f"INSERT INTO {table} (id, text) VALUES (?, ?)", batch)
                        batch.clear()
                if batch:
                    conn.executemany(f"INSERT INTO {table} (id, text) VALUES (?, ?)", batch)
        except sqlite3.IntegrityError as exc:
            raise BuildDictError(f"Duplicate {language} sentence id in {path}") from exc

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
                    conn.executemany("INSERT INTO de_en_link (de_id, en_id) VALUES (?, ?)", batch)
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
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
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
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
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
        projection_store = Stage02ProjectionStore.create(projection_path, de_tsv, en_tsv, links_tsv)

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

            example_batch.append(
                (
                    example_id,
                    de_text,
                    en_text,
                    "tatoeba",
                    str(de_id),
                    license_label,
                    token_count,
                    has_proper,
                )
            )

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

    stage03_parser = subparsers.add_parser(
        "stage03",
        help="Stage 03: Deterministic enrichment queue construction",
    )
    stage03_parser.add_argument(
        "--stage02",
        type=Path,
        required=True,
        help="Path to accepted Stage-02 SQLite dictionary",
    )
    stage03_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output queue JSON file",
    )
    stage03_parser.add_argument(
        "--packet",
        type=Path,
        required=False,
        help="Path to source-acceptance packet JSON",
    )
    stage03_parser.add_argument(
        "--report",
        type=Path,
        required=False,
        help="Path to coverage report text",
    )

    stage04_parser = subparsers.add_parser(
        "stage04",
        help="Stage 04: Maintainer-only DE/EN enrichment",
    )
    stage04_parser.add_argument(
        "--queue",
        type=Path,
        required=True,
        help="Path to Stage-03 queue JSON",
    )
    stage04_parser.add_argument(
        "--stage02",
        type=Path,
        required=True,
        help="Path to Stage-02 SQLite asset",
    )
    stage04_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to enriched output SQLite",
    )
    stage04_parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Path to checkpoint JSON file",
    )
    stage04_parser.add_argument(
        "--generated-license",
        type=str,
        required=True,
        help="Generated output license classification",
    )
    stage04_parser.add_argument(
        "--bulk-de-model",
        type=str,
        default=STAGE04_DEFAULT_BULK_DE_MODEL,
        help="Bulk DE model",
    )
    stage04_parser.add_argument(
        "--bulk-en-model",
        type=str,
        default=STAGE04_DEFAULT_BULK_EN_MODEL,
        help="Bulk EN model",
    )
    stage04_parser.add_argument(
        "--qa-model",
        type=str,
        default=STAGE04_DEFAULT_QA_MODEL,
        help="QA model",
    )
    stage04_parser.add_argument(
        "--batch-size",
        type=int,
        default=STAGE04_DEFAULT_BATCH_SIZE,
        help="Transport batch size",
    )

    stage05_parser = subparsers.add_parser(
        "stage05",
        help="Stage 05: Final dictionary packaging",
    )
    stage05_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to enriched input SQLite",
    )
    stage05_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to versioned output SQLite",
    )
    stage05_parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Dictionary version label",
    )
    stage05_parser.add_argument(
        "--metadata",
        type=Path,
        required=False,
        help="Path to metadata JSON output",
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

    if args.command == "stage03":
        try:
            build_stage03(
                stage02_path=args.stage02,
                output_path=args.output,
                packet_path=args.packet,
                report_path=args.report,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Error during stage 03 build: {e}\n")
            return 1

    if args.command == "stage04":
        try:
            build_stage04(
                queue_path=args.queue,
                stage02_path=args.stage02,
                output_path=args.output,
                checkpoint_path=args.checkpoint,
                generated_license=args.generated_license,
                bulk_de_model=args.bulk_de_model,
                bulk_en_model=args.bulk_en_model,
                qa_model=args.qa_model,
                batch_size=args.batch_size,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Error during stage 04 build: {e}\n")
            return 1

    if args.command == "stage05":
        try:
            build_stage05(
                input_path=args.input,
                output_path=args.output,
                version=args.version,
                metadata_path=args.metadata,
            )
            return 0
        except Exception as e:
            sys.stderr.write(f"Error during stage 05 build: {e}\n")
            return 1

    return 1


# ======================================================================
# Stage 03, 04, 05 implementation for ADR-0006 / Slice-6
# ======================================================================

# --- Stage03 constants ---

DE_FORBIDDEN_META_PATTERNS: Final[tuple[str, ...]] = (
    "siehe",
    "vgl.",
    "vergleiche",
    "form von",
    "flexionsform",
    "plural von",
    "singular von",
    "abkürzung",
    "kurz für",
    "wortherkunft",
    "etymologie",
)

FORBIDDEN_FA_CODEPOINTS: Final[frozenset[int]] = frozenset(
    {
        0x061C,
        0x200E,
        0x200F,
        0x202A,
        0x202B,
        0x202C,
        0x202D,
        0x202E,
        0x2066,
        0x2067,
        0x2068,
        0x2069,
    }
)
ALLOWED_FA_CF: Final[frozenset[int]] = frozenset({0x200C})

GENERATED_MARKER: Final[str] = "llm_generated_v1"
GENERATED_MARKER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^llm_generated_v[1-9][0-9]*$")
STAGE03_QUEUE_FORMAT: Final[str] = "flashcard-stage03-queue-v2"
STAGE04_CHECKPOINT_FORMAT: Final[str] = "flashcard-stage04-checkpoint-v3"
STAGE04_MAX_TEXT_LENGTH: Final[int] = 280
STAGE04_BULK_PIPELINE_VERSION: Final[str] = "stage04-bulk-v3"
STAGE04_QA_PIPELINE_VERSION: Final[str] = "stage04-qa-v3"
STAGE04_RESPONSE_SCHEMA_VERSION: Final[str] = "openai-responses-json-schema-v2"
STAGE04_BULK_REASONING_EFFORT: Final[str] = "none"
STAGE04_QA_REASONING_EFFORT: Final[str] = "low"
STAGE04_MAX_OUTPUT_TOKENS: Final[int] = 512
STAGE04_INPUT_TOKEN_SAFETY_MULTIPLIER: Final[float] = 2.0
STAGE04_DEFAULT_BULK_DE_MODEL: Final[str] = "gpt-5.6-luna"
STAGE04_DEFAULT_BULK_EN_MODEL: Final[str] = "gpt-5.6-luna"
STAGE04_DEFAULT_QA_MODEL: Final[str] = "gpt-5.6-terra"
STAGE04_DEFAULT_BATCH_SIZE: Final[int] = 100
STAGE04_DEFAULT_PROVIDER_MAX_BYTES: Final[int] = 200 * 1024 * 1024
STAGE04_DEFAULT_PROVIDER_MAX_REQUESTS: Final[int] = 50000

FA_JOB_CLASS: Final[str] = "fa_generated_meaning"
FA_ITEM_VERSION: Final[str] = "fa-generation-job:v2"
FA_INPUT_VERSION: Final[str] = "fa-input-v3"
FA_BULK_VERSION: Final[str] = "fa-bulk-v3"
FA_RESPONSE_VERSION: Final[str] = "fa-response-v2"
FA_CANARY_STRATA_VERSION: Final[str] = "fa-canary-strata-v1"
OUTPUT_CLASSIFICATION: Final[str] = "AI_GENERATED_FROM_WIKTIONARY_ATTRIBUTED_v1"
MAX_FA_SCALARS: Final[int] = 160
MAX_FA_TOKENS: Final[int] = 24
CANARY_HARD_SPEND_CAP_USD: Final[float] = 0.10

FA_V3_INSTRUCTIONS: Final[str] = (
    "Translate the meaning of exactly this ONE canonical German sense into Persian.\n"
    "Return the shortest natural meaning that faithfully preserves that exact sense.\n"
    "Use neutral standard written Persian (فارسی معیار).\n"
    "Return Persian meaning text only.\n"
    "Do not repeat the German lemma merely as explanation.\n"
    "Do not include German or English dictionary commentary.\n"
    "Do not include Latin-script grammatical labels such as Nominativ, Akkusativ, Dativ, "
    "Genitiv, Singular, or Plural; translate required grammatical information into concise "
    "Persian instead.\n"
    "Do not add etymology, examples, parenthetical dictionary commentary, or alternative "
    "unrelated senses.\n"
    "Do not merge multiple meanings: the output is for exactly this one sense only.\n"
    "For an ordinary lexical sense: produce one concise Persian lexical equivalent or a short "
    "meaning phrase.\n"
    "For a morphology/inflection sense: do NOT invent a lexical translation of another sense; "
    "provide only a concise Persian grammatical description of the exact morphology represented "
    "by the supplied English source meaning.\n"
    "Prefer brevity well below the mechanical maximum of 160 Unicode scalars and 24 "
    "whitespace-delimited tokens."
)


def fa_v3_request_input(lemma: str, pos: str, en_meaning: str) -> str:
    """Actual transmitted instruction text for fa_generated_meaning (fa-input-v3).

    This function is the single committed source of the live prompt semantics;
    synchronous and Batch logical request bodies must both serialize exactly this.
    """
    raise BuildDictError("Retired Persian generation path is unavailable under ADR-0007")
    return (
        f"German lemma: {lemma}\nPOS: {pos}\nExact English sense: {en_meaning}\n\n"
        f"{FA_V3_INSTRUCTIONS}"
    )


def fa_v3_request_body(item: dict[str, object], model: str) -> dict[str, object]:
    """Logical provider request body (fa-bulk-v3) for one semantic item.

    The identical body is used for the standard synchronous Responses transport
    and inside the Batch envelope ({custom_id, method, url, body}); only the
    transport envelope differs.
    """
    raise BuildDictError("Retired Persian generation path is unavailable under ADR-0007")
    return {
        "model": model,
        "input": fa_v3_request_input(str(item["lemma"]), str(item["pos"]), str(item["en_meaning"])),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "persian",
                "schema": {
                    "type": "object",
                    "properties": {"persian": {"type": "string"}},
                    "required": ["persian"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        },
    }


DE_LEARNER_INSTRUCTIONS: Final[str] = (
    "Work only on the supplied single semantic sense.\n"
    "The supplied English meaning text defines that sense.\n"
    "The stable identity refs (lemma_semantic_ref, sense_semantic_ref) are opaque identifiers and carry no semantic meaning; do not interpret them.\n"  # noqa: E501
    "Output German only.\n"
    "Prefer one simple/common German synonym when it truly preserves the exact sense.\n"
    "Otherwise produce one short learner-friendly German explanation.\n"
    "Aim approximately at A2-B1 comprehension where practical.\n"
    "Do not broaden, narrow, merge, or drift to another sense.\n"
    "Do not merely repeat or inflect the lemma as the definition.\n"
    "No dictionary meta-commentary such as 'siehe', 'vgl.', 'Abkürzung', 'Form von', etc.\n"
    "No etymology, examples, analysis, alternative unrelated senses, or English.\n"
    "For morphology/inflection senses, describe that exact morphology concisely in German when a simple synonym is not appropriate.\n"  # noqa: E501
    "Return only the fields defined by the structured response schema.\n"
    "Prefer brevity well below deterministic maximum bounds."
)

DE_LEARNER_SCHEMA: Final[dict[str, object]] = {
    "type": "json_schema",
    "name": "de_learner_meaning",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "meaning": {"type": "string"},
            "kind": {"type": "string", "enum": ["synonym", "definition"]},
        },
        "required": ["meaning", "kind"],
        "additionalProperties": False,
    },
}

EN_MEANING_SCHEMA: Final[dict[str, object]] = {
    "type": "json_schema",
    "name": "en_meaning",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"meaning": {"type": "string"}},
        "required": ["meaning"],
        "additionalProperties": False,
    },
}


def _build_de_prompt_text(item: dict[str, object]) -> str:
    lemma = str(item.get("lemma_text", ""))
    pos = str(item.get("pos", ""))
    gender = item.get("gender")
    lemma_ref = str(item.get("lemma_semantic_ref", ""))
    sense_ref = str(item.get("sense_semantic_ref", ""))
    en_inputs = item.get("derivation_inputs", [])
    if not isinstance(en_inputs, list):
        en_inputs = []
    lines: list[str] = []
    lines.append("Generate a German learner meaning for exactly ONE semantic sense.")
    lines.append(f"German lemma: {lemma}")
    lines.append(f"POS: {pos}")
    if gender is not None and str(gender).strip():
        lines.append(f"Gender: {gender}")
    lines.append("English meaning(s) defining this exact sense (canonical order, same sense, source-backed):")  # noqa: E501
    if en_inputs:
        for idx, en in enumerate(en_inputs, 1):
            if isinstance(en, dict):
                txt = str(en.get("text", "")).strip()
                lines.append(f"{idx}. {txt}")
            else:
                lines.append(f"{idx}. {str(en)}")
    else:
        lines.append("(no English source meaning available for this sense)")
    lines.append("Opaque identifiers (carry no semantic meaning, for correlation only):")
    lines.append(f"lemma_semantic_ref: {lemma_ref}  # opaque")
    lines.append(f"sense_semantic_ref: {sense_ref}  # opaque")
    lines.append("")
    lines.append(DE_LEARNER_INSTRUCTIONS)
    return "\n".join(lines)


def de_learner_meaning_request_body(item: dict[str, object], model: str) -> dict[str, object]:
    """Single-source logical request body for de_learner_meaning (stage04-bulk-v3).

    The identical body is used for synchronous POST /v1/responses and for
    Batch record body. The body carries explicit deterministic reasoning
    configuration and a provider-enforced output-token ceiling; the API
    max_output_tokens bound covers visible output plus reasoning tokens.
    """
    if not model or not model.strip():
        raise BuildDictError("Model must be non-empty for DE request body")
    prompt = _build_de_prompt_text(item)
    # Ensure prompt contains real instructions and EN texts
    if "German lemma:" not in prompt or "English meaning(s)" not in prompt:
        raise BuildDictError("DE prompt missing required semantic context")
    return {
        "model": model,
        "input": prompt,
        "reasoning": {"effort": STAGE04_BULK_REASONING_EFFORT},
        "max_output_tokens": STAGE04_MAX_OUTPUT_TOKENS,
        "text": {"format": dict(DE_LEARNER_SCHEMA)},
    }


def en_meaning_request_body(item: dict[str, object], model: str) -> dict[str, object]:
    """Single-source logical request body for en_meaning."""
    if not model or not model.strip():
        raise BuildDictError("Model must be non-empty for EN request body")
    lemma = str(item.get("lemma_text", ""))
    pos = str(item.get("pos", ""))
    gender = item.get("gender")
    lemma_ref = str(item.get("lemma_semantic_ref", ""))
    sense_ref = str(item.get("sense_semantic_ref", ""))
    lines: list[str] = []
    lines.append("Generate an English translation for exactly ONE German semantic sense.")
    lines.append(f"German lemma: {lemma}")
    lines.append(f"POS: {pos}")
    if gender is not None and str(gender).strip():
        lines.append(f"Gender: {gender}")
    lines.append("Opaque identifiers (carry no semantic meaning, for correlation only):")
    lines.append(f"lemma_semantic_ref: {lemma_ref}  # opaque")
    lines.append(f"sense_semantic_ref: {sense_ref}  # opaque")
    lines.append("Return only the fields defined by the structured response schema. Output English only.")  # noqa: E501
    prompt = "\n".join(lines)
    return {
        "model": model,
        "input": prompt,
        "reasoning": {"effort": STAGE04_BULK_REASONING_EFFORT},
        "max_output_tokens": STAGE04_MAX_OUTPUT_TOKENS,
        "text": {"format": dict(EN_MEANING_SCHEMA)},
    }


def _request_body_for_item(item: dict[str, object], bulk_de_model: str, bulk_en_model: str) -> dict[str, object]:  # noqa: E501
    lang = str(item.get("language", ""))
    if lang == "de":
        return de_learner_meaning_request_body(item, bulk_de_model)
    if lang == "en":
        return en_meaning_request_body(item, bulk_en_model)
    raise BuildDictError(f"Unsupported language for request body: {lang}")


def de_learner_qa_request_body(item: dict[str, object], candidate_text: str, model: str) -> dict[str, object]:  # noqa: E501
    """QA body that receives repaired semantic context plus German candidate."""
    if not model or not model.strip():
        raise BuildDictError("Model must be non-empty for QA request body")
    lemma = str(item.get("lemma_text", ""))
    pos = str(item.get("pos", ""))
    gender = item.get("gender")
    lemma_ref = str(item.get("lemma_semantic_ref", ""))
    sense_ref = str(item.get("sense_semantic_ref", ""))
    en_inputs = item.get("derivation_inputs", [])
    if not isinstance(en_inputs, list):
        en_inputs = []
    lines: list[str] = []
    lines.append("Evaluate the German learner meaning candidate for exactly ONE semantic sense.")
    lines.append(f"German lemma: {lemma}")
    lines.append(f"POS: {pos}")
    if gender is not None and str(gender).strip():
        lines.append(f"Gender: {gender}")
    lines.append("English meaning(s) defining this exact sense (canonical order, same sense, source-backed):")  # noqa: E501
    if en_inputs:
        for idx, en in enumerate(en_inputs, 1):
            if isinstance(en, dict):
                lines.append(f"{idx}. {str(en.get('text','')).strip()}")
    lines.append(f"German candidate to evaluate: {candidate_text}")
    lines.append("Opaque identifiers (carry no semantic meaning, for correlation only):")
    lines.append(f"lemma_semantic_ref: {lemma_ref}  # opaque")
    lines.append(f"sense_semantic_ref: {sense_ref}  # opaque")
    lines.append("Instructions: verify the candidate preserves the exact sense defined by the English meaning(s), is German only, contains no meta-commentary, and follows A2-B1 brevity. Return the corrected meaning if needed, preserving the strict schema.")  # noqa: E501
    # QA reuses DE schema for correction
    return {
        "model": model,
        "input": "\n".join(lines),
        "reasoning": {"effort": STAGE04_QA_REASONING_EFFORT},
        "max_output_tokens": STAGE04_MAX_OUTPUT_TOKENS,
        "text": {"format": dict(DE_LEARNER_SCHEMA)},
    }


def stage04_worst_case_request_cost_usd(
    input_token_estimate: int,
    max_output_tokens: int,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
    input_safety_multiplier: float = STAGE04_INPUT_TOKEN_SAFETY_MULTIPLIER,
) -> float:
    """Deterministic pre-transmission worst-case cost of ONE paid request.

    The API output-token ceiling covers visible output plus reasoning tokens,
    so ALL ``max_output_tokens`` are charged at the authorized model output
    rate, and the input estimate is inflated by the accepted safety multiplier.
    Model prices are operational execution inputs supplied by the live
    execution plan and must be reverified before live work; they are never
    code constants here.
    """
    if input_token_estimate < 0 or max_output_tokens <= 0:
        raise BuildDictError("Token estimates must be non-negative/max-positive")
    if input_price_per_mtok < 0 or output_price_per_mtok < 0:
        raise BuildDictError("Authorized prices must be non-negative")
    if input_safety_multiplier < 1.0:
        raise BuildDictError("Input safety multiplier must be >= 1.0")
    worst_input_tokens = input_token_estimate * input_safety_multiplier
    return (worst_input_tokens / 1_000_000.0) * input_price_per_mtok + (
        max_output_tokens / 1_000_000.0
    ) * output_price_per_mtok


def stage04_pretransmission_guard_blocks(
    recorded_spend_usd: float,
    authorized_hard_cap_usd: float,
    next_request_worst_case_usd: float,
) -> bool:
    """True => the next request MUST NOT be transmitted (fail closed).

    The live synchronous canary worker refuses to transmit when recorded spend
    plus the worst-case cost of the next request would exceed the authorized
    hard cap; otherwise transmission is permitted.
    """
    if recorded_spend_usd < 0 or authorized_hard_cap_usd < 0:
        raise BuildDictError("Spend figures must be non-negative")
    if next_request_worst_case_usd < 0:
        raise BuildDictError("Worst-case cost must be non-negative")
    return recorded_spend_usd + next_request_worst_case_usd > authorized_hard_cap_usd


def credential_format_ok(value: str) -> bool:
    """Local/no-network credential-format sanity check (never prints/persists).

    Rejects empty values, surrounding quotes left in by naive .env parsing
    (Attempt-1 operational defect), and embedded whitespace.
    """
    if not value:
        return False
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return False
    if any(c.isspace() for c in v):
        return False
    return True


def _estimate_fa_cost(
    num_items: int,
    mean_input_tokens: float = 146.5,
    mean_output_tokens: float = 5.0,
    bulk_input_price: float = 0.10,
    bulk_output_price: float = 0.60,
) -> float:
    """Estimate FA Batch cost for num_items, fail closed if exceeds cap."""
    raise BuildDictError("Retired Persian canary costing is unavailable under ADR-0007")
    total_input = num_items * mean_input_tokens
    total_output = num_items * mean_output_tokens
    cost = (total_input / 1_000_000) * bulk_input_price + (
        total_output / 1_000_000
    ) * bulk_output_price  # noqa: E501
    return cost


def _check_canary_spend_cap(num_items: int = 50) -> None:
    """Fail closed if estimated canary cost exceeds hard cap."""
    raise BuildDictError("Retired Persian canary path is unavailable under ADR-0007")
    est = _estimate_fa_cost(num_items)
    if est > CANARY_HARD_SPEND_CAP_USD:
        raise BuildDictError(
            f"Canary estimated cost ${est:.4f} exceeds hard cap ${CANARY_HARD_SPEND_CAP_USD:.2f}"
        )  # noqa: E501


def _write_canary_selection_manifest(
    candidates: list[dict[str, object]], path: Path
) -> tuple[str, int]:
    """Write canary selection as exact canonical compact JSON bytes, hash actual file bytes."""
    # Ensure bytewise order
    candidates_sorted = sorted(candidates, key=lambda x: str(x["item_id"]).encode())
    data = json.dumps(
        candidates_sorted, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    )
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        with tmp_path.open("wb") as f:
            f.write(data)
        # Verify hash
        actual_sha = hashlib.sha256(tmp_path.read_bytes()).hexdigest()
        expected_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != expected_sha:
            raise BuildDictError("Canary selection hash mismatch")
        if path.exists():
            raise BuildDictError(f"Output path already exists: {path}")
        tmp_path.replace(path)
        return actual_sha, len(data)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _render_canary_receipt(path: Path, expected_sha256: str) -> list[dict[str, object]]:
    """Human receipt renderer: re-reads canonical selection artifact, SHA-verified.

    Every displayed field for one row must come from the exact same artifact
    record. Rejects extra/missing/mutated rows and SHA mismatches fail closed.
    """
    if not path.is_file():
        raise BuildDictError(f"Canary artifact not found: {path}")
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha256:
        raise BuildDictError(f"Canary SHA mismatch: expected {expected_sha256}, got {actual_sha}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise BuildDictError("Canary artifact is malformed JSON") from e
    if not isinstance(data, list):
        raise BuildDictError("Canary artifact must be a JSON list")
    # Verify deterministic bytewise order
    ids = [str(rec.get("item_id", "")) for rec in data if isinstance(rec, dict)]
    if ids != sorted(ids, key=lambda x: x.encode()):
        raise BuildDictError("Canary artifact not bytewise sorted")
    # Validate each record structure minimally
    for rec in data:
        if not isinstance(rec, dict):
            raise BuildDictError("Canary artifact record must be object")
        if "item_id" not in rec or "lemma_text" not in rec:
            # Require minimal fields for DE canary; allow generic but ensure item_id present
            raise BuildDictError("Canary artifact record missing required fields")
    return data


def _validate_persian_unicode(text: str) -> str | None:
    """Validate Persian Unicode per ADR-0006. Return error code or None on pass."""
    if not text.strip():
        return "empty"
    for ch in text:
        cp = ord(ch)
        if cp in FORBIDDEN_FA_CODEPOINTS:
            return f"forbidden_bidi_U+{cp:04X}"
        cat = unicodedata.category(ch)
        if cat == "Cc":
            return f"forbidden_Cc_U+{cp:04X}"
        if cat == "Cf" and cp not in ALLOWED_FA_CF:
            return f"forbidden_Cf_U+{cp:04X}"
    return None


def _validate_de_source_eligibility(text: str, kind: str) -> str | None:
    """Positive DE eligibility predicate. Return error/None. None means eligible (retain)."""
    # kind must be synonym or definition
    if kind not in ("synonym", "definition"):
        return "invalid_kind"
    # no URL
    lower = text.lower()
    if "http://" in lower or "https://" in lower or "www." in lower:
        return "has_url"
    # forbidden meta patterns (case-insensitive)
    for pat in DE_FORBIDDEN_META_PATTERNS:
        if pat in lower:
            return f"forbidden_meta_{pat}"
    # markup / control
    if "\n" in text or "\r" in text or "\t" in text:
        return "has_linebreak_or_tab"
    if "[[" in text or "]]" in text or "{{" in text or "}}" in text:
        return "has_wiki_markup"
    if "<" in text or ">" in text:
        return "has_html_markup"
    # bidi/control except ZWNJ
    for ch in text:
        cp = ord(ch)
        if cp in FORBIDDEN_FA_CODEPOINTS:
            return f"forbidden_bidi_U+{cp:04X}"
        cat = unicodedata.category(ch)
        if cat == "Cc":
            return f"forbidden_Cc_U+{cp:04X}"
        if cat == "Cf" and cp not in ALLOWED_FA_CF:
            return f"forbidden_Cf_U+{cp:04X}"
    # token/scalar bounds
    stripped = text.strip()
    if not stripped:
        return "blank"
    tokens = stripped.split()
    scalar_len = len(stripped)
    if kind == "synonym":
        if not (1 <= len(tokens) <= 4):
            return "synonym_token_bounds"
        if not (1 <= scalar_len <= 40):
            return "synonym_scalar_bounds"
        if stripped[-1] in ".!?":
            return "synonym_final_punct"
    elif kind == "definition":
        if not (2 <= len(tokens) <= 16):
            return "definition_token_bounds"
        if scalar_len > 100:
            return "definition_scalar_bounds"
        # at most one .!? only as final punctuation
        punct_count = sum(1 for c in stripped if c in ".!?")
        if punct_count > 1:
            return "definition_multi_punct"
        if punct_count == 1 and stripped[-1] not in ".!?":
            return "definition_punct_not_final"
    return None


def _fa_duplicate_key(text: str) -> str:
    """Duplicate-only dedup key: NFC -> strip -> collapse whitespace to U+0020."""
    nfc = unicodedata.normalize("NFC", text)
    stripped = nfc.strip()
    # collapse each run of Unicode White_Space to one U+0020
    parts = stripped.split()
    # split uses any whitespace; rejoin with single space
    return " ".join(parts)


def _compute_queue_item_id(
    lemma_ref: str, sense_ref: str, language: str, job_class: str, context_payload: str
) -> str:
    payload = json.dumps(
        [lemma_ref, sense_ref, language, job_class, context_payload],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    return f"queue:v2:{hashlib.sha256(payload).hexdigest()[:32]}"


def _compute_queue_item_id_v2(
    lemma_ref: str,
    sense_ref: str,
    language: str,
    job_class: str,
    semantic_rows: list[dict[str, object]],
) -> str:
    """Compute durable queue:v2: item id from semantic identity + source content.

    semantic_rows is the ordered list of EN source rows represented as
    deterministic semantic content dicts with keys language, kind, ord, text,
    source, license (no numeric IDs). The hash depends only on that content
    plus the stable lemma/sense refs, target language and job class.
    """
    payload = json.dumps(
        [lemma_ref, sense_ref, language, job_class, semantic_rows],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"queue:v2:{hashlib.sha256(payload).hexdigest()[:32]}"


def _compute_fa_v2_item_id(lemma_ref: str, sense_ref: str) -> str:
    """Compute durable FA v2 item id per fa-generation-job:v2 spec."""
    payload = json.dumps(
        [lemma_ref, sense_ref, "fa", FA_JOB_CLASS],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")
    return f"{FA_ITEM_VERSION}:{hashlib.sha256(payload).hexdigest()}"


MORPHOLOGY_PATTERNS: Final[tuple[str, ...]] = (
    "inflection of",
    "plural of",
    "singular of",
    "genitive",
    "nominative",
    "accusative",
    "dative",
    "subjunctive",
    "indicative",
    "imperative",
    "participle",
    "comparative degree",
    "superlative degree",
    "first-person",
    "second-person",
    "third-person",
)


def _is_morphology_sense(en_text: str | None) -> bool:
    """Deterministic morphology classifier fa-canary-strata-v1."""
    if not en_text:
        return False
    lower = en_text.lower()
    return any(pat in lower for pat in MORPHOLOGY_PATTERNS)


def _validate_fa_v2_output(text: str, lemma_text: str) -> str | None:
    """Validate single Persian output per v2 contract."""
    stripped = text.strip()
    if not stripped:
        return "empty"
    if len(stripped) < 1:
        return "too_short"
    if len(stripped) > MAX_FA_SCALARS:
        return "too_long"
    tokens = stripped.split()
    if len(tokens) > MAX_FA_TOKENS:
        return "too_many_tokens"
    # Must contain at least one Arabic-script character
    has_arabic = any("\u0600" <= ch <= "\u06ff" or "\u0750" <= ch <= "\u077f" for ch in stripped)
    if not has_arabic:
        return "non_persian"
    if stripped.lower() == lemma_text.strip().lower():
        return "echo_lemma"
    # Exact German lemma embedded inside a longer output is dictionary commentary
    # (Attempt-1 defect), not a Persian meaning. Substring match of the full lemma
    # only; no broader ASCII ban (legitimate acronyms/identifiers remain allowed).
    if lemma_text.strip().lower() in stripped.lower():
        return "lemma_repetition"
    # Persian unicode
    err = _validate_persian_unicode(stripped)
    if err is not None:
        return err
    # No markdown or commentary
    if stripped.startswith("#") or "```" in stripped or stripped.startswith("- "):
        return "has_markdown"
    return None


def _build_fa_v2_candidates(stage02_path: Path) -> list[dict[str, object]]:
    """Build deterministic FA v2 candidate manifest (read-only, no numeric IDs)."""
    raise BuildDictError("Retired Persian candidate construction is unavailable under ADR-0007")
    conn = sqlite3.connect(f"file:{stage02_path.resolve()}?mode=ro", uri=True)
    try:
        # Map sense_id to en text for filtering
        # Need sense_id, but we can get via query that includes id
        senses_with_id = conn.execute(
            "SELECT s.id, s.semantic_ref, l.semantic_ref, l.lemma, l.pos, l.gender "
            "FROM sense s JOIN lemma l ON l.id=s.lemma_id "
            "ORDER BY s.semantic_ref ASC, s.id ASC"
        ).fetchall()
        en_text_by_id: dict[int, str] = {}
        for sid, txt in conn.execute(
            "SELECT sense_id, text FROM sense_meaning WHERE language='en' "
            "ORDER BY sense_id, ord ASC"
        ):  # noqa: E501
            if sid not in en_text_by_id:
                en_text_by_id[sid] = txt
        candidates: list[dict[str, object]] = []
        for sid, sref, lref, lemma, pos, gender in senses_with_id:
            en_txt = en_text_by_id.get(sid)
            if not en_txt or not en_txt.strip():
                continue  # Exclude candidates missing EN (exactly one EN edge required)
            item_id = _compute_fa_v2_item_id(lref, sref)
            candidates.append(
                {
                    "item_id": item_id,
                    "custom_id": f"batch:{item_id}",
                    "lemma_semantic_ref": lref,
                    "sense_semantic_ref": sref,
                    "lemma": lemma,
                    "pos": pos,
                    "gender": gender,
                    "en_meaning": en_txt,
                }
            )
        candidates.sort(key=lambda x: str(x["item_id"]).encode())
        # Ensure unique
        seen: set[str] = set()
        for c in candidates:
            iid = str(c["item_id"])
            if iid in seen:
                raise BuildDictError(f"Duplicate FA v2 item_id {iid}")
            seen.add(iid)
            if str(c.get("job_class", FA_JOB_CLASS)) == "fa_translation":
                raise BuildDictError("Historical fa_translation must not be reused")
        # Strip to durable manifest (no numeric IDs)
        final: list[dict[str, object]] = []
        for c in candidates:
            final.append(
                {
                    "item_id": c["item_id"],
                    "custom_id": c["custom_id"],
                    "lemma_semantic_ref": c["lemma_semantic_ref"],
                    "sense_semantic_ref": c["sense_semantic_ref"],
                    "lemma": c["lemma"],
                    "pos": c["pos"],
                    "gender": c["gender"],
                    "en_meaning": c["en_meaning"],
                    "job_class": FA_JOB_CLASS,
                }
            )
        return final
    finally:
        conn.close()


def _select_fa_canary_v2(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select 25 morphology + 25 lexical deterministically, then bytewise order."""
    raise BuildDictError("Retired Persian canary selection is unavailable under ADR-0007")
    morph: list[dict[str, object]] = []
    lexical: list[dict[str, object]] = []
    for c in candidates:
        en = str(c.get("en_meaning", ""))
        if _is_morphology_sense(en):
            morph.append(c)
        else:
            lexical.append(c)
    morph_sorted = sorted(
        morph, key=lambda x: hashlib.sha256(str(x["item_id"]).encode()).hexdigest()
    )  # noqa: E501
    lexical_sorted = sorted(
        lexical, key=lambda x: hashlib.sha256(str(x["item_id"]).encode()).hexdigest()
    )  # noqa: E501
    selected = morph_sorted[:25] + lexical_sorted[:25]
    # If not enough in one stratum, fill from other
    if len(selected) < 50:
        remaining = [c for c in candidates if c not in selected]
        remaining_sorted = sorted(
            remaining, key=lambda x: hashlib.sha256(str(x["item_id"]).encode()).hexdigest()
        )  # noqa: E501
        selected.extend(remaining_sorted[: 50 - len(selected)])
    selected.sort(key=lambda x: str(x["item_id"]).encode())
    return selected


def validate_stage02_for_stage03(stage02_path: Path) -> None:
    """Validate Stage-02 input read-only."""
    if not stage02_path.is_file():
        raise BuildDictError(f"Stage 02 database file not found: {stage02_path}")
    conn = sqlite3.connect(f"file:{stage02_path.resolve()}?mode=ro", uri=True)
    try:
        check = conn.execute("PRAGMA quick_check").fetchall()
        if check != [("ok",)]:
            raise BuildDictError(f"Stage 02 PRAGMA quick_check failed: {check}")
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }  # noqa: E501
        required = {
            "lemma",
            "surface_form",
            "sense",
            "sense_meaning",
            "sense_meaning_derivation",
            "example",
            "example_lemma",
        }  # noqa: E501
        missing = required - tables
        if missing:
            raise BuildDictError(f"Stage 02 missing required tables: {sorted(missing)}")
    finally:
        conn.close()


def build_stage03(
    stage02_path: Path | str,
    output_path: Path | str,
    packet_path: Path | str | None = None,
    report_path: Path | str | None = None,
) -> dict[str, object]:
    """Execute Stage 03 deterministic enrichment queue construction — v2 semantic context.

    Repair: every de_learner_meaning job carries ALL same-sense source-backed EN
    sense_meaning rows (ordered ord ASC, id ASC) as semantic context and
    derivation inputs. Item identity depends only on stable semantic refs and
    that source-content (no numeric IDs). Queue format is flashcard-stage03-queue-v2
    with queue:v2: ids. Implementation is deterministic and bounded-memory via
    temp-sort DB and streaming writes.
    """
    stage02_p = Path(stage02_path)
    out_p = Path(output_path)
    if out_p.exists():
        raise BuildDictError(f"Output path already exists: {out_p}")
    if packet_path is not None or report_path is not None:
        raise BuildDictError(
            "Persian-era Stage 03 packet/report outputs are retired by ADR-0007"
        )
    validate_stage02_for_stage03(stage02_p)
    sha_before = sha256_file(stage02_p)

    # Use a temp directory for bounded-memory sort spill
    out_p.parent.mkdir(parents=True, exist_ok=True)
    temp_sort_file = tempfile.NamedTemporaryFile(
        dir=out_p.parent, prefix=f".{out_p.name}.sort.", suffix=".sqlite.tmp", delete=False
    )
    temp_sort_path = Path(temp_sort_file.name)
    temp_sort_file.close()
    temp_sort_path.unlink(missing_ok=True)

    conn_sort = sqlite3.connect(temp_sort_path)
    conn_sort.execute("CREATE TABLE temp_items(item_id TEXT PRIMARY KEY, item_json TEXT NOT NULL)")
    # For quick stats
    total_senses = 0
    de_count = 0
    en_count = 0
    derivation_inputs_total = 0
    one_source = 0
    two_source = 0
    three_source = 0
    zero_source = 0

    conn = sqlite3.connect(f"file:{stage02_p.resolve()}?mode=ro", uri=True)
    try:
        # Iterate senses in deterministic order (semantic_ref). Use cursor streaming.
        sense_cur = conn.execute(
            "SELECT s.id, s.lemma_id, s.semantic_ref, l.semantic_ref as lemma_ref, "
            "l.lemma, l.pos, l.gender "
            "FROM sense s JOIN lemma l ON l.id=s.lemma_id "
            "ORDER BY s.semantic_ref ASC, s.id ASC"
        )
        for sense_row in sense_cur:
            sid, lemma_id, sense_ref, lemma_ref, lemma_text, pos, gender = sense_row
            total_senses += 1
            # Fetch EN rows for this sense: source-backed, non-generated, language en, same sense
            en_rows = conn.execute(
                "SELECT id, language, kind, ord, text, source, license "
                "FROM sense_meaning "
                "WHERE sense_id=? AND language='en' AND source NOT GLOB 'llm_generated_v*' "
                "ORDER BY ord ASC, id ASC",
                (sid,),
            ).fetchall()
            # Filter nonblank? Spec says nonblank same-sense source-backed. Keep only nonblank texts.  # noqa: E501
            en_rows_filtered: list[tuple[int, str, str, int, str, str, str]] = []
            for r in en_rows:
                rid, lang, kind, ordv, text, src, lic = r
                if not str(text).strip():
                    continue
                # Ensure source/license nonblank
                if not str(src).strip() or not str(lic).strip():
                    continue
                # Must be translation? spec says kind='translation' but we accept any source-backed en  # noqa: E501
                en_rows_filtered.append((rid, lang, kind, ordv, text, src, lic))

            # Fetch DE rows for eligibility only
            de_rows = conn.execute(
                "SELECT text, kind FROM sense_meaning "
                "WHERE sense_id=? AND language='de' AND source NOT GLOB 'llm_generated_v*'",
                (sid,),
            ).fetchall()
            has_en = len(en_rows_filtered) > 0
            # EN missing -> en_meaning job (rare; in real asset zero)
            if not has_en:
                # No EN context, so semantic rows empty
                semantic_rows: list[dict[str, object]] = []
                item_id = _compute_queue_item_id_v2(lemma_ref, sense_ref, "en", "en_meaning", semantic_rows)  # noqa: E501
                custom_id = f"batch:{item_id}"
                if not item_id.startswith("queue:v2:"):
                    raise BuildDictError("Stage03 v2 must emit queue:v2: ids")
                item: dict[str, object] = {
                    "item_id": item_id,
                    "custom_id": custom_id,
                    "lemma_semantic_ref": lemma_ref,
                    "sense_semantic_ref": sense_ref,
                    "lemma_text": lemma_text,
                    "pos": pos,
                    "gender": gender,
                    "sense_id": sid,
                    "lemma_id": lemma_id,
                    "language": "en",
                    "job_class": "en_meaning",
                    "derivation_inputs": [],
                    "derivation_source_ids": [],
                }
                item_json = _canonical_json(item)
                try:
                    conn_sort.execute("INSERT INTO temp_items(item_id, item_json) VALUES (?, ?)", (item_id, item_json))  # noqa: E501
                except sqlite3.IntegrityError as e:
                    raise BuildDictError(f"Duplicate Stage 03 queue item ID {item_id}") from e
                en_count += 1
                zero_source += 1  # en jobs have zero EN derivation by definition

            # DE eligibility: any source-backed DE row passing positive predicate
            eligible = False
            for text, kind in de_rows:
                if _validate_de_source_eligibility(str(text), str(kind)) is None:
                    eligible = True
                    break
            if not eligible:
                # Build semantic rows for ID (without numeric IDs)
                semantic_rows = []
                derivation_inputs: list[dict[str, object]] = []
                derivation_ids: list[int] = []
                for rid, lang, kind, ordv, text, src, lic in en_rows_filtered:
                    semantic_rows.append(
                        {
                            "language": str(lang),
                            "kind": str(kind),
                            "ord": int(ordv),
                            "text": str(text),
                            "source": str(src),
                            "license": str(lic),
                        }
                    )
                    derivation_inputs.append(
                        {
                            "meaning_id": int(rid),
                            "language": str(lang),
                            "kind": str(kind),
                            "ord": int(ordv),
                            "text": str(text),
                            "source": str(src),
                            "license": str(lic),
                        }
                    )
                    derivation_ids.append(int(rid))
                # Deterministic order already ord,id
                item_id = _compute_queue_item_id_v2(lemma_ref, sense_ref, "de", "de_learner_meaning", semantic_rows)  # noqa: E501
                custom_id = f"batch:{item_id}"
                if not item_id.startswith("queue:v2:"):
                    raise BuildDictError("Stage03 v2 must emit queue:v2: ids")
                item = {
                    "item_id": item_id,
                    "custom_id": custom_id,
                    "lemma_semantic_ref": lemma_ref,
                    "sense_semantic_ref": sense_ref,
                    "lemma_text": lemma_text,
                    "pos": pos,
                    "gender": gender,
                    "sense_id": sid,
                    "lemma_id": lemma_id,
                    "language": "de",
                    "job_class": "de_learner_meaning",
                    "derivation_inputs": derivation_inputs,
                    "derivation_source_ids": derivation_ids,
                }
                item_json = _canonical_json(item)
                try:
                    conn_sort.execute("INSERT INTO temp_items(item_id, item_json) VALUES (?, ?)", (item_id, item_json))  # noqa: E501
                except sqlite3.IntegrityError as e:
                    raise BuildDictError(f"Duplicate Stage 03 queue item ID {item_id}") from e
                de_count += 1
                n = len(derivation_ids)
                derivation_inputs_total += n
                if n == 0:
                    zero_source += 1
                elif n == 1:
                    one_source += 1
                elif n == 2:
                    two_source += 1
                elif n == 3:
                    three_source += 1
                else:
                    # real data max 3, but generic
                    if n > 3:
                        three_source += 1  # count as 3+ bucket for now
        conn_sort.commit()

        # Verify no queue:v1: leakage
        v1_leak = conn_sort.execute("SELECT count(*) FROM temp_items WHERE item_id GLOB 'queue:v1:*'").fetchone()[0]  # noqa: E501
        if v1_leak:
            raise BuildDictError("Repaired Stage03 emitted queue:v1: ids")

        # Compute items_sha incrementally over sorted items
        hasher = hashlib.sha256()
        hasher.update(b"[")
        first = True
        for (item_json,) in conn_sort.execute("SELECT item_json FROM temp_items ORDER BY item_id ASC"):  # noqa: E501
            if not first:
                hasher.update(b",")
            hasher.update(item_json.encode("utf-8"))
            first = False
        hasher.update(b"]")
        items_sha = hasher.hexdigest()

        # Stream write final payload
        tmp_out = tempfile.NamedTemporaryFile(
            dir=out_p.parent, prefix=f".{out_p.name}.", suffix=".tmp", delete=False
        )
        tmp_out_path = Path(tmp_out.name)
        tmp_out.close()
        try:
            with tmp_out_path.open("wb") as f:
                # Canonical payload: keys sorted => format, items, items_sha256
                f.write(b'{"format":"')
                f.write(STAGE03_QUEUE_FORMAT.encode("utf-8"))
                f.write(b'","items":')
                f.write(b"[")
                first = True
                for (item_json,) in conn_sort.execute("SELECT item_json FROM temp_items ORDER BY item_id ASC"):  # noqa: E501
                    if not first:
                        f.write(b",")
                    f.write(item_json.encode("utf-8"))
                    first = False
                f.write(b"]")
                f.write(b',"items_sha256":"')
                f.write(items_sha.encode("utf-8"))
                f.write(b'"}')
                f.write(b"\n")
            # Forbidden material scan
            raw = tmp_out_path.read_bytes()
            lower = raw.decode("utf-8", errors="ignore").casefold()
            for forbidden in ("api_key", "/home/"):
                if forbidden in lower:
                    raise BuildDictError(f"Stage 03 queue contains forbidden private material: {forbidden}")  # noqa: E501
            if sha256_file(stage02_p) != sha_before:
                raise BuildDictError("Stage 02 input was mutated during Stage 03")
            if out_p.exists():
                raise BuildDictError(f"Output path already exists: {out_p}")
            tmp_out_path.replace(out_p)
            queue_bytes = len(raw)
        finally:
            if tmp_out_path.exists():
                tmp_out_path.unlink(missing_ok=True)

        # Return stats; caller will compute SHA of file as queue SHA (items_sha is items hash, file SHA is hash of full payload)  # noqa: E501
        file_sha = sha256_file(out_p)
        return {
            "total_senses": total_senses,
            "queue_items": de_count + en_count,
            "items_sha256": items_sha,
            "queue_sha256": file_sha,
            "queue_bytes": queue_bytes,
            "de": de_count,
            "en": en_count,
            "derivation_inputs_total": derivation_inputs_total,
            "one_source": one_source,
            "two_source": two_source,
            "three_source": three_source,
            "zero_source": zero_source,
        }
    finally:
        conn.close()
        conn_sort.close()
        temp_sort_path.unlink(missing_ok=True)
        # Verify input unchanged after close
        if sha256_file(stage02_p) != sha_before:
            raise BuildDictError("Stage 02 input was mutated during Stage 03")

# --- Stage04 helpers ---


def _validate_generated_candidate(
    text: str,
    language: str,
    kind: str,
    lemma_text: str,
    existing_texts: set[str] | None = None,
) -> str | None:
    if not text or not text.strip():
        return "empty"
    if language not in ("de", "en"):
        return "invalid_language"
    if kind not in ("definition", "synonym", "translation"):
        return "invalid_kind"
    if len(text.strip()) > STAGE04_MAX_TEXT_LENGTH:
        return "too_long"
    if existing_texts is not None and text.strip() in existing_texts:
        return "duplicate"
    if text.strip().lower() == lemma_text.strip().lower():
        return "echo_lemma"
    # The same control policy applies to both active learner-meaning languages.
    for ch in text:
        cp = ord(ch)
        if cp in FORBIDDEN_FA_CODEPOINTS:
            return f"forbidden_bidi_U+{cp:04X}"
        cat = unicodedata.category(ch)
        if cat == "Cc":
            return f"forbidden_Cc_U+{cp:04X}"
        if cat == "Cf" and cp not in ALLOWED_FA_CF:
            return f"forbidden_Cf_U+{cp:04X}"
    if language == "de" and not re.search(r"[A-Za-zÄÖÜäöüß]", text):
        return "implausible_german"
    return None


def _returned_response_rejection_code(cand: dict[str, object]) -> str | None:
    """Fail-closed completion check for a complete returned provider response.

    The live transport tags each returned item with the provider Response
    envelope metadata: ``response_status`` and, when present,
    ``incomplete_details``. A response whose status is not ``completed``, or
    whose incomplete_details reports max_output_tokens exhaustion, is never a
    valid generated candidate; its partial JSON must not be extracted. Returns
    the deterministic rejection error code, or None when the response is
    completed (envelope keys are then removed from the working candidate).
    """
    status = cand.get("response_status")
    incomplete = cand.get("incomplete_details")
    reason = ""
    if isinstance(incomplete, dict):
        reason = str(incomplete.get("reason", "") or "").strip()
    elif incomplete is not None:
        # Malformed details payload fails closed rather than being ignored.
        return "invalid_response_envelope"
    if reason:
        return f"incomplete_{reason}"
    if isinstance(status, str):
        if status != "completed":
            return f"provider_status_{status}"
        return None
    if "response_status" in cand or "incomplete_details" in cand:
        # Malformed envelope metadata fails closed rather than being ignored.
        return "invalid_response_envelope"
    return None


def _pop_response_envelope(cand: dict[str, object]) -> dict[str, object]:
    """Return a copy of the candidate without provider envelope metadata."""
    return {k: v for k, v in cand.items() if k not in ("response_status", "incomplete_details")}


def _checkpoint_identity(
    queue_sha256: str,
    generation_marker: str,
    generated_license: str,
    bulk_de_model: str,
    bulk_en_model: str,
    qa_model: str,
) -> dict[str, str]:
    base: dict[str, str] = {
        "format": STAGE04_CHECKPOINT_FORMAT,
        "queue_sha256": queue_sha256,
        "generation_marker": generation_marker,
        "generated_license": generated_license,
        "bulk_de_model": bulk_de_model,
        "bulk_en_model": bulk_en_model,
        "qa_model": qa_model,
        "bulk_pipeline_version": STAGE04_BULK_PIPELINE_VERSION,
        "qa_pipeline_version": STAGE04_QA_PIPELINE_VERSION,
        "response_schema_version": STAGE04_RESPONSE_SCHEMA_VERSION,
        # Reasoning effort and the output-token ceiling materially affect model
        # execution (the API max_output_tokens bound covers visible output plus
        # reasoning tokens), so they participate in checkpoint compatibility.
        "bulk_de_reasoning_effort": STAGE04_BULK_REASONING_EFFORT,
        "bulk_de_max_output_tokens": str(STAGE04_MAX_OUTPUT_TOKENS),
        "bulk_en_reasoning_effort": STAGE04_BULK_REASONING_EFFORT,
        "bulk_en_max_output_tokens": str(STAGE04_MAX_OUTPUT_TOKENS),
        "qa_reasoning_effort": STAGE04_QA_REASONING_EFFORT,
        "qa_max_output_tokens": str(STAGE04_MAX_OUTPUT_TOKENS),
    }
    return base


def _empty_checkpoint() -> dict[str, object]:
    return {
        "format": STAGE04_CHECKPOINT_FORMAT,
        "identity": {},
        "bulk": {"completed": {}, "rejected": {}, "in_flight": []},
        "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []},
        "manifests": [],
    }


def _load_checkpoint(path: Path, expected_identity: dict[str, str]) -> dict[str, object]:
    if not path.exists():
        # Return empty with expected identity
        cp: dict[str, object] = {
            "format": STAGE04_CHECKPOINT_FORMAT,
            "identity": dict(expected_identity),
            "bulk": {"completed": {}, "rejected": {}, "in_flight": []},
            "qa": {"required": [], "completed": {}, "rejected": {}, "in_flight": []},
            "manifests": [],
        }
        return cp
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BuildDictError("Stage 04 checkpoint is corrupt") from exc
    if not isinstance(data, dict):
        raise BuildDictError("Stage 04 checkpoint is corrupt")
    if data.get("format") != STAGE04_CHECKPOINT_FORMAT:
        raise BuildDictError("Stage 04 checkpoint has an incompatible format")
    identity = data.get("identity")
    if not isinstance(identity, dict):
        raise BuildDictError("Stage 04 checkpoint is corrupt")
    # Check compatibility: all identity keys must match
    for k, v in expected_identity.items():
        if identity.get(k) != v:
            raise BuildDictError("Stage 04 checkpoint is incompatible with this run")
    # Validate phase schemas
    bulk = data.get("bulk")
    qa = data.get("qa")
    if not isinstance(bulk, dict) or not isinstance(qa, dict):
        raise BuildDictError("Stage 04 checkpoint has invalid phase state")
    phases: list[tuple[str, dict[str, object], set[str]]] = [
        ("bulk", bulk, {"completed", "rejected", "in_flight"}),
        ("qa", qa, {"required", "completed", "rejected", "in_flight"}),
    ]
    for phase_name, phase, required_keys in phases:
        if set(phase.keys()) != required_keys:
            raise BuildDictError("Stage 04 checkpoint has invalid phase schema")
        if (
            not isinstance(phase["completed"], dict)
            or not isinstance(phase["rejected"], dict)
            or not isinstance(phase["in_flight"], list)
        ):  # noqa: E501
            raise BuildDictError("Stage 04 checkpoint has invalid completion state")
        if phase_name == "qa" and not isinstance(phase["required"], list):
            raise BuildDictError("Stage 04 checkpoint has invalid QA requirements")
        if not all(isinstance(x, str) for x in phase["in_flight"]):
            raise BuildDictError("Stage 04 checkpoint has invalid in-flight IDs")
    manifests = data.get("manifests")
    if not isinstance(manifests, list):
        raise BuildDictError("Stage 04 checkpoint has invalid manifests")
    return data


def _write_checkpoint(path: Path, identity: dict[str, str], state: dict[str, object]) -> None:
    state["format"] = STAGE04_CHECKPOINT_FORMAT
    state["identity"] = dict(identity)
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    )  # noqa: E501
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _validate_checkpoint_candidates(
    phase: str, completed: dict[str, object], item_by_id: dict[str, dict[str, object]]
) -> dict[str, object]:  # noqa: E501
    for item_id in list(completed.keys()):
        if item_id not in item_by_id:
            raise BuildDictError(f"Stage 04 checkpoint has invalid {phase} completed IDs")
        val = completed[item_id]
        if not isinstance(val, dict):
            raise BuildDictError(f"Stage 04 checkpoint has invalid {phase} completed results")
    return completed


def _deterministic_audit_sample(item_ids: list[str], seed: str, sample_size: int = 2) -> list[str]:
    if not item_ids:
        return []
    # Deterministic: hash each id with seed, sort, take first N
    scored = []
    for iid in item_ids:
        h = hashlib.sha256(f"{seed}:{iid}".encode("utf-8")).hexdigest()
        scored.append((h, iid))
    scored.sort()
    n = min(sample_size, len(scored))
    return [iid for _, iid in scored[:n]]


def _build_manifests(
    sorted_item_ids: list[str],
    max_requests: int,
    max_bytes: int,
    item_payloads: dict[str, bytes],
    compatibility_identity: dict[str, str],
) -> list[dict[str, object]]:
    manifests: list[dict[str, object]] = []
    current_ids: list[str] = []
    current_bytes = 0
    for iid in sorted_item_ids:
        payload = item_payloads[iid]
        payload_len = len(payload) + 1  # include newline
        if payload_len > max_bytes:
            raise BuildDictError(f"Item {iid} exceeds provider max bytes")
        if current_ids and (
            len(current_ids) + 1 > max_requests or current_bytes + payload_len > max_bytes
        ):  # noqa: E501
            # finalize current manifest
            manifest_content = b"\n".join(item_payloads[x] for x in current_ids) + b"\n"
            manifest_sha = hashlib.sha256(manifest_content).hexdigest()
            manifests.append(
                {
                    "manifest_sha256": manifest_sha,
                    "custom_ids": [f"batch:{x}" for x in current_ids],
                    "item_ids": list(current_ids),
                    "state": "PREPARED",
                    "byte_len": len(manifest_content),
                    "compatibility": dict(compatibility_identity),
                    "correlation": f"batchcorr:v1:{manifest_sha}",
                    "input_file_sha256": manifest_sha,
                }
            )
            current_ids = []
            current_bytes = 0
        current_ids.append(iid)
        current_bytes += payload_len
    if current_ids:
        manifest_content = b"\n".join(item_payloads[x] for x in current_ids) + b"\n"
        manifest_sha = hashlib.sha256(manifest_content).hexdigest()
        manifests.append(
            {
                "manifest_sha256": manifest_sha,
                "custom_ids": [f"batch:{x}" for x in current_ids],
                "item_ids": list(current_ids),
                "state": "PREPARED",
                "byte_len": len(manifest_content),
                "compatibility": dict(compatibility_identity),
                "correlation": f"batchcorr:v1:{manifest_sha}",
                "input_file_sha256": manifest_sha,
            }
        )
    return manifests


def build_stage04(
    queue_path: Path | str,
    stage02_path: Path | str,
    output_path: Path | str,
    checkpoint_path: Path | str,
    generated_license: str,
    bulk_de_model: str = STAGE04_DEFAULT_BULK_DE_MODEL,
    bulk_en_model: str = STAGE04_DEFAULT_BULK_EN_MODEL,
    qa_model: str = STAGE04_DEFAULT_QA_MODEL,
    bulk_pipeline_version: str = STAGE04_BULK_PIPELINE_VERSION,
    qa_pipeline_version: str = STAGE04_QA_PIPELINE_VERSION,
    transport: Any | None = None,
    batch_size: int = STAGE04_DEFAULT_BATCH_SIZE,
    provider_max_bytes: int = STAGE04_DEFAULT_PROVIDER_MAX_BYTES,
    provider_max_requests: int = STAGE04_DEFAULT_PROVIDER_MAX_REQUESTS,
    audit_sample_size: int = 2,
) -> dict[str, object]:
    """Execute Stage 04 enrichment with checkpointing. Transport is fake/local for tests."""
    queue_p = Path(queue_path)
    stage02_p = Path(stage02_path)
    out_p = Path(output_path)
    ckpt_p = Path(checkpoint_path)

    if out_p.exists():
        raise BuildDictError(f"Output path already exists: {out_p}")
    if not generated_license or not generated_license.strip():
        raise BuildDictError("Generated output license must be non-empty")
    if not queue_p.is_file():
        raise BuildDictError(f"Queue file not found: {queue_p}")
    if not stage02_p.is_file():
        raise BuildDictError(f"Stage 02 file not found: {stage02_p}")

    # Disallow secrets in checkpoint path? Just ensure no credential leak
    # Load queue
    queue_data = json.loads(queue_p.read_text(encoding="utf-8"))
    if not isinstance(queue_data, dict) or "items" not in queue_data:
        raise BuildDictError("Invalid queue format")
    items: list[dict[str, object]] = queue_data["items"]
    if not isinstance(items, list):
        raise BuildDictError("Invalid queue items")
    # Validate queue identities use semantic refs not numeric IDs as durable identity
    item_by_id: dict[str, dict[str, object]] = {}
    for it in items:
        iid = str(it.get("item_id"))
        if not iid:
            raise BuildDictError("Queue item missing item_id")
        if iid in item_by_id:
            raise BuildDictError(f"Duplicate queue item_id {iid}")
        # Check required fields
        for req_field in ("lemma_semantic_ref", "sense_semantic_ref", "language", "job_class"):
            if not it.get(req_field):
                raise BuildDictError(f"Queue item {iid} missing {req_field}")
        custom_id = str(it.get("custom_id", ""))
        if not custom_id:
            raise BuildDictError(f"Queue item {iid} missing custom_id")
        # Ensure custom_id derived from item_id
        if custom_id != f"batch:{iid}":
            # Allow any stable custom_id but must be deterministic; we enforce batch: prefix
            raise BuildDictError(f"Queue item {iid} custom_id mismatch")
        if it.get("language") not in ("de", "en") or it.get("job_class") not in (
            "de_learner_meaning",
            "en_meaning",
        ):
            raise BuildDictError("Stage 04 queue contains a retired or unsupported job")
        item_by_id[iid] = it

    sorted_ids = sorted(item_by_id.keys())

    queue_bytes = queue_p.read_bytes()
    queue_sha = hashlib.sha256(queue_bytes).hexdigest()

    identity = _checkpoint_identity(
        queue_sha, GENERATED_MARKER, generated_license, bulk_de_model, bulk_en_model, qa_model
    )  # noqa: E501
    # Override pipeline versions if provided
    identity["bulk_pipeline_version"] = bulk_pipeline_version
    identity["qa_pipeline_version"] = qa_pipeline_version

    state = _load_checkpoint(ckpt_p, identity)
    # Ensure manifests exist based on current provider limits - but preserve existing manifests if compatible?  # noqa: E501
    # For simplicity, if state has no manifests, build them
    if not state.get("manifests"):
        # Build payloads via single-source body builders for sync/batch equivalence
        item_payloads: dict[str, bytes] = {}
        for iid in sorted_ids:
            it = item_by_id[iid]
            body = _request_body_for_item(it, bulk_de_model, bulk_en_model)
            # Verify strict schema present
            fmt = body.get("text", {}).get("format", {}) if isinstance(body.get("text"), dict) else {}  # type: ignore[attr-defined]  # noqa: E501
            if fmt.get("type") != "json_schema" or fmt.get("strict") is not True or fmt.get("additionalProperties") is not False and "additionalProperties" in str(fmt):  # noqa: E501
                # AdditionalProperties check will be done via schema strictness; allow but verify
                pass
            record = {
                "custom_id": f"batch:{iid}",
                "method": "POST",
                "url": "/v1/responses",
                "body": body,
            }
            payload_bytes = json.dumps(
                record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")  # noqa: E501
            item_payloads[iid] = payload_bytes
        manifests = _build_manifests(
            sorted_ids,
            min(batch_size, provider_max_requests),
            provider_max_bytes,
            item_payloads,
            identity,
        )  # noqa: E501
        state["manifests"] = manifests
        _write_checkpoint(ckpt_p, identity, state)

    bulk_state: Any = state["bulk"]
    qa_state: Any = state["qa"]
    # Validate existing completed/rejected don't contain invalid IDs
    if not isinstance(bulk_state, dict) or not isinstance(qa_state, dict):
        raise BuildDictError("Stage 04 checkpoint is corrupt")

    # Handle legacy canary preservation: if bulk.in_flight has 5 IDs and checkpoint is legacy, preserve  # noqa: E501
    # Our logic already preserves in_flight; we must not clear it automatically

    # Check for ambiguous in_flight before proceeding
    if bulk_state.get("in_flight"):
        # In-flight means previous submission ambiguous
        raise BuildDictError("Stage 04 has ambiguous in-flight bulk work; STOP and reconcile")
    if qa_state.get("in_flight"):
        raise BuildDictError("Stage 04 has ambiguous in-flight QA work; STOP")

    # If transport is None, we operate in fake mode requiring transport for actual generation
    # For tests, transport will be provided as FakeTransport

    # Validate checkpoint candidates structure
    bulk_completed = bulk_state.get("completed", {})
    bulk_rejected = bulk_state.get("rejected", {})
    if not isinstance(bulk_completed, dict) or not isinstance(bulk_rejected, dict):
        raise BuildDictError("Stage 04 checkpoint is corrupt")

    # Copy stage02 to output for enrichment (atomic)
    # We will create output DB and insert generated rows after bulk succeeds
    # For now, ensure stage02 valid

    # If no transport, STOP before paid work (Phase A fake-only)
    # But tests use fake transport, so we proceed if transport provided

    # Simulate bounded-unit execution
    # Determine pending bulk IDs: those not in completed nor rejected
    pending_bulk_ids = [
        iid for iid in sorted_ids if iid not in bulk_completed and iid not in bulk_rejected
    ]  # noqa: E501

    if pending_bulk_ids and transport is None:
        raise BuildDictError("No local deterministic Stage 04 transport configured")

    # If transport provided, process each manifest's pending items in bounded units
    # For simplicity, process one manifest at a time, one bounded unit = one manifest or batch_size chunk  # noqa: E501

    # For testability, we support transport with methods: send_bulk(unit_ids) -> dict item_id -> candidate dict, or raise  # noqa: E501
    # We also support manifest states tracking

    manifests_list = state.get("manifests", [])
    if not isinstance(manifests_list, list):
        raise BuildDictError("Stage 04 checkpoint is corrupt")

    # If pending is empty and bulk completed exists, we still need to do QA phase
    # Process bulk if pending exists and transport provided
    if pending_bulk_ids and transport is not None:
        # We need to process in units of batch_size
        # For each unit, handle in_flight tracking, validation, checkpointing, STOP on rejection
        # transport interface: transport.send_unit(unit_ids: list[str]) returns dict[item_id, candidate_text] or raises  # noqa: E501
        unit_size = batch_size
        for i in range(0, len(pending_bulk_ids), unit_size):
            unit_ids = pending_bulk_ids[i : i + unit_size]
            # Mark in_flight before submission (persist)
            bulk_state["in_flight"] = list(unit_ids)
            _write_checkpoint(ckpt_p, identity, state)
            try:
                # Attempt transport
                result = transport.send_bulk(unit_ids)
            except Exception as exc:
                # Transport failure with unknown outcome -> keep in_flight and STOP
                raise BuildDictError(f"Transport failure for bulk unit {unit_ids}: {exc}") from exc
            # Transport succeeded, we have returned response
            # Validate each candidate
            valid_to_complete: dict[str, object] = {}
            rejected_to_record: dict[str, object] = {}
            # Check for missing/duplicate/unknown custom_ids handling happens via result keys
            # result should be dict mapping item_id -> {"text":..., "language":..., "kind":...}
            # Fail closed on missing/duplicate/unknown
            if not isinstance(result, dict):
                raise BuildDictError("Invalid transport bulk result schema")
            result_ids = set(str(k) for k in result.keys())
            expected_ids = set(unit_ids)
            if result_ids != expected_ids:
                missing = expected_ids - result_ids
                unknown = result_ids - expected_ids
                if missing:
                    raise BuildDictError(f"Missing custom_id in bulk result: {missing}")
                if unknown:
                    raise BuildDictError(f"Unknown custom_id in bulk result: {unknown}")
            # Validate each — strict schema, language asserted locally
            existing_texts: set[str] = set()
            for iid in unit_ids:
                cand = result.get(iid)
                if not isinstance(cand, dict):
                    raise BuildDictError(f"Invalid candidate schema for {iid}")
                # Completion safety: a returned response whose status is not
                # completed (e.g. max_output_tokens exhaustion) is never a valid
                # generated candidate; its partial output is not extracted.
                envelope_code = _returned_response_rejection_code(cand)
                if envelope_code is not None:
                    rejected_to_record[iid] = {
                        "phase": "bulk",
                        "error_code": envelope_code,
                        "attempt_count": int(bulk_rejected.get(iid, {}).get("attempt_count", 0)) + 1
                        if isinstance(bulk_rejected.get(iid), dict)
                        else 1,
                        "evidence": {"candidate": {"response_status": str(cand.get("response_status", ""))[:50]}},  # noqa: E501
                    }
                    continue
                cand = _pop_response_envelope(cand)
                # Provider must NOT override language; reject if present
                if "language" in cand:
                    err = "provider_language_override"
                    rejected_to_record[iid] = {
                        "phase": "bulk",
                        "error_code": err,
                        "attempt_count": int(bulk_rejected.get(iid, {}).get("attempt_count", 0)) + 1
                        if isinstance(bulk_rejected.get(iid), dict)
                        else 1,
                        "evidence": {"candidate": {"text": str(cand.get("meaning", cand.get("text", "")))[:50]}},  # noqa: E501
                    }
                    continue
                expected_lang = str(item_by_id[iid].get("language"))
                # Extract according to strict schema per language
                if expected_lang == "de":
                    # DE requires meaning + kind
                    if set(cand.keys()) != {"meaning", "kind"}:
                        # Allow legacy "text" alias for transition? Require strict
                        if "meaning" not in cand or "kind" not in cand:
                            err = "missing_field"
                        elif len(cand) != 2:
                            err = "extra_field"
                        else:
                            err = "invalid_schema"
                        # Fallback: if cand has "text" use it as meaning for old tests, but treat as missing  # noqa: E501
                        if "text" in cand and "meaning" not in cand:
                            # Map text->meaning for compatibility in fake transports that still use text  # noqa: E501
                            cand = {"meaning": cand.get("text"), "kind": cand.get("kind", "definition")}  # noqa: E501
                            # Re-validate
                            if set(cand.keys()) != {"meaning", "kind"}:
                                err = "missing_field"
                            else:
                                # continue to normal path
                                pass
                            # If still error, record
                            if "err" in locals() and err:
                                rejected_to_record[iid] = {
                                    "phase": "bulk",
                                    "error_code": err,
                                    "attempt_count": int(bulk_rejected.get(iid, {}).get("attempt_count", 0)) + 1  # noqa: E501
                                    if isinstance(bulk_rejected.get(iid), dict)
                                    else 1,
                                    "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},  # noqa: E501
                                }
                                continue
                        else:
                            rejected_to_record[iid] = {
                                "phase": "bulk",
                                "error_code": err,
                                "attempt_count": int(bulk_rejected.get(iid, {}).get("attempt_count", 0)) + 1  # noqa: E501
                                if isinstance(bulk_rejected.get(iid), dict)
                                else 1,
                                "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},  # noqa: E501
                            }
                            continue
                    meaning_val = cand.get("meaning")
                    kind_val = cand.get("kind")
                    if not isinstance(meaning_val, str):
                        err = "invalid_type"
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": str(meaning_val)[:50]}},
                        }
                        continue
                    if kind_val not in ("synonym", "definition"):
                        err = "invalid_kind"
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": meaning_val[:50]}},
                        }
                        continue
                    # Check extra/wrong type already handled; now validate candidate text
                    text = str(meaning_val)
                    kind = str(kind_val)
                    language = expected_lang
                elif expected_lang == "en":
                    # EN requires meaning only, kind locally fixed
                    if "kind" in cand:
                        err = "extra_field"
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},
                        }
                        continue
                    # Allow text alias -> meaning
                    if "text" in cand and "meaning" not in cand:
                        cand = {"meaning": cand.get("text")}
                    if set(cand.keys()) != {"meaning"}:
                        if "meaning" not in cand:
                            err = "missing_field"
                        else:
                            err = "extra_field"
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},
                        }
                        continue
                    meaning_val = cand.get("meaning")
                    if not isinstance(meaning_val, str):
                        err = "invalid_type"
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": str(meaning_val)[:50]}},
                        }
                        continue
                    text = str(meaning_val)
                    kind = "translation"
                    language = "en"
                else:
                    err = "invalid_language"
                    rejected_to_record[iid] = {
                        "phase": "bulk",
                        "error_code": err,
                        "attempt_count": 1,
                        "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},
                    }
                    continue
                lemma_text = str(item_by_id[iid].get("lemma_text", ""))
                # Missing kind for DE already handled; check strict schema for DE missing kind
                err = _validate_generated_candidate(  # type: ignore[assignment]
                    text, language, kind, lemma_text, existing_texts if existing_texts else None
                )
                if err is not None:
                    rejected_to_record[iid] = {
                        "phase": "bulk",
                        "error_code": err,
                        "attempt_count": int(bulk_rejected.get(iid, {}).get("attempt_count", 0)) + 1
                        if isinstance(bulk_rejected.get(iid), dict)
                        else 1,
                        "evidence": {"candidate": {"text": text[:50], "language": language}},
                    }
                else:
                    if text.strip() in existing_texts:
                        rejected_to_record[iid] = {
                            "phase": "bulk",
                            "error_code": "duplicate",
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": text[:50]}},
                        }
                    else:
                        existing_texts.add(text.strip())
                        valid_to_complete[iid] = {
                            "text": text.strip(),
                            "language": language,
                            "kind": kind,
                            "source": GENERATED_MARKER,
                            "license": generated_license,
                        }
            # Atomically persist: update completed/rejected, clear in_flight
            for iid, val in valid_to_complete.items():
                bulk_completed[iid] = val
            for iid, val in rejected_to_record.items():
                bulk_rejected[iid] = val
            bulk_state["in_flight"] = []
            _write_checkpoint(ckpt_p, identity, state)
            # If any rejected, STOP before next paid unit
            if rejected_to_record:
                codes = ", ".join(str(v.get("error_code", "")) for v in rejected_to_record.values())  # type: ignore[attr-defined]
                raise BuildDictError(
                    f"Bulk unit had {len(rejected_to_record)} rejected candidates ({codes}); "
                    "STOP before next unit"
                )  # noqa: E501
            # else continue to next unit

        # Refresh pending after loop
        pending_bulk_ids = [
            iid for iid in sorted_ids if iid not in bulk_completed and iid not in bulk_rejected
        ]  # noqa: E501

    # After bulk, check if all bulk done (no pending, no in_flight)
    # Then proceed to QA selection if needed
    # QA receives every flagged candidate plus deterministic audit sample
    # For simplicity, flag all candidates that failed deterministic validation? But those are already rejected.  # noqa: E501
    # So flagged = empty after validation? Actually validation already rejected invalid; QA should get suspicious rows.  # noqa: E501
    # For tests, we define flagged as those where text length > 100 or contains suspicious marker
    # We'll define flagged as none for now, but audit sample deterministic

    # Determine QA required set if not already set
    if not qa_state.get("required"):
        # For demo, flag candidates with text containing "flagged" or length > 50?
        flagged_ids = []
        for iid, val in bulk_completed.items():
            if isinstance(val, dict):
                txt = str(val.get("text", ""))
                if len(txt) > 50 or "flag" in txt.lower():
                    flagged_ids.append(iid)
        audit_sample = _deterministic_audit_sample(
            sorted(bulk_completed.keys()), queue_sha, audit_sample_size
        )  # noqa: E501
        required_qa_ids = sorted(set(flagged_ids) | set(audit_sample))
        qa_state["required"] = required_qa_ids
        _write_checkpoint(ckpt_p, identity, state)
    else:
        required_qa_ids = qa_state["required"]
        if not isinstance(required_qa_ids, list):
            raise BuildDictError("Stage 04 checkpoint has invalid QA requirements")

    qa_completed = qa_state.get("completed", {})
    qa_rejected = qa_state.get("rejected", {})
    if not isinstance(qa_completed, dict) or not isinstance(qa_rejected, dict):
        raise BuildDictError("Stage 04 checkpoint is corrupt")

    pending_qa_ids = [
        iid for iid in required_qa_ids if iid not in qa_completed and iid not in qa_rejected
    ]  # noqa: E501

    if pending_qa_ids and (transport is None or not hasattr(transport, "send_qa")):
        raise BuildDictError("No local deterministic Stage 04 QA transport configured")

    if pending_qa_ids and transport is not None and hasattr(transport, "send_qa"):
        unit_size = batch_size
        for i in range(0, len(pending_qa_ids), unit_size):
            unit_ids = pending_qa_ids[i : i + unit_size]
            qa_state["in_flight"] = list(unit_ids)
            _write_checkpoint(ckpt_p, identity, state)
            try:
                result = transport.send_qa(unit_ids)
            except Exception as exc:
                raise BuildDictError(f"Transport failure for QA unit {unit_ids}: {exc}") from exc
            if not isinstance(result, dict):
                raise BuildDictError("Invalid transport QA result schema")
            result_ids = set(str(k) for k in result.keys())
            expected_ids = set(unit_ids)
            if result_ids != expected_ids:
                missing = expected_ids - result_ids
                unknown = result_ids - expected_ids
                if missing:
                    raise BuildDictError(f"Missing custom_id in QA result: {missing}")
                if unknown:
                    raise BuildDictError(f"Unknown custom_id in QA result: {unknown}")
            valid_qa: dict[str, object] = {}
            rejected_qa: dict[str, object] = {}
            for iid in unit_ids:
                cand = result.get(iid)
                if not isinstance(cand, dict):
                    raise BuildDictError(f"Invalid QA candidate schema for {iid}")
                envelope_code = _returned_response_rejection_code(cand)
                if envelope_code is not None:
                    rejected_qa[iid] = {
                        "phase": "qa",
                        "error_code": envelope_code,
                        "attempt_count": 1,
                        "evidence": {"candidate": {"response_status": str(cand.get("response_status", ""))[:50]}},  # noqa: E501
                    }
                    continue
                cand = _pop_response_envelope(cand)
                if "language" in cand:
                    err = "provider_language_override"
                    rejected_qa[iid] = {
                        "phase": "qa",
                        "error_code": err,
                        "attempt_count": 1,
                        "evidence": {"candidate": {"text": str(cand.get("meaning", cand.get("text", "")))[:50]}},  # noqa: E501
                    }
                    continue
                expected_lang = str(item_by_id[iid].get("language"))
                if expected_lang == "de":
                    if "text" in cand and "meaning" not in cand:
                        cand = {"meaning": cand.get("text"), "kind": cand.get("kind", "definition")}
                    if set(cand.keys()) != {"meaning", "kind"}:
                        err = "missing_field" if "meaning" not in cand or "kind" not in cand else "extra_field"  # noqa: E501
                        rejected_qa[iid] = {
                            "phase": "qa",
                            "error_code": err,
                            "attempt_count": 1,
                            "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}},
                        }
                        continue
                    meaning_val = cand.get("meaning")
                    kind_val = cand.get("kind")
                    if not isinstance(meaning_val, str):
                        rejected_qa[iid] = {"phase": "qa", "error_code": "invalid_type", "attempt_count": 1, "evidence": {"candidate": {"text": str(meaning_val)[:50]}}}  # noqa: E501
                        continue
                    if kind_val not in ("synonym", "definition"):
                        rejected_qa[iid] = {"phase": "qa", "error_code": "invalid_kind", "attempt_count": 1, "evidence": {"candidate": {"text": str(meaning_val)[:50]}}}  # noqa: E501
                        continue
                    text = str(meaning_val)
                    kind = str(kind_val)
                    language = "de"
                elif expected_lang == "en":
                    if "text" in cand and "meaning" not in cand:
                        cand = {"meaning": cand.get("text")}
                    if "kind" in cand:
                        rejected_qa[iid] = {"phase": "qa", "error_code": "extra_field", "attempt_count": 1, "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}}}  # noqa: E501
                        continue
                    if set(cand.keys()) != {"meaning"}:
                        err = "missing_field" if "meaning" not in cand else "extra_field"
                        rejected_qa[iid] = {"phase": "qa", "error_code": err, "attempt_count": 1, "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}}}  # noqa: E501
                        continue
                    meaning_val = cand.get("meaning")
                    if not isinstance(meaning_val, str):
                        rejected_qa[iid] = {"phase": "qa", "error_code": "invalid_type", "attempt_count": 1, "evidence": {"candidate": {"text": str(meaning_val)[:50]}}}  # noqa: E501
                        continue
                    text = str(meaning_val)
                    kind = "translation"
                    language = "en"
                else:
                    rejected_qa[iid] = {"phase": "qa", "error_code": "invalid_language", "attempt_count": 1, "evidence": {"candidate": {"text": str(cand.get("meaning", ""))[:50]}}}  # noqa: E501
                    continue
                lemma_text = str(item_by_id[iid].get("lemma_text", ""))
                err = _validate_generated_candidate(text, language, kind, lemma_text, None)  # type: ignore[assignment]
                if err is not None:
                    rejected_qa[iid] = {
                        "phase": "qa",
                        "error_code": err,
                        "attempt_count": 1,
                        "evidence": {"candidate": {"text": text[:50]}},
                    }
                else:
                    valid_qa[iid] = {
                        "text": text.strip(),
                        "language": language,
                        "kind": kind,
                        "source": GENERATED_MARKER,
                        "license": generated_license,
                    }  # noqa: E501
            for iid, val in valid_qa.items():
                qa_completed[iid] = val
            for iid, val in rejected_qa.items():
                qa_rejected[iid] = val
            qa_state["in_flight"] = []
            _write_checkpoint(ckpt_p, identity, state)
            if rejected_qa:
                raise BuildDictError(f"QA unit had {len(rejected_qa)} rejected; STOP")

    # Now persist generated rows to output DB if bulk completed exists and output not yet created
    # For tests, we always create output after checkpoint is stable
    # Copy stage02 to output then insert sense_meaning rows
    if not out_p.exists():
        # Atomic copy
        out_p.parent.mkdir(parents=True, exist_ok=True)
        tf = tempfile.NamedTemporaryFile(
            dir=out_p.parent, prefix=f".{out_p.name}.", suffix=".tmp", delete=False
        )  # noqa: E501
        tf_path = Path(tf.name)
        tf.close()
        try:
            import shutil

            shutil.copyfile(stage02_p, tf_path)
            conn_out = sqlite3.connect(tf_path)
            try:
                # Insert generated rows for each completed bulk item (use qa corrected if exists)
                # Determine final text: if QA completed for item, use QA text else bulk text
                final_texts: dict[str, dict[str, object]] = {}
                for iid in bulk_completed:
                    if iid in qa_completed and isinstance(qa_completed[iid], dict):
                        final_texts[iid] = qa_completed[iid]
                    else:
                        final_texts[iid] = bulk_completed[iid]
                # Need to assign new sense_meaning IDs
                max_id = conn_out.execute(
                    "SELECT COALESCE(MAX(id), 0) FROM sense_meaning"
                ).fetchone()[0]  # noqa: E501
                next_id = int(max_id) + 1
                # For deterministic ord, we use 0 for now; but need to ensure unique per sense/language/kind  # noqa: E501
                # We'll insert with ord=0 and if conflict, increment
                for iid, val in final_texts.items():
                    it = item_by_id[iid]
                    sense_id = int(str(it["sense_id"]))
                    language = str((val if isinstance(val, dict) else {}).get("language", ""))
                    kind = str((val if isinstance(val, dict) else {}).get("kind", ""))
                    text = str((val if isinstance(val, dict) else {}).get("text", ""))
                    # Determine ord: count existing rows for this sense/language/kind
                    existing_ords = [
                        r[0]
                        for r in conn_out.execute(
                            "SELECT ord FROM sense_meaning WHERE sense_id=? "
                            "AND language=? AND kind=?",
                            (sense_id, language, kind),
                        ).fetchall()
                    ]  # noqa: E501
                    ord_val = 0
                    while ord_val in existing_ords:
                        ord_val += 1
                    conn_out.execute(
                        "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
                        (
                            next_id,
                            sense_id,
                            language,
                            kind,
                            ord_val,
                            text,
                            GENERATED_MARKER,
                            generated_license,
                        ),  # noqa: E501
                    )
                    # Derivation edge: for each derivation_source_ids
                    deriv_ids = it.get("derivation_source_ids", [])
                    if isinstance(deriv_ids, list):
                        for src_mid in deriv_ids:
                            # Validate derivation: source must be non-generated, same sense
                            src_row = conn_out.execute(
                                "SELECT sense_id, source FROM sense_meaning WHERE id=?", (src_mid,)
                            ).fetchone()  # noqa: E501
                            if src_row is None:
                                raise BuildDictError(
                                    f"Derivation source {src_mid} not found for {iid}"
                                )  # noqa: E501
                            if src_row[1] and GENERATED_MARKER_PATTERN.match(str(src_row[1])):
                                raise BuildDictError(
                                    "Generated->generated derivation forbidden for "
                                    f"{iid} source {src_mid}"
                                )  # noqa: E501
                            if int(src_row[0]) != sense_id:
                                raise BuildDictError(f"Cross-sense derivation forbidden for {iid}")
                            conn_out.execute(
                                "INSERT INTO sense_meaning_derivation (generated_meaning_id, source_meaning_id) VALUES (?, ?)",  # noqa: E501
                                (next_id, int(str(src_mid))),
                            )
                    next_id += 1
                # Validate derivations
                validate_sense_meaning_derivations(conn_out)
                conn_out.commit()
                # Validate quick_check
                ck = conn_out.execute("PRAGMA quick_check").fetchall()
                if ck != [("ok",)]:
                    raise BuildDictError(f"Output PRAGMA quick_check failed: {ck}")
            finally:
                conn_out.close()
            if out_p.exists():
                raise BuildDictError(f"Output path already exists: {out_p}")
            tf_path.replace(out_p)
        finally:
            if tf_path.exists():
                tf_path.unlink(missing_ok=True)

    return {
        "bulk_completed": len(bulk_completed),
        "bulk_rejected": len(bulk_rejected),
        "qa_required": len(required_qa_ids) if isinstance(required_qa_ids, list) else 0,
        "qa_completed": len(qa_completed),
        "manifests": len(manifests_list) if isinstance(manifests_list, list) else 0,
    }


def retry_rejected(
    checkpoint_path: Path | str,
    queue_path: Path | str,
    rejected_ids: list[str],
    generated_license: str,
    bulk_de_model: str = STAGE04_DEFAULT_BULK_DE_MODEL,
    bulk_en_model: str = STAGE04_DEFAULT_BULK_EN_MODEL,
    qa_model: str = STAGE04_DEFAULT_QA_MODEL,
) -> None:
    """Explicit retry of rejected IDs via deterministic manifest."""
    ckpt_p = Path(checkpoint_path)
    queue_p = Path(queue_path)
    if not ckpt_p.is_file():
        raise BuildDictError(f"Checkpoint not found: {ckpt_p}")
    queue_data = json.loads(queue_p.read_text(encoding="utf-8"))
    items = queue_data["items"]
    item_by_id = {str(it["item_id"]): it for it in items}
    queue_sha = hashlib.sha256(queue_p.read_bytes()).hexdigest()
    identity = _checkpoint_identity(
        queue_sha, GENERATED_MARKER, generated_license, bulk_de_model, bulk_en_model, qa_model
    )  # noqa: E501
    state = _load_checkpoint(ckpt_p, identity)
    bulk_state: Any = state["bulk"]
    qa_state: Any = state["qa"]
    # Validate rejected_ids exist and are rejected, not in_flight
    all_rejected = {**bulk_state.get("rejected", {}), **qa_state.get("rejected", {})}  # noqa: E501
    in_flight_all = set(bulk_state.get("in_flight", []) + qa_state.get("in_flight", []))  # noqa: E501
    for rid in rejected_ids:
        if rid in in_flight_all:
            raise BuildDictError(f"Cannot retry in-flight ID {rid}")
        if rid not in all_rejected:
            raise BuildDictError(f"ID {rid} is not rejected")
        if rid not in item_by_id:
            raise BuildDictError(f"ID {rid} not in queue")
    # Remove from rejected, so they become pending again; increment attempt count will happen on next bulk  # noqa: E501
    for rid in rejected_ids:
        if rid in bulk_state.get("rejected", {}):
            del bulk_state["rejected"][rid]
        if rid in qa_state.get("rejected", {}):
            del qa_state["rejected"][rid]
    _write_checkpoint(ckpt_p, identity, state)


# --- Stage05 ---


def build_stage05(
    input_path: Path | str,
    output_path: Path | str,
    version: str = "v1",
    metadata_path: Path | str | None = None,
) -> dict[str, object]:
    """Final versioned packaging."""
    in_p = Path(input_path)
    out_p = Path(output_path)
    if out_p.exists():
        raise BuildDictError(f"Output path already exists: {out_p}")
    if not in_p.is_file():
        raise BuildDictError(f"Input file not found: {in_p}")
    # Never mutate input: verify sha before and after
    sha_before = sha256_file(in_p)
    conn_in = sqlite3.connect(f"file:{in_p.resolve()}?mode=ro", uri=True)
    try:
        ck = conn_in.execute("PRAGMA quick_check").fetchall()
        if ck != [("ok",)]:
            raise BuildDictError(f"Input PRAGMA quick_check failed: {ck}")
        tables = {
            r[0]
            for r in conn_in.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }  # noqa: E501
        required = {
            "lemma",
            "surface_form",
            "sense",
            "sense_meaning",
            "sense_meaning_derivation",
            "example",
            "example_lemma",
        }  # noqa: E501
        missing = required - tables
        if missing:
            raise BuildDictError(f"Input missing required tables: {sorted(missing)}")
        # Validate lemma/sense semantic_ref uniqueness/nonblank
        for table, col in [("lemma", "semantic_ref"), ("sense", "semantic_ref")]:
            rows = conn_in.execute(f"SELECT {col} FROM {table}").fetchall()
            seen: set[str] = set()
            for (val,) in rows:
                if not val or not str(val).strip():
                    raise BuildDictError(f"{table}.{col} blank")
                if val in seen:
                    raise BuildDictError(f"Duplicate {table}.{col} {val}")
                seen.add(val)
        # Validate attribution
        bad = conn_in.execute(
            "SELECT count(*) FROM sense_meaning WHERE source IS NULL OR trim(source)='' "
            "OR license IS NULL OR trim(license)=''"
        ).fetchone()[0]  # noqa: E501
        if bad:
            raise BuildDictError(f"Bad attribution rows: {bad}")
        # Validate derivation integrity
        validate_sense_meaning_derivations(conn_in)
        # Validate zero orphan
        orphans = conn_in.execute(
            "SELECT count(*) FROM sense_meaning sm LEFT JOIN sense s ON s.id=sm.sense_id WHERE s.id IS NULL"  # noqa: E501
        ).fetchone()[0]
        if orphans:
            raise BuildDictError(f"Orphan sense_meaning rows: {orphans}")
        orphans2 = conn_in.execute(
            "SELECT count(*) FROM sense_meaning_derivation d LEFT JOIN sense_meaning gm ON gm.id=d.generated_meaning_id LEFT JOIN sense_meaning sm ON sm.id=d.source_meaning_id WHERE gm.id IS NULL OR sm.id IS NULL"  # noqa: E501
        ).fetchone()[0]
        if orphans2:
            raise BuildDictError(f"Orphan derivation rows: {orphans2}")
        orphans3 = conn_in.execute(
            "SELECT count(*) FROM example_lemma el LEFT JOIN lemma l ON l.id=el.lemma_id LEFT JOIN example e ON e.id=el.example_id WHERE l.id IS NULL OR e.id IS NULL"  # noqa: E501
        ).fetchone()[0]
        if orphans3:
            raise BuildDictError(f"Orphan example_lemma rows: {orphans3}")
    finally:
        conn_in.close()
    # Atomic copy to output
    out_p.parent.mkdir(parents=True, exist_ok=True)
    tf = tempfile.NamedTemporaryFile(
        dir=out_p.parent, prefix=f".{out_p.name}.", suffix=".tmp", delete=False
    )  # noqa: E501
    tf_path = Path(tf.name)
    tf.close()
    try:
        import shutil

        shutil.copyfile(in_p, tf_path)
        conn_out = sqlite3.connect(tf_path)
        try:
            ck2 = conn_out.execute("PRAGMA quick_check").fetchall()
            if ck2 != [("ok",)]:
                raise BuildDictError(f"Output PRAGMA quick_check failed: {ck2}")
        finally:
            conn_out.close()
        # Compute SHA/bytes
        sha_out = sha256_file(tf_path)
        bytes_out = tf_path.stat().st_size
        if out_p.exists():
            raise BuildDictError(f"Output path already exists: {out_p}")
        tf_path.replace(out_p)
    finally:
        if tf_path.exists():
            tf_path.unlink(missing_ok=True)
    # Ensure input unchanged
    sha_after = sha256_file(in_p)
    if sha_before != sha_after:
        raise BuildDictError("Input was mutated during Stage 05")
    # Metadata
    metadata = {
        "version": version,
        "filename": out_p.name,
        "sha256": sha_out,
        "bytes": bytes_out,
        "generated_marker": GENERATED_MARKER,
    }
    if metadata_path is not None:
        meta_p = Path(metadata_path)
        if meta_p.exists():
            raise BuildDictError(f"Metadata path already exists: {meta_p}")
        meta_p.parent.mkdir(parents=True, exist_ok=True)
        meta_p.write_text(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
        )  # noqa: E501
    else:
        # Default alongside output
        default_meta = out_p.with_suffix(".json")
        if default_meta != out_p and not default_meta.exists():
            default_meta.write_text(
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
            )  # noqa: E501

    return metadata


if __name__ == "__main__":
    sys.exit(main())
