# Slice 4 — Gate 2: real-textbook Stage-01 dictionary coverage

Task:        Execute ADR-0002 §6 order 5 / ADR-0001 §13 Gate 2 against a real Stage-01 dictionary asset and 200–300 vocabulary headwords from one real German-textbook unit. Produce a deterministic coverage receipt and misses list. This slice is a design gate: baseline coverage `<85%` returns to governance; `85% <= coverage < 95%` requires exactly one separately orchestrated splitter/fuzzy remedy cycle in this same slice before a rerun; `coverage >=95%` continues directly. No stage-02 work may start before Gate 2 reaches its accepted decision point.

Depends:     slice-3

Precondition: slice-3 is accepted, merged and closed. The slice-4 orchestrator supplies all four non-repository inputs before dispatch: `GATE2_EN_JSONL=<real English-edition Wiktextract JSONL>`, `GATE2_DE_JSONL=<real German-edition Wiktextract JSONL>`, `GATE2_WORDS_FILE=<UTF-8 file containing 200–300 unique vocabulary headwords from one real textbook unit, one entry per line>`, and non-empty `GATE2_UNIT_LABEL=<human-readable textbook/unit label>`. Those source files remain local and uncommitted. Missing/invalid inputs block dispatch rather than becoming synthetic substitutes.

Allowlist:
- `tools/gate2_coverage.py`
- `tests/test_gate2_coverage.py`
- `tasks/slice-4.report.md`

Acceptance:
(C1) Add `tools/gate2_coverage.py`, a deterministic local-only measurement CLI:

`python tools/gate2_coverage.py --dictionary <stage01.sqlite> --words <words.txt> --misses-out <misses.txt>`

It imports and uses the canonical `app.dictionary.Dictionary` and `app.resolve.resolve_word`; it does not copy or reimplement resolution logic.

(C2) The word file is UTF-8 and, after stripping leading/trailing whitespace and rejecting blank lines, must contain between 200 and 300 entries inclusive. Duplicate normalized input lines are a hard error rather than being silently removed because changing the denominator would bias the gate.

(C3) Textbook entries are evaluated exactly as follows. Strip surrounding whitespace. If an entry has the exact form `der <term>`, `die <term>`, or `das <term>` with a non-empty remainder, evaluate `<term>` with that article passed as the resolver gender hint. Otherwise evaluate the complete stripped entry unchanged. Do not stem, fuzzy-match, translate, spell-correct, split punctuation, or otherwise massage baseline input.

(C4) Resolve every entry through `resolve_word(term, dictionary, gender=gender_hint)`. An entry is a hit iff at least one returned reference has `status` equal to `resolved` or `derived_compound`. It is a miss iff no returned reference has either status. Preserve input order in the misses output.

(C5) The CLI prints machine-readable JSON containing at least: `total`, `hits`, `misses`, exact unrounded `coverage_ratio`, a display percentage, and the misses-output path. Threshold decisions use integer arithmetic, never rounded display percentages:
- `100 * hits < 85 * total` -> `GOVERNANCE_REDESIGN_REQUIRED`
- `85 * total <= 100 * hits < 95 * total` -> `REMEDY_REQUIRED`
- `100 * hits >= 95 * total` -> `CONTINUE`

(C6) The CLI refuses to overwrite an existing `--misses-out` path. Measurement failure leaves no completed misses file. It performs no network call, download, LLM/API call, secret read, user-DB mutation, or dictionary mutation.

(C7) `tests/test_gate2_coverage.py` proves: 200 and 300 inputs are accepted; 199/301 rejected; blank and duplicate input rejected; article/gender normalization; exact hit; surface-form hit; derived-compound hit using a fully stable D46 component binding; miss classification; deterministic misses order; no rounded-threshold error at both 85% and 95% boundaries; and output-collision failure.

(C8) For the real Gate-2 run, first build a fresh local Stage-01 asset using the accepted slice-3 CLI:

`python tools/build_dict.py stage01 --en-jsonl "$GATE2_EN_JSONL" --de-jsonl "$GATE2_DE_JSONL" --output build/gate2/stage01.sqlite`

`build/` is already ignored. Do not commit the real Wiktextract dumps, textbook word list, generated SQLite asset, or generated misses file.

(C9) Run the coverage CLI against that fresh real asset and the supplied real textbook-unit list. Record in `tasks/slice-4.report.md`: unit label; input word count; hits; misses; exact ratio; display percentage; threshold decision; SHA-256 of the textbook word-list file; Stage-01 lemma/sense/sense_meaning row counts; exact misses count; and the complete command/gate evidence. Do not record private absolute machine paths.

