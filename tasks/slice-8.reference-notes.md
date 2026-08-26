# Slice 8 reference inspection

## Verified reference commits

All five local reference repositories were inspected directly from `/home/saber/projects/flashcard-reference-repos`. Every repository was verified to have a clean working tree (`git status --porcelain` empty) and to match its expected pinned commit SHA exactly:

1. **lit**
   - Path: `/home/saber/projects/flashcard-reference-repos/lit`
   - Expected commit: `c42ee1e96b8fd61f7256f61d715daef572e76e52`
   - Verified commit: `c42ee1e96b8fd61f7256f61d715daef572e76e52`
   - Status: Clean, exact match.

2. **webawesome**
   - Path: `/home/saber/projects/flashcard-reference-repos/webawesome`
   - Expected commit: `695c51fde74b03dc3b7ca021bbcecd337d173dd2`
   - Verified commit: `695c51fde74b03dc3b7ca021bbcecd337d173dd2`
   - Status: Clean, exact match.

3. **genanki**
   - Path: `/home/saber/projects/flashcard-reference-repos/genanki`
   - Expected commit: `73f1debfd74d25245403186d52a093e6d846da41`
   - Verified commit: `73f1debfd74d25245403186d52a093e6d846da41`
   - Status: Clean, exact match.

4. **ts-fsrs-demo**
   - Path: `/home/saber/projects/flashcard-reference-repos/ts-fsrs-demo`
   - Expected commit: `8291081ca3daebd8cc4b2b82a271a6eb1557e70c`
   - Verified commit: `8291081ca3daebd8cc4b2b82a271a6eb1557e70c`
   - Status: Clean, exact match.

5. **full-stack-fastapi-template**
   - Path: `/home/saber/projects/flashcard-reference-repos/full-stack-fastapi-template`
   - Expected commit: `68adb40d37425f6f8668ec7e5a054500d045e43e`
   - Verified commit: `68adb40d37425f6f8668ec7e5a054500d045e43e`
   - Status: Clean, exact match.

---

## Lit findings

The `lit` repository (packages `lit`, `lit-element`, `lit-html`, `@lit/reactive-element`, `lit-starter-ts`) provides patterns for high-performance, standards-compliant web components without framework lock-in or heavy virtual DOM runtime overhead.

### Recommended Lit project/module organization
- **Feature/Component-centric layout**: Separate components into dedicated files within `src/components/`, named with a kebab-case prefix matching their custom element tag (e.g. `fc-app.ts`, `fc-review-screen.ts`, `fc-card-face.ts`, `fc-confidence-bar.ts`).
- **Styles module**: Maintain design tokens in a central `tokens.css` or `shared.ts` module providing reusable CSS template tagged literals (`css`...``).
- **Service/API separation**: Network communication and state management live in lightweight TypeScript services (`src/api/client.ts`), completely decoupled from rendering classes.
- **Entry point**: A root element `<fc-app>` bootstrapped in `index.html` and `src/main.ts`.

### Component and base-class patterns
- **Direct subclassing**: All UI components extend `LitElement` (`import { LitElement, html, css } from 'lit'`).
- **Static scoped styles**: Components define `static override styles = [sharedTokens, css`:host { display: block; } ...`];` utilizing Shadow DOM encapsulation while allowing CSS custom properties to pierce the boundary for theming.
- **Explicit Lifecycle usage**:
  - `connectedCallback()` / `disconnectedCallback()`: Used to attach and detach global window keyboard listeners (`Space`, `1`..`5`, `r`, `z`) and media streams.
  - `render()`: Pure declarative template function returning `TemplateResult`.
  - `updated(changedProperties: PropertyValues)`: Executes post-render actions such as programmatic focus on rating buttons or audio playback triggers.

### Reactive state and update patterns
- **Property Decorators**:
  - `@property({ type: ... })`: For public component inputs and parameters (e.g. `@property({ type: Object }) card!: CardRenderData`).
  - `@state()`: For internal reactive state (e.g. `@state() private _isRevealed = false`, `@state() private _loading = false`). Mutating `@state()` automatically schedules an asynchronous batch update.
- **Asynchronous Task State**:
  - Keep async state machine simple without heavy state-machine libraries: `status: 'idle' | 'loading' | 'success' | 'error'`, with `errorMessage: string | null`.

