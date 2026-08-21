# Slice 6 — build stages 03–05: multilingual offline enrichment and packaging

Task:        Implement the maintainer-operated offline dictionary stages 03–05
             required by ADR-0001 §12, ADR-0002 §6 order 7, ADR-0004
             D33–D38/D45, and ADR-0005 D56: deterministic enrichment queue
             construction, multilingual build-time meaning
             generation/validation/QA, final versioned dictionary packaging,
             and the first standalone Dockerfile with the build-time Piper
             engine+voice prerequisite. Phase A ends before any paid full
             Stage-04 generation run.

Depends:     slice-5

## Entry condition

slice-5 must be ACCEPTED, merged, closed, and pushed before implementation
dispatch.

The accepted local Stage-02 asset is a required uncommitted input.

The slice-5 acceptance asset had:

- SHA-256:
  `75658966655bd68729b105dbae1b62f500b30e8e2d08b9689b207f72c4997f97`
- bytes:
  `945410048`
- Tatoeba examples:
  `777295`
- examples with English translation:
  `494687`
- examples without English translation:
  `282608`
- `example_lemma` associations:
  `6504849`
- distinct indexed lemmas:
  `99537`
- Tatoeba token-count sum:
  `7292286`
- incomplete Tatoeba attribution:
  `0`
- orphan `example_lemma` rows:
  `0`

The slice-6 orchestrator supplies:

`STAGE06_STAGE02=<accepted Stage-02 SQLite asset>`

before Attempt 1.

That asset must be verified executable/read-only with:

- exact SHA-256 above;
- exact byte count above;
- `PRAGMA quick_check = ok`;
- expected row counts above;
- required PART-A + Stage-02 tables;
- no mutation of the accepted input during stages 03–05.

If the accepted local Stage-02 asset is absent or differs, STOP. Do not silently
substitute a different dictionary build.

Real Stage-04 API credentials are maintainer-local inputs and are never committed,
printed, copied into reports, written into Docker images, or placed in task files.

## Authority

The binding architecture is:

- ADR-0001 §12, except where superseded;
- ADR-0002 §6 order 7;
- ADR-0004 D33–D38, D45 and §§3–8;
- ADR-0005 D56 (Piper build/runtime prerequisite);
- AGENTS R1 and R11;
- docs/plan.md slice-6 row;
- docs/backlog.md Stage-04 credit deadline.

ADR-0004 is ACCEPTED / FROZEN.

No ADR is reopened by this slice.

The target vocabulary language remains German. DE, EN and FA are learner-meaning
languages only.

Runtime LLM usage remains absolutely forbidden.

## Allowlist

Implementation may modify/create only:

- `tools/build_dict.py`
- `tests/test_build_dict_stage03.py`
- `tests/test_build_dict_stage04.py`
- `tests/test_build_dict_stage05.py`
- `pyproject.toml`
- `Dockerfile`
- `.dockerignore`
- `tasks/slice-6.report.md`

No other tracked path is allowed.

In particular do NOT modify:

- `app/`
- `app/resolve.py`
- `app/dictionary.py`
- `reference/schema.sql`
- Stage-01 or Stage-02 accepted semantics
- existing Stage-01 / Stage-02 tests except through their normal regression runs
- ADRs
- `AGENTS.md`
- `WORKFLOW.md`
- `PROMPTS.md`
- `STATE.md`
- `docs/plan.md`
- `docs/backlog.md`
- user-data/runtime schema
- browser/API/UI code
- pronunciation/audio runtime architecture

Keep these prohibitions:

- no app/runtime pronunciation implementation
- no pronunciation database
- no bulk Piper pre-generation
- no runtime pronunciation API
- no pronunciation selection/cache behavior
- no custom recording/upload persistence
- no human-audio discovery
- no pronunciation UI/browser behavior
- no Stage-04 pronunciation work

No bulk pronunciation/audio database or LLM pronunciation pipeline belongs in
this slice.

## Acceptance

### A1 — CLI stages

Extend the existing maintainer build CLI with separate commands for:

- Stage 03 — deterministic enrichment queue construction;
- Stage 04 — maintainer-only multilingual enrichment;
- Stage 05 — final dictionary packaging.

