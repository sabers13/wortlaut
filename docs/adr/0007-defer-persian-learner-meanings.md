# ADR-0007 — Defer Persian learner meanings from v1

**Status:** NEEDS COLD REVIEW.

**Lineage:** This is a genuinely new architectural decision made after
ADR-0004 and ADR-0006 were accepted and frozen. It begins a new cold-review
lineage under WORKFLOW §7 / AGENTS G7; it does not reopen, reset, or consume
reviews in the ADR-0004 or ADR-0006 lineages.

**Amends:**
- ADR-0004: D32, D35, D36, D38, D41, D42, D43, D44, §5, §6, §7, §8, §10, §12,
  §13;
- ADR-0006: D57–D64, D70, D71, §§3, 6, 7, 8, 9, 10.

**Preserves unchanged:**
- ADR-0001 in full (except where superseded by earlier accepted ADRs);
- ADR-0002 in full (standalone service, app factory C1, loopback R8, request
  guards R12);
- ADR-0003 in full (confidence ratings, FSRS mapping, append-only `review_log` R6);
- ADR-0004:
  - D33 (German learner meaning quality and style);
  - D34 (English stays source-first);
  - D36 (language-neutral `sense` and normalized `sense_meaning` relation);
  - D37 (maintainer-only offline LLM roles);
  - D39 (tri-state noun plural on back of cards);
  - D40 (inflected forms resolve to canonical lemma);
  - D45 (derivation edges for generated meanings);
  - D46 (derived-compound conservative component decomposition);
  - D47 (stable semantic references, atomic dictionary activation/relink);
- ADR-0005 in full (pronunciation audio precedence, Piper TTS prerequisite,
  user recording/upload lifecycle);
- ADR-0006:
  - D65 (German source-first conservative positive eligibility filter);
  - D66 (one semantic enrichment item equals one model request);
  - D67 (bounded, deterministically partitioned OpenAI Batch transport);
  - D68 (manifest-first upload, correlation, durable state, exact-one
    ambiguous reconciliation);
  - D69 (no monitoring waste / asynchronous retrieval discipline).

**Decision IDs:** D72–D81.

---

## 1. Context and historical evidence

### 1.1 Context

ADR-0004 broadened the flashcard meaning model from English-only glosses to
multilingual learner meanings in German, English, and Persian (`{de, en, fa}`).
ADR-0006 subsequently established a source-first cascade for Persian translations
(attempting direct English-Wiktionary relations first, followed by an optional
German-Wiktionary cross-edition bridge) and specified bounded OpenAI Batch
transport for maintainer-operated offline generation of remaining gaps.

During the execution of Slice 6 (offline enrichment), thorough source
investigations demonstrated that:
1. Direct English-Wiktionary translation sections for German lexemes do not
   consistently provide exact sense-level Persian translation bindings;
2. German-Wiktionary cross-edition bridging lacks documented exact sense
   foreign-key structures (`senseid` links), making deterministic non-guessing
   sense alignment unachievable;
3. Falling back to universal LLM generation for Persian across the full vocabulary
   queue would require substantial recurring model costs, complex multilingual
   prompt engineering, Persian-specific Unicode/ZWNJ verification, and Right-to-Left
   (RTL) UI/rendering support.

Following prototype canary execution and evaluation of operational complexity,
the product owner made a deliberate architectural decision: **REMOVE Persian from
the active v1 flashcard product scope**.

Persian is deferred as a potential future feature. For v1, the active learner
meaning languages are restricted strictly to **German** and **English**.

### 1.2 Preservation of historical audit record

This ADR reduces forward product scope without rewriting history. The following
historical facts and artifacts remain preserved as immutable audit records:
- The initial multilingual conception and review lineage in ADR-0004;
- The source-first cascade architecture and Batch specifications in ADR-0006;
- The Slice-6 primary and secondary source investigation reports (including
  `slice-6-secondary-persian-source-investigation.md`), which proved that
  deterministic exact-sense source mapping was unavailable;
- The Slice-6 Attempt-1 paid canary execution (2026-08-21), which spent exactly
  **USD 0.0008764** on 5 test items;
- The Attempt-1 canary prompt-contract failure and subsequent Attempt-2 prompt
  repair design;