### Parent/child communication and custom events
- **Data down via properties**: Parents bind structured domain data directly to child properties (e.g. `<fc-card-face .card=${this.currentCard} .isRevealed=${this.isRevealed}></fc-card-face>`).
- **Events up via CustomEvent**: Children dispatch standard DOM events bubbling through Shadow DOM:
  ```ts
  this.dispatchEvent(new CustomEvent('fc-confidence-submit', {
    bubbles: true,
    composed: true,
    detail: { confidence: 4 }
  }));
  ```
  `composed: true` is strictly required for events that must cross Shadow DOM boundaries to ancestor containers.

### Form and input handling
- **Standard DOM binding**: `@input=${(e: Event) => this._text = (e.target as HTMLInputElement).value}`.
- **Checked/Value synchronization**: Use Lit's `live()` directive (`import { live } from 'lit/directives/live.js'`) when programmatic resets must overwrite uncommitted user input (e.g. resetting custom text fields).

### Testing approach
- Component unit tests with `@open-wc/testing` (`fixture`, `html`, `assert.shadowDom.equal`).
- End-to-end integration tests using Playwright against real rendered web components in Chromium.

### TypeScript configuration and build assumptions
- `experimentalDecorators: true` and `useDefineForClassFields: false` in `tsconfig.json` to ensure Lit's `@property()` and `@state()` decorators function correctly.
- `moduleResolution: "bundler"` or `"node"` with ES2022+ target.

### Accessibility conventions
- Use native interactive elements inside Shadow DOM (`<button>`, `<dialog>`, `<input>`) so keyboard focus and accessible roles come built-in.
- ARIA live regions (`role="status" aria-live="polite"`) for due card counts and state transitions.
- Proper heading hierarchy (`<h1>`, `<h2>`) and `aria-label` attributes on audio triggers and confidence buttons.

### Smallest sensible component architecture
For the standalone flashcard application, the minimal complete Lit component tree consists of exactly 8 components:
1. `fc-app`: Root router and shell (views: Decks, Review, Lookup/Capture, Import/Export).
2. `fc-deck-list`: Deck overview cards with due counts (`new`, `learning`, `review`), mastery %, deck creation/deletion.
3. `fc-review-screen`: Review session manager (fetches `/vocab/review/next`, passes card to face, coordinates confidence submission).
4. `fc-card-face`: Presentational component for Front (lemma, article, IPA, audio) and Back (Grammar, tri-state plural, Meaning blocks `{de, en}`, Examples, `⌄ more` progressive disclosure).
5. `fc-confidence-bar`: 5-level confidence buttons (`1`..`5`) with hotkey labels and interval previews.
6. `fc-audio-player`: Audio button with playback state and error fallbacks.
7. `fc-audio-recorder`: Recording/upload dialog with browser-local preview, Save as pronunciation, and Revert to automatic (ADR-0005).
8. `fc-capture-picker`: Two-stage capture / manual entry candidate picker with D11 multi-select, language selectors `{de, en}`, and asset token conflict handling (HTTP 409).

---

## Web Awesome findings

The `webawesome` repository (`packages/webawesome`) provides pre-built, accessible web components extending a custom base class (`WebAwesomeElement` on top of Lit).

### Installation and integration pattern with Lit
- Web Awesome components are standard Custom Elements built with Lit.
- Integration in a Lit project is direct: import the required component module (e.g. `import '@awesome.me/webawesome/dist/components/button/button.js'`), then use `<wa-button>` directly inside Lit `html` templates.
- Properties and events integrate seamlessly with Lit's standard binding syntax (`variant="brand"`, `@click=${this._onClick}`, `@wa-show=${this._onShow}`).

### Theme and design-token integration
- Web Awesome structures tokens using CSS Cascade Layers (`@layer wa-theme`, `@layer wa-component`) and CSS custom properties prefixed with `--wa-*`.
- Provides curated light and dark mode palettes (`--wa-color-surface-default`, `--wa-color-text-normal`, `--wa-color-brand-50`, etc.).
- Dark mode is activated via `.wa-dark` class or `color-scheme: dark`.

### Accessibility behavior
- Form controls implement `ElementInternals` for constraint validation and form association.
- Modal components (`wa-dialog`) provide automatic focus trapping, restore focus on close, escape key handling, and background inerting.

