# Slice 8 reference inspection

This inspection is advisory input to a pre-Slice-8 planning repair. It does not
start Slice 8, amend an ADR, or authorize implementation. The donor repositories
were inspected read-only; no donor source should be copied into this project.

## Verified reference commits

Each donor had an empty `git status --porcelain` and its `HEAD` exactly matched
the requested pinned commit before inspection.

| Reference | Verified `HEAD` | Clean |
| --- | --- | --- |
| Lit | `c42ee1e96b8fd61f7256f61d715daef572e76e52` | yes |
| Web Awesome | `695c51fde74b03dc3b7ca021bbcecd337d173dd2` | yes |
| genanki | `73f1debfd74d25245403186d52a093e6d846da41` | yes |
| ts-fsrs-demo | `8291081ca3daebd8cc4b2b82a271a6eb1557e70c` | yes |
| full-stack-fastapi-template | `68adb40d37425f6f8668ec7e5a054500d045e43e` | yes |

## Lit findings

- The useful project pattern is a conventional Vite/TypeScript application with
  one small entry module, application components under `src/`, shared styles in
  their own modules, and tests kept beside or immediately below the code they
  exercise. The starter's package publishing machinery is irrelevant here.
- Extend `LitElement` directly. A base-class hierarchy is not justified for this
  application. API access belongs in a plain TypeScript client, not in a component
  superclass. A mixin or base class should be introduced only after repeated,
  concrete behavior exists.
- Use public reactive properties for values supplied by a parent and private
  reactive state for component-owned presentation state. Treat arrays and objects
  as immutable values so assignment triggers a predictable update. Use
  `requestUpdate()` only for data Lit cannot observe, and `updateComplete` only
  when code or tests truly must wait for rendered DOM.
- Data flows down as properties. User intent flows up as typed `CustomEvent`s with
  a small `detail` payload; events crossing shadow roots use `bubbles: true` and
  `composed: true`. Native `input`, `change`, `submit`, and `click` events remain
  preferable when they already express the interaction.
- Forms should use semantic `<form>`, `<label>`, and button/input controls. Handle
  submission at the form boundary, keep draft values local until submission, and
  surface server validation beside the relevant field and in a summary when
  needed. Do not mutate server state merely because a reactive field changed.
- The donor tests render a fixture in a real browser, interact through the DOM,
  await Lit updates, and assert visible/shadow-DOM behavior. For this app,
  Playwright can cover the small number of component and full-flow behaviors;
  adding Web Test Runner and Open WC solely to mirror the starter would add more
  tooling than the product needs.
- Retain strict TypeScript assumptions: modern ESM, DOM libraries, an ES2021-class
  target, `strict`, unused-code checks, fallthrough checks, and explicit override
  checking. Decorators are optional; ordinary static properties/private state are
  acceptable if decorator configuration creates friction.
- Accessibility starts with native semantics, visible labels, keyboard-operable
  controls, logical heading order, focus visibility, and status/error announcements.
  Shadow DOM and a component library do not make the assembled workflow accessible.

The smallest sensible component architecture is one `flashcard-app` shell, four
screen components (`capture-view`, `decks-view`, `review-view`, and
`import-export-view`), and only three initially shared domain components:
`candidate-picker`, `review-card`, and `audio-control`. A small `status-callout`
may be added only if the same status presentation is repeated. Ordinary HTML
inside a view is preferred over extracting one-use components.

## Web Awesome findings

- Install the package normally and import its default theme stylesheet once at the
  application entry. Cherry-pick component modules (for example the button module)
  instead of using the CDN autoloader or importing the whole component catalog.
  Web Awesome is itself Lit-based and its custom elements work directly in Lit
  templates.
- Use the normal bundler-oriented `dist` assets. Avoid icon components initially:
  their asset base-path configuration adds a deployment concern that visible text
  and small app-owned SVGs do not require.
- Define application semantic tokens such as `--fc-surface`, `--fc-text`,
  `--fc-accent`, `--fc-danger`, `--fc-space-*`, and `--fc-radius`. Map their
  defaults to stable Web Awesome theme primitives where useful. Components should
  consume `--fc-*` tokens so the application is not coupled throughout to the
  library's token vocabulary. Support the library's light/dark theme classes and
  preserve a usable fallback for each app token.
