# ADR-0006 — Source-first Persian and quality-preserving batch enrichment

**Status:** NEEDS COLD REVIEW.

**Lineage:** This is a genuinely new architectural decision made after
ADR-0004 was accepted and frozen. It begins a new cold-review lineage; it does
not reopen, reset, or consume another review in ADR-0004's exhausted lineage.

**Amends on acceptance:** ADR-0004 D35, D37, D38, §5, §7 and §8 as specified in
§12 below. Until this ADR is accepted, ADR-0004 remains the binding historical
architecture. ADR-0005 is not amended.

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
| D57 | **Persian is source-first.** For every canonical sense, attempt exact DE→FA source evidence first, then exact EN→FA source evidence, otherwise record an unresolved Persian gap. DE→FA wins whenever both safely cover the same canonical sense. No automatic LLM fallback exists. | A source-backed translation is auditable and reversible without recasting a coverage gap as a model decision. |
| D58 | **A Persian source must pass the eligibility gate.** An eligible product has explicit compatible redistribution terms; a reproducible, versionable offline artifact; recorded revision/date and SHA-256; deterministic Persian extraction; per-row provenance; and a non-guessing exact mapping to the canonical sense. | Translation count alone cannot prove legal reuse or semantic fidelity. |
| D59 | **Imported Persian is sense-bound.** Lemma-only, ordinal-only, fuzzy, embedding, LLM, first-hit, and gloss-string-only matching are forbidden authoritative matches. Ambiguity produces no FA row. | `Schloss` / castle / `قلعه` and `Schloss` / lock / `قفل` must never collapse. |
| D60 | **The EN bridge is a semantic bridge, not a gloss lookup.** It requires a trustworthy German-canonical-sense → exact-English-semantic-sense binding and an exact English-semantic-sense → Persian source relation. | Matching a familiar English string is not enough to prove its intended sense. |
| D61 | **Imported FA rows are source-backed.** They carry their actual namespace, license, source artifact identity, language, text, and deterministic ordering. They never use `llm_generated_vN`; generated rollback never removes them. | R11 attribution and rollback remain truthful. |
| D62 | **A deterministic missing-Persian report is a hard owner gate.** After source ingestion, report coverage and representative rejected/missing senses, then stop. | The owner decides the policy for measured gaps, not a hidden fallback. |
| D63 | **Persian source ingestion precedes final LLM queue materialization.** The historical 480,221 `fa_translation` jobs are evidence only. The new queue has no automatic Persian jobs and receives only items that genuinely need generation, presently principally DE learner meanings and missing EN meanings. | A historical checkpoint or queue cannot re-authorize the superseded Persian path. |
| D64 | **A future Persian LLM fallback needs a new explicit authorization.** It may be considered only after D62 and must define the bounded count, model, estimate, prompt contract, classification/provenance, QA, checkpointing, and canary. Until then, Persian LLM jobs equal zero. | This preserves a future option without silently choosing it now. |
| D65 | **German learner meanings are source-first.** Preserve an existing source-backed German meaning when it is semantically correct, concise, learner-useful, and compatible with D33; otherwise make one independent German generation job. The job remains synonym-first, then a short approximately A2–B1 explanation, without sense change. | Do not spend money or create a duplicate where good licensed wording already exists. |
| D66 | **One semantic enrichment item equals one model request.** Its deterministic context contains exactly one item. Multi-sense giant prompts, shared unrelated context, and one response responsible for multiple senses are prohibited. | Token savings may not trade away isolation, validation, or QA. |
| D67 | **Use OpenAI Batch as a conditional production processing mode.** When the configured model and required endpoint officially support Batch, package independent item requests as independent input records. Each has a stable deterministic `custom_id`; result order is ignored and records rejoin solely through that ID. Missing, duplicate, or unknown IDs fail closed. | Batch changes transport/processing only, not the item contract. |
| D68 | **Batch paid-work durability is manifest-first and fail-closed.** Persist the exact manifest and compatibility identity atomically before submission; persist the provider batch ID after a known submission. Ambiguous submission is never automatically resubmitted. Per-record results become durable completed/rejected items independently. | Restart must neither duplicate a possibly billed batch nor lose valid partial work. |
| D69 | **No monitoring waste.** Submit once, persist the provider identity, and retrieve status/result only at a later explicit decision point or terminal retrieval. No continuously active worker or repetitive hours-long polling is required. | WORKFLOW §15 remains binding for asynchronous work. |
| D70 | **QA is selective and item-isolated.** Deterministic validation applies to generated DE/EN candidates; stronger QA gets every suspicious result plus a deterministic small audit sample. Optional Batch QA keeps one item per request. FA source rows receive deterministic integrity/provenance/sense/script/license checks and bounded human review, never LLM QA. | Strong semantic review belongs where a model generated content, not where a source relation is being preserved. |
| D71 | **The production long run remains owner-gated.** Source coverage must be accepted; the owner must see the FA gap; the DE source-first queue must be measured; a small German canary and selective QA must pass; current Batch support and cost must be reported; and the orchestrator must explicitly authorize submission. | A passing canary proves feasibility, not authority to spend for production. |

