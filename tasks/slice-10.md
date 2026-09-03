# Slice 10 — Online and offline dictionary modes (ADR-0008)

**BLOCKED until ADR-0008 passes cold review #3 — FINAL CONVERGENCE REVIEW.**
This brief is dependency-closed and dispatch-ready, but ADR-0008 currently
carries `NEEDS COLD REVIEW`: reviews #1 and #2 are complete (O1–O5 CLOSED, O6
resolved by the preservation remedy in ADR-0008 §9.3.1/§9.3.2). Do not dispatch
implementation while that marker stands (WORKFLOW §7 / AGENTS G7).

Depends: ADR-0008 accepted (cold review #3 PASS). **Not** dependent on slice-9,
which remains blocked on lecture-app Phase-4 decomposition and
`tasks/adr-0002-donor-notes.md`; the two slices touch disjoint scopes and may be
ordered freely.

---

```
Task:        Implement ADR-0008: a DictionaryProvider seam with Local and Online
             implementations, a static sharded online dictionary format plus its
             deterministic builder, a validated local mode preference and startup
             state machine, an online shard cache with fail-closed integrity, the
             first-run chooser and Settings/Dictionary UI, and the differential
             verification harness that proves the online provider observably
             equals the local provider. Do NOT create, upload to, or publish any
             GitHub Release in this slice; §13.3 steps 3–8 of ADR-0008 are a
             separate authorized operation.

Allowlist:   app/provider.py                       (new — DictionaryProvider seam, D85)
             app/provider_local.py                 (new — LocalDictionaryProvider)
             app/provider_online.py                (new — OnlineDictionaryProvider)
             app/online_manifest.py                (new — manifest schema + strict validation, D89)
             app/online_cache.py                   (new — shard cache, D95)
             app/online_filter.py                  (new — Bloom membership accelerator, D88)
             app/routing.py                        (new — routing-key + bucket functions, D87)
             app/preferences.py                    (new — preferences.json store, D91)
             app/dictionary.py                     (provider-facing reads; no PART-A semantic change)
             app/deck.py                           (lazy ReadingSnapshot resolvers D100; provider switch atomicity D99)
             app/api.py                            (route reads through the provider; dictionary_unavailable state; mode + cache routes)
             app/dict_install.py                   (progress-reporting seam only; verification logic unchanged, D94)
             app/standalone.py                     (startable with no dictionary; startup state machine, D92)
             wortlaut                              (--dictionary-mode; §9.3 table exactly)
             tools/build_online_dictionary.py      (new — deterministic builder, D101)
             frontend/src/app.ts                   (setup + settings views)
             frontend/src/api/client.ts            (typed calls for mode, cache, install)
             frontend/src/api/types.ts             (typed payloads incl. dictionary_unavailable)
             frontend/src/api/errors.ts            (online_dictionary_unavailable mapping)
             frontend/tests/e2e/dictionary-modes.spec.ts   (new)
             tests/test_provider_differential.py   (new — D102 harness)
             tests/test_routing_equivalence.py     (new — §14.2 test 1)
             tests/test_online_cache.py            (new — §14.2 tests 5, 6)
             tests/test_online_manifest.py         (new)
             tests/test_preferences.py             (new — §14.2 test 7)
             tests/test_build_online_dictionary.py (new)
             tests/test_api.py                     (regression + new routes)
             tests/test_deck.py                    (lazy resolver regression)
             tests/test_standalone.py              (startup state machine)
             tests/test_launcher.py                (CLI table; ADDITIVE ONLY — the existing
                                                    custom-manifest startup cases named in
                                                    ADR-0008 §9.3.1 must remain unchanged)
             tests/test_dict_install.py            (progress seam)
             tests/test_check_agents.py            (R14 Product/developer boundary gate coverage)
             tests/conftest.py                     (fixture shard set)
             release/dictionary-online-manifest-v2.json   (fixture/schema-shaped placeholder ONLY until the production build; see Stop-and-ask)
             release/README.md                     (document the online manifest + release identity)
             AGENTS.md                             (add R14; clarify R9 per ADR-0008 §16.2 — those two edits only)
             tools/check_agents.py                 (R14 executable Product-path check)
             MODULES.toml                          (new modules per ADR-0008 §16.2)
             README.md                             (scope the privacy claim per ADR-0008 §11)
             .gitignore                            (block production shard output, D101)
             docs/backlog.md                       (file the deferred items named in ADR-0008 §5.7, §12.5, §14.4)
             tasks/slice-10.report.md              (new — worker report)

             Anything not listed is a scope violation. In particular:
             reference/schema.sql, pyproject.toml, Dockerfile,
             release/dictionary-manifest-v2.json, release/ATTRIBUTION-v2.md,
             app/render.py, app/examples.py, app/export.py, app/audio.py and
             app/resolve.py are OUT OF SCOPE — ADR-0008 requires no change to
             any of them.

Required reading:
             WORKFLOW.md; AGENTS.md; STATE.md; MODULES.toml;
             docs/adr/0008-online-offline-dictionary.md (the controlling document);
             docs/adr/0001-flashcards-core.md §10, §12, D1, D4;
             docs/adr/0002-standalone-and-integration.md D20, D24, D25, D26, D27, §4.1, §7;
             docs/adr/0004-multilingual-learner-meanings.md D43, D45, D46, D47, §6.6;
             docs/adr/0007-defer-persian-learner-meanings.md §3.1, §7 (DE/EN only);
             release/dictionary-manifest-v2.json; release/ATTRIBUTION-v2.md; release/README.md;
             app/dictionary.py; app/dict_install.py; app/deck.py (DictionaryRuntime,
               ReadingSnapshot, reading(), activate_dictionary, _relink_part_b,
               _materialize_lemma_under_gen, _materialize_components_under_gen);
             app/api.py (_ConnectionLookupOracle, _materialize_candidate_from_ref,
               create_app, the /vocab route table, static serving);
             app/resolve.py (resolve_word, split_compound, _bind_component);
             app/standalone.py; wortlaut; flashcard;
             frontend/src/app.ts; frontend/src/api/*;
             tools/check_agents.py; tools/check_modules.py;
             tests/test_dictionary.py; tests/test_deck.py; tests/test_api.py;
             tests/test_dict_install.py; tests/test_standalone.py; tests/test_launcher.py;
             tests/conftest.py.
             MODULES.toml dependency closure for the modules named in the
             Allowlist. Do not broaden to whole-repository rediscovery.

Acceptance:  1. `make gate` passes on the exact final candidate: ruff clean;
                mypy --strict clean; full pytest green; AGENTS
                R1/R3/R6/R7/R12/R13 PASS plus the new R14 check; MODULES
                validation passes for the updated module set.
             2. Every pre-existing test passes unchanged with the local
                provider active — offline behaviour is byte-identical
                (ADR-0008 D82, §14.2 test 8). This explicitly includes the
                existing `tests/test_launcher.py` custom-manifest startup class
                — `--manifest CUSTOM` **without** `--install-dictionary`,
                Offline/canonical startup — named in ADR-0008 §9.3.1: size
                mismatch, SHA-256 mismatch, filename/canonical-path mismatch,
                identity-not-full-installer verification, runtime validation
                after a valid precheck, replacement after precheck, and
                `--dict-path` bypassing manifest identity. Those tests must keep
                exercising the real integrity path; they must not be rewritten,
                relaxed, or deleted to fit a new CLI contract, and acceptance
                must not be weakened merely to make tests pass.
             3. The differential harness (tests/test_provider_differential.py)
                proves observable equality between LocalDictionaryProvider and
                OnlineDictionaryProvider over the fixture shard set, across the
                full ADR-0008 §14.1 sample list. Equality = identical ordered
                rows, field values, absence, dedup, and asset_token, including
                arbitrary `sense_ids[sense_ref]` point reads and D47 relinking.
             4. Routing equivalence (§14.2 test 1) holds for the 2,716
                ASCII/Unicode-lower divergence population, NFD inputs,
                `STRASSE`, and `äpfel`.
             5. The 256 lookup shards contain both bucket-closed lookup-key and
                `sense_ref → parent lemma_ref` indexes. The builder emits every
                authoritative sense ref exactly once; a sense point read routes
                lookup shard then parent entry shard with no entry-shard scan.
                The build report reconciles revised §5.6 sizing (417.6 MB lookup
                family projection, ≤1.61 MB median, ≤3.72 MB max), retains 577
                assets, and proves each actual shard remains ≤4 MB.
             6. Membership filter has zero false negatives over its build set;
                false positives are permitted and measured FPR is reported
                against the manifest-declared statistical target.
             7. The harness proves the absolute 256 distinct lookup-family
                maximum and enforces the 32-new-remote-lookup-shard logical
                operation budget. A forced 33rd acquisition cancels cleanly,
                returns `online_dictionary_budget_exceeded` (not not-found or
                `needs_gloss`), releases leases, preserves cache, and performs
                zero PART-B writes. The approximate 12-shard production probe is
                performance evidence only, not a correctness bound.
             8. Integrity failures (truncated / byte-flipped / wrong SHA /
                non-SQLite / wrong dataset version) are rejected, never become an
                active cache entry, surface `online_dictionary_unavailable`, and
                perform zero PART-B writes.
             9. A later byte-corrupted canonical cached shard is revalidated,
                never opened, safely evicted/quarantined and refetched or fails
                closed. Concurrent same-shard misses yield one verified install;
                clear-cache during an immutable active lease blocks new canonical
                acquisition, defers cleanup until release, never invalidates that
                reader, and proves no PART-B/media/offline-dictionary path was
                touched. Provider switching with leases never mixes providers
                inside one logical operation.
            10. All four §8.2 startup branches behave as specified, including the
                corrupt-preference branch failing safe with no network access.
            11. A pre-existing valid dictionary.sqlite with no preference file
                boots straight into Offline with no chooser (D105).
            12. Every §9.3 matrix row is enumerated under both default and
                `--data-dir PATH` roots: selected provider, session-only mode
                persistence, preferences/cache/canonical dictionary/PART-B-media
                locations, manifest/trust domain, network permission, install
                then launch/exit behaviour, and all usage errors. Product fetches
                allow only the exact GitHub initial path and closed redirect-host
                policy; the explicit `--manifest PATH` path is tested as a
                segregated developer/recovery Offline-only path — in both its
                `--install-dictionary` install role and its network-free
                canonical-identity-verification startup role — and cannot affect
                Online or browser/API input. Specifically, for the four
                custom-manifest / no-install rows (ADR-0008 §9.3.1): a valid
                manifest verifies the canonical dictionary under the selected
                data root and launches Offline successfully; an invalid one
                produces the exact documented integrity error and exit code with
                no PART-B database created or written; no
                `OnlineDictionaryProvider` is constructed; and no custom source
                or dictionary mode is persisted. Explicit rejection tests for
                `--dictionary-mode online --manifest CUSTOM` (all four rows,
                ADR-0008 §9.3.2) must prove deterministic exit 2 before any
                network access, provider activation, preference mutation or
                PART-B mutation. `--dict-path` precedence is asserted as shipped:
                inert manifest without install, manifest-constrained activation
                with install.
            13. Playwright coverage against the real FastAPI-served compiled
                product: first-run chooser, both modes, both switch directions,
                cache size display, clear-cache, UI-initiated offline install
                with progress, and the dictionary_unavailable surface.
            14. `git diff --check` clean; only Allowlist paths changed.
            15. Frontend: `npm ci`, `tsc --noEmit`, unit tests, `vite build`,
                and `npm run test:e2e` all clean.

Stop-and-ask:
             * Any change would be required to reference/schema.sql, pyproject.toml,
               the Dockerfile, release/dictionary-manifest-v2.json,
               release/ATTRIBUTION-v2.md, or the dictionary-v2 release.
             * Preserving current lookup semantics under ADR-0008 §6 proves
               impossible for any measured case — this is an ADR defect, not a
               worker decision.
             * A shard family exceeds the ADR-0008 §5.6 budget (any shard > 4 MB,
               or median lookup/entry shard > 2 MB) on real data.
             * Total release assets would exceed 700 (ADR-0008 budgets 577 of the
               1000 limit; a design that needs more than 700 must return to
               governance).
             * A new runtime dependency would be required. ADR-0008 assumes none:
               stdlib `urllib`, `sqlite3` and `hashlib` only.
             * Any AGENTS rule beyond the exact R14 addition and R9 clarification
               in ADR-0008 §16.2 would need editing.
             * A PART-B schema migration appears necessary for any reason.
             * The production v2 shard build, the draft release, asset upload, or
               publication is reached — those are ADR-0008 §13.3 steps 2–8 and are
               a separate authorized operation, never part of this slice.

Risk:        public-api, auth-security, data-loss

             public-api  — app/api.py gains browser-callable mode-switch and
                           cache routes and a new dictionary_unavailable
                           contract; app/provider*.py and app/dictionary.py are
                           importable/callable surfaces; wortlaut gains a CLI
                           flag.
             auth-security — app/provider_online.py, app/online_manifest.py and
                           app/online_cache.py introduce the product's first
                           routine outbound network path; AGENTS R12 guard
                           coverage extends to the new non-GET routes.
             data-loss   — "Remove offline copy" and "Clear online cache" are
                           destructive actions adjacent to user data, and
                           app/deck.py's activation/relink path is touched.

             Per WORKFLOW §6 this slice ships with a pre-committed T3 full-diff
             review. No merge until that review line is filled.

Model:       gpt-5.6-terra / T3 / high

Why:         WORKFLOW §4, highest triggered row — Novelty: this establishes a new
             cross-cutting pattern (the DictionaryProvider seam) that every later
             dictionary change will copy. Blast radius and Spec completeness also
             trigger: the allowlist spans runtime, network, public API, launcher,
             frontend and a new build tool, and the worker must exercise design
             judgment inside ADR-0008's constraints.

Fallback:    opus-5 / T3 / high (same tier). If GPT quota is exhausted,
             antigravity/gemini-3.7-flash / T3 / high for implementation
             evidence; the mandatory T3 full-diff risk review must be a
             different fresh T3 session either way (AGENTS G11 / WORKFLOW §14.5).
```

---

## Suggested staging

ADR-0008 §17 defines the implementation sequence. Stages S1 and S2 land value
with zero network surface and are separately revertible; prefer dispatching them
as their own candidates before S3–S5.

| Stage | Scope | Independent value |
|---|---|---|
| S1 | Provider seam + LocalDictionaryProvider + lazy ReadingSnapshot resolvers | Removes `app/api.py`'s raw-connection coupling and the eager 1.1M-entry map copy per `reading()` call |
| S2 | Preferences store + startup state machine + `dictionary_unavailable` | App becomes startable without a dictionary |
| S3 | Builder + fixture shard set + differential harness | Proves the format before any network code exists |
| S4 | Online provider + cache + manifest validation + failure semantics | The feature, behind a mode the user must choose |
| S5 | First-run chooser + Settings view + UI-initiated install | The product surface |

Stage S6 (production build and publication) is explicitly **not** in this
slice's allowlist.
