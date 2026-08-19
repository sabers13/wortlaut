"""Read-only dictionary asset reader for German flashcards.

Implements PART A of reference/schema.sql:
- lemma
- surface_form
- sense
- example
- example_lemma

Never accesses, writes, or references PART B user tables (AGENTS R9 / C2).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

from app.resolve import (
    LemmaRecord,
    LookupProtocol,
    Ref,
    TokenLike,
    resolve_token,
    resolve_word,
)

if TYPE_CHECKING:
    import types


@dataclass(frozen=True)
class LemmaEntry(LemmaRecord):
    """Full structured lemma row matching PART A lemma table."""

    id: int
    lemma: str
    pos: str
    gender: str | None = None
    plural: str | None = None
    genitive_sg: str | None = None
    aux: str | None = None
    separable: int = 0
    particle: str | None = None
    reflexive: int = 0
    praesens_3sg: str | None = None
    praeteritum_3sg: str | None = None
    partizip_ii: str | None = None
    governs: str | None = None
    comparative: str | None = None
    superlative: str | None = None
    ipa: str | None = None
    ipa_source: str | None = None
    freq_rank: int | None = None
    source: str | None = None
    license: str | None = None


@dataclass(frozen=True)
class SenseEntry:
    """Gloss sense row matching PART A sense table."""

    id: int
    lemma_id: int
    ord: int
    gloss_en: str
    register: str | None = None
    source: str | None = None
    license: str | None = None


@dataclass(frozen=True)
class ExampleEntry:
    """Example sentence row matching PART A example table."""

    id: int
    de: str
    en: str | None = None
    source: str | None = None
    source_ref: str | None = None
    license: str | None = None
    token_count: int | None = None
    has_proper: int = 0


@dataclass(frozen=True)
class DictionaryEntry:
    """Composite entry containing lemma, senses, examples, and surface forms."""

    lemma: LemmaEntry
    senses: list[SenseEntry]
    examples: list[ExampleEntry]
    surface_forms: list[str]


def _row_to_lemma(row: sqlite3.Row) -> LemmaEntry:
    """Map a sqlite3.Row to LemmaEntry."""
    return LemmaEntry(
        id=int(row["id"]),
        lemma=str(row["lemma"]),
        pos=str(row["pos"]),
        gender=str(row["gender"]) if row["gender"] is not None else None,
        plural=str(row["plural"]) if row["plural"] is not None else None,
        genitive_sg=str(row["genitive_sg"]) if row["genitive_sg"] is not None else None,
        aux=str(row["aux"]) if row["aux"] is not None else None,
        separable=int(row["separable"]) if row["separable"] is not None else 0,
        particle=str(row["particle"]) if row["particle"] is not None else None,
        reflexive=int(row["reflexive"]) if row["reflexive"] is not None else 0,
        praesens_3sg=(
            str(row["praesens_3sg"]) if row["praesens_3sg"] is not None else None
        ),
        praeteritum_3sg=(
            str(row["praeteritum_3sg"]) if row["praeteritum_3sg"] is not None else None
        ),
        partizip_ii=(
            str(row["partizip_ii"]) if row["partizip_ii"] is not None else None
        ),
        governs=str(row["governs"]) if row["governs"] is not None else None,
        comparative=str(row["comparative"]) if row["comparative"] is not None else None,
        superlative=str(row["superlative"]) if row["superlative"] is not None else None,
        ipa=str(row["ipa"]) if row["ipa"] is not None else None,
        ipa_source=str(row["ipa_source"]) if row["ipa_source"] is not None else None,
        freq_rank=int(row["freq_rank"]) if row["freq_rank"] is not None else None,
        source=str(row["source"]) if row["source"] is not None else None,
        license=str(row["license"]) if row["license"] is not None else None,
    )


def _row_to_sense(row: sqlite3.Row) -> SenseEntry:
    """Map a sqlite3.Row to SenseEntry."""
    return SenseEntry(
        id=int(row["id"]),
        lemma_id=int(row["lemma_id"]),
        ord=int(row["ord"]),
        gloss_en=str(row["gloss_en"]),
        register=str(row["register"]) if row["register"] is not None else None,
        source=str(row["source"]) if row["source"] is not None else None,
        license=str(row["license"]) if row["license"] is not None else None,
    )


def _row_to_example(row: sqlite3.Row) -> ExampleEntry:
    """Map a sqlite3.Row to ExampleEntry."""
    return ExampleEntry(
        id=int(row["id"]),
        de=str(row["de"]),
        en=str(row["en"]) if row["en"] is not None else None,
        source=str(row["source"]) if row["source"] is not None else None,
        source_ref=str(row["source_ref"]) if row["source_ref"] is not None else None,
        license=str(row["license"]) if row["license"] is not None else None,
        token_count=int(row["token_count"]) if row["token_count"] is not None else None,
        has_proper=int(row["has_proper"]) if row["has_proper"] is not None else 0,
    )


class Dictionary(LookupProtocol):
    """Read-only SQLite dictionary reader implementing LookupProtocol."""

    def __init__(self, db_path: Path | str) -> None:
        """Open SQLite database in read-only mode."""
        self._path = Path(db_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Dictionary database file not found: {self._path}")

        # Open SQLite read-only with URI mode=ro
        uri = f"file:{self._path.resolve().as_posix()}?mode=ro"
        try:
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        except sqlite3.OperationalError:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.execute("PRAGMA query_only = ON;")

        self._conn.row_factory = sqlite3.Row

    @property
    def path(self) -> Path:
        """Return the database path."""
        return self._path

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Dictionary:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.close()

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaEntry]:
        """Look up lemma by exact text, optionally filtered by POS and/or gender."""
        query = [
            "SELECT id, lemma, pos, gender, plural, genitive_sg, aux, separable, particle,",
            "       reflexive, praesens_3sg, praeteritum_3sg, partizip_ii, governs,",
            "       comparative, superlative, ipa, ipa_source, freq_rank, source, license",
            "FROM lemma",
            "WHERE (lemma = ? OR lower(lemma) = ?)",
        ]
        params: list[Any] = [lemma, lemma.lower()]

        if pos is not None:
            query.append("AND pos = ?")
            params.append(pos)

        if gender is not None:
            query.append("AND gender = ?")
            params.append(gender)

        query.append("ORDER BY freq_rank ASC NULLS LAST, id ASC")
        cur = self._conn.execute(" ".join(query), params)
        return [_row_to_lemma(row) for row in cur.fetchall()]

    def lookup_surface_form(self, form: str) -> Sequence[LemmaEntry]:
        """Look up lemmas associated with an inflected surface form."""
        query = (
            "SELECT l.id, l.lemma, l.pos, l.gender, l.plural, l.genitive_sg, l.aux, "
            "       l.separable, l.particle, l.reflexive, l.praesens_3sg, "
            "       l.praeteritum_3sg, l.partizip_ii, l.governs, l.comparative, "
            "       l.superlative, l.ipa, l.ipa_source, l.freq_rank, l.source, l.license "
            "FROM surface_form sf "
            "JOIN lemma l ON sf.lemma_id = l.id "
            "WHERE (sf.form = ? OR lower(sf.form) = ?) "
            "ORDER BY l.freq_rank ASC NULLS LAST, l.id ASC"
        )
        cur = self._conn.execute(query, [form, form.lower()])
        seen: set[int] = set()
        results: list[LemmaEntry] = []
        for row in cur.fetchall():
            lemma_entry = _row_to_lemma(row)
            if lemma_entry.id not in seen:
                seen.add(lemma_entry.id)
                results.append(lemma_entry)
        return results

    def get_lemma_by_id(self, lemma_id: int) -> LemmaEntry | None:
        """Fetch a single lemma row by primary key."""
        query = (
            "SELECT id, lemma, pos, gender, plural, genitive_sg, aux, separable, particle, "
            "       reflexive, praesens_3sg, praeteritum_3sg, partizip_ii, governs, "
            "       comparative, superlative, ipa, ipa_source, freq_rank, source, license "
            "FROM lemma WHERE id = ?"
        )
        cur = self._conn.execute(query, [lemma_id])
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_lemma(row)

    def get_senses_for_lemma(self, lemma_id: int) -> list[SenseEntry]:
        """Fetch all English gloss senses for a lemma, ordered by ord."""
        query = (
            "SELECT id, lemma_id, ord, gloss_en, register, source, license "
            "FROM sense WHERE lemma_id = ? "
            "ORDER BY ord ASC, id ASC"
        )
        cur = self._conn.execute(query, [lemma_id])
        return [_row_to_sense(row) for row in cur.fetchall()]

    def get_examples_for_lemma(self, lemma_id: int) -> list[ExampleEntry]:
        """Fetch example sentences indexed for a lemma via example_lemma."""
        query = (
            "SELECT e.id, e.de, e.en, e.source, e.source_ref, e.license, "
            "       e.token_count, e.has_proper "
            "FROM example_lemma el "
            "JOIN example e ON el.example_id = e.id "
            "WHERE el.lemma_id = ? "
            "ORDER BY e.id ASC"
        )
        cur = self._conn.execute(query, [lemma_id])
        return [_row_to_example(row) for row in cur.fetchall()]

    def get_surface_forms_for_lemma(self, lemma_id: int) -> list[str]:
        """Fetch all surface forms recorded for a lemma."""
        query = "SELECT form FROM surface_form WHERE lemma_id = ? ORDER BY form ASC"
        cur = self._conn.execute(query, [lemma_id])
        return [str(row["form"]) for row in cur.fetchall()]

    def get_entry(self, lemma_id: int) -> DictionaryEntry | None:
        """Fetch composite entry (lemma + senses + examples + surface forms)."""
        lemma = self.get_lemma_by_id(lemma_id)
        if lemma is None:
            return None
        senses = self.get_senses_for_lemma(lemma_id)
        examples = self.get_examples_for_lemma(lemma_id)
        surface_forms = self.get_surface_forms_for_lemma(lemma_id)
        return DictionaryEntry(
            lemma=lemma,
            senses=senses,
            examples=examples,
            surface_forms=surface_forms,
        )

    def suggest_lemmas(self, prefix: str, limit: int = 10) -> list[LemmaEntry]:
        """Prefix lookup for autocomplete suggestions (ADR-0001 §10)."""
        query = (
            "SELECT id, lemma, pos, gender, plural, genitive_sg, aux, separable, particle, "
            "       reflexive, praesens_3sg, praeteritum_3sg, partizip_ii, governs, "
            "       comparative, superlative, ipa, ipa_source, freq_rank, source, license "
            "FROM lemma "
            "WHERE lemma LIKE ? || '%' "
            "ORDER BY freq_rank ASC NULLS LAST, lemma ASC "
            "LIMIT ?"
        )
        cur = self._conn.execute(query, [prefix, limit])
        return [_row_to_lemma(row) for row in cur.fetchall()]

    def resolve(
        self,
        word: str,
        pos: str | None = None,
        gender: str | None = None,
    ) -> Sequence[Ref]:
        """Convenience method resolving a bare word through the ladder."""
        return resolve_word(word, oracle=self, pos=pos, gender=gender)

    def resolve_tok(self, tok: TokenLike) -> Sequence[Ref]:
        """Convenience method resolving a token through the ladder."""
        return resolve_token(tok, oracle=self)
