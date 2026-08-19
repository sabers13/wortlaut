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
  row, every **localized meaning** row (the DE/EN/FA learner-meaning texts hanging
  off a sense — ADR-0004 §6, pending cold review), and every `example` row carries
  a non-empty `source` and `license`. Provenance lives on the localized meaning
  row, not on the sense, because German, English and Persian meanings for one
  sense routinely come from different sources under different licenses.
  A computed derived-compound meaning block does not create a synthetic
  persisted provenance row; provenance is the ordered set of the exact component
  `sense_meaning` rows rendered (ADR-0004 D46), and any generated component rows
  still traverse D45 derivation edges.
  LLM-generated build rows are marked `source='llm_generated_v1'` or an explicitly
  versioned successor (`llm_generated_vN`); they must never masquerade as
  source-backed Wiktionary rows, must never overwrite a source-backed row in
  place (simplifying one produces a new generated row beside it), and must be
  reversible by deleting on that marker alone. Every source-backed localized
  meaning text actually consumed by generation, simplification, or semantic QA
  as derivation input is recorded in a derivation edge
  (`sense_meaning_derivation`, ADR-0004 D45 §6.1); generated→generated
  derivation edges are forbidden in v1; upstream source/license obligations
  remain traversable through those derivation edges; and rollback by generated
  version deletes generated rows plus their derivation edges, never source-backed
  rows.
  *Defect prevented:* CC BY-SA obligations and clean rollback of generated rows
  are unreconstructable after the fact (ADR-0001 §8, §12; ADR-0004 §8).

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

- **R13 — Dictionary numeric IDs are never durable semantic identity.** `[executable]`
  Dictionary-backed PART-B state uses ADR-0004 D47 stable semantic refs;
  `lemma_id` / `sense_id` may be active-asset caches only. A replacement
  dictionary is not visible until stable-ref validation and atomic PART-B
  relink + active-version update complete. Stale picker asset tokens are
  rejected before writes. Duplicate/ambiguous stable refs or mixed
  old-binding/new-asset states fail closed. User-authored meanings and review
  history survive replacement. Gate coverage is assigned to the owning
  alignment/runtime/smoke slices.
  *Defect prevented:* a recycled numeric SQLite ID after dictionary rebuild
  silently binding a user's note to an unrelated semantic sense or exposing wrong
  meaning text.

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
  fail conditions. Under the supervised worker fallback (G11 / WORKFLOW §14),
  the owner functions strictly as a transport relay ferrying prompts to the
  local worker and returning verifiable execution evidence to the orchestrator,
  never as the manual operator, verifier, or decision maker.
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

- **G7 — ADR cold review converges within a three-review lineage cap.**
  Every ADR lineage tracks its cold-review ordinal. Review #1 is the broad
  architecture challenge. If it objects, revise the objections and proceed to
  fresh review #2. Review #2 is focused on those remedies, their direct knock-on
  contradictions, and serious materially missed correctness/executability/
  integrity defects; optional improvements and implementation details are not
  blockers. If qualifying blockers remain, revise them and proceed to fresh
  review #3, explicitly the **FINAL CONVERGENCE REVIEW**. Review #3 may block only
  for severe data-corruption/data-loss, security/integrity, impossible or
  non-executable architecture, direct binding-contract contradiction, or
  persistent-state failure/atomicity defects. There is **no review #4** for the
  same lineage. Review #3 either approves/removes `NEEDS COLD REVIEW`/freezes the
  architecture, or records terminal final-convergence blockers (`F1`, `F2`, ...)
  and replaces `NEEDS COLD REVIEW` with **`NON-CONVERGENT / BLOCKED`**, permanently
  closing that lineage. A blocked lineage is never substantively revised into a
  review #4. Recovery requires product descope or a genuinely new successor ADR
  lineage whose architecture is materially simpler, narrower, split, or otherwise
  materially different and explicitly supersedes the blocked lineage. Cosmetic
  renaming, file movement, wording cleanup, or substantially preserving the same
  unresolved architecture does not reset the count. A legitimate successor starts
  at review #1 with its own three-review cap. Every permitted review still uses a
  fresh, cold orchestrator session. Approval and immediate administrative removal
  of `NEEDS COLD REVIEW` do not themselves trigger another review.
  *Defect prevented:* governance becoming an unbounded review/revision loop that
  continually expands architecture and delays implementation (WORKFLOW §7).

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
  or a fresh passing gate. Under supervised worker fallback (G11 / WORKFLOW §14),
  fresh local execution facts are established by a supervised local worker running in
  the authoritative local checkout and relayed to the orchestrator.
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

- **G11 — Supervised worker fallback and authority delegation.** `[reviewed]`
  Physical local terminal access and project decision authority are strictly
  separated. Worker execution and local evidence collection can be delegated to
  a local terminal/coding worker with access to the authoritative local checkout;
  project decision authority (interpreting governance, deciding next sessions,
  brief composition, architectural reasoning, evaluating worker evidence,
  requesting retries, acceptance/rejection, and closure decisions) cannot be
  delegated and remains strictly with the primary orchestrator.
  Under supervised worker fallback (WORKFLOW §14), local evidence generated by a
  worker in the authoritative checkout (exact commands, stdout/stderr, exit codes,
  commit SHAs, `git status`, gate numbers) is relayed (via the owner as transport
  layer when necessary) to the primary orchestrator. The orchestrator may accept
  that verified local evidence for workflow decisions after verifying that it
  identifies the authoritative checkout, target branch, and expected refs.
  Local terminal access does not confer project decision authority: a local worker
  is not a self-authorizing orchestrator. It may not redesign architecture, alter
  workflow, expand scope, self-accept its own implementation, waive failures, or
  invent next steps. Separation of duties is preserved: a worker never self-approves
  a slice, and governance/ADR cold reviews remain separate fresh sessions.
  *Defect prevented:* conflating physical local terminal access with project decision
  authority, or forcing governance orchestration to migrate away from the primary
  ChatGPT chat when direct tool bridges are unavailable (WORKFLOW §14).

## Conventions

- **C1 — App factory, no module-level state.** The service is constructed by
  `create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None)`;
  no env reads at import time, all endpoints under one prefix. This is what
  keeps the later mount-vs-compose choice free (ADR-0002).
- **C2 — Dependency direction is one-way:** `api → deck → render → dictionary →
  resolve`. Nothing below `deck` touches user state; that is what makes `render`
  and `dictionary` exact-match testable (ADR-0001 §10).
- **C3 — German-only, by decision.** "German-only" names the **target
  vocabulary language**: German is the only language whose words become notes. It
  does **not** mean learner-facing meanings must be written in German, nor that
  they must be written in English. A note may display its meaning in German,
  English and/or Persian — a per-note, non-empty selection rendered over
  structured fields (ADR-0004, pending cold review) — and that is a display
  contract, not a generalisation of the app. What stays rejected is unchanged: no
  generic note types, no cloze, no configurable templates (ADR-0001 D18, §17.8),
  and no second target language. Proposals to generalise, including making the
  target language configurable, are Stop-and-ask, not scope.
