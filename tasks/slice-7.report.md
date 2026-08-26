# Slice 7 report

## NARRATIVE

### Executive Summary & Stage Progression

Slice 7 delivers the complete standalone runtime application for the flashcard system in accordance with ADR-0001, ADR-0002 §6 order 8, ADR-0003, ADR-0004 (D43, D46, D47), ADR-0005 (D48–D56), accepted ADR-0007 (D72–D81), and AGENTS rules R4, R5, R6, R9, R10, R12, R13, C1, C2, and C3.

The slice progressed across six staged increments:
1. **Stage S1 (`a678f1b`)**: Completed `reference/schema.sql` PART-B user DDL and implemented FSRS review scheduling and append-only confidence logging (`app/deck.py`).
2. **Stage S2 (`8cf6367`)**: Note-local selected learner meanings (`{de, en}`), user-authored overrides, D43 meaning availability, display-time card rendering, and tri-state noun plurals (`app/render.py`, `app/deck.py`).
3. **Stage S3 (`bbf858e`)**: `DictionaryRuntime` atomic activation, PART-B relinking, durable semantic refs, generation leasing, and stale picker HTTP 409 conflict detection (`app/deck.py`).
4. **Stage S4 (`3e3e9d8`)**: Pronunciation audio precedence ladder (saved custom, approved Commons human, Piper TTS cache, silent fallback), untrusted media validation, sacred custom persistence, and crash-safe replacement (`app/audio.py`).
5. **Stage S5 (`35c70c9`)**: Standalone FastAPI app factory `create_app`, browser-facing loopback security middleware, `X-Flashcards-Request` header guards, full `/vocab` HTTP API, and sanitized Anki TSV export (`app/api.py`, `app/__init__.py`).
6. **Stage S6 (current stage)**: Executable AGENTS rule checks for R6, R12, and R13 in `tools/check_agents.py` with full negative/positive test controls in `tests/test_check_agents.py` and this comprehensive slice report.

### 1. PART-B User Database Schema Landed in S1

The user database schema in `reference/schema.sql` establishes complete PART-B persistence with foreign keys enabled (`PRAGMA foreign_keys = ON;`) while maintaining strict physical and logical separation from read-only dictionary assets (AGENTS R9):
- `deck`: User decks (`id`, `name`, `created_at`).
- `note`: Core vocabulary notes (`id`, `lemma_semantic_ref`, `sense_semantic_ref`, `status`, `created_at`, `due_at`, `interval_days`, `ease_factor`, `review_count`, `last_confidence`). The `status` column is constrained to `('resolved', 'needs_gloss', 'derived_compound', 'orphaned')`.
- `card`: FSRS card state (`id`, `note_id`, `state`, `step`, `stability`, `difficulty`, `due_at`, `last_review`). In accordance with AGENTS R4, rendered card faces (front/back HTML/text) are never stored in SQLite; they are dynamically rendered at display time.
- `review_log`: Append-only review history (AGENTS R6). Enforces `confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5)` and `rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4)` along with `scheduled_days`, `elapsed_days`, `reviewed_at`. There are zero `UPDATE` or `DELETE` statements targeting `review_log` across the entire application codebase.
- `note_deck`: Many-to-many note-deck memberships. Deck deletion removes `note_deck` rows; orphaned notes move to the `"Orphaned"` deck and are never cascade-deleted if they have review history (AGENTS R5).
- `note_meaning_lang`: Composite primary key `(note_id, lang)` enforcing per-note selected meaning languages from the valid active domain `CHECK (lang IN ('de', 'en'))`.
- `note_user_meaning`: Per-note user-authored learner glosses `(note_id, lang, meaning_text, created_at, updated_at)` superseding dictionary entries.
- `note_dictionary_binding`: Durable dictionary bindings mapping `(note_id, role, component_ord)` to `lemma_semantic_ref`, `sense_semantic_ref`, `cached_lemma_id`, `cached_sense_id`, and `binding_status` (`'bound'`, `'unbound'`, `'ambiguous'`). For `role = 'component'`, `component_count` stores the resolver's declared vector length, enabling independent D46 all-components-or-none validation.
- `active_dictionary_metadata`: Singleton table (`singleton = 1`) tracking `active_version`, `active_filename`, `active_sha256`, and `activated_at`.
- `custom_pronunciation`: Sacred user-recorded or uploaded pronunciation media metadata (`note_id`, `media_filename`, `sha256`, `byte_size`, `format`, `source_type`, `created_at`).

