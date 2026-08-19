# ADR-0001 — Flashcard subsystem: core design

**Status:** Accepted (design session, 2026-08-18). Filed verbatim on 2026-08-19
from that session's brief plus its §17 plugin amendment. Do not edit the original
text below; changes happen in later ADRs.

**Partially superseded.** The following parts are revised by later ADRs; on
conflict, the later ADR wins:

| Superseded below | By | Replacement |
|---|---|---|
| D2 — resolution at ingest, persisted token index; highlight does zero NLP | ADR-0002 | resolution at capture inside the standalone service; the ingest token index is abandoned and capture runs the resolver locally |
| D7 — example stored as `(lesson_id, char_span)` pointer | ADR-0002 | sentence **text** stored at capture; provenance fields kept as metadata only |
| §5 Behaviour: lecture deck auto-create/delete tied to host ingest/deletion; `note.lesson_id` as the rendering pointer | ADR-0002 | no host-ingest lifecycle exists: highlight commit finds/creates standalone lecture-deck membership from the submitted lesson/deck context, standalone decks survive host deletion, and cards render the copied `sentence_text`; lesson/span fields are optional provenance only |
| §6 Endpoint: bare `/lookup`, plus the statement that highlight/manual differ only by candidate generation while using the old host-shaped API | ADR-0002 | D13's shared pipeline remains, but standalone API routes live under `/vocab`; highlight uses the two-stage D11 flow (`/vocab/highlight` candidates + capture context, picker, then `/vocab/cards` commit), while manual lookup uses `/vocab/lookup` and the same picker/commit stage |
| §10 `resolve.py` described as spaCy-at-ingest only; endpoint table paths and the old `/highlight`→`/cards` boundary | ADR-0002 | `app/resolve.py` runs locally at capture/manual resolution and is also imported by build stage 02 per D3; **every** standalone endpoint receives the `/vocab` prefix, `/vocab/highlight` is non-mutating candidate/context generation, and `/vocab/cards` is the post-picker commit boundary. ADR-0003 separately controls the `/vocab/review` request body and `/vocab/decks` response body |
| §11 Example ranking: `known = deck lemmas ∪ completed-lecture lemmas` | ADR-0002 | ranking/scoring stays unchanged, but host-derived lemmas are optional by-value input only: `known = deck lemmas ∪ known_lemmas` when `known_lemmas` is supplied; no live host fetch is allowed; when absent, `known = deck lemmas` |
| §14 deferred `lesson_token` optimisation | ADR-0002 | `lesson_token` is dropped, not deferred; no host token index exists in the standalone architecture |
| §15 `load_lesson_doc()` stub as an implementation defect | ADR-0002 | no live lesson loader exists or is required; capture supplies sentence/context by value and commit reuses that submitted context |
| §16 copyright/consistency paragraph: source text never persisted, D7 pointer rendering, CSV excludes lecture text | ADR-0002 | the selected sentence is intentionally copied into `note.example_de`; optional provenance does not render; exports may carry the stored sentence text as part of the user's local card data |
| §17 amendment header; D15–D17; §17.2 decomposition; §17.3 decomposition-specific table ownership; §17.4 `HostContext`; §17.5 integration + `lesson_token`; §17.8 rejection of a two-component split and of a separate HTTP service; §17.9 in-process-first sequencing | ADR-0002 | fully standalone service is the accepted v1 architecture: own container/DB, HTTP + compose integration, app factory, capture-time resolution, no `HostContext`, no shared `german-vocab-core`, no `lesson_token`; the earlier in-process/service-rejection path is superseded rather than deferred |
| §10 `POST /review` rating input; `GET /decks` due-count-only response | ADR-0003 | on ADR-0002 D25's prefix, `POST /vocab/review` accepts confidence 1–5 only and server maps/logs FSRS rating; `GET /vocab/decks` also returns mastery |
| §11 four-grade rating UI | ADR-0003 | five-level confidence UI mapped onto FSRS; FSRS itself (D6) unchanged |

Everything else — D1, D3–D6, D8–D14 (D3 remains the one-resolver invariant;
D23 only removes the obsolete host-ingest consumer; D11 picker/multi-select, D12
many-to-many deck membership, and D13 manual-entry sharing remain), D18–D19,
§17.7 CSV import, the unrelated §17.8 rejected generic-note/configurable-template/
plugin-registry alternatives, the gates (§13), dictionary build and distribution
(§12), card spec (§11 except the rating UI, D7-derived example-pointer wording,
and the Example ranking `known` formula superseded above),
and export format/behaviour (§7) — stands as written.

---

# ADR — Flashcard subsystem (Anki-style, zero-runtime-LLM, local-first)

