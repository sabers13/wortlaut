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

### Donor evidence
Inspection of the pinned Lit repository (`packages/lit`, `packages/lit-element`, `packages/lit-html`, and `packages/lit-starter-ts`) confirms:
- **Component foundation**: Standard custom elements extending `LitElement`, using tagged template literals (`html`...``, `css`...``) with Shadow DOM encapsulation.
- **Decorator support**: Legacy experimental TypeScript decorators (`@customElement`, `@property`, `@state`, `@query`).
- **Reactive updates**: Reactive property/state mutation automatically schedules asynchronous batched re-renders via `requestUpdate()`.
- **Event patterns**: Standard DOM events; `CustomEvent` with `bubbles: true` and `composed: true` when piercing Shadow DOM boundaries to parent containers.
- **Testing approach**: Unit/component testing with `@open-wc/testing` and Web Test Runner (`@web/test-runner`) using Mocha/Chai.
- **TypeScript configuration in donor**: `packages/lit-starter-ts/tsconfig.json` specifically uses:
  - `target: "es2021"`
  - `module: "es2020"`
  - `moduleResolution: "node"`
  - `experimentalDecorators: true`
  - `strict: true`
  - Note: The pinned starter does *not* explicitly set `useDefineForClassFields: false`, nor does it use `moduleResolution: "bundler"` or `target: "ES2022"`.

### Slice-8 adaptation
Our flashcard application can adopt Lit's core component model while deliberately choosing a modern, Vite-compatible toolchain during implementation:
- **TypeScript configuration**: Our standalone `frontend/tsconfig.json` can target `ES2022` / `ESNext` with `moduleResolution: "bundler"`, `experimentalDecorators: true`, and `useDefineForClassFields: false` (to ensure predictable decorator property initialization under Vite/esbuild).
- **Smallest sensible component tree (8 components)**:
  1. `fc-app`: Root router and layout shell (views: Decks, Review, Lookup/Capture, Import/Export).
  2. `fc-deck-list`: Deck summary cards with due counts (`new`, `learning`, `review`), mastery %, deck creation/deletion.
  3. `fc-review-screen`: Review session coordinator (fetches `/vocab/review/next`, passes card to face, coordinates confidence submission).
  4. `fc-card-face`: Presentational component for Front (lemma, article, IPA, audio trigger) and Back (Grammar block with tri-state plural, Meaning blocks `{de, en}`, Examples, `⌄ more` progressive disclosure).
  5. `fc-confidence-bar`: 5-level confidence rating buttons (`1`..`5`) with hotkeys and interval previews.
  6. `fc-audio-player`: Pronunciation playback button with loading, playing, and fallback error states.
  7. `fc-audio-recorder`: Custom recording/upload dialog with browser-local preview, Save as pronunciation, and Revert to automatic (ADR-0005).
  8. `fc-capture-picker`: Two-stage capture / lookup candidate picker with D11 multi-select, language selectors `{de, en}`, and asset token conflict handling (HTTP 409).
- **Communication pattern**: Properties down (`.card=${card}`), custom events up (`@fc-confidence-submit=${this._onSubmit}`).
- **Testing**: End-to-end user-flow validation via Playwright against the served application.

---

## Web Awesome findings

The `webawesome` repository (`packages/webawesome`) provides pre-built, accessible web components extending a Lit-based base class (`WebAwesomeElement`).

- **Donor evidence**:
  - Architecture: Collection of custom elements extending Lit, distributed as ES modules (e.g. `@awesome.me/webawesome/dist/components/button/button.js`).
  - Styling and tokens: Uses CSS custom properties prefixed with `--wa-*` scoped within CSS Cascade Layers (`@layer wa-theme`, `@layer wa-component`). Light and dark theme palettes are activated via `.wa-dark` or `color-scheme: dark`.
  - Accessibility: Built-in ARIA roles, `ElementInternals` form association, and accessible focus management in modal components (`wa-dialog`).
- **Architectural boundary**: Lit owns the application architecture; Web Awesome must NEVER become the application's framework or architecture. Plain Lit with semantic HTML5 (`<button>`, `<dialog>`, `<input>`) and Vanilla CSS tokens remains the primary, preferred implementation.
- **Candidate evaluation**:
  - `button` (`<wa-button>`): *Useful candidate* — provides built-in variant styles (`brand`, `neutral`, `danger`), size presets, and `loading` state spinner.
  - `dialog` (`<wa-dialog>`): *Useful candidate* — accessible modal with focus trap, backdrop, and smooth transitions for modals (candidate picker, audio recording, CSV import).
  - `spinner` (`<wa-spinner>`): *Useful candidate* — compact loading indicator for network requests and audio loading.
  - `callout` / `toast` (`<wa-callout>`, `<wa-toast>`): *Useful candidate* — accessible feedback for success/error states (e.g. HTTP 409 dictionary changed, import statistics).
  - `input`, `select`, `dropdown`, `tabs`, `card`, `tooltip`: *Skip / Optional* — native HTML5 controls or lightweight Lit templates are simpler and eliminate unnecessary dependencies.
