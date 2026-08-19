# ADR-0004 — Multilingual learner meanings (DE/EN/FA) for German vocabulary

**Status:** NEEDS COLD REVIEW. Drafted 2026-08-19 by a non-slice governance
session from owner decisions taken after the slice-3 implementation was accepted
report-only and before slice-3 closure. Not accepted; nothing may be implemented
against it until PROMPTS.md §ADR cold review approves it (WORKFLOW §7, AGENTS G7).

**Amends:** ADR-0001 (§1's English-gloss-only product statement; D9's English-only
`needs_gloss` wording; §11 Card specification's `Gloss | English sense(s), max 3`
field row and the `needs_gloss` UI rule's English-only phrasing; §12's stage-04
English-gap-only scope; §8's per-row attribution scope, extended to localized
meaning rows) and ADR-0002 (§4's picker/commit contract, which gains an explicit
per-note meaning-language selection; §4's per-selection override schema; §6
order 7, whose stages 03–05 now include multilingual offline meaning enrichment).

**Does not amend and does not reopen:** ADR-0001 D1 (no runtime LLM), D3 (one
resolver), D4 (static SQLite dictionary asset), D8 (rendered faces never stored),
D18 and §17.8's rejection of generic/non-German note types, cloze, and
configurable templates; ADR-0002 §6 order 5 (Gate 2) and its coverage thresholds;
ADR-0002's standalone-service architecture and browser boundary; ADR-0003 in
full; AGENTS R1, R2, R4, R9, R12. Gate 2 keeps its position **before** stages
02–05.

**Decision IDs.** This ADR uses D32–D42. See §14 for a pre-existing ID collision
in the repository that this ADR deliberately does not repair.

---

## 1. Context — what changed, and what did not

ADR-0001 §1 states the product outcome as a fully populated German side "plus an
English gloss". Every downstream artifact inherited that: `sense.gloss_en` in
`reference/schema.sql`, D9's `needs_gloss` meaning *no English gloss*, §11's
`Gloss | English sense(s), max 3` field row, and §12 stage 04 as a job that fills
*English* gaps. The accepted slice-3 build stage 01 implements exactly that
contract.

The owner's decision is that a German-vocabulary card must be able to carry its
meaning in **German, English, or Persian**, in any non-empty combination, chosen
per note. That is a change to what a *meaning* is, not to what the app is for.

**The target language remains German.** DE, EN and FA are *meaning/display*
languages for German vocabulary. This ADR does not make the app a generic
multilingual learning platform, does not introduce generic note types,
configurable templates, or cloze, and does not reopen ADR-0001 D18 / §17.8. A
proposal to learn a language other than German remains a Stop-and-ask under
AGENTS C3, not scope.

