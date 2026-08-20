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