The exact argument naming is implementation-owned, but the commands must have
clear `--help`, refuse unsafe overwrite, produce nonzero exit on validation
failure, and never mutate their supplied input SQLite asset in place.

Stages must be independently resumable/checkpointable.

No automatic source-data download is introduced.

### A2 — Stage 03 is deterministic and network-free

Stage 03 reads the accepted Stage-02 dictionary asset read-only and produces a
deterministic local enrichment queue.

The queue is the bridge from source-backed dictionary state to ADR-0004 Stage 04.

It must represent at least the Stage-04 job classes:

A. missing English meaning;
B. German learner meaning creation/simplification candidate;
C. Persian translation candidate.

The queue is sense-aware.

Every queue record must carry enough stable semantic identity to survive local
numeric-ID renumbering:

- `lemma.semantic_ref`;
- `sense.semantic_ref`;
- target language;
- generation job class;
- source-backed semantic/context fields needed by ADR-0004;
- identities/provenance of any localized source rows offered as derivation input.

Numeric lemma/sense/meaning IDs may appear only as convenience references to the
specific input asset.

A deterministic queue/item ID must depend on semantic identity and the actual
source/context content relevant to that job, not on mtimes or absolute paths.

Queue ordering is deterministic.

Identical logical input produces logically identical queue output.

Stage 03 performs zero network calls and creates no generated meaning rows.

The deferred Tatoeba `FREQ` feature remains deferred. Do not resurrect it as a
hidden prerequisite.

### A3 — Source-first enrichment

Stage 04 is enrichment over the source-backed dictionary spine.

It must never replace the dictionary with an LLM-generated dictionary.

Existing source-backed `sense`, `sense_meaning`, lemma grammar, IPA, morphology,
Tatoeba examples, and stable semantic refs remain authoritative and unchanged.

A source-backed localized meaning is never rewritten in place merely to simplify
it.

When simplifying source-backed German wording, persist a separate generated row
and preserve the original source row.

### A4 — Multilingual Stage-04 jobs and Persian orthography

Stage 04 supports ADR-0004 §8:

A. fill missing English meanings;
B. create/simplify German learner meanings;
C. create Persian translations;
D. deterministic validation of generated localized meanings;
E. selective stronger-model semantic QA/correction.

German learner meanings follow ADR-0004 D33:

1. prefer one simple/common German synonym when sense-preserving;
2. otherwise one short learner-friendly German explanation;
3. aim roughly at A2–B1 comprehension where practical;
4. never simplify into a semantically different sense.

English remains source-first.

Persian generation is sense-disambiguated and receives deterministic available
context such as lemma, POS, gender where relevant, semantic sense, English
source meaning where available, and German source definition where available.

Persian is stored as plain Unicode.

#### Persian Unicode Policy

The generated Persian text must follow standard Persian orthography and must
never contain bidi direction-manipulation controls.

Ordinary Persian orthography MUST NOT be rejected merely because it contains
`U+200C` ZERO WIDTH NON-JOINER (ZWNJ).

ALLOWED for FA text:

- `U+200C` ZERO WIDTH NON-JOINER (ZWNJ) when used inside otherwise valid Persian
  text.

FORBIDDEN:

- `U+061C` ARABIC LETTER MARK
- `U+200E` LEFT-TO-RIGHT MARK
- `U+200F` RIGHT-TO-LEFT MARK
- `U+202A` LEFT-TO-RIGHT EMBEDDING
- `U+202B` RIGHT-TO-LEFT EMBEDDING
- `U+202C` POP DIRECTIONAL FORMATTING
- `U+202D` LEFT-TO-RIGHT OVERRIDE
- `U+202E` RIGHT-TO-LEFT OVERRIDE
- `U+2066` LEFT-TO-RIGHT ISOLATE
- `U+2067` RIGHT-TO-LEFT ISOLATE
- `U+2068` FIRST STRONG ISOLATE
- `U+2069` POP DIRECTIONAL ISOLATE

Other Unicode control (`Cc`) and format (`Cf`) characters remain forbidden unless
the brief explicitly lists an allowed exception. The validator must not be relaxed
into accepting arbitrary `Cf` characters.

#### Stronger-model Persian QA evaluation

Selective QA for Persian candidates must evaluate:

- semantic fidelity to the source sense;
- preservation of grammatical/inflectional relationships (e.g. inflected forms,
  plural forms, degrees of comparison, tense/person/mood);
- natural idiomatic Persian phrasing;
- learner usefulness;
- correct Persian orthography including legitimate `U+200C` ZWNJ;
- zero forbidden bidi controls.

A structurally valid but unnatural or grammar-losing Persian candidate may be
corrected by QA when selected. QA returns only the final structured candidate,
never chain-of-thought.

### A5 — Offline-only LLM boundary and per-language model roles

AGENTS R1 remains absolute.

No LLM SDK may enter:

- `[project].dependencies`;
- `app/`;
- the Docker runtime dependency graph.

If an SDK is useful for the maintainer build, it may be placed only in a
build-only optional dependency group in `pyproject.toml`.

The only code permitted to read an LLM API credential is the Stage-04 path in
`tools/build_dict.py`.

The credential is read at execution time from the maintainer environment.

Never:

- print it;
- persist it;
- put it in command output/report text;
- put it in checkpoints;
- write it to Docker layers;
- commit it.

Tests use a fake/mock transport and require no credential/network.

#### Per-language bulk model roles

Stage 04 must allow configuring model occupants separately for at least:

- `bulk DE` (German learner meaning bulk model);
- `bulk EN` (English translation bulk model);
- `bulk FA` (Persian translation bulk model);
- `semantic QA` (selective semantic QA / correction model).

Operational model product names remain operational configuration, NOT
architecture. The non-normative initial baseline defaults are:

- bulk DE: `gpt-5.6-luna`;
- bulk EN: `gpt-5.6-luna`;
- bulk FA: to be decided by canary comparison and explicit approval (A15);
- semantic QA: `gpt-5.6-terra`.

Checkpoint compatibility must include every configured model role that can
materially affect its corresponding generated output.

Changing the FA bulk model must invalidate incompatible FA generation state and
prevent silent reuse of incompatible FA completed results.

Do not hard-code a permanent FA provider/model into the architecture.

### A6 — Structured generation, checkpoint/resume, and paid-response state machine

Paid generation must be resumable.

Every generation item has a stable deterministic identity.

Completed provider responses/results and rejected paid results are checkpointed in
maintainer-local, ignored build storage so interruption does not rebill completed
work.

A restart must:

- reuse exactly matching completed work;
- not duplicate meaning rows;
- not resubmit completed queue items;
- not automatically resubmit rejected items without explicit authorization;
- fail closed on corrupt/incompatible checkpoint state.

Changing any material generation input — prompt/pipeline semantics, generation
version, queue content, configured model role occupants (per-language bulk model
or QA model) — must not silently reuse an incompatible checkpoint. Incompatible
reuse explicitly includes:

- generated-output license/classification;
- bulk prompt/pipeline version;
- QA prompt/pipeline version;
- configured bulk model for that language role;
- configured QA model role;
- any provider-response schema/version that materially changes interpretation.

Do not make transport batch size part of durable semantic identity unless batch
size itself changes the prompt/result semantics.

The generation version is explicit.

First live generated rows use:

`source='llm_generated_v1'`

unless the slice-6 orchestrator explicitly authorizes a successor marker before
the real run.

#### Paid-response state machine and bounded durability

The live Stage-04 transport must expose paid work to the checkpoint layer in
deterministic bounded units.

It is not acceptable for `run_stage04` to hand the entire remaining real queue
to an opaque provider transport and checkpoint only after all pending provider
work has returned.

The checkpoint layer must strictly distinguish two distinct conditions:

A. **IN_FLIGHT (Ambiguous request outcome):**
   A request unit was transmitted over transport and no complete usable provider
   response outcome is known (e.g. transport, network, timeout, or process failure
   before a complete usable response was received).
   - In this state, retain `in_flight` IDs in the checkpoint;
   - STOP immediately;
   - Never automatically resubmit or clear in-flight IDs.

B. **RETURNED RESPONSE (Complete provider response received):**
   The provider returned a complete response for the exact requested item-ID set.
   The request is complete and may have been billed by the provider.

For a complete returned bounded unit:

1. Validate each returned candidate independently;
2. Candidates that pass deterministic validation become durable **completed**
   candidates;
3. Candidates that fail deterministic validation become durable **rejected**
   (validation-failed) paid results;
