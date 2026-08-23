# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE from repository/gate evidence.

## What landed

* **slice-0 through slice-6 are accepted, merged and closed.**
  - slice-0 established repository/gate governance.
  - slice-1 landed the canonical resolver/read-only dictionary boundary.
  - slice-2 locked Gate 1.
  - slice-3 landed deterministic Stage-01 plus ADR-0004 PART-A alignment.
  - slice-4 completed Gate 2 at **198/200 = 99.00% → CONTINUE** after the one authorized deterministic remedy.
  - slice-5 completed deterministic Stage-02 Tatoeba indexing.
  - slice-6 completed the maintainer-side Stage-03/04/05 infrastructure and Piper/Docker build prerequisite.

* **Accepted Stage-02 remains the source-backed runtime dictionary baseline.**
  SHA-256:
  `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`
  with 777295 examples and 6504849 `example_lemma` associations.
  It remains immutable source-backed input for later work.

* **Slice-6 Stage-03/04/05 infrastructure is accepted.**
  Deterministic queue construction, offline-only structured generation tooling,
  validation/QA, checkpoint/resume, spend fencing, Batch manifest/correlation,
  fail-closed recovery, Stage-05 packaging machinery, and the pinned Piper
  image-build prerequisite are implemented and gate-tested.
  Runtime LLM usage remains forbidden.

* **German Canary v4 is accepted as historical validation evidence.**
  Final independent semantic result after two explicit manual adjudications:
  **48 PASS / 2 MINOR / 0 MATERIAL — PASS_WITH_2_MINOR**.
  The two manual adjudications were:
  - `Marmarameer` → `Marmarameer`
  - `Mod` → `Mod`
  Historical German v4 provider spend is **USD 0.0716368**.
  Manual rows remain explicitly distinguished from provider-generated rows.

* **Full paid Stage-04 German production is deliberately deferred from v1.**
  Production planning proved full-coverage LLM enrichment economically and
  operationally disproportionate for v1. No full production Batch was executed
  and no production authorization exists.
  Paid enrichment remains optional future maintainer work, not a prerequisite
  for the standalone v1 application.

* **v1 proceeds source-first and permits incomplete German learner-meaning coverage.**
  Existing source-backed data, deterministic grammar/morphology, existing English
  meanings, and suitable source-backed German meanings are used when available.
  Missing German learner meanings remain unavailable/partial under ADR-0004 D43;
  they are never invented or generated at runtime.

* **ADR-0004, ADR-0005, ADR-0006 and ADR-0007 remain ACCEPTED / FROZEN.**
  Persian remains deferred from active v1 scope under ADR-0007.
  Active meaning languages are `{de, en}`.

* **Two-authority workflow remains binding.**
  Local Git/terminal is authoritative for working-tree/runtime/gate/local-asset
  facts. Private `origin` is the persistent authoritative mirror for committed
  and pushed state.

## Gate

* Slice-6 pre-closure preparation reported `make gate` PASS at accepted
  `slice/6 = 09384cd1fd23ee01a4bcf2f0d0ee791361e5f4a4`.
* Slice-6 is `Risk: none`; no WORKFLOW §6 risk full-diff review is required.
* Closure must run a fresh final `make gate` on merged `main`; authoritative
  stdout/stderr is stored in `handoff/main-gate.txt`.

## Escalation status

* **none active.**
* Historical Slice-6 provider/canary stops and design repairs are preserved in
  `tasks/slice-6.report.md`; no retry or paid execution remains pending.
* Full paid Stage-04 production is a deferred optional capability, not an active
  escalation or blocker.

## Sessions since last audit

* 7

## Blocked

* **ADR-0004 PART-B/runtime work is owned by slice-7.**
  This includes DE/EN meaning selection and D43 availability, note-local user
  meanings, durable semantic dictionary bindings, active dictionary version/SHA,
  D47 activation/relink semantics, stale-picker handling, and runtime rendering.

* **`reference/smoke_test.py` repair remains owned by slice-8.**

* **Compose integration remains blocked** by the lecture app's Phase-4
  decomposition and required donor evidence; slice-9 owns that boundary.

* **ADR-0002 D27 / ADR-0003 D27 identifier collision** remains naming debt only.

## Next three actions

1. Open a fresh Slice-7 orchestrator against the final merged `main`; formally
   verify startup and `Depends: slice-6`.
2. Execute `tasks/slice-7.md`. Full paid Stage-04 generation is explicitly NOT
   an entry condition; partial/absent DE learner-meaning coverage must work
   according to D43 and no runtime LLM is permitted.
3. Because Slice-7 is risk-labeled `migration, auth-security, public-api,
   data-loss`, perform its required T3 full-diff risk review before Slice-7 merge
   and closure.