- Web Awesome controls provide useful form association, constraint-validation,
  focus, and keyboard behavior. They still require visible labels, meaningful hint
  and error text, correct heading/dialog structure, and application-level focus
  management. Server validation remains authoritative.
- Recommended initial subset: **button, input, dialog, spinner, and callout**.
  Button and input cover repeated high-value controls; dialog fits the capture
  candidate picker and destructive/commit confirmations; spinner covers genuine
  indeterminate waits; callout covers persistent validation, offline, and request
  failures.
- Prefer a native `select` for the few deck/language choices, native `textarea` and
  `progress` where needed, and semantic `article`/`section` containers instead of a
  card component. Do not initially add drawer, dropdown/menu, tabs, toast, or
  tooltip. Navigation has few direct destinations; persistent errors are safer
  than ephemeral toasts; critical help must be visible rather than tooltip-only.

Web Awesome is a control and token implementation detail, not the application's
component model, router, state layer, or visual architecture.

## genanki findings

- The minimal creation sequence is `Model(...)`, `Deck(...)`, `Note(...)`,
  `deck.add_note(note)`, then `Package(deck, media_files=...).write_to_file(...)`.
  A model supplies named fields, card templates, and CSS; a note supplies ordered
  field values, tags, and optionally an explicit GUID.
- The inspected donor identifies itself as genanki `0.13.1`. If planning accepts
  it, the project should pin `genanki==0.13.1` rather than silently following an
  unbounded release range.
- Deck and model IDs are integers. Generate stable, project-namespaced IDs once and
  commit them as constants; never generate fresh random IDs per export. Generate a
  note GUID with `genanki.guid_for(...)` from the application's durable local note
  identity or D47 stable semantic identity plus a namespace. Do not derive it from
  editable surface text or dictionary numeric IDs.
- `write_to_file` builds an Anki collection and packages it with a media manifest.
  It writes to a filesystem path, so an HTTP endpoint should create a private
  temporary directory, close the package fully, stream/read the completed file,
  and clean only those temporary artifacts. A fixed timestamp can stabilize
  database timestamps in tests, but byte-for-byte ZIP reproducibility should not
  be promised without a separate proof.
- Field content is Anki HTML. Escape literal user/dictionary text for HTML; the TSV
  export's tab/newline sanitation is not an HTML-escaping boundary. Add intentional
  `<br>` and `[sound:...]` markup only after escaping. Normalize or reject tag
  whitespace according to genanki's tag rules.
- Media files are supplied as paths. genanki stores numbered objects plus a manifest
  mapping them to basenames, and card audio is referenced as
  `[sound:basename.ext]`. Stage eligible bytes under collision-resistant,
  validated basenames such as a SHA-256 digest plus an allowlisted extension.
  Basenames must be unique; absolute local paths and original unsafe filenames must
  never appear in fields.
- Package tests should write to a temporary directory, inspect the ZIP media
  manifest and referenced filenames, and, where the test environment supports it,
  open/import the result with Anki's collection code. Unit tests should separately
  cover stable IDs/GUIDs, HTML escaping, filename collision handling, missing or
  ineligible audio, and cleanup after failure.
- genanki is **export only**. The exporter must not read or write `review_log`, map
  FSRS state into Anki cards, calculate due dates, or enter the live review path.
  Exported Anki cards start with Anki's ordinary new-card state and subsequently
  have independent scheduling inside Anki. The server remains authoritative for
  this application's FSRS state and history.

The minimal Python boundary is a pure `app/export.py` package builder that accepts
an already-observed immutable export DTO plus staged, redistribution-eligible media
bytes/paths and writes an `.apkg`. It may import genanki but must not open the user
database or dictionary, select senses, resolve lemmas, or select pronunciation
sources. `app/api.py` performs the authorized observation through existing domain
boundaries, passes the snapshot to the builder, and returns the completed artifact.

## ts-fsrs-demo findings

Safe UX inspiration:

- Use a centered, width-limited, single-task review surface with a quiet due-count
  header, a strong question/answer hierarchy, and generous space around the card.
- Hide the answer until an explicit full-width **Show answer** action. After reveal,
  keep the prompt visible, show the answer below a divider, and replace the reveal
  action with confidence controls.
- On narrow screens, lay confidence controls out in a comfortable two-column grid
  (with the fifth item spanning or placed deliberately); on wide screens, use one
  five-button row. Targets remain large and labels remain visible.
- Show server-returned new/learning/review or due counts when the API provides them;
  do not infer them from a client queue. Provide an explicit all-caught-up state.
