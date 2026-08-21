# Slice 6 — Phase A implementation and acceptance remediation

## Attempt history and disposition

- Attempt 1 implementation commit: `a03cb6b1364d493d4443dc68448a8153e024dbbe`.
- Attempt 1 completed non-paid implementation, real Stage-03 measurement,
  fake-only Stage-04 E2E, fixture Stage-05 packaging, container smoke, and
  green gates. Orchestrator acceptance classified it as **Failure 1** because
  A13 coverage was incomplete, this durable report retained stale fields, and
  A12 GPL/MIT evidence was not fail-closed. It was not a runtime or gate failure.
- Attempt 2 remediates those A12, A13, and A16 gaps. Its report-finalization
  commit and push identity are supplied by the mechanical worker receipt; this
  report deliberately does not claim a self-referential commit SHA.
- Branch evidence head before report finalization:
  `a03cb6b1364d493d4443dc68448a8153e024dbbe`; branch: `slice/6`.
- Attempt-2 Stage-03 production semantics changed: **no**. The valid Attempt-1
  real measurement is therefore reused unchanged.

## Accepted Stage-02 input and preserved measurement

- SHA-256: `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`.
- Bytes: `945410048`; `PRAGMA quick_check`: `ok`.
- Counts: 777295 Tatoeba examples; 494687 with English; 282608 without English;
  6504849 `example_lemma` rows; 99537 indexed lemmas; token-count sum 7292286;
  zero incomplete-attribution rows; zero orphan index rows.
- Input hash and bytes were verified after both attempts; the supplied asset was
  not mutated.
- Real Stage-03 queue: 960442 records; SHA-256
  `9433f7e236bbf621ff22b0e9ae7b3f350ec4986ec693b0b3408f08fc6ec71ef0`;
  bytes `914504842`.
- Queue language counts: `de=480221`, `en=0`, `fa=480221`.
- Queue job counts: `de_learner_meaning=480221`, `fa_translation=480221`,
  `missing_en=0`; all source senses already had English meanings.
- Localized derivation-input counts: with text `960442`; without text `0`.
- Queue private-path and secret-pattern checks: PASS.

## Attempt-2 remediations

- A13 coverage is now focused and executable: Stage 03 proves semantic identity,
  stable ordering, numeric-ID/insertion-order independence, no network, no input
  mutation, all three job classifications, and overwrite refusal. Stage 04
  proves fake bulk/QA behavior, no implicit transport, generated DE/EN/FA rows,
  exact and zero derivations, deterministic suspicious/audit identities,
  checkpoint rejection/reuse, no-resubmit, rollback, and secret-bearing response
  rejection before checkpoint or output persistence. Stage 05 proves package
  success, attribution and blank-ref rejection, malformed generated provenance
  rejection through its validation boundary, duplicate lemma/sense stable-ref
  rejection, input immutability, overwrite refusal, and metadata consistency.
- Stage 05 now explicitly verifies duplicate semantic references in addition to
  SQLite schema constraints.
- The image now mechanically verifies GPL-3.0-or-later from installed
  `piper-tts==1.6.0` distribution metadata; retrieves immutable metadata from
  the pinned Piper voice revision and requires matching revision SHA plus MIT;
  and retrieves the pinned Thorsten model card and requires CC0. The verified
  source artifacts and derived notices remain in the image.

## Phase-A boundary and generated-data evidence

- Stage 04 transport remains fake/local deterministic only. Live provider
  requests: `0`; paid credits consumed: no; no credential was inspected.
- Generated rows use `llm_generated_v1`, explicit test-only classification in
  fixtures, deterministic ordering, source-backed same-sense derivation only,
  and no generated-to-generated links. SQL rollback preserves source rows.
- Fake Stage-04 E2E, deterministic validation, selective QA routing,
  checkpoint resume/no-resubmit, and rollback: PASS.
- Stage 05 exercised only a synthetic/fake-enriched fixture. The real dictionary
  is not claimed Stage-04 complete, no release was published, and no bulk
  pronunciation media was generated.

## Container / Piper evidence

- Available tooling: Docker (Podman-backed Docker CLI) and Podman.
- Rebuild command: `docker build --progress=plain -t flashcard-slice6-phasea-attempt2 .`.
  Result: PASS.
- Piper: `piper-tts==1.6.0`; voice `de_DE-thorsten-high`; revision
  `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8`; model SHA-256
  `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1`.
- Engine license: PASS — installed pinned distribution metadata exactly equals
  `GPL-3.0-or-later`.
- Voice-repository license: PASS — pinned revision metadata has matching SHA and
  `cardData.license == mit`.
- Thorsten model/dataset license: PASS — pinned `MODEL_CARD` contains
  `License: CC0`.
- Runtime inspection: selected model exists with the required digest; Piper
  bounded synthesis PASS; required notices present; no `anthropic`, `openai`, or
  `google-genai` runtime package exists.

## Test and gate evidence

- A13 focused command:
  `pytest -q tests/test_build_dict_stage03.py tests/test_build_dict_stage04.py tests/test_build_dict_stage05.py`:
  `16 passed`.
- Stage-01 through Stage-05 regression command: `116 passed` (Stage 01: 46;
  Stage 02: 54; Stage 03: 4; Stage 04: 6; Stage 05: 6).
- Attempt-2 pre-commit `git diff --check`: PASS.
- Attempt-2 pre-commit `make gate`: PASS; 239 tests. A fresh committed-tree gate
  is required and recorded in the mechanical receipt after the finalization
  commit.

## Final scope and outstanding work

- Changed tracked paths relative to Attempt 1: `tools/build_dict.py`,
  `tests/test_build_dict_stage03.py`, `tests/test_build_dict_stage04.py`,
  `tests/test_build_dict_stage05.py`, `Dockerfile`, and this report.
- Allowlist: PASS. `git diff --check`: PASS. No generated SQLite/DB/queue,
  checkpoint, model cache, credential, or private absolute path is committed.
- Local/remote equality and push result are recorded in the final mechanical
  receipt; this report contains no unfinalized status field.
- Stop conditions hit: none.
- Deliberately not done: paid/live Stage-04 canary; full real generation; real
  semantic QA; final real Stage-05 package; release publication; runtime
  pronunciation implementation.