### 2. FSRS Review Scheduling & Raw Confidence Logging Evidence

The review scheduling loop in `app/deck.py` integrates `fsrs==6.3.2` with learning steps `(1 min, 10 min)`:
- Accepts raw learner confidence ratings 1–5 (ADR-0003 D27).
- Applies the deterministic ADR-0003 D28 mapping:
  - Confidence `1` -> `Rating.Again` (rating 1, Learning state, interval 1 min)
  - Confidence `2` -> `Rating.Again` (rating 1, Learning state, interval 1 min; identical to 1 on new cards)
  - Confidence `3` -> `Rating.Hard` (rating 2, Learning state, interval 5.5 min)
  - Confidence `4` -> `Rating.Good` (rating 3, Learning state, interval 10 min)
  - Confidence `5` -> `Rating.Easy` (rating 4, Review state, interval 8 days; graduates new cards)
- Both the raw confidence (1–5) and the mapped FSRS rating (1–4) are persisted to `review_log` in an append-only transaction.
- Key test evidence in `tests/test_deck.py`:
  - `test_confidence_mapping_and_new_card_scheduler_cases`: validates mapped ratings, intervals, 1/2 equality on new cards, and confidence 5 graduation across all five confidence ratings.
  - `test_review_log_persists_raw_confidence_and_mapped_rating`: verifies append-only logging of raw confidence and mapped rating.
  - `test_deck_deletion_orphans_unreviewed_and_reviewed_notes`: verifies AGENTS R5 non-cascade orphan mechanics upon deck deletion.

### 3. Multilingual Meaning Sets, User Meanings & D43 Availability Evidence

In `app/deck.py` and `app/render.py`:
- Each note selects a non-empty subset of `{de, en}` (`{'de'}`, `{'en'}`, or `{'de', 'en'}`).
- Persian (`fa`) is strictly deferred under accepted ADR-0007; any submission specifying `fa` is rejected with HTTP 422 Unprocessable Entity with zero database writes.
- User-authored meanings (`note_user_meaning`) take precedence over dictionary meanings for the respective language and are marked as user-authored.
- D43 availability state is computed over selected languages:
  - `complete`: all selected languages have at least one valid meaning (user-authored or dictionary-bound).
  - `partial`: at least one selected language has meaning text, but not all.
  - `none`: none of the selected languages have meaning text (e.g. `needs_gloss` stubs or unbound senses).
- Key test evidence:
  - `tests/test_deck.py::test_user_meanings_precede_dictionary_and_availability_uses_binding`
  - `tests/test_deck.py::test_derived_compound_availability_requires_all_components`
  - `tests/test_deck.py::test_persian_is_rejected_without_database_mutations`

### 4. Display-Time Card Rendering, Tri-State Plurals & D46 Decomposition Evidence

In `app/render.py`:
- `render_card` dynamically produces `RenderedCard` (front and back faces) from structured input.
- **Front Face**: headword, gender/article (for nouns), POS, IPA (if available), and audio trigger token.
- **Back Face**: front face header, rendered meanings grouped by selected language, user-authored badges, grammar metadata (separable prefix, auxiliary, inflection/governs), and Tatoeba example sentences (German + English translation).
- **Tri-State Noun Plural** (ADR-0004 §10):
  1. `plural` present -> renders plural form (e.g. `Plural: die Häuser`).
  2. `plural_none = 1` -> renders explicit `"kein Plural"` indicator.
  3. Both null / non-noun -> plural section is completely omitted.