4. Atomically persist that per-item result state to the maintainer-local
   checkpoint;
5. Clear the request's `in_flight` state because provider completion is no longer
   ambiguous;
6. If any candidate in that unit was rejected, STOP before submitting another
   paid bounded unit;
7. Restart MUST NOT automatically resubmit rejected IDs;
8. A single invalid candidate must not erase, discard, or hide valid paid
   candidates returned from the same bounded batch.

Bulk generation and selective QA are BOTH paid-work phases for the purposes of
resume safety.

#### Durable rejected state

Checkpoint state must explicitly and durably represent rejected paid results.

For each rejected item, preserve at least:

- item ID;
- phase (`bulk` or `qa`);
- deterministic / sanitized validation error code;
- paid attempt count;
- sufficient non-secret metadata to prove the item was returned and rejected.

Do not require persistence of raw unsafe provider text merely for diagnostics.

Rejected state must be structurally validated on checkpoint load. Corrupt or
malformed rejected state fails closed.

Rejected IDs are NOT pending normal work. They may not be automatically
resubmitted on normal restart.

#### Explicit retry of rejected work

A knowingly authorized paid retry is distinct from accidental automatic
resubmission.

A rejected item may be retried ONLY when the orchestrator explicitly authorizes
the exact rejected item IDs via a deterministic explicit recovery mechanism (such
as a maintainer-local retry manifest or explicit CLI option).

Explicit retry requirements:

- Exact item IDs explicitly authorized;
- Prior rejected state preserved / recorded;
- Durable paid-attempt count increments;
- No wildcard "retry everything";
- No implicit retry on ordinary restart;
- No retry of genuinely ambiguous `in_flight` work;
- Every retry remains checkpointed under compatible run identity.

#### Legacy first-canary checkpoint preservation

The existing first-canary checkpoint predates the repaired rejected-state
semantics. Its five current `bulk.in_flight` IDs remain LEGACY UNRESOLVED.

The implementation MUST NOT automatically reinterpret, clear, migrate, or
resubmit those five IDs.

The first canary is retired as failure evidence. Preserve its checkpoint and
artifacts locally. After repaired implementation acceptance, the orchestrator
will authorize a fresh deterministic canary-v2 rather than rewriting old paid
state.

### A7 — Generated-row provenance and derivation

Every persisted generated `sense_meaning` row has:

- non-empty `source`;
- non-empty `license`;
- correct target language;
- valid kind;
- deterministic ordering metadata.

Generated rows must never masquerade as source-backed rows.

For every source-backed localized meaning TEXT actually consumed as generation,
simplification, or semantic-QA derivation input, write the corresponding
`sense_meaning_derivation` edge.

Validate that:

- generated side points to a versioned generated row;
- source side points to a non-generated source-backed localized row;
- both rows belong to the same sense;
- generated→generated edges do not exist;
- duplicate derivation pairs do not exist.

A generated job that consumes only source-backed sense/grammar/context fields
and no localized source text may legitimately have zero derivation edges.

If the implementation would require generated→generated provenance chains,
STOP rather than inventing them.

QA/correction occurs before the final generated row is persisted; it does not
create a generated→generated lineage.

### A8 — Generated output license is explicit

Do not invent a blanket license for generated output.

The live Stage-04 run requires an explicit maintainer-approved generated-output
license/classification input.

If the build cannot establish a distribution/license classification compatible
with applicable linked upstream obligations, STOP.

Source-backed localized rows retain their original source/license.

Generated rows retain the generation marker as `source`; they are not relabeled
as Wiktionary.

### A9 — Deterministic validation precedes semantic QA

Every generated candidate is deterministically validated before stronger-model
QA selection.

Validation covers at minimum:

- structured response/schema conformance;
- allowed language/kind;
- nonblank text;
- length bounds;
- duplicate detection;
- obvious echo-the-lemma failures;
- Persian-script expectation for FA;
- Persian Unicode validation:
  - ALLOWED: `U+200C` ZERO WIDTH NON-JOINER (ZWNJ) in valid Persian text;
  - FORBIDDEN: bidi controls `U+061C`, `U+200E`, `U+200F`, `U+202A`–`U+202E`,
    `U+2066`–`U+2069`;
  - FORBIDDEN: general control characters (`Cc`) and unallowed format characters
    (`Cf`);
