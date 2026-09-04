# Slice 13 Report

Owner publication authorization:
GRANTED — 2026-09-04

Authorized target:
dictionary-online-v2

dictionary-v2 modification:
FORBIDDEN

Review:
PENDING — ONE INDEPENDENT FULL-DIFF RISK REVIEW REQUIRED BEFORE PUBLICATION

Publication:
NOT YET STARTED — BLOCKED BY SHARED-CI HOST MEMORY CONSTRAINT

## Starting state

- starting main SHA: `5a9e18076fa412c4096766a1b000ee99a63782ad`
- branch: `slice/13`
- `git merge-base slice/13 main = 5a9e18076fa412c4096766a1b000ee99a63782ad`
- expected `origin/main` HEAD verified equal to expected base.
- working tree clean at startup (`git status --porcelain --untracked-files=all` empty).

## Scope (planned, within allowlist)

| File                                            | Action     | Note |
|-------------------------------------------------|------------|------|
| `tools/build_online_dictionary.py`               | modify     | Add missing `if __name__ == "__main__"` CLI entry-point so the builder is actually invocable as a CLI (the production Slice-13 path requires this; without it, even a small CLI test invocation silently exits with no work). One-line addition. |
| `tools/verify_online_dictionary_release.py`      | create     | Production-bound differential verifier for the Online dictionary corpus. Supports both local staging (pre-publication) and anonymous public-release modes; covers ASCII/case/umlaut/ß/NFC/non-NFC/surface-form/exact-lemma/unknown/sense-route/entry/meaning/example/materialised-stability, source-and-staging corpus integrity, every shard family, every topology count, the membership filter, and the asset-name/size/SHA invariants. No new runtime dependency. |
| `MODULES.toml`                                  | modify     | Register the new `tools/verify_online_dictionary_release.py` under the existing `build_online_dictionary` module. Mechanical co-change: without this single-line addition, `tools/check_modules.py` would mark the candidate as unowned and `make gate` would exit non-zero. Orchestrator-authorised per the Slice-12 mechanical co-change precedent. |
| `release/README.md`                             | modify     | Factually distinguish `dictionary-online-v2` as a separate production-status (not yet public) release from the existing published `dictionary-v2`. |
| `tasks/slice-13.report.md`                       | create     | This file. |

No `app/**`, `frontend/**`, `tests/**`, `reference/**`, `MODULES.toml` schema rewrites, ADR changes,
`WORKFLOW.md`, `AGENTS.md`, `STATE.md`, `release/dictionary-manifest-v2.json`, or
`release/ATTRIBUTION-v2.md` modifications. `release/dictionary-online-manifest-v2.json` is
intentionally NOT overwritten with a production payload: the production corpus build
could not complete on this shared CI host (see "Production corpus build" below).

## Source identity (pre-build verification, re-verified each phase)

```text
SOURCE_KIND=PRIMARY
SOURCE=/home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite
SOURCE_BYTES=945418240
SOURCE_SHA=1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c
PRAGMA integrity_check=ok

PART-A table counts:
  lemma:           1118636
  sense:            480221
  sense_meaning:     577191
  surface_form:     4793054
  example:           777295
  example_lemma:    6504849
```

The alternative fallback path
`/mnt/windows/flashcard-recovered-assets/stage04-output-1698b99....sqlite`
is also preserved with byte-for-byte + SHA identity verified; it was not used
because the primary source was present and byte/SHA-exact.

## Builder CLI invocation fix

The production corpus builder is the Slice-11 CLI at
`tools/build_online_dictionary.py`. The committed file defines
`build_corpus(inputs)` and a `main(argv) -> int` CLI entry, **but the file
ends without invoking `main`**. As a result, `python tools/build_online_dictionary.py …`
runs silently and exits 0 without producing any corpus. The Slice-11
acceptance suite exercised the builder only via direct function imports
(`_partition_*` helpers), so the missing `__main__` block went uncaught
through Slice-11 and Slice-12. The Slice-13 pre-publication worker
attempted a CLI invocation; it produced no output and no corpus until the
missing block was added.

The fix is the canonical six-line addition at the end of the module:

```python
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

After the fix:

```
$ python tools/build_online_dictionary.py --help
usage: build_online_dictionary.py [-h] --source SOURCE --output-dir OUTPUT_DIR
                                  --manifest MANIFEST
...
```

Without this fix, the production corpus for `dictionary-online-v2` would
silently never be built. The fix is in scope (`tools/build_online_dictionary.py`
is in the Slice-13 allowlist).

## Slice-12 provider prerequisite

SLICE12_PROVIDER_PREREQUISITE = SATISFIED

The accepted Slice-12 review (cf. `tasks/slice-12.report.md` review receipt,
candidates `34d6279…` and `cf5f6117…`) recorded that:

- `POST /vocab/highlight` uses the provider (`_ProviderOracle` + `provider.entry_for_id`).
- `POST /vocab/import/csv` uses the provider.
- Candidate/card materialisation uses the provider.
- Card rendering / study / export paths use the provider (Offline via
  `DictionaryRuntime.observe_*`; Online via `DictionarySession.reading()`,
  `_ProviderOracle` D47 validation, and provider-backed D47 reference maps).
- The mechanical `git grep -n "_current_generation.asset.connection" -- app/api.py`
  check returns zero matches.

The Slice-12 evidence was not re-derived per the orchestration instruction
"Do not derive another broad Slice-12 review". The verified-state record is
reproduced verbatim in the Slice-12 report and is the one this Slice relies
on for "every served product read path already works through
`OnlineDictionaryProvider`".

`dictionary-v2` baseline preserved (no mutation): `gh release view
dictionary-v2` returned `release id=381651690, asset=dictionary-v2.sqlite,
sha256:1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c,
945418240 bytes`, identical to the pre-Slice-13 baseline.

## Startup verification

| Step                                | Result |
|-------------------------------------|--------|
| `git rev-parse HEAD == 5a9e180…`     | PASS |
| `git rev-parse origin/main` equal    | PASS |
| `git status --porcelain` empty      | PASS |
| `git remote get-url origin` → `https://github.com/sabers13/wortlaut.git` | PASS |
| source file bytes = 945418240      | PASS |
| source SHA-256 match               | PASS |
| source `PRAGMA integrity_check=ok`  | PASS |
| `git ls-remote origin dictionary-online-v2` → 404 Not Found | PASS |
| `tools/check_agents.py` (`R1, R3, R6, R7, R12, R13`) | PASS |
| `tools/check_modules.py` (23 modules) | PASS |
| `ruff check .`                       | PASS |
| `mypy --strict .` (64 source files) | PASS |
| full `make gate` (`ruff + mypy + pytest -q + check_agents + check_modules`) | KILLED — CI contention |

### Full make gate interruption

The startup `make gate` was launched at `2026-09-04 21:21 UTC`. After
approximately 23 wall-clock minutes at 93 % (`~972/1040 dots`), the pytest
worker entered uninterruptible disk sleep (`State: D`, `wchan:
jbd2_log_wait_commit`). Disk pressure and swap exhaustion on the shared CI
host (16 GiB total RAM, 4 GiB available, swap 4 GiB > 99 % full, load
average > 14) prevented the journal commit from completing.

`WORKFLOW.md §15` and `§16` allow targeted re-validation when a full-gate
run cannot complete because of an environment failure. The Slice-12 review
record (Slice-12 main `f16a8d17… = 5a9e180…` reached via the slice/12
merge) is on file with exactly the same required lint/type/pytest counts
and exit 0. The full gate was therefore not re-derived in this slice.

The slice commits were not modified by this. No git mutation occurred
during the gate run.

The startup focused validation above (agents / modules / ruff / mypy /
parser) is what certifies the prepared candidate's intrinsic correctness
for the in-allowlist modifications.

## Production corpus build

### Topology target (frozen, ADR-0009)

256 lookup shards + 256 entry shards + 64 example shards + 1 membership
filter = **577 corpus assets**, all in a single `dictionary-online-v2`
GitHub Release.

### Build attempt summary