- `Space` may reveal the answer and `1` through `5` may submit confidence. Ignore
  shortcuts while an input, textarea, select, contenteditable element, or IME
  composition is active; ignore repeats and prevent default only for a handled key.
- Each rating control should contain its number and the ADR-0003 confidence label.
  Meaning must not depend on color. Preserve focus and announce the newly revealed
  answer/status appropriately.

Unsafe reuse:

- Do not add `ts-fsrs`, React, Next.js, context/provider state, client card boxes,
  client due queues, interval previews, difficulty/stability displays, or donor
  scheduler hooks.
- Do not port the donor's four-grade model. This project has five raw confidence
  values with the accepted server mapping to FSRS ratings.
- Do not add undo merely because the donor shows it. `review_log` is append-only and
  no accepted server undo contract exists.
- Do not copy the donor's global keyboard handler without the editable-target,
  composition, repeat, and handled-key guards described above.

## FastAPI-template findings

- The useful packaging pattern is a separate frontend source directory whose Vite
  build emits hashed production assets, followed by a multi-stage container build
  that copies only the compiled frontend into the Python runtime image. Node/Bun is
  absent at runtime.
- The donor develops the frontend and backend as separate processes and uses a
  configured frontend API URL. For this localhost app, a Vite development proxy for
  relative `/vocab` requests is simpler and keeps the production and development
  client boundary identical. The proxy must preserve the configured loopback
  `Host`/`Origin` expectations, while the API client supplies
  `X-Flashcards-Request: 1` and the declared content type on mutations.
- Production should serve the built app from the existing FastAPI process. Keep all
  API routes under `/vocab`; serve `index.html` at `/` and hashed assets below one
  static asset path. Hash routing (`#/capture`, `#/decks`, `#/review`,
  `#/import-export`) avoids a catch-all server route and cannot shadow API routes.
- Locate bundled assets relative to the installed `app` package inside
  `create_app(...)`; do not read frontend configuration from the environment at
  import time and do not add module-level application state. Hashed assets may use
  long-lived immutable caching; `index.html` should be revalidated/no-cache.
- The container may listen on its internal interface, but host publication remains
  `127.0.0.1:8000:8000` as required by R8. Do not copy the donor's public ingress,
  Traefik, authentication, or deployment assumptions.
- Keep build-time frontend configuration minimal. Production API calls are
  same-origin and relative. Backend runtime behavior remains explicit factory
  configuration; no Vite environment variable becomes domain configuration.
- The donor's Playwright layout usefully separates configuration from scenario
  files, supports an explicit base URL, starts a development web server, uses CI
  retries/traces, and selects elements by role/label. This project needs no auth
  setup project or stored browser session.
- Do not adopt the donor's React/TanStack tree, generated API client, authentication,
  PostgreSQL/database layers, backend service structure, or broad compose stack.
  None of them informs the frozen flashcard backend.

## Recommended Slice-8 architecture

1. **Frontend source tree.** Add `frontend/` with `index.html`, `package.json`, a
   committed lockfile, strict `tsconfig.json`, `vite.config.ts`, and `src/`.
   Within `src/`, use `main.ts`, `flashcard-app.ts`, `api/client.ts`, `api/types.ts`,
   `views/{capture,decks,review,import-export}-view.ts`,
   `components/{candidate-picker,review-card,audio-control}.ts`, and
   `styles/{tokens,global}.css`. Put Playwright config and scenarios under
   `frontend/` so frontend commands are self-contained.
2. **Lit boundaries.** `flashcard-app` owns navigation and selects one hash-routed
   view. Views coordinate one user workflow. The three shared domain components
   render candidate selection, one review card, and pronunciation recording/
   playback. Keep one-use buttons, fields, headings, and containers as ordinary
   markup rather than components.
3. **State ownership.** The shell owns only current view and truly cross-view
   summaries. Each view owns its draft, busy/error state, and latest server
   response. `review-view` owns only transient reveal state and the currently
   returned card; it fetches the next card after each server mutation and never
   builds a parallel queue. `audio-control` may own an unsaved browser `Blob` and
   object URL, revoking the URL on replacement/disconnect. The backend owns all
   durable notes, cards, audio identity, review history, and scheduling.