The second thing that did not change is AGENTS R1 / ADR-0001 D1. Multilingual
meanings are produced in the **maintainer-operated offline dictionary build**.
The installed application still contains no LLM SDK, no API key, no network call
for meanings, and no per-card cost.

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D32 | **Three independent meaning languages.** A vocabulary note carries a **non-empty** selected subset of `{de, en, fa}` — seven legal combinations. The selected set is part of the note's meaning-display contract and drives which meaning sections a card renders. German grammar is **not** part of that selection and is never hidden by it | The learner, not the build, decides which meanings help. Making the set per-note and non-empty keeps "a card always shows some meaning" true without forcing a language on anyone |
| D33 | **German learner meaning is a first-class meaning, not the absence of a translation.** For each semantic sense: prefer one simple, common German synonym when it accurately preserves the sense; otherwise one short learner-friendly German explanation; target ≈A2–B1 comprehension where practical; never substitute an easier but semantically different word | "No translation" is not a teaching artifact. A learner-comprehensible German gloss is the monolingual-dictionary habit the app should build, and it is the only meaning language that stays inside the target language |
| D34 | **English stays source-first.** Wiktionary-derived English meanings are preferred wherever present. Missing English meanings may be generated **only** in the maintainer-side offline build, never at runtime | Preserves ADR-0001 §8's attribution chain and D1. Generation is a gap filler, not a source |
| D35 | **Persian is a first-class optional meaning language.** Persian text is generated offline against an **already disambiguated German semantic sense**, never from an isolated surface string, and with deterministic/source-backed context supplied to the generator. Persian rendering must support RTL correctly | Sense-blind translation of `Schloss` produces one wrong answer half the time. RTL is a presentation requirement of the renderer; it introduces no runtime service |
| D36 | **Language-neutral senses + a normalized localized-meaning relation.** The sense is the language-neutral semantic identity; localized texts hang off it in one table keyed by `(sense_id, language, kind, ord)` with their own `source`/`license`. Parallel `gloss_en`/`gloss_de`/`gloss_fa` columns are rejected (§12) | Adding a language must be data plus UI, never a schema redesign. DE, EN and FA come from different sources under different licenses, so provenance belongs on the localized row, not on the sense |
| D37 | **LLMs are permitted only in the maintainer-operated offline dictionary build**, in two roles: a **bulk structured-output generator** and a **selective semantic QA/correction reviewer**. Roles are normative; the commercial model names filling them are not | AGENTS R1 is absolute and unweakened. Naming roles rather than products keeps the pipeline portable when a model is renamed, repriced, or withdrawn |
| D38 | **Stage 04 is broadened** from "fill English gaps" to five maintainer-side jobs (A–E, §8). Every generated localized row stays individually identifiable and reversible under a versioned `source` marker | The existing stage-04 discipline (versioned marker, clean `DELETE`, never indistinguishable from Wiktionary) is exactly what multilingual generation needs; broadening scope must not dilute it |
| D39 | **Noun plural is core German grammar on the back of every noun card**, independent of the DE/EN/FA selection, rendered with its article (`Plural: die Häuser`). Plural knowledge is **tri-state**: known form / explicitly no normal plural / unknown. Unknown must never render as `kein Plural` | `das Haus → house` is an inadequate card (ADR-0001 §11) and so is `das Haus` with no plural. Collapsing unknown into "no plural" teaches a false fact, which is worse than teaching nothing |
| D40 | **Inflected and otherwise changed surface forms resolve to the canonical lemma.** One vocabulary note is based on the lemma; a conjugated, declined, comparative, or separable surface form never justifies a second note. Named regression families are planned test coverage, not aspiration (§9) | Reaffirms ADR-0001 D3 and the resolution ladder against the concrete way learners actually type and highlight. Per-form notes would fragment one FSRS state across a paradigm |
| D41 | **The card's meaning section is driven by the note's selected set**; only selected languages render. Core German grammar (article/gender, plural, principal parts, IPA, audio, separability, governed case, gradation) renders independently of that set. Rendered faces remain unstored (ADR-0001 D8 / AGENTS R4) | The selection is a display contract over structured fields — precisely the thing D8 made cheap. Storing per-language faces would recreate the migration cost D8 deleted |
| D42 | **Multilingual contribution policy is deferred, not decided.** The existing `gloss_contribution` scope (ADR-0001 D10) stays exactly as accepted — English, one vote per user per lemma — and is **not** silently generalized to German or Persian | No accepted decision requires generalizing it, and promotion/voting across three languages with different provenance rules is its own design problem. Deferring is cheaper than guessing (docs/backlog.md) |

## 3. German learner meaning (D33)

Policy, in order:

1. one simple, common German synonym, when it accurately preserves the sense;
2. otherwise one short learner-friendly German explanation;
3. target approximately A2–B1 comprehension where practical;
4. never replace a precise sense with an easier but semantically different one.

Intended style:

```text
anrufen
DE: mit jemandem am Telefon sprechen

beginnen
DE: anfangen

Umgebung
DE: der Bereich oder die Gegend um einen Ort
```

Existing German Wiktionary wording may be used verbatim when it is already
suitable, in which case the row is source-backed (`source='wiktionary_de'`,
CC BY-SA) and is **not** a generated row. Otherwise the offline build may
simplify or generate the learner wording, and the row carries the versioned
generated marker of D38. The `kind` of a German row is `synonym` when rule 1
applies and `definition` when rule 2 applies; that distinction is what lets the
renderer and a later QA pass treat them differently without re-parsing text.

## 4. English meaning (D34)

Unchanged in substance from ADR-0001: Wiktionary-derived English meanings are
preferred, ADR-0001's three-sense cap continues to govern how many English
meanings a lemma carries, and attribution stays per row. What changes is only
where the text lives — a localized meaning row with `language='en'`,
`kind='translation'` — and that a missing English meaning is now one absent
meaning among up to three, not automatically a `needs_gloss` card (§6).

