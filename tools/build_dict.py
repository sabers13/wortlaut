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
import sqlite3
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Sequence

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


def canonicalize_string_projection(s: str) -> str | None:
    """Canonicalize string for sense fallback fingerprint projection."""
    s = unicodedata.normalize("NFC", s).casefold()
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    s = " ".join(s.split())
    return s if s else None


def canonicalize_projection_value(val: object) -> object:
    """Canonicalize any value (string, list, dict, scalar) for fallback fingerprint."""
    if val is None:
        return None
    if isinstance(val, str):
        return canonicalize_string_projection(val)
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, list):
        canon_items: list[Any] = []
        for item in val:
            c = canonicalize_projection_value(item)
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
            c_val = canonicalize_projection_value(val[k])
            if c_val is not None:
                canon_dict[k] = c_val
        return canon_dict if canon_dict else None
    return None


def compute_sense_fallback_ref(raw_sense: dict[str, Any]) -> str:
    """Compute cosmetic-stable fallback sense source_ref fingerprint (A4)."""
    projection: dict[str, Any] = {}
    for f in INCLUDED_SENSE_DISTINCTION_FIELDS:
        if f in raw_sense and raw_sense[f] is not None:
            c = canonicalize_projection_value(raw_sense[f])
            if c is not None:
                projection[f] = c
    payload = json.dumps(
        projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"fingerprint:v1:{hashlib.sha256(payload).hexdigest()}"


def compute_sense_source_ref(raw_sense: dict[str, Any]) -> str:
    """Compute stable sense source_ref from senseid, wikidata, or fallback fingerprint (A4)."""
    # 1. Prefer usable upstream senseid values
    senseids_raw = raw_sense.get("senseid")
    if senseids_raw is None:
        senseids_raw = raw_sense.get("senseids")
    if senseids_raw is not None:
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
        elif len(clean_senseids) > 1:
            sorted_senseids = sorted(clean_senseids)
            payload = json.dumps(
                sorted_senseids, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            return f"senseids:v1:{hashlib.sha256(payload).hexdigest()}"

    # 2. Prefer usable sense-level Wikidata QID(s)
    wikidata_raw = raw_sense.get("wikidata")
    if wikidata_raw is not None:
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
        elif len(clean_qids) > 1:
            sorted_qids = sorted(clean_qids)
            payload = json.dumps(
                sorted_qids, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            return f"wikidata-set:v1:{hashlib.sha256(payload).hexdigest()}"

    # 3. Fallback canonical fingerprint
    return compute_sense_fallback_ref(raw_sense)


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
            gender: str | None = None
            has_no_plural_tag = False
            if "tags" in record and record["tags"] is not None:
                tags = record["tags"]
                _validate_type(tags, list, "tags", file_path, line_no)
                for tag in tags:
                    _validate_type(tag, str, "tags[]", file_path, line_no)

                found_genders: set[str] = set()
                if "masculine" in tags:
                    found_genders.add("der")
                if "feminine" in tags:
                    found_genders.add("die")
                if "neuter" in tags:
                    found_genders.add("das")

                if len(found_genders) > 1:
                    raise BuildDictError(
                        f"Conflicting gender tags {sorted(found_genders)} for '{word}' in "
                        f"{file_path}:{line_no}"
                    )
                if found_genders:
                    gender = next(iter(found_genders))

                if "no-plural" in tags:
                    has_no_plural_tag = True

            canonical_pos = canonicalize_pos(pos)
            lemma_key = (word, canonical_pos, gender)

            if lemma_key not in accumulators:
                accumulators[lemma_key] = LemmaAccumulator(
                    word=word, pos=canonical_pos, gender=gender
                )
            acc = accumulators[lemma_key]
            if has_no_plural_tag:
                acc.plural_none = True

            # 2. Sounds and IPA
            if "sounds" in record and record["sounds"] is not None:
                sounds = record["sounds"]
                _validate_type(sounds, list, "sounds", file_path, line_no)
                for sound in sounds:
                    _validate_type(sound, dict, "sounds[]", file_path, line_no)
                    if "ipa" in sound and sound["ipa"] is not None:
                        ipa_val = sound["ipa"]
                        _validate_type(ipa_val, str, "sounds[].ipa", file_path, line_no)
                        if ipa_val.strip() and acc.ipa is None:
                            acc.ipa = ipa_val.strip()
                            acc.ipa_source = "wiktionary"

            # 3. Senses (owned by English edition, C5)
            if "senses" in record and record["senses"] is not None:
                senses = record["senses"]
                _validate_type(senses, list, "senses", file_path, line_no)
                for sense in senses:
                    _validate_type(sense, dict, "senses[]", file_path, line_no)
                    if is_en_edition:
                        acc.raw_senses_en.append(sense)

            # 4. Forms (Surface forms and Form-derived fields, C6 & C7)
            if "forms" in record and record["forms"] is not None:
                forms = record["forms"]
                _validate_type(forms, list, "forms", file_path, line_no)
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
                            if clean_form != word:
                                acc.surface_forms.add(clean_form)

                            tags_set = set(form_tags) if form_tags is not None else set()
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
    sorted_keys = sorted(accumulators.keys(), key=lambda k: (k[0], k[1], k[2] or ""))

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
                retained_senses: list[tuple[dict[str, Any], list[str]]] = []
                total_en_meanings = 0
                seen_gloss_texts: set[str] = set()

                for raw_sense in acc.raw_senses_en:
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
                            (raw_sense, retained_glosses_for_this_sense)
                        )

                for ord_idx, (raw_sense, gloss_list) in enumerate(retained_senses):
                    source_namespace = "wiktextract:enwiktionary"
                    source_ref = compute_sense_source_ref(raw_sense)
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

    return 1


if __name__ == "__main__":
    sys.exit(main())