- German-language plausibility checks for DE;
- forbidden/control-content checks;
- derivation/provenance consistency.

The exact safe thresholds/heuristics are implementation-owned and golden-tested.

Validation output deterministically defines the suspicious/flagged set.

Semantic QA receives:

- every deterministically flagged candidate;
- plus a deterministic small random audit sample.

The random audit selection must be reproducible from recorded deterministic
seed/input identity.

QA is selective, never every row by default.

Selective QA prompt for Persian enforces:

- semantic fidelity;
- preservation of grammatical/inflectional relationships;
- natural idiomatic Persian phrasing;
- learner usefulness;
- correct Persian orthography including legitimate ZWNJ;
- zero forbidden bidi controls.

Record actual queue size, validation flags, QA sample size, correction counts,
and rejected item counts in the report. ADR-0004 deliberately defines no fixed
percentage acceptance threshold.

### A10 — Clean rollback

Generated data must remain cleanly reversible by generation marker.

Tests must prove that rollback equivalent to:

`DELETE FROM sense_meaning WHERE source='llm_generated_v1'`

removes generated rows and their outgoing derivation edges while preserving all
source-backed localized meanings.

Source rows referenced by live generated derivation edges must not be silently
deleted.

### A11 — Stage 05 final packaging

Stage 05 consumes a completed validated enriched dictionary copy and produces a
new versioned distributable package.

For the first accepted release target, support a semantic dictionary filename
such as:

`dictionary_v1.sqlite`

Stage 05:

- never overwrites an existing packaged version;
- never mutates its input asset;
- validates SQLite `PRAGMA quick_check`;
- validates required tables;
- validates stable lemma/sense semantic-ref uniqueness/nonblankness;
- validates localized-meaning attribution;
- validates generated derivation integrity;
- validates zero orphan example/meaning/derivation rows;
- records output SHA-256 and byte size;
- emits deterministic machine-readable release metadata containing at least
  version, filename, SHA-256 and bytes;
- emits checksum/attribution material sufficient to reconstruct the mixed
  Wiktionary/Tatoeba/generated provenance represented in the asset.

Do not publish a GitHub Release in Phase A.

Release publication is an operational action requiring separate orchestrator
authorization after the final real enriched asset is accepted.

Do not commit the packaged SQLite asset.

### A12 — Dockerfile and Piper build prerequisite

Create the first standalone `Dockerfile` required by ADR-0002 §6 order 7 and
ADR-0005 D56.

The Docker acceptance contract requires:

- existing Python/runtime foundation and `de_core_news_md`;
- `piper-tts==1.6.0` pinned in the runtime image;
- selected voice `de_DE-thorsten-high` pinned to source revision
  `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8`;
- model SHA-256
  `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1`;
- image build verifies the expected model digest;
- engine and voice are present at runtime;
- a bounded smoke invocation proves Piper can synthesize with the selected
  voice/model inside the built image;
- build/release evidence records engine classification GPL-3.0-or-later,
  separate voice-repository MIT metadata and Thorsten-Voice model-card dataset
  classification CC0, plus required notices/attribution;
- conflicting, missing, or unverifiable upstream artifact metadata is a STOP,
  not a guessed license conclusion;
- no runtime LLM SDK/API key/build cache/user DB enters the image;
- no bulk pronunciation media is generated or baked in.

The future worker may decide ordinary Docker implementation details, but it may
not choose a different engine/voice/identity/license policy without governance.

This addition is the build/runtime prerequisite only; slice-6 must not add:

- app/runtime pronunciation implementation;
- a pronunciation database;
- bulk Piper pre-generation;
- a runtime pronunciation API;
- pronunciation selection/cache behavior;
- custom recording/upload persistence;
- human-audio discovery;
- pronunciation UI/browser behavior;
- Stage-04 pronunciation work.

Loopback publication/CORS/API runtime behavior remains owned by later runtime
slices.

If available in the authoritative local environment, use Podman or Docker to
prove the image builds.

### A13 — Phase-A tests

Tests cover at minimum:

Stage 03:
- deterministic queue IDs/order;
- input-order independence where relevant;
- missing-EN classification;
- DE learner-meaning job classification;
- FA job classification;
- stable refs rather than numeric IDs as durable queue identity;
- no network;
- no input SQLite mutation;
- overwrite refusal.

Stage 04:
- fake structured bulk response;
- fake QA response;
- no live network in tests;
- generated source marker;
- explicit generated license;
- source-backed rows unchanged;
- DE/EN/FA row persistence;
- derivation edges exact;
- zero-edge valid case;
- generated→generated rejection;
- deterministic validation;
- Persian with legitimate `U+200C` ZWNJ passes validation;
- Persian with prohibited bidi controls (`U+061C`, `U+200E`, `U+200F`, `U+202A`–`U+202E`, `U+2066`–`U+2069`) fails validation;
- ordinary control characters/newlines where forbidden fail validation;
- complete five-item provider response with four valid + one invalid:
  - four valid candidates become completed;
  - one invalid candidate becomes durable rejected;
  - `in_flight` clears;
  - execution STOPs before submitting the next paid request;
- restart does not resubmit completed or rejected IDs;
- transport failure with unknown provider outcome keeps `in_flight` and fails closed;
- explicit retry manifest is required to retry rejected IDs;
- retry manifest cannot authorize `in_flight` IDs;
- explicit rejected retry increments durable paid-attempt state;
- per-language DE/EN/FA model roles participate correctly in checkpoint compatibility;
- FA model change cannot silently reuse incompatible FA completed state;
- Persian QA prompt includes naturalness, grammatical/inflectional preservation, and ZWNJ/bidi requirements;
- legacy first-canary in-flight checkpoint is not silently cleared or migrated;
- suspicious-row routing;
- deterministic audit sample;
- checkpoint resume;
- completed-item no-resubmit;
- corrupt checkpoint fails closed;
- rollback preserves source rows;
- API secret never written/logged;
- partial bulk interruption after at least one completed bounded unit;
- restart after partial bulk interruption submits zero already-checkpointed bulk item IDs;
- resumed bulk run produces the same logical generated result set as an uninterrupted equivalent run;
- partial selective-QA interruption after at least one completed QA unit;
- restart after partial QA interruption submits zero already-checkpointed QA item IDs;
- resumed QA run produces the same logical corrected result set as an uninterrupted equivalent run;
- bulk completed, rejected, and QA completion states are independently represented in checkpoint state;
- corrupt partial bulk checkpoint fails closed;
- corrupt partial QA checkpoint fails closed;
- incompatible generated-output classification invalidates checkpoint reuse;
- incompatible bulk prompt/pipeline version invalidates checkpoint reuse;
- incompatible QA prompt/pipeline version invalidates checkpoint reuse;
- mocked tests make zero live requests.

Tests must use fake/local deterministic transports only.

No provider credential or network is used by these tests.

The fake transport used for interruption testing must be able to:

1. successfully complete and expose at least one bounded unit;
2. deliberately fail afterward;
3. permit restart from the persisted partial checkpoint;
4. record exact submitted item IDs so no-resubmit is mechanically asserted.

The test must track BOTH bulk submission IDs and QA submission IDs.

A test that only performs one complete run followed by a second complete run is
not sufficient evidence of interruption safety.

Stage 05:
- validation success;
- malformed/generated provenance rejection;
- duplicate stable-ref rejection;
- bad attribution rejection;
- input asset unchanged;
- overwrite refusal;
- metadata/checksum consistency.

Docker / Piper prerequisite:
- image build succeeds when container tooling is available;
- runtime dependency inspection proves no LLM SDK;
- mechanical evidence of the Piper pin, digest, presence, invocation, and recorded classification/notices.

All prior Stage-01 and Stage-02 regressions remain passing.

`make gate` remains green.

### A14 — Mandatory Phase-A real execution

Attempt 1 does NOT perform the paid full Stage-04 run.

Against the accepted real Stage-02 asset:

1. verify input SHA/bytes/counts/quick_check;
2. execute real Stage 03;
3. record total deterministic queue size;
4. record counts by:
   - target language;
   - job class;
   - availability of source-backed localized derivation text;
5. record the queue SHA-256 and bytes;
6. validate that queue output contains no secrets/private paths;
7. exercise Stage-04 end-to-end only with fake/local deterministic transport;
8. exercise Stage 05 on a synthetic or fake-enriched fixture, not by pretending
   the real dictionary has already completed Stage 04;