4. **API-client boundary.** Use one small, stateless typed client over relative
   `/vocab` URLs. It parses a common success/error shape, supports cancellation,
   and distinguishes expected `409` stale-token conflicts and `422` validation
   failures. Every non-GET call adds `X-Flashcards-Request: 1`; JSON calls also add
   `Content-Type: application/json`, while multipart uploads let the browser set
   their boundary. No generated client or frontend access to SQLite is warranted.
5. **CSS tokens.** Define app-owned semantic `--fc-*` color, typography, spacing,
   radius, focus, and elevation tokens, mapping defaults to Web Awesome primitives.
   Use local component CSS plus a very small global reset/layout sheet. Meet focus,
   contrast, reduced-motion, zoom/reflow, and mobile target-size requirements; do
   not encode confidence meaning by color alone.
6. **Web Awesome subset.** Initially import exactly button, input, dialog, spinner,
   and callout plus the default theme. Use native select, textarea, progress,
   article, nav, and form elements. Any sixth component requires a demonstrated
   repeated need, not catalogue-driven adoption.
7. **Development build.** Use supported Node plus npm, Vite, strict TypeScript,
   Lit, and the two runtime UI dependencies (`lit` and Web Awesome). Commit the npm
   lockfile. Provide `dev`, `typecheck`, `build`, and `test:e2e` scripts. Vite proxies
   `/vocab` to the loopback FastAPI development server. Python gates remain the
   backend authority; the repaired brief must add explicit frontend gate commands.
8. **Production serving.** A Node build stage runs `npm ci` and the Vite build. The
   final Python image copies only `frontend/dist` to a fixed package-relative static
   directory. `create_app(...)` registers `/vocab` first, then `/` and the asset
   mount. Hash routes require no SPA catch-all. The same FastAPI origin serves UI
   and API, with Docker published only on host loopback.
9. **Playwright.** Configure one deterministic base URL and web-server procedure
   backed by temporary dictionary/user databases and fake audio providers; never
   use the maintainer's user data or a remote TTS service. Start with Chromium plus
   one mobile viewport, CI trace-on-first-retry, screenshots on failure, and
   role/label locators. Cover capture/picker stale-token behavior, deck browsing,
   reveal then confidence `1`–`5`, editable-field shortcut suppression, import/
   export, audio object-URL cleanup, R12 mutation headers, and a downloaded APKG's
   archive/media contract. Add Firefox/WebKit only when the baseline is stable or a
   browser-specific risk requires them.
10. **genanki boundary.** Add a pure `app/export.py` that receives immutable,
    sanitized export records and eligible staged media, constructs one stable model
    and deck plus stable note GUIDs, and writes a completed APKG. `app/api.py`
    observes data through current domain APIs and exposes a new APKG download route;
    retain the existing TSV Anki export unchanged. The brief must choose and freeze
    the additive route name and response media type before implementation.
11. **Audio in APKG.** Resolve audio through the accepted server audio-selection
    boundary at export-observation time. Custom audio has precedence. Automatic
    human/Piper audio is included only when a cached artifact exists and its source
    is explicitly eligible for redistribution under ADR-0005; export performs no
    network fetch. Stage selected bytes under a digest-based safe basename, pass the
    staged path to genanki, and append `[sound:basename.ext]` after escaping the
    visible field. Missing/ineligible audio yields a card without sound, not an
    invalid package. Never delete or rename the authoritative audio artifact.
12. **Rejected patterns.** Reject Lit internals/base hierarchies, Web Awesome as an
    application framework, CDN/autoloader loading, ts-fsrs and all client scheduling,
    donor four-grade controls, genanki scheduling/state import, template auth/DB/
    React/generated-client/public-ingress architecture, runtime Node, runtime LLMs,
    dictionary numeric IDs as export identity, rendered-card persistence, and any
    direct lecture-app code/data dependency.

This architecture leaves the existing FastAPI/SQLite service authoritative and
independently usable. Later lecture composition remains HTTP-only: the frontend
uses the same guarded `/vocab` contracts and does not acquire lecture application
imports or state.

## Explicit non-reuse decisions

- No donor source file is copied. Findings are patterns to reimplement in the local
  style under the repaired Slice-8 brief.
- No runtime LLM, LLM SDK, remote generation path, or browser-side model is added.
- No scheduler code or scheduling data comes from ts-fsrs-demo or genanki. No client
  queue, interval forecast, or local FSRS mirror is created.
- No Web Awesome autoloader, full catalogue import, router, state layer, icon asset
  loader, drawer/navigation system, or toast-first error handling is adopted.