| | |
|---|---|
| **Status** | Accepted. Design closed; two gates open before implementation |
| **Supersedes** | first-pass brief from the same session |
| **Scope** | Word capture (highlight + manual) → card creation → scheduled review → Anki export |
| **Suggested path** | `decisions/ADR-00X-flashcards.md` |
| **Deployment** | Local-only. Runs on the user's PC, Docker first. No multi-user server |
| **Code delivered** | `app/{resolve,dictionary,examples,render,deck,api}.py`, `schema.sql`, `smoke_test.py` |
| **Verified** | Smoke test passes: ladder, three templates, FSRS, dupe detection, contribution write |
| **Unverified** | `resolve.py` — see Gate 1 |

---

## 1. Problem

A user reads an ingested lecture. They highlight a German word, or type one in manually. The system produces a flashcard with the German side fully populated — headword, article, inflectional forms, IPA, audio, example sentence — plus an English gloss, without manual front/back authoring. Cards group by lecture, are editable, and export to Anki.

## 2. Deployment context

Everything runs locally on the user's machine, containerised. This removes an entire class of problems an earlier draft treated as open: renderer duplication across client/server, FSRS parameter agreement, a sync layer, auth, bundled-asset size budgets, and audio cache eviction. All are non-issues in a single-process local app.

One security note survives: bind `127.0.0.1:8000:8000`, **not** `8000:8000`. Docker's default publish rule traverses most host firewalls and would expose an unauthenticated deck API to the LAN.

## 3. Decision summary

| # | Decision | Rationale |
|---|---|---|
| D1 | **No LLM at runtime, in any code path** | Offline operation; exact-match golden tests; no API key in the app; bounded latency. `anthropic` must not appear in `app/` requirements — that absence is the test |
| D2 | Lemma resolution at **ingest**, persisted as a token index; highlight is an interval lookup | Reuses the spaCy pass already in ingest; highlight does zero NLP |
| D3 | **One** resolver module shared by ingest, Tatoeba indexing, highlight, and manual entry | Divergence silently breaks separable-verb matching |
| D4 | Dictionary is a **static SQLite asset**, built offline, versioned, distributed via GitHub releases | Removes the dictionary from the runtime dependency graph |
| D5 | **note/card split** (Anki model) from v1, though v1 ships one template | Retrofitting after review history exists is a painful migration |
| D6 | **FSRS**, not SM-2; full append-only `review_log` | Current Anki algorithm; the log enables later per-user parameter optimisation and cannot be reconstructed retroactively |
| D7 | Lecture example sentences stored as **`(lesson_id, char_span)` pointers**, rendered from the local lecture copy | Preserves "no source content persisted" from the copyright ADR |
| D8 | Rendered front/back **never stored**; structured fields + nullable overrides | New fields update all existing cards at render time, no migration |
| D9 | Unresolvable words still **create a complete card**, `status='needs_gloss'` | The German side carries the card; user types English during review |
| D10 | User-filled glosses **contributable**; ≥3 agreeing votes promote at next dictionary build | Makes zero-LLM sustainable rather than merely cheap |
| **D11** | **Candidate picker with multi-select** on capture; candidates generated parser-independently | §4. Turns a hard parser dependency into a soft one, and multi-select is pedagogically valuable in German |
| **D12** | **Decks are many-to-many with notes**, keyed by lecture | A word met in two lectures is one note with one FSRS state, appearing in both decks |
| **D13** | **Manual word entry** is a first-class path sharing the capture pipeline with highlight | Only candidate generation differs |
| **D14** | **Anki export = tab-separated CSV**, per deck or whole collection | Requested. Scheduling state does not survive CSV — §7 |

## 4. Candidate generation and the picker (D11)

### The parser dependency, and how it is neutralised

German separable verbs split across a sentence:

```
anrufen ("to phone")   →   Ich rufe dich morgen an.
rufen   ("to shout")   →   Ich rufe laut.
```

The original resolver decided between them by reading spaCy's dependency label (`svp`). If that string is wrong, the code silently returns `rufen` for both — no error — and the Tatoeba index inherits the same fault, so lookups still succeed and nothing surfaces the problem.

**Revised approach: generate candidates by surface scan, filter by the dictionary.**

```python
PARTICLES = {"an","auf","aus","ab","ein","mit","vor","zu","nach",
             "um","bei","los","weg","zurück","fest","frei","statt"}

def candidates(tok, sent):
    out = [Ref(tok.lemma_, tok.pos_)]
    if tok.pos_ in ("VERB", "AUX"):
        for other in sent:
            if other.text.lower() in PARTICLES and other.i != tok.i:
                out.append(Ref(other.text.lower() + tok.lemma_, "VERB"))
    return [c for c in out if dictionary_has(c)]
```

The dictionary filter kills nonsense — `zurufen` exists, `mitrufen` does not, so it is dropped. This finds `anrufen` whether or not the dep label is correct.

The dep label still matters for **default ordering** and for the Tatoeba index, so Gate 1 stands. But a mistake there now degrades to "the user picks from two options" instead of "every card is wrong."

### Multi-select

`note` uniqueness is `(user_id, lemma_text, pos, sense_id)` — a distinct `sense_id` is a distinct note, so multi-select needs no schema change.