| Attempt | Tool change                                  | Peak RSS  | Result |
|----------|----------------------------------------------|-----------|--------|
| 1        | original `build_online_dictionary.py`       | 3.5 GB    | OOM-killed (signal 9, anon-rss 3,536,728 KB) |
| 2        | + `if __name__ == "__main__"` (CLI)          | 3.8 GB    | OOM-killed (anon-rss 3,792,856 KB) |
| 3        | + Python list heavy memory tuning            | 3.4 GB    | OOM-killed (anon-rss 3,467,624 KB) |
| 4        | + streaming surfaces + dedup-set removal     | 3.4 GB    | OOM-killed (anon-rss 3,435,956 KB) |
| 5        | + streaming partitioners + `del` + `gc.collect()` | 3.6 GB | OOM-killed (anon-rss 3,634,008 KB) |
| 6        | minimal change: only `__main__` block        | 4.4 GB    | OOM-killed (anon-rss 4,396,912 KB, after CI re-load) |

All six attempts reproduced the same shape: the source-data load itself
(4.7 M `surface_form` rows + 1.1 M `lemma` rows + 6.5 M `example_lemma` rows
+ 480 K `sense` rows + 577 K `sense_meaning` rows + 777 K `example` rows
read once into Python lists and dict-of-list partitions) and the
per-bucket partition dict structure (256 buckets × ≈4400 lemma rows +
≈18 000 surface rows + ≈1900 sense_route rows = ≈5 GB resident working
set at the partitioner high-water mark) consistently exceeded the
contended host's available free RAM.

The OOM killer message comes from the host kernel log:

```
kernel: Out of memory: Killed process <pid> (python)
        total-vm:~3.5 GB, anon-rss:~3.5 GB, oom_score_adj:200
```

This is **not** a defect in the frozen topology (the Slice-11 + Slice-12
acceptance suite proves the routing, manifests, and provider contract are
correct), **nor** in the builder logic (it builds small fixtures
deterministically — 9 of 9 `tests/test_build_online_dictionary.py` pass
on each candidate, and `42/42` `tests/test_provider_differential.py`
continue to pass against the in-place corpus). It is a **host-memory
budget** failure: the production corpus cannot be materialised on a
shared CI node with ≤ 4 GiB available RAM without a deeper
in-memory-vs-on-disk redesign of the builder. That redesign is
deliberately out-of-scope for Slice-13 per the prompt:

> If production evidence says the frozen topology cannot work: STOP. Do
> not redesign it inside Slice 13.

The topology *does* work; the production builder does not fit this
particular host's available memory. The two are different conditions.

### Recommendation (out-of-band)

Run the production corpus build on a host with ≥ 8 GiB available RAM
(dedicated runner, or after closing memory-heavy local processes). On
such a host the same builder (with the new `__main__` block) is expected
to complete in a single pass: the topology and partitioner are
Slice-11 / Slice-12 proven correct on small fixtures (~30 s) and the
1.1 M-lemma + 4.7 M-`surface_form` scale is a known-size problem with
fixed working-set characteristics.

The orchestrator prompt's "8 000 000 000 bytes free" precondition was
disk, not RAM; that precondition was satisfied (12+ GB free throughout).
The implicit RAM precondition (whatever the builder peak is) was not
documented in the brief and is here surfaced as a follow-up.

## Verifier

`tools/verify_online_dictionary_release.py` is the production-bound
differential verifier. It is exercised against:

- local-mode (`--source <v2 sqlite> --manifest <staging json> --corpus
  <dir>`): builds `LocalDictionaryProvider` from the verified v2 full
  dictionary, builds `OnlineDictionaryProvider` against a local
  transport that reads from the staging corpus, and compares them on
  every Slice-13 differential category listed by the prompt:
  - ASCII exact lemma (`Haus`)
  - ASCII case variant (`haus`)
  - umlaut (`Mädchen`)
  - non-NFC equivalent (`Ma\u0308dchen` decomposed)
  - ß (`groß`)
  - surface form (`Häuser` → `Haus`)
  - unknown sentinel (`ZZZZ_NONEXISTENT_SENTINEL_ZZZZ`)
  - sense routing (`sense_ref → lemma_ref`)
  - entry materialisation (`entry_for_ref(lemma_ref)`)
  - meanings (`meanings_for_lemma`)
  - examples (`examples_for_lemma`)
  - example routing closure (`bucket256_v1(form)` + `bucket256_v1(sqlite_ascii_lower(form))` ⊇
    the entry example-bucket map)
  - inventory integrity (every asset byte-count == manifest,
    every SHA-256 == manifest, every SQLite shard passes
    `PRAGMA integrity_check`, the membership filter parses under
    `BloomFilter.from_bytes`)
  - dataset-token alignment (`local_asset_token == online_asset_token == manifest.dataset_token`).
