# Slice 5 report

## NARRATIVE

### Escalation history

Attempt 1 was the counted T2 Failure 1: the real cache MISS began with cache
key `stage02:v1:0be1d3165dfe261b2c5706226948990b62030aa1b86c424e3e3c76cca747ef57`,
then infrastructure interrupted execution with NVMe write-timeout and
memory-pressure evidence. Its incomplete evidence remains preserved.

Attempt 2 was the counted T2 same-tier Failure 2: the real cache MISS began
with the same cache key, then systemd-oomd killed the tmux execution scope due
to memory pressure. Its incomplete evidence remains preserved; no commit or
push occurred.

Attempt 3 was the required WORKFLOW §5 one-tier escalation to T3 / high. The
CLI default remains `n_process=8`; this authorized real acceptance execution
used `n_process=1`.

The recovered implementation originally materialized all dictionary lookup
records and all Tatoeba projections in Python memory. The Stage-02 path now
uses bounded LRU read-only dictionary lookups, a disk-backed validated
projection store streamed through `nlp.pipe`, and committed output batches.
These changes preserve the specified cache, resolver, ordering, attribution,
and persistence semantics; no architecture or acceptance criterion changed.

### Stage-02 inputs

Export label: Tatoeba weekly export 2026-08-15
License: CC BY 2.0 FR
Stage-01 SHA-256: 06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547
German projection SHA-256: 093c75b568e6bc10b637a903c2e253e54670144ad25ab527490fb1278f08744c
English projection SHA-256: 9ed0e241964b6ab28b1961192fc014eac9ba12dc851462a8264dce276246f139
Links projection SHA-256: 4ce5d9123141d3c93ef6c104ef498198067d594028d81446cc47712074ca0d97
Resolver SHA-256: b09ee526951fdd28bfcfffbe3f43253c21e627e731e66d1daffeb3ca34fddc2d
spaCy model: de_core_news_md
n_process: 1

### Real cache-miss build

German sentences: 777664
English sentences: 2033977
Links: 583244
Persisted examples: 777657
Examples with EN: 494939
Examples without EN: 282718
example_lemma rows: 296004868
Distinct indexed lemmas: 112759
Output SHA-256: 070cb12a0461f70266ca1414e257e66d656cafce80c62aea8fb7a54e6dd27316
Output bytes: 4830187520
Cache key: stage02:v1:0be1d3165dfe261b2c5706226948990b62030aa1b86c424e3e3c76cca747ef57
Cache result: MISS
PRAGMA quick_check: ok
Incomplete attribution: 0
Orphan associations: 0

### Exact-key cache-hit verification

Cache result: HIT
Cache key: stage02:v1:0be1d3165dfe261b2c5706226948990b62030aa1b86c424e3e3c76cca747ef57
Output SHA-256: 070cb12a0461f70266ca1414e257e66d656cafce80c62aea8fb7a54e6dd27316
Output bytes: 4830187520
PRAGMA quick_check: ok
Logical output equality: PASS — the ordered example stream matched through all
777657 Tatoeba rows; both complete SQLite assets also have identical SHA-256,
which establishes equality of the corresponding associations and all persisted
content.

### Verification

Implementation evidence HEAD: 897bfed9596157ccf36ad949ab5f55d4677233fb
Stage-02 targeted tests: 50 passed
Stage-01 regression tests: 46 passed
make gate: PASS — 216 passed; AGENTS R3 PASS
git diff --check: PASS
Allowlist:
- tools/build_dict.py
- tests/test_build_dict_stage02.py
- tasks/slice-5.report.md
Push: pending implementation/report commits

### Stop-and-ask

None.

### Work left undone

None. Frequency and Stage 03+ remain explicitly deferred by the slice contract.

## Design-reset Attempt 2 — performance repair preflight

Base HEAD: `0c2ee4ebac8161a85c9a2091027e0d0ac7fbda09`

### Failure-1 cause and implementation