Three cases where it earns its place:

**Homographs** — genuinely different words:
```
die Bank    ☑ bank (financial institution)
            ☐ bench (seating)
```

**Senses** — one word, several meanings:
```
die Karte   ☑ card
            ☑ map
            ☐ ticket
```

**Compound decomposition** — the strongest case, and specific to German:
```
Krankenversicherungskarte
            ☑ Krankenversicherungskarte
            ☐ die Versicherung — insurance
            ☑ die Karte        — card
```

Learning the parts teaches decoding of the *next* compound encountered, which transfers. The splitter already produces this list.

**Constraints:** default-check only the top candidate — three checked boxes turns "add a word" into "add three cards" and decks bloat fast. Cap senses at three (`_build()` already does `LIMIT 3`); Wiktionary entries for common words carry a dozen, mostly archaic or domain-specific.

The picker is also the natural home for the edit-before-adding flow.

## 5. Decks (D12)

### Model

A note is global to the user; deck membership is many-to-many. Reviewing `Haus` from the Lektion 3 deck advances the same card that appears in Lektion 7 — one FSRS state, one review history.

```sql
CREATE TABLE deck (
  id          INTEGER PRIMARY KEY,
  user_id     INTEGER NOT NULL,
  name        TEXT NOT NULL,
  lesson_id   TEXT,               -- NULL for manual/custom decks
  kind        TEXT NOT NULL,      -- 'lecture' | 'manual' | 'custom'
  created_at  TEXT NOT NULL,
  UNIQUE(user_id, lesson_id),
  UNIQUE(user_id, name)
);

CREATE TABLE note_deck (
  note_id  INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  deck_id  INTEGER NOT NULL REFERENCES deck(id) ON DELETE CASCADE,
  added_at TEXT NOT NULL,
  PRIMARY KEY (note_id, deck_id)
) WITHOUT ROWID;
```

**Rejected alternative:** deck-scoped uniqueness, i.e. duplicating the note per lecture. It produces two independent FSRS states for one word, so the user reviews `Haus` twice on the same day and neither review informs the other. Global note plus membership link is correct.

### Behaviour

- A lecture deck is auto-created at ingest, named from the lecture.
- Highlight capture inserts `note_deck(note, lecture_deck)`.
- Meeting an existing word in a **new** lecture inserts a membership row only. The picker reports *"already in your deck (Lektion 3) — add to Lektion 7 as well?"*
- Manual entry defaults to a `kind='manual'` deck ("My words"), with an optional deck selector.
- Deleting a lecture deletes its deck; notes survive if they belong to another deck, otherwise they move to an "Orphaned" deck. **Never cascade-delete a note that has review history.**
- Review runs per-deck or across all decks. Because state is shared, "review all" deduplicates naturally.

### `note.lesson_id` keeps its old meaning

It remains the **provenance pointer** for the example sentence (D7) — where the word was *first* captured. It is not the deck key. Deck membership lives in `note_deck`. Keeping these separate matters: a note can belong to five decks but has exactly one first-encounter context, and that context is what renders on the card.

## 6. Manual entry (D13)

### Shared pipeline

Highlight and manual entry differ only in how candidates are produced:

```
highlight  → token + sentence context → candidates() → picker → note
manual     → bare string              → candidates() → picker → note
```

Everything downstream — ladder, picker, note creation, deck assignment, rendering — is identical.

### Bare-string handling

Manual entry has no sentence, so:

- **No POS from context.** The ladder tries all plausible POS values and the picker disambiguates. `groß` returns ADJ only; `Bank` returns two noun candidates by gender.
- **No determiner, so no gender hint.** Gender comes from the dictionary row instead, which is where it should come from anyway.
- **No separable-verb reconstruction from context** — but users type infinitives (`anrufen`), which is the easy case. Inflected input (`rief an`, `ruft`) is caught by ladder step 2 (`surface_form`). Confirm stage 01 populates multi-word separable surface forms.

### Consequence: the always-has-an-example property breaks

Previously every card had at least the lecture sentence, because that is why the word was highlighted. Manually added words have no lecture context, fall through to Tatoeba, and rare words may have neither.

Acceptable — the grammar fields carry the card — but `render.back()` must handle an empty example list cleanly and the UI must not imply something is missing. The code tolerates `examples=[]`; add a test, since manual entry makes that path reachable.

### Endpoint

```
POST /lookup   {"text": "anrufen", "deck_id": 3}
  → {"candidates": [ {ref, grammar, senses, examples, status}, ... ]}
```

Same response shape as `/highlight` minus `lesson_ref`. One picker component serves both paths.

Worth adding: lookup-as-you-type against `lemma` and `surface_form` with a `LIMIT 10` prefix query. Cheap on indexed local SQLite, and it prevents typo-driven `needs_gloss` cards — a card for a word that does not exist is the worst kind.

## 7. Anki export (D14)

### Format