- **D46 Compound Rendering**: Derived compound notes render all constituent components in decomposition order or none if any component is missing or unbound.
- Key test evidence in `tests/test_render.py`:
  - `test_t1_front_face_noun_with_article_gender_ipa`, `test_t1_front_face_ipa_absent`, `test_t1_front_face_non_noun_has_no_article`, `test_t1_front_face_from_lemma_entry`
  - `test_t2_back_face_composition_selected_languages_de_only`, `test_t2_back_face_composition_selected_languages_en_only`, `test_t2_back_face_composition_selected_languages_de_and_en_order`, `test_t2_back_face_unselected_language_absent_entirely`
  - `test_t3_user_meaning_precedence_and_marking`
  - `test_t4_tri_state_plural_known_form`, `test_t4_tri_state_plural_none_singular_only`, `test_t4_tri_state_plural_unknown_load_bearing_omitted`, `test_t4_tri_state_plural_non_noun_omitted`
  - `test_t5_grammar_metadata_all_conditional_fields`, `test_t5_grammar_metadata_absent_fields_contribute_nothing`
  - `test_t6_examples_de_and_en`, `test_t6_examples_de_only`, `test_t6_examples_empty_list_clean`, `test_t6_examples_from_example_entry`
  - `test_t7_derived_compound_all_components_present_head_last`, `test_t7_derived_compound_missing_component_suppresses_language_block`, `test_t7_derived_compound_user_meaning_overrides_whole_block`
  - `test_t8_purity_and_determinism`, `test_t9_language_domain_persian_fa_raises_value_error`

### 5. DictionaryRuntime Atomic Activation, Relink, Stale-Picker & Clarified Contract Evidence

The `DictionaryRuntime` in `app/deck.py` implements the complete D47 lifecycle:
- **Managed Directory & Path Traversal Prevention**: Candidates must resolve within the runtime's managed directory; path traversal, symlink escapes, and separators in filenames are rejected.
- **Underlying-File Identity (Hard-Link Safe R9)**: Compares candidates against the user database inode/device via `os.path.samefile` / `_is_same_file`, rejecting hard-link aliases and identical inodes.
- **Value-Snapshot Reading View**: `reading()` yields an inert, immutable `ReadingSnapshot` holding only copied primitive values under an atomic generation pin and deferred read transaction.
- **All-or-Nothing Pins & Release Symmetry**: Pins increment only after reader setup succeeds; teardown cleanly releases connections and decrements pins on both normal exit and exception rollback.
- **No-Drain Concurrency**: Activation does not drain or block readers; the runtime lock is held only across the commit and generation swap. Readers observe complete-old or complete-new states without mixed PART-A/PART-B visibility.
- **Same-Thread Reentrancy Refusal**: Calling `activate_dictionary` or `close` while holding a read pin on the same thread raises `DictionaryRuntimeError` immediately without deadlocking.
- **Deterministic Relinking**: Stable semantic references (`lemma_semantic_ref`, `sense_semantic_ref`) are validated against the candidate dictionary. Surviving refs become `'bound'`; missing refs fail closed to `'unbound'` with `note.status = 'needs_gloss'`. Compound notes revalidate their full component vector against `component_count`.
- **Stale Picker 409 Rejection**: `POST /vocab/notes` validates the submitted asset token against `runtime.asset_token`, rejecting mismatches with HTTP 409 Conflict.
- **Full E-Suite Test Coverage** in `tests/test_dictionary.py`:
  - `test_e1_purity_immutable_reading_snapshot`
  - `test_e2_all_or_nothing_pin_acquisition_failure`
  - `test_e3_reading_snapshot_release_symmetry_teardown`
  - `test_e4_no_drain_concurrent_reading_and_activation`
  - `test_e5_reentrancy_refusal_raises_immediately`
  - `test_e5b_blocking_validation_serializes_concurrent_ops`
  - `test_e5c_same_thread_reentrancy_termination`
  - `test_e6_whole_table_non_vacuous_rollback`
  - `test_e7_overlapping_read_visibility_single_generation_pairing`
  - `test_e8_seam_probe_exception_containment`
  - `test_e9_managed_directory_rejection_cases`
  - `test_e10_restart_recovery_sha_mismatch_fails_construction`
  - `test_e11_teardown_close_failure_contained`
  - `test_e12_cleanup_non_masking_primary_exception_propagates`
  - `test_e13_underlying_file_identity_rejected`
  - `test_e14_role_status_consistency_stray_rows`
  - `test_e15_stale_token_detection_readiness`