9. build/inspect the Dockerfile when local container tooling is available;
10. run all targeted tests and full `make gate`.

If real Stage-03 queue construction shows a contract ambiguity requiring an ADR
decision, STOP and return to the orchestrator.

### A15 — Paid-run authorization boundary, Persian Quality Gate, and Canary-v2

After Phase-A implementation and real Stage-03 queue measurement, STOP.

Do NOT:

- submit the full queue to an LLM provider;
- consume the owner's Stage-04 credits;
- perform a paid canary without explicit authorization;
- run selective real QA without explicit authorization;
- claim the final real dictionary is Stage-05 complete;
- publish a release.

The Phase-A worker returns measured queue evidence to the orchestrator.

The orchestrator then decides the exact live Stage-04 execution scope and
authorizes any paid canary/full run explicitly.

That continuation remains within the same WORKFLOW attempt when no code/design
change is required.

#### Persian full-run quality gate

Before the full Stage-04 run, the orchestrator must explicitly approve the
Persian bulk model based on live evidence.

A fresh deterministic canary-v2 must exercise Persian lexical AND
grammatical/inflectional senses.

The evidence returned for each FA candidate must include:

- lemma;
- POS;
- exact source English meaning/context;
- generated Persian;
- whether the source meaning represents an inflection/form relation;
- model role occupant;
- derivation IDs;
- whether stronger QA selected/corrected it.

The orchestrator manually evaluates at minimum:

- exact sense preservation;
- preservation of grammatical/inflectional relationships;
- natural Persian phrasing;
- learner usefulness;
- correct Persian script/orthography;
- no bidi-control abuse.

The full FA run is blocked until the orchestrator explicitly records:

`PERSIAN BULK MODEL APPROVED: <configured model>`

Neither Luna nor Terra is presumed approved in advance; the canary decides.

Selective QA remains selective as required by A9 (never every row by default).

#### Canary-v2 model comparison

The next live canary must permit a small controlled comparison of candidate FA
bulk model occupants on the SAME deterministic semantic sample (for example, Luna
vs a stronger candidate).

This comparison is a separately bounded paid canary, not the production run.

Canary-v2 comparison requirements:

- same semantic inputs;
- same prompt/pipeline semantics;
- model occupant recorded per run;
- outputs shown side-by-side for review;
- exact request/job caps;
- no production expansion until manual approval.

#### Full-run blockers

The 960,442-job real production run remains strictly prohibited until ALL of the
following are true:

1. Repaired implementation accepted;
2. All repaired A13 tests green;
3. Fresh canary-v2 completes without unresolved paid state;
4. Persian model comparison reviewed;
5. Orchestrator explicitly approves the FA bulk model (`PERSIAN BULK MODEL APPROVED: <model>`);
6. DE/FA semantic sample accepted;
7. Selective QA actually executes successfully;
8. Generated-output classification remains approved;
9. Credential handling remains compliant;
10. Explicit orchestrator authorization for the full run is issued.

No worker may infer full-run authorization merely because a canary passes.

### A16 — Report

Create `tasks/slice-6.report.md`.

Record only executable evidence.

Phase-A report includes:

- accepted Stage-02 input SHA/bytes/counts;
- Stage-03 queue SHA/bytes;
- total queue records;
- queue counts by language/job class;
- counts with/without localized derivation inputs;
- implementation decisions not fixed by ADRs;
- build-only provider/SDK boundary, if any;
- deterministic validation rules implemented;
- checkpoint/resume evidence;
- rollback evidence;
- Stage-05 fixture packaging evidence;
- Docker build/runtime-dependency evidence;
- mechanical evidence of the Piper pin, digest, presence, invocation, and recorded classification/notices;
- targeted test counts;
- Stage-01 regression count;
- Stage-02 regression count;
- full `make gate` count;
- `git diff --check`;
- exact changed paths;
- final branch HEAD;
- push status;
- exact Stop-and-ask conditions hit;
- work left undone;
- bulk transport bounded-unit policy;
- partial bulk interruption point;
- exact bulk item IDs submitted before failure;
- exact already-completed bulk IDs skipped on restart;
- partial QA interruption point;
- exact QA item IDs submitted before failure;
- exact already-completed QA IDs skipped on restart;
- proof resumed logical result equals uninterrupted logical result;
- checkpoint schema/version;
- checkpoint identity components;
- proof bulk completed, rejected, and QA completion states are independently durable;
- generated-output classification included in checkpoint compatibility identity;
- durable rejected state counts, validation error breakdown, and explicit retry manifest verification;
- per-language bulk model occupants recorded;
- Persian ZWNJ and bidi-control test results;
- verification of legacy first-canary preservation.