- The committed Slice-6 development branch (`slice/6` at
  `430cfa10e928b341e0c8c6342321cc50b6b2bd57`).

These historical records provide evidence of the technical investigation and
financial auditability. They impose **no forward Persian implementation obligation**.
No further Persian API calls or expenditures are authorized.

---

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D72 | **Active learner meaning languages in v1 are German and English only.** A German vocabulary note supports learner meanings strictly in `{de, en}`. The legal non-empty per-note selection subsets are exactly `{de}`, `{en}`, and `{de, en}`. Persian (`fa`) is removed from active product scope and deferred. German remains the sole target vocabulary language. | Deliberate product-scope reduction. Concentrates resources on high-fidelity German and English learner glosses while eliminating multilingual operational overhead in v1. |
| D73 | **Persian learner meaning is deferred from v1.** All active v1 requirements for Persian dictionary/source ingestion, cross-edition bridging, LLM generation, Persian QA, `bulk_fa` pipelines, Persian checkpoints, canaries, Persian Unicode/ZWNJ validation, Persian RTL rendering (`dir="rtl"`, `lang="fa"`), Persian API fields, and Persian runtime tests are removed. No Persian provider calls or spending are authorized. Future reintroduction requires a fresh explicit owner decision and architectural review. | Prevents dead code, unmaintainable heuristics, and unnecessary API expenditure. |
| D74 | **Normalized localized-meaning architecture is preserved for DE and EN.** The `sense` table remains language-neutral. Localized meanings are stored in `sense_meaning` keyed by `(sense_id, language, kind, ord)` with per-row provenance (`source`, `license`). Parallel `gloss_en`/`gloss_de` columns remain rejected. Normalized user-authored meanings `(note_id, language)` in `note_user_meaning` support `{de, en}`. `sense_meaning_derivation` and D45 derivation tracking continue for generated DE/EN rows. | Schema normalization and per-row provenance are sound engineering foundations that cleanly accommodate DE and EN without schema restructuring. |
| D75 | **German learner meanings remain source-first with conservative positive eligibility; English remains source-first.** German learner meanings follow ADR-0004 D33 (synonym first, short A2–B1 explanation otherwise, preserving sense). Existing source-backed German rows are retained without generation only when satisfying ADR-0006 D65 conservative positive eligibility; any uncertainty creates one isolated `de_learner_meaning` request. English remains source-first (ADR-0004 D34); only missing English meanings generate enrichment. | Maintains high pedagogical quality for German learner glosses while preventing unnecessary model generation where licensed source text is already concise and accurate. |
| D76 | **Stage 03 is purely deterministic DE/EN queue construction without Persian source cascade.** Stage 03 reads the accepted Stage-02 dictionary asset, evaluates source-backed English and German localized meanings, identifies remaining enrichment gaps, and materializes a deterministic queue for missing English meanings and required German learner meanings. All Persian source extraction, bridging, source-acceptance packets, and missing-Persian owner STOP gates are removed from the active pipeline. | Eliminates non-functional source-cascade complexity from the build pipeline. |
| D77 | **Stage 04 generated work is bounded to DE and EN only.** Offline generation consists solely of: (A) missing English meanings, (B) German learner meanings, (C) deterministic validation of generated DE/EN rows, and (D) selective stronger-model semantic QA/correction on generated DE/EN. No Persian job class exists in the active pipeline. | Stage-04 scope is narrowed to essential DE/EN enrichment. |
| D78 | **Quality-preserving Batch architecture is preserved for DE/EN production runs.** ADR-0006 D66–D69 remain binding: one semantic item per request, stable semantic IDs, synchronous/Batch semantic equivalence, bounded deterministic JSONL manifests, manifest-first upload and correlation, durable provider batch IDs, fail-closed `SUBMISSION_AMBIGUOUS` with exact-one owner reconciliation, and no monitoring waste. | Batch processing remains valuable for cost-effective, durable, and restartable generation of DE/EN items. |
| D79 | **Production gate is updated for DE/EN scope.** The owner authorization gate for paid Stage-04 production (ADR-0006 D71) removes Persian source-acceptance packets and Persian coverage/gap decisions. Production requires: ADR-0007 accepted/frozen, measured DE/EN source-first queue, accepted bounded German canary and selective QA, verified current Batch limits/correlation capabilities, prepared partition plan/manifests, current cost estimate, and explicit orchestrator authorization. | Aligns deployment criteria with the DE/EN scope while preserving strict financial and quality controls. |
| D80 | **Runtime and render contract (Slice 7) is DE/EN only.** Runtime meaning selection, note-level meaning state (`meaning_state`), `/vocab/cards` display, `/vocab/gloss` user-meaning editing, and export support `{de, en}` only. Persian RTL handling, `dir="rtl"`, `lang="fa"` attributes, and Persian browser tests are removed from active requirements. German grammar (gender, plural, principal parts, audio) renders independently of meaning selection. | Simplifies runtime API and frontend renderer by avoiding bidirectional text layout complexity in v1. |
| D81 | **Historical investigations, canaries, and spend are preserved as audit evidence.** Historical investigation of direct EN→FA translations and DE→FA Wiktionary bridges, the finding that acceptable exact sense-level FA source mapping was not established, the D64 LLM fallback preparation, the Attempt-1 paid canary ($0.0008764 spend) and prompt repair are preserved as immutable historical record. They impose no forward implementation obligation. | Complete audit transparency and adherence to AGENTS G5/G8. |

