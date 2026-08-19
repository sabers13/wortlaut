# AGENTS — conventions and prohibitions. Every rule states the defect that caused it.

Rules marked `[executable]` are (or will be) enforced by a `make gate` check;
`[reviewed]` rules rely on review. Converting reviewed → executable is standing
backlog work.

## Prohibitions

- **R1 — No LLM at runtime, in any code path.** `[executable]` No LLM SDK
  (`anthropic`, `openai`, `google-genai`, …) may appear in the runtime dependency
  graph (`pyproject.toml` runtime deps, `app/` imports). The only permitted key
  location in the whole project is `tools/build_dict.py` stage 04, run by hand on
  the maintainer's machine.
  *Defect prevented:* an offline app silently grows a network failure path and
  ships an API key (ADR-0001 D1). Gate check: scan runtime deps and `app/` imports.

- **R2 — Exactly one resolver.** `[reviewed]` `app/resolve.py` is the only
  lemma-resolution implementation. The Tatoeba indexing stage (build stage 02)
  imports it; it never reimplements it.
  *Defect prevented:* divergent separable-verb logic between the example index and
  live lookup fails silently and self-consistently — lookups succeed, results are
  wrong, nothing surfaces it (ADR-0001 D3, Gate 1).

- **R3 — Build-cache keys include the resolver hash.** `[executable]` Any cached
  stage-02 artifact is keyed on a SHA-256 of `app/resolve.py`.
  *Defect prevented:* fixing the resolver and rebuilding silently reuses an index
  built with the broken logic — the bug resurrected by caching (ADR-0001 §12).

- **R4 — Rendered card faces are never stored.** `[reviewed]` Cards are structured
  fields plus nullable user overrides; front/back are rendered at display time.
  *Defect prevented:* every new field or template tweak becomes a data migration
  over the user's whole collection (ADR-0001 D8).

- **R5 — Never cascade-delete a note that has review history.** `[reviewed]`
  Deck deletion removes membership rows; orphaned notes move to an "Orphaned"
  deck.
  *Defect prevented:* deleting a lecture destroys months of FSRS history
  (ADR-0001 D12/§5).

- **R6 — `review_log` is append-only and logs the raw confidence.** `[executable]`
  Every review row carries both the raw 1–5 confidence and the mapped FSRS
  rating. `reference/schema.sql` requires confidence 1–5 and rating 1–4 with
  `NOT NULL` + `CHECK`; application code has no UPDATE or DELETE path for
  `review_log`. Gate checks the schema constraints and scans/tests the write path.
  *Defect prevented:* changing the confidence→FSRS mapping becomes irreversible
  if only the mapped value survives; log replay (ADR-0003) depends on the raw
  value existing.

- **R7 — Zero coupling to the lecture app.** `[executable]` No import from, no
  foreign key into, and no direct read of the German lecture app's code or data.
  Integration is HTTP only, via the app factory (ADR-0002). Everything the
  flashcard side needs from a lecture (sentence text, lesson label) is passed in
  the capture request and stored here.
  *Defect prevented:* a convenience import today makes the compose-level
  integration impossible later, and re-creates the HostContext growth failure
  mode ADR-0002 deleted.

- **R8 — The container binds `127.0.0.1` only.** `[reviewed]` Compose/run files
  publish `127.0.0.1:8000:8000`, never `8000:8000`.
  *Defect prevented:* Docker's default publish traverses most host firewalls and
  exposes an unauthenticated deck API to the LAN (ADR-0001 §2).

- **R9 — Dictionary and user data never share a file or volume.** `[reviewed]`
  `dictionary_vN.sqlite` is a read-only, disposable, refetchable asset; notes,
  cards, `review_log`, audio live in a separate DB file and volume.
  *Defect prevented:* an app or dictionary update destroys the user's deck
  (ADR-0001 §12).

- **R10 — Anki export is tab-separated; fields are sanitised.** `[reviewed]`
  Never comma-separated; tabs and newlines are stripped/converted (`<br>`) in
  every field before writing.
  *Defect prevented:* German glosses contain commas constantly; one literal
  newline corrupts every record after it (ADR-0001 D14/§7).