### Candidate evaluation
- `button` (`<wa-button>`): *Useful candidate* — provides built-in variant styles (`brand`, `neutral`, `danger`), size presets, and `loading` state spinner.
- `input` (`<wa-input>`): *Optional* — adds clearable buttons and prefix/suffix slots; native `<input>` is equally effective.
- `select` (`<wa-select>`, `<wa-option>`): *Optional* — accessible dropdown for deck switching or language selection.
- `dialog` (`<wa-dialog>`): *Useful candidate* — accessible modal with focus trap, backdrop, and smooth transitions for modals (candidate picker, audio recording, CSV import).
- `dropdown` (`<wa-dropdown>`): *Skip* — native buttons/menus or custom Lit popovers are simpler.
- `tabs` (`<wa-tab-group>`, `<wa-tab>`, `<wa-tab-panel>`): *Skip/Optional* — simple view switching in `<fc-app>` is cleaner with plain Lit state.
- `card` (`<wa-card>`): *Skip* — flashcard front/back faces require tailored typography and progressive disclosure; plain semantic `<article>` with CSS tokens is better.
- `spinner` (`<wa-spinner>`): *Useful candidate* — clean loading indicator for network requests and audio loading.
- `callout` / `toast` (`<wa-callout>`, `<wa-toast>`): *Useful candidate* — accessible feedback for success/error states (e.g. HTTP 409 dictionary changed, import statistics).
- `tooltip` (`<wa-tooltip>`): *Optional* — helpful for displaying hotkey shortcuts (`Space`, `1`..`5`).

### Recommended subset
- **Recommendation**: Web Awesome should NOT be adopted as the overall application architecture. Plain Lit with semantic HTML5 (`<button>`, `<dialog>`, `<input>`) and Vanilla CSS tokens is simpler, lighter, and eliminates third-party component version lock-in.
- If generic UI primitives are desired to accelerate polished styling, adopt ONLY a **minimal subset of 4 primitives**:
  1. `wa-button` (interactive buttons with loading state)
  2. `wa-dialog` (accessible modal dialogs)
  3. `wa-spinner` (compact loading indicator)
  4. `wa-callout` / `wa-toast` (error/info notification banners)

---

## genanki findings

The `genanki` repository was inspected to determine the exact Python boundary for exporting collections and decks to real `.apkg` files.

### Package, deck, model, and note creation API
- **Model**: Defines fields and card templates:
  ```python
  model = genanki.Model(
      model_id=1607392319,  # 31-bit deterministic integer
      name="German Vocabulary",
      fields=[
          {"name": "Front"},
          {"name": "Back"},
          {"name": "Grammar"},
          {"name": "Example"},
          {"name": "IPA"},
          {"name": "Audio"},
          {"name": "Tags"},
      ],
      templates=[
          {
              "name": "Recognition",
              "qfmt": "{{Front}}<br>{{IPA}}<br>{{Audio}}",
              "afmt": "{{FrontSide}}<hr id=\"answer\">{{Back}}<br><br>{{Grammar}}<br><br>{{Example}}",
          }
      ],
      css=".card { font-family: sans-serif; text-align: center; }",
  )
  ```
- **Deck**:
  ```python
  deck = genanki.Deck(deck_id=deck_id, name=deck_name)
  ```
- **Note**:
  ```python
  note = genanki.Note(
      model=model,
      fields=[front, back, grammar, example, ipa, audio_tag, tags_str],
      guid=genanki.guid_for(lemma_ref, sense_ref),
      tags=tags_list,
  )
  deck.add_note(note)
  ```
- **Package**:
  ```python
  package = genanki.Package(deck_or_decks=[deck])
  package.media_files = [path_to_audio_file1, path_to_audio_file2]
  package.write_to_file("output.apkg", timestamp=fixed_timestamp)
  ```

### Media-file inclusion
- `package.media_files` accepts a list of local file paths.
- During packaging, `genanki` creates a ZIP archive containing:
  - `collection.anki2` (SQLite collection database)
  - `media` (JSON mapping file: `{"0": "audio_filename.ogg", "1": "audio_filename2.ogg"}`)
  - Numbered binary media entries (`0`, `1`, `2`, ...) corresponding to the paths in `media_files`.