- **Recommended small subset**: If adopted to accelerate polished UI styling, restrict strictly to the 4 primitives:
  1. `wa-button`
  2. `wa-dialog`
  3. `wa-spinner`
  4. `wa-callout` / `wa-toast`

---

## genanki findings

The `genanki` repository was inspected to determine the minimal Python boundary needed to generate real `.apkg` export packages.

- **Donor evidence**:
  - Version: The pinned donor version is `genanki 0.13.1` (defined in `genanki/version.py`).
  - Core API: `Model`, `Deck`, `Note`, and `Package` in `genanki/__init__.py`.
  - Media inclusion: `package.media_files` accepts file paths. In generated packages, binary files are stored under numbered filenames (`0`, `1`, `2`, ...) in the ZIP root with a JSON dictionary `media` mapping indices to original filenames: `{"0": "audio.ogg"}`. Card fields reference audio strictly by **basename**: `[sound:audio.ogg]` (never a path).
  - Deterministic identifiers: 31-bit integers for `model_id` and `deck_id`; `genanki.guid_for(lemma_ref, sense_ref)` for stable Base91 note GUIDs.
  - Sanitization / Escaping: HTML escaping via `html.escape()`, newlines as `<br>`, and tag spaces disallowed.
- **Boundary and invariants**:
  - Export-only boundary: Encapsulate in `app/export.py` with `export_anki_apkg(...) -> bytes`.
  - Authoritative Scheduler Invariant: `genanki` is **EXPORT ONLY**. It must never be imported into review, card creation, or scheduling flows. The Python `fsrs` scheduler in the FastAPI backend remains the sole authority.
  - Dependency pinning: In `pyproject.toml`, pin the inspected version deterministically as `genanki==0.13.1` (rather than an open-ended `>=0.13.0` range).

### Determinism caveat

In `genanki/package.py`, the `Package` constructor normalizes media files via:
```python
self.media_files = list(set(media_files or []))
```
Because Python's `set()` iteration order is subject to hash randomization across process invocations, the internal numbering (`0`, `1`, ...) and `media` JSON key ordering may vary between separate runs even when input lists are identical.
Therefore, passing a fixed `timestamp: Optional[float]` to `write_to_file()` ensures deterministic note/card database timestamps, but **does NOT guarantee bitwise byte-identical `.apkg` ZIP archives across different process runs**.

Automated tests for `.apkg` export MUST therefore use **semantic validation**:
1. `.apkg` opens successfully as a valid `zipfile.ZipFile`.
2. `collection.anki2` exists and is a readable SQLite database.
3. Expected deck, model, and note records exist in the SQLite tables.
4. Stable GUIDs match expected deterministic values.
5. Expected media manifest entries exist in the `media` JSON index.
6. Media basenames in note fields match `[sound:filename]` syntax.
7. Expected audio payload bytes in the archive match source audio files.
8. The package imports structurally into Anki collections without errors.

---

## ts-fsrs-demo findings

The `ts-fsrs-demo` repository was inspected strictly as a **UX reference** for card layout, interaction mechanics, and review flow.

### Donor UX
The pinned donor demonstrates:
- **Card layout**: Centered container with status header, large question typography, and answer section.
- **Status bar**: Pill badges showing due card counts for `New`, `Learning`, and `Review` queues.
- **Answer reveal**: Prominent "Show answer" button with a `Space` keyboard shortcut indicator.
- **Review rating**: **4 FSRS grade buttons** (`Again`, `Hard`, `Good`, `Easy`) mapped to keyboard keys `1`, `2`, `3`, and `4`.
- **Interval previews**: Displaying predicted next due intervals on rating buttons.
- **Rollback**: `Ctrl+Z` / `Cmd+Z` shortcut to undo the previous review step.