---

## 3. Active meaning languages and normalized data model (D72, D74)

### 3.1 Active languages

In v1, learner meanings are supported in German (`de`) and English (`en`) only.
Every vocabulary note specifies a non-empty subset of active languages:
- `{de}`: Monolingual German learner gloss/synonym only;
- `{en}`: English gloss/translation only;
- `{de, en}`: Both German learner gloss and English translation.

Selecting Persian (`fa`) is invalid in v1. Requests providing `fa` in language
selections or user-meaning updates fail validation with HTTP 422 / 400.

### 3.2 Normalized localized-meaning relations

The normalized schema established in ADR-0004 PART A and PART B is retained:
- `sense` is the language-neutral semantic anchor;
- `sense_meaning` holds localized texts with schema `(sense_id, language, kind, ord, text, source, license)` where `language IN ('de', 'en')`;
- `note_user_meaning` stores user-authored overrides per `(note_id, language)` where `language IN ('de', 'en')`;
- `sense_meaning_derivation` records derivation inputs for generated DE/EN rows;
- `note_meaning_lang` (or the equivalent normalized selection table) stores selected languages from `{'de', 'en'}`.

Reverting to parallel columns (`gloss_en`, `gloss_de`) is explicitly rejected.
The normalized model provides clean separation of concerns, per-row license
attribution (AGENTS R11), and structured extensibility without schema migrations.

---

## 4. German and English learner meanings (D75)

### 4.1 German learner meanings

German learner meanings follow ADR-0004 D33 and ADR-0006 D65:
1. **Style and pedagogical goal:**
   - Prefer one simple, common German synonym when it accurately preserves the sense;
   - Otherwise, provide one short, learner-friendly German explanation;
   - Comprehension level targeted at approximately A2–B1 where practical;
   - Never substitute an easier word that alters the semantic sense.
2. **Source-first positive eligibility:**
   - Existing source-backed German localized meanings from Wiktionary are evaluated
     against the conservative positive eligibility predicate defined in ADR-0006 §4
     (exact source-sense attachment, explicit synonym or definition/gloss relation,
     length/token/punctuation bounds, and absence of forbidden meta-patterns);
   - Only rows passing all checks are retained without generation;
   - Any uncertainty or unprovable property falls through to create one isolated
     `de_learner_meaning` generation request.

### 4.2 English meanings

English meanings follow ADR-0004 D34:
- Source-backed English glosses from the canonical English Wiktionary parse remain
  authoritative;
- LLM generation is utilized only to fill genuine gaps where canonical English
  meaning text is missing.

---

## 5. Offline dictionary build pipeline (Stages 03–05) (D76, D77)

### 5.1 Stage 03 — Deterministic DE/EN queue construction

Stage 03 operates as an offline, network-free, deterministic process reading the
accepted Stage-02 dictionary asset:
1. Evaluates canonical senses and existing source-backed `sense_meaning` rows for `de` and `en`;
2. Applies the D65 positive eligibility filter to source-backed German rows;
3. Identifies missing English meanings and required German learner meanings;
4. Materializes a deterministic JSONL enrichment queue containing only `de_learner_meaning`
   and missing `en_meaning` jobs;
