# Slice 4 report

## NARRATIVE

### Gate-2 baseline
Unit: Deutsch im Blick — Kapitel 1: Willkommen in Würzburg! (COERLL, CC BY)
Words SHA-256: 2f2c35ea5ebb19ad4a69c19d5505836bb603453b73086c6902753d5786282924
Total: 200
Hits: 189
Misses: 11
Coverage ratio: 0.945
Display coverage: 94.50%
Decision: REMEDY_REQUIRED

Gate 2 is ADR-0002 §6 order 5 and is not the WORKFLOW §5 retry ladder.

Decision is REMEDY_REQUIRED (85% <= 94.50% < 95%).
No remedy implemented. Awaiting the single separately orchestrated splitter/fuzzy remedy amendment.

### Gate-2 remedy/rerun
One-time authorized lexical coverage remedy completed.
Rerun command executed with `--lexical-split-remedy`.
Total: 200
Hits: 198
Misses: 2
Coverage ratio: 0.99
Display coverage: 99.00%
Raw CLI decision: CONTINUE
Final post-remedy Gate-2 disposition: CONTINUE

### Stop-and-ask
None.

### Work left undone
None. One-time Gate-2 remedy cycle is complete and Gate 2 has reached its final accepted decision point (CONTINUE).


## DESIGN RESET SUMMARY

### 1. Pre-reset Attempt Ladder and T3 Ceiling
The original slice-4 implementation ladder reached the WORKFLOW §5 T3 ceiling across five attempts:
- Attempt 1 (T1): Failed during Stage-01 build on multi-gender tags for `April`.
- Attempt 2 (T1): Failed on fallback sense collision for `Ahnenpasses` due to Unicode `casefold` mapping `ß` to `ss`.
- Attempt 3 (T2): Failed on canonical-equivalent fallback senses within one record for `Freimaurer`.
- Attempt 4 (T2): Failed on ambiguous upstream `senseid` (`de:grammar`) for `Konjunktion`.
- Attempt 5 (T3): Successfully built and verified real Stage-01 database (`build/gate2/stage01.sqlite`), but failed direct-script CLI execution with `ModuleNotFoundError: No module named 'app'`.

Per WORKFLOW §5, reaching the T3 ceiling required returning the task to design rather than dispatching Attempt 6. The redesigned task started a new ladder at Design-Reset Attempt 1.

### 2. Direct-Script Import Repair
- In `tools/gate2_coverage.py`, added a direct-script `sys.path` bootstrap:
  ```python
  if __package__ in (None, ""):
      repo_root = Path(__file__).resolve().parents[1]
      repo_root_str = str(repo_root)
      if repo_root_str not in sys.path:
          sys.path.insert(0, repo_root_str)
  ```
- This ensures the exact C1 command (`python tools/gate2_coverage.py ...`) executes cleanly from repository root without requiring caller-supplied `PYTHONPATH`, module invocations (`python -m`), or package installation.

### 3. Subprocess Regression Tests
Added two subprocess tests to `tests/test_gate2_coverage.py`:
- `test_gate2_coverage_direct_script_subprocess`: Executes `tools/gate2_coverage.py` via `sys.executable` in a subprocess with `PYTHONPATH` explicitly removed from the environment. Validates exit code 0, JSON structure and fields, atomic misses file creation, and exact deterministic ordering.
- `test_gate2_coverage_subprocess_startup_validation`: Executes `tools/gate2_coverage.py` without arguments and confirms argument validation is reached without `ModuleNotFoundError` or `No module named 'app'`.

### 4. Preserved Stage-01 Asset Verification
The completed Attempt-5 Stage-01 asset was verified and reused (not rebuilt):
- Asset path: `build/gate2/stage01.sqlite`
- Asset SHA-256: `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`
- Asset bytes: `767926272`
- PRAGMA quick_check: `ok`
- Lemma rows: `1118636`
- Sense rows: `480221`
- Sense_meaning rows: `577141`

Carried Stage-01 implementation files verified unchanged:
- `tools/build_dict.py` SHA-256: `6a16ea098d01950bc22402c415a27d70aebeb8f9cb2976795e38cf058b6a8a4f`
- `tests/test_build_dict_stage01.py` SHA-256: `9ddafb293e48248bb51fba1cb1f9749788ff02d137db8588cc988075ba160f28`

### 5. Targeted Test and Gate Numbers
- `tests/test_gate2_coverage.py`: 20 passed
- `tests/test_build_dict_stage01.py`: 46 passed
- `make gate`: 149 passed
  - `ruff check .`: All checks passed
  - `mypy --strict .`: Success: no issues found in 14 source files
  - `pytest -q`: 149 passed
  - `tools/check_agents.py`: AGENTS checks passed: R1 (runtime LLM), R3 (resolver cache key), R7 (lecture coupling)

### 6. Gate-2 Baseline Measurement Evidence
Command executed:
```
python tools/gate2_coverage.py \
  --dictionary build/gate2/stage01.sqlite \
  --words "$GATE2_WORDS_FILE" \
  --misses-out build/gate2/gate2-misses.txt
```

