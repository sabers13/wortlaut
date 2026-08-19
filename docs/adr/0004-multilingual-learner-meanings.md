# ADR-0004 — Multilingual learner meanings (DE/EN/FA) for German vocabulary

**Status:** ACCEPTED / FROZEN. ADR-0004 was approved at cold review #3 —
**FINAL CONVERGENCE REVIEW**. `NEEDS COLD REVIEW` is removed. O1–O5 and every
resolution record remain preserved. This ADR lineage is closed to further
ordinary cold review: there is no ADR-0004 review #4. Subsequent work may
implement this accepted architecture but must not substantively revise it
without a genuinely new architectural decision/lineage.

**Amends:** ADR-0001 (§1's English-gloss-only product statement; D9's English-only
`needs_gloss` wording; §11 Card specification's `Gloss | English sense(s), max 3`
field row and the `needs_gloss` UI rule's English-only phrasing; §12's stage-04
English-gap-only scope; §8's per-row attribution scope, extended to localized
meaning rows; §4's numeric `sense_id` note/dictionary-identity assumption;
§12's dictionary-replacement/activation lifecycle; §14's deferred
compound-gloss/composition behaviour) and ADR-0002 (§4's picker/commit contract,
which gains an explicit per-note meaning-language selection; §4's per-selection
override schema; §4's picker/commit dictionary identity transport and
revalidation; §5's smoke expectations for dictionary replacement/stale picker;
§6 order 7, whose stages 03–05 now include multilingual offline meaning
enrichment).

**Does not amend and does not reopen:** ADR-0001 D1 (no runtime LLM), D3 (one
resolver), D4 (static SQLite dictionary asset), D8 (rendered faces never stored),
D18 and §17.8's rejection of generic/non-German note types, cloze, and
configurable templates; ADR-0002 §6 order 5 (Gate 2) and its coverage thresholds;
ADR-0002's standalone-service architecture and browser boundary; ADR-0003 in
full; AGENTS R1, R2, R4, R9, R12. Gate 2 keeps its position **before** stages
02–05.

**Decision IDs.** This ADR uses D32–D47. See §14 for a pre-existing ID collision
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
| D32 | **Three independent meaning languages.** A vocabulary note carries a **non-empty** selected subset of `{de, en, fa}` — seven legal combinations. The selected set is part of the note's meaning-display contract and drives which meaning sections a card renders. German grammar is **not** part of that selection and is never hidden by it | The learner, not the build, decides which meanings help. Making the set per-note and non-empty ensures every note specifies at least one desired learner-meaning language without forcing a language on anyone; actual content availability is represented separately by D43 (`meaning_state`) and may be none, partial or complete |
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
| D43 | **Resolver outcome and meaning availability are independent.** `note.status` remains the persisted resolver outcome (`resolved | derived_compound | needs_gloss`), where `needs_gloss` means only that the resolver reached its stub fallback and could not bind the note to a dictionary-backed identity. Selected-language availability is a separate, computed, non-persisted `meaning_state = none | partial | complete`; the learner-facing "needs meaning" condition is `meaning_state='none'`. Changing language selection, user meanings, or dictionary coverage recomputes `meaning_state` but never rewrites resolver status | A resolved sense with no text in a selected language and an unresolved stub with complete user meanings are both legitimate states; overloading `note.status` with both machines makes every such transition ambiguous (O1). Computing availability from current data keeps a dictionary swap from becoming a user-DB migration |
| D44 | **Normalized language-bearing user-authored meanings.** One `note_user_meaning` row per `(note_id, language)` holds the user's own DE/EN/FA meaning text. `/vocab/cards` carries an explicit language-keyed `user_meanings` override (string upsert, `null` delete, omission = no mutation, `{}` invalid), and `/vocab/gloss` becomes a language-bearing edit API (POST upsert / DELETE by note+language) independent of resolver status. Scalar `note.gloss_user` is superseded; D10 contribution stays English-only | One scalar gloss cannot represent meanings in three languages, and the old `gloss_user` rule was tied to resolver `needs_gloss` (O2). Normalizing by `(note_id, language)` gives unambiguous add/update/delete semantics, keeps authored data independent of the display selection, and avoids an implicit English default |
| D45 | **Generated localized-meaning derivation/provenance relation.** `sense_meaning_derivation` records, per generated meaning, every source-backed localized meaning whose text was actually consumed as derivation input; generated→generated edges are forbidden in v1. Generated rows keep their versioned `llm_generated_vN` marker, and rollback by that marker deletes generated rows plus their derivation edges, never source-backed rows | A generated row's `source` must stay the generation version and `license` is not a source-row reference, so the upstream CC BY-SA obligation was unreconstructable from the proposed row alone (O3). A normalized derivation relation makes attribution/license traversal and clean rollback both explicit |
| D46 | **Derived-compound learner meanings remain in v1, but only as a conservative, computed component decomposition.** For `status='derived_compound'`, the note persists an ordered stable component/sense binding vector; rendering an ordered per-component decomposition for selected language L when all components have localized text in L. If any component lacks L text, no dictionary L block is rendered and L is unavailable under D43. Note-local user meanings win; no composed text or card face is stored; provenance remains the exact component rows rendered (§6.5) | Preserves derived compound learning value without guessing or concatenating inaccurate natural-language translations of whole compounds (O4). All-components-or-none keeps availability and rendering deterministic |
| D47 | **Dictionary replacement uses stable semantic references and atomic fail-closed re-binding; numeric IDs are per-asset caches only.** PART A assigns deterministic stable semantic references to lemmas and senses (`lemma.semantic_ref`, `sense.semantic_ref`, `sense.source_ref`); PART B persists durable semantic bindings and active dictionary version+SHA metadata. Candidate dictionaries undergo checksum/integrity/stable-ref validation before an atomic relink transaction swaps handles under an exclusive lock; missing items fail closed to `needs_gloss` without losing user data; duplicate/ambiguous refs abort activation; stale picker tokens return HTTP 409 (§6.6) | Numeric SQLite IDs are not durable cross-version identity and change on rebuilds (O5). Stable semantic refs plus fail-closed atomic activation prevent stale ID collisions, wrong-sense binding, and mixed runtime states while preserving user history |

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
meaning among up to three. Whether a note is resolver-`needs_gloss` is decided
solely by the resolver outcome, never by whether English text happens to exist
(D43, §6.3).

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