Tab-separated, not comma. German glosses contain commas constantly (`big, large, tall`) and quoting is a reliable source of broken imports. Anki reads file-header directives:

```
#separator:tab
#html:true
#notetype:German Vocab
#deck:German::Lektion 4
#columns:Front	Back	Grammar	Example	IPA	Tags
```

Then one note per line. Embedded newlines must become `<br>` (hence `#html:true`); a literal newline terminates the record and corrupts everything after it. Sanitise tabs and newlines out of every field before writing.

### Structured, not two-field

Exporting `Front | Back` discards everything that makes these cards worth having. Export structured fields and let the user's Anki note type lay them out:

| Column | Content |
|---|---|
| Front | `das Haus` / `anrufen` |
| Back | primary gloss |
| Grammar | `Substantiv · Neutrum · die Häuser` |
| Example | `Ruf mich morgen an!<br>Call me tomorrow!` |
| IPA | `haʊ̯s` |
| Tags | `lektion04 noun A1` |

Ship a matching note-type template, or document the field order plainly in the export dialog.

### Known limitation: scheduling does not survive

Anki's CSV import creates **new** cards. FSRS stability, difficulty, due date and review history are lost — the user restarts from zero in Anki. This is a property of the format, not a bug. State it in one line in the export dialog.

If preserving scheduling matters, that is `.apkg` via `genanki`, which carries scheduling and media. Keep as a follow-up (§14) — roughly 50 lines, and it makes "Anki-style" literal rather than approximate.

### Scope and media

- Export one deck, several decks, or everything.
- Audio: reference `[sound:hash.ogg]` in a field and emit the referenced `.ogg` files into a sibling folder for manual `collection.media` placement. CSV cannot bundle media; `.apkg` can. Another point for the genanki follow-up.
- Include `needs_gloss` cards with an empty Back, flagged by tag — silently dropping them loses user work.

## 8. Data sources

| Source | Use | License | Obligation |
|---|---|---|---|
| Wiktionary EN via wiktextract/kaikki | glosses, structured grammar | CC BY-SA 3.0 | Attribute; the derived DB file stays CC BY-SA. Does **not** infect app code — bundling is aggregation, not derivation |
| Wiktionary DE via wiktextract | `{{Beispiele}}` — better coverage than EN, but German-only and often literary register | CC BY-SA 3.0 | as above |
| Tatoeba | primary examples, DE↔EN linked | CC BY 2.0 (FR) | attribution only |
| spaCy `de_core_news_md` | lemma/POS/morph/dep | MIT | — |
| Piper + espeak-ng | TTS + IPA G2P fallback | MIT | — |
| py-fsrs | scheduling | MIT | — |
| genanki | `.apkg` export (follow-up) | MIT | — |
| Frequency list | derived from Tatoeba counts — §14 | — | sidesteps DeReWo/Leipzig licensing entirely |

**Verify every license at the download page before shipping.** Dump licensing gets revised.

Attribution is tracked **per row** (`example.source`, `example.source_ref`, `sense.source`, `sense.license`), not per app. `source_ref` also enables diffing against newer dumps instead of rebuilding.

## 9. Rejected

| Rejected | Reason |
|---|---|
| MT API for headwords | Worse than a dictionary on isolated words — collapses senses, drops gender |
| Runtime LLM gloss fallback, even cached | The key still ships, the failure path still exists, and misses arrive forever since German compounding is generative. "Rare" ≠ "removed" |
| LLM contextual sense ranking | A tap is cheaper than a call, and the user is better at it than a small model |
| Live Wiktionary API at runtime | Returns wiki markup, not fields; re-parsing per lookup; rate-limited; makes a local app need the internet |
| dict.cc, Leo, Linguee | No API; ToS prohibits scraping; HTML changes without notice |
| **Leipzig/Wortschatz sentence corpus** | CC BY-NC — blocks any future paid tier. The sentences are good, which is why it is a trap |
| OpenSubtitles/OPUS | Register wrong: fragmentary dialogue, profanity, alignment noise |
| **Coqui XTTS-v2** | CPML, non-commercial only. Coqui shut down in 2024, no relicensing path. Remove from the TTS candidate list now, not after building around its voice |
| Deck-scoped note uniqueness | Duplicate FSRS states for one word across lectures — §5 |
| Comma-separated Anki export | German glosses contain commas; quoting breaks imports |
| Baking the dictionary into the Docker image | Couples dictionary versions to image versions; one corrected gloss would need a full release |

## 10. Architecture

```
app/
  resolve.py      Ref[] <- token | string        spaCy only (ingest), no I/O
  dictionary.py   Entry <- Ref                   SQLite + subprocess(espeak) only
  examples.py     ranking                        pure function
  render.py       Face  <- (Entry, template)     pure function
  deck.py         note/card/deck writes, FSRS    user DB
  export.py       CSV (+ apkg later)             NEW
  api.py          endpoints
```

