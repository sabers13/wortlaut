# Slice 12 — Session-scoped dictionary startup and UI

**BLOCKED until ADR-0009 is frozen and Slice-11 is accepted and merged.**

Task: Add ADR-0009's session-only provider selection, first-run chooser and
Settings controls on top of accepted Slice 11, without persisting dictionary
mode, and complete the product's migration onto the Slice-11 provider
contract.

Depends: ADR-0009 approved and frozen; slice-11 accepted and merged.

Allowlist:
- `wortlaut`, `flashcard`
- `app/api.py`, `app/dict_install.py`, `app/dictionary.py`, `app/deck.py`,
  `app/standalone.py`, `app/provider.py`, `app/provider_local.py`,
  `app/provider_online.py`, `app/online_manifest.py`, `app/online_cache.py`
- `frontend/src/app.ts`, `frontend/src/api/client.ts`,
  `frontend/src/api/types.ts`, `frontend/src/api/errors.ts`,
  `frontend/src/api/index.ts`, `frontend/src/api/client.test.ts`,
  `frontend/src/styles/tokens.css`,
  `frontend/tests/e2e/dictionary-modes.spec.ts` (new),
  `frontend/tests/e2e/serve.py`, `frontend/tests/e2e/run-server.sh`,
  `frontend/playwright.config.ts`
- `tests/test_api.py`, `tests/test_deck.py`, `tests/test_dict_install.py`,
  `tests/test_standalone.py`, `tests/test_launcher.py`, `tests/test_provider_differential.py`
- `MODULES.toml` only if required to register changed modules
- `tasks/slice-12.report.md`

The frontend/E2E files above may be modified only as necessary for the
dictionary-mode feature (e.g. adding a second deterministic served-product
state and the local fixture Online source), not for unrelated cleanup. If
implementing the design genuinely requires another tightly related frontend
harness file beyond this list, Stop-and-ask rather than silently expanding
scope.

Required reading: `docs/adr/0009-session-scoped-online-dictionary.md`,
`AGENTS.md`, `MODULES.toml`, Slice-11 report (including its contract-coverage
map), launcher/API/install/provider modules and their tests, frontend
application/settings code and tests, and `tasks/slice-12.md`.

Acceptance:

1. No backend mode-preference file or persisted `online`, `offline`, or
   `unconfigured` state exists. Explicit CLI selection is session-only.
2. The launcher implements ADR-0009's exact precedence: custom manifests are
   Offline Developer/Recovery only; `--dict-path` retains its established inert
   manifest / install precedence; contradictory Online combinations exit 2
   before network, provider activation or PART-B mutation; explicit Offline
   fails actionable rather than falling back Online. `--dictionary-mode
   online --install-dictionary` is an explicit CLI-matrix row asserting exit-2
   before any network, provider activation, dictionary install, or PART-B
   mutation.
3. With no explicit selection, a verified full Offline dictionary starts
   Offline with no chooser/network. Without it, the unconfigured runtime UI
   makes zero dictionary requests until the user chooses Online or Offline
   download. Restart behavior is derived from the then-current Offline asset.
   **Startup construction order (new):** provider/startup selection checks
   whether the canonical full Offline asset actually exists and validates
   *before* constructing `LocalDictionaryProvider`/`DictionaryRuntime` or
   invoking its local recovery path, so a stale historical
   `active_dictionary_metadata` row can never by itself trigger
   `DictionaryRuntime`'s missing-file recovery error when no Local provider
   is being activated. This intentionally supersedes the prior
   `missing dictionary -> launcher exits` behavior; the existing
   `tests/test_launcher.py` cases asserting that old exit behavior (e.g.
   `test_launcher_fails_closed_when_dictionary_missing`,
   `test_launcher_fails_closed_with_exit_code_on_missing_dict`) MAY and MUST
   be updated to assert the new unconfigured-chooser behavior instead; they
   are not required to remain unchanged. Existing custom-manifest integrity
   and valid-Offline startup tests remain protected and must keep passing.
