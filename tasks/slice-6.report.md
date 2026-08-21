# Slice 6 — Attempt 1 / Phase A report

## Scope and input

- Attempt: 1. Phase: A (non-paid).
- Starting main: `2400cec62d6fd0f4e291def59079535f7a4393d6`.
- Accepted Stage-02 role: final cache-MISS asset from slice 5.
- Stage-02 SHA-256: `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`.
- Stage-02 bytes: `945410048`; `PRAGMA quick_check`: `ok`.
- Stage-02 counts: 777295 Tatoeba examples; 494687 with English; 282608
  without English; 6504849 `example_lemma` rows; 99537 indexed lemmas;
  token-count sum 7292286; 0 incomplete-attribution rows; 0 orphan index rows.
- The accepted input was SHA/byte checked before and after Phase A and was not
  mutated.

## Implementation evidence

- Stage 03 is a deterministic, network-free JSONL queue with semantic-only
  durable identities: queue items use lemma/sense semantic refs and hashes of
  relevant source context; local SQLite IDs and filesystem paths are absent.
  Missing-EN jobs are emitted only for senses without an English row; every
  sense receives DE learner-meaning and FA translation candidates.
- Stage 04 is copy-on-write and has no implicit network transport. Phase-A tests
  use injected fake/local deterministic transports only. Candidate schemas are
  validated before checkpoint persistence; therefore arbitrary provider payload
  fields cannot enter the checkpoint. The checkpoint identity includes queue
  hash, generation version, and model-role occupants.
- Validation rejects bad schema/language/kind/text, controls, lemma echoes,
  invalid Persian script, unavailable derivation inputs, and duplicates. The
  selective QA set is deterministic: all soft flags plus a seed derived from the
  queue hash, at one percent with a minimum of one and maximum of 25 audit rows.
- Generated rows are version-marked, hold an explicit generated-output test
  classification, use deterministic ordering, and create only same-sense,
  source-backed derivation edges. A zero-edge job is valid. Generated-to-
  generated edges are rejected. SQL rollback by generation marker cascades only
  its outgoing derivation rows and preserves source rows.
- Stage 05 validates an enriched copy then produces only a new
  `dictionary_vN.sqlite` plus deterministic metadata and provenance summary;
  unsafe overwrite is refused.
- The Docker prerequisite installs `piper-tts==1.6.0`, the required spaCy model,
  and the pinned `de_DE-thorsten-high` voice. Build-time SHA-256 verification,
  the pinned model card, notices, and bounded Piper smoke are in the Dockerfile.
  No pronunciation runtime/API/cache/database/UI or bulk media was added.

## Phase-A real Stage-03 measurement

- Queue records: `960442`.
- Queue SHA-256: `9433f7e236bbf621ff22b0e9ae7b3f350ec4986ec693b0b3408f08fc6ec71ef0`.
- Queue bytes: `914504842`.
- Target-language counts: `de=480221`, `en=0`, `fa=480221`.
- Job-class counts: `de_learner_meaning=480221`, `fa_translation=480221`,
  `missing_en=0`. The accepted source asset had English meanings for every
  sense, so no missing-EN job was applicable.
- Localized derivation-input counts: with text `960442`; without text `0`.
- Queue private-path check: PASS. Queue secret-pattern check: PASS.

## Fake-only Stage 04 / fixture Stage 05

- Transport: fake/local deterministic only. Live provider requests: `0`.
  Paid credits consumed: no.
- Fake Stage-04 E2E: PASS; deterministic validation: PASS; selective QA routing:
  PASS; checkpoint resume and completed-item no-resubmit: PASS; rollback: PASS;
  generated-to-generated derivation count: `0`.
- Stage-05 input class: synthetic/fake-enriched fixture. Fixture packaging:
  PASS. The real dictionary is **not** claimed Stage-04 complete. No release was
  published.

## Container / Piper evidence

- Container CLI: Docker was available (Podman-backed Docker CLI); Podman was
  also available.
- Image build: PASS (`flashcard-slice6-phasea`).
- Runtime dependency inspection: no `anthropic`, `openai`, or `google-genai`
  package was present.
- Piper version pin: `1.6.0`.
- Voice: `de_DE-thorsten-high`; source revision:
  `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8`.
- Model SHA-256:
  `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1`;
  verified during build and runtime inspection.
- Piper runtime presence and bounded `Hallo` synthesis: PASS.
- Notices/classifications recorded and mechanically checked: Piper engine
  GPL-3.0-or-later; Piper voice-repository metadata MIT; Thorsten model-card
  dataset classification CC0.
- Bulk pronunciation media generated: no.

## Test and gate evidence

- Targeted Stage 01–05 regression command: `pytest -q` over the five build
  stage test modules: `107 passed` (Stage 01: 46; Stage 02: 54; Slice-6: 7).
- Pre-commit `git diff --check`: PASS.
- Pre-commit `make gate` exit: `0`.

```text
.venv/bin/ruff check .
All checks passed!
.venv/bin/mypy --strict .
Success: no issues found in 18 source files
.venv/bin/pytest -q
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
..............                                                           [100%]
230 passed in 64.55s (0:01:04)
.venv/bin/python tools/check_agents.py
AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling)
```

Post-commit gate is executed and reported in the machine receipt returned with
this implementation; its complete output is identical in contract scope to the
fresh pre-commit gate above.

## Handoff state

- Changed tracked paths: `tools/build_dict.py`, `tests/test_build_dict_stage03.py`,
  `tests/test_build_dict_stage04.py`, `tests/test_build_dict_stage05.py`,
  `Dockerfile`, `.dockerignore`, and this report.
- Allowlist check: pending final mechanical check before commit.
- Final branch HEAD and push status: pending the authorized commit/push.
- Stop conditions hit: none.

## Deliberately left undone

- paid/live Stage-04 canary;
- full real Stage-04 generation;
- real selective semantic QA;
- final real Stage-05 dictionary packaging;
- release publication;
- runtime pronunciation implementation.