(C10) Gate decision is mechanical:
- baseline `<85%`: write `Decision: GOVERNANCE_REDESIGN_REQUIRED`, commit/push the measurement/report, then STOP. This is an ADR-0002 design-gate outcome, not a WORKFLOW §5 implementation failure. Stage 02 is forbidden.
- baseline `85% <= coverage <95%`: write `Decision: REMEDY_REQUIRED`, commit/push the baseline measurement/report, then STOP and return the exact misses and measurement evidence to this slice's orchestrator. Do NOT invent or implement the fuzzy/splitter remedy in this worker. The orchestrator must issue one explicit remedy amendment/dispatch inside slice-4, after which Gate 2 is rerun exactly once. This branch is a design-gate branch, not a WORKFLOW §5 failure.
- baseline `>=95%`: write `Decision: CONTINUE`; no remedy is permitted or needed.
- after the one authorized 85–<95 remedy cycle: rerun once; result `<85%` -> governance redesign; result `>=85%` -> record the rerun and continue, exactly as ADR-0002 §6 specifies. There is no second Gate-2 remedy cycle.

(C11) `make gate` and `git diff --check` pass. Real input/output artifacts stay untracked/ignored and outside the commit. No existing application/schema code changes are permitted by this baseline brief.

(C12) `tasks/slice-4.report.md` contains:
- baseline input/evidence;
- baseline decision;
- if applicable, a clearly separated one-time remedy/rerun amendment authored only after orchestrator dispatch;
- Stop-and-ask conditions;
- work left undone;
- explicit statement that Gate 2 is ADR-0002 §6 order 5 and not the WORKFLOW §5 retry ladder.

Stop-and-ask:
- any `Depends:` verification fails;
- one of the four required Gate-2 inputs is absent;
- the real textbook list is not 200–300 unique nonblank entries;
- the word list is not from one real textbook unit as attested by the supplied `GATE2_UNIT_LABEL`;
- the real Wiktextract inputs cannot be consumed by accepted Stage-01 without changing slice-3's contract;
- Stage-01 build fails;
- satisfying baseline measurement requires changing `app/`, `reference/schema.sql`, dependencies, ADRs, AGENTS, WORKFLOW, or any path outside the Allowlist;
- baseline result is 85–<95 and no explicit orchestrator remedy amendment has yet been issued;
- a requested operation would overwrite an existing real/generated input or output;
- the Gate-2 procedure cannot classify an observed vocabulary entry without inventing preprocessing not specified here.

Risk:        none

Why-risk:    WORKFLOW.md §6 path lookup: the baseline Gate-2 allowlist contains one maintainer-only measurement tool, its tests, and its report. It touches no schema/migration, auth/security code, public external API contract, destructive transform, user data, or existing data artifact. The tool refuses output overwrite. If the 85–<95 branch requires an `app/` remedy, the orchestrator must author a separate explicit remedy amendment and recompute its Risk label before dispatch.

Model:       gemini-flash / T1 / low

Why:         WORKFLOW.md §4: the baseline Gate-2 procedure is fully specified, deterministic, tightly allowlisted, and automatically verified; the threshold decision is integer arithmetic with no implementation judgment. The branch that might require design/code judgment is deliberately returned to the orchestrator rather than delegated.

Fallback:    codex-low / T1 / low

## Worker implementation constraints

1. Read `app/resolve.py`, `app/dictionary.py`, `tools/build_dict.py`, ADR-0001 Gate 2, ADR-0002 §6, AGENTS R2/R3/R9/R11/R13, and this brief before editing.
2. Do not edit `app/resolve.py`, `app/dictionary.py`, `tools/build_dict.py`, schema, dependencies, or governance files.
3. The real textbook word list and real Wiktextract dumps are local evaluation inputs, not repository fixtures.
4. Build the real Stage-01 asset under `build/gate2/`; never commit it.
5. Do not download data automatically.
6. Do not implement stage 02.
7. Do not apply fuzzy matching or splitter changes during baseline measurement.
8. The 85–<95 branch returns to the slice-4 orchestrator for one explicit remedy amendment. That return is not a WORKFLOW §5 failure.
9. The `<85%` branch returns to governance. Do not attempt to rescue the design.
10. Preserve the exact ADR-0002 thresholds and sequence.

## Required report scaffold

Create:

```markdown
# Slice 4 report

## NARRATIVE

### Gate-2 baseline
Unit:
Words SHA-256:
Total:
Hits:
Misses:
Coverage ratio:
Display coverage:
Decision:

### Gate-2 remedy/rerun
Not applicable unless baseline is 85–<95 and an explicit orchestrator remedy amendment is later issued.

### Stop-and-ask
None or exact condition.

### Work left undone
```

Populate from executable evidence only.