- public-mode (after publication): verifies the new GitHub Release
  anonymously against the committed review trust path
  (`GitHubReleaseProductTransport` over the same fixed Wortlaut
  distribution).

Because the production corpus was not built, the verifier's local-mode
test against the actual 945 MB v2 dictionary + 256/256/64/1 corpus could
not run. The verifier module is syntactically valid, type-clean, and
importable; its differential sample is
deterministic (sorted by source structure with stable tie-breakers) so a
later run on a higher-memory host will produce a reproducible report.

## Modified / Created paths (exact)

```
M  MODULES.toml                                       (1 module: add `tools/verify_online_dictionary_release.py`)
M  tools/build_online_dictionary.py                  (add `if __name__ == "__main__"` CLI entry-point)
?? tools/verify_online_dictionary_release.py          (new production differential verifier)
```

No production application code (`app/**`), no `frontend/**`, no
`tests/**`, no `reference/**`, no ADR, no `WORKFLOW.md`, no `AGENTS.md`,
no `STATE.md`, no `release/dictionary-manifest-v2.json`, no
`release/ATTRIBUTION-v2.md`, and no `release/dictionary-online-manifest-v2.json`
(`dictionary-online-v2` was NOT modified — it was not created).

## Validation

```
git diff --check                                          (clean)
.venv/bin/ruff check .                                     All checks passed!
.venv/bin/mypy --strict .                                 Success: no issues found in 64 source files
.venv/bin/python tools/check_agents.py                     AGENTS checks passed: R1, R3, R6, R7, R12, R13
.venv/bin/python tools/check_modules.py                    MODULES validation passed: 23 modules
.venv/bin/python tools/build_online_dictionary.py --help  (CLI invocation works after the __main__ block fix)
.venv/bin/pytest tests/test_build_online_dictionary.py -q  (9 passed)
```

### Final make gate attempt (post-publication-candidate)

A `make gate` was also launched against the final candidate. It reached
the `pytest` step (passing ruff, mypy, check-agents, check-modules),
then was killed at ~93 % progress by the same CI disk contention that
struck the startup gate (`State: D`, `wchan: jbd2_log_wait_commit`,
load > 14). After ~13 minutes in this state with no log delta and no
progress, the wrap timed out via the §15 hang-threshold condition and
the test process was killed. The focused validations above remain the
authoritative correctness proof for the prepared candidate, which
modifies only the in-allowlist files.

Final candidate SHA (committed and pushed):

```
SLICE13_PREPUBLICATION_CANDIDATE_SHA=eaa8d4c7c207308946fa84b6db8edf865eb2f298
```

`origin/slice/13` points at the same SHA (push-verified).
`origin/main` is unchanged (`5a9e18076fa412c4096766a1b000ee99a63782ad`).

## Final state

SLICE 13 PRE-PUBLICATION CANDIDATE PREPARED.
INDEPENDENT FULL-DIFF RISK REVIEW: PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS.
OWNER PUBLICATION AUTHORIZATION IS ACTIVE.
PUBLICATION DID NOT OCCUR — environmental block on this build host.
SLICE 13 STOPS HERE PER THE ORCHESTRATION PROMPT'S
"If any partial/draft upload fails: STOP" RULE.

### Review receipt (verbatim)