- **R11 — Attribution is per row, always filled.** `[reviewed]` Every `sense`
  and `example` row carries `source` and `license`; LLM-generated build rows are
  marked `source='llm_generated_v1'` and must never be indistinguishable from
  Wiktionary rows.
  *Defect prevented:* CC BY-SA obligations and clean rollback of generated rows
  are unreconstructable after the fact (ADR-0001 §8, §12).

- **R12 — Browser-facing localhost requests are origin/host guarded.** `[executable]`
  `cors_origins` is an exact-origin allowlist; `*` is forbidden. Every request
  validates `Host` as loopback (`127.0.0.1`, `localhost`, or `[::1]`, with its
  configured port), and any present `Origin` must exactly match `cors_origins`.
  Every non-GET browser-callable route requires `X-Flashcards-Request: 1`;
  missing/invalid guards are rejected before any action. JSON routes additionally
  require `Content-Type: application/json`; import/export may use their declared
  media types. The custom header intentionally forces browser CORS preflight.
  Gate checks wildcard rejection, host/origin middleware, and guard coverage on
  every non-GET `/vocab` route (ADR-0002 D24/D25).
  *Defect prevented:* an arbitrary web page or DNS-rebinding host reaching the
  unauthenticated loopback deck API; loopback binding alone does not define a
  browser trust boundary.

## Governance (process rules; binding on orchestrators, workers, and closure)

- **G1 — Every reusable orchestrator prompt is followed by an owner-facing
  `## Next step`, outside the prompt block.** It states what to do, which
  worker/model/session gets the prompt, whether a fresh chat is required, what
  to attach, and what evidence to return. A prompt without it is an incomplete
  dispatch.
  *Defect prevented:* the owner left guessing what to do with a prompt — and
  owner instructions ("send this to X and return the output") accidentally
  executed by the worker they were about (WORKFLOW §10).

- **G2 — Strict one-writer invariant.** One agent/process mutating the working
  tree at a time; the orchestrator does not edit docs while a worker writes code.
  *Defect prevented:* interleaved edits producing trees no report describes
  (WORKFLOW §1).

- **G3 — The owner is not the routine terminal operator.** Git/shell/gate/diff/
  merge work goes into worker prompts as complete procedures with executable
  fail conditions.
  *Defect prevented:* hand-run commands that are unlogged, unauditable, and
  paraphrased ("run the gate") into something that skips the checks
  (WORKFLOW §1).

- **G4 — The closure worker makes zero decisions.** It performs pre-authorized
  mechanical steps; any mismatch or nonzero exit is STOP-and-report.
  *Defect prevented:* judgment silently absorbed into the one step nobody
  reviews — the merge (WORKFLOW §11).

- **G5 — Handoff packaging and synchronization fail closed.** `[reviewed]`
  Missing required file, failing final gate, moved `main`, push failure, or
  corrupted ZIP archive ⇒ no handoff exists. The final gate runs after the
  STATE.md closure commit; `main-gate.txt` includes stderr; the manifest
  carries the actual final `main` HEAD and an audit counter equal to committed
  STATE.md; and `main` is pushed to the private remote mirror before handoff is
  complete.
  *Defect prevented:* the next orchestrator discovering mid-flight that its
  authoritative startup material describes a repo state that never existed
  (WORKFLOW §11).

- **G6 — Donor inspection is read-only and out-of-ladder.** Complete local
  donor repo only; no branches, no commits, no modifications anywhere; not a
  slice attempt; donor machinery excluded by default; any dependency/allowlist/
  ADR/contract change returns to governance before code moves.
  *Defect prevented:* reference-reading silently mutating two repos and
  smuggling scope changes past the brief (WORKFLOW §12).

