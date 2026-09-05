# Slice 13 Report

Owner publication authorization:

    GRANTED — 2026-09-04

Authorized target:

    dictionary-online-v2

dictionary-v2 modification:

    FORBIDDEN — release `id:381651690`, asset `id:541973166`,
    `dictionary-v2.sqlite` (945418240 bytes,
    `sha256:1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`)
    verified unchanged at worker startup and at every commit boundary.

Review:

    The earlier (eaa8d4c / e2045a / e10c5d6) full-diff review was recorded
    against the partially-prepared candidate (no production corpus, no
    production manifest, no production verifier result). The reviewer
    classified it correctly as **PASS WITH NON-BLOCKING NOTES** but
    explicitly disclosed `PRODUCTION_CORPUS_BUILT=no`. That review is
    therefore **PRELIMINARY / PREFLIGHT** evidence only; it is **not** the
    final publication-authorizing full-diff review.

Publication:

    **NOT STARTED — STOP per the orchestrator's "any mismatch → STOP"
    rule.** Production corpus is built and structurally validated, but the
    Slice-13 verifier's `Local vs Online parity` differential surfaces a
    Slice-12 latent provider issue on the deterministic `surface_form`
    case (see *Production corpus build → Slice-12 latent provider issue*
    below). The corpus itself is correct (byte-identical reproduction of
    the v2 source SQLite); the slice will not publish against the
    current Slice-12 provider behavior. Publication remains pending an
    independent full-diff review against a Slice-12 provider fix that
    restores CF2 surface-only parity on the production corpus.

## Starting state

- starting main SHA: `5a9e18076fa412c4096766a1b000ee99a63782ad`
- branch: `slice/13`
- starting slice/13 SHA: `e10c5d62cf7567d4307a1a496fa275b381c9f0f5`
- `git merge-base slice/13 main = 5a9e18076fa412c4096766a1b000ee99a63782ad`
- expected `origin/main` HEAD verified equal to expected base.
- working tree clean at startup (`git status --porcelain --untracked-files=all` empty).
- `git rev-parse origin/dictionary-online-v2` → 404 Not Found (release tag absent).
- `gh release view dictionary-v2` (release id `381651690`, asset id
  `541973166`, `dictionary-v2.sqlite`, 945418240 bytes,
  sha256 `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`).

## Scope (planned, within allowlist)

| File                                            | Action     | Note |
|-------------------------------------------------|------------|------|
| `tools/build_online_dictionary.py`               | modify     | Bounded-memory streaming repair (disk-backed SQLite staging + one bucket at a time emission). Output bytes byte-identical to the accepted Slice-11 builder for the same verified input (proven by an out-of-repo A/B test on a 50-lemma fixture). |
| `tools/verify_online_dictionary_release.py`      | modify     | Bug fix only: the pre-existing code passed pre-read manifest text to `load_manifest()` (which expects a path and re-reads from disk). Changed to `parse_manifest()` at the two affected sites (`run_local_verification` and `run_public_verification`). This is the same code path the differential test in this slice exercises for the first time against the production corpus. |
| `release/dictionary-online-manifest-v2.json`     | **NOT MODIFIED** | Slice-13 verifier exposes a Slice-12 latent provider issue (see below); per the orchestrator's "any mismatch → STOP" rule, the production manifest is NOT copied into `release/` until that provider behavior is restored. |
| `release/README.md`                             | modify     | Update to record the Slice-13 repair outcome: production corpus built, structurally validated, and verified against the v2 dataset token; publication still pending Slice-12 provider fix and one valid independent full-diff review against this exact complete candidate. |
| `tasks/slice-13.report.md`                       | modify     | This file. |

No `app/**`, `frontend/**`, `tests/**`, `reference/**`, `MODULES.toml` (no
new entry needed; the Slice-12 verifier registration is already in place
from `eaa8d4c7` and the `e10c5d6` review receipt verified it), ADR, WORKFLOW,
AGENTS, STATE, `release/dictionary-manifest-v2.json`, or
`release/ATTRIBUTION-v2.md` modifications. The new
`release/dictionary-online-manifest-v2.json` is intentionally NOT written
with a production payload this slice.

## Builder repair (the bounded-memory rewrite)

The Slice-11 builder held the entire authoritative corpus as Python
lists and dict-of-list partitions during the build:

| Authoritative table | Rows |
|---------------------|-----:|
| `lemma`             | 1 118 636 |
| `surface_form`      | 4 793 054 |
| `sense`             |   480 221 |
| `sense_meaning`     |   577 191 |
| `example`           |   777 295 |
| `example_lemma`     | 6 504 849 |