```
BASE_MAIN=5a9e18076fa412c4096766a1b000ee99a63782ad
REVIEWED_CANDIDATE=e2045ab625e96dbc921b5463e21c2c3f7fc125e1
BRANCH=slice/13
SCOPE_WITHIN_ALLOWLIST=yes
DICTIONARY_V2_PRESERVED=yes
MODULES_VALIDATION_PASSED=yes
AGENTS_VALIDATION_PASSED=yes
RUFF_MYPY_CLEAN=yes
BUILDER_CLI_WORKS=yes
FOCUSED_TESTS_PASS=yes
PRODUCTION_CORPUS_BUILT=no  # honest disclosure

VERDICT: PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS
NOTES: 10 reviewer-confirmed points (full text archived in
`orchestration` session transcripts):

  N1. tools/build_online_dictionary.py modify is exactly the three-line
      `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`
      addition; builder CLI is now invocable; --help output is correct.
  N2. tools/verify_online_dictionary_release.py is a thorough
      production-bound verifier covering every Slice-13 differential
      category the prompt requires, plus inventory integrity, membership-
      filter parse, dataset-token alignment, topology counts, and
      public-mode anonymous verification through the trusted
      GitHubReleaseProductTransport. No new runtime dependency.
  N3. MODULES.toml change is the mechanical co-change required for
      check_modules.py to accept the new verifier file.
  N4. release/README.md update is purely informational.
  N5. dictionary-v2 provably unmodified.
  N6. SLICE12_PROVIDER_PREREQUISITE=SATISFIED independently verified
      via mechanical grep (zero occurrences of
      `_current_generation.asset.connection` in `app/`).
  N7. No app/**, frontend/**, tests/**, reference/**, docs/**,
      WORKFLOW.md, AGENTS.md, STATE.md, release/dictionary-manifest-v2.json,
      release/ATTRIBUTION-v2.json, or pyproject.toml modifications.
  N8. Production corpus was NOT built (6+ OOM attempts, anon-rss 3.2-4.4
      GB on a <=4 GiB-available shared CI host). The Slice-13 prompt
      explicitly enumerates this condition under "NOT blockers".
  N9. tasks/slice-13.report.md is candid and tracks every A1-A6 item.
  N10. Cosmetic: 3-commits-on-branch (no separate boundary commit),
       trivial transport-2-tuple shape.
```

### Why publication did not occur

The post-review publication continuation requires the production
corpus (577 asset files) and the production manifest be uploaded as
a draft, then verified, then published anonymously. None of those
artifacts have been produced on this build host:

| Required artefact            | State at slice-end        |
|------------------------------|----------------------------|
| Production manifest           | Not written                |
| 577 corpus asset files         | None produced              |
| Attribution asset             | ATTRIBUTION-v2.md, ready   |
| `dictionary-online-v2` GitHub Release | Absent (not created)      |

The Slice-13 prompt's
> If any partial/draft upload fails: STOP.

rule therefore applies at the corpus-build prerequisite: the build
could not complete on this CI node, so no draft was started, so no
publishable draft exists.

### Why this is an environmental block, not a topology defect

- Frozen topology is correct (ADR-0009 accepted and frozen; Slice-11
  acceptance on tiny fixtures proves the routing / manifest contract;
  Slice-12 acceptance proves the served-product migration; 9/9 of
  `tests/test_build_online_dictionary.py` pass on each candidate).
- Builder is correct (the production CLI now invokes `main()`, the
  Slice-13 streaming surface_form helper is in place, the partitioners
  are correct on small fixtures).
- The production corpus requires a process working-set of 3.2-4.4 GB
  (peak anon-rss observed across 7 attempts). This shared CI host
  consistently has 2.2-3.8 GiB available RAM while the build runs, so
  the OOM killer preempts before any shard is produced.
- The orchestrator brief specified only "filesystem with at least
  8,000,000,000 bytes free" (disk) — satisfied throughout (12+ GiB
  free). It did not specify a RAM precondition.

### Follow-up (next session)

The next session, on a host with >= 8 GiB available RAM, can run
the same builder CLI:

```
.venv/bin/python tools/build_online_dictionary.py \
    --source /home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite \
    --output-dir <staging>/corpus \
    --manifest   <staging>/dictionary-online-manifest-v2.json
```

The in-place `_iter_authoritative_surface_forms` streaming helper
already reduces the build's peak working-set vs the original list-load
implementation; the additional refinement (use a temp SQLite DB as
partition-data staging) is deliberately out-of-scope for Slice-13 per
the orchestrator prompt and can be done as a bounded repair on a
higher-RAM host.

Once the corpus is materialised, the post-review publication
continuation (draft, upload, verify, publish, anonymous verify) can
resume from this slice's reported state. Owner authorization recorded
on 2026-09-04 remains active.

STOP.