## 3. Persian source cascade (D57–D64)

### 3.1 Deterministic cascade

For each canonical `sense.semantic_ref`, source ingestion evaluates in this order:

1. an accepted DE→FA source relation for that exact canonical German sense;
2. only if step 1 did not safely yield a row, an accepted EN→FA relation through
   the D60 semantic bridge;
3. otherwise, a persisted/reportable unresolved Persian gap.

No step may infer a translation from lemma spelling, an unrelated source ordinal,
similarity search, an LLM, or an English gloss string. If any required relation is
missing, non-unique, contradictory, malformed, or unlicensed, reject that
candidate and leave the canonical sense without a Persian row. The primary wins
deterministically over a safe secondary candidate.

The source-ingestion result must be reproducible from recorded source artifacts
and deterministic extractor/mapping versions. It must not mutate the accepted
Stage-02 asset in place; it creates the next copy-on-write build input.

### 3.2 Source eligibility and feasibility record (D58)

No external source is accepted merely because it appears broad. Implementation
must record a candidate feasibility record before ingestion with the following
fields: name, upstream location, artifact format, license evidence, offline
reproduction route, source sense representation, stable artifact identity,
proposed deterministic mapping, and every unresolved uncertainty.

Current investigated candidates are deliberately **provisional**, not accepted
source products:

| Candidate | Upstream / format | License evidence | Sense relation and feasibility | Status / uncertainty |
|---|---|---|---|---|
| German Wiktionary DE→FA translations, extracted from a versioned `dewiktionary-<date>-pages-articles.xml.bz2` artifact | [Wikimedia dumps](https://dumps.wikimedia.org/); XML dump, with a pinned date, upstream checksum and local SHA-256; Wiktextract can capture translations from a dump | Wiktionary entry text is published under CC BY-SA 4.0 and GFDL according to the [Wiktionary copyright policy](https://en.wiktionary.org/wiki/Wiktionary:Copyrights) | Promising primary: the canonical German sense already originates in this edition and build metadata has source namespace/ref. A source translation is usable only when the extractor preserves a unique relation to that same source sense. | Candidate only. The concrete dump/date, extractor version, template coverage, source-sense relation, translation text cleanup, and applicable per-row license string must be proven on a bounded fixture before acceptance. |
| English Wiktionary EN→FA translations, extracted from a versioned `enwiktionary-<date>-pages-articles.xml.bz2` artifact | [Wikimedia dumps](https://dumps.wikimedia.org/); XML dump and reproducible Wiktextract projection | Same official Wiktionary dual-license evidence | Candidate secondary only. English Wiktionary has sense/translation structures, but that does not itself establish German-canonical-sense → English-sense identity. | Not accepted. A deterministic bridge with both ends uniquely evidenced must be demonstrated; a matching English gloss alone fails D60. If it cannot be established, no EN→FA input is used. |
| Kaikki pre-extracted Wiktionary JSONL | [Kaikki](https://kaikki.org/) publishes JSON extracted from Wiktionary, including German and English editions | It is an extraction convenience, not independent license evidence; obligations remain those of the underlying Wiktionary content | Useful only as a reproducibility convenience or comparison input after pinning its release/digest and proving it preserves required source/sense linkage. | Not a substitute for source acceptance; no row may claim Kaikki's convenience URL as the actual lexical license. |

Wiktionary's own parsing guidance says dumps are available as XML/SQL and warns
that templates make raw parsing difficult; that is why a successful complete
source mapping is an explicit implementation proof rather than an assumption.
See [Wiktionary parsing](https://en.wiktionary.org/wiki/Wiktionary:Parsing) and
[Wiktextract's dump/translation documentation](https://github.com/tatuylonen/wiktextract).

### 3.3 Exact sense alignment and the English bridge (D59–D60)

An accepted DE→FA importer must prove a deterministic relation from the canonical
source sense identity to the exact source translation relation. An accepted
EN→FA importer must additionally prove both links:

```text
canonical German sense
        -> exact English semantic sense
        -> exact Persian source translation
```

The bridge cannot be inferred from an English string. A reusable canonical
cross-source relation is acceptable only if both source identities, relation
type, artifact versions, and a one-to-one mapping rule are recorded and the
mapping fails closed on ambiguity. Otherwise the EN candidate is rejected.

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
DE_TO_FA EXACTLY COVERED: <n>
EN_TO_FA ADDITIONAL EXACTLY COVERED: <n>
TOTAL FA COVERED: <n>
FA STILL MISSING: <n>
FA COVERAGE PERCENT: <n>
AMBIGUOUS PRIMARY REJECTED: <n>
AMBIGUOUS SECONDARY REJECTED: <n>
INVALID/UNUSABLE SOURCE ROWS: <n>
```

Its representative missing-sense sample is deterministic and includes German
lemma, POS, canonical sense ref, source English meaning when present, source
German definition/context when present, and the precise non-acceptance reason.
The report is then a STOP point. The owner may choose to leave gaps, authorize
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
localized meanings before queue construction. A versioned deterministic,
conservative eligibility predicate must retain a source row only when it is
semantically correct, concise, learner-useful, and D33-compatible. It must not
silently call an LLM to decide that predicate.

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

Before attempting a Batch submission, atomically persist a deterministic manifest
that contains its identity and SHA-256, exact `custom_id`s, exact enrichment item
IDs, model role occupant, prompt/pipeline version, response-schema version, and
output classification. State is at least:

```text
PREPARED
SUBMISSION_AMBIGUOUS
SUBMITTED
PROCESSING
COMPLETED
FAILED
EXPIRED/CANCELLED
```

Persist the provider batch ID only after a known successful submission. If a
submission may have reached the provider but has no trustworthy batch ID/outcome,
set `SUBMISSION_AMBIGUOUS` and STOP; never create or resubmit an equivalent
manifest automatically. Terminal output processing makes each returned request
result independently durable as completed or rejected, so a failed record cannot
erase valid results from other records. The repaired A6 per-item rejection and
retry rules remain binding.

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
integrity. A bounded human-review sample assesses source extraction quality.

Before any German production long run, all of the following are required:

1. accepted rebuilt source-backed Persian coverage report and owner visibility of
   its remaining-gap count;
2. any required owner Persian-gap decision;
3. measured German source-first queue size;
4. successful small live German canary and manual semantic inspection;
5. passing selective QA path;
6. current Batch model/endpoint support verification;
7. reported production cost estimate; and
8. explicit orchestrator authorization of the production Batch submission.

A canary never implies full-run authorization.

## 7. Consequences

- Persian remains a first-class optional learner-meaning language, but source
  coverage—not a generated default—determines current availability.
- A valid architecture may initially have only DE→FA ingestion; EN→FA is
  optional until D60 is proven. Measured gaps are preferable to guessed mapping.
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
- exact primary mapping, rejected ambiguity, and D60 bridge failure cases;
- DE→FA precedence and no FA row on ambiguous mapping;
- deterministic coverage report/order/sample and owner STOP boundary;
- no automatic Persian queue records or reuse of old Persian identities;
- German source-row retention and isolated fallback request creation;
- one item per synchronous/Batch record, deterministic `custom_id`, and
  order-independent output joining;
- Batch manifest/ambiguous-submission/partial-result durability;
- selective DE/EN QA and no LLM QA for source-backed FA;
- preservation of the legacy canary; and
- no paid full run before the D71 authorization gate.

## 10. Pending supersession record

This record activates only if ADR-0006 is accepted. It does not rewrite the
historical body of ADR-0004.

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