- **Filename invariant**: In note fields, audio must be referenced by its **basename only**: `[sound:audio_filename.ogg]`. Full paths or subdirectories break in Anki.

### Deterministic identifiers
- `model_id`: Fixed integer (e.g. deterministic hash of model name).
- `deck_id`: Integer derived deterministically from the database deck ID.
- `guid`: Use `genanki.guid_for(lemma_ref, sense_ref)` to produce stable Base91 note GUIDs that allow re-importing updated decks into Anki without creating duplicate cards.
- `timestamp`: The `timestamp: Optional[float]` parameter in `write_to_file()` allows hermetic builds and deterministic export testing.

### Escaping and sanitization concerns
- Fields are rendered as HTML in Anki. Plain text fields MUST be escaped with `html.escape()`.
- Literal newlines MUST be converted to `<br>`.
- Literal tabs must be converted to spaces.
- Tags cannot contain spaces (`ValueError` is raised by `_TagList._validate_tag` if a tag has spaces; convert spaces to underscores).
- `Note._check_invalid_html_tags_in_fields()` scans fields and emits a warning if raw unescaped `<` or `>` characters are found.

### Test patterns
- Generate `.apkg` to a temporary file via `tempfile.NamedTemporaryFile`.
- Inspect using `zipfile.ZipFile(apkg_path)`:
  - Verify `collection.anki2` exists and can be queried with `sqlite3`.
  - Verify `media` JSON mapping matches expected filenames.
  - Verify extracted audio bytes match source files.

### Minimal Python boundary
- Encapsulate `.apkg` generation in a dedicated module `app/export.py`.
- **Explicit Invariant**: `genanki` is **EXPORT ONLY**. It must never be imported or used in the review loop, note creation, or card scheduling paths. Server-side FSRS remains the sole authority.

---

## ts-fsrs-demo findings

The `ts-fsrs-demo` repository was inspected strictly as a **UX reference** for review interactions, responsive layout, and visual feedback.

### Safe UI inspiration to adopt
1. **Review screen layout**:
   - Clean, centered card container (`max-w-2xl` / `max-w-3xl`) with generous padding and subtle border/shadow.
   - Distinct separation between Question/Front and Answer/Back with an elegant horizontal divider on reveal.
2. **Status bar indicator**:
   - Top status bar displaying pill badges with colored dots for card queue counts:
     - `New` (sky/blue dot)
     - `Learning` (amber/orange dot)
     - `Review` (emerald/green dot)
   - Active queue highlighted with tabular numeric counts.
3. **Answer reveal interaction**:
   - Before reveal: Large, prominent "Show answer" primary action button with a `Space` keyboard shortcut badge.
   - On reveal: Seamlessly replaces the reveal button with the rating controls.
4. **Confidence controls and visual hierarchy**:
   - Color-coded rating buttons with distinct semantic accents:
     - 1: Red/Rose ("Not at all")
     - 2: Orange ("Barely")
     - 3: Amber/Yellow ("Somewhat / Hard")
     - 4: Sky/Blue ("Good / Confident")
     - 5: Emerald/Green ("Never forget")
   - Clear visual hierarchy: Confidence label prominent, next interval preview subtle (`text-xs opacity-90`), keyboard shortcut badge (`1`..`5`) anchored in the corner.
5. **Keyboard navigation**:
   - `Space`: Reveal answer.
   - `1`..`5`: Submit corresponding confidence level.
   - `r`: Play/replay pronunciation audio.
   - `Ctrl+Z` / `Cmd+Z`: Undo/revert review if supported.

### Explicit non-reuse / forbidden patterns
- **NO `ts-fsrs` npm dependency**: Do not install or import `ts-fsrs` in the frontend.
- **NO client-side scheduling**: Do not compute intervals, stability, difficulty, or due dates in the browser.
- **NO client-side card state duplication**: Do not store review cards or schedules in browser memory/IndexedDB.
- **NO 4-grade rating schema**: `ts-fsrs-demo` uses 4 FSRS grades (`Again`, `Hard`, `Good`, `Easy`). The flashcard application MUST strictly adhere to ADR-0003: 5 confidence buttons on the UI, mapped server-side to FSRS.

---

## FastAPI-template findings

The `full-stack-fastapi-template` repository was inspected strictly for **packaging, serving, build-stage, and test patterns**.