Generation of missing English meanings remains a build-time job. There is no
`/gloss/generate`; ADR-0001 §10's "that absence is the design" stands.

## 5. Persian meaning (D35)

Persian rows are generated offline against a disambiguated sense. The generation
context must include the deterministic, source-backed information available for
that sense:

```text
German lemma
POS
gender where relevant
the selected semantic sense
English gloss where available
German source definition where available
```

Sense disambiguation is what makes this correct:

```text
Schloss / NOUN / das / sense = lock
EN: lock
FA: قفل

Schloss / NOUN / das / sense = castle
EN: castle
FA: قلعه
```

**RTL is a presentation requirement.** Persian text is stored as plain Unicode;
the build does not inject bidirectional control characters, and the renderer is
responsible for marking the Persian block `dir="rtl"` and `lang="fa"` so mixed
Latin/Persian content (a German lemma quoted inside a Persian explanation, Latin
punctuation, digits) lays out correctly. No runtime service, font download, or
network call is introduced. Rendering correctness for RTL is acceptance criteria
for the render slice, not a runtime dependency.

## 6. The data contract (D36)

### 6.1 Target shape

The sense is the language-neutral semantic identity. Localized texts are rows.

```sql
-- PART A (dictionary asset). Conceptual target; exact DDL is authored by the
-- slice that lands it, and reference/schema.sql is stale until then (§13).

CREATE TABLE sense (
  id        INTEGER PRIMARY KEY,
  lemma_id  INTEGER NOT NULL REFERENCES lemma(id),
  ord       INTEGER NOT NULL DEFAULT 0,
  register  TEXT,
  source    TEXT NOT NULL,          -- provenance of the sense DISTINCTION
  license   TEXT NOT NULL
);

CREATE TABLE sense_meaning (
  id        INTEGER PRIMARY KEY,
  sense_id  INTEGER NOT NULL REFERENCES sense(id),
  language  TEXT NOT NULL,          -- BCP-47 primary subtag: 'de' | 'en' | 'fa' | ...
  kind      TEXT NOT NULL,          -- 'definition' | 'synonym' | 'translation'
  ord       INTEGER NOT NULL DEFAULT 0,
  text      TEXT NOT NULL,
  source    TEXT NOT NULL,          -- wiktionary | wiktionary_de | llm_generated_v1 | contributed
  license   TEXT NOT NULL,
  UNIQUE(sense_id, language, kind, ord)
);
CREATE INDEX ix_sense_meaning ON sense_meaning(sense_id, language, ord);
```

`sense.gloss_en` is removed as the normative carrier of meaning. The English
gloss becomes one `sense_meaning` row.

**The `language` column carries no enumerating `CHECK` and no foreign key to a
closed list.** Adding a fourth meaning language must be data plus UI, never DDL —
that is the whole point of D36, and a `CHECK (language IN ('de','en','fa'))`
would silently reintroduce the schema redesign this decision exists to prevent.
The *currently supported* set is enforced by the build and the API, where it can
be changed without a migration. `kind` may carry a `CHECK`; it is a closed
vocabulary of three by design and adding a fourth kind is a deliberate contract
change.

**Provenance is per localized row** (AGENTS R11, ADR-0001 §8). DE, EN and FA
routinely come from different sources under different licenses for the *same*
sense; a single `source`/`license` on the sense cannot express that, and CC BY-SA
obligations and clean rollback of generated rows both depend on it being exact.

### 6.2 The note's selected languages

```sql
-- PART B (user DB).
CREATE TABLE note_meaning_lang (
  note_id  INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  language TEXT NOT NULL,
  PRIMARY KEY (note_id, language)
) WITHOUT ROWID;
```

- The set must be **non-empty**. SQLite cannot express "at least one child row"
  declaratively, so the non-empty invariant is enforced at the commit/API layer
  and rejected with HTTP 422 before any write (consistent with ADR-0002 §4).
- The selected set is **not part of note identity**. ADR-0001's
  `UNIQUE(user_id, lemma_text, pos, sense_id)` dupe rule is unchanged; two notes
  for one lemma+sense differing only in language selection must never exist.