- **G7 — ADR cold review has explicit objecting and approving terminal rules.**
  When PROMPTS.md §ADR cold review returns objections, the ADR keeps
  `NEEDS COLD REVIEW`, and PROMPTS.md §Orchestrator CLOSE step 3 is satisfied by
  targeting an ADR **revision** session whose own close then targets a fresh cold
  review. Re-reviewing an unchanged draft is a no-op. When a cold review approves
  an ADR, recording that approval and immediately removing `NEEDS COLD REVIEW` is
  an administrative review-status change and does **not** itself require another
  cold review. Any substantive ADR modification still requires the normal fresh
  cold review before dispatch.
  *Defect prevented:* a literal reading of CLOSE step 3 loops either an objected
  unchanged draft or an already-approved ADR through cold review forever
  (WORKFLOW §7).

- **G8 — Two authorities: local execution vs. private GitHub mirror.** `[reviewed]`
  The local Git repository / terminal environment is authoritative for: `git status`
  and uncommitted/untracked files; the actual checked-out branch; fresh `git rev-parse`
  verification when execution depends on it; installed Python packages, spaCy models,
  local services, databases, caches, credentials, environment variables, and other
  machine state; `make gate` and all fresh executable verification; and local
  mutations (commits, merges, branch creation). The private GitHub repository is the
  authoritative persistent mirror for committed/pushed state available there:
  committed source and documentation; `WORKFLOW.md`, `AGENTS.md`, `STATE.md`,
  `PROMPTS.md`, ADRs, plans, backlog, task briefs, worker reports, pushed branches/commits,
  commit history, and committed diff ranges when WORKFLOW permits such inspection.
  GitHub presence does **not** prove a clean local working tree, local runtime state,
  or a fresh passing gate.
  *Defect prevented:* an orchestrator assuming remote mirror existence proves local
  cleanliness, runtime correctness, or passing gate status (ADR-0001/0002).

- **G9 — Push synchronization and privacy invariant.** `[reviewed]`
  Committed repository state required by a subsequent orchestrator or external
  reviewer must be pushed to the private GitHub mirror before handoff. Specifically:
  accepted commits must be pushed before a later session relies on them; after
  worker close, slice branches must be pushed when external review is required;
  after accepted closure/merge, updated `main` must be pushed before the next
  slice handoff is considered complete; authored next-slice briefs and governance
  changes must be committed and pushed before subsequent chats consume them. A push
  failure must be reported as a handoff/synchronization failure, never silently
  ignored. The repository is private by default. No `.env`, API keys, credentials,
  local databases (`*.sqlite`, `*.db`), `.venv`, model caches, or user data may
  ever be committed or pushed.
  *Defect prevented:* stale or missing remote state causing subsequent orchestrator
  sessions to act on out-of-sync context or desynchronizing multi-session handoffs,
  or leaking private credentials and local database state to remotes.

- **G10 — GitHub-first access; no routine ZIP or manual diff upload.** `[reviewed]`
  When GitHub access is available, orchestrators and reviewers must inspect
  committed files, briefs, reports, and authorized diff ranges directly from the
  private GitHub repository without requiring the owner to upload handoff ZIPs,
  markdown files, or patch/diff files. Manual handoff ZIPs and manual diff uploads
  are strictly fallback mechanisms used when GitHub is disconnected, unavailable,
  stale, or incomplete, or when an immutable offline archive is explicitly mandated.
  GitHub access does not broaden diff-reading permissions: orchestrators continue to
  review reports rather than diffs (WORKFLOW §1), and full-diff review remains
  strictly restricted to risk-labeled slices under WORKFLOW §6.
  *Defect prevented:* manual courier toil and token waste uploading redundant files,
  while preventing unauthorized full-diff leakage into normal report-based
  orchestration reviews.

## Conventions

- **C1 — App factory, no module-level state.** The service is constructed by
  `create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None)`;
  no env reads at import time, all endpoints under one prefix. This is what
  keeps the later mount-vs-compose choice free (ADR-0002).
- **C2 — Dependency direction is one-way:** `api → deck → render → dictionary →
  resolve`. Nothing below `deck` touches user state; that is what makes `render`
  and `dictionary` exact-match testable (ADR-0001 §10).
- **C3 — German-only, by decision.** No generic note types, no cloze, no
  configurable templates (ADR-0001 D18). Proposals to generalise are
  Stop-and-ask, not scope.