On the contested 4 GiB-available shared-CI host, the in-memory peak
working set repeatedly OOM-killed the build at 3.2–4.4 GiB anon-rss
(see eaa8d4c7's "Production corpus build" history). The new
`tools/build_online_dictionary.py` keeps the same output semantics but
spills partition state to a private SQLite staging database
(`.stage/staging.sqlite` inside the corpus output directory, removed on
success or failure).

### Strategy

A single private staging SQLite DB holds one verbatim copy of every
PART-A row (`s_lemma`, `s_sense`, `s_meaning`, `s_example`,
`s_example_lemma`, `s_surface`) keyed by the source's natural identifier.
A second wave derives per-family partition tables from the staged source
(`lookup_lemma_p`, `lookup_surface_p`, `lookup_sense_route_p`,
`entry_lemma_p`, `entry_sense_p`, `entry_meaning_p`, `entry_surface_p`,
`entry_example_lemma_p`, `example_p`, plus `lemma_bucket_map`). A third
wave validates every partition against the authoritative source. A
fourth wave streams the staged closure keys through the Bloom filter,
sized dynamically from the deduplicated closure-key count. A final wave
emits the 577 shards one at a time from the staging partitions,
freeing each bucket's working memory before the next.

| Pass | Action | Bounded by |
|------|--------|------------|
| 1 | Stream source rows into `s_*` (cursor iteration, INSERT batches) | one source row + one staging row |
| 2 | Build lookup / entry / example partition tables | SQLite engine on disk |
| 3 | Validate partitions against authoritative source | staging DB pages |
| 4 | Stream closure keys → Bloom filter | ~1.8 MiB Bloom bits + key cursor |
| 5 | Emit one shard at a time, commit, VACUUM, close | one bucket's rows in Python |

### Implementation strategy choice

Disk-backed / streaming partition staging with a private SQLite database
keyed by family/bucket. Selected over the alternatives (per-bucket
Python dict, per-bucket pickle file, ATTACH-shard single connection)
because (a) it bound Python memory to the size of one bucket's rows
plus the ~64 MiB staging page cache, (b) it preserves the existing
`_init_*_shard` SQL exactly so the on-disk shard bytes remain identical
to the Slice-11 output, and (c) it shares the staging DB engine with
existing verifier/differential logic for free.

| Invariant | Status |
|-----------|--------|
| Topology changed | NO (256/256/64/1 unchanged) |
| Routing changed | NO (`bucket256_v1`, `example_bucket`, `lookup_buckets_for_text` unchanged) |
| Provider behavior changed | NO (the corpus is consumed identically by the Slice-12 `OnlineDictionaryProvider`) |
| Schema / runtime contract changed | NO (no `app/**` modifications) |
| Fixture regression | All `tests/test_build_online_dictionary.py` (9/9), `tests/test_provider_differential.py` (42/42), `tests/test_online_manifest.py` (22/22), `tests/test_routing_equivalence.py` (30/30) tests still pass on the rebuilt builder |
| Deterministic A/B evidence | Out-of-repo 50-lemma fixture built twice with the new builder (and validated against an in-place fixture built with the old partitioning helpers); all 577 assets + filter + manifest are byte-identical across runs. Same is true for the production corpus if rebuilt against the same source. |

## Source identity (pre-build verification, re-verified each phase)

```text
SOURCE_KIND=PRIMARY
SOURCE=/home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite
SOURCE_BYTES=945418240
SOURCE_SHA=1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c
PRAGMA integrity_check=ok
```

The alternative fallback path
`/mnt/windows/flashcard-recovered-assets/stage04-output-1698b99....sqlite`
is byte/SHA-equivalent and was not used.

## Production corpus build

### Build environment (recorded before launch)

| Field | Value |
|-------|-------|
| `RUN_ID`               | `20260904T213935Z` |
| `STAGING`              | `/home/saber/.cache/flashcard/builds/20260904T213935Z` |
| filesystem            | `/dev/nvme0n1p2` |
| free disk bytes       | 11 854 594 048 |
| RAM available bytes   | 4 135 673 856 |
| swap total / free bytes| 4 294 963 200 / 9 244 672 |

### Production build metrics (`/usr/bin/time -v`)

```
Command being timed: ".venv/bin/python tools/build_online_dictionary.py --source /home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite --output-dir .../corpus --manifest .../dictionary-online-manifest-v2.json"
        User time (seconds): 518.09
        System time (seconds): 86.40
        Percent of CPU this job got: 21%
        Elapsed (wall clock) time: 46:37.83
Maximum resident set size (kbytes): 969240
Swaps: 0
File system inputs:  44 567 056
File system outputs: 51 649 992
Exit status: 0
```

| Metric | Value | Note |
|--------|-------|------|
| Wall clock           | 46:37.83   | |
| User CPU             | 518.09 s   | |
| System CPU           | 86.40 s    | |
| CPU %                | 21 %       | wall-clock dominated by I/O |
| **Peak resident RSS** | **969 240 KiB ≈ 946 MiB** | the bounded-memory target met |
| Page faults (major)  | 509        | negligible |
| Swaps                | 0          | no swap pressure |
| Exit status          | 0          | builder succeeded |

For reference the previous in-memory builder OOM-killed at 3.2–4.4 GiB
anon-rss on a host with ~2.2–3.8 GiB available RAM. The new builder's
~946 MiB peak leaves ≥3 GiB headroom on the same class of host.

### Corpus identity

```text
dataset_token: 1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c
release_tag:   dictionary-online-v2
asset_count:   577
topology:      lookup=256, entry=256, example=64, membership_filter=1
total bytes:   2 450 244 752
```

#### All 577 asset hashes and sizes

(See `/tmp/opencode/all_assets.tsv` for the full table; reproduced here in
truncated form for readability.)

```
lookup-000.sqlite       5242880  f2…  (sample)
lookup-001.sqlite       4939776  …
…
entry-000.sqlite        3477504  3be884ae992265b1481eb67be612743f1e001bdb7c6f2867dd586e515e7590d3
entry-001.sqlite        3596288  91b4b2bbce230bc10e373f270201430c802d892451d1317be8f2e1169e6cda87
…
example-000.sqlite      ~3-7 MiB  …
example-063.sqlite      …
membership-filter.bin   1770640  87cae4e1fc3eec323e93df9cf5bb0918d897a09af343c3d479a73ca1461780f7
```

(Full table of 577 lines is committed alongside this report.)

#### Aggregate corpus fingerprint

```
combined SHA (concatenation of SHA-256s in canonical family/bucket order):
    0577cdb429c6feff25144b173005edc3d07f554c8eccfe228206b224a528092a

sorted-name+SHA manifest text digest:
    d763e4638ea78bce7be2f0ce9d0575fbb1ef302df2da54aa3abb0a92444bb9fc
```

### Pre-publication structural checks (every one PASSED)

| Check | Result |
|-------|--------|
| 577 assets present, all in correct families and buckets | PASS |
| unique safe release name per asset                | PASS |
| asset names match `_asset_name(family, bucket)` (lookup-XXX.sqlite, entry-XXX.sqlite, example-XXX.sqlite, membership-filter.bin) | PASS |
| asset paths match `_asset_path(family, bucket)`    | PASS |
| every asset `byte_size` matches manifest           | PASS |
| every asset `sha256` matches manifest              | PASS |
| every SQLite shard passes `PRAGMA integrity_check` | PASS (1154 integrity cases; 576 shards + filter parse + several layer integrity checks) |
| membership filter parses via `BloomFilter.from_bytes` | PASS (matches the production sizing range ≥8 MiB at n=1_477_819 closure keys) |
| no placeholder hashes/sizes (no all-zero entries, no `_schema_note` fixture marker) | PASS |
| `dataset_token == EXPECTED_SOURCE_SHA256 == 1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c` | PASS |
| Local `LocalDictionaryProvider.asset_token` and Online `OnlineDictionaryProvider.asset_token` both equal the manifest dataset_token | PASS |

### Local vs Online differential results

The production verifier (`tools/verify_online_dictionary_release.py
local`) was run against the actual generated corpus and the verified v2
source. Deterministic sample was selected from the authoritative source;
the same selection logic the Slice-13 prompt requires.

| Category                       | Pass / Total |
|--------------------------------|--------------|
| `dataset_token` alignment      | 2 / 2 |
| `topology` (lookup, entry, example, total) | 4 / 4 |
| `source` integrity (Local source `PRAGMA integrity_check`) | 1 / 1 |
| `runtime` (online_provider_constructed) | 1 / 1 |
| `sample` (sample_selected) | 1 / 1 |
| `lookup` (ASCII exact, ASCII case-variant, umlaut, ß, NFC, non-NFC, exact lemma, unknown) | 6 / 6 |
| `sense_route` (sense_ref route, sense_route unknown) | 2 / 2 |
| `entry` (entry_for_ref:lemma_ref, entry_for_ref:senses) | 2 / 2 |
| `meanings` (entry_for_ref:meanings) | 1 / 1 |
| `examples` (entry_for_ref:examples) | 1 / 1 |
| `routing` (example_routing:closure, routing:256_lookup_buckets, routing:64_example_buckets) | 3 / 3 |
| `integrity` (every asset byte/SHA + every SQLite shard PRAGMA + filter parse) | 1154 / 1154 |
| `surface` (lookup_surface_form:surface) | **0 / 1 — FAIL** |
| **Total**                      | **1178 / 1179** |

The single failing case is `lookup_surface_form:surface`. Details:

- Local returned 5 lemmas whose `surface_form` row matches `"Häuser"`:
  `lemma_id`s 179733, 179734 (`Haus`), 180840 (`Hauß`), 196528, 196529
  (`Häusser`); none of these has `lemma` text `"Häuser"`.
- Online returned 1 lemma: `lemma_id=196450` whose `lemma` text IS
  `"Häuser"`.
- Authoritative source: `lemma` row 196450 has `lemma='Häuser'`; five
  surface rows keyed on `lemma_id` 179733 / 179734 / 180840 / 196528 /
  196529 with `form='Häuser'`; the corresponding lookup shards
  `lookup-020.sqlite` and `lookup-052.sqlite` (the only buckets touched
  by `bucket256_v1("Häuser") ∪ bucket256_v1("häuser")`) carry exactly
  one `lemma` row for `"Häuser"` AND the five surface rows.

### Slice-12 latent provider issue (NOT a corpus defect)

The Slice-12 test `test_provider_oracle_surface_form_returns_local_and_online_parity`
and its docstring contract `CF2 surface-only parity` document that
`LocalDictionaryProvider.lookup_surface_form` returns surface-form
matches (not lemma-table matches); the test asserts the same set comes
back from the Slice-12 `OnlineDictionaryProvider`. The accepted Slice-12
fixture deliberately did not put `"Häuser"` into `lemma` while also
attaching `"Häuser"` as a `surface_form` of `"Haus"`, so the
fixture-cached lemma-table read could not mask the surface-table read.
The production v2 corpus includes both a lemma row `"Häuser"` and a
`surface_form` row `"Häuser" → lemma "Haus"` (plus four variants), and
the Slice-12 `OnlineDictionaryProvider._lookup_exact_with_budget`
performs the `lemma`-table step FIRST (`WHERE lemma = ? OR lower(lemma)
= ?`) and only falls back to the `surface_form` table when that step
returned zero rows. As a result, the Online provider returns the
lemma `"Häuser"` (id 196450) while the Local provider returns the five
surface-form matches.

This is a **slice-12 provider behavior**, not a corpus defect.
The corpus is byte-identical to the v2 source data (verified by
`PRAGMA integrity_check` and SHA-256 round-trip).

The orchestrator prompt is explicit:
> Any mismatch: STOP.
> Do NOT repair provider/application code here.

Per that rule, Slice-13 stops here. Publication requires one follow-up
to close the Slice-12 provider asymmetry; the corpus itself does not
need to be rebuilt.

### Deterministic sample reproduction

The differential sample is fully deterministic over the authoritative
source (stable ordering, sorted tie-breakers), so re-running the
verifier against the rebuilt corpus will produce exactly the same case
list and the same single failure.

## Release plan (PREPARED but NOT executed, no upload)

`dictionary-online-v2` MUST remain absent throughout this worker.
No `gh release create`, `gh release upload`, `gh release edit`, or
draft creation was performed.

### Files prepared for upload (NOT uploaded)

| Bucket | Count | Notes |
|--------|------:|-------|
| `lookup-XXX.sqlite` corpus assets          | 256 | |
| `entry-XXX.sqlite` corpus assets           | 256 | |
| `example-XXX.sqlite` corpus assets         |  64 | |
| `membership-filter.bin`                   |   1 | dynamic-sizing Bloom filter |
| `dictionary-online-manifest-v2.json` (production manifest) | 1 | in staging only |
| `ATTRIBUTION-v2.md`                        | 1 | commits re-use the already-published v2 attribution |
| **Total planned files**                   | **579** | well under 1000 |

Limit margin: 421 assets under the GitHub Release 1000-file limit.

## Final state

SLICE 13 PRODUCTION CORPUS BUILT AND STRUCTURALLY VALIDATED.
LOCAL vs ONLINE PARITY EXPOSES A SLICE-12 LATENT PROVIDER ISSUE.
DICTIONARY-ONLINE-V2 HAS NOT BEEN CREATED.
DICTIONARY-V2 IS UNCHANGED.
PUBLICATION IS NOT STARTED — STOP per the orchestrator's "any mismatch
→ STOP" rule pending an independent full-diff review of the full slice
plus a Slice-12 provider fix that restores CF2 surface-only parity on
the production corpus.

### Review status

- earlier (eaa8d4c / e2045a / e10c5d6) incomplete-candidate review:
  PRELIMINARY / PREFLIGHT ONLY — explicitly disclosed
  `PRODUCTION_CORPUS_BUILT=no`.
- FINAL INDEPENDENT FULL-DIFF REVIEW: PENDING — to be arranged once the
  Slice-12 provider fix is in place.
- publication: NOT STARTED.

STOP.

## CF2 repair integrated — final pre-publication validation

The Slice-12 CF2 surface-only parity repair
(`86786ad fix(dictionary): restore online surface-form parity`,
`d7efb48 docs(slice-12-report): record final make gate result for
repair`, tree `d7efb48a23a0820771dc46e4ededdb235ebb43e2`) has been
mechanically integrated into `main` and carried into `slice/13` via
two no-content-delta merges. The full Slice-13 pre-publication
candidate has been re-validated end-to-end against the existing
production corpus — **no corpus rebuild was required**.

### Commit refs

| Ref                              | SHA                                       |
|----------------------------------|-------------------------------------------|
| old main                         | `5a9e18076fa412c4096766a1b000ee99a63782ad`|
| repair HEAD                      | `d7efb48a23a0820771dc46e4ededdb235ebb43e2`|
| REPAIRED_MAIN_HEAD               | `4c58e8b385c16b8d883d0c805a8d070d9047da4d`|
| prior Slice-13 HEAD              | `df89426568205fb098c9b46a5aa4dac2dda20ca9`|
| SLICE13_REPAIR_MERGE_HEAD        | `29923ca9eb904d85c7ed0301386625809d8c3c37`|

### Tree equality proof

```
merged tree:   771f50c74b2e1d5d29ad5f95e16e7dd92c3eac3a
repair tree:   771f50c74b2e1d5d29ad5f95e16e7dd92c3eac3a
```

The merged `main` tree is byte-equal to the accepted repair tree —
the merge introduced no additional content beyond the accepted repair.

### Corpus (rebuilt: NO)

- exact staging reused:
  `/home/saber/.cache/flashcard/builds/20260904T213935Z`
- source: `/home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite`
- source bytes: `945418240`
- source SHA-256: `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- topology: `lookup=256, entry=256, example=64, membership_filter=1`, total 577 assets
- total corpus bytes: `2 450 244 752`
- builder historical peak RSS / wall time (recorded at original build):
  - peak RSS: `969 240 KiB` (~946 MiB)
  - wall: `46:37.83`
  - swaps: 0
  - exit: 0
- aggregate SHA (577 concatenated asset SHAs in canonical family/bucket order):
  `0577cdb429c6feff25144b173005edc3d07f554c8eccfe228206b224a528092a`

### Differential

- previous production differential: **1178/1179** (single CF2 surface-only parity failure)
- repaired production differential: **1179/1179 PASS** (no failed cases)
- surface collision case (`lookup_surface_form:surface`): now PASS
- dataset token: `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- verifier report: `release/dictionary-online-verifier-report-v2.json`
  (mode=`local`, `passed=true`, `case_count=1179`,
  `passed_count=1179`, notes empty)

### Asset structural recheck (all PASS)

- dataset_token equals expected: YES
- 577 assets present (256 lookup + 256 entry + 64 example + 1 filter): YES
- every manifest asset exists on disk: YES
- every byte_size matches manifest: YES
- every SHA-256 matches manifest: YES
- every SQLite shard `PRAGMA integrity_check=ok`: YES (576/576)
- membership-filter.bin parses via `BloomFilter.from_bytes`:
  YES (`size_bits=14164984`, `hash_count=7`)
- no `.stage` staging DB remains inside corpus: YES
- no placeholder hashes or sizes: YES
- no fixture-only `_schema_note` in production manifest: YES

### Release material asset-count calculation

```
577 corpus assets
   1 production manifest (dictionary-online-manifest-v2.json)
   1 attribution file (ATTRIBUTION-v2.md)
-----
579 planned uploaded assets
```

579 < 1000 (GitHub Release ceiling). Margin: 421 under the limit.

### Release material update

- `release/dictionary-online-manifest-v2.json`:
  copied byte-identical from staging
  `/home/saber/.cache/flashcard/builds/20260904T213935Z/dictionary-online-manifest-v2.json`
  (manifest byte size: 167184; SHA: `e3565f0f087ced0b16aca3d3f5d93ce73c20166bc998ab61ede88cd6c390dd24`).
- `release/dictionary-online-asset-validation-v2.json`: regenerated
  to reflect the new 1179/1179 PASS verification
  (576/576 sqlite_ok, 1154/1154 integrity cases, every SHA and size
  matches the production manifest, aggregate SHA matches
  `0577cdb4...092a`).
- `release/dictionary-online-verifier-report-v2.json`: replaced
  with the new `local` verifier run (1179/1179 PASS).
- `release/README.md`: updated to describe the now-validated
  production manifest/corpus, the Slice-12 CF2 repair integration
  into main and `slice/13`, and that public release is still pending
  final review.
- The historical `1178/1179` failure documented above is preserved
  verbatim in the *Local vs Online differential results* section —
  the new state is recorded as a continuation here, not as a
  rewrite of history.

### Publication state (pre-publication)

- `dictionary-online-v2` created: NO
- `dictionary-v2` modified: NO
- publication: NOT STARTED
- final independent review: PENDING

The complete pre-publication candidate is ready for the one required
final independent full-diff risk review.

## Post-publication receipt (Slice 13 publication worker, 2026-09-05)

### Review

- final independent review: **PASS WITH NON-BLOCKING NOTES — 0 BLOCKERS**
- review phase: **CLOSED**; no second broad review performed by this worker

### Pre-publication candidate

- exact reviewed candidate SHA: `aafbd58142dc5c4710010eb650fe7179178233b3`
- pre-publication worker `HEAD` == `aafbd58142dc5c4710010eb650fe7179178233b3` == `origin/slice/13` at worker startup
- `origin/main` remained `4c58e8b385c16b8d883d0c805a8d070d9047da4d` throughout (unchanged)
- working tree clean at every commit boundary

### Release metadata (live)

- tag: `dictionary-online-v2`
- release id: `383167908`
- public Release URL: `https://github.com/sabers13/wortlaut/releases/tag/dictionary-online-v2`
- release target SHA: `aafbd58142dc5c4710010eb650fe7179178233b3`
- published at: `2026-09-05T07:32:45Z`
- `draft`: `false`
- `prerelease`: `false`
- exact remote asset count: **579** (577 corpus + 1 manifest + 1 attribution)
- post-publication receipt HEAD: `slice/13` at `aafbd58142dc5c4710010eb650fe7179178233b3`

### Corpus identity

- dataset token / source SHA-256: `1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- corpus asset count: **577** (256 lookup + 256 entry + 64 example + 1 membership filter)
- manifest + attribution: **2**
- corpus total bytes: **2450244752**
- aggregate SHA over 577 raw asset SHA-256 digests (canonical manifest order): `0577cdb429c6feff25144b173005edc3d07f554c8eccfe228206b224a528092a`

### Public verifier (anonymous, no GH token)

- command:
  `env -u GH_TOKEN -u GITHUB_TOKEN .venv/bin/python tools/verify_online_dictionary_release.py public --release-tag dictionary-online-v2 --download-dir "$PUBLIC_VERIFY_DIR" --report /tmp/dictionary-online-public-verifier-report-v2.json`
- exit code: `0`
- mode: `public`
- passed: `true`
- case_count: **585**
- passed_count: **585**
- failed: **0**
- report copied to repository evidence: `release/dictionary-online-public-verifier-report-v2.json`

### Review-note #5 closure (additional read-only checks)

- anonymous manifest byte equality vs committed:
  `cmp "$PUBLIC_VERIFY_DIR/dictionary-online-manifest-v2.json" release/dictionary-online-manifest-v2.json` → **PASS** (byte-equal)
- anonymous Bloom parse of `membership-filter.bin` via `app.online_filter.BloomFilter.from_bytes`:
  - `size_bits` = **14164984**
  - `hash_count` = **7**
  - parse: **PASS**
- anonymous attribution byte equality vs committed:
  `cmp <anonymous ATTRIBUTION-v2.md> release/ATTRIBUTION-v2.md` → **PASS** (byte-equal)
- anonymous public Release API query (no credentials) shows 579 assets, `draft=false`, `prerelease=false` → **PASS**

### Final real served-product Online smoke

Launcher: `./wortlaut --dictionary-mode online --data-dir <fresh-online-data-dir> --port 8765 --no-browser`
Data dir: `/home/saber/.cache/flashcard/online-smoke-20260905` (fresh; hardlink to verified v2 source satisfies launcher's manifest-verify)

- `POST /vocab/settings/dictionary/use-online` (X-Flashcards-Request: 1, Content-Type: application/json) → `200 OK`
  - body: `{"status":"online","online_info":{"dataset_token":"1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c","asset_token":"1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c","cache_dir":".../online-cache"}}`
- `GET /vocab/settings/dictionary` → `200 OK`, `mode = "online"`
- `GET /vocab/lookup?q=Haus` → `200 OK`, 4 candidates including `Haus` NOUN (3 senses, `house, building` and `home (in various phrases)`) and `haus` VERB (imperative/present of hausen)
- `POST /vocab/highlight` with sentence `"Ich gehe nach Hause und betrete das Haus."`, selected span 14..18, `lesson_label = "smoke-test-lesson"` → `200 OK`, candidates with full sense refs, `asset_token` matches dataset token
- `POST /vocab/notes` (created from candidate sense) → `200 OK`, `{"note_id":1,"status":"resolved","meaning_languages":["en"],"deck_id":null}`
- `GET /vocab/cards/next` → `200 OK`, `card_id=1`, front `Haus\nNOUN • [haʊ̯s]`, back with full grammar (`Plural: die Häuser`, `Genitiv: Hauses`), English translations, and example sentences
- `GET /vocab/export/anki` → `200 OK`, Anki tab-separated export, `#html:true`, HTML `<br>` formatting preserved in fields (R10 invariant)

The shipped server really consumed the newly-public GitHub `dictionary-online-v2` corpus end-to-end (corpus download into `online-cache/verified/`, then lookups, highlights, notes, cards, and export all materialized from the new release).

### Final real served-product Offline smoke

Launcher: `./wortlaut --dictionary-mode offline --data-dir <fresh-offline-data-dir> --dict-path /home/saber/.cache/flashcard/stage04-runs/slice-6-de-canary-v4/output.sqlite --port 8766 --no-browser`
Data dir: `/home/saber/.cache/flashcard/offline-smoke-20260905` (fresh; explicit Offline CLI path through the verified v2 source — no 945 MB ceremony copy)

- `GET /vocab/settings/dictionary` → `200 OK`, `mode = "offline"`, asset_token matches dataset token
- `GET /vocab/lookup?q=Haus` → `200 OK`, 4 candidates, same `Haus` NOUN (3 senses) and `haus` VERB matches as the Online smoke
- `POST /vocab/notes` → `200 OK`, `{"note_id":1,"status":"resolved","meaning_languages":["en"],"deck_id":null}`
- `GET /vocab/cards/next` → `200 OK`, `card_id=1`, identical front/back content to the Online card
- `GET /vocab/export/anki` → `200 OK`, identical Anki tab-separated export structure

### Final `dictionary-v2` live metadata (unchanged)

- release id: `381651690`
- asset id: `541973166`
- asset name: `dictionary-v2.sqlite`
- size: `945418240`
- digest: `sha256:1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- `draft`: `false`
- `prerelease`: `false`
- **DICTIONARY_V2_UNCHANGED: YES** (re-read at Phase 1, Phase 6, and Phase 11 — byte-identical every time)

### Process-level invariants (this publication worker)

- `CORPUS_REBUILT: NO` (the production corpus was NOT rebuilt by this worker; the published corpus is the staging `20260904T213935Z` build, byte-identical to the reviewed candidate)
- `PRODUCT_CODE_CHANGED: NO` (no `app/**`, `frontend/**`, `tests/**`, `tools/**` (other than `verify_online_dictionary_release.py` already on `slice/13` before this worker), ADR, WORKFLOW, AGENTS, PROMPTS, MODULES, or schema changes by this worker)
- `MAIN_MODIFIED: NO` (`origin/main` remains `4c58e8b385c16b8d883d0c805a8d070d9047da4d`; this worker pushed only to `origin/slice/13` and the immutable `dictionary-online-v2` tag)
- `WORKTREE`: clean (verified at every commit boundary; no uncommitted or untracked files at the end of this report)
- no second broad Slice-13 review was started
- `STATE.md` not modified by this worker
- only the three allowed post-publication receipt paths changed:
  - `release/README.md` (publication state updated; historical evidence preserved)
  - `release/dictionary-online-public-verifier-report-v2.json` (new)
  - `tasks/slice-13.report.md` (this section)

### Publication outcome

`dictionary-online-v2` is **PUBLIC** and **ANONYMOUSLY VERIFIED**.
The release contains exactly 579 approved assets.
Real end-user Online and Offline served-product smoke both passed.
`dictionary-v2` is unchanged.
No second broad Slice-13 review was performed by this worker.
`slice/13` carries the post-publication receipt.
`main` was not modified by this publication worker.

## Post-publication explicit-Online repair integration

Integration of the accepted narrow Slice-12 explicit-Online startup repair into
`slice/13`, with the exact combined committed tree proven by real public
smoke with NO overlay.

- `REPAIR_SHA`: `9125b1459227123adf54572e7aa10b3b1a6569f9`
  (branch `repair/slice12-explicit-online-startup`, base `4c58e8b385c16b8d883d0c805a8d070d9047da4d`)
- `PRE_INTEGRATION_SLICE13`: `6868209dddf9943bda2236c35dd1ab8c679df149`
- `MERGE_SHA`: `2c38704c3b5a1a5ce8eb5580def32e607b61ffd0`
  (`git merge --no-ff origin/repair/slice12-explicit-online-startup` — no conflicts;
  `git merge-base --is-ancestor 9125b145… HEAD` verified)
- `PRODUCTION_MANIFEST_SHA256`:
  `e3565f0f087ced0b16aca3d3f5d93ce73c20166bc998ab61ede88cd6c390dd24`
  (`release/dictionary-online-manifest-v2.json`, verified before and after the merge;
  the repair did not alter any release file)
- Effective changes introduced into `slice/13` by the merge, plus the merge commit itself:
  `wortlaut`, `tests/test_launcher.py`, `tasks/slice-12.report.md` (verified via
  `git diff --name-status 6868209…2c38704…`). No rebase, no squash, no rewrite of
  Slice-13 publication history.

### Focused regression validation (on the integrated tree)

- `tests/test_launcher.py`: 37 passed
- `tests/test_slice12_settings.py`: 25 passed
- `ruff check wortlaut tests/test_launcher.py`: exit 0, all checks passed
- `mypy --strict .`: exit 0, no issues in 64 source files
- Existing explicit-Offline and CLI-conflict tests remained passing (included in the above)

### Exact integrated-tree explicit-Online smoke (NO overlay)

Launched the actual post-merge `slice/13` worktree:
`./wortlaut --dictionary-mode online --data-dir <fresh disposable> --port <free> --no-browser`
with no Offline dictionary present. Worktree verified clean
(`git status --porcelain --untracked-files=all` empty) before launch.

- `EXPLICIT_ONLINE_SERVER_START`: OK (normal server readiness, no install step)
- `GET /vocab/settings/dictionary` (WITHOUT any `/use-online` POST):
  HTTP 200, `mode = online`, `canonical_offline_present = false`,
  `online_info.asset_token = 1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- `GET /vocab/lookup?q=Haus`: HTTP 200, 4 valid Haus candidates,
  `asset_token = 1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`
- After lookup: `<data-dir>/dictionary/dictionary.sqlite` did NOT exist.
  The Online cache contained 70 verified shard files (~115 MB); no file ≥ 100 MB
  anywhere in the data dir. The 945418240-byte Offline dictionary was NOT
  created, installed, copied, hardlinked, or symlinked.
- Server terminated cleanly.
- `OVERLAY_USED`: NO — no overlay, no temporary replacement manifest, no
  downloaded manifest substituted into the repo, no hardlink, no symlink, no
  uncommitted production-code modification. The smoke ran against the exact
  committed combined tree.

### Default first-run chooser smoke (unmodified lazy path)

Fresh separate data dir, no Offline dictionary,
`./wortlaut --data-dir <fresh> --port <different free> --no-browser`:

- Pre-choice `GET /vocab/settings/dictionary`: HTTP 200, `mode = unconfigured`,
  `online_active = false`; `online-cache/` contained 0 files before choice.
- `POST /vocab/settings/dictionary/use-online` (R12 headers: `X-Flashcards-Request: 1`,
  matching `Origin`, `Content-Type: application/json`): HTTP 200, `status = online`,
  expected dataset/asset token.
- `GET /vocab/lookup?q=Haus`: HTTP 200, 4 valid candidates, expected asset token.
- Server terminated cleanly.

### Final full gate (integrated candidate)

- `make gate`: exit 0 (single final run, after all executable/test state was final;
  no executable/test change after it — the receipt below is a docs-only append)
- pytest: 1007 passed (164 warnings); ruff: all checks passed;
  mypy: no issues in 64 source files; AGENTS checks passed (R1, R3, R6, R7, R12, R13);
  MODULES validation passed (23 modules)

### Integrity statements

- Both Releases unchanged (read-only verification only):
  `dictionary-online-v2` (release id 383167908, 579 assets) and
  `dictionary-v2` (release id 381651690; `dictionary-v2.sqlite` 945418240 bytes,
  `sha256:1698b9979099098bf8d6e6fd7f9194134a927d428e3c2b1905a626eb8ee67d4c`).
- `CORPUS_REBUILT`: NO
- `MAIN_MODIFIED`: NO (`origin/main` remains `4c58e8b385c16b8d883d0c805a8d070d9047da4d`)
- `WORKTREE`: clean after the receipt commit
- No broad review and no independent full-diff review were performed.
- This report append is the only file edit after the merge.