### Frontend build and output organization
- Frontend is placed in a sibling directory (`frontend/`) using Vite.
- `vite.config.ts` outputs production build directly to the backend's static directory (`outDir: "../app/static"`, `emptyOutDir: true`).

### Development server and proxy patterns
- During development, Vite runs on port `5173` with HMR.
- `vite.config.ts` configures proxy for `/vocab` requests:
  ```ts
  server: {
    proxy: {
      '/vocab': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
  ```
- Dev proxy ensures localhost development can test browser flows without disabling security headers.

### Production static-asset serving
- In production, FastAPI serves the compiled SPA assets directly using Starlette's `StaticFiles`:
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
  ```
- API routes live under `/vocab/...` prefix, preventing routing collision with static assets.

### Docker multi-stage build pattern
- Multi-stage `Dockerfile`:
  - **Stage 1 (Frontend build)**: Node/Bun image copies `frontend/`, runs `npm ci && npm run build`, outputting compiled bundle.
  - **Stage 2 (Runtime image)**: Python 3.12-slim base installs Python dependencies (`pip install .`, `piper-tts`), downloads models, copies backend `app/`, and copies compiled frontend from Stage 1 into `/app/app/static`.
- Single container serves both API and static frontend on `127.0.0.1:8000`.

### Playwright organization
- `playwright.config.ts` located at project root or in `frontend/`.
- Configured with `baseURL: 'http://127.0.0.1:8000'`.
- `webServer` section automatically starts the backend server when running tests locally.
- E2E tests exercise complete user flows in headless Chromium.

### Explicit non-reuse decisions
- **NO multi-tenant authentication/OAuth2/JWT**: Flashcard app is local-first, single-user.
- **NO PostgreSQL / SQLModel / Alembic**: Backend is already frozen on SQLite with `reference/schema.sql`.
- **NO React / TanStack Router**: Frontend will use Lit web components.
- **NO complex generated API client SDK**: A minimal typed `fetch` wrapper is sufficient and keeps dependencies near zero.

---

## Recommended Slice-8 architecture

Based on the synthesis of all five reference repositories and the accepted ADR constraints (ADR-0001 through ADR-0005, ADR-0007), here is the concrete architecture recommendation:

### 1. Frontend source-tree layout
```text
frontend/
├── package.json               # Dependencies: lit, @types/..., vite, typescript
├── tsconfig.json              # ES2022, decorators enabled
├── vite.config.ts             # Proxy to :8000, outDir: ../app/static
├── index.html                 # HTML shell loading src/main.ts
├── src/
│   ├── main.ts                # Custom elements registration & router initialization
│   ├── api/
│   │   └── client.ts          # Typed fetch client with R12 header injection
│   ├── types/
│   │   └── api.ts             # TypeScript interfaces matching FastAPI schemas
│   ├── styles/
│   │   ├── tokens.css         # CSS design tokens (colors, spacing, typography)
│   │   └── shared.ts          # Shared Lit CSS tagged template literals
│   └── components/
│       ├── fc-app.ts          # Root view shell and navigation
│       ├── fc-deck-list.ts    # Decks overview, due counts, mastery %
│       ├── fc-review-screen.ts# Review loop manager (Space, 1-5 keys)
│       ├── fc-card-face.ts    # Card front/back presentation & progressive disclosure
│       ├── fc-confidence-bar.ts # 5-level confidence buttons with shortcuts
│       ├── fc-audio-player.ts # Audio playback button & status
│       ├── fc-audio-recorder.ts # Custom recording/upload with preview/save/revert
│       ├── fc-capture-picker.ts # D11 candidate picker & 2-stage commit dialog
│       └── fc-import-export-dialog.ts # CSV import & TSV/APKG export
└── tests/
    └── e2e/
        ├── review.spec.ts     # Review loop and confidence mapping E2E
        ├── capture.spec.ts    # Two-stage capture and candidate picker E2E
        ├── audio.spec.ts      # Audio playback and recording lifecycle E2E
        └── import-export.spec.ts # CSV import and TSV/APKG export E2E
