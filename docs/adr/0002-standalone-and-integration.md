# ADR-0002 — Fully standalone service; integration with the lecture app by composition, not ingestion

**Status:** Accepted 2026-08-19 (owner-approved in conversation). Cold review approved 2026-08-19 after the O15–O19 revision; see `## Cold review`.
**Amends:** ADR-0001 (D2, D7; §5 Behaviour's host-ingest/deletion deck lifecycle
and `note.lesson_id` rendering-pointer paragraph; §6 endpoint/API wording; §10
`resolve.py` ingest-only qualifier, endpoint paths, and picker/commit boundary;
§11 Example ranking's completed-lecture `known` formula (ADR-0003 still owns the
`/vocab/review` request body and `/vocab/decks` response body); §14's deferred
`lesson_token` row; §15's
`load_lesson_doc()` defect row; §16's pointer/no-copied-source-text paragraph;
the §17 amendment header; D15–D17; §17.2; §17.3; §17.4; §17.5; §17.8 only the
rejected "Two-component split (lecture-engine + flashcards)" and "Separate
container / HTTP service for flashcards" rows; §17.9). D3, D11, D12, D13, D18,
D19, §17.7, and every unrelated Rejected choice remain in force.

**Amended by ADR-0004 — pending cold review, not in force yet.** ADR-0004 is
`NEEDS COLD REVIEW`; the rows below take effect only on its approval. It adds a
per-note meaning-language selection to this ADR's picker/commit contract:

| Amended here | Replacement under ADR-0004 (pending) |
|---|---|
| §4 Picker / §4 Stage 2 commit: a selection carries dictionary identity plus `overrides` only | each selection additionally carries the note's **non-empty** meaning-language set drawn from `{de, en, fa}`, which the picker offers at note/card creation |
| §4 per-selection override schema (`front_override`, `back_override`, `gloss_user`) | one further permitted key, `meaning_langs`: a JSON array of distinct supported language codes. Omission means **no mutation** on a reused note; explicit `null` and `[]` are invalid, because the set may never be emptied; a newly created note requires an explicit non-empty set — there is no implicit default, and the picker's preselection is UI, not API. Persistence is `note_meaning_lang` (ADR-0004 §6.2), patched note-wide in the same atomic transaction as membership creation, exactly as this section already specifies for the other keys. Unknown, duplicate or unsupported codes reject the entire `/vocab/cards` request with HTTP 422 before any note, override, membership or language write |
| §4 `gloss_user` as an English-only correction for a revalidated `status='needs_gloss'` selection | the user-authored meaning records which language it was written in (ADR-0004 §6.3); it is not assumed English. `needs_gloss` itself becomes language-aware: no meaning in **any** selected language |
| §6 order 7 — `build stages 03-05 + Dockerfile; stage 04 before mid-September 2026` | stages 03–05 additionally perform the ADR-0004 §8 multilingual offline meaning enrichment (English gap fill, German learner meanings, Persian translations, deterministic validation, selective QA). The mid-September 2026 API-credit constraint is unchanged |
| §6 order 8's sequencing of the remaining app modules | render/API must additionally support the selected DE/EN/FA meaning set, Persian RTL presentation, and tri-state noun plural on the back before UI/browser completion |

**Unaffected by ADR-0004:** §6 order 5 (Gate 2) and its coverage thresholds,
verbatim; Gate 2's position **before** stages 02–05 — it measures stage-01
coverage, which ADR-0004 does not change; the standalone HTTP architecture;
D20–D27; §3's rejections; §4.1's browser boundary and AGENTS R12; and §5's
consequences other than the note contract named above. ADR-0004 does not reopen
the standalone-vs-mounted question.

**Context source:** prior inspection of the German lecture app repo
(`~/projects/german app`) as it existed at its slice-3 close. That donor evidence
was not preserved in this handoff; §1 therefore separates accepted design input
from evidence that must be re-verified before compose integration.

## 1. Context — the host ADR-0001 §17 imagined does not exist

The §17 amendment was written against an assumed host: a stateful Python
application that persists lectures server-side and runs a spaCy pass at ingest.
The accepted design input from that inspection is that the actual lecture app
is the opposite:

- **Its server is stateless.** All user state — lessons, vocabulary, progress —
  lives in browser IndexedDB. Nothing on its server outlives a response.
- **Its ingest does no NLP.** PDF bytes → geometric `PagePrimitives`; there is no
  spaCy pass or server-side token index.

Those two donor claims are **not independently evidenced in this repo**: no
`tasks/*donor-notes.md` survived the earlier session. They are not a prerequisite
for standalone v1 (D20–D23 are now owner-approved constraints in this repo), but
D24's claim that compose integration preserves the host's invariants may not be
implemented until a read-only donor inspection records the exact donor ADR IDs
and executable statelessness-check name in `tasks/adr-0002-donor-notes.md` per
WORKFLOW §12 / AGENTS G6. If that inspection contradicts these premises, STOP at
governance before compose work; do not silently reinterpret either repo.

Under those accepted premises, `HostContext.sentence_at(lesson_id, span)` is
unanswerable — the host holds no lesson to look into. `known_lemmas()` is unanswerable — vocabulary
lives in the browser. The `lesson_token` prerequisite is pointless — there is no
second component with NLP to deduplicate against. And mounting the flashcard
router inside the lecture app's `api/` would put a persistent user DB behind a
server whose statelessness is the *enforcement mechanism* for its content rules,
reverting three executable guarantees to promises.

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D20 | **Fully standalone service.** Own repo, own Docker container, own DB files. v1 is complete with manual entry, CSV word-list import, decks, review, export — no lecture app required | Every feature except highlight-capture works with no host at all |
| D21 | **D7 revised: store the example sentence *text* at capture time**, plus a lesson label. `lesson_id`/`char_start`/`char_end` remain as optional provenance metadata, never required to render | The stateless host *cannot* serve `sentence_at`; the browser has the sentence at highlight time and sends it. ADR-0001 §17.6 already flagged this exit; local-only deployment (§ 53 private copy) covers the copyright rationale |
| D22 | **`HostContext` deleted** (revises D16). Anything the flashcard side needs is passed in the request and stored | The three-method contract was designed for a host that doesn't exist; passing-at-creation was already named the correct answer for contract growth (§17.4) |
| D23 | **Resolution happens at capture time, inside this service** (revises all of ADR-0001 D2). spaCy loads here and only here; the persisted ingest token index and the "highlight does zero NLP" property are **abandoned, not deferred**; `lesson_token` is dropped, not deferred | One captured sentence is resolved locally. Only this component owns NLP, so the duplicated-model/token-index problem no longer exists |
| D24 | **Integration = browser → localhost HTTP + one compose file** (revises D17/§17.5). The lecture app's reader emits a capture request `{sentence_text, selected_span, lesson_label, lesson_id?, known_lemmas?}` and receives the D27 picker payload; deck/review screens are linked from its nav. Its server gains zero endpoints, zero state. The browser boundary is constrained by §4.1 / AGENTS R12 | "Works as a unit" at the UX and `docker compose up` level without importing or persisting host state |
| D25 | **App factory:** `create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None)`; all endpoints under one prefix (`/vocab/...`); no module-level state, no env reads at import; no imports from the lecture app in either direction (AGENTS R7/C1). `cors_origins` is exact-only; `*` is invalid | Gives D26 an explicit configuration seam, keeps browser trust configuration explicit, and preserves mount-vs-compose freedom |
| D26 | **TTS:** Piper is authoritative. If `tts_remote_url` is configured, `POST /speak` is opportunistic only, with a total request timeout of at most 1 second; timeout, connection error, non-2xx, or invalid payload falls back silently to local Piper. No card/review/export path depends on the remote service | Standalone operation has no runtime network dependency; composition may reuse the host voice without turning host availability into a correctness condition |
| D27 | **Highlight capture is two-stage and stateless between requests.** `POST /vocab/highlight` performs local resolution only and returns picker candidates plus a normalized `capture_context`; it creates no note/deck membership. After D11 multi-select/edit-before-add, `POST /vocab/cards` receives the selected candidate/sense references, edits, explicit lesson/deck target, and that `capture_context`, then atomically creates/reuses notes and memberships. No live host fetch and no server-side draft/session state bridges the two calls | Makes D11 executable across the standalone HTTP boundary while preserving D21/D22's by-value host decoupling |

