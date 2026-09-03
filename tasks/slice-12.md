# Slice 12 — Session-scoped dictionary startup and UI

**BLOCKED until ADR-0009 is frozen and Slice-11 is accepted and merged.**

Task: Add ADR-0009's session-only provider selection, first-run chooser and
Settings controls on top of accepted Slice 11, without persisting dictionary
mode.

Depends: ADR-0009 approved and frozen; slice-11 accepted and merged.

Allowlist:
- `wortlaut`, `flashcard`
- `app/api.py`, `app/dict_install.py`, `app/dictionary.py`, `app/deck.py`,
  `app/standalone.py`, `app/provider.py`, `app/provider_local.py`,
  `app/provider_online.py`, `app/online_manifest.py`, `app/online_cache.py`
- `frontend/src/app.ts`, `frontend/src/api/client.ts`,
  `frontend/src/api/types.ts`, `frontend/src/api/errors.ts`,
  `frontend/tests/e2e/dictionary-modes.spec.ts` (new)
- `tests/test_api.py`, `tests/test_deck.py`, `tests/test_dict_install.py`,
  `tests/test_standalone.py`, `tests/test_launcher.py`, `tests/test_provider_differential.py`
- `MODULES.toml` only if required to register changed modules
- `tasks/slice-12.report.md`

Required reading: `docs/adr/0009-session-scoped-online-dictionary.md`,
`AGENTS.md`, `MODULES.toml`, Slice-11 report, launcher/API/install/provider
modules and their tests, frontend application/settings code and tests, and
`tasks/slice-12.md`.

Acceptance:

1. No backend mode-preference file or persisted `online`, `offline`, or
   `unconfigured` state exists. Explicit CLI selection is session-only.
2. The launcher implements ADR-0009's exact precedence: custom manifests are
   Offline Developer/Recovery only; `--dict-path` retains its established inert
   manifest / install precedence; contradictory Online combinations exit 2
   before network, provider activation or PART-B mutation; explicit Offline
   fails actionable rather than falling back Online.
3. With no explicit selection, a verified full Offline dictionary starts
   Offline with no chooser/network. Without it, the unconfigured runtime UI
   makes zero dictionary requests until the user chooses Online or Offline
   download. Restart behavior is derived from the then-current Offline asset.
4. Settings exposes session-scoped Online/Offline switching, download with
   progress, Offline removal, and Online-cache clearing. Switching never
   activates invalid/incomplete Offline data; destructive actions are explicit
   and preserve all user cards, reviews, meanings and audio.
5. API and browser guards satisfy AGENTS R12; no browser input can choose a
   manifest or network endpoint. Existing fully local behavior and `./flashcard`
   compatibility remain intact.
6. CLI-matrix tests cover default and `--data-dir` roots, custom-manifest
   verification/install, explicit-path behavior, all Online conflicts, absence,
   integrity and no-mutation paths. Playwright runs against the actual served
   product and covers chooser, both switch directions, progress, clear cache,
   removal, and unavailable/error states.
7. Frontend focused validation and one final `make gate` pass. The report
   records exact commands and the mandatory full-diff T3 review result.

Stop-and-ask: any need to persist dictionary mode, alter the custom-manifest
Offline contract, introduce runtime dependencies or a PART-B migration, publish
assets, alter user data during cache/offline cleanup, or change outside the
allowlist.

Risk: public-api, auth-security, data-loss.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's cross-cutting launcher/API/frontend behavior, browser trust
boundary and destructive-adjacent controls require design judgment.

Fallback: opus-5 / T3 / high.