- Changing the set is a display change: it adds or removes rendered sections and
  never destroys review history, note data, or FSRS state.

### 6.3 `needs_gloss` under three languages (supersedes D9's English-only wording)

- `status='needs_gloss'` means the note has **no** available meaning text in
  **any** of its selected meaning languages, from source or from the user.
- A note whose selected set is `{de, en, fa}` and which has only an English
  meaning is **resolved**. The DE and FA sections render as absent, not as
  failure, and this is not a status.
- ADR-0001 §11's rule stands unchanged: `needs_gloss` cards enter scheduling
  normally and are never quarantined. What is superseded is only the assumption
  that the missing thing is English.
- The user-authored meaning field must record **which language it is written
  in**. Its exact column/table shape is set by the slice that lands the note
  contract; it may not default to English silently.

## 7. LLM architecture (D37)

AGENTS R1 is absolute and unchanged. The installed flashcard application must
require:

```text
no OpenAI/Anthropic/etc. API key
no LLM SDK
no network request for meanings
no per-user/per-card LLM cost
```

The maintainer-operated offline build is the only place an LLM appears, and
`tools/build_dict.py` stage 04 remains the only place an API key exists anywhere
in the project (AGENTS R1, ADR-0001 §12).

Planned build architecture:

```text
source-backed dictionary
        ↓
deterministic sense/enrichment queue
        ↓
low-cost bulk structured-output model
        ↓
deterministic validation
        ↓
suspicious rows + small random audit sample
        ↓
stronger QA model
        ↓
validated localized meanings
        ↓
versioned SQLite dictionary asset
```

**Model roles (normative):**

| Role | Required capability | Applied to |
|---|---|---|
| Bulk generator | High-throughput structured/schema-constrained output; asynchronous or batch submission where the provider supports it; low unit cost at dictionary scale | Every queued enrichment row |
| Semantic QA / correction | Stronger semantic judgment on German sense fidelity and Persian/German learner wording | Deterministically flagged rows **plus** a small random quality sample — never every row |

**Commercial model names are not architectural dependencies.** The current
operational defaults are recorded non-normatively in `docs/plan.md`; swapping
them is an operational change, not an ADR change. A role may only be filled by a
model that satisfies its capability column.

**Deterministic validation runs before the QA model**, not after it: shape and
schema conformance, language/script checks (a Persian row must actually be
Persian script; a German row must not be English), empty/duplicate/echo-the-lemma
detection, length bounds, and forbidden-content checks. Its output is what
defines "suspicious".

**No speculative numbers are normative.** Queue size, generated-row counts,
coverage percentages, flag rates, wall-clock, and cost are **measured** during
the build and recorded in the slice report. This ADR fixes no percentage
threshold and no dollar estimate as acceptance criteria; see §11.

## 8. Stage-04 scope (D38)

Stage 04 may perform:

```text
A. fill missing English meanings
B. create/simplify German learner meanings
C. create Persian translations
D. validate generated localized meanings
E. selectively send suspicious rows to the stronger QA model
```

Constraints that survive the broadening unchanged:

- Every generated localized row is marked `source='llm_generated_v1'` or an
  explicitly versioned successor (`llm_generated_v2`, …). A new prompt, model
  role occupant, or pipeline revision that changes row semantics gets a new
  version string rather than reusing the old one.
- `DELETE FROM sense_meaning WHERE source LIKE 'llm_generated_%'` (or the
  specific version) must cleanly reverse a generation run.
- **No generated row may masquerade as source-backed Wiktionary content**
  (AGENTS R11). A generated row never carries `source='wiktionary'` or
  `'wiktionary_de'`, and a source-backed row is never rewritten in place by the
  pipeline — simplifying an existing German Wiktionary definition produces a
  *new* generated row alongside it, so the source text stays recoverable.
- License on a generated row records the generation terms, not CC BY-SA
  inherited from a source it did not come from. Where a generated row is derived
  from source-backed input, the derivation is recorded so the CC BY-SA
  obligation of ADR-0001 §8 remains traceable.
- Stage 04 stays inside the mid-September 2026 API-credit window recorded in
  `docs/backlog.md`; broadening its scope does not move that constraint.

## 9. Morphology: surface forms resolve to the lemma (D40)