Raw CLI output JSON:
```json
{
  "total": 200,
  "hits": 189,
  "misses": 11,
  "coverage_ratio": 0.945,
  "display_percentage": "94.50%",
  "display_coverage": "94.50%",
  "misses_output": "build/gate2/gate2-misses.txt",
  "misses_output_path": "build/gate2/gate2-misses.txt",
  "decision": "REMEDY_REQUIRED"
}
```

Integer threshold evaluation:
- `100 * hits = 18900`
- `85 * total = 17000`
- `95 * total = 19000`
- `17000 <= 18900 < 19000` -> `REMEDY_REQUIRED`

### 7. Exact Misses List (11 entries)
Preserved in `build/gate2/gate2-misses.txt`:
```
Bis morgen
Bis nächste Woche
Bis Samstag
hundertundeins
der PIN-Code
das Nebenfach
während der Woche
jede Woche
am Wochenende
diese Woche
nächste Woche
```

## ONE-TIME GATE-2 REMEDY / RERUN

### Remedy authorization

- amendment HEAD: `1eab518ba779576b3e9486855c32d8bdfdcfbb1a`
- baseline: 189 / 200 = 94.50%
- baseline Decision: `REMEDY_REQUIRED`
- remedy cycles before rerun: 1
- remedy cycles after rerun: 0

### Remedy contract

- Opt-in `--lexical-split-remedy` flag (default `False`). Without the flag, baseline behavior is strictly preserved.
- Complete-term resolver execution happens first (`resolve_word(term, dictionary, gender=gender_hint)`). If whole-term resolves or derives as compound, it is counted as a hit immediately.
- Lexical splitting occurs only when `--lexical-split-remedy` is enabled and whole-term resolution missed.
- Splitting is performed strictly on Unicode whitespace runs or literal ASCII hyphen runs (`r"(?:\s+|-+)"`).
- Empty fragments are discarded; at least two non-empty lexical pieces are required.
- Each piece is resolved independently through canonical `resolve_word(piece, dictionary)` with no gender hint propagated.
- A lexical piece succeeds iff any returned ref has status `resolved` or `derived_compound`.
- The original textbook entry is counted as a hit iff EVERY lexical piece succeeds.
- No fuzzy matching, stemming, translation, spell-correction, manual lowercasing, or article dropping is performed.
- No modifications were made to `app/resolve.py`, `app/dictionary.py`, or Stage-01 build logic.

### Rerun evidence

Command executed:
```
python tools/gate2_coverage.py \
  --dictionary build/gate2/stage01.sqlite \
  --words "$GATE2_WORDS_FILE" \
  --misses-out build/gate2/gate2-remedy-misses.txt \
  --lexical-split-remedy
```

Artifacts and inputs:
- Stage-01 asset: `build/gate2/stage01.sqlite` (reused preserved asset, not rebuilt)
- Stage-01 SHA-256: `06c98d098691f7cdfff7d87d11d802fee2b73933f4e7e3e9e332a95aca997547`
- Word list SHA-256: `2f2c35ea5ebb19ad4a69c19d5505836bb603453b73086c6902753d5786282924`

Raw CLI output JSON:
```json
{
  "total": 200,
  "hits": 198,
  "misses": 2,
  "coverage_ratio": 0.99,
  "display_percentage": "99.00%",
  "display_coverage": "99.00%",
  "misses_output": "build/gate2/gate2-remedy-misses.txt",
  "misses_output_path": "build/gate2/gate2-remedy-misses.txt",
  "decision": "CONTINUE"
}
```

Integer threshold evaluation:
- `100 * hits = 19800`
- `95 * total = 19000`
- `19800 >= 19000` -> `CONTINUE`

Raw CLI decision: `CONTINUE`
Final post-remedy Gate-2 disposition: `CONTINUE`

Exact complete remedy misses list (2 entries preserved in `build/gate2/gate2-remedy-misses.txt`):
```
hundertundeins
das Nebenfach
```

### Delta

- Baseline hits: 189
- Rerun hits: 198
- Recovered hits: +9 (Bis morgen, Bis nächste Woche, Bis Samstag, der PIN-Code, während der Woche, jede Woche, am Wochenende, diese Woche, nächste Woche)
- Baseline misses: 11
- Rerun misses: 2
- Coverage delta: +4.50% (94.50% -> 99.00%)

### Validation

- Targeted Gate-2 test count: 37 passed (`tests/test_gate2_coverage.py`)
- Stage-01 test count: 46 passed (`tests/test_build_dict_stage01.py`)
- Final make-gate pytest count: 166 passed
- Direct-script subprocess remedy test: PASS (`test_gate2_coverage_direct_script_subprocess_remedy_flag`)
- PYTHONPATH required: no
- Stage-01 rebuild: none (preserved asset reused and verified)
- App modification: none (`app/` untouched)

There is no second Gate-2 remedy cycle.
Gate 2 is ADR-0002 §6 order 5 and is not the WORKFLOW §5 retry ladder.