### 6. Pronunciation Audio Precedence, Custom Media & Piper Evidence

In `app/audio.py`:
- **5-Stage Precedence Ladder** (ADR-0005 D48):
  1. Note-local custom audio (user recording or upload).
  2. Validated human pronunciation from approved Commons metadata.
  3. Automatic local Piper TTS cache (`de_DE-thorsten-high`).
  4. Optional remote `/speak` endpoint (<= 1.0s timeout with automatic Piper fallback).
  5. Silent fallback (cards display and review normally without audio).
- **Untrusted Media Validation**: Enforces container/codec validation (WAV, MP3, OGG, WebM/Opus), size bounds (<= 2MB), and duration limits (<= 15s) using standard library audio headers.
- **Sacred User Media & Crash-Safe Replacement**: Custom audio is persisted in the user media directory; replacements write to a staging file under non-active identity before committing to SQLite and unlinking the prior asset.
- **Reversion to Automatic**: `DELETE /vocab/notes/{id}/audio` removes the custom override and restores automatic synthesis.
- Key test evidence in `tests/test_audio.py`:
  - `test_audio_precedence_ladder`
  - `test_custom_audio_validation_and_persistence`
  - `test_custom_audio_crash_safe_replacement`
  - `test_custom_audio_revert_to_automatic`
  - `test_human_pronunciation_cache_and_discovery`
  - `test_piper_synthesis_and_disposable_cache`
  - `test_remote_tts_fallback_to_piper`
  - `test_silent_fallback_when_audio_unavailable`

### 7. API Endpoint Coverage & AGENTS R12 Security Guards

In `app/api.py` and `app/__init__.py`:
- App factory `create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None, media_dir=None, cache_dir=None)` maintains zero module-level state and performs no import-time environment reads (AGENTS C1).
- Enforces strict one-way dependency direction `api -> deck -> render -> dictionary -> resolve` (AGENTS C2).
- **AGENTS R12 Security Guards**:
  - `cors_origins` wildcard `*` is strictly forbidden and rejected at creation with `ValueError`.
  - `BrowserSecurityMiddleware` validates `Host` header against loopback endpoints (`127.0.0.1`, `localhost`, `[::1]`).
  - `Origin` header must match the configured allowlist exactly.
  - All non-GET `/vocab` routes require header `X-Flashcards-Request: 1` (rejecting missing/invalid headers with HTTP 403 before route execution).
  - JSON endpoints require `Content-Type: application/json` (HTTP 400 on invalid content type).
- **Comprehensive `/vocab` API Surface**:
  - `GET /vocab/lookup?q=...`: resolution candidates, active asset token.
  - `POST /vocab/notes`: note capture with asset token verification and stale picker rejection (HTTP 409).
  - `GET /vocab/cards/next`: next due card with dynamic display-time rendering.
  - `POST /vocab/cards/{id}/review`: submit confidence 1–5 rating.
  - `POST /vocab/notes/{id}/gloss` & `DELETE /vocab/notes/{id}/gloss`: user meaning endpoints.
  - `POST /vocab/notes/{id}/audio` & `DELETE /vocab/notes/{id}/audio`: custom pronunciation media management.
  - `GET /vocab/audio/{audio_id}`: audio streaming endpoint.
  - `POST /vocab/dictionary/activate`: atomic dictionary activation.
  - `GET /vocab/decks`, `POST /vocab/decks`, `DELETE /vocab/decks/{id}`: deck management.
  - `GET /vocab/export/anki`: sanitized tab-separated Anki export (AGENTS R10).
