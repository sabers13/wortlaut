"""Offline dictionary build tooling for German flashcards.

Implements build stage 01 (ADR-0001 §12):
Deterministic offline JSONL-to-SQLite transform from Kaikki/Wiktextract dumps
to the read-only dictionary core (lemma, surface_form, sense tables).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Sequence

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
CREATE TABLE IF NOT EXISTS lemma (
  id            INTEGER PRIMARY KEY,
  lemma         TEXT NOT NULL,
  pos           TEXT NOT NULL,
  gender        TEXT,
  plural        TEXT,
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
  UNIQUE(lemma, pos, gender)
);
CREATE INDEX IF NOT EXISTS ix_lemma_lookup ON lemma(lemma, pos);

CREATE TABLE IF NOT EXISTS surface_form (
  form      TEXT NOT NULL,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  PRIMARY KEY (form, lemma_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sense (
  id        INTEGER PRIMARY KEY,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  ord       INTEGER NOT NULL DEFAULT 0,
  gloss_en  TEXT NOT NULL,
  register  TEXT,
  source    TEXT,
  license   TEXT
);
CREATE INDEX IF NOT EXISTS ix_sense_lemma ON sense(lemma_id, ord);
"""


class BuildDictError(Exception):
    """Base error for dictionary build failures."""


def canonicalize_pos(raw_pos: str) -> str:
    """Map Wiktextract POS tag to canonical Universal POS tag or uppercase raw POS."""
    return POS_MAP.get(raw_pos, raw_pos.upper())


@dataclass
class LemmaAccumulator:
    """In-memory accumulator for a single merged lemma identity."""

    word: str
    pos: str
    gender: str | None
    ipa: str | None = None
    ipa_source: str | None = None
    plural_candidates: set[str] = field(default_factory=set)
    genitive_sg_candidates: set[str] = field(default_factory=set)
    praesens_3sg_candidates: set[str] = field(default_factory=set)
    praeteritum_3sg_candidates: set[str] = field(default_factory=set)
    partizip_ii_candidates: set[str] = field(default_factory=set)
    comparative_candidates: set[str] = field(default_factory=set)
    superlative_candidates: set[str] = field(default_factory=set)
    surface_forms: set[str] = field(default_factory=set)
    glosses_en: list[str] = field(default_factory=list)


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

            # Participating record: validate participating fields (C8)
            # 1. Tags and Gender
            gender: str | None = None
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

            canonical_pos = canonicalize_pos(pos)
            lemma_key = (word, canonical_pos, gender)

            if lemma_key not in accumulators:
                accumulators[lemma_key] = LemmaAccumulator(
                    word=word, pos=canonical_pos, gender=gender
                )
            acc = accumulators[lemma_key]

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

            # 3. Senses and English Glosses (owned by English edition, C5)
            if "senses" in record and record["senses"] is not None:
                senses = record["senses"]
                _validate_type(senses, list, "senses", file_path, line_no)
                for sense in senses:
                    _validate_type(sense, dict, "senses[]", file_path, line_no)
                    if "glosses" in sense and sense["glosses"] is not None:
                        glosses = sense["glosses"]
                        _validate_type(glosses, list, "senses[].glosses", file_path, line_no)
                        for g in glosses:
                            _validate_type(g, str, "senses[].glosses[]", file_path, line_no)
                            if is_en_edition and g.strip():
                                clean_g = g.strip()
                                if clean_g not in acc.glosses_en and len(acc.glosses_en) < 3:
                                    acc.glosses_en.append(clean_g)

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

        with conn:
            sense_id_counter = 1
            for lemma_id, key in enumerate(sorted_keys, start=1):
                acc = accumulators[key]

                plural = min(acc.plural_candidates) if acc.plural_candidates else None
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

                conn.execute(
                    """
                    INSERT INTO lemma (
                        id, lemma, pos, gender, plural, genitive_sg, aux, separable, particle,
                        reflexive, praesens_3sg, praeteritum_3sg, partizip_ii, governs,
                        comparative, superlative, ipa, ipa_source, freq_rank, source, license
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lemma_id,
                        acc.word,
                        acc.pos,
                        acc.gender,
                        plural,
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

                # Insert senses with ord
                for ord_idx, gloss_en in enumerate(acc.glosses_en):
                    conn.execute(
                        """
                        INSERT INTO sense (
                            id, lemma_id, ord, gloss_en, register, source, license
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            sense_id_counter,
                            lemma_id,
                            ord_idx,
                            gloss_en,
                            None,  # register
                            "wiktionary",
                            "CC BY-SA",
                        ),
                    )
                    sense_id_counter += 1

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