Design-reset Attempt 1's Phase-B lookup adapter performed per-token full scans
of the accepted Stage-01 `lemma` and `surface_form` relations through SQLite
`lower(...)` predicates, so it made zero first-batch commits before the
orchestrator-authorized SIGTERM (exit 143).

This retry preserves the accepted resolver semantics and lookup-oracle parity.
`Stage02LookupOracle` builds a bounded-memory, Stage-02-only temporary SQLite
accelerator once. `exact_lookup` and `surface_lookup` materialize the source
values and SQLite's own `lower(...)` values, so indexed equality lookups retain
the runtime Dictionary's SQLite/Python case behavior. The accelerator is
deleted by normal oracle cleanup and is neither a Stage-01 mutation nor durable
state.

`app/resolve.py` remained frozen at SHA-256
`0e7663bf351d177bbc3ac176f1508c549e396bed67e5c3c0928f8d8ad3cbda08`.

### Inputs and semantic evidence

Stage-01 SHA-256: `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`

Optimized lookup parity: PASS — the Stage-02 and runtime Dictionary lookup
tests cover exact, surface, sense, ordering, case, POS/gender filtering,
deduplication, and canonical `resolve_token` numeric-ID parity.

Real forensic parity: PASS — token-by-token numeric-ID sets agreed for `Was
ist das?` and `Die Großeltern haben Geschenke für ihre Enkelkinder
mitgebracht.`; `?` produced no numeric IDs, and `haben` tagged `AUX` produced
zero numeric IDs rather than wrong-POS surface matches.

Source-table query plans: PASS

```text
exact:   SEARCH exact_lookup USING PRIMARY KEY (lookup_key=?)
surface: SEARCH sl USING PRIMARY KEY (lookup_key=?)
         SEARCH l USING INTEGER PRIMARY KEY (rowid=?)
```

Neither plan scans source `lemma` or `surface_form`. The one-time permitted
source scan occurs only while materializing the accelerator.

Representative cold lookup timings:

```text
haben  exact 0.222 ms (3 rows)      surface 60.498 ms (15168 rows)
die    exact 0.096 ms (4 rows)      surface 1.060 ms (12 rows)
Haus   exact 0.059 ms (4 rows)      surface 0.070 ms (7 rows)
was    exact 0.031 ms (6 rows)      surface 0.033 ms (4 rows)
gehen  exact 0.024 ms (3 rows)      surface 0.015 ms (0 rows)
```

### Bounded real-data throughput preflight

The German projection was verified strictly ascending by numeric Tatoeba ID;
the first 5,000 rows were processed through `de_core_news_md`, `n_process=1`,
canonical `resolve_token`, and the optimized adapter. No Stage-02 output or
cache was published.

```text
Accelerator setup:                 27.230 s; 385,794,048 bytes
spaCy model load:                   1.064 s
Prefix sentences:                   5,000
Non-space tokens:                   43,120
NLP/resolver wall time:             4.731 s
Sentences/second:                   1,056.963
Tokens/second:                      9,115.249
Peak RSS:                           878,920 kB
Raw numeric associations:           39,596
Deduplicated sentence-local IDs:    37,754
Projected 777,664-sentence NLP loop: 735.8 s / 0.204 h
Performance disposition: PASS (<= 4.0 h)
```

Full real Stage-02 MISS: NOT RUN — orchestrator authorization required.

### Verification

Stage-02 targeted tests: 54 passed
Resolver tests: 25 passed
Stage-01 regression tests: 46 passed
make gate: PASS — 223 passed; AGENTS R3 PASS
git diff --check: PASS
Changed paths:

- `tools/build_dict.py`
- `tests/test_build_dict_stage02.py`
- `tasks/slice-5.report.md`

### Stop-and-ask

None.

### Work left undone

The required real cache-MISS and exact-key cache-HIT remain intentionally
unrun pending explicit orchestrator authorization. Frequency and Stage 03+ are
unchanged and deferred.