- Key test evidence in `tests/test_api.py`:
  - `test_r12_wildcard_cors_rejected_at_creation`
  - `test_r12_host_header_loopback_enforced`
  - `test_r12_origin_header_allowlist_enforced`
  - `test_r12_custom_header_required_on_non_get`
  - `test_r12_json_content_type_required`
  - `test_lookup_endpoint`, `test_capture_note_and_failure_matrix`, `test_next_card_and_review_loop`
  - `test_gloss_endpoints_and_fa_rejection`, `test_audio_endpoints_and_preservation`, `test_dictionary_activate_endpoints`
  - `test_deck_management_endpoints`, `test_anki_tsv_export_sanitization`

### 8. Executable AGENTS Check Results for R6, R12, and R13

Extended `tools/check_agents.py` with three new executable checks:
- **R6 Check (`check_r6`)**:
  - Verifies `reference/schema.sql` defines `review_log` with `confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5)` and `rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4)`.
  - Scans all Python files under `app/` proving zero `UPDATE review_log` or `DELETE FROM review_log` SQL statements.
- **R12 Check (`check_r12`)**:
  - Verifies `create_app` in `app/api.py` rejects wildcard `*` CORS origins at creation.
  - Verifies structural host-and-origin middleware presence (`BrowserSecurityMiddleware`).
  - Parses the route table in `app/api.py` to prove that every non-GET `/vocab` route is guarded by `X-Flashcards-Request: 1`.
- **R13 Check (`check_r13`)**:
  - Verifies candidate dictionary validation and stable semantic reference relinking in `DictionaryRuntime.activate_dictionary`.
  - Verifies stale-token HTTP 409 rejection logic in note capture endpoints.
- **Negative & Positive Control Verification**:
  - `tests/test_check_agents.py` includes 62 tests covering positive controls on clean repositories and negative controls detecting seeded violations:
    - Missing schema file, missing table, missing confidence check, missing rating check, `UPDATE review_log` in app, `DELETE FROM review_log` in app (`test_r6_detects_*`).
    - Missing API file, wildcard origin acceptance, missing middleware marker, uncovered non-GET route (`test_r12_detects_*`).
    - Missing activation ref validation, missing stale-token HTTP 409 rejection (`test_r13_detects_*`).
  - All 62 checker tests pass cleanly.

### 9. Routing Notes & Model Governance

- **Dispatch Routing**: Due to upstream GPT quota exhaustion across the orchestrator fleet, all slice-7 stage dispatches were routed to `gemini-3.7-flash` (medium reasoning effort) under the authorized worker fallback. The `ox-alpha-free` transport was unavailable at the transport layer.
- **Review Protocols**: Reviews were consequently conducted as same-family cold sessions under heightened skepticism protocols, with explicit negative control seeding and exhaustive mechanical proof across every invariant.
- **Pre-Merge Governance**: In accordance with the Risk specification for slice-7 (`migration`, `auth-security`, `public-api`, `data-loss`), a mandatory full-diff review is required before merge closure to main.

### 10. Accepted Stage Commit History

- Stage S1 (`a678f1b`): PART-B user schema tables and FSRS scheduling loop
- Stage S2 (`8cf6367`): Multilingual meaning selection and card rendering
- Stage S3 (`bbf858e`): DictionaryRuntime atomic activation and relinking
- Stage S4 (`3e3e9d8`): Pronunciation audio precedence, custom media, and Piper cache
- Stage S5 (`35c70c9`): App factory, loopback security guards, and `/vocab` API
- Stage S6 (current): Executable AGENTS checks for R6/R12/R13, negative controls, and slice report

### 11. Gate Evidence

> **Note**: The authoritative gate is engine-run in the project's authoritative virtual environment. Local verification numbers recorded during this stage:

- **Ruff**: `ruff check .` -> All checks passed!
- **Mypy**: `mypy --strict .` -> Success: no issues found in 26 source files
- **Pytest**: `pytest -q` -> 664 passed, 56 warnings in 229.44s
- **AGENTS Checker**: `python3 tools/check_agents.py` -> All 6 executable checks passed (`R1`, `R3`, `R6`, `R7`, `R12`, `R13`).