4. **`active_dictionary_metadata` and removal semantics (new).**
   `active_dictionary_metadata` keeps recording only the metadata of the last
   successfully activated full Offline dictionary; it is not dictionary-mode
   state and this slice introduces no new preference/state table.
   - **Offline active + Remove Offline:** rejected with a structured,
     actionable conflict (conceptually `offline_dictionary_in_use`); the
     canonical file remains, the metadata row is unchanged, and no user data
     is touched.
   - **Online active + Remove Offline:** the canonical Offline file is
     removed after verifying it is exactly the managed canonical asset; the
     active Online session remains functional; `active_dictionary_metadata`
     is retained unchanged; zero D47/user-state mutation occurs.
   - **Restart after removal:** no local `DictionaryRuntime` recovery attempt
     occurs; the chooser appears; zero dictionary network access happens
     before a choice; no crash results from the stale historical metadata.
   - **Reinstall exact same v2 after removal:** Offline activates
     successfully via the normal metadata-match path, using the same logical
     asset identity, with no unnecessary D47 relink merely because the file
     was once removed. Activating a genuinely different dictionary identity
     still follows normal D47 activation/relink rules.
   - All cleanup operations (removal, cache clearing) are proven, by test, to
     never touch cards, reviews, meanings, audio/media, or other dictionary
     assets.
5. Settings exposes session-scoped Online/Offline switching, download with
   progress, Offline removal, and Online-cache clearing. Switching never
   activates invalid/incomplete Offline data; destructive actions are explicit
   and preserve all user cards, reviews, meanings and audio. Downloading the
   ~945 MB full Offline asset performs a conservative free-space preflight
   (accounting for the installer's temporary file and the existing
   activation/private-snapshot behavior) before beginning a download that is
   predictably unable to complete; if exact current peak-space behavior is
   unclear, measure it during this slice and fail safely rather than
   guessing. An insufficient-space failure is actionable, replaces no valid
   Offline asset, and mutates no user data.
6. **Complete provider migration in `app/api.py` (new).** All product
   dictionary reads are migrated onto the Slice-11 provider contract per its
   accepted contract-coverage map. This explicitly names and
   removes/bypasses:
   - the direct `runtime._current_generation.asset.connection` reads
     currently used by `POST /vocab/highlight` and `POST /vocab/import/csv`;
   - the raw dictionary SQL in `_materialize_candidate_from_ref`.
   Low-level SQLite access remains allowed only inside
   `LocalDictionaryProvider`/dictionary implementation, never reintroduced as
   a bypass elsewhere in `app/api.py`. A mechanical check (grep-style,
   recorded in the report) proves no direct
   `_current_generation.asset.connection` dictionary-read use remains in
   `app/api.py`, and that no replacement raw-SQL bypass was added outside the
   provider boundary.
7. **End-to-end Online fixture acceptance (new).** Against the deterministic
   fixture Online provider, prove at minimum that `POST /vocab/highlight` and
   `POST /vocab/import/csv` work without a full local dictionary, and that
   candidate materialization and a representative card-creation path work
   through Online provider data. Transport/integrity/budget errors remain
   structured provider failures and never become valid dictionary misses or
   PART-B writes.
8. API and browser guards satisfy AGENTS R12; no browser input can choose a
   manifest or network endpoint. Existing fully local behavior and `./flashcard`
   compatibility remain intact.
9. CLI-matrix tests cover default and `--data-dir` roots, custom-manifest
   verification/install, explicit-path behavior, all Online conflicts
   (including the `--dictionary-mode online --install-dictionary` row),
   absence, integrity and no-mutation paths.
10. **Expanded E2E harness (new).** The Playwright harness supports at least
    two deterministic served-product states: (A) an Offline-installed
    fixture (normal local dictionary available), and (B) a
    no-full-dictionary/fixture-Online environment (no canonical full Offline
    dictionary; chooser visible; a local deterministic static online-shard
    fixture reachable through the Product trust/test seam under
    backend/harness control — never an arbitrary browser-supplied endpoint).
    Normal Playwright tests must not depend on public GitHub network
    availability. Acceptance exercises: chooser; explicit Use Online;
    Download for Offline use; Online → Offline; Offline → Online; progress;
    Clear Online cache; Remove Offline dictionary; removal rejection while
    Offline active; restart after Offline removal; unavailable/integrity
    errors. Frontend focused tests include the co-owned `client.test.ts`.
11. Frontend focused validation and one final `make gate` pass. The report
    records exact commands and the mandatory full-diff T3 review result.

Stop-and-ask: any need to persist dictionary mode, alter the custom-manifest
Offline contract, introduce runtime dependencies or a PART-B migration, publish
assets, alter user data during cache/offline cleanup, add a frontend/E2E
harness file beyond the expanded allowlist above, or change outside the
allowlist.

Risk: public-api, auth-security, data-loss.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's cross-cutting launcher/API/frontend behavior, browser trust
boundary and destructive-adjacent controls require design judgment.

Fallback: opus-5 / T3 / high.