Dependency direction is one-way: `api → deck → render → dictionary → resolve`. Nothing below `deck` touches user state, which is what makes `render` and `dictionary` exact-match testable.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/highlight` | Candidates from a lecture span, with `lesson_ref` |
| POST | `/lookup` | Candidates from a bare string (manual entry) |
| GET | `/lookup/suggest` | Prefix autocomplete, `LIMIT 10` |
| POST | `/cards` | Commit selected candidates + deck membership. Idempotent |
| GET | `/decks` | List with due counts |
| GET | `/review/next` | Due cards, optionally deck-filtered |
| POST | `/review` | Rating 1–4, returns next due |
| POST | `/gloss` | Fill `needs_gloss`, optional contribute |
| POST | `/export` | CSV per deck or all |

There is no `/gloss/generate`. That absence is the design.

### Resolution ladder

1. **Exact** `(lemma, pos[, gender])` — gender disambiguates `der See`/`die See`, `die Bank`
2. **Surface form** — catches lemmatisation misses and inflected manual input
3. **Compound split** — deterministic longest-known-head with Fugenelemente (`s, es, n, en, er, e, ns`). Compound gender equals head gender; exceptionless, hardcoded
4. **Stub** — `status='needs_gloss'`, card created anyway

Verified: `Krankenversicherungskarte → ['kranken','versicherung','karte']`, gender `die` inherited from `Karte`.

## 11. Card specification

Five field groups:

| Group | Contents | Source |
|---|---|---|
| Pronunciation | IPA + audio | Wiktionary IPA → espeak-ng fallback; Piper audio |
| Grammar | article/gender, plural, genitive, verb principal parts, aux, separability, governed case, gradation | Wiktionary structured |
| Gloss | English sense(s), max 3 | Wiktionary → user → contributions |
| Examples | lecture pointer + Tatoeba, ranked | pointer / shipped corpus |
| Scheduling | FSRS state | own |

`das Haus → house` is an inadequate card. The grammar group is the point.

### Templates

- **recognition** (v1) — DE front → meaning back. Trains reading.
- **production** (v2) — meaning front → DE back. Trains speaking. Omitting it indefinitely produces learners who read but cannot speak.
- **gender** (v2, nouns) — `___ Haus` → `das`. Separated because gender is memorised independently of meaning; bundled, the learner passes on "house" while staying fuzzy on the article.

Each template is its own `card` row with its own FSRS state, sharing one `note`. `TEMPLATES` in `deck.py` is the single line to change.

### UI rules

- **IPA on the front**, not the back — same-glance orthography→sound mapping. On the back it is decoration.
- **Audio does not autoplay on the front** — that turns recall into recognition and nothing is retrieved. Tap to play; autoplay on reveal.
- **Progressive disclosure** — essentials visible, rest behind `⌄ more`. Heavy backs cause session abandonment, which kills an SRS app faster than any accuracy problem.
- `needs_gloss` cards **enter scheduling normally**. A complete German side with an empty English side is still reviewable; only production is blocked. Do not quarantine.
- Manual cards may have **no example at all**. Render cleanly; do not imply failure.

### Example ranking

Deterministic scoring: length toward 9 tokens; penalise unknown lemmas (i+1), rare unknowns harder, proper nouns, and untranslated; small bonus for questions. `known` = deck lemmas ∪ completed-lecture lemmas — **personalised without inference**, and better than a small model because the model does not have that set.

Priority: lecture sentence > Tatoeba > `de.wiktionary` Beispiele (untranslated, marked) > none.

Freeze the primary at creation for recall stability; re-rank only on "show another example".

## 12. Dictionary build and distribution

Five offline stages, run by the maintainer:

| Stage | Input | Output | Time |
|---|---|---|---|
| 01 `parse_wiktextract` | kaikki JSONL (EN + DE) | `lemma`, `sense`, `surface_form` | 5–15 min |
| 02 `index_tatoeba` | Tatoeba TSVs | `example`, `example_lemma`, `freq` | 10–40 min (`nlp.pipe(n_process=8)`) |
| 03 `find_gaps` | freq list + ladder | `gaps.jsonl` | 2–5 min |
| 04 `gloss_gaps_batch` | `gaps.jsonl` | glossed rows, `source='llm_generated_v1'` | ≤24h wall-clock, ~0 compute |
| 05 `pack` | all | `dictionary_vN.sqlite` (~130 MB) | 5–10 min |

**Stage 02 must import the resolver, not reimplement it** (D3).

**Stage 04** is the only place an API key exists anywhere in the project. It runs on the maintainer's machine, invoked by hand, once. Structured output matching the schema, spot-checked by hand, rows marked `source='llm_generated_v1'` so `DELETE WHERE source='llm_generated_v1'` reverses it cleanly. Generated rows must never be indistinguishable from Wiktionary rows.

### Checkpointing — do this upfront

A 40-minute build is fine once and miserable on the fifth run. Without checkpoints, people hand-patch the SQLite file and the asset stops being reproducible.

```python
def checkpoint(name, fn, *args, force=False):
    p = Path(f"build/cache/{name}.parquet")
    if p.exists() and not force:
        return pd.read_parquet(p)
    df = fn(*args); p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p); return df