```

### 2. Lit component boundaries
- Components are strictly decoupled:
  - `fc-app`: Manages active screen view (`decks` | `review` | `lookup` | `import` | `export`) and toast notification overlay.
  - `fc-deck-list`: Reads deck summary from `/vocab/decks`, displays due counts and mastery %, dispatches `fc-open-review`.
  - `fc-review-screen`: Calls `GET /vocab/review/next`, passes payload to `fc-card-face`, handles `fc-submit-confidence` to `POST /vocab/review`.
  - `fc-card-face`: Presentational only. Displays front headword, IPA, audio trigger; back grammar (tri-state noun plural), meaning blocks for `{de, en}`, and example sentences.
  - `fc-confidence-bar`: Presentational 5-button bar with hotkeys (`1`..`5`).
  - `fc-audio-player` & `fc-audio-recorder`: Manages audio triggers, microphone recording via `MediaRecorder`, file uploads, browser-local preview, Save as pronunciation, and Revert to automatic (ADR-0005).
  - `fc-capture-picker`: Implements ADR-0002 §4 Stage-1 `/vocab/highlight` & `/vocab/lookup` response rendering, multi-select, language toggles, user overrides, and Stage-2 `/vocab/cards` commit.
  - `fc-import-export-dialog`: Handles CSV word-list upload (`POST /vocab/import/csv`), TSV download (`GET /vocab/export/anki`), and APKG download (`GET /vocab/export/apkg`).

### 3. State ownership
- **Authoritative state**: Resides 100% in the backend SQLite database accessed via FastAPI.
- **Client state**: Ephemeral UI state only (active view, answer revealed boolean, active candidate checkboxes, current audio recording Blob, toast alerts).
- **Zero local database duplication**: No IndexedDB card caches, no client-side scheduling.

### 4. API-client boundary
- `frontend/src/api/client.ts` wraps standard `window.fetch`.
- Automatically injects required AGENTS R12 security headers:
  - `X-Flashcards-Request: 1` on all non-GET requests.
  - `Content-Type: application/json` for JSON endpoints.
- Provides typed methods matching the FastAPI backend routes.
- Handles HTTP 409 `dictionary_changed` by notifying the user to refresh candidate selections.

### 5. CSS token strategy
- Design tokens defined in `frontend/src/styles/tokens.css` as CSS custom properties:
  - Dark/Light mode color schemes:
    - Backgrounds: `--fc-bg-base`, `--fc-bg-surface`, `--fc-bg-surface-raised`
    - Text: `--fc-text-primary`, `--fc-text-secondary`, `--fc-text-muted`
    - Accents: `--fc-accent-brand`, `--fc-accent-focus`
    - Confidence levels: `--fc-conf-1` (rose), `--fc-conf-2` (orange), `--fc-conf-3` (amber), `--fc-conf-4` (sky), `--fc-conf-5` (emerald)
  - Typography: System sans-serif font stack (`Inter`, `system-ui`, `-apple-system`, `sans-serif`) with tabular numbers for stats.

### 6. Exact Web Awesome subset
- Adopt pure Lit + Vanilla CSS tokens as the primary implementation.
- If Web Awesome is used for UI primitives, restrict strictly to:
  1. `wa-button`
  2. `wa-dialog`
  3. `wa-spinner`
  4. `wa-callout` / `wa-toast`

### 7. Dev build tooling
- Use **Vite**: instant server start, fast ES module HMR, simple `vite.config.ts` proxy forwarding `/vocab` to FastAPI at `http://127.0.0.1:8000`.

### 8. Production frontend-serving approach
- Vite compiles static bundle into `app/static/`.
- FastAPI mounts `StaticFiles` at `/` with `html=True`.
- Backend loopback guard (AGENTS R12) ensures unauthenticated LAN access remains blocked.

### 9. Playwright setup
- `playwright.config.ts` configuring Chromium headless tests against `http://127.0.0.1:8000`.
- Integrated into `make gate` or standalone test command.

### 10. genanki integration boundary
- Python module `app/export.py` using `genanki>=0.13.0`.
- Strictly read-only export producing `.apkg` packages containing Anki models, notes, and embedded audio media files.
- Endpoint: `GET /vocab/export/anki/apkg?deck_id=...`.
- Invariant: genanki is strictly EXPORT-ONLY.

### 11. Audio-in-APKG mechanism
- Custom and cached audio files referenced by basename: `[sound:custom_123.ogg]`.
- Files attached to `genanki.Package.media_files`.
- Built-in Anki player handles audio on card reveal.

---