- No full-stack-template authentication, React, TanStack, OpenAPI client generation,
  PostgreSQL, migration, deployment ingress, environment loader, or compose topology
  is adopted.
- No donor database/domain organization displaces `api -> deck -> render ->
  dictionary -> resolve`; the pure export builder is an API-side leaf and not a new
  resolver or user-state owner.
- No existing TSV export contract is replaced. APKG is additive and export-only.
- No Anki package contains this app's `review_log`, raw confidence history, FSRS
  due/stability/difficulty state, or a promise that scheduling transfers.
- No ineligible licensed audio, unsafe filename, source path, user database,
  dictionary database, credential, or remote fetch enters the APKG build.
- No public bind, wildcard CORS, relaxed host/origin guard, or omitted mutation
  header is borrowed from a donor development setup.

## Required brief changes

### Dependency addition

- Authorize and pin the Python runtime dependency `genanki==0.13.1`, after the
  planning worker verifies Python-version compatibility and transitive dependency
  acceptability. This is not permitted by the current brief's constrained
  `pyproject.toml` allowance.
- Authorize frontend manifests and a lockfile with minimal runtime dependencies
  `lit` and `@awesome.me/webawesome`, plus Vite, TypeScript, and Playwright as
  development dependencies. Pin/lock exact resolved versions during planning; the
  donor commit alone is not an npm version-selection policy.
- Extend dependency/gate review to confirm R1 remains satisfied and that Node is a
  build/test dependency only, absent from the production runtime image.

### Allowlist addition

- Add the new `frontend/` tree, its lockfile, Playwright configuration/tests, and
  necessary root build/gate wiring.
- Add the production frontend build/copy and static-serving files, including the
  Dockerfile and any compose/run file actually needed, while retaining the exact
  R8 host-loopback publication.
- Add `app/export.py`, APKG-focused backend tests, and the narrowly required edits
  to `app/api.py` and package/dependency metadata.
- Allow documentation/report updates required by WORKFLOW. Keep unrelated backend,
  dictionary-build, schema, and lecture-app files excluded.
- Reconcile this expansion with the current `tasks/slice-8.md`, whose allowlist and
  objective cover smoke/capture/import/pronunciation work but not a standalone Lit
  frontend, Docker frontend build, Playwright, or APKG export.

### Implementation guidance

- Freeze the twelve numbered architecture decisions above in the repaired brief,
  including the exact component list, state ownership, relative API client, initial
  five-component Web Awesome subset, hash routing, and build output location.
- Define the additive APKG endpoint path, content type, filename/content-disposition,
  observation/transaction semantics, export DTO, stable ID/GUID inputs, HTML
  escaping, temporary-file cleanup, size/error behavior, and redistribution-
  eligible audio rule before code begins.
- State expressly that the TSV route remains compatible and that APKG exports no
  server FSRS/review history. Anki scheduling after import is independent.
- Add executable frontend acceptance commands (`npm ci`, typecheck, production
  build, Playwright), production static-asset smoke checks, and APKG archive/media
  tests to the worker procedure and final gate. Tests use temporary data and fake
  providers and must exercise R12 through the browser client.
- Preserve the existing Slice-8 capture/import/ranking/pronunciation acceptance
  scope or explicitly split it into smaller governed slices if the combined repaired
  brief is too broad. Inspection does not decide that planning question.

### Architecture/governance

- **Accepted-ADR contradictions found: none.** A standalone Lit UI served by the
  existing factory is consistent with ADR-0002; server-authoritative FSRS and five
  confidence values remain consistent with ADR-0003; DE/EN-only display remains
  consistent with accepted ADR-0007; runtime-rendered cards, additive APKG export,
  and genanki as an export-only leaf are consistent with ADR-0001; and eligible
  audio packaging follows ADR-0005.
- Adding a dependency and changing the implementation allowlist require the normal
  pre-slice planning repair and gate/allowlist authorization. On the inspected
  design they do not, by themselves, require a new ADR.
- Return to architecture/governance before implementation if planning proposes any
  scheduler authority outside the server, persistence of rendered card faces,
  direct lecture coupling, a change to the exact `create_app(...)` contract,
  packaging audio without an ADR-0005 redistribution classification, a new learner
  meaning language, a public container bind, or a domain/dependency-direction
  change. Do not silently solve such a proposal inside Slice 8.
