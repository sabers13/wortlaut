# Slice 2 report

## NARRATIVE

### Empirical spaCy & Model Identity
- spaCy version: `3.8.15`
- Model package: `de_core_news_md`
- Model metadata name: `core_news_md`
- Model version: `3.8.0`

### Empirical Three-Sentence Probe Evidence
```text
SPACY_VERSION: 3.8.15
MODEL_PACKAGE: de_core_news_md
MODEL_NAME: core_news_md
MODEL_VERSION: 3.8.0

Ich rufe dich morgen an.
Ich          PRON   dep=sb         head=rufe
rufe         VERB   dep=ROOT       head=rufe
dich         PRON   dep=oa         head=rufe
morgen       ADV    dep=mo         head=rufe
an           ADP    dep=svp        head=rufe
.            PUNCT  dep=punct      head=rufe

Der Zug kommt um acht an.
Der          DET    dep=nk         head=Zug
Zug          NOUN   dep=sb         head=kommt
kommt        VERB   dep=ROOT       head=kommt
um           ADP    dep=mo         head=kommt
acht         NUM    dep=nk         head=um
an           ADP    dep=svp        head=kommt
.            PUNCT  dep=punct      head=kommt

Ich rufe laut.
Ich          PRON   dep=sb         head=rufe
rufe         VERB   dep=ROOT       head=rufe
laut         ADV    dep=mo         head=rufe
.            PUNCT  dep=punct      head=rufe
```

### Separable-Particle Dependency Label
- Exact common dependency label observed for `an` in both separable sentences: `svp`
- Head relationship verified:
  - `Ich rufe dich morgen an.`: `an` (dep `svp`) -> head `rufe` (finite verb)
  - `Der Zug kommt um acht an.`: `an` (dep `svp`) -> head `kommt` (finite verb)
  - `Ich rufe laut.`: control sentence with no separable particle (`rufe` dep `ROOT`, head `rufe`)

### Resolver Constant Status
- `SVP_DEP` was already correctly defined as `"svp"` in `app/resolve.py`. No modification to `app/resolve.py` was necessary.

### Real-Model CASES Test Locking
- Created `tests/test_resolve_spacy.py` executing the real `de_core_news_md` pipeline.
- Locked exactly the five ADR-0001 §13 CASES in exact order:
  1. `("Ich rufe dich morgen an.", "rufe", "anrufen")`
  2. `("Der Zug kommt um acht an.", "kommt", "ankommen")`
  3. `("Ich rufe dich morgen an.", "an", "anrufen")`
  4. `("Ich rufe laut.", "rufe", "rufen")`
  5. `("Sie interessiert sich für Musik.", "interessiert", "interessieren")`
- All 5 real-model test cases pass through the existing slice-1 resolver seam without creating a secondary resolver or altering resolution logic.

### Governance Checklist
- Stop-and-ask conditions encountered: `None`
- Problems noticed but deliberately not fixed: `None`
- Work left undone: `None`