A learner enters or highlights the form they met, not the dictionary form. The
resolution ladder (ADR-0001 §10) and the single resolver (D3, AGENTS R2) already
own this; this ADR makes the expected behaviour explicit so it becomes planned
test coverage rather than an assumption.

```text
ging        -> gehen
gegangen    -> gehen
Häuser      -> Haus
Kindern     -> Kind
größeren    -> groß
rief an     -> anrufen
ruft an     -> anrufen
```

One vocabulary note is based on the canonical lemma. **Do not create separate
notes merely because the learner encountered a conjugated, declined, comparative,
or separable surface form** — that would fragment one FSRS state across a
paradigm and defeat ADR-0001 D5's note/card model.

Regression coverage is planned for these families:

```text
regular + irregular verb conjugation
noun plural/case forms
adjective declension
comparative/superlative forms
separable verbs
```

The originally captured or example sentence is preserved **by value** under
ADR-0002 D21 regardless of which form the learner selected: the card records the
sentence the learner actually met, while the note is keyed on the lemma.

## 10. Card behaviour (D39, D41)

Conceptual back of a card whose selected set is `{de, en, fa}`:

```text
anrufen

German grammar:
Verb
ruft an
rief an
hat angerufen
IPA
...

Deutsch:
mit jemandem am Telefon sprechen

English:
to call / to phone

فارسی:
تماس گرفتن

Example:
Ich rufe dich morgen an.
```

- Only selected meaning languages render. An unselected language contributes no
  section, no heading, and no empty placeholder.
- **Core German grammar renders independently of the selection.** Disabling
  English does not hide the article, the principal parts, the IPA, or the plural.
- For nouns, **plural belongs in that core grammar block**:

```text
das Haus

Plural: die Häuser
```

- Plural rendering is tri-state and driven by data, not by NULL-guessing:

| Dictionary state | Rendered |
|---|---|
| A plural form is known | `Plural: die <form>` — prominently, with the article `die` |
| The upstream source explicitly states no normal plural exists | `kein Plural` |
| No plural information | nothing about plural at all |

  The third row is the load-bearing one: **missing or unknown plural data must
  never be presented as `kein Plural`.** The target shape is `lemma.plural TEXT`
  plus an explicit `lemma.plural_none INTEGER NOT NULL DEFAULT 0` set only from
  explicit upstream evidence (singulare tantum / "no plural" tagging), with
  `plural_none = 1` requiring `plural IS NULL`. Inferring `plural_none` from
  absence is forbidden.
- The article `die` in plural rendering is a rendering rule; it is not stored in
  `lemma.plural`.
- Existing article/gender, pronunciation, and other German grammar remain core
  card information (ADR-0001 §11).
- **Rendered faces are still never stored** (ADR-0001 D8, AGENTS R4). The
  selection is applied at render time over structured fields.
- **Translated example sentences are not made mandatory by this decision.**
  Nothing here requires a Persian or English rendering of the example sentence;
  that is unapproved and out of scope.
- Which selected meaning language appears on the *front* of a future production
  card (ADR-0001 §11 templates, v2) is deferred to the render slice. It may not
  silently assume English.

## 11. Non-normative operational details

The following are explicitly **not** acceptance criteria and must not be treated
as architectural commitments:

- exact commercial model names and their versions;
- API prices, per-row cost, and total build cost estimates;
- expected coverage percentages, flag rates, and queue sizes;
- wall-clock estimates for a generation run.

Real coverage and generation counts are **measured** in the build and recorded in
the owning slice's report. A number that has not been measured does not enter a
gate.

## 12. Rejected