```

**One hard rule: stage 02's cache key must include a hash of `resolve.py`.** Otherwise fixing Gate 1 and rebuilding silently reuses an index built with the broken separable-verb logic — the same bug, resurrected by your own caching.

```python
resolver_hash = hashlib.sha256(Path("app/resolve.py").read_bytes()).hexdigest()[:8]
checkpoint(f"tatoeba_index_{resolver_hash}", index_tatoeba)
```

### Distribution — RESOLVED

Built by the maintainer, published as a **GitHub release asset**, downloaded by the container into a volume on first run.

- **Never overwrite a published asset.** Semantic filenames: `dictionary_v1.sqlite`, `dictionary_v2.sqlite`
- Publish a small `latest.json` the container reads to learn what to fetch
- Publish a **SHA-256 checksum**; verify after download. A truncated 130 MB download produces a corrupt SQLite file and an incomprehensible failure otherwise
- Ship `LICENSE` and `ATTRIBUTION` alongside (CC BY-SA for Wiktionary-derived rows, CC BY for Tatoeba). The file is a Wiktionary derivative and cannot be claimed as proprietary. Application code is unaffected

Users building it themselves is not viable — multi-GB dumps and a 40-minute spaCy pass.

### Volume layout

```yaml
volumes:
  - dict:/app/assets       # read-only after bootstrap, disposable
  - userdata:/app/data     # notes, cards, review_log, audio — sacred
  - ./lessons:/app/uploads # user's own PDFs, bind mount
```

Design against one failure: a user updating the app and losing their deck. Dictionary and deck live in different volumes so the former can be destroyed and refetched without touching the latter.

Download spaCy and the Piper voice at **image build time**, not first run — otherwise first launch silently pulls ~100 MB and looks broken.

## 13. Gates — resolve before implementation

Deferring these costs rework of an expensive artifact or of the design itself, not just a fix.

### Gate 1 — Verify the spaCy dependency labels · 20 min

`resolve.py` assumes the label linking a separable particle to its verb is `svp`. If that string is wrong, the resolver silently returns `rufen` for `anrufen`, **and stage 02 bakes the same fault into a 40-minute index**, where it is self-consistent and therefore invisible.

```python
import spacy
nlp = spacy.load("de_core_news_md")
for s in ["Ich rufe dich morgen an.", "Der Zug kommt um acht an.", "Ich rufe laut."]:
    print(f"\n{s}")
    for t in nlp(s):
        print(f"  {t.text:12} {t.pos_:6} dep={t.dep_:10} head={t.head.text}")
```

Read the `dep=` value for `an`. Put it in `SVP_DEP`. The third sentence is the control — if plain `rufen` becomes separable, that is the opposite bug.

Lock it in:

```python
CASES = [
    ("Ich rufe dich morgen an.",         "rufe",         "anrufen"),
    ("Der Zug kommt um acht an.",        "kommt",        "ankommen"),
    ("Ich rufe dich morgen an.",         "an",           "anrufen"),
    ("Ich rufe laut.",                   "rufe",         "rufen"),
    ("Sie interessiert sich für Musik.", "interessiert", "interessieren"),
]
```

D11's candidate generation reduces the blast radius, but the label still determines default ordering and index correctness. Cheapest irreversibility in the project.

### Gate 2 — Measure dictionary coverage · 30 min after stage 01

**This does not require a finished dictionary.** Whether a word is found is decided entirely by stage 01 plus the splitter. Stages 02–05 add examples, gap glosses and packaging — none of them change hit rate. So this is measurable ~30 minutes into the build, not a day.

```
01  parse wiktextract  →  lemma + sense    ← ENOUGH TO MEASURE
02  index Tatoeba      →  examples            (does not affect hit rate)
03  find gaps          →  gap list            (does not affect hit rate)
04  batch gloss        →  fill gaps           (does not affect hit rate)
05  pack               →  final asset         (does not affect hit rate)
```

**Procedure**

1. Take 200–300 words from the vocabulary index at the back of the real textbook, one unit.
2. Run stage 01 only.
3. Loop:

```python
misses = [w for w in words
          if DICT.lookup(parse(w)).status == "needs_gloss"]
print(f"{len(words)-len(misses)}/{len(words)} = "
      f"{(len(words)-len(misses))/len(words):.0%}")
