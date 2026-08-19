# Slice 1 report

## NARRATIVE
- Decisions not already fixed by the brief:
  - Defined `LookupProtocol` and `LemmaRecord` in `app/resolve.py` as pure structural interfaces, ensuring `app/resolve.py` has zero I/O or database dependencies while allowing `app/dictionary.py` to implement the protocol cleanly.
  - Configured `app/dictionary.py` with SQLite read-only enforcement (`?mode=ro` and `PRAGMA query_only = ON;`), restricting all queries to PART A tables (`lemma`, `surface_form`, `sense`, `example`, `example_lemma`).
  - Employed Unicode-safe case normalization `(lemma = ? OR lower(lemma) = ?)` in dictionary lookup queries to support both inflected forms and compound elements with German umlauts.
  - Added canonical `tools/resolver_hash.py` SHA-256 computation over raw bytes and AST-based fail-closed checking in `tools/check_agents.py` for AGENTS R3.
- Stop-and-ask conditions encountered:
  - None.
- Problems noticed but deliberately not fixed:
  - `reference/smoke_test.py` has outdated paths; left untouched as instructed for repair in a later slice.
  - Real spaCy pipeline loading and ADR-0001 §13 Gate 1 verification are intentionally deferred to slice-2.
- Work left undone:
  - None for slice-1. All acceptance criteria B1–B13 and worker constraints are fully satisfied.
