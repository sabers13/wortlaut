"""Resolution ladder and deterministic compound splitter for German vocabulary.

Implements ADR-0001 §10 four-step resolution ladder:
1. Exact (lemma, pos[, gender])
2. Surface form
3. Compound split (deterministic longest-known-head with Fugenelemente)
4. Stub fallback (status='needs_gloss')

This module is completely pure and performs no I/O of any kind.
All dictionary checks are injected via LookupProtocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, Protocol, Sequence, runtime_checkable

# Canonical separable-verb dependency label (ADR-0001 §13 Gate 1 / slice-2 target)
SVP_DEP: Final[str] = "svp"

# Standard German separable verb prefix particles
PARTICLES: Final[frozenset[str]] = frozenset({
    "ab",
    "an",
    "auf",
    "aus",
    "bei",
    "ein",
    "fest",
    "frei",
    "los",
    "mit",
    "nach",
    "statt",
    "um",
    "vor",
    "weg",
    "zu",
    "zurück",
})

# Deterministic Fugenelemente hardcoded per ADR-0001 §10 (Acceptance B2)
FUGENELEMENTE: Final[tuple[str, ...]] = ("s", "es", "n", "en", "er", "e", "ns")


@dataclass(frozen=True)
class LemmaRecord:
    """Lightweight lemma record returned by lookup oracle."""

    id: int | None
    lemma: str
    pos: str
    gender: str | None = None


@dataclass(frozen=True)
class Ref:
    """Resolved candidate reference matching ADR-0001 schema and domains."""

    lemma: str
    pos: str
    gender: str | None = None
    status: str = "resolved"  # 'resolved' | 'derived_compound' | 'needs_gloss'
    lemma_id: int | None = None
    components: list[str] | None = None
    head_lemma: str | None = None


# Alias for Ref to match ADR naming
ResolvedRef = Ref


@dataclass(frozen=True)
class CompoundSplitResult:
    """Result of deterministic compound splitting."""

    components: list[str]
    head: LemmaRecord


@runtime_checkable
class LookupProtocol(Protocol):
    """Injected dictionary lookup protocol (pure seam between resolve and dictionary)."""

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaRecord]:
        """Look up lemma by exact text, optionally filtered by POS and/or gender."""
        ...

    def lookup_surface_form(self, form: str) -> Sequence[LemmaRecord]:
        """Look up lemmas associated with an inflected surface form."""
        ...


@runtime_checkable
class TokenLike(Protocol):
    """Structural protocol for token test doubles and NLP tokens."""

    @property
    def text(self) -> str: ...

    @property
    def lemma_(self) -> str: ...

    @property
    def pos_(self) -> str: ...

    @property
    def dep_(self) -> str: ...

    @property
    def head(self) -> TokenLike: ...

    @property
    def children(self) -> Iterable[TokenLike]: ...


def split_compound(word: str, oracle: LookupProtocol) -> CompoundSplitResult | None:
    """Deterministic longest-known-head compound splitter.

    Uses hardcoded exceptionless Fugenelemente (s, es, n, en, er, e, ns).
    Inherits gender and POS from the head (rightmost component).
    Returns lowercased component list and the head LemmaRecord.
    """
    w = word.strip().lower()
    if len(w) < 3:
        return None

    # Search for longest known head from right to left (i from 1 to len(w)-1)
    for i in range(1, len(w)):
        head_text = w[i:]
        head_matches = oracle.lookup_exact(head_text)
        if not head_matches:
            continue

        # Prioritize noun match for head to inherit gender
        head_record = next(
            (m for m in head_matches if m.pos == "NOUN"),
            head_matches[0],
        )

        prefix = w[:i]
        # Check direct attachment ("") and all matching Fugenelemente
        sorted_fuges = [""] + [
            f for f in sorted(FUGENELEMENTE, key=len, reverse=True) if prefix.endswith(f)
        ]

        for fuge in sorted_fuges:
            stem = prefix[: -len(fuge)] if fuge else prefix
            if not stem:
                continue

            # Base case: stem is a known lemma
            stem_matches = oracle.lookup_exact(stem)
            if stem_matches:
                return CompoundSplitResult(
                    components=[stem, head_text],
                    head=head_record,
                )

            # Recursive case: stem can be further decomposed
            sub_split = split_compound(stem, oracle)
            if sub_split is not None:
                return CompoundSplitResult(
                    components=sub_split.components + [head_text],
                    head=head_record,
                )

    return None


def resolve_word(
    word: str,
    oracle: LookupProtocol,
    pos: str | None = None,
    gender: str | None = None,
) -> Sequence[Ref]:
    """Resolve a bare word string through the 4-step resolution ladder.

    Ladder steps:
    1. Exact (lemma, pos[, gender])
    2. Surface form lookup
    3. Compound split (deterministic longest-known-head)
    4. Fallback stub (status='needs_gloss')
    """
    cleaned = word.strip()
    if not cleaned:
        return [Ref(lemma="", pos=pos or "UNKNOWN", gender=gender, status="needs_gloss")]

    # 1. Exact match
    exact_matches = oracle.lookup_exact(cleaned, pos=pos, gender=gender)
    if exact_matches:
        return [
            Ref(
                lemma=m.lemma,
                pos=m.pos,
                gender=m.gender,
                status="resolved",
                lemma_id=m.id,
            )
            for m in exact_matches
        ]

    # 2. Surface form match
    surface_matches = oracle.lookup_surface_form(cleaned)
    if surface_matches:
        if pos is not None:
            pos_filtered = [m for m in surface_matches if m.pos == pos]
            if pos_filtered:
                surface_matches = pos_filtered
        seen_surface: set[tuple[str, str, str | None, int | None]] = set()
        deduped_surface: list[Ref] = []
        for m in surface_matches:
            key = (m.lemma, m.pos, m.gender, m.id)
            if key not in seen_surface:
                seen_surface.add(key)
                deduped_surface.append(
                    Ref(
                        lemma=m.lemma,
                        pos=m.pos,
                        gender=m.gender,
                        status="resolved",
                        lemma_id=m.id,
                    )
                )
        if deduped_surface:
            return deduped_surface

    # 3. Compound split
    split = split_compound(cleaned, oracle)
    if split is not None:
        head = split.head
        return [
            Ref(
                lemma=cleaned,
                pos=head.pos,
                gender=head.gender,
                status="derived_compound",
                lemma_id=None,
                components=split.components,
                head_lemma=head.lemma,
            )
        ]

    # 4. Stub fallback
    return [
        Ref(
            lemma=cleaned,
            pos=pos or "UNKNOWN",
            gender=gender,
            status="needs_gloss",
            lemma_id=None,
            components=None,
            head_lemma=None,
        )
    ]


def resolve_token(
    tok: TokenLike,
    oracle: LookupProtocol,
) -> Sequence[Ref]:
    """Resolve an NLP token through candidate generation and the resolution ladder.

    Handles German separable verbs via SVP_DEP dependency links.
    """
    tok_lemma = tok.lemma_
    tok_pos = tok.pos_
    tok_text = tok.text
    tok_dep = getattr(tok, "dep_", "")

    # Handle separable prefix token pointing to a head verb
    if tok_dep == SVP_DEP:
        head = getattr(tok, "head", None)
        if head is not None and getattr(head, "pos_", "") in ("VERB", "AUX"):
            combined = f"{tok_text.lower()}{head.lemma_.lower()}"
            matches = oracle.lookup_exact(combined, pos="VERB")
            if matches:
                return [
                    Ref(
                        lemma=m.lemma,
                        pos=m.pos,
                        gender=m.gender,
                        status="resolved",
                        lemma_id=m.id,
                    )
                    for m in matches
                ]

    # Handle verb with separable particle children
    if tok_pos in ("VERB", "AUX"):
        children = getattr(tok, "children", [])
        for child in children:
            if getattr(child, "dep_", "") == SVP_DEP:
                particle = child.text.lower()
                combined = f"{particle}{tok_lemma.lower()}"
                matches = oracle.lookup_exact(combined, pos="VERB")
                if matches:
                    return [
                        Ref(
                            lemma=m.lemma,
                            pos=m.pos,
                            gender=m.gender,
                            status="resolved",
                            lemma_id=m.id,
                        )
                        for m in matches
                    ]

    # Standard ladder: try lemma first, then surface text
    exact = oracle.lookup_exact(tok_lemma, pos=tok_pos)
    if exact:
        return [
            Ref(
                lemma=m.lemma,
                pos=m.pos,
                gender=m.gender,
                status="resolved",
                lemma_id=m.id,
            )
            for m in exact
        ]

    return resolve_word(tok_text, oracle, pos=tok_pos)


def generate_candidates(
    tok: TokenLike,
    sent: Iterable[TokenLike],
    oracle: LookupProtocol,
) -> list[Ref]:
    """Surface-scan candidate generation per ADR-0001 §4, filtered by oracle."""
    results: list[Ref] = []
    tok_lemma = tok.lemma_
    tok_pos = tok.pos_

    # Candidate 1: base token
    base_refs = resolve_word(tok_lemma, oracle, pos=tok_pos)
    for r in base_refs:
        if r.status == "resolved":
            results.append(r)

    # Candidate 2: separable verb combinations across sentence
    if tok_pos in ("VERB", "AUX"):
        for other in sent:
            if other.text.lower() in PARTICLES and getattr(other, "text", "") != tok.text:
                combined = f"{other.text.lower()}{tok_lemma.lower()}"
                matches = oracle.lookup_exact(combined, pos="VERB")
                for m in matches:
                    ref = Ref(
                        lemma=m.lemma,
                        pos=m.pos,
                        gender=m.gender,
                        status="resolved",
                        lemma_id=m.id,
                    )
                    if ref not in results:
                        results.append(ref)

    return results