print("MISSES:", misses)
```

**Interpretation**

| Result | User experience | Consequence |
|---|---|---|
| ≥95% | types a gloss ~1 word in 20 | build as designed |
| 85–95% | ~1 in 10 | loosen splitter `MIN_PART` to 2, add fuzzy surface matching |
| <85% | types constantly | **the design is wrong** — needs a second source or a different fallback |

The bottom row is not a bug fix. It means automatic card creation does not work on this textbook, and finding that out after stages 02–05 and Docker packaging throws away a week.

**Free byproduct:** the `MISSES` list *is* stage 03's input. This measurement is not a detour.

### Gate 3 — Distribution · RESOLVED

GitHub release asset, volume download, checksummed. §12.

## 14. Deferred to implementation

None of these invalidate prior work; each is additive.

| Item | Note |
|---|---|
| `lesson_token` table replacing `load_lesson_doc()` | Now pure optimisation — spaCy is resident for ingest anyway, so the naive path only wastes CPU. Additive table, no migration |
| `FREQ` from Tatoeba counts | Falls out of stage 02 free: count lemmas while indexing, rank by count. Zero extra passes, zero licensing question, and better matched to the corpus being ranked than a news-derived list. Absent, ranking degrades to length-only |
| Compound gloss trimming | `Karte` = `card; map; ticket` currently concatenates whole, producing `sick insurance card; map; ticket`. Fix: `re.split(r"[;,]", g)[0]` per component. Then demote the composed gloss in the UI and promote the decomposition — the split is reliably correct, the gloss never will be |
| espeak-ng | `apt install espeak-ng` in the Dockerfile. Add a startup check so it fails loudly rather than emitting blank IPA. Prefer Wiktionary IPA when present — espeak applies German rules mechanically and mangles loanwords (`Restaurant`) |
| Derived card state | Replaying `review_log` to reconstruct FSRS state. Was a correctness gate for multi-device sync; for single-user it is a nice property enabling clean undo and parameter re-optimisation. `review_log` is already append-only, so the option stays open free. Do not build now |
| `.apkg` export via genanki | ~50 lines. Carries scheduling *and* media, which CSV cannot |
| Contribution promotion job | At each dictionary build. Normalised string overlap suffices for "to call" vs "to phone, to call"; semantic similarity is unnecessary at this scale |

## 15. Known defects in delivered code

| Item | Detail |
|---|---|
| `resolve.py` unverified | Gate 1 |
| Compound gloss concatenation | §14 |
| `load_lesson_doc()` stub | §14 |
| `FREQ` empty | §14 |
| `render.back()` with `examples=[]` | Tolerated but untested — reachable via manual entry (§6). Add a test |
| `surface_form` and multi-word separable forms | Confirm stage 01 populates `rief an`, `ruft an`; inflected manual entry depends on it |
| `deck` / `note_deck` tables | Not in delivered `schema.sql` — added by D12, §5 |
| `export.py` | Does not exist |
| `tools/build_dict.py` | Does not exist. Own session, own ADR |

## 16. Consistency with existing ADRs

- **Copyright ADR** — flashcards are derived items (lemmas, grammar tags, glosses). The one field touching source content is the lecture example sentence, resolved by D7 (pointer, not copy). No shared corpus of source text. CSV export emits user-derived cards, not lecture text.
- **Mostly-code principle** — runtime inference count is zero, not "minimal". Strengthens rather than bends the constraint.
- **Fable-as-specialist** — stage 04's one-time gap-gloss pass is a build-time artifact-producing job, matching the established pattern. It does not become a runtime dependency.


---

# ADR amendment — vocab plugin decomposition

**Amends:** `ADR-00X-flashcards.md` (file as §17, or as a standalone ADR if the split gets its own phase)
**Status:** Accepted as a target architecture. Deferrable — v1 may ship in-process
**Depends on:** `lesson_token` table (promoted from deferred to prerequisite; see §17.5)

---

## 17.1 Decisions added

| # | Decision | Rationale |
|---|---|---|
| **D15** | **Three components**, not two: `german-vocab-core`, `lecture-engine`, `flashcards`. Both consumers depend on core; neither depends on the other | The resolver is shared by ingest and capture (D3). A two-way split would force copying it, breaking D3 and reintroducing the divergence Gate 1 exists to prevent |
| **D16** | Coupling is a **three-method `HostContext` protocol**. It does not grow without an ADR entry | The boundary erodes one convenience method at a time; the guard has to be procedural |
| **D17** | Ship as an **in-process Python package**, not a container or service | Delivers the actual goals — independent development, explicit contract, reusability — without a network hop, second process, or version matrix. Protocol-shaped contracts make later promotion to a service mechanical |
| **D18** | **No generic/non-German note types.** No configurable note types, cloze, or custom templates | The German specialisation is the product. A general flashcard app competes with Anki on Anki's terms and loses; effort would come out of features nobody else has |
| **D19** | **CSV import is German word-list bulk capture**, one lemma per line — not front/back pairs | Follows from D18. Import runs each line through the same ladder and picker as manual entry |

## 17.2 Decomposition

```
        german-vocab-core
     (resolver, dictionary, ladder, IPA)
              ↑          ↑
              │          │
    lecture-engine    flashcards
    (ingest, parse,   (notes, cards,
     reader, TTS)      FSRS, import/export)