CREATE TABLE lemma (
  id           INTEGER PRIMARY KEY,
  semantic_ref TEXT NOT NULL UNIQUE,  -- namespaced/versioned canonical identity hash (D47)
  lemma        TEXT NOT NULL,
  pos          TEXT NOT NULL,
  gender       TEXT,                  -- 'm' | 'f' | 'n' | NULL
  freq_rank    INTEGER,
  plural       TEXT,
  plural_none  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sense (
  id           INTEGER PRIMARY KEY,
  lemma_id     INTEGER NOT NULL REFERENCES lemma(id),
  semantic_ref TEXT NOT NULL UNIQUE,  -- namespaced/versioned sense identity hash (D47)
  source_ref   TEXT NOT NULL,         -- upstream stable sense identifier or canonical raw distinction hash
  ord          INTEGER NOT NULL DEFAULT 0,
  register     TEXT,
  source       TEXT NOT NULL,         -- provenance of the sense DISTINCTION
  license      TEXT NOT NULL
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

CREATE TABLE sense_meaning_derivation (
    generated_meaning_id INTEGER NOT NULL
        REFERENCES sense_meaning(id) ON DELETE CASCADE,
    source_meaning_id INTEGER NOT NULL
        REFERENCES sense_meaning(id) ON DELETE RESTRICT,
    PRIMARY KEY (generated_meaning_id, source_meaning_id),
    CHECK (generated_meaning_id <> source_meaning_id)
) WITHOUT ROWID;
```

Numeric `lemma.id` and `sense.id` remain local INTEGER primary keys inside one
`dictionary_vN.sqlite`; they are per-asset local keys, not durable cross-version
identity (D47).

`sense.gloss_en` is removed as the normative carrier of meaning. The English
gloss becomes one `sense_meaning` row.

**Derivation (D45).** `sense_meaning_derivation` records, for each generated
localized meaning, every source-backed localized meaning whose **text** was
actually consumed as derivation input. Cardinality:

- one generated meaning → zero or more source-backed localized inputs;
- one source-backed localized meaning → zero or more generated meanings;
- each pair is unique.

Build-time validation (not SQLite FK syntax) enforces that:

- `generated_meaning_id` points to a row whose `source` is a versioned
  `llm_generated_vN` marker;
- `source_meaning_id` points to a source-backed, non-generated localized meaning;
- both rows belong to the same semantic `sense_id`;
- generated-to-generated derivation edges are forbidden in v1;
- every source-backed localized meaning row whose text is actually supplied to
  generation, simplification, or semantic QA as derivation input is recorded.

If generation uses no localized source-backed meaning text and operates only
from source-backed sense/grammar/context fields, zero derivation edges are
valid — the generated row's `sense_id` plus sense provenance still identifies
its semantic sense lineage. If a pipeline revision would otherwise consume a
generated meaning as derivation input, v1 must instead re-anchor to the
original source-backed localized rows or STOP; do not create generated→generated
provenance chains.

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
- The selected set is **not part of note identity**. ADR-0001's historical
  numeric-sense note uniqueness assumption `UNIQUE(user_id, lemma_text, pos, sense_id)`
  is explicitly superseded: selected languages remain not part of note identity;
  direct/derived dictionary identity is D47's durable semantic binding (stable
  `sense_ref` for direct, ordered component `(lemma_ref, sense_ref)` vector for
  derived compounds); and numeric `sense_id` is never durable note identity.
  Two notes differing only in language selection must never exist.
- Changing the set is a display change: it adds or removes rendered sections and
  never destroys review history, note data, or FSRS state.

### 6.3 Resolver status vs. meaning availability (D43; supersedes D9's English-only wording)

`note.status` is and remains the **persisted resolver outcome**, with exactly
`resolved | derived_compound | needs_gloss`. `needs_gloss` means **only** that
the resolver reached its fourth fallback/stub outcome and could not bind the
note to a dictionary-backed resolved or derived-compound identity
(ADR-0001 §10, `app/resolve.py`). It is **not** a statement about whether
DE/EN/FA meaning text currently exists.

Separately, a **non-persisted computed** state named `meaning_state` has exactly
`none | partial | complete`. For each currently selected language L, L is
**available** when either:

1. a `note_user_meaning` row exists for `(note_id, L)`; OR
2. `note.status == 'resolved'` and a **successfully validated current D47 direct
   binding** has at least one matching `sense_meaning` row for `(current_sense_id, language=L)`; OR
3. `note.status == 'derived_compound'` and a **successfully validated current D47
   component vector** satisfies D46's all-components localized-meaning rule for L.

If the note has no valid current dictionary binding (including an unresolved
stub or a note whose binding disappeared during dictionary replacement),
dictionary conditions 2 and 3 are false; user meanings may still make languages
available. Then:

- `none`: zero selected languages are available;
- `partial`: at least one, but fewer than all selected languages, are available;
- `complete`: every selected language is available.

The learner-facing "needs meaning" condition is `meaning_state == 'none'`, **not**
"one or more selected languages missing". `partial` is a usable card, not a
failure condition. Missing selected-language sections may be absent from
rendering and may expose an edit/add affordance, but they do not change resolver
status.

**Status interactions (normative):**

- An unresolved/stub note remains `status='needs_gloss'` even after the learner
  writes one or more user meanings.
- A dictionary-resolved note remains `status='resolved'` even if none of its
  currently selected meaning languages has text.
- Changing selected meaning languages or editing user meanings **must not**
  rewrite resolver status.
- Dictionary replacement runs D47 atomic validation and relinking before a new
  asset is visible. D47's activation/relink owner is the only component that may
  alter `note.status` upon dictionary replacement (e.g. transitioning a note
  whose sense or component disappeared to `needs_gloss`, or restoring it on
  exact re-binding). `meaning_state` is then recomputed against the successfully
  activated current binding; no bulk persisted `meaning_state` migration is
  introduced.

**Recalculation.** `meaning_state` is computed, not stored, and is recomputed
from current data: on note/card read; on rendering; on the representation
returned after note creation; after `meaning_langs` replacement; after
user-meaning add/update/delete; and automatically on reads against the
successfully activated current dictionary binding. No migration or bulk user-DB
state rewrite is needed when dictionary meaning coverage changes.

**Scheduling.** Scheduling remains independent of both states. ADR-0001 §11's
rule stands unchanged: resolver `needs_gloss` cards enter scheduling normally
and are never quarantined. Likewise `meaning_state=none` or `partial` does not
quarantine a resolved note. What is superseded is only the assumption that
`needs_gloss` said something about missing meaning text.

### 6.4 Normalized language-bearing user meanings (D44)

Conceptual PART-B relation:

```sql
CREATE TABLE note_user_meaning (
    note_id  INTEGER NOT NULL
        REFERENCES note(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    text     TEXT NOT NULL,
    PRIMARY KEY (note_id, language)
) WITHOUT ROWID;
```

This is conceptual architecture DDL; implementation/alignment owns the exact
physical migration. The currently supported API language codes are exactly
`de | en | fa`. There is **no** closed database `CHECK` or language-enum FK —
the API enforces the current supported set (same rule as §6.1's `language`
column). One note may have at most one user-authored meaning per language in
v1. `note.gloss_user` is superseded as the normative persistence carrier (D44;
see the ADR-0002 supersession below).

**`/vocab/cards` request contract.** The existing per-selection `overrides`
object is unchanged, and `meaning_langs` stays exactly as already defined. One
further permitted override key is added: `user_meanings` — an object keyed by
language, with allowed keys exactly `de | en | fa`.

```json
{
  "selections": [
    {
      "ref": "stable-dictionary-ref",
      "sense_id": 17,
      "overrides": {
        "meaning_langs": ["de", "fa"],
        "user_meanings": {
          "de": "mit jemandem am Telefon sprechen",
          "fa": "تماس گرفتن"
        }
      }
    }
  ],
  "capture_context": { },
  "deck": { }
}
```

Each value is either a nonblank JSON string — insert or replace
`(note_id, language)` — or JSON `null` — delete `(note_id, language)` if present
(idempotent no-op when absent). A blank or whitespace-only string is invalid and
must **not** mean delete. An empty `user_meanings: {}` is invalid with HTTP 422;
omission is the no-op representation. Unknown language key, unknown override
key, unsupported type, blank text, duplicate language representation, malformed
object, or any other validation failure rejects the entire `/vocab/cards`
request with HTTP 422 **before any write**. No language is inferred from
content, and no language silently defaults to English.

On a newly created note, `meaning_langs` is still explicitly required and
non-empty, and omitted `user_meanings` creates no user-meaning rows. On a reused
note, omitted `user_meanings` means no mutation and only explicitly present
language keys are changed. All validation occurs before mutation, and the entire
`/vocab/cards` commit remains atomic across candidate identity revalidation,
note create/reuse, front/back override changes, `meaning_langs`,
`user_meanings`, note/deck membership, and capture/example persistence; any
failure returns HTTP 422 with zero writes.

**Interaction with `meaning_langs`.** `meaning_langs` is a display/render
selection, not ownership of authored data. A `note_user_meaning` may exist for
an unselected language; removing a language from `meaning_langs` must **not**
delete its user meaning; reselecting that language makes the stored user meaning
available again; the selected set must always remain non-empty; and D43
`meaning_state` counts only currently selected languages.

**Dictionary vs. user meaning rendering.** Source-backed `sense_meaning` rows
are immutable dictionary data; user edits never overwrite them. For each
selected language:

1. if `note_user_meaning(note_id, language)` exists, render that note-local user
   meaning as the complete meaning block for that language;
2. else if `note.status == 'resolved'` and a valid current D47 direct binding
   exists, render the direct dictionary `sense_meaning` row(s) for that note's
   current sense/language in deterministic order;
3. else if `note.status == 'derived_compound'` and a valid current D47 component
   vector satisfies D46's all-components localized-meaning rule for that
   language, render the computed D46 component decomposition for that language;
4. otherwise render no meaning block for that language.

A user meaning is therefore a note-local display override for one language; it
does not modify dictionary provenance. `back_override` remains the existing
whole-back override and remains orthogonal — it is not repurposed as structured
meaning storage.

**`/vocab/gloss` contract.** `/vocab/gloss` is retained to minimize API churn
but is superseded from "fill a resolver needs_gloss card" to the dedicated
language-bearing note-user-meaning edit endpoint.

```json
POST /vocab/gloss
{ "note_id": 123, "language": "fa", "text": "تماس گرفتن", "contribute": false }
```

`note_id` identifies an existing note; `language` is required and exactly one of
`de | en | fa`; `text` is required, a JSON string with at least one
non-whitespace code point, stored verbatim. The operation is an upsert of
`(note_id, language)`, valid regardless of `note.status` and valid whether or
not `language` is currently selected. No resolver-status mutation occurs, and
the returned meaning state is recomputed under D43.

```text
DELETE /vocab/gloss/{note_id}/{language}
```

`language` must be one of `de | en | fa`; only the matching `note_user_meaning`
row is deleted; deleting a nonexistent row is idempotent success; `meaning_langs`
is not altered; resolver `note.status` is not altered; D43 meaning state is
recomputed for the returned/current representation. The API may use the existing
project convention for the precise success status code; the mutation semantics
above are normative.

**D10 / `gloss_contribution`.** ADR-0001 D10 remains English-only. `contribute`
is valid only on `POST /vocab/gloss` with `language == "en"`. `contribute:
true` upserts the user's one existing D10 English contribution for the note's
lemma/POS to the exact submitted English text, in the same transaction as the
English user-meaning upsert; `contribute: false` or omission does not mutate
`gloss_contribution`; `contribute: true` with `de` or `fa` is HTTP 422 before
any write. German/Persian meanings are never written to `gloss_contribution`.
Deleting a local English `note_user_meaning` does not implicitly retract or
delete a previously submitted contribution, and changing a local English meaning
without `contribute:true` does not silently rewrite an earlier contribution —
contribution stays an explicit submitted vote, separate from local card editing.
Multilingual contribution/voting and contribution-withdrawal policy remain
deferred (D42).

### 6.5 Derived-compound learner meanings (D46)

For notes with `status='derived_compound'`, learner meanings remain in v1 as a
conservative, computed component decomposition rather than an unprincipled
synthesized translation.

1. **Resolver outcome and component ordering.** `status='derived_compound'`
   remains solely a persisted resolver outcome. The resolver's compound
   components are ordered left-to-right, with the grammatical head last. The
   implementation-alignment work extends derived-compound resolver results from
   bare surface strings to an ordered stable component binding.
2. **Deterministic component lemma selection.** For the head component, retain
   the resolver-selected head. For every preceding component candidate set,
   order candidates deterministically by current dictionary `freq_rank`
   ascending (with `NULL` last), then `pos`, then `gender` (with `NULL` last),
   then stable `lemma.semantic_ref` lexical order; select the first.
3. **Deterministic source sense selection.** For each selected component lemma,
   select exactly one source sense independent of display language: lowest
   `sense.ord`, tie-broken lexically by stable `sense.semantic_ref`.
4. **Durable persistence.** The ordered component semantic bindings are
   persisted in PART B under D47 (`note_dictionary_binding` with
   `role='component'`). No composed compound learner-meaning text is ever
   persisted in PART A or PART B.
5. **Language-by-language rendering and availability.** For each selected
   language L:
   - If `note_user_meaning(note_id, L)` exists, it is the entire meaning block
     for L and L is available under D43.
   - Otherwise, a derived dictionary meaning for L is available ONLY if every
     bound component lemma has at least one localized `sense_meaning` row for L
     under its bound source sense.
   - If only some components have localized meaning text in L, there is NO
     partial component composition for that language: render no dictionary
     block for L and count L as unavailable in D43 `meaning_state`.
6. **Deterministic localized text selection.** When all components have L text,
   select exactly one localized row per component by the deterministic tuple:
   - source-backed rows before `llm_generated_vN` rows;
   - kind priority:
     - for DE: `synonym`, `definition`, `translation`;
     - for EN / FA: `translation`, `definition`, `synonym`;
   - `ord` ascending;
   - lexical tie-breakers on `source`, `license`, `text`.
7. **Decomposition rendering.** Render an ordered decomposition, one component
   lemma + its selected localized text per line/block, left-to-right. The
   system does **not** concatenate or synthesize those component glosses into a
   claimed natural-language translation of the whole compound. The historical
   ADR-0001 §14 "compound gloss trimming" concatenation is superseded on
   ADR-0004 approval.
8. **Attribution and provenance.** Derived compound output is computed on
   read/render and is never stored as a `sense_meaning`, note meaning, or card
   face (AGENTS R4). Provenance for a derived language block is the ordered set
   of the exact component `sense_meaning` rows rendered; each retains its own
   `source` and `license`. If any selected component row is generated, D45
   derivation traversal remains mandatory. No synthetic compound provenance row
   is created. User meanings do not alter component/dictionary provenance.
9. **State and scheduling.** `meaning_state` evaluates D46 availability under the
   all-components-or-none rule. Resolver status remains `derived_compound` and
   card scheduling remains independent.

### 6.6 Dictionary semantic identity, relinking, and fail-closed activation (D47)

Numeric SQLite IDs (`lemma.id`, `sense.id`) are per-asset local primary keys and
are **never durable cross-version semantic identity**. Cross-version dictionary
replacement is governed by stable semantic references, immutable asset tokens,
and atomic fail-closed relinking.

#### Stable PART-A identities

- Every dictionary lemma row has exactly one non-empty unique
  `lemma.semantic_ref`.
- Every dictionary sense row has exactly one non-empty unique
  `sense.semantic_ref` and a non-empty source-side `sense.source_ref`.
- `lemma.semantic_ref` is generated deterministically from a versioned canonical
  tuple: `(target_lang='de', nfc_lemma_text, pos, gender_or_null_sentinel)`.
  It uses a namespaced/versioned SHA-256 representation, e.g.
  `lemma:v1:<sha256(canonical tuple)>`. Exact serialization is specified in
  implementation and golden-tested. Homographs are disambiguated by POS/gender.
- `sense.source_ref` is the upstream stable sense identifier when provided by the
  source. If no upstream identifier exists, build stage 01 deterministically
  fingerprints the canonical raw source-side sense-distinction record (excluding
  asset-local numeric IDs and localized/generated enrichment rows). A changed
  fingerprint indicates a new semantic distinction; continuity must not be
  guessed.
- `sense.semantic_ref` is a namespaced/versioned SHA-256 over
  `(lemma.semantic_ref, sense.source_namespace, sense.source_ref)`. Multiple
  senses for one homograph produce distinct stable sense refs.
- Build/release validation rejects blank refs, duplicate refs, malformed refs,
  and any cross-version reuse of one semantic ref for a different canonical
  identity tuple. A defective asset is never activatable.

#### Durable PART-B semantic binding

Conceptual `note_dictionary_binding` relation:

```sql
CREATE TABLE note_dictionary_binding (
    note_id                    INTEGER NOT NULL REFERENCES note(id) ON DELETE CASCADE,
    role                       TEXT NOT NULL CHECK (role IN ('direct', 'component')),
    component_ord              INTEGER NOT NULL DEFAULT 0,
    lemma_ref                  TEXT NOT NULL,
    sense_ref                  TEXT NOT NULL,
    cached_lemma_id            INTEGER,
    cached_sense_id            INTEGER,
    bound_dictionary_version   TEXT,
    PRIMARY KEY (note_id, role, component_ord)
);
```

- A `resolved` note has exactly one `direct` binding (`component_ord = 0`).
- A `derived_compound` note has one or more `component` bindings, contiguous
  `component_ord` starting at 0 in D46 order, head last.
- A never-bound `needs_gloss` stub has no semantic binding.
- If a bound sense or component disappears from the current dictionary, retain
  its durable semantic refs but clear `cached_lemma_id`, `cached_sense_id`, and
  `bound_dictionary_version` so historical semantic identity is preserved.
- Old PART-B `lemma_id` / `sense_id` columns, if retained physically during
  migration, are convenience caches only and never decide cross-version identity.
- Direct note create/reuse identity is the stable `sense_ref`. Derived-compound
  create/reuse identity is the ordered vector of bound component
  `(lemma_ref, sense_ref)` pairs. If the physical note table requires a scalar
  uniqueness key, materialize a versioned deterministic `dictionary_key` from
  those stable refs.
- User meanings (`note_user_meaning`), selected languages (`note_meaning_lang`),
  cards, review history, front/back overrides, frozen example sentences, and
  deck memberships survive relinking unchanged.

#### Picker and API contract

- Stage 1 picker payload (`POST /vocab/highlight`, `POST /vocab/lookup`) exposes
  an immutable dictionary asset token containing dictionary version + SHA-256
  checksum.
- A resolved candidate transports stable lemma `ref` + stable `sense_ref`.
- A derived-compound candidate transports its ordered component
  `(lemma_ref, sense_ref)` vector.
- Numeric `lemma_id` / `sense_id` may be included as convenience caches for the
  currently active asset but are never authoritative.
- `/vocab/cards` commit round-trips the exact picker dictionary asset token.
- If the active dictionary token changed between picker and commit,
  `/vocab/cards` returns HTTP 409 `dictionary_changed` before ANY write, and the
  client must refresh/reselect. Stale picker results are never silently rebound.

#### Candidate download vs. activation

- `latest.json` indicates available downloads, but checksum/download success
  does not make a candidate visible to runtime reads.
- Candidates are downloaded to immutable versioned file paths,
  checksum-verified, opened read-only, and validated against schema, integrity,
  and stable-ref uniqueness gates before becoming eligible for activation.
- PART B stores one active dictionary version + SHA metadata record.

#### Atomic activation and fail-closed relinking

- The user-data/deck layer owns activation (`app/dictionary.py` remains read-only
  and never accesses user state per AGENTS C2/R9).
- Acquire an exclusive dictionary-activation lock excluding concurrent API
  reads/writes during the transition.
- Pre-open and validate the candidate dictionary handle before mutating PART B.
- In a single user-DB transaction, rebind every existing durable semantic
  binding by exact stable ref matching. Numeric IDs are NEVER used as match
  keys.
- Exact one-match rebind updates `cached_lemma_id`, `cached_sense_id`, and
  `bound_dictionary_version`.
- Zero matches for a direct sense is a legitimate disappearance outcome: clear
  cached numeric IDs/version, retain durable refs, set `note.status='needs_gloss'`,
  and preserve user meanings and review history.
- Zero matches for ANY component of a derived compound invalidates the entire
  derived binding: clear cached numeric IDs/version for all components in the
  vector, retain stable refs/order, set `note.status='needs_gloss'`; never expose
  a partially rebound compound.
- If a subsequent asset restores the exact durable sense or component vector,
  the activation owner restores `note.status` to `resolved` or
  `derived_compound` after exact all-component rebind.
- A never-bound `needs_gloss` stub has no semantic ref and is never
  auto-promoted simply because a new dictionary contains matching text. User
  capture/re-resolution remains the explicit path for new semantic bindings.
- Multiple matches for one stable ref, duplicate refs, malformed cardinality, or
  any candidate integrity ambiguity is an ACTIVATION FAILURE: rollback the user
  transaction, discard the candidate handle, and keep the previous dictionary
  active.
- Implementations must never guess a "closest" replacement sense.
- `app/resolve.py` is the only resolver. The PART-B activation owner is the ONLY
  owner of resolver-status mutations caused by dictionary replacement. Exact
  stable-ref relinking is not a second resolver. If dictionary activation ever
  requires a true semantic re-resolution rather than an exact stable-ref rebind,
  the activation owner MUST invoke the canonical `app/resolve.py` resolver; it
  must not implement or embed an independent resolver path.
- Update the active dictionary version + SHA metadata in the same user-DB
  transaction as binding caches and status.
- While the activation lock is held, commit the user transaction, swap the
  runtime dictionary handle to the pre-validated candidate, and then release the
  lock.
- Requests observe either the complete old state or complete new state, never a
  mixed binding/asset state.
- On startup, open the exact immutable asset specified by PART-B active metadata;
  never bind blindly to `latest`.
- If candidate validation, relinking, or transaction commit fails, fail closed
  and continue serving the previous active asset.

#### Meaning state and R9 interaction

- `meaning_state` consults dictionary meanings only through a current binding
  whose `bound_dictionary_version` matches active PART-B metadata and whose
  stable refs match cached IDs. It never dereferences an old numeric `sense_id`
  into a replacement dictionary.
- User meanings survive all replacement outcomes and remain available.
- `dictionary_vN.sqlite` remains a disposable, read-only asset in its own file
  and volume (AGENTS R9). Failed activation affects only candidate state.

#### Required gate coverage

- Deterministic stable-ref generation for lemmas and senses;
- Uniqueness and malformed/duplicate ref rejection;
- Rejection of cross-version semantic ref reuse for different canonical tuples;
- Dictionary replacement where numeric IDs are completely renumbered but stable
  refs match: notes stay correctly bound;
- Reused numeric ID pointing to an unrelated sense: must NOT bind;
- Disappeared sense: user meanings and history survive, status transitions to
  `needs_gloss` through activation owner;
- Duplicate/ambiguous stable ref: entire activation rolls back, previous asset
  stays active;
- Derived compound all components survive: correctly rebound;
- Derived compound component disappears: whole derived block unavailable;
- Never-bound `needs_gloss` remains unbound;
- Stale picker asset token → HTTP 409 and zero writes;
- `meaning_state` only sees successfully validated current bindings;
- No mixed binding/asset state observable;
- Startup metadata/asset checksum mismatch fails closed.

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
- **No generated row may masquerade as source-backed Wiktionary content**
  (AGENTS R11). A generated row never carries `source='wiktionary'` or
  `'wiktionary_de'` unless it is genuinely source-backed, and a source-backed
  row is never rewritten in place by the pipeline — simplifying an existing
  German Wiktionary definition produces a *new* generated row alongside it, so
  the source text stays recoverable.
- **Derivation (D45).** Every source-backed localized text input actually
  consumed by generation, simplification, or semantic QA is recorded in
  `sense_meaning_derivation` (cardinality and validation in §6.1). Generated
  rows keep their versioned `source` marker; upstream Wiktionary identity is not
  written into that field; generated→generated derivation edges are forbidden in
  v1.
- **License semantics (D45).** For a generated `sense_meaning`: `source`
  identifies the generation pipeline/version; `license` records the output
  distribution/license classification assigned by the maintainer build policy
  after considering applicable upstream obligations. It must not falsely
  relabel generated output as Wiktionary. Each linked source-backed localized
  row retains its own `source`/`license`; derivation edges do not duplicate or
  replace those licenses. Attribution/package generation must traverse
  `generated sense_meaning → sense_meaning_derivation → source-backed
  sense_meaning row(s)` so upstream attribution/license obligations remain
  reconstructable. If build policy cannot establish an output-license
  classification compatible with the linked upstream obligations, validation
  must STOP rather than erase the provenance problem.
- **Rollback (D45).** Rollback is driven solely by the generated version marker:

  ```sql
  DELETE FROM sense_meaning WHERE source = 'llm_generated_vN';
  ```

  Deleting the generated row cascades its outgoing `sense_meaning_derivation`
  edges, and must **not** delete source-backed localized meaning rows.
  `ON DELETE RESTRICT` on `source_meaning_id` prevents deleting a source row
  while a generated row still depends on it. Generated data therefore remains
  cleanly reversible without provenance loss.
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
- For each selected language, the meaning block renders:
  1. note-local `note_user_meaning` when one exists (D44);
  2. otherwise, for `status='resolved'`, the direct dictionary `sense_meaning`
     rows for the note's sense/language in deterministic order (D36);
  3. otherwise, for `status='derived_compound'`, the computed D46 component
     decomposition only when all components satisfy availability for that
     language (all-components-or-none; no partial composition);
  4. otherwise no meaning block for that language.
  A user meaning is a note-local display override for one language and never
  modifies dictionary provenance. No composed compound text is ever persisted;
  component provenance remains attributable under AGENTS R11 / D45.
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
- **Implementation alignment and owning slices:**
  - **slice-3 alignment** owns only the Stage-01 / PART-A contract alignment:
    `lemma.semantic_ref`; `sense.semantic_ref`; `sense.source_ref`; numeric
    lemma/sense IDs explicitly remaining per-asset local keys; the schema and
    representation shape needed for D36 `sense_meaning`; the schema and
    representation shape needed for D45 `sense_meaning_derivation`;
    deterministic D46 component semantic-binding information needed by the
    canonical resolver/alignment; and the already-required tri-state noun-plural
    shape (`lemma.plural`, `lemma.plural_none`). Slice-3 is stage-01 dictionary
    build work and does not implement the runtime user DB, activation transaction,
    API behavior, rendering, or smoke scenarios.
  - **slice-6** remains the offline enrichment owner: stages 03–05
    populate/enrich multilingual meaning rows under the documented ADR-0004
    contract; the mid-September 2026 API-credit constraint on stage 04 is
    unchanged.
  - **slice-7** (runtime app work) owns PART-B and runtime behavior:
    `note_meaning_lang`; `note_user_meaning`; scalar `note.gloss_user`
    supersession/removal; PART-B `note_dictionary_binding`; active dictionary
    version+SHA metadata; resolver-status / computed `meaning_state` runtime
    integration; D43/D44/D46 read/render behavior; user-meaning precedence
    (`note_user_meaning` over dictionary `sense_meaning`); Persian RTL; tri-state
    noun plural rendering; the language-bearing `/vocab/gloss` POST/DELETE
    endpoint; stable picker semantic refs; immutable dictionary asset token;
    stale-token HTTP 409 `dictionary_changed`; D47 dictionary
    activation/relink/rollback; and AGENTS R12/R13 runtime enforcement before
    browser integration.
  - **slice-8** (smoke work) repairs the `reference/smoke_test.py` baseline and
    owns the corresponding end-to-end D47 replacement and stale-picker smoke
    verification.
- **`reference/schema.sql` is deliberately stale** with respect to §6 and §10.
  It still shows `sense.gloss_en NOT NULL`, scalar `note.gloss_user`, and
  `note.status` without the resolver/meaning-state separation documented in §6.3;
  it has no `sense_meaning`, no `sense_meaning_derivation`, no
  `note_meaning_lang`, no `note_user_meaning`, no `lemma.plural_none`, no
  lemma/sense stable semantic refs, no `sense.source_ref`, no
  `note_dictionary_binding` relation, and no active dictionary version+SHA
  metadata, with numeric `lemma_id` / `sense_id` still appearing as if durable.
  That staleness is recorded here and in `docs/backlog.md` rather than repaired in
  this governance session, because a schema edit is implementation work and this
  session is forbidden from it. The documented mismatch is repaired by the
  respective owning alignment/runtime slices: slice-3 for PART-A/stage-01 shape,
  slice-7 for PART-B/runtime persistence, and slice-8 for the corresponding
  end-to-end smoke verification. A cold reviewer should read the mismatch as
  *blocked and documented*, not as an undetected contradiction.
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

**Reviewer:** fresh cold-review orchestrator session, 2026-08-19, repo-only
context per WORKFLOW §7 / PROMPTS.md §ADR cold review.

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** The multilingual direction,
Gate-2 position, German target-language boundary, zero-runtime-LLM rule, and the
accepted-but-paused slice-3 treatment are sound. The blockers below are contract
gaps that make parts of the ADR non-executable as written.

### O1 — BLOCKING. The invented `needs_gloss` redefinition collapses resolution state and meaning-availability state.

The existing resolver/ref contract uses `resolved`, `derived_compound`, and
`needs_gloss` to describe **resolution outcome** (ADR-0001 §10; `app/resolve.py`),
and `reference/schema.sql` gives `note.status` the same domain. ADR-0004 §6.3
redefines that same persisted status by **availability of meaning text in the
selected languages**. Those are independent state machines. A dictionary-resolved
`Haus` with selection `{fa}` and no Persian row must become `needs_gloss` under
§6.3 even though resolution succeeded. Conversely, an unresolved stub given a
user-authored meaning in its selected language no longer satisfies §6.3's
`needs_gloss` definition, but it is neither `resolved` nor `derived_compound`. A
`meaning_langs` patch can also flip meaning availability without changing the
resolver result, yet no recomputation/transition rule is defined. D32's rationale
that a non-empty selected set keeps “a card always shows some meaning” true is
therefore false for the very `needs_gloss` case this ADR preserves.

*Remedy:* separate resolution state from meaning-availability/completeness state
(or define a replacement status model with equally explicit semantics), say which
state is persisted, define transitions/recomputation on selected-language changes,
user-meaning changes, and dictionary-version changes, and amend ADR-0001/ADR-0002
and resolver/API expectations consistently. The drafting session's invented
decision (a) is **not accepted in its current form**; the revision must explicitly
decide whether the learner-facing condition means “no selected meaning exists” or
“one or more selected meanings are missing” rather than overloading resolver
status by implication.

**Resolution — 2026-08-19 revision:** RESOLVED by D43 and the corresponding
ADR-0001/ADR-0002 pending supersession amendments. `note.status` remains the
persisted resolver outcome (`resolved | derived_compound | needs_gloss`);
selected-language availability is instead the computed, non-persisted
`meaning_state = none | partial | complete`. The learner-facing "needs meaning"
condition is `meaning_state='none'`. Language-selection, user-meaning and
dictionary-coverage changes recompute meaning state without mutating resolver
status.

### O2 — BLOCKING. `meaning_langs` is well-defined, but localized user-authored meanings have no executable API or persistence contract.

The drafting session's invented decision (b) is sound on its own: omission means
no mutation on a reused note, `null`/`[]` are invalid, and creation requires an
explicit non-empty set with no API default. However, ADR-0002 §4 still permits
exactly `gloss_user: string | null -> note.gloss_user`, only for a revalidated
`needs_gloss` selection. ADR-0004 §6.3 simultaneously requires a user-authored
meaning to record **which language it is written in** while deferring the exact
shape to an implementation slice. That is not an implementation detail: it is the
public commit/edit contract and the PART-B data model.

The current rules are also behaviorally inconsistent. With selected
`{de,en,fa}` and only an English source meaning, §6.3 calls the note resolved, so
ADR-0002's `gloss_user` rule rejects an attempt to add the missing German or
Persian meaning. If no selected meaning exists and the user adds one, the new
status definition then makes the note resolved, preventing a second language from
being added through the same path. One scalar `note.gloss_user` cannot represent
multiple language-tagged user meanings.

*Remedy:* define the exact language-bearing request shape for user meanings
(`/vocab/cards` and `/vocab/gloss` if that endpoint remains), the normalized or
otherwise unambiguous PART-B persistence shape, add/update/clear semantics,
validation and transaction rules, and how the still-English-only D10 contribution
path interacts with it. Explicitly supersede ADR-0002 §4's scalar `gloss_user`
contract and its smoke-baseline expectations instead of leaving the slice to invent
a public API.

**Resolution — 2026-08-19 revision:** RESOLVED by D44. User-authored meanings
are normalized as one `note_user_meaning` row per note/language; `/vocab/cards`
uses an explicit language-keyed `user_meanings` override with exact
add/update/delete/validation/transaction semantics; `/vocab/gloss` becomes a
language-bearing edit API independent of resolver status; scalar
`note.gloss_user` is superseded; D10 contribution remains explicitly
English-only.

### O3 — BLOCKING. Per-row provenance is required, but generated-row derivation has no data carrier.

D36's conceptual `sense_meaning` target carries only `source` and `license`. D38
then requires a generated localized meaning that was derived from source-backed
input to record that derivation so the upstream CC BY-SA obligation remains
traceable, while also requiring `source='llm_generated_vN'` for clean rollback and
forbidding generated rows from masquerading as Wiktionary. Those requirements
cannot all be represented by the target row as written: `source` must remain the
generation marker, `license` is not a source-row reference, and `sense.source` /
`sense.license` describe provenance of the semantic distinction rather than the
localized text used as generation input. AGENTS R11 therefore asserts traceability
that the proposed relation cannot reconstruct.

*Remedy:* define an explicit localized-meaning derivation/provenance carrier
(e.g. an upstream/source reference field or normalized derivation relation), its
cardinality and license semantics, and amend the conceptual target plus R11 wording
so a generated row can identify both its generation version and every
source-backed localized row it derives from. Preserve deletion/reversal by the
versioned generation marker.

**Resolution — 2026-08-19 revision:** RESOLVED by D45 and amended AGENTS R11.
Generated localized meanings retain their versioned `llm_generated_vN` source
marker while a normalized `sense_meaning_derivation` relation records every
source-backed localized text input used in derivation. Cardinality, license
traceability, validation, and rollback semantics are now explicit.

### O4 — BLOCKING. D43 leaves `derived_compound` meaning availability undefined and can disagree with rendering.

D43 preserves `note.status = resolved | derived_compound | needs_gloss` but
defines a selected language as available only when either a note-local
`note_user_meaning` exists or the note has a direct dictionary `sense_id` with a
matching `sense_meaning`. That is not exhaustive for the retained
`derived_compound` outcome. ADR-0001's resolution ladder produces derived
compounds from dictionary-backed components, and its still-retained compound
gloss/decomposition path derives learner meaning from those component meanings.
A derived-compound note need not have its own direct `sense_id`.

The resulting state machine is ambiguous: the card may have a dictionary-derived
compound/component meaning to render while D43 is forced to report
`meaning_state='none'`; alternatively an implementation must invent an
unrecorded third availability rule. Multilingual meanings make the gap larger
because it is also undefined which component localized meanings establish
availability for DE, EN or FA, and what happens when only some components have
text in a selected language.

*Remedy:* define one executable `derived_compound` meaning contract. If
component-derived localized meanings remain part of v1, specify
language-by-language availability, deterministic component/sense selection and
ordering, behaviour when only some component meanings exist, note-local
`note_user_meaning` precedence, rendering, and source/license attribution; state
whether the derived text is computed or persisted while preserving the
rendered-faces-never-stored rule. If v1 intentionally excludes dictionary-derived
compound meanings from selected-language availability/rendering, explicitly
supersede the conflicting ADR-0001 compound-gloss/decomposition behaviour
instead. In either design, `status='derived_compound'` remains a resolver outcome
and scheduling remains independent.

**Resolution — 2026-08-19 revision:** RESOLVED by D46 and the D43/D44/D47
integration in §6. Derived-compound learner meanings remain in v1 as a computed,
language-by-language component decomposition over one persisted ordered stable
component/sense binding vector. A note-local user meaning wins for its language;
otherwise every component must have localized text for that language or the
derived dictionary block is unavailable. Component order, component/sense
selection, localized-row selection, rendering, provenance, dictionary-replacement
interaction and all-components-or-none availability are deterministic. No
composed compound learner-meaning row or rendered face is persisted;
`status='derived_compound'` remains solely a resolver outcome and scheduling
remains independent.

### O5 — BLOCKING. D43's dictionary-replacement recomputation has no safe cross-version dictionary-identity contract.

D43 requires `meaning_state` to be recomputed automatically from current data on
the next read after a dictionary asset/version replacement. Its dictionary
availability predicate dereferences the note's persisted numeric `sense_id`.
The repository, however, treats `dictionary_vN.sqlite` as a versioned,
replaceable/disposable asset while PART-B notes persist numeric `lemma_id` and
`sense_id`; `lemma_text` is explicitly denormalized so user data survives
dictionary rebuilds. No accepted contract guarantees that those numeric IDs
identify the same lemma/sense in every future dictionary version, and no
activation-time relink step is required before D43 reads the replacement asset.

Consequently a replacement can make an old numeric `sense_id` disappear or,
more dangerously, make the same integer identify a different new sense. D43
cannot then distinguish genuine meaning-coverage change from stale identity, so
automatic recomputation can return a false `none`/`partial` state or expose
meaning text for the wrong sense while leaving resolver status untouched.

*Remedy:* define the cross-version identity/activation contract before D43 is
accepted. Either guarantee and gate stable persisted dictionary identities across
all asset versions, or persist/use a stable semantic reference and perform a
fail-closed relink/rebind of `lemma_id`/`sense_id` before a replacement asset is
made visible to reads. Define the disappeared/ambiguous-sense case explicitly:
user-authored meanings survive; no stale numeric ID may bind to an unrelated
sense; resolver status changes only through its separately owned
re-resolution/relink rule; and `meaning_state` is computed only against a
successfully validated binding. Asset activation must not expose a mixed
old-identity/new-asset state.

**Resolution — 2026-08-19 revision:** RESOLVED by D47. Numeric dictionary
`lemma_id`/`sense_id` are explicitly per-asset caches, not durable identity.
PART A gains deterministic stable lemma/sense semantic references; PART B keeps
durable semantic bindings and active dictionary version+SHA metadata. A candidate
dictionary is checksum/integrity/stable-ref validated, then every binding is
relinked by exact stable ref inside one user-DB transaction while reads/writes are
excluded; only after that transaction commits is the already-open candidate made
visible. Missing direct senses or compound components fail closed to an unbound
resolver state without losing user meanings/history, ambiguous duplicate refs
abort the entire activation, old numeric IDs are never match keys, stale picker
asset tokens are rejected before writes, and failed activation leaves the
previous asset active. `meaning_state` consults only a validated current binding.

### Cold review #3 — FINAL CONVERGENCE REVIEW — APPROVED

**APPROVED — remove NEEDS COLD REVIEW.**

The final convergence review found no qualifying severe blocker under
WORKFLOW.md §7 / AGENTS G7. O1–O5 and all resolution records remain preserved.
ADR-0004 is accepted and frozen. Implementation may resume against D32–D47.
There is no ADR-0004 review #4.