## 3. Rejected

| Rejected | Reason |
|---|---|
| Mounting the flashcard router in the lecture app's `api/` ("ingestion") | Breaks the host's stateless-server invariant and its E1 gate; taints its Phase-3 public demo with a stateful server. The whole benefit would be removing one localhost HTTP hop |
| Keeping D7's pointer + `sentence_at` | Unimplementable against a stateless host — a dangling reference from birth, not a deliberate cost |
| `lesson_token` in the lecture app | Requires adding spaCy and server-side persistence to an app that structurally forbids both |
| Porting flashcards into the browser (IndexedDB + wasm SQLite) | The only true single-app path, but a full rewrite plus a ~130 MB dictionary in the browser. Out of proportion to the benefit |
| Filing these ADRs into the lecture app repo now | Its SRS is Phase-4-BLOCKED by design; an accepted server-side-FSRS ADR next to its ADR-0001/0010 creates exactly the cross-file contradiction its workflow escalates on. One backlog line there at its Phase-4 decomposition is the correct footprint |

## 4. Two-stage capture and commit contract (normative)

Highlight capture preserves ADR-0001 D11: resolution/candidate generation happens
first, the picker may multi-select and edit, and only the explicit commit creates
notes or deck memberships. There is no temporary capture record on the server.

**Stage 1 — resolve for the picker.** `POST /vocab/highlight` receives:

```json
{
  "sentence_text": "Ich rufe dich morgen an.",
  "selected_span": {"start": 4, "end": 8},
  "lesson_label": "Lektion 7",
  "lesson_id": "optional-host-lesson-id",
  "known_lemmas": ["optional", "ranking", "context"]
}
```

`selected_span` is validated as in-bounds character offsets into the submitted
`sentence_text`. The service runs `app/resolve.py` locally at this point and
returns candidate/sense data sufficient for D11's picker plus a normalized,
self-contained `capture_context`:

```json
{
  "candidates": [
    {"ref": "stable-dictionary-ref", "senses": [{"sense_id": 17, "gloss": "to call"}]}
  ],
  "capture_context": {
    "sentence_text": "Ich rufe dich morgen an.",
    "selected_span": {"start": 4, "end": 8},
    "lesson_label": "Lektion 7",
    "provenance": {
      "lesson_id": "optional-host-lesson-id",
      "char_start": 4,
      "char_end": 8
    }
  }
}
```

`provenance` is optional as a whole; when no stable host lesson identifier exists,
it may be omitted. `known_lemmas` is resolution/ranking input only and need not be
round-tripped. **Stage 1 performs no note creation and no `note_deck` write.**

**Picker.** The client presents the returned candidates and keeps D11's
default-one selection and multi-select behaviour. A selected item is identified at
commit by its stable dictionary `ref` plus `sense_id` (or the existing
unresolved/stub identity), not by ephemeral server memory. `ref`, `sense_id`,
`lemma_text`, `pos`, dictionary grammar fields, and provenance are identity/source
data, **not editable fields**.

**Per-selection edit/override schema.** Each selection carries an `overrides` JSON
object; omitted `overrides` is equivalent to `{}`. v1 permits exactly these keys,
which map directly to the existing `reference/schema.sql` `note` columns:

| Override key | JSON value | Persistence / meaning |
|---|---|---|
| `front_override` | string or `null` | `note.front_override`; whole rendered front override |
| `back_override` | string or `null` | `note.back_override`; whole rendered back override |
| `gloss_user` | string or `null` | `note.gloss_user`; only valid for a revalidated `status='needs_gloss'` selection |

For any non-null override, the value must be a JSON string containing at least one
non-whitespace code point; no numeric/boolean/object coercion is allowed, and the
submitted string is persisted verbatim. Key omission means **no mutation** of that
column on a reused note (and SQL `NULL` on a newly created note); explicit `null`
means clear that override to SQL `NULL`. `gloss_user` is rejected for a resolved or
derived candidate even when its value is `null`; resolved-sense gloss correction
uses `back_override` rather than changing dictionary data. Unknown override keys,
blank strings, invalid value types, duplicate selections that revalidate to the
same note identity, or an override whose candidate identity cannot be revalidated
reject the entire `/vocab/cards` request with HTTP 422 before any note, override,
or membership write.

Overrides are scoped to their own `selections[i]`. Under multi-select, each
selection is independently revalidated and patched; edits from one selection never
apply to another. If the note already exists under D12's shared-note model, the
explicitly present keys patch that shared note in the same atomic transaction as
membership creation; omitted keys remain unchanged. This is deliberately note-wide,
not deck-membership-specific. Candidate `ref`/`sense_id` remains the revalidated
dictionary identity and can never be changed through `overrides`.

**Stage 2 — commit the picker result.** `POST /vocab/cards` receives:

```json
{
  "selections": [
    {"ref": "stable-dictionary-ref", "sense_id": 17, "overrides": {}}
  ],
  "capture_context": {
    "sentence_text": "Ich rufe dich morgen an.",
    "selected_span": {"start": 4, "end": 8},
    "lesson_label": "Lektion 7",
    "provenance": {
      "lesson_id": "optional-host-lesson-id",
      "char_start": 4,
      "char_end": 8
    }
  },
  "deck": {"kind": "lecture", "name": "Lektion 7", "lesson_id": "optional-host-lesson-id"}
}
```

