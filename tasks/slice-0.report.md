# Slice 0 report

## NARRATIVE

- **Decisions not in the brief:**
  - Excluded `reference` in `pyproject.toml` from `ruff`, `mypy`, and `pytest` discovery because `reference/` contains filed reference artifacts (`reference/smoke_test.py`, `reference/schema.sql`) rather than active gate/application code.
  - Configured `explicit_package_bases = true` and `mypy_path = "."` in `pyproject.toml` under `[tool.mypy]` so `mypy --strict .` resolves `tools.check_agents` without requiring an `__init__.py` inside `tools/`.
  - In `tools/check_agents.py`, implemented AST inspection for both `ast.Import` and `ast.ImportFrom` (including compound module paths such as `from google import genai`) and normalized package names to prevent dependency evasion.
- **Stop-and-ask conditions hit:** None.
- **Problems noticed but not fixed:**
  - `reference/smoke_test.py` is known to be path-broken and contains legacy styling per `STATE.md`; it is preserved intact as a reference artifact and excluded from gate scans.
- **Work left undone:** None. All acceptance criteria (A1–A9) are fully satisfied.