### Slice-8 adaptation
- **5-Level Confidence UI**: While the donor uses 4 FSRS grades, our flashcard application MUST strictly adhere to ADR-0003 by providing **5 confidence rating buttons**:
  1. "Not at all" (Rose / Red accent) — hotkey `1`
  2. "Barely" (Orange accent) — hotkey `2`
  3. "Somewhat / Hard" (Amber / Yellow accent) — hotkey `3`
  4. "Good / Confident" (Sky / Blue accent) — hotkey `4`
  5. "Never forget" (Emerald / Green accent) — hotkey `5`
- **Server-Side Mapping**: The frontend submits the raw integer confidence `1`..`5` directly to `POST /vocab/review`; all FSRS interval and state calculations happen server-side.
- **Suggested Shortcut**: Hotkey `r` for replaying pronunciation audio is a **suggested Slice-8 UX adaptation** (not evidenced in the donor codebase).
- **Progressive disclosure**: `⌄ more` toggle for detailed grammatical principal parts and secondary examples per ADR-0001 §11.

### Explicit non-reuse
- **NO `ts-fsrs` npm package**: The `ts-fsrs` dependency is completely forbidden in the frontend.
- **NO client-side scheduling**: No interval calculation, stability/difficulty estimation, or due-date computation in the browser.
- **NO client-side card state duplication**: No IndexedDB or local memory store replicating flashcard states.
- **NO React / Next.js architecture**: Application is implemented with Lit web components.

---

## FastAPI-template findings

The `full-stack-fastapi-template` repository was inspected for **packaging, serving, Docker multi-stage builds, and test organization**.

### Donor evidence
- **Frontend build output**: `frontend/vite.config.ts` outputs production build artifacts to `outDir: "../backend/app/frontend"` with `emptyOutDir: true`. It does *not* contain a `/vocab` proxy configuration.
- **FastAPI frontend-serving helper**: `backend/app/main.py` serves the frontend using a custom helper:
  ```python
  FRONTEND_DIR = Path(__file__).parent / "frontend"
  app.frontend("/", directory=FRONTEND_DIR)
  ```
  It places the compiled frontend assets directly inside a subfolder of the backend application package (`backend/app/frontend`).
- **Docker build pattern**: Multi-stage `Dockerfile` using:
  - **Stage 1 (`frontend-build`)**: `FROM oven/bun:1 AS frontend-build`, runs `bun install` and `bun run build`. (Note: The donor uses Bun, not `npm ci`).
  - **Stage 2 (`runtime`)**: `FROM python:3.14`, installs Python dependencies via `uv sync`, copies `app/`, copies compiled frontend from `frontend-build` (`COPY --from=frontend-build /app/backend/app/frontend /app/backend/app/frontend`), and runs `fastapi run`.
- **Playwright configuration**:
  - `frontend/playwright.config.ts` defaults to `baseURL: 'http://localhost:5173'`.
  - `webServer` is configured to start the frontend dev server locally via `command: 'bun run dev'`.
  - It does *not* default to `http://127.0.0.1:8000` for local test execution.

### Slice-8 adaptation
- **Authoritative source vs build output**:
  - `frontend/` is the authoritative handwritten browser source directory.
  - `app/frontend/` (or `app/static/`) is the GENERATED build output destination and is never hand-maintained.
- **Vite development proxy**: During local frontend development, configure `frontend/vite.config.ts` to proxy `/vocab` requests to the FastAPI backend running at `http://127.0.0.1:8000`.
- **Production serving in FastAPI**: Mount compiled static assets using Starlette/FastAPI static file serving (e.g. `StaticFiles(directory=..., html=True)`) at root `/`, while preserving all `/vocab/...` API routes. Loopback security checks (AGENTS R12) apply to all routes.
- **Product E2E testing in Playwright**: As a **deliberate Slice-8 adaptation**, our Playwright E2E suite will test directly against the standalone FastAPI-served application at `http://127.0.0.1:8000` to validate the real production serving boundary, loopback security headers, and backend FSRS integration.

---

## Recommended Slice-8 architecture

Synthesizing the donor lessons into a concrete, minimal architecture:

```text
flashcard/
├── app/
│   ├── api.py                 # FastAPI application factory & routes (/vocab)
│   ├── audio.py               # Pronunciation audio selection & storage
│   ├── deck.py                # Card & deck SQLite domain operations
│   ├── dictionary.py          # Dictionary asset lookup
│   ├── export.py              # Anki TSV and APKG (genanki) export
│   ├── render.py              # Pure card-face HTML/text rendering
│   ├── resolve.py             # German lemmatization & candidate matching
│   └── frontend/              # [GENERATED] Compiled production bundle (build output)
│
├── frontend/                  # [AUTHORITATIVE] Handwritten frontend source
│   ├── package.json           # Minimal dependencies: lit, vite, typescript, playwright
│   ├── package-lock.json      # Pinned dependency lockfile
│   ├── tsconfig.json          # ES2022, decorators enabled
│   ├── vite.config.ts         # Proxy to :8000, outDir: ../app/frontend
│   ├── playwright.config.ts   # E2E test configuration against :8000
│   ├── index.html             # Shell loading src/main.ts
│   ├── src/
│   │   ├── main.ts            # App entry point & router bootstrap
│   │   ├── api/
│   │   │   └── client.ts      # Typed fetch client with R12 header injection
│   │   ├── types/
│   │   │   └── api.ts         # TypeScript interfaces matching backend DTOs
│   │   ├── styles/
│   │   │   ├── tokens.css     # CSS custom properties (colors, spacing, typography)
│   │   │   └── shared.ts      # Shared Lit CSS tagged template literals
│   │   └── components/
│   │       ├── fc-app.ts      # Root view shell and navigation
│   │       ├── fc-deck-list.ts# Decks overview, due counts, mastery %
│   │       ├── fc-review-screen.ts # Review session manager (Space, 1-5 keys)
│   │       ├── fc-card-face.ts# Card presentation & progressive disclosure
│   │       ├── fc-confidence-bar.ts # 5-level confidence buttons with shortcuts
│   │       ├── fc-audio-player.ts # Audio playback button & status
│   │       ├── fc-audio-recorder.ts # Custom recording/upload with preview/save/revert
│   │       ├── fc-capture-picker.ts # D11 candidate picker & 2-stage commit dialog
│   │       └── fc-import-export-dialog.ts # CSV import & TSV/APKG export
│   └── tests/
│       └── e2e/
│           ├── review.spec.ts     # Review loop & confidence mapping E2E
│           ├── capture.spec.ts    # Two-stage capture & picker E2E
│           ├── audio.spec.ts      # Audio playback, recording & revert E2E
│           └── import-export.spec.ts # CSV import & TSV/APKG export E2E
│
├── reference/
│   ├── schema.sql             # Authoritative SQLite database schema
│   └── smoke_test.py          # Repaired baseline smoke suite
│
└── tests/                     # Backend unit and integration test suite
```

### Key Architectural Decisions
1. **Frontend source tree**: Isolated in `frontend/`, independent of backend Python structure.
2. **Lit component boundaries**: 8 focused Custom Elements handling distinct UI responsibilities.
3. **State ownership**: Authoritative state resides 100% on the server in SQLite. Frontend owns only ephemeral UI interaction state.
4. **API client boundary**: `frontend/src/api/client.ts` automatically attaches `X-Flashcards-Request: 1` on all non-GET requests to satisfy AGENTS R12.
5. **CSS token strategy**: Vanilla CSS custom properties for dark/light themes and 5-level confidence color scales.
6. **Web Awesome subset**: Optional 4 primitives (`wa-button`, `wa-dialog`, `wa-spinner`, `wa-callout`), with plain Lit/HTML5 preferred.
7. **Dev build tooling**: Vite with local proxy forwarding `/vocab` to FastAPI at `http://127.0.0.1:8000`.
8. **Production frontend serving**: FastAPI mounts compiled static bundle at `/` with loopback host checks active.
9. **Playwright setup**: Automated E2E tests run against the standalone FastAPI-served instance.
10. **genanki integration boundary**: Pure export function in `app/export.py` using `genanki==0.13.1`.
11. **Audio in APKG**: Basename-only references `[sound:filename.ogg]` mapped in `Package.media_files`.

---

## Explicit source/build ownership

- **frontend/ is authoritative source**: All handwritten TypeScript, Lit components, HTML templates, CSS tokens, and frontend tests live exclusively in `frontend/`.
- **Generated backend frontend assets are build output and are never separately hand-maintained**: Compiled static assets (HTML, JS, CSS) output by `vite build` into `app/frontend/` are purely generated build output.
- **Clean build lifecycle**: Running the build command clears and regenerates the backend frontend distribution directory from `frontend/` source.

---

## Explicit non-reuse decisions

The following patterns and libraries from the reference repositories are **explicitly rejected**:

| Reference Repository | Rejected Pattern / Technology | Rationale |
|---|---|---|
| `ts-fsrs-demo` | `ts-fsrs` npm package | Violates authoritative server-side FSRS invariant (ADR-0001, ADR-0003, AGENTS R6). |
| `ts-fsrs-demo` | Client-side scheduling & interval calculations | Backend Python FSRS scheduler is the single source of truth. |
| `ts-fsrs-demo` | 4-grade rating interface | ADR-0003 explicitly mandates a 5-level confidence UI mapped server-side. |
| `ts-fsrs-demo` | React / Next.js framework | Project technology stack is Lit web components. |
| `full-stack-fastapi-template` | Authentication / JWT / OAuth2 / multi-user models | Flashcard app is single-user and local-only (ADR-0001 §2). |
| `full-stack-fastapi-template` | PostgreSQL, SQLModel, Alembic | Backend is frozen on SQLite with `reference/schema.sql`. |
| `full-stack-fastapi-template` | React + TanStack Router | Project uses Lit. |
| `full-stack-fastapi-template` | Generated `@hey-api/openapi-ts` SDK | Adds unnecessary build complexity; handwritten typed client is simpler and fully auditable. |
| `genanki` | Any runtime / review / scheduling usage | `genanki` is strictly an export utility for `.apkg` generation. |
| `webawesome` | Monolithic framework adoption | Full Web Awesome adoption is unnecessary; plain Lit/HTML/CSS is simpler. |
| `lit` | Copying Lit internal repository scripts | Use standard public `lit` npm package. |

---

## Required brief changes

When planning the implementation of the standalone product:

### Dependency addition
1. **Backend (`pyproject.toml`)**:
   - Add `genanki==0.13.1` (deterministically pinned) to `dependencies` for `.apkg` export capability.
2. **Frontend (`frontend/package.json`)**:
   - `lit` (runtime web component library).
   - `@awesome.me/webawesome` (optional, only if the minimal 4-primitive subset is used).
   - `vite`, `typescript`, `@types/node` (dev dependencies).
   - `@playwright/test` (E2E testing).

### Allowlist addition
For the slice implementing the standalone UI and export features:
- `frontend/` (entire source directory: `package.json`, lockfile, `tsconfig.json`, `vite.config.ts`, `playwright.config.ts`, `index.html`, `src/**`, `tests/e2e/**`).
- `app/frontend/` (compiled frontend distribution directory).
- `app/export.py` (new module for `.apkg` generation).
- `pyproject.toml` (for `genanki` dependency and tool configurations).
- `app/api.py` (mounting static files and APKG export endpoint).

### Implementation guidance
1. **Smoke baseline repair**: `reference/smoke_test.py` must fix the `sys.path` import defect, open `reference/schema.sql` explicitly, and remove `reference` exclusions from `pyproject.toml` (mypy, ruff, pytest).
2. **Strict R12 Enforcement**: Frontend API client MUST automatically attach `X-Flashcards-Request: 1` to all non-GET requests to pass the backend browser security middleware.
3. **5-Level Confidence UI**: Ensure the review UI exposes 5 distinct confidence rating buttons (`1`..`5`) per ADR-0003, with `Space` for answer reveal and `1`..`5` hotkeys for rating.
4. **ADR-0005 Audio Lifecycle**: Ensure custom audio recording preview remains browser-local before explicit Save, and Revert restores automatic selection without deleting files.
5. **Two-Stage Capture Flow**: Implement `/vocab/highlight` candidate resolution, D11 multi-select, and atomic `/vocab/cards` commit with asset token verification (handling HTTP 409).
6. **Semantic APKG Tests**: Verify exported packages semantically (ZIP structure, SQLite tables, GUIDs, media manifest, audio bytes) rather than relying on byte-exact file hashing.

### Architecture / governance considerations
- **No ADR Contradictions**: The findings and recommendations are fully coherent with accepted ADRs (ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005, ADR-0007) and AGENTS rules (R1, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, C1, C2, C3).
- **Scope Sequencing**: `tasks/slice-8.md` currently covers backend smoke repair, two-stage capture/import flows, example ranking, and pronunciation E2E smoke. A pre-slice-8 planning repair session can either incorporate the frontend/export implementation into an expanded Slice-8 brief or schedule it as a planned follow-on slice.

---

## Verification verdict

- **REFERENCE INSPECTION: PASS WITH MINOR CORRECTIONS**
- **ADR CONTRADICTIONS: NONE**
- **Governance status**: No accepted ADR contradiction was discovered, and no ADR reopening or governance escalation is required.
- **Attribution precision**: All corrections are donor-attribution or implementation-planning refinements.
- **Readiness**: This document is now verified and suitable input for the pre-Slice-8 planning repair session.
- **Slice status**: Slice 8 has **NOT** started.