5. Assigns deterministic item IDs derived from stable semantic refs (`lemma.semantic_ref`,
   `sense.semantic_ref`, target language, job class, source context);
6. Entirely omits Persian source ingestion, German-Wiktionary DE→FA bridging,
   source-acceptance packets, and missing-Persian owner STOP gates.

### 5.2 Stage 04 — Maintainer-operated offline generation

Stage 04 executes offline generation for queued DE and EN items:
1. **Job classes:**
   - `de_learner_meaning`: Generate simple German synonym or short A2–B1 explanation;
   - `en_meaning`: Fill missing English translation/gloss;
2. **Item isolation:** Each model request contains exactly one semantic sense context;
3. **Deterministic validation:** Generated texts are validated for schema conformity,
   correct language/script (German/English Latin alphabet, no empty/echoed text,
   no forbidden prefixes/meta-commentary);
4. **Selective QA:** Stronger-model semantic review is routed only for flagged items
   plus a small deterministic audit sample;
5. **Attribution and rollback:** Generated rows are tagged `source='llm_generated_v1'`
   with derivation edges recorded in `sense_meaning_derivation`.

### 5.3 Stage 05 — Packaging

Stage 05 packages the final SQLite dictionary asset:
1. Combines source-backed and generated `sense_meaning` rows for `de` and `en`;
2. Builds search indexes and stable semantic reference lookups;
3. Generates complete, accurate attribution metadata reflecting English and German
   sources under CC BY-SA and generated row markers;
4. Verifies database integrity and row count invariants before freezing the asset.

---

## 6. Quality-preserving Batch processing and paid durability (D78, D79)

ADR-0006's robust Batch architecture is fully preserved for DE and EN generation:
- **Logical equivalence:** Synchronous Responses and Batch requests share identical
  prompts, contexts, schemas, and validation rules;
- **Deterministic manifests:** Queue items are partitioned into bounded JSONL manifests
  respecting verified provider limits, with deterministic `custom_id`s;
- **Manifest-first durability:** Manifest SHA-256 and correlation IDs (`batchcorr:v1:<sha256>`)
  are persisted before upload;
- **Fail-closed reconciliation:** `SUBMISSION_AMBIGUOUS` states are reconciled solely
  by exact-one correlation matching authorized by the owner/orchestrator;
- **No polling waste:** Single submission with subsequent status retrieval at explicit
  decision points.

### Production authorization gate

Prior to executing a paid production Stage-04 run, the following prerequisites
must be satisfied:
1. ADR-0007 accepted and frozen;
2. Measured Stage-03 DE/EN queue size and cost estimate reported;
3. Accepted bounded German canary and selective QA run;
4. Current provider Batch limits and correlation capabilities verified;
5. Prepared partition plan and manifests persisted;
6. Explicit owner/orchestrator authorization to proceed.

---

## 7. Runtime, render, and API contract (Slice 7) (D80)

### 7.1 Meaning selection and display

- The note display contract supports subsets of `{de, en}` only;
- Meaning sections render the selected language(s) in deterministic order (`de` then `en`);
- If a note lacks dictionary text for a selected language, user-authored meanings
  take precedence; if neither exists, `meaning_state` computes to `partial` or `none`
  under ADR-0004 D43;
- German grammar (article/gender, noun plural, principal parts, IPA, audio) renders
  independently on the card back and is never hidden by meaning selection.

### 7.2 Removal of Persian presentation requirements

- Right-to-Left (RTL) layout handling is removed from v1 renderer requirements;
- No HTML blocks require `dir="rtl"` or `lang="fa"`;
- User meaning endpoints (`/vocab/gloss`, `/vocab/cards`) reject `language='fa'`;
- Test suites in Slice 7 and Slice 8 test German and English meaning rendering,
  user overrides, and availability states without Persian test cases.

### 7.3 Contribution policy

Under ADR-0004 D42, user gloss contribution (`gloss_contribution`) remains
restricted to English single-vote contributions as originally specified in ADR-0001 D10.
No multi-language contribution or voting mechanism is introduced for v1.

---

