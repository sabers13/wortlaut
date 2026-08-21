# ADR-0006 — Source-first Persian and quality-preserving batch enrichment

**Status:** ACCEPTED / FROZEN.

**Lineage:** This is a genuinely new architectural decision made after
ADR-0004 was accepted and frozen. It begins a new cold-review lineage; it does
not reopen, reset, or consume another review in ADR-0004's exhausted lineage.

**Amends:** ADR-0004 D35, D37, D38, §5, §7 and §8 as specified in
§10 below. ADR-0006's §10 supersession record is active. ADR-0004 remains
`ACCEPTED / FROZEN`; provisions not explicitly superseded by §10 remain binding.
ADR-0005 is not amended.

## 1. Context

ADR-0004 correctly required Persian to be bound to a disambiguated German sense,
not a surface spelling. It nevertheless made Persian generation the normal
Stage-04 path. The owner now requires source-backed Persian coverage to be
measured before any decision to generate a remaining gap.

The owner also requires a production cost-control mechanism for the genuinely
generated German/English work without weakening semantic isolation. Provider
batching is transport, not permission to put unrelated senses in one model
context.

This ADR makes no paid API call, runs no live stage, and fixes neither a model
name nor commercial price as architecture. Current OpenAI documentation describes
the Batch API as asynchronous JSONL work with `custom_id`, terminal/partial
result states, and an up-to-24-hour completion window; current provider/model
support must be checked immediately before paid use. See the
[Batch API reference](https://developers.openai.com/api/reference/resources/batches).

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D57 | **Persian is source-first from the canonical source.** The canonical persisted German-lexeme sense is rooted in the English-edition Wiktionary source sense: `source_namespace='wiktextract:enwiktionary'`, its exact persisted English-edition `source_ref`, and `semantic_ref=hash(lemma semantic identity, source_namespace, source_ref)`. Attempt Persian translation evidence attached directly to that exact source sense first; use optional German-Wiktionary DE→FA only through a proven exact cross-edition bridge; otherwise record an unresolved Persian gap. No automatic LLM fallback exists. | A source-backed translation is auditable and reversible without recasting a coverage gap as a model decision. |
| D58 | **A Persian source must pass eligibility and owner source acceptance.** An eligible product has explicit compatible redistribution terms; a reproducible, versionable offline artifact; recorded revision/date and SHA-256; deterministic Persian extraction; per-row provenance; and a non-guessing exact mapping to the canonical sense. Every candidate mapping also supplies an owner/orchestrator source-acceptance packet before its source-backed FA build is accepted. | Translation count alone cannot prove legal reuse or semantic fidelity. |
| D59 | **Imported Persian is sense-bound.** Lemma-only, ordinal-only, fuzzy, embedding, LLM, first-hit, and gloss-string-only matching are forbidden authoritative matches. Ambiguity produces no FA row. | `Schloss` / castle / `قلعه` and `Schloss` / lock / `قفل` must never collapse. |
| D60 | **A German-Wiktionary bridge is a semantic bridge, not a gloss lookup.** It requires the exact persisted English-edition canonical source sense → exactly one German-Wiktionary source sense → Persian relation(s) on that exact German source sense. It records both identities, artifact versions/digests, relation type, and mapping version, and fails closed unless the sense-level mapping is one-to-one. | Matching a familiar English or German string is not enough to prove its intended sense. |
| D61 | **Imported FA rows are source-backed and deterministically plural.** An exact source-sense mapping may retain zero, one, or many independently valid Persian translation strings. Deduplication is only within that exact mapped result set; each retained row carries the selected exact source provenance and deterministic `ord`. They never use `llm_generated_vN`; generated rollback never removes them. | R11 attribution and rollback remain truthful. |
| D62 | **A deterministic missing-Persian report and used source-acceptance packets are hard owner gates.** After source ingestion, report coverage and representative rejected/missing senses, then stop; coverage is not accepted until all used packets are explicitly owner/orchestrator-accepted. | The owner decides the policy for measured gaps, not a hidden fallback. |
| D63 | **Persian source ingestion precedes final LLM queue materialization.** The historical 480,221 `fa_translation` jobs are evidence only. The new queue has no automatic Persian jobs and receives only items that genuinely need generation, presently principally DE learner meanings and missing EN meanings. | A historical checkpoint or queue cannot re-authorize the superseded Persian path. |
| D64 | **A future Persian LLM fallback needs a new explicit authorization.** It may be considered only after D62 and must define the bounded count, model, estimate, prompt contract, classification/provenance, QA, checkpointing, and canary. Until then, Persian LLM jobs equal zero. | This preserves a future option without silently choosing it now. |
| D65 | **German learner meanings are source-first only under a conservative positive eligibility filter.** Retain an already exactly attached source-backed synonym or definition/gloss only when its explicit relation, structural bounds, and versioned forbidden-meta rule are mechanically proven. The predicate is not a CEFR or semantic judge; any uncertainty makes one independent German generation job. That job remains synonym-first, then a short approximately A2–B1 explanation, without sense change. | Do not spend money or create a duplicate where mechanically safe licensed wording already exists; spend more DE generation when safety is uncertain. |
| D66 | **One semantic enrichment item equals one model request.** Its deterministic context contains exactly one item. Multi-sense giant prompts, shared unrelated context, and one response responsible for multiple senses are prohibited. | Token savings may not trade away isolation, validation, or QA. |
| D67 | **Use OpenAI Batch as a conditional, bounded production processing mode.** When the configured model and required endpoint officially support Batch, compute stable item IDs independently of transport, sort them bytewise, verify current provider request-count/input-byte limits, and deterministically partition exact serialized JSONL bytes into independently durable manifests. Each record has a stable deterministic `custom_id`; result order is ignored and records rejoin solely through that ID. Missing, duplicate, or unknown IDs fail closed. | Batch changes transport/processing only, not the item contract. |
| D68 | **Batch paid-work durability is manifest-first, correlated, and fail-closed.** Before Batch create, persist the exact manifest/compatibility identity, upload identity/SHA-256, and `batchcorr:v1:<manifest-sha256>` correlation value; create with supported metadata. Persist the provider batch ID after a known submission. An ambiguous submission is never automatically resubmitted and may be reconciled only by owner/orchestrator-authorized exact-one matching. Per-record results become durable completed/rejected items independently. | Restart must neither duplicate a possibly billed batch nor lose valid partial work. |
| D69 | **No monitoring waste.** Submit once, persist the provider identity, and retrieve status/result only at a later explicit decision point or terminal retrieval. No continuously active worker or repetitive hours-long polling is required. | WORKFLOW §15 remains binding for asynchronous work. |
| D70 | **QA is selective and item-isolated.** Deterministic validation applies to generated DE/EN candidates; stronger QA gets every suspicious result plus a deterministic small audit sample. Optional Batch QA keeps one item per request. FA source rows receive deterministic integrity/provenance/sense/script/license checks and owner/orchestrator-accepted source-acceptance packets with bounded human review, never LLM QA. | Strong semantic review belongs where a model generated content, not where a source relation is being preserved. |
| D71 | **The production long run remains owner-gated.** ADR acceptance/freeze, all used owner-accepted source packets, accepted FA coverage/gap report and gap decision, measured DE queue, accepted German canary and QA, verified current Batch correlation/limit capabilities, prepared partition plan/manifests, current cost estimate, and explicit orchestrator authorization are all required before submission. | A passing canary proves feasibility, not authority to spend for production. |

## 3. Persian source cascade (D57–D64)

### 3.1 Deterministic cascade

For each canonical `sense.semantic_ref`, source ingestion evaluates this topology:

1. **Primary direct relation:** Persian translation evidence attached directly to
   the exact persisted English-edition canonical source sense;
2. **Secondary optional relation:** only when primary yields zero accepted rows,
   an exact English-edition canonical source sense → exactly one German-Wiktionary
   source sense bridge and Persian relation(s) on that exact German source sense;
3. otherwise, a persisted/reportable unresolved Persian gap.

The canonical identity is `wiktextract:enwiktionary`, its exact persisted source
ref, and the D47 semantic-ref tuple. The primary relation is not a bridge.
German Wiktionary is optional and fails closed. No step may infer a translation
from lemma spelling, source ordinal, English- or German-definition string,
first-hit, similarity search, embedding, or LLM. Missing, ambiguous,
contradictory, malformed, or unlicensed relations produce no source-backed FA row.

The source-ingestion result must be reproducible from recorded source artifacts
and deterministic extractor/mapping versions. It must not mutate the accepted
Stage-02 asset in place; it creates the next copy-on-write build input.

### 3.2 Source eligibility and feasibility record (D58)

No external source is accepted merely because it appears broad. Implementation
must record a candidate feasibility record before ingestion with the following
fields: name, upstream location, artifact format, license evidence, offline
reproduction route, source sense representation, stable artifact identity,
proposed deterministic mapping, and every unresolved uncertainty.

Before any candidate source-backed FA build is accepted, its feasibility record
becomes a source-acceptance packet delivered to the owner/orchestrator. It records
candidate/edition, artifact revision/date/SHA-256, source/license evidence,
extractor and mapping/bridge versions, exact accepted rule, mapped/
rejected-ambiguous/invalid/uncovered counts, deterministic human-sample rule,
and for each sample the canonical semantic/source identities, any bridged source
identity, relation chain, translation-record identity, retained text,
provenance/license, and extraction/mapping evidence. No arbitrary pass percentage
applies. The worker cannot self-accept it.

Current investigated candidates are deliberately **provisional**, not accepted
source products:

| Candidate | Upstream / format | License evidence | Sense relation and feasibility | Status / uncertainty |
|---|---|---|---|---|
| English Wiktionary EN→FA translations, extracted from a versioned `enwiktionary-<date>-pages-articles.xml.bz2` artifact | [Wikimedia dumps](https://dumps.wikimedia.org/); XML dump and reproducible Wiktextract projection | Same official Wiktionary dual-license evidence | Primary/direct candidate: usable only when the extractor/source artifact proves the Persian translation relation belongs to the exact persisted canonical English-edition source sense. | Candidate only. Dump/date, extractor version, template coverage, exact source-sense relation, text cleanup, and per-row license must be proven on a bounded fixture before acceptance. |
| German Wiktionary DE→FA translations, extracted from a versioned `dewiktionary-<date>-pages-articles.xml.bz2` artifact | [Wikimedia dumps](https://dumps.wikimedia.org/); XML dump, with a pinned date, upstream checksum and local SHA-256 | Same official Wiktionary dual-license evidence | Optional secondary candidate only: requires a deterministic exact one-to-one bridge from the persisted English-edition canonical source sense to one German-edition source sense, then relations on that exact German sense. | Not accepted. Missing or ambiguous bridge evidence rejects this path; no lemma, ordinal, gloss, fuzzy, embedding, or LLM bridge is allowed. |
| Kaikki pre-extracted Wiktionary JSONL | [Kaikki](https://kaikki.org/) publishes JSON extracted from Wiktionary, including German and English editions | It is an extraction convenience, not independent license evidence; obligations remain those of the underlying Wiktionary content | Useful only as a reproducibility convenience or comparison input after pinning its release/digest and proving it preserves required source/sense linkage. | Not a substitute for source acceptance; no row may claim Kaikki's convenience URL as the actual lexical license. |

Wiktionary's own parsing guidance says dumps are available as XML/SQL and warns
that templates make raw parsing difficult; that is why a successful complete
source mapping is an explicit implementation proof rather than an assumption.
See [Wiktionary parsing](https://en.wiktionary.org/wiki/Wiktionary:Parsing) and
[Wiktextract's dump/translation documentation](https://github.com/tatuylonen/wiktextract).

### 3.3 Exact sense alignment, translation sets, and the optional bridge (D59–D60)

The direct source relation must prove that each Persian translation belongs to
the exact persisted English-edition canonical source sense. The optional bridge
must prove both links:

```text
exact persisted enwiktionary canonical source sense
        -> exactly one dewiktionary source sense
        -> Persian translation relation(s) on that exact source sense
```

The bridge records both source identities, artifact versions/digests, relation
type, and mapping version; it cannot be inferred from strings and fails closed
unless its sense-level mapping is one-to-one.

Mapping uniqueness and translation cardinality are distinct. One exact mapped
source sense may yield zero, one, or many valid translations. Validate every
record independently for relation, provenance/license, Persian text/Unicode, and
extraction integrity. Deduplicate only within that exact mapped result set using:

```text
NFC(text) -> strip leading/trailing Unicode whitespace
          -> collapse each run of Unicode White_Space to one U+0020 SPACE
```

This key is duplicate-only: never use it for sense matching; do not casefold,
remove punctuation, translate/transliterate, normalize Arabic/Persian letters,
remove ZWNJ, or use edit/semantic similarity. For equal keys retain the row with
the lexicographically smallest stable provenance tuple identifying artifact,
source record, relation, and raw retained text. Sort retained rows by duplicate
key UTF-8 bytes, retained source text UTF-8 bytes, then that tuple; enumerate
`ord=0..N-1`. Primary rows are retained as their entire deduplicated set and
prevent secondary consultation; secondary is fallback-only, never additive.

### 3.4 Source-backed FA persistence (D61)

Every accepted imported row has `language='fa'`, a valid translation kind,
actual source text, actual source namespace, actual license, deterministic
ordinal/provenance, and artifact identity in build metadata. It is never marked
as generated and has no generated-row derivation edge. Stage-05 attribution must
include the actual FA source artifacts and their license obligations.

### 3.5 Coverage report and owner stop (D62)

After all accepted primary/secondary inputs, produce a deterministic
machine-readable report with at least:

```text
TOTAL CANONICAL SENSES: <n>
CANONICAL_ENWIKTIONARY_DIRECT_FA_COVERED: <n>
DEWIKTIONARY_BRIDGED_FA_ADDITIONAL_COVERED: <n>
TOTAL FA COVERED: <n>
FA STILL MISSING: <n>
FA COVERAGE PERCENT: <n>
AMBIGUOUS_DIRECT_RELATIONS_REJECTED: <n>
AMBIGUOUS_CROSS_EDITION_BRIDGES_REJECTED: <n>
INVALID/UNUSABLE SOURCE ROWS: <n>
```

Its representative missing-sense sample is deterministic and includes German
lemma, POS, canonical sense ref, source English meaning when present, source
German definition/context when present, and the precise non-acceptance reason.
Coverage is sense coverage, not translation-string count. The report is not
accepted until every used source-acceptance packet is explicitly accepted by the
owner/orchestrator. The report is then a STOP point. The owner may choose to leave gaps, authorize
another source investigation, or later authorize a separately bounded Persian
LLM policy. This ADR chooses none of those later paths.

### 3.6 Queue boundary and future Persian generation (D63–D64)

The historical Stage-03 `fa_translation` count and the five legacy in-flight
Luna canary items remain historical evidence. They are not a reusable queue,
checkpoint, source row, or production input. They must not be retried, migrated
to the final dictionary, or deleted.

After source ingestion, materialize a new deterministic queue identity/version.
It includes only generated DE/EN needs; it has zero automatic Persian requests.
If a later owner authorization proposes Persian generation, it must state exact
item IDs/count, model, estimated cost, prompt and output classification,
provenance marker, QA, checkpoint protocol, and bounded canary. It is a new
explicit decision, not a restart option.

## 4. German source-first learner meanings (D65)

For every canonical German semantic sense, inspect existing source-backed German
localized meanings before queue construction. The versioned predicate is a
positive eligibility filter, not a semantic judge or CEFR classifier. A row is
retained without generation only when it is already exactly attached under an
accepted exact source relation (with the same fail-closed bridge rule if another
edition supplies it), its explicit relation is `synonym` or `definition/gloss`,
it has no unresolved ambiguity, and it has no URL, wiki/template/HTML/XML markup,
line break, tab, bidi/control or unexplained format control, or forbidden meta
pattern. The v1 case-insensitive forbidden set includes `siehe`, `vgl.`,
`vergleiche`, `form von`, `flexionsform`, `plural von`, `singular von`,
`abkürzung`, `kurz für`, `wortherkunft`, and `etymologie`.

Synonyms require explicit synonym relation, 1–4 whitespace-delimited tokens,
1–40 Unicode scalar values after outer trim, and no sentence-terminal `.`, `!`,
or `?`. Definitions/glosses require explicit definition/gloss relation, 2–16
tokens, at most 100 scalar values after trim, one line, and at most one `.`, `!`,
or `?`, only as final punctuation. The literal rule table may be versioned but
may not silently weaken. These bounds do not establish learner usefulness or
A2–B1. Any unprovable requirement is uncertain and falls through to generation.

If no retained row satisfies it, make one isolated `de_learner_meaning` request.
The request first seeks one simple/common sense-preserving German synonym; only
then a short learner-friendly explanation at approximately A2–B1 where practical.
The original source row stays untouched and any generated row retains its
versioned generated marker and D45 derivation edges.

## 5. Quality-preserving Batch processing (D66–D69)

### 5.1 Logical request contract

One enrichment item has exactly one stable identity, deterministic source context,
model role occupant, prompt/pipeline version, strict response schema, validation,
and QA criteria. A synchronous Responses call and a Batch input record for that
item must have the same logical request contract.

Batch input is a collection of independent records, one per item. A record's
`custom_id` derives deterministically from the enrichment item identity. The
record body supplies only that item's context and schema. Output order is never
semantic: results rejoin only by `custom_id`; unknown, duplicate, missing, or
schema-incompatible IDs reject the affected manifest fail-closed.

No request may contain a list of unrelated senses to reduce prompt tokens, and
no response may be responsible for several independent meanings. Provider Batch
therefore changes neither prompt semantics, role, source context, schema,
identity, validation, QA, nor final ordering.

### 5.2 Conditional use and durability

Use Batch for a large production DE/EN generation run only after confirming that
the configured production model and the required endpoint currently support the
Batch contract. If not, STOP and report. Do not silently change models, use a
giant prompt, or accept synchronous full-run cost without orchestrator approval.

Before preparing production, compute stable enrichment item IDs independently of
transport, bytewise-sort pending eligible IDs, verify the provider's current
request-count and input-file-byte limits, persist those observed limits as
operational metadata, and partition the exact serialized JSONL UTF-8 byte stream.
Include JSONL newline bytes; append an item only while both limits remain met; an
item that cannot fit an empty legal manifest is a STOP. Persist the complete
partition plan and every manifest before submission. Manifest identity derives
from exact ordered item IDs, serialized content, and compatibility identity;
ordinal is convenience only. Transport grouping cannot change item ID, prompt,
context, schema, model role, validation, QA, or final meaning identity.

Before attempting a Batch submission, atomically persist each deterministic
manifest's identity/SHA-256, exact `custom_id`s/item IDs, model role,
prompt/pipeline and response-schema versions, output classification, provider
limits, and state. State is at least:

```text
PREPARED
UPLOADED
SUBMISSION_AMBIGUOUS
SUBMITTED
PROCESSING
COMPLETED
FAILED
EXPIRED/CANCELLED
```

Upload the exact JSONL and persist before create the provider `input_file_id`,
local SHA-256 of exact uploaded bytes, and `batchcorr:v1:<manifest-sha256>`.
Create with provider-supported metadata containing the correlation/manifest SHA.
Immediately before paid execution, verify that create with `input_file_id`,
metadata, list/retrieve, returned `input_file_id`/metadata, and output/error
identities/request counts remain available; otherwise STOP before create.

Persist the provider batch ID only after a known successful submission. If create
may have succeeded without durable ID, set `SUBMISSION_AMBIGUOUS` and STOP. Only
the owner/orchestrator may authorize reconciliation; a supervised worker may list
or retrieve only on that explicit instruction. Reconciliation paginates all
relevant batches and matches the conjunction of persisted input file ID,
correlation/manifest SHA metadata, expected endpoint, and compatible run identity.
Exactly one match is durably recovered after verifying returned correlation fields;
zero, multiple, or contradictory matches remain ambiguous and STOP. No ordinary
restart or automatic resubmission may alter that state. An owner may explicitly
choose evidence-preserving `ABANDONED`; any paid retry is separately authorized.

Completed manifests are never resubmitted. A later failed, expired, rejected, or
ambiguous manifest preserves earlier independent manifest and per-item histories.
Restart resumes only unfinished, unambiguous manifests from the plan. If limits
change, submitted/completed/ambiguous manifests remain historical; an unsubmitted
prepared manifest must still fit or STOP. Repartitioning never-submitted work
requires explicit orchestrator authorization and a successor plan.

Workers do not poll a long-running provider job. They submit once and later,
at an explicit resume/retrieval decision point, make only the minimum status or
output retrieval needed to establish terminal handling.

## 6. Validation, QA, and production gate (D70–D71)

Generated German/English candidates first receive deterministic structural,
language, provenance, and content validation. Stronger semantic QA is one item
per request and receives every suspicious result plus a deterministic small
audit sample; it never becomes universal merely because Batch is cheaper. When
the selected QA model supports the needed Batch contract, it may use the same
transport-only batching rule.

Source-backed Persian rows receive no LLM QA. Their validation verifies source
artifact digest/identity, license/provenance presence, exact mapping evidence,
Persian script/Unicode and forbidden bidi controls, deterministic ordering, and
integrity. Every candidate mapping produces an owner/orchestrator
source-acceptance packet: candidate name/edition, artifact revision/date/SHA,
license evidence, extractor and mapping/bridge versions, accepted exact rule,
counts, deterministic sample rule, and each sampled canonical/source identity,
relation chain, translation record, retained text, provenance/license, and
decision evidence. A material alignment, extraction, provenance, or attribution
defect means `SOURCE ACCEPTANCE = REJECTED` and STOP; repair requires corrected
extractor/mapping, fixtures, a new packet, and fresh acceptance. Coverage is not
accepted until every used packet is explicitly accepted.

Before any German production long run, all of the following are required:

1. ADR-0006 accepted/frozen;
2. all used source-acceptance packets explicitly accepted by owner/orchestrator;
3. accepted deterministic source-backed FA coverage/gap report and required gap decision;
4. measured German source-first queue and accepted bounded German canary;
5. accepted selective QA path;
6. current Batch endpoint/model/correlation/limit capabilities verified;
7. production partition plan/manifests prepared and current cost estimate reported; and
8. explicit orchestrator authorization of paid production submission.

A canary never implies full-run authorization.

## 7. Consequences

- Persian remains a first-class optional learner-meaning language, but source
  coverage—not a generated default—determines current availability.
- A valid architecture may initially have only the direct English-edition
  canonical-source FA relation; the German-Wiktionary cross-edition fallback is
  optional until the D60 bridge is proven. Measured gaps are preferable to
  guessed mapping.
- Stage-03/04 implementation must be revised before any paid work: old Persian
  jobs and multi-item prompt transport are historical, not forward contracts.
- Batch reduces provider processing cost only when currently available; it does
  not authorize a pricing assumption or a weaker quality contract.
- The legacy Persian canary remains retained, retired evidence. Its recovery
  lessons still apply to generated DE/EN and Batch result ingestion.

## 8. Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| Automatically generate Persian when no source row exists | Replaces a measured owner decision with a hidden paid/model policy. |
| Match FA from a lemma or English gloss alone | Polysemy makes this persistently wrong and hard to detect. |
| Accept a high-coverage source without reproducible artifact/license/mapping proof | Violates per-row attribution and cannot be rebuilt or audited. |
| One prompt/response for many unrelated semantic senses | Changes semantic isolation and makes validation/QA ambiguous. |
| Automatically fall back to another model or synchronous full-run processing | Changes cost and model behavior without the required authorization. |
| LLM QA of source-backed FA translations | QA would invent a model-derived layer where deterministic source integrity is required. |

## 9. Required implementation evidence

The owning slice must prove, with bounded fixtures before source acceptance:

- each source eligibility field and actual source metadata/digest;
- direct canonical-source mapping, rejected direct ambiguity, optional bridge
  accept/reject cases, and no FA row on ambiguous mapping;
- zero/one/many exact-sense translations, duplicate collapse, deterministic
  representative/provenance/`ord`, and fallback-only source precedence;
- deterministic coverage report/order/sample and owner STOP boundary;
- no automatic Persian queue records or reuse of old Persian identities;
- German positive eligibility predicate and isolated uncertainty fallback request;
- one item per synchronous/Batch record, deterministic `custom_id`, and
  order-independent output joining;
- bounded partition/manifest boundaries, immutable completed manifests, ambiguous
  exact-one reconciliation and zero/multiple fail-closed durability;
- source-acceptance packet owner STOP behavior, selective DE/EN QA, and no LLM QA
  for source-backed FA;
- preservation of the legacy canary; and
- no paid full run before the D71 authorization gate.

## 10. Supersession record — ACTIVE

ADR-0006 is accepted/frozen, so this supersession record is active. It does not
rewrite the historical body of ADR-0004.

| ADR-0004 provision | Accepted ADR-0006 replacement |
|---|---|
| D35 Persian generation | Source-cascade ingestion plus owner-controlled gap handling. |
| D37 LLM roles | Continue for genuinely generated DE/EN; do not automatically apply to Persian. |
| D38 / §8 Stage-04 Persian creation | Deterministic source-backed Persian ingestion supersedes generated Persian as the ordinary path. |
| §5 Persian generation procedure | Source-first cascade, coverage report, and owner stop supersede it. |
| §7 bulk generator applies to every queued enrichment row | It no longer applies to source-backed Persian rows. |
| Generated-row rules | Continue unchanged for genuinely generated DE/EN rows. |
| FA provenance | Source-backed FA keeps its actual source/license; future Persian generation needs a later explicit decision. |

## 11. Cold review

No cold review is performed in this drafting session. A fresh cold orchestrator
session must review this ADR under WORKFLOW §7. Its first review is the broad
architecture challenge for this new ADR-0006 lineage.

### Cold review #1 — broad architecture challenge

**Reviewer:** fresh cold orchestrator session, 2026-08-21. Repository-only architecture review under WORKFLOW §7 / AGENTS G7, with current provider/source facts checked only where the ADR depends on them.

**Verdict: BLOCKING OBJECTIONS — `NEEDS COLD REVIEW` stays.** ADR-0006 is a legitimate new lineage and does not reopen ADR-0004, and its fail-closed EN→FA, source-license, one-item-per-request, owner gap gate, copy-on-write, no-monitoring, and legacy-canary directions are coherent. The following seven defects are architecture-blocking rather than optional refinements.

#### O1 — BLOCKING. The proposed DE→FA primary path is based on the wrong canonical source-sense lineage.

**Concrete defect.** §3.2 says the German-Wiktionary candidate is promising because "the canonical German sense already originates in this edition and build metadata has source namespace/ref." That is false for the accepted Stage-01 implementation and asset. `tools/build_dict.py` appends raw senses only for the `is_en_edition` input, resolves `source_ref` from `raw_senses_en`, and materializes canonical `sense` rows from those English-edition Wiktionary senses. The German-edition input does not supply the persisted canonical sense identity. Current `sense.semantic_ref` / `sense.source_ref` therefore cannot, by themselves, prove an exact relation to a German-Wiktionary translation block.

This also changes the meaning of D60: the accepted canonical German-lexeme sense is already sourced from the English Wiktionary edition, so an English-edition translation attached to that exact persisted source sense may be a direct source relation, whereas German Wiktionary is the path that requires a cross-edition bridge. The ADR currently assumes the opposite source topology.

**Why blocking.** D59 correctly forbids lemma, ordinal, gloss-string, fuzzy, embedding and LLM matching. With those fallbacks forbidden and Stage-01 semantics frozen for slice-6, the advertised primary importer has no defined executable mapping to the actual canonical identity. A worker can only guess, reject all rows, or silently invent a cross-edition mapper.

**Affected contract.** D57–D60; §3.1–§3.3; §7; `tasks/slice-6.md` A2/A4; accepted Stage-01 semantic identity in `tools/build_dict.py` / ADR-0004 D47.

**Required remedy direction.** Rebase the source cascade on the canonical identity that actually exists. Either define and prove an exact stable cross-edition mapping from the persisted English-edition source sense to a German-Wiktionary sense, make German Wiktionary optional/fail-closed when that mapping is unavailable, or explicitly redesign/rebuild canonical Stage-01 identity in a separately authorized architecture change. Also distinguish a direct translation attached to the exact canonical English-edition sense from a genuinely cross-source EN bridge. Do not use lemma, ordinal, gloss text, fuzzy, embedding or LLM matching as the repair.

**Resolution (2026-08-21 revision): APPLIED.**
The forward source topology now follows the accepted Stage-01 identity actually
persisted by `tools/build_dict.py`: canonical `sense` identity is rooted in the
English-edition Wiktionary source sense (`wiktextract:enwiktionary`). ADR-0006
now treats a Persian translation relation attached to that exact persisted
source sense as the primary direct relation, not a cross-edition bridge.
German-Wiktionary DE→FA is optional and may contribute only through a proven
deterministic one-to-one cross-edition sense bridge; missing or ambiguous bridge
evidence fails closed. Lemma, ordinal, gloss-string, fuzzy, embedding and LLM
mapping remain forbidden. Stage-01 identity is not redesigned.

#### O2 — BLOCKING. Pending ADR-0006 is simultaneously non-binding and given forward precedence over frozen ADR-0004.

**Concrete defect.** ADR-0006's header and §10 correctly say its supersession activates only on acceptance and that ADR-0004 remains binding until then. In conflict, `tasks/slice-6.md` says pending ADR-0006 "controls every conflict with ADR-0004 ... until its cold review resolves," and `docs/plan.md` calls it the forward design constraint for slice-6 planning. `STATE.md` still points toward slice-6 Phase-A dispatch. These are not merely historical notes: the slice brief is executable worker authority and already requires the pending source-first architecture.

**Why blocking.** A worker cannot know whether to implement frozen ADR-0004's generated-Persian path or unaccepted ADR-0006's source-first path. Treating a `NEEDS COLD REVIEW` ADR as binding before its review defeats the governance boundary; treating ADR-0004 as binding makes the current slice brief contradictory and capable of building the wrong architecture before acceptance.

**Affected contract.** ADR-0006 header / §10; `tasks/slice-6.md` Authority and A2–A6; `docs/plan.md` slice-6 row and pending ADR-0006 amendment; `STATE.md` next-action contract; ADR-0004 accepted/frozen status.

**Required remedy direction.** Make the pre-acceptance authority rule unambiguous across all forward contracts. Architecture-changing slice-6 implementation must remain blocked until ADR-0006 is accepted, or any pre-acceptance work must be explicitly limited to non-binding investigation/fixtures that cannot materialize the pending architecture. The accepted ADR alone may supersede ADR-0004.

**Resolution (2026-08-21 revision): APPLIED.**
The repository now has one pre-acceptance authority rule: ADR-0004 remains
binding while ADR-0006 is `NEEDS COLD REVIEW`; pending ADR-0006 may constrain
planning and investigation only and cannot supersede ADR-0004. The Slice-6
implementation brief is explicitly dormant for architecture-changing work until
ADR-0006 is accepted. `tasks/slice-6.md`, `docs/plan.md`, `docs/backlog.md` and
`STATE.md` all carry the same block, and the next action remains governance.

#### O3 — BLOCKING. Source mapping ambiguity is not separated from valid multi-translation cardinality, deduplication and precedence.

**Concrete defect.** §3.1 says a "non-unique" required relation is rejected, while D61 and the existing `sense_meaning` model permit multiple ordered localized rows for one sense. A single exact source sense may legitimately contain several Persian translations that are synonyms, variant wording, or duplicate extraction rows. ADR-0006 does not define whether all exact translations are retained, how exact/normalized duplicates are collapsed, how deterministic `ord` is assigned, or whether a secondary source may add wording when the primary already safely yielded one or more rows.

**Why blocking.** Without this distinction an importer can incorrectly reject a perfectly exact sense relation merely because it has several valid Persian strings, arbitrarily keep a first hit, or produce unstable rows/order across rebuilds. Those outcomes directly affect dictionary semantics, provenance, coverage counts and Stage-05 reproducibility.

**Affected contract.** D57, D59, D61; §3.1, §3.4, §3.5; `sense_meaning` cardinality/ordering contract from ADR-0004 D36/D45 and PART-A schema.

**Required remedy direction.** Define mapping uniqueness separately from translation-row multiplicity. State the deterministic rule for retaining a set of valid exact-sense FA translations, duplicate normalization/collapse, stable ordering, and source precedence. A secondary source should run only under an explicit rule when the primary produced no accepted set (or, if additive secondary wording is intended, that must be stated explicitly with provenance). Do not force one Persian string per sense unless deliberately chosen.

**Resolution (2026-08-21 revision): APPLIED.**
ADR-0006 now separates unique exact source-sense mapping from translation-row
cardinality. One exactly mapped source sense may retain zero, one or many valid
Persian strings. Duplicate detection uses only the specified NFC/Unicode-
whitespace normalization and never participates in semantic matching; duplicate
representatives, per-row provenance and `ord` are selected deterministically.
The direct canonical-source set is primary, and German-Wiktionary is consulted
only when the primary accepted set is empty, so secondary wording is never
additive.

#### O4 — BLOCKING. D65's source-first German eligibility predicate contains semantic/user-level judgments that are not mechanically decidable as specified.

**Concrete defect.** D65/§4 requires a deterministic non-LLM predicate to decide that source text is "semantically correct, concise, learner-useful, and D33-compatible." Exact attachment to the canonical sense can establish source-sense membership, but "learner-useful" and approximate A2–B1 suitability are not made executable by saying the predicate is deterministic/conservative. Length or punctuation alone cannot prove those semantic quality properties, and no positive-evidence rule or mandatory uncertainty fallback is defined.

**Why blocking.** This predicate decides whether source wording becomes the final learner-facing German meaning or whether a paid isolated generation job exists. An implementation-specific heuristic can silently accept complex, circular, meta-lexicographic or otherwise unsuitable source definitions merely to reduce cost, which violates D33's quality contract without any later universal QA to catch it.

**Affected contract.** D65; §4; ADR-0004 D33; `tasks/slice-6.md` A2/A4.

**Required remedy direction.** Define a deliberately conservative mechanically checkable positive-eligibility contract and an explicit fail-closed rule: any property that cannot be established by allowed deterministic source/structural evidence falls through to the isolated DE generation job. It is acceptable for this to create more DE work. Do not make a deterministic heuristic pretend to perform semantic/CEFR judgment it cannot prove.

**Resolution (2026-08-21 revision): APPLIED.**
D65 is now a deliberately conservative positive-eligibility predicate rather
than a claimed deterministic CEFR/semantic judge. Exact sense attachment and
source relation type are prerequisites; explicit structural bounds and
meta-lexicographic exclusions decide only whether source wording is safe enough
to retain without generation. Any uncertain or unprovable property falls through
to one isolated DE generation request. The architecture explicitly accepts the
resulting higher DE job count.

#### O5 — BLOCKING. `SUBMISSION_AMBIGUOUS` prevents duplicate submission but has no executable reconciliation path for a provider-created Batch whose ID was lost locally.

**Concrete defect.** D68 persists the provider batch ID only after a known successful submission and says an ambiguous create must STOP. It does not define how a later owner/session determines whether the provider actually created the Batch after the process/network failed between provider creation and local ID persistence. In that state, merely stopping is safe against automatic rebilling but can permanently orphan paid work and valid results.

The current OpenAI Batch contract exposes durable Batch IDs, the uploaded `input_file_id`, attachable metadata, list/retrieve operations, output/error artifacts and per-request completion/failure counts. ADR-0006 does not require any provider-side deterministic manifest correlation or ownership/reconciliation procedure that uses those facilities.

**Why blocking.** The stated invariant is stronger than "never auto-retry": D68 says restart must neither duplicate possibly billed work nor lose valid partial work. The current state machine cannot satisfy both after provider creation/local-persist loss. Manual intervention is not executable when it has no exact reconciliation key or single-owner decision rule.

**Affected contract.** D68–D69; §5.2; §9 Batch durability evidence; `tasks/slice-6.md` A6.

**Required remedy direction.** Add a durable submission-ownership/reconciliation contract. Before create, persist the provider upload identity and a deterministic manifest correlation value; submit that correlation through provider-supported metadata/idempotency facilities when available. A later explicit reconciliation owner must be able to enumerate/retrieve provider batches and recover exactly one matching provider ID, or remain blocked on zero/multiple/contradictory matches. Ambiguous work must still never be automatically resubmitted. If the provider later lacks an adequate reconciliation facility, the architecture must state the fail-closed manual evidence/abandonment path rather than guessing.

**Resolution (2026-08-21 revision): APPLIED.**
D68 now persists the exact provider upload identity and deterministic manifest
correlation before Batch create and requires provider-supported correlation
metadata when paid execution occurs. `SUBMISSION_AMBIGUOUS` has an explicit
owner/orchestrator reconciliation path: enumerate/retrieve provider batches and
recover only an exactly-one match on persisted input-file/correlation/compatibility
identity. Zero, multiple or contradictory matches remain blocked; no ambiguous
manifest is automatically resubmitted. If provider facilities cannot establish
identity, an explicit evidence-preserving owner abandonment decision is required
before any separately authorized future attempt.

#### O6 — BLOCKING. "One Batch" is not bounded or partitioned against provider limits, so the production architecture is non-executable for a large queue.

**Concrete defect.** D67/§5 describes a Batch manifest but does not define deterministic partitioning into multiple independently durable manifests. As of this review, the official OpenAI create-Batch contract permits at most 50,000 requests and 200 MB in one Batch input file. The existing historical Stage-03 measurement is on the order of 480,221 DE jobs before D65 source-first reduction, so a production queue can easily exceed one provider manifest even if source-first filtering substantially reduces it.

**Why blocking.** A production run cannot rely on an implementation constant or accidental queue size to fit one provider object. Without a partition/restart contract, transport grouping can leak into semantic identity, a later manifest failure can invalidate or cause resubmission of earlier work, and restart cannot prove that completed partitions will not be billed again.

**Affected contract.** D67–D69; §5.1–§5.2; §9; `tasks/slice-6.md` A6; cost/operational-complexity assumptions.

**Required remedy direction.** Require deterministic bounded manifest partitioning under the provider limits verified at execution time, without freezing today's commercial limits into architecture. Partition identity/order must derive from the already-stable item stream/content, transport grouping must not change enrichment-item semantic identity, each manifest must be independently durable/reconcilable, completed manifests must never be resubmitted, and a later manifest failure must preserve earlier completed/rejected per-item results.

**Resolution (2026-08-21 revision): APPLIED.**
Production Batch transport is now deterministically partitioned into bounded,
independently durable manifests using provider limits verified immediately before
execution. Semantic item identity is independent of partitioning; partition
boundaries derive from the sorted stable item stream and exact serialized bytes.
Every manifest has its own durable state and reconciliation history, completed
manifests are never resubmitted, later failures do not invalidate earlier
per-item results, and restart resumes only unfinished unambiguous work.

#### O7 — BLOCKING. The bounded human review of source-backed Persian has no explicit acceptance owner or failure consequence.

**Concrete defect.** D70 says a bounded human-review sample assesses Persian source extraction quality, while D62/D71 require a coverage report and owner visibility/acceptance. The ADR never states who receives the D70 sample, what evidence accompanies it, whether source acceptance depends on that review, or what must happen if the sample exposes wrong sense mapping/extraction despite passing deterministic structural checks.

**Why blocking.** Source-backed FA deliberately receives no LLM semantic QA. The human sample is therefore the only stated semantic sanity check on the extraction/mapping implementation. If its result has no explicit stop/accept owner, a structurally valid but systematically mis-mapped source import can proceed to Stage-05 with no architecture-level decision point.

**Affected contract.** D58, D62, D70–D71; §3.2, §3.5, §6, §9; `tasks/slice-6.md` A4.

**Required remedy direction.** Make the source-acceptance packet explicitly include the deterministic human-review sample and its mapping/provenance evidence, identify the owner/orchestrator as the acceptance authority, and require STOP/rejection of the source mapping/build when review finds a material extraction or sense-binding defect. No arbitrary percentage threshold is required; the important contract is explicit evidence, owner acceptance, and fail-closed handling of a bad sample.

**Resolution (2026-08-21 revision): APPLIED.**
The bounded Persian human review is now part of an explicit source-acceptance
packet delivered to the owner/orchestrator, who is the sole acceptance authority.
The packet carries canonical/source identities, bridge/mapping evidence,
provenance, extraction versions and the deterministic sample. Any material
sense-alignment, extraction or provenance defect rejects source acceptance and
STOPs the affected source-backed FA build until a corrected mapping/extractor is
re-evidenced and explicitly accepted. No arbitrary pass percentage is used.

### Cold review #2 — FOCUSED REMEDY VERIFICATION

**Reviewer:** fresh cold orchestrator session, 2026-08-21. Repository-only
focused remedy verification under WORKFLOW §7 / AGENTS G7.

**Verdict: APPROVED.** O1–O7 remedies were verified against the accepted
Stage-01 source-sense identity and the converged forward contract. Direct
knock-on contradictions introduced by those remedies were checked. No qualifying
blocking correctness, executability, persistent-state, integrity, or architecture
defect remains.

ADR-0006 is approved and frozen. Its §10 supersession record is now active.
ADR-0004 remains `ACCEPTED / FROZEN` and binding everywhere not explicitly
superseded by that record. The stale header cross-reference from `§12` to the
actual `§10` supersession record was corrected administratively during
activation; this does not alter the reviewed architecture.