## Explicit non-reuse decisions

The following patterns and libraries from the reference repositories are **explicitly rejected** from adoption in the flashcard application:

| Reference Repository | Rejected Pattern / Technology | Rationale |
|---|---|---|
| `ts-fsrs-demo` | `ts-fsrs` npm package | Violates authoritative server-side FSRS invariant (ADR-0001, ADR-0003, AGENTS R6). |
| `ts-fsrs-demo` | Client-side scheduling & interval calculations | Backend Python FSRS scheduler is the single source of truth. |
| `ts-fsrs-demo` | 4-grade rating interface | ADR-0003 explicitly mandates a 5-level confidence UI mapped server-side. |
| `ts-fsrs-demo` | React / Next.js framework | Project technology stack is Lit web components. |
| `full-stack-fastapi-template` | Authentication / JWT / OAuth2 / multi-user models | Flashcard app is single-user and local-only (ADR-0001 §2). |
| `full-stack-fastapi-template` | PostgreSQL, SQLModel, Alembic | Backend is frozen on SQLite with `reference/schema.sql`. |
| `full-stack-fastapi-template` | React + TanStack Router | Project uses Lit. |
| `full-stack-fastapi-template` | Generated `@hey-api/openapi-ts` SDK | Adds unnecessary build complexity; a small handwritten typed client is simpler and more auditable. |
| `genanki` | Any runtime / review / scheduling usage | `genanki` is strictly an export utility for `.apkg` generation. |
| `webawesome` | Monolithic framework adoption | Full Web Awesome adoption is unnecessary; plain Lit/HTML/CSS is simpler. |
| `lit` | Copying Lit internal repository scripts | Use standard public `lit` npm package. |

---

## Required brief changes

To implement the complete standalone product in Slice 8 (or properly sequence the remaining work between Slice 8 smoke repair and frontend delivery), the following brief adjustments are required:

### Dependency addition
1. **Backend (`pyproject.toml`)**:
   - Add `genanki>=0.13.0` to `dependencies` for `.apkg` export capability (as anticipated in ADR-0001 §7 / §14).
2. **Frontend (`frontend/package.json`)**:
   - `lit` (core web component library).
   - `@awesome.me/webawesome` (optional, only if the minimal 4-primitive subset is used).
   - `vite`, `typescript`, `@types/node` (dev dependencies).
   - `@playwright/test` (E2E testing).

### Allowlist addition
For the slice implementing the frontend and export extensions:
- `frontend/` (entire directory: `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/**`, `tests/e2e/**`).
- `app/export.py` (new module for `.apkg` generation).
- `app/static/` (compiled frontend distribution directory).
- `pyproject.toml` (for `genanki` dependency and tool inclusion).
- `app/api.py` (mounting static files and `/vocab/export/anki/apkg` endpoint).

### Implementation guidance
1. **Smoke baseline repair**: `reference/smoke_test.py` must fix the `sys.path` import defect, open `reference/schema.sql` explicitly, and remove `reference` exclusions from `pyproject.toml` (mypy, ruff, pytest).
2. **Strict R12 Enforcement**: Frontend API client MUST automatically attach `X-Flashcards-Request: 1` to all non-GET requests to pass the backend browser security middleware.
3. **5-Level Confidence UI**: Ensure the review UI exposes 5 distinct confidence rating buttons (`1`..`5`) per ADR-0003, with `Space` for answer reveal and `1`..`5` hotkeys for rating.
4. **ADR-0005 Audio Lifecycle**: Ensure custom audio recording preview remains browser-local before explicit Save, and Revert restores automatic selection without deleting files.
5. **Two-Stage Capture Flow**: Implement `/vocab/highlight` candidate resolution, D11 multi-select, and atomic `/vocab/cards` commit with asset token verification (handling HTTP 409).

### Architecture / governance considerations
- **No ADR Contradictions**: The findings and recommendations are fully coherent with accepted ADRs (ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0007) and AGENTS rules (R1, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, C1, C2, C3).
- **Scope Sequencing**: `tasks/slice-8.md` currently covers backend smoke repair, two-stage capture/import flows, example ranking, and pronunciation E2E smoke. A pre-slice-8 planning repair session can either incorporate the frontend/export implementation into an expanded Slice-8 brief or cleanly schedule it as a planned follow-on slice.