## 8. Historical record and reintroduction policy (D73, D81)

### 8.1 Historical record

The repository preserves the complete record of Persian investigations:
- Total historical paid spend for Persian canary exploration: **USD 0.0008764**;
- Technical evidence that Wiktionary translation sections lacked exact sense
  foreign-key alignment;
- All historical reports and canary artifacts in repository history and scratch
  locations remain intact.

### 8.2 Future reintroduction policy

Persian may be reconsidered in a future major version after v1 delivery.
Reintroduction will require:
1. A new, explicit owner decision and architectural proposal (ADR);
2. A proven source mapping methodology or explicitly budgeted and approved LLM
   generation plan;
3. Full specification of Persian-specific validation, script handling, and RTL
   rendering;
4. Complete provenance and licensing review.

No dormant or hidden code paths shall be left in the v1 codebase to automatically
reactivate Persian.

---

## 9. Consequences

### Positive
- **Drastic scope and complexity reduction:** Eliminates Persian source parsing,
  cross-edition bridging heuristics, complex Persian prompt engineering, and RTL UI
  rendering from v1.
- **Cost control:** Eliminates hundreds of thousands of potential Persian generation
  calls, avoiding unnecessary API spend.
- **Fast-tracked v1 completion:** Unblocks Slice 6 and Slice 7 by focusing
  implementation on German and English.
- **Clean architectural preservation:** Retains the normalized `sense_meaning`
  architecture, stable semantic identity, derivation tracking, and robust Batch
  infrastructure.

### Negative / Trade-offs
- Learners whose native language is Persian cannot use Persian meanings in v1 and
  must rely on German learner glosses and/or English translations.

### Neutral
- Historical spend of USD 0.0008764 is accounted for and retired.
- Target vocabulary language remains German.

---

## 10. Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| Retain Persian via automatic full-dictionary LLM generation | Incurs high API costs, complex QA requirements, and substantial prompt-engineering overhead for v1. |
| Retain Persian via fuzzy/lemma-level Wiktionary mapping | Violates ADR-0004/ADR-0006 semantic fidelity; polysemous words collapse into wrong meanings. |
| Revert schema to parallel `gloss_de` and `gloss_en` columns | Destroys per-row license attribution, derivation tracking, and clean extensibility. |
| Keep dormant Persian code and RTL handling in v1 | Violates YAGNI; creates dead code paths, maintenance burden, and testing overhead. |

---

## 11. Supersession record — ACTIVE on acceptance

This table specifies the exact supersessions enacted by ADR-0007 upon approval
and freezing. Historical ADR bodies remain unmodified.

| Historical provision | Active ADR-0007 replacement |
|---|---|
| **ADR-0004 D32** (Three meaning languages `{de, en, fa}`) | Superseded by **D72**: Two active meaning languages `{de, en}` in v1. |
| **ADR-0004 D35** (Persian first-class optional meaning & RTL) | Superseded by **D73**: Persian deferred from v1; RTL presentation removed from v1 renderer. |
| **ADR-0004 D36** (Normalized meaning relation examples mentioning FA) | Clarified by **D74**: Normalized relation is retained, active languages restricted to `{de, en}`. |
| **ADR-0004 D38** / **§8** (Stage 04 includes Persian creation) | Superseded by **D77**: Stage 04 generated work is DE and EN only. |
| **ADR-0004 D41** / **§10** (Card meaning section renders selected DE/EN/FA & RTL) | Superseded by **D80**: Meaning section renders selected DE/EN only; no RTL markup. |
| **ADR-0004 D42** (Multilingual contribution policy across 3 languages) | Clarified by **§7.3**: Contribution remains English-only per ADR-0001 D10. |
| **ADR-0004 D43** (`meaning_state` across DE/EN/FA) | Clarified by **D80**: `meaning_state` computes availability over selected subset of `{de, en}`. |
| **ADR-0004 D44** (`note_user_meaning` for DE/EN/FA) | Superseded by **D74**: `note_user_meaning` supports `language IN ('de', 'en')` only. |
| **ADR-0004 §5** (Persian generation and RTL specification) | Superseded by **D73**: Entire section deferred from v1. |
| **ADR-0006 D57–D64** / **§3** (Persian source cascade, bridge, packets, gates) | Superseded by **D73** and **D76**: Persian source cascade and owner gates removed from pipeline. |
| **ADR-0006 D70** (Persian source row validation and packets) | Superseded by **D73** and **D79**: FA validation/packets removed; QA applies to DE/EN only. |
| **ADR-0006 D71** (Production gate FA coverage prerequisites) | Superseded by **D79**: FA source packets and gap decisions removed from production gate. |