```

Clean DAG. `resolve.py` lives in exactly one place with both consumers importing it, satisfying D3 structurally rather than by convention.

Side benefit: the CC BY-SA obligation attaches to the dictionary asset, which now lives with a component that can be open-sourced cleanly, leaving the lecture engine separate.

## 17.3 Table ownership

Separate SQLite files. **No foreign keys across component boundaries.**

| Component | Owns |
|---|---|
| core | `dictionary_vN.sqlite` — read-only asset |
| lecture-engine | lessons, `lesson_token`, audio cache |
| flashcards | `deck`, `note_deck`, `note`, `card`, `review_log`, `gloss_contribution` |

**The test:** if a foreign key from `note` into lecture-engine tables ever seems necessary, the boundary is wrong. This is why D7's pointer is stored as **plain values** (`lesson_id` TEXT, `char_start`, `char_end`) rather than a reference — the flashcard DB holds strings and integers, and resolving them is a question it asks the host.

## 17.4 The two contracts

### What flashcards exposes

Six operations, roughly: get candidates for a word; create notes from selected candidates; ensure a deck exists; fetch due cards; submit a review; import/export CSV. That is the entire public surface.

### What the host must provide

Three callbacks. This is the complete real coupling:

| Method | Why it exists |
|---|---|
| `sentence_at(lesson_id, span) -> str \| None` | D7 stores a pointer, so flashcards cannot render the lecture example without asking the host for the text |
| `known_lemmas() -> set[str]` | Powers i+1 example ranking (§11). Only the lecture engine knows what has been completed |
| `tts(text) -> Path` | Reuses the Piper pipeline instead of duplicating it |

**Growth is the failure mode.** Someone wants the lecture title on a deck screen, so a fourth method appears; then a fifth; six months later the plugin cannot be built without the lecture engine. Guard: `HostContext` does not grow without an ADR entry. When a new method seems necessary, the usual correct answer is that the data should have been passed at note-creation time and stored, not fetched live.

## 17.5 Integration layers

| Layer | Mechanism |
|---|---|
| Code | Separate repo, own version, own tests. Main app declares a dependency |
| Wiring | Host constructs the service once at startup with `(dictionary_path, db_path, host_context)`. That single call is the entire integration |
| HTTP | Flashcards ships a FastAPI router; host mounts it under `/vocab`. The host writes zero flashcard endpoints |
| UI | Reader emits "word selected" with `(lesson_id, span)`. Flashcards owns the picker, deck screens, and review screen. The lecture engine never renders a card |

### Prerequisite: `lesson_token`

Previously deferred as "pure optimisation." **Now a prerequisite for the split.**

Without it, resolving a highlight requires spaCy — so a split component loads a ~250 MB model in a second place. With it, the lecture engine resolves at ingest and persists the answer; flashcards then needs only the dictionary SQLite and **zero NLP**. That is what makes the split cheap.

Reorder in `docs/plan.md`: `lesson_token` precedes any extraction work.

## 17.6 D7 flagged as revisitable

D7 (pointer, not copy) exists so a *server* never persists textbook content. Local-only Docker weakens that rationale considerably — the user's own machine, their own legally-owned material, squarely § 53 private-copy territory.

If flashcards stored the sentence text directly: `sentence_at` disappears, the component becomes fully self-contained, decks survive lecture deletion, and exports carry real sentences instead of dangling pointers.

**Recommendation: keep the pointer**, because it preserves the option of a hosted version later. But this is now a cost being chosen deliberately, not a constraint being inherited. Revisit if a hosted version is ruled out.

## 17.7 CSV import (D19)

Not front/back pairs. A German word list:

```
das Haus
anrufen
Krankenversicherungskarte
groß
```

Each line runs through the same pipeline as manual entry: ladder → candidates → picker. Ambiguous entries either queue for picker review or take the top candidate with a summary at the end. Misses become `needs_gloss` notes, same as any other capture path.

This is bulk **capture**, not bulk authoring, and it is the natural bridge for someone arriving with an existing vocabulary list.

## 17.8 Added to §9 Rejected

| Rejected | Reason |
|---|---|
| Generic / non-German note types | D18. Competes with Anki on Anki's terms; effort displaces the German-specific features that have no competitor |
| Configurable note types, cloze deletion, custom templates | Same. Explicitly out of scope so it does not creep in later |
| Two-component split (lecture-engine + flashcards) | Forces copying `resolve.py`, breaking D3 |
| Separate container / HTTP service for flashcards | Network hop, second process, version compatibility matrix — none of it buys anything at current scale. Protocol contracts keep the option open |
| Plugin registry with hooks | Only justified once there is a second plugin |

## 17.9 Sequencing

The split is **deferrable indefinitely**. v1 may ship in-process with the boundaries observed as convention. Because the contracts are protocol-shaped, extraction later is mechanical: wrap the service in FastAPI on one side, swap the import for a client stub on the other.

What matters now is that v1 does not create coupling the split would have to undo — specifically: no cross-component foreign keys, and no direct reads of lecture-engine tables from flashcard code.