| Rejected | Reason |
|---|---|
| **Parallel `gloss_en` / `gloss_de` / `gloss_fa` columns on `sense`** | Every new meaning language becomes a schema migration over a shipped dictionary asset plus every reader, writer, and test. It also has nowhere to put per-language `source`/`license`, so it breaks R11 the moment DE comes from `wiktionary_de` and FA from generation. It looks cheaper only while the count is three |
| **Runtime translation or runtime LLM calls (including "cached" ones)** | Violates ADR-0001 D1 and AGENTS R1 absolutely: ships a key, creates a network failure path in an offline app, and adds per-card cost. ADR-0001 §9 already rejected this for English; three languages do not change the argument, they triple it |
| **LLM-generating the whole dictionary instead of source-first enrichment** | Discards Wiktionary's structured grammar — gender, principal parts, plural, IPA, separability — which is the part of the card that actually carries it (ADR-0001 §11), in exchange for fluent unverifiable text. It also destroys the attribution chain and the ability to re-diff against a newer dump, and makes every error unattributable and irreversible. Generation stays a gap filler over a source-backed spine |
| **Separate vocabulary notes for every inflected surface form** | Fragments one FSRS state across a paradigm: `gehen`, `ging` and `gegangen` become three schedules for one word, review counts inflate, and dupe detection stops meaning anything. It is also a "solution" to a problem the resolver already solves (D3, D40) |
| Generic multilingual note types / configurable templates as the vehicle for DE/EN/FA | Would reopen ADR-0001 D18 and §17.8. Meaning-language selection is a fixed, small, German-vocabulary-specific display contract, not a template engine |
| Storing rendered per-language card faces | Reintroduces the migration cost ADR-0001 D8 / AGENTS R4 deleted, multiplied by the number of selected-set combinations |
| A closed `CHECK (language IN (...))` or a language foreign-key table | Makes adding a language a migration over a shipped read-only asset — exactly what D36 exists to prevent |
| Injecting Unicode bidi control characters into stored Persian text at build time | Encodes one renderer's assumptions into the data asset and corrupts export, search, and diffing. Direction is the renderer's job (§5) |
| Generalizing `gloss_contribution`/voting to German and Persian now | No accepted decision requires it, and promotion rules differ per language and per provenance. Deferred explicitly (D42), not silently adopted |
| Fixed cost/percentage acceptance criteria for the generation pipeline | Numbers nobody has measured become gates that either block correct work or pass incorrect work. Measure, then record (§11) |

## 13. Consequences

- **The accepted slice-3 implementation is now implementation-stale and must not
  close.** It writes `sense.gloss_en` under the English-only contract. It is
  correct against the contract it was briefed on, was accepted on Attempt 1 under
  `Risk: none`, and its acceptance stands. Closure is paused until this ADR is
  cold-review-approved and the existing slice-3 orchestrator issues an alignment
  brief. This is an owner-driven governance amendment, **not** a WORKFLOW §5
  implementation failure: it increments no attempt and no audit counter.
- **`reference/schema.sql` is deliberately stale** with respect to §6 and §10.
  It still shows `sense.gloss_en NOT NULL`, no `sense_meaning`, no
  `note_meaning_lang`, and no `lemma.plural_none`. That staleness is recorded
  here and in `docs/backlog.md` rather than repaired in this governance session,
  because a schema edit is implementation work and this session is forbidden from
  it. A cold reviewer should read the mismatch as *blocked and documented*, not
  as an undetected contradiction.
- Gate 2 (ADR-0002 §6 order 5) is unaffected and **stays where it is**. It
  measures stage-01 lemma/sense coverage — whether a word is found — which no
  part of this ADR changes. It must continue to run before the expensive later
  stages, and after the forthcoming slice-3 alignment.
- Stage 04's scope grows but its mid-September 2026 credit window does not.
- The render and API slices gain acceptance criteria: selected-set-driven meaning
  rendering, Persian RTL, and noun-plural-on-the-back tri-state behaviour, before
  UI/browser completion.
- Export (ADR-0001 §7 / AGENTS R10) will carry multiple meaning languages per
  note; sanitisation obligations are unchanged and now also apply to Persian text.

## 14. Known repository defect this ADR does not repair

`ADR-0002 D27` (two-stage highlight capture) and `ADR-0003 D27` (five confidence
buttons) are **two different decisions sharing one ID**. Both ADRs are accepted
and cold-review-approved; repairing the collision would mean editing accepted ADR
bodies, which is outside this session's mandate. It is filed in
`docs/backlog.md`. This ADR starts at D32 so the collision is not compounded.

## Cold review

Pending. This ADR has never been cold-reviewed; its status is `NEEDS COLD REVIEW`
and the drafting session did not remove it (WORKFLOW §7, AGENTS G7). A cold
reviewer writes either `APPROVED — remove NEEDS COLD REVIEW` or a numbered
objection list under this heading.