---

## 12. Cold review

No cold review is performed in this drafting session. A fresh cold orchestrator
session must review this ADR under WORKFLOW §7 / AGENTS G7. Its first review is
the broad architecture challenge for this new ADR-0007 lineage.

### Cold review #1 — broad architecture challenge

*Pending dispatch to a fresh cold orchestrator session.*

#### O1 — BLOCKING. Historical paid-canary item accounting is materially incorrect.

**Concrete defect.** ADR-0007 §1.2 says the Slice-6 Attempt-1 paid canary
"spent exactly USD 0.0008764 on 5 test items." The committed Slice-6 report
records a different execution history: the authorized 50-item canary stopped
when generation item 4 returned and failed deterministic validation; generation
state was 3 completed + 1 rejected + 0 ambiguous/in-flight, and the contract
stopped before item 5. A separate HTTP 401 authorization failure was unbilled.
Attempt 2 performed no provider calls.

**Why blocking.** D81 makes the canary/spend history an immutable audit record.
Freezing an unsupported five-item paid-execution claim would make the
architecture's historical accounting materially false.

**Affected contract/files.** ADR-0007 §1.2, D81 and §8.1;
tasks/slice-6.report.md on the preserved slice/6 branch.

**Required remedy direction.** Preserve the exact known cumulative spend
USD 0.0008764, but record that four model-generation items actually returned
before STOP (3 completed, 1 rejected), item 5 was never sent after that STOP,
the separate 401 was unbilled, and Attempt 2 made zero provider calls. Do not
rewrite or delete historical evidence.

#### O2 — BLOCKING. The DE/EN scope wording can incorrectly close the physical language schema.

**Concrete defect.** ADR-0007 D74 / §3.2 describes sense_meaning and
note_user_meaning using `language IN ('de', 'en')`. Accepted ADR-0004 D36 /
§6.1 and D44 / §6.4 deliberately require no enumerating language CHECK and no
closed-list language foreign key in those normalized relations; the currently
supported language set is enforced by the build/API so a future language does
not require a schema migration. ADR-0007 also says it preserves that normalized,
migration-friendly architecture.

**Why blocking.** The current wording can reasonably be implemented as a
physical SQLite CHECK restricted to DE/EN, directly contradicting a preserved
accepted invariant and creating the future migration D36 explicitly rejected.
The owner decision to ship DE/EN only does not require physically closing the
schema.

**Affected contract/files.** ADR-0007 D74, §3.2 and its D36/D44 supersession
wording; accepted ADR-0004 D36 §6.1 and D44 §6.4.

**Required remedy direction.** State explicitly that `{de,en}` is the active v1
build/API domain, while the physical language columns remain open TEXT with no
closed enumerating CHECK or language-enum FK. The v1 API/build rejects `fa`.
Future Persian still requires a fresh explicit owner decision and architectural
review; no generic multilingual product scope is implied.

#### O3 — BLOCKING. ADR-0007 makes unsupported-language HTTP validation ambiguous.

**Concrete defect.** ADR-0007 §3.1 says requests supplying `fa` in language
selection or user-meaning updates fail with "HTTP 422 / 400". The accepted
ADR-0004 / ADR-0002 request contracts already require unsupported language codes
to fail semantic validation with HTTP 422 before any write.

**Why blocking.** Slice-7 cannot implement and test one deterministic API
contract while the new ADR permits two status codes for the same validation
condition. This is a direct forward API-contract contradiction, not an
implementation preference.

**Affected contract/files.** ADR-0007 §3.1 and D80; ADR-0004 D44 §6.4;
ADR-0002 picker/commit and language-bearing gloss validation contracts.

**Required remedy direction.** Unsupported `fa` in an otherwise structurally
valid v1 request must return HTTP 422 with zero writes. Do not broaden that
semantic validation condition to HTTP 400.