Do not record:

- API keys;
- credential fragments;
- private absolute paths;
- speculative unmeasured coverage/cost as fact.

## Stop-and-ask

STOP and return to the slice-6 orchestrator if:

- `Depends: slice-5` is not merged/closed;
- the accepted Stage-02 input is missing or differs;
- satisfying the task requires modifying `app/`, runtime/user schema, ADRs,
  `reference/schema.sql`, AGENTS, WORKFLOW, STATE, or another path outside the
  allowlist;
- Stage-03 queue semantics cannot be reconciled with accepted ADR-0004 without a
  new architecture decision;
- Stage-04 would require runtime LLM/API dependency;
- a provider secret would need to be committed, printed or written to an image;
- provenance cannot satisfy D45/R11;
- output-license classification cannot be established without erasing upstream
  obligations;
- generated→generated derivation would be required;
- deterministic validation cannot fail closed;
- checkpoint/resume cannot avoid duplicate paid submission;
- the accepted Stage-02 asset would need in-place mutation;
- Stage 05 would overwrite an existing dictionary release;
- STOP if satisfying the Piper prerequisite requires any runtime pronunciation
  feature, API/cache/database/custom-media/human-discovery/UI work, a different
  unpinned artifact, or an architecture/license decision not fixed by ADR-0005;
- any mandatory gate/test fails;
- Phase A reaches the paid-run boundary.

STOP if:

- transport failure leaves provider call outcome ambiguous (`in_flight` retained);
- any candidate in a returned unit is rejected before submitting another paid bounded unit;
- restart would automatically resubmit rejected IDs without explicit authorization;
- legacy first-canary `bulk.in_flight` state would be cleared, migrated, or resubmitted;
- full FA run is attempted before explicit `PERSIAN BULK MODEL APPROVED: <configured model>` record;
- arbitrary `Cf` format characters are accepted or forbidden bidi controls are not rejected;
- successfully billed bulk work can complete without becoming durably
  checkpointed before later paid work;
- successfully billed selective-QA work can complete without becoming durably
  checkpointed before later paid QA work;
- restart can resubmit any compatible completed bulk item;
- restart can resubmit any compatible completed QA item;
- the transport abstraction hides partial paid completion from the checkpoint
  layer;
- interruption/resume requires guessing whether provider work already completed.

Do not solve a Stop-and-ask condition by changing architecture.

## Risk

Risk: none

## Why-risk

WORKFLOW §6 path lookup: the allowlist contains maintainer-only offline build
tooling, tests, build-only dependency metadata, a Dockerfile, `.dockerignore`,
and the slice report. It touches no user-data migration, auth/security path,
externally callable application API, or destructive transform of an existing
accepted artifact. Every dictionary stage consumes an accepted asset read-only
and publishes a new local artifact.

## Model

Model: gpt-5.6-terra / T3 / high

## Why

WORKFLOW §4:

- Stage 04 establishes the project's paid offline structured-generation,
  deterministic-validation, selective-QA and resumable-checkpoint pattern;
- provenance/license errors can remain internally self-consistent while being
  legally or semantically wrong;
- Stage 05 establishes the reusable final dictionary packaging pattern;
- multiple cross-cutting accepted ADR constraints must remain aligned.

Novelty and judgment therefore route to T3.

## Fallback

Fallback: opus-5 / T3 / high

No lower-tier fallback is authorized.

## Phase-A disposition

Attempt 1 ends after:

- implementation;
- real Stage-03 queue measurement;
- fake-transport Stage-04 verification;
- fixture Stage-05 packaging;
- Docker verification;
- tests/gate;
- report commit/push.

It does not spend Stage-04 API credits.

The orchestrator must explicitly authorize the next live generation step.