The commit revalidates the capture-context shape, candidate references, and every
per-selection override under the schema above; it never fetches sentence or lesson
state from the host. It finds or creates the standalone lecture deck from the
explicit `deck` target (using `lesson_id` when present, otherwise the submitted
name under ADR-0001 D12's existing uniqueness rules), then atomically
creates/reuses and patches each selected note and inserts the required `note_deck`
memberships. `capture_context.sentence_text` is copied into
`note.example_de` and frozen per ADR-0001 §11. The span and optional provenance
are stored only as metadata; rendering never depends on them. Existing notes keep
their first frozen primary example; committing the same note from a new lesson
adds membership without replacing that example.

Manual entry and CSV import keep D13/D19 and join the same picker/commit stage.
They have no highlight `capture_context`; after ranking examples, the chosen
primary dictionary sentence is copied by value into `note.example_de` at creation.
It is never re-ranked on ordinary render. `example_de` may be NULL only when no
usable example exists, preserving ADR-0001 §11's explicit manual-no-example case.
No `example_id` foreign key is added.

### 4.1 Browser boundary (normative)

The loopback API is unauthenticated, so browser access is a trust boundary, not
a CORS decoration. AGENTS R12 is part of D24/D25:

- `cors_origins` contains exact origins only; `*` is rejected at app creation.
- Every request validates `Host` as the configured loopback endpoint
  (`127.0.0.1`, `localhost`, or `[::1]`, with port). An `Origin` header, when
  present, must exactly match one configured origin.
- Every non-GET `/vocab` route rejects the request unless it carries
  `X-Flashcards-Request: 1`; the route's declared media type is still enforced
  (`application/json` for JSON APIs, CSV/multipart only where explicitly
  defined). The custom header alone deliberately makes browser cross-origin
  mutation require a successful preflight. CLI/local-process callers may omit
  `Origin`, but not the Host/non-GET guards.
- Guard failure happens before endpoint logic; no state change or export side
  effect occurs first.

## 5. Consequences

- v1 has no highlight capture until the lecture app's reader gains the emit
  handler — manual entry and CSV import are the capture paths until then.
- The flashcard DB is self-contained: decks survive lecture deletion trivially;
  exports carry real sentences, not pointers.
- The i+1 example ranking algorithm remains ADR-0001 §11's, but its `known` set
  is narrowed by this ADR: `known = deck lemmas ∪ known_lemmas` only when the
  optional by-value `known_lemmas` input is supplied. No live host fetch is
  permitted; when the input is absent, `known = deck lemmas`.
- `reference/smoke_test.py` remains the rewrite baseline but its contracts must
  be amended in the first slice that makes it executable: `/vocab/highlight`
  returns candidates plus `capture_context` and performs no note/membership write;
  `/vocab/cards` receives picker selections, that context, and the explicit deck
  target, then persists the frozen sentence + optional provenance. The baseline
  multi-selects at least two distinct candidates with different valid per-selection
  overrides and asserts the exact `note.front_override`/`note.back_override`/
  `note.gloss_user` column effects that apply; it also sends an unknown or invalid
  override and asserts HTTP 422 with no note/membership/override write. Manual/CSV
  creation asserts a chosen dictionary example is frozen by value. Its separately
  filed import-path defect
  is unchanged and is fixed only with the `app/` rewrite (docs/backlog.md).

## 6. Sequencing — normative input to `docs/plan.md`

Execute in this order; a later line may not start before the preceding line's
acceptance/decision point is satisfied:

```
0  one-time repository bootstrap: execute PROMPTS.md §Repository bootstrap
   worker from a non-slice orchestrator session. It must create `.git` with
   `main`, commit the pre-existing repository tree, and print the resulting
   `main` HEAD. No slice worker starts before this succeeds.
1  slice-0: repo skeleton + make gate infrastructure, using the bootstrap HEAD
   as the expected main HEAD and PROMPTS.md's first-slice startup exception
2  app/resolve.py + app/dictionary.py (resolution ladder + compound splitter)
   + executable R3 stage-02 cache-key check scaffold
3  Gate 1: verify spaCy dep label and lock SVP_DEP tests
4  build stage 01: wiktextract -> lemma/sense/surface_form
5  Gate 2: real-textbook coverage using resolve + dictionary
      <85%    -> STOP; governance redesign, no stage 02
      85-<95% -> apply the already-specified splitter/fuzzy remedy once, rerun;
                  if rerun is still >=85%, record it and continue; <85% -> STOP
      >=95%   -> continue
6  build stage 02: Tatoeba index; MUST import app/resolve.py and key cache on
   its SHA-256 (AGENTS R2/R3)
7  build stages 03-05 + Dockerfile; stage 04 before mid-September 2026
8  remaining app modules: examples, render, deck, api, export; implement
   ADR-0003 review/mastery contracts and AGENTS R12 before browser integration
9  capture + manual/CSV import/export flows; amend and run the smoke baseline
10 read-only donor verification (tasks/adr-0002-donor-notes.md), then compose
   integration only after the lecture app's Phase 4 decomposition
```

Line 5 is a design gate, not a retry ladder: `<85%` returns to governance. Line
10 is blocked independently by the host's Phase 4 and by the missing donor
evidence named in §1.

---

## Cold review

**Reviewer:** fresh orchestrator session, 2026-08-19 (Opus 5). Repo-only context,
per WORKFLOW.md §7 / PROMPTS.md §ADR cold review. The draft was written outside
any orchestrator session, so this session is a valid cold reviewer.

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** The core direction (D20
standalone, D21 store-the-sentence, D22 delete `HostContext`) is sound and the
premises in §1, where they can be checked against this repo, hold. The
objections below are about what the ADR leaves unstated or contradicts, not
about the direction. O1–O7 are BLOCKING (they change either a normative
contract or the sequencing that `docs/plan.md` must follow); O8–O9 are MINOR
(citation hygiene) and may be fixed in the same revision pass.

### O1 — BLOCKING. D23 revises ADR-0001 D2, but nothing records that.

D23 states resolution moves from ingest to capture time. That revises ADR-0001
D2 ("Lemma resolution at **ingest**, persisted as a token index; highlight is an
interval lookup"). But:

- this ADR's `Amends:` line lists only D7, D15–D17, §17.4–§17.5 — not D2;
- ADR-0001's supersession header says "Everything else — **D1–D6**, D8–D14,
  D18–D19 … stands as written."

So the two files assert opposite things about D2, and the D2 clause that D23
does *not* mention — the persisted token index, and "highlight does zero NLP" —
is dropped silently rather than deliberately. WORKFLOW.md §10 makes a
cross-file contradiction a dispatch blocker, so this must be repaired in files.

*Remedy:* add D2 to this ADR's `Amends:` line, add a D2 row to ADR-0001's
supersession table, and state explicitly in D23 that the token index and the
zero-NLP-at-capture property are abandoned, not deferred.

**Resolution (2026-08-19 revision): APPLIED.** `Amends:` now includes D2;
ADR-0001's supersession table has an explicit D2 row; D23 now supersedes the
whole ingest/token-index/zero-NLP contract and says those properties are
abandoned rather than deferred.

### O2 — BLOCKING. §6's sequencing is not executable in the order given.

`docs/plan.md` is required to follow §6, and §6 cannot be followed as written:

- Step 1 (Gate 1) verifies `SVP_DEP` **in `app/resolve.py`** (ADR-0001 §13).
- Step 3 (Gate 2) runs `DICT.lookup(parse(w)).status` — that is `app/resolve.py`
  plus `app/dictionary.py` including the compound splitter (ADR-0001 §10 ladder
  steps 1–4). ADR-0001 §13 says so itself: hit rate is "stage 01 plus **the
  splitter**".
- Step 4 (build stage 02) **must import the resolver** — ADR-0001 D3/§12 and
  AGENTS R2, with R3 keying the stage-02 cache on a SHA-256 of
  `app/resolve.py`.

All three depend on modules §6 places at **step 5** ("flashcards v1 (app
modules)"). Combined with this repo's state — `app/` does not exist at all
(STATE.md "Blocked", docs/backlog.md) — the ordering is not a nuance, it is
undeliverable.

*Remedy:* split step 5. Insert `resolve.py` + `dictionary.py` (ladder +
splitter) before Gate 1, and state that the remaining app modules
(`examples`, `render`, `deck`, `api`, `export`) follow Gate 2. Note that this
also puts AGENTS R3's executable cache-key check on the critical path earlier
than §6 implies.

**Resolution (2026-08-19 revision): APPLIED.** §6 is now a normative,
plan-ready sequence beginning with slice-0, then `resolve.py` + `dictionary.py`
and the R3 cache-key scaffold, then Gate 1, stage 01, and Gate 2. Stage 02 cannot
start before Gate 2 and must import/hash the resolver; the remaining app modules
follow the build gates. `<85%` is an explicit STOP back to governance.

### O3 — BLOCKING. D24 + D25 open a browser attack surface that AGENTS R8 does not cover.

ADR-0001 §2 names exactly one surviving security concern and answers it by
binding `127.0.0.1` (AGENTS R8). That answer is sufficient only while the
caller is a local process. D24 makes the caller **a web page in the user's
browser**, and D25 adds `cors_origins` to the factory. Loopback binding does not
defend an unauthenticated API against the browser:

- a simple cross-origin `POST` is **sent** regardless of CORS; CORS only hides
  the *response*. Every mutating endpoint (`/cards`, `/review`, `/gloss`,
  `/export`) is therefore reachable from any page the user has open;
- `Origin`-allowlisting alone is defeated by DNS rebinding unless the `Host`
  header is also validated;
- `cors_origins` is a free-form parameter: nothing in this ADR or AGENTS
  forbids `*`, which would additionally expose the whole deck for reading.

This is not a step-6 implementation detail — it constrains the factory contract
D25 declares normative, so it belongs in this ADR.

*Remedy:* decide here, and reflect it as a new AGENTS rule (candidate for
`[executable]`): exact-origin allowlist with `*` prohibited; `Host`/`Origin`
validation on every request; all mutating endpoints require a condition that
forces a CORS preflight (e.g. `Content-Type: application/json` plus a custom
header) so that CORS actually enforces rather than decorates. If the owner
prefers to accept the risk for a local-only v1, say so explicitly with the
threat named — an unstated risk is the failure mode ADR-0001 §2 was written
against.

**Resolution (2026-08-19 revision): APPLIED.** §4.1 defines the browser trust
boundary and AGENTS R12 is `[executable]`: wildcard CORS is forbidden; Host is
loopback-validated on every request; any present Origin is exact-allowlisted;
and every non-GET `/vocab` route requires `X-Flashcards-Request: 1` (plus its
declared media type), forcing browser preflight before endpoint logic.

### O4 — BLOCKING. D26 has no configuration seam in D25's factory signature.

D25 fixes the signature as `create_app(dict_path, user_db_path, cors_origins)`
and forbids module-level state and import-time env reads (AGENTS C1). AGENTS R7
makes the factory the *only* permitted integration point. D26 then allows
calling the lecture app's `POST /speak` — with no parameter to carry its base
URL. As written, D25 and D26 cannot both be satisfied.

*Remedy:* extend the signature (e.g. `tts_remote_url: str | None = None`) in
D25 itself, or drop D26 from this ADR and file it as a backlog item with the
signature change named as its precondition.

**Resolution (2026-08-19 revision): APPLIED.** D25 and AGENTS C1 now use
`create_app(dict_path, user_db_path, cors_origins, *, tts_remote_url=None)`.
D26 therefore has an explicit configuration seam without import-time env reads
or module-level state.

### O5 — BLOCKING. D26 adds an unstated runtime network failure path.

ADR-0001 D1's recorded defect is "an offline app silently grows a network
failure path and ships an API key" (AGENTS R1). R1's letter covers LLM SDKs
only, so D26 does not violate it — but it introduces exactly the defect the
rule exists to prevent, and states no fallback, no timeout, and no behaviour
when the lecture app is absent or slow.

*Remedy:* state normatively that Piper is authoritative, the remote `/speak`
call is opportunistic with a bounded timeout and silent fallback to Piper, and
that no code path may block on it.

**Resolution (2026-08-19 revision): APPLIED.** D26 makes Piper authoritative,
caps the optional remote call at a one-second total timeout, falls back on every
remote failure, and forbids card/review/export correctness from depending on
remote availability.

### O6 — BLOCKING. D21/D24 invalidate the named acceptance baseline; §5 does not say so.

STATE.md and docs/backlog.md both name `reference/smoke_test.py` as *the*
acceptance baseline for the `app/` rewrite. On disk that file calls:

```python
deck.add_note(udb, 1, e, lesson_id="lektion04", span=(120, 130))
```

— i.e. the D7 pointer signature, with no sentence text. Under D21/D24 and the
`note.example_de` / `lesson_label` columns already present in
`reference/schema.sql`, that call cannot be the baseline. §5 Consequences lists
three consequences and not this one.

*Remedy:* add a consequence naming the baseline amendment and the new
`add_note` parameters (`sentence_text`, `lesson_label`, provenance optional).
Separately note that `reference/smoke_test.py` is also path-broken as filed —
it does `sys.path.insert(0, dirname(__file__))` and imports `app.*`, which
resolves to `reference/app/`, not the repo's `app/`. That is a disk defect, not
an ADR defect; it is filed in docs/backlog.md.

**Resolution (2026-08-19 revision): APPLIED.** §5 now makes the smoke baseline
amendment part of the rewrite contract: note creation supplies
`sentence_text`/`lesson_label` and optional provenance. The separate path defect
remains untouched and blocked with the `app/` rewrite in docs/backlog.md, as
required by this session's scope.

### O7 — BLOCKING. On the path this ADR makes primary, ADR-0001 §11's "freeze the primary example" is unimplementable.

§5's first consequence is that until the lecture app's reader emits captures,
**manual entry and CSV import are the only capture paths**. Those notes have no
captured sentence: `reference/schema.sql` documents `note.example_de` as "NULL
for manual entry", and there is no `note.example_id`. ADR-0001 §11 requires
"Freeze the primary at creation for recall stability" — with nothing to freeze
it in, the primary example silently re-ranks on every render for every note in
v1. That is a correctness property, not a nicety: the card the user memorised
changes under them.

*Remedy:* decide the storage now — either write the chosen dictionary sentence
into `note.example_de` at creation (simplest, and keeps rendering
source-agnostic), or add `note.example_id INTEGER` referencing the dictionary
asset by value (no FK, per ADR-0001 §17.3). Then state which, and amend
`reference/schema.sql` accordingly.

**Resolution (2026-08-19 revision): APPLIED.** The by-value option is chosen.
§4 now requires manual/CSV creation to copy the selected primary dictionary
sentence into `note.example_de`; NULL is allowed only when no usable example
exists. `reference/schema.sql` documents the same invariant. No cross-DB
`example_id` reference is introduced.

### O8 — MINOR. §6 points at a file that is not in this repo.

"replaces HANDOFF ordering; **steps 5 and 7 deleted**" is unverifiable here —
there is no `HANDOFF` document on disk, and STATE.md records that the design
session's artifacts were not recovered. A normative section may not depend on a
missing file.

*Remedy:* state the replaced ordering inline, or delete the parenthetical.

**Resolution (2026-08-19 revision): APPLIED.** The missing-HANDOFF
parenthetical is gone. §6 is now self-contained and explicitly normative input
to `docs/plan.md`.

### O9 — MINOR. §1's load-bearing premises have no in-repo evidence.

D20–D26 all rest on §1's claims about `~/projects/german app` (stateless server
enforced by a gate check; no spaCy; state in IndexedDB). §3 cites "its
ADR-0001/0010" loosely; nothing else is checkable from here, and there is no
`tasks/<ID>.donor-notes.md` (PROMPTS.md §Donor inspection). If §1 is wrong the
whole ADR collapses, and a cold reviewer cannot tell.

*Remedy:* cite the donor ADR numbers and the name of its executable
statelessness check precisely, or dispatch a read-only donor inspection to
produce the notes file (out-of-ladder, does not touch the audit counter —
WORKFLOW.md §12, AGENTS G6).

**Resolution (2026-08-19 revision): REMEDY APPLIED WITH AN EVIDENCE GATE;
immediate donor dispatch rejected.** The current handoff contains no donor repo
or preserved donor notes, so inventing ADR IDs/check names would violate AGENTS
G6. §1 now marks those host claims as un-evidenced in this repo and makes
standalone D20–D23 independent of them; §6 requires a read-only donor inspection
to create `tasks/adr-0002-donor-notes.md` immediately before compose
integration. Any contradiction is a governance STOP. This does not repair or
re-open the host app in this revision session.

### Checked and found sound (no objection)

- D22 (`HostContext` deleted) against ADR-0001 §17.4's own stated growth
  failure mode — consistent, and §17.4 already named passing-at-creation as the
  correct answer.
- D25's `/vocab` prefix against ADR-0001 §17.5 — keeps the mount option free
  without creating coupling; consistent with AGENTS C1/R7.
- §3's rejection of router mounting, of keeping D7's pointer, of `lesson_token`
  in the lecture app, and of the browser rewrite — each carries a stated cost
  and a reason, not a dismissal.
- D21 against ADR-0001 §17.3's "no cross-component foreign keys" test and
  §17.6's flagged exit — the exit was pre-authorised, and `reference/schema.sql`
  already implements it as plain values.
- D23's latency claim ("one sentence through spaCy is milliseconds") — true,
  and the model-load cost is a container-build concern already covered by
  ADR-0001 §12 ("Download spaCy … at image build time"). Noted here only
  because §5 does not mention that spaCy is now in this service's runtime
  dependency graph; that is a documentation gap, not an objection.

### Fresh cold review — 2026-08-19

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** The 2026-08-19 revision
actually resolves O1–O9 and their recorded cross-file remedies are present.
Two independent blockers remain in the revised contract.

### O10 — BLOCKING. ADR-0001 still contains unsuperseded decomposition text that rejects ADR-0002's chosen architecture.

ADR-0002 says it amends D15–D17 and §17.4–§17.5, and ADR-0001's supersession
header names the same limited range. ADR-0001 then says everything else stands.
Several later §17 clauses therefore remain normative while contradicting D20,
D22–D24:

- the §17 amendment header still says the target is deferrable and v1 may ship
  in-process, and still declares `lesson_token` as a dependency;
- §17.2 still requires the `german-vocab-core` / `lecture-engine` / `flashcards`
  three-component DAG with both consumers importing the shared resolver;
- §17.3 still assigns `lesson_token` to the lecture engine and describes the
  flashcard DB as asking the host to resolve stored lecture pointers;
- §17.8 still lists **"Separate container / HTTP service for flashcards"** as a
  rejected alternative; and
- §17.9 still says v1 may ship in-process and service extraction is merely a
  later mechanical option.

Later-ADR precedence cannot repair text that ADR-0002 never declares
superseded while ADR-0001 explicitly says that unlisted text still stands. A
worker can therefore obey either ADR and be wrong under the other.

*Remedy:* extend ADR-0002's `Amends:` declaration and ADR-0001's supersession
header to cover the conflicting §17 amendment header/decomposition/ownership/
Rejected/sequencing clauses, while explicitly preserving D18, D19, §17.7 and
unrelated rejected generic-note/plugin alternatives. Do not re-open the
standalone-vs-in-process choice; record that ADR-0002 supersedes it.

**Resolution (2026-08-19 revision): APPLIED.** ADR-0002's `Amends:` declaration
now explicitly supersedes the §17 amendment header, D15–D17, §17.2, §17.3,
§17.4, §17.5, §17.8's rejected two-component-split and separate-HTTP-service
rows, and §17.9. ADR-0001's supersession header records the same scope and
states that standalone HTTP is the accepted v1 path, not a deferred
alternative. D18, D19, §17.7, and the unrelated §17.8 generic-note,
configurable-template, and plugin-registry rejections are explicitly preserved.
The historical ADR-0001 body remains untouched.

### O11 — BLOCKING. §6 line 1 is not dispatchable under the repository's mandatory worker preflight before Git exists.

§6 begins with `slice-0: git/repo skeleton + make gate infrastructure`. On disk,
STATE.md and docs/backlog.md correctly state that there is no `.git`, no `main`
HEAD, and no branch. But PROMPTS.md §Worker OPEN requires every implementation
worker to run, exactly and before implementation:

```text
git status --porcelain
git checkout -b slice/<ID> <expected main HEAD>
```

Both commands are impossible under the pre-slice-0 state. docs/backlog.md says
slice-0 should special-case `git init`, but backlog prose does not amend the
mandatory executable worker procedure and there is no bootstrap exception for
this preflight in WORKFLOW.md or PROMPTS.md. As written, planning can produce a
slice-0 brief that governance itself forbids from starting.

*Remedy:* add one explicit bootstrap exception in the binding workflow/prompt
contract for the first repository-creation worker (with executable clean-path
checks, `git init -b main`, initial commit, and printed resulting `main` HEAD),
or move repository initialization into a distinct governance/bootstrap
procedure that completes before the normal slice worker lifecycle. Then make
ADR-0002 §6 line 1 point to that executable procedure. The owner must not become
the terminal operator (AGENTS G3).

**Resolution (2026-08-19 revision): APPLIED.** Repository initialization is now
a distinct one-time pre-slice worker procedure in WORKFLOW.md §10 and
PROMPTS.md §Repository bootstrap worker. Its executable preflight verifies that
the target is not already inside a Git work tree, that `.git` is absent, that
the required governance files are present, and that Git identity is available
*before* mutation; it then runs `git init -b main`, commits the existing tree,
verifies a clean `main`, and prints the actual `main` HEAD. The owner only
ferries the prompt/result per AGENTS G3. PROMPTS.md's first-slice startup
exception consumes that bootstrap HEAD without requiring a nonexistent prior
manifest or `main-gate.txt`, after which normal worker preflight applies.
ADR-0002 §6 now points to this procedure before slice-0.

### Fresh cold review — 2026-08-19 (post O10–O11 revision)

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** The O10 and O11 revision
mechanisms are present on disk: ADR-0001/ADR-0002 now record the §17 standalone
supersession, and WORKFLOW/PROMPTS now provide a real pre-repository bootstrap
worker plus a slice-0 startup exception. The bootstrap command sequence itself
is executable. Three blockers remain: O10's cross-file supersession is still
incomplete outside §17, O11's first-slice transition still contains a
contradictory owner-facing ZIP instruction, and the revised capture endpoint
does not define an executable D11 picker-to-commit flow.

### O12 — BLOCKING. O10 fixed §17, but ADR-0001 still has unsuperseded normative text outside §17 that contradicts ADR-0002.

ADR-0001's new header supersedes D2, D7 and the conflicting §17 clauses, then
says everything else stands. Several surviving clauses are therefore still
normative even though the accepted standalone architecture makes them false or
unimplementable:

- **§5 Behaviour** still says a lecture deck is auto-created *at ingest* and
  that deleting a lecture deletes its deck. ADR-0002 has no host ingest path
  and §5 explicitly says standalone decks survive lecture deletion. The same
  section's `note.lesson_id` paragraph still says the provenance pointer is
  what renders on the card, while D21/§4 render the copied sentence text and
  keep provenance optional.
- **§6 / §10 API text** still describes `/highlight` as taking a lecture
  reference/span and `/lookup`/other routes without D25's `/vocab` boundary;
  §10 also labels `resolve.py` as "spaCy only (ingest)". D23/D24/D25 instead
  require capture-time local resolution and the standalone `/vocab/...` API.
  ADR-0003 already had to supersede two §10 rows explicitly; ADR-0002 has not
  done the corresponding work for its own API changes.
- **§14** still defers a `lesson_token` table as an additive optimisation even
  though D23 says `lesson_token` is **dropped, not deferred** and
  docs/backlog.md correctly lists it under Rejected.
- **§15** still carries `load_lesson_doc()` as a defect to implement, although
  D21/D22 forbid the live host lookup that loader existed to support.
- **§16** still states that source text is never persisted, D7 remains a
  pointer, and CSV export does not emit lecture text. D21/§4 deliberately copy
  the sentence by value, and ADR-0002 §5 says exports carry real sentences.

This is the same class of ambiguity O10 was meant to eliminate, just outside
the §17 amendment. A worker can still obey ADR-0001 literally and reintroduce
host ingest, `lesson_token`, `load_lesson_doc()`, or pointer rendering.

*Remedy:* extend ADR-0002's `Amends:` declaration and ADR-0001's supersession
table to cover the exact conflicting §5/§6/§10/§14/§15/§16 clauses, with concise
replacement text for each. Preserve the still-valid D3/D11/D12/D13 invariants
and all Rejected choices; do not rewrite the historical ADR-0001 body and do not
re-open standalone-vs-in-process.

**Resolution (2026-08-19 revision): APPLIED.** ADR-0002's `Amends:` declaration
and ADR-0001's immutable-body supersession table now cover the conflicting §5
host-ingest/deletion deck lifecycle + pointer rendering, §6 old endpoint wording,
§10 ingest-only resolver qualifier + endpoint paths/picker boundary, §14 `lesson_token`
deferral, §15 `load_lesson_doc()` defect, and §16 no-copied-source/pointer/export
claims. Each row states its standalone replacement. D3, D11, D12, D13 and every
Rejected choice are explicitly preserved; the historical ADR-0001 body is not
rewritten and standalone-vs-in-process is not re-opened.

### O13 — BLOCKING. O11's slice-0 startup exception contradicts PROMPTS.md's mandatory owner-facing `## Next step`.

PROMPTS.md correctly says inside NEW SLICE OPEN that slice-0 has **no ZIP** and
must read the repository after bootstrap. WORKFLOW §11 says the same. But the
canonical `## Next step` immediately beneath NEW SLICE OPEN still says:

```text
Open a fresh orchestrator chat ..., attach <zip path>, paste the prompt above...
```

For slice-0 no such handoff ZIP can exist. G1 makes the owner-facing `## Next
step` part of the binding dispatch contract and requires it to state what to
attach accurately. The O11 revision therefore fixed the executable startup
checks but left the transition instruction internally contradictory.

*Remedy:* make the canonical NEW SLICE OPEN `## Next step` explicitly branch on
slice-0: for slice-0, attach **no prior handoff ZIP**, open the repo after the
bootstrap receipt, and carry the exact `BOOTSTRAP MAIN HEAD` into the filled
prompt; for later slices, retain the existing handoff-ZIP instruction. Keep the
bootstrap worker and normal post-slice handoff path unchanged.

**Resolution (2026-08-19 revision): APPLIED.** PROMPTS.md's canonical NEW SLICE
OPEN owner-facing `## Next step` now has two explicit branches. Slice-0 opens a
fresh orchestrator on the exact post-bootstrap repository, attaches no prior ZIP,
and fills `<bootstrap main HEAD>` from the bootstrap receipt. Slice-1+ continues
to attach the validated handoff ZIP from normal closure. The bootstrap worker,
normal Worker OPEN preflight, and post-slice handoff contract are unchanged.

### O14 — BLOCKING. §4 conflates highlight candidate generation with note creation, so D11's required picker flow has no executable handoff.

ADR-0001 D11 remains in force: highlight capture generates candidates, the user
may multi-select/edit them in the picker, and only then are notes committed.
ADR-0001 §10 accordingly separates `/highlight` (candidate generation) from
`/cards` (commit). The revised ADR-0002 §4 instead says that at
`POST /vocab/highlight` the raw sentence/span/lesson payload arrives and then
describes **"the created note"** as being stored by that endpoint. D24's reader
request contains no selected candidate or sense, so `/vocab/highlight` cannot
know which note or notes to create before the D11 picker runs.

If `/vocab/highlight` only returns candidates, the ADR also does not say how
`sentence_text`, `lesson_label`, selected span, and optional provenance reach the
later commit without a live host fetch or unspecified temporary server state.
That is exactly the boundary D21/D22 were supposed to make explicit.

*Remedy:* define the two-stage capture contract normatively. The minimal
consistent form is: `/vocab/highlight` performs capture-time resolution and
returns candidates plus the normalized capture context needed for commit; after
the D11 picker, `/vocab/cards` receives the selected candidate(s) **and that
capture context**, then writes the note(s), frozen `example_de`, lesson/deck
metadata, and optional provenance. An explicitly designed persisted-draft
alternative is acceptable if its state/schema/cancellation semantics are
specified. Do not remove or bypass D11's picker/multi-select decision.

**Resolution (2026-08-19 revision): APPLIED.** D27 and revised §4 now define the
stateless two-stage boundary. `/vocab/highlight` validates the submitted sentence
and span, runs the one resolver locally, returns stable candidate/sense references
plus normalized `capture_context`, and performs no note or membership write. The
D11 picker retains multi-select and edit-before-add. `/vocab/cards` then receives
those selections, edits, the same by-value capture context, and an explicit deck
target; it revalidates them and atomically creates/reuses notes and memberships,
freezing `sentence_text` while storing span/lesson provenance only as optional
metadata. No host fetch and no unspecified temporary server state bridges the
calls. ADR-0002 §5 now requires the smoke baseline to exercise that split.


### Fresh cold review — 2026-08-19 (post O12–O14 revision)

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** O12's main supersession
rows, O13's slice-0/later-slice owner-instruction branch, and O14's by-value
highlight → picker → commit split are present on disk. Five blockers remain in
the binding cross-file contract; none re-opens standalone-vs-in-process or any
Rejected choice.

### O15 — BLOCKING. O13's NEW SLICE OPEN remedy is not one executable reusable prompt because its nested code fence closes the prompt early.

PROMPTS.md §Orchestrator — NEW SLICE OPEN opens the reusable prompt with a
triple-backtick fence, then the new slice-0 exact shell procedure opens another
triple-backtick fence. In Markdown that second fence closes the outer prompt.
The three required slice-0 checks therefore sit **outside** the reusable prompt,
and the text after them becomes a second fenced block. The mandatory owner-facing
instruction still says to "paste the prompt above", but there is no longer one
contiguous prompt to paste. A literal copy can omit the exact checks; copying the
whole rendered section risks mixing prompt text and owner instructions. That also
undercuts AGENTS G1/G3: the exact terminal procedure must reach the read-only
worker through the orchestrator prompt, not become an owner-side command fragment.

*Remedy:* make NEW SLICE OPEN a single syntactically valid prompt block while
keeping the slice-0 shell commands inside it and the `## Next step` outside it.
For example, use a four-backtick outer fence, or remove/indent the inner fence.
Preserve O13's two owner branches exactly: slice-0 uses the bootstrap HEAD with
no prior ZIP; slice-1+ uses the validated handoff ZIP.

**Resolution (2026-08-19 revision): APPLIED.** PROMPTS.md's canonical NEW SLICE
OPEN now uses one four-backtick outer prompt fence, leaving the exact slice-0
three-command shell block inside it. The owner-facing `## Next step` remains
outside the reusable prompt. O13's branches are unchanged: slice-0 uses the
bootstrap HEAD with no prior handoff ZIP; slice-1+ uses the validated handoff ZIP,
and the owner remains a courier rather than the terminal operator.

### O16 — BLOCKING. O12 still leaves ADR-0001 §11's completed-lecture-lemma requirement normative even though ADR-0002 makes that host-derived ranking input optional.

ADR-0001's supersession header says §11 stands except its rating UI and
D7-derived example-pointer wording. Its §11 ranking rule therefore still says
`known = deck lemmas ∪ completed-lecture lemmas`. ADR-0002 D22/D24 instead removes
live host callbacks and makes `known_lemmas?` optional by-value request input;
ADR-0002 §5 explicitly says that when it is absent the ranking degrades to deck
lemmas only. That paragraph then claims this is the "same fallback ADR-0001 §11
already defines", but ADR-0001 §11 defines no such fallback.

As written, one worker may treat completed-lecture lemmas as mandatory and
reintroduce a host dependency, while another follows ADR-0002 and permits the
deck-only fallback. This is the same incomplete-supersession failure class as
O10/O12.

*Remedy:* add a narrow ADR-0001 supersession row and matching ADR-0002 `Amends:`
entry for §11's `known` formula only. Preserve the ranking algorithm itself. State
that completed-lecture lemmas may influence ranking only when supplied by value
as optional `known_lemmas`; no live host fetch is allowed, and absence means
`known = deck lemmas`.

**Resolution (2026-08-19 revision): APPLIED.** ADR-0001's supersession header now
narrowly supersedes only §11's completed-lecture `known` formula, and ADR-0002's
`Amends:`/§5 state the replacement explicitly: optional request-supplied
`known_lemmas` may be unioned with deck lemmas; absent input means deck lemmas
only; no live host fetch exists. The ranking/scoring algorithm and D3, D11, D12,
and D13 remain unchanged.

### O17 — BLOCKING. ADR-0003's normative API section still names unprefixed `/review` and `/decks`, conflicting with ADR-0002 D25's all-`/vocab` API boundary.

ADR-0002 D25 and ADR-0001's supersession table require **every** standalone
endpoint to live under `/vocab`, and ADR-0002's header correctly describes
ADR-0003 as owning the `/vocab/review` request body and `/vocab/decks` response
body. But approved ADR-0003 §5 still normatively says `POST /review` and
`GET /decks`. ADR-0003's own `Amends:` line names those unprefixed paths too.
The confidence/mastery semantics are compatible; the route names are not.

The ADR-0001 header's attempt to reconcile them does not make ADR-0003 itself
unambiguous. A worker reading the approved API contracts can implement either
path spelling and claim compliance.

*Remedy:* record the prefix supersession explicitly wherever needed so ADR-0002
and ADR-0003 agree that ADR-0003 owns only the confidence/mastery **body
semantics**, while the actual routes are `/vocab/review` and `/vocab/decks` under
D25. Do not alter ADR-0003's D27–D31 scheduling/mastery decisions or reopen any
Rejected choice.

**Resolution (2026-08-19 revision): APPLIED.** ADR-0003's `Amends:` line and §5
now name `POST /vocab/review` and `GET /vocab/decks` and state that ADR-0002 D25
owns the `/vocab` route prefix while ADR-0003 owns only confidence/mastery body
semantics. D27–D31 and every Rejected choice are unchanged.

### O18 — BLOCKING. O14 carries an `overrides` object across the HTTP boundary but never defines the edit-before-add contract that the smoke baseline must exercise.

ADR-0002 §4 says the picker may edit the fields/overrides "allowed by the existing
edit-before-add flow" and shows each selection as
`{"ref": ..., "sense_id": ..., "overrides": {}}`. The reviewed files contain no
normative definition of that existing flow: ADR-0001 D8 only says structured
fields have nullable user overrides, and ADR-0001 §4 only says the picker is the
natural home for edit-before-add. No allowed override keys, value types,
validation rules, or persistence semantics are specified.

Multi-select itself is executable because `selections` is an array and each item
has a stable candidate/sense identity. Edit-before-add is not: an implementation
worker must invent the request schema and a smoke test cannot know which edit to
make or what persisted result proves success. O14's resolution therefore carries
"edits" nominally but not operationally.

*Remedy:* define the per-selection edit payload sufficiently to implement and
test it: enumerate the editable keys (or point to one normative schema that does),
their value/nullability rules, how each maps to persisted note override fields,
and rejection of unknown/invalid edits. Keep edits scoped per selected item so
multi-select can commit different edits for different candidates. The candidate
`ref`/`sense_id` identity remains the revalidated dictionary selection, not an
editable field.

**Resolution (2026-08-19 revision): APPLIED.** §4 now defines v1's per-selection
`overrides` object explicitly against the existing `note` columns:
`front_override`, `back_override`, and `gloss_user`, with string/null validation,
omitted-vs-null patch semantics, the `needs_gloss` restriction, direct persistence
mapping, atomic HTTP 422 rejection for unknown/invalid edits, duplicate-identity
rejection, and note-wide patch behaviour for reused D12 notes. Overrides are
independent per selected item; candidate `ref`/`sense_id` and dictionary/source
fields are never editable. §5 now makes multi-select with distinct overrides plus
an invalid-override/no-write case mandatory in the smoke baseline. The stateless
highlight → picker → `/vocab/cards` flow and by-value context remain unchanged.

### O19 — BLOCKING. An approving ADR cold review still cannot terminate mechanically under PROMPTS.md §Orchestrator — CLOSE step 3.

PROMPTS.md §ADR cold review requires the successful result
`APPROVED — remove NEEDS COLD REVIEW`, and the repository's ADR-0003 precedent
shows the marker is removed on approval. But PROMPTS.md §Orchestrator — CLOSE
step 3 says that **if any ADR was modified this session**, the next session must
be another ADR cold review. Removing the marker is an ADR modification. AGENTS G7
adds an exception only for an **objecting** review (next session = revision); it
does not define the approval case. STATE.md meanwhile requires the opposite
transition: after approval, remove the marker, close governance, then plan.

A literal application of the binding close contract therefore loops an approved
ADR back into cold review instead of allowing the planning transition. This does
not affect today's objecting close because G7 sends the next session to revision,
but it prevents the next successful review from closing cleanly.

*Remedy:* make the approval terminal condition explicit in PROMPTS.md/AGENTS.md:
administrative removal of `NEEDS COLD REVIEW` immediately following an approving
cold review does **not** itself trigger another cold review, while any substantive
ADR content change still does. Preserve G7's objection → revision → fresh-review
sequence.

**Resolution (2026-08-19 revision): APPLIED.** AGENTS G7 now defines both
objecting and approving terminal rules, and PROMPTS.md §Orchestrator — CLOSE step
3 keys the fresh-review trigger to substantive ADR changes. Recording an approving
review status and immediately removing `NEEDS COLD REVIEW` are administrative
review-status changes and do not by themselves trigger another review; any
substantive ADR modification still does. The objection → revision → fresh-review
sequence remains mandatory.

### Fresh cold review — 2026-08-19 (post O15–O19 revision)

**Verdict: APPROVED — `NEEDS COLD REVIEW` removed.** O15–O19 are resolved as
recorded, and their cross-file remedies are present in the binding repository
contract. PROMPTS.md's canonical NEW SLICE OPEN is one contiguous four-backtick
prompt with the exact slice-0 shell checks inside it and the owner-facing
`## Next step` outside it; slice-0 consumes the bootstrap HEAD with no prior ZIP,
while slice-1+ consumes the validated handoff ZIP, with terminal work still
delegated to workers.

ADR-0001 now supersedes only §11's completed-lecture `known` formula: the
ranking/scoring contract remains intact, optional by-value `known_lemmas` may be
unioned with deck lemmas, absent input means deck lemmas only, and no live host
fetch exists. D3, D11, D12, and D13 remain in force. ADR-0003's normative API
section now names `POST /vocab/review` and `GET /vocab/decks` under ADR-0002 D25
while retaining its accepted D27–D31 confidence/mastery semantics.

ADR-0002 D27/§4 now defines the edit-before-add boundary sufficiently for a cold
implementation worker and smoke test: the editable keys, types/nullability,
omitted-vs-null patch semantics, direct note-column persistence, atomic invalid
edit rejection, per-selection multi-select behaviour, reused-note patch semantics,
and immutable candidate identity are explicit. The same section preserves the
stateless highlight → picker → `/vocab/cards` flow with an explicit deck target,
round-tripped sentence/span/lesson context, optional provenance, and no live host
fetch or unspecified draft/session state.

AGENTS G7 and PROMPTS.md §Orchestrator — CLOSE now agree that recording approval
and immediately removing the marker are administrative review-status changes, not
a new substantive ADR revision; objection → revision → fresh review remains
binding for objected drafts, and any substantive ADR modification still requires
its own fresh cold review. No new blocking objection was found. The repository
still has no `.git`, `Makefile`, `docs/plan.md`, or `tasks/slice-0.md`, so no
project gate exists yet and no bootstrap or implementation action was dispatched
in this review.
