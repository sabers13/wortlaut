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

### Cold review #1 — broad architecture challenge

**Reviewer:** fresh cold orchestrator session, 2026-08-21. Repository-only architecture review under WORKFLOW §7 / AGENTS G7, with current provider/source facts checked only where the ADR depends on them.

**Verdict: BLOCKING OBJECTIONS — `NEEDS COLD REVIEW` stays.** ADR-0006 is a legitimate new lineage and does not reopen ADR-0004, and its fail-closed EN→FA, source-license, one-item-per-request, owner gap gate, copy-on-write, no-monitoring, and legacy-canary directions are coherent. The following seven defects are architecture-blocking rather than optional refinements.

#### O1 — BLOCKING. The proposed DE→FA primary path is based on the wrong canonical source-sense lineage.

**Concrete defect.** §3.2 says the German-Wiktionary candidate is promising because "the canonical German sense already originates in this edition and build metadata has source namespace/ref." That is false for the accepted Stage-01 implementation and asset. `tools/build_dict.py` appends raw senses only for the `is_en_edition` input, resolves `source_ref` from `raw_senses_en`, and materializes canonical `sense` rows from those English-edition Wiktionary senses. The German-edition input does not supply the persisted canonical sense identity. Current `sense.semantic_ref` / `sense.source_ref` therefore cannot, by themselves, prove an exact relation to a German-Wiktionary translation block.

This also changes the meaning of D60: the accepted canonical German-lexeme sense is already sourced from the English Wiktionary edition, so an English-edition translation attached to that exact persisted source sense may be a direct source relation, whereas German Wiktionary is the path that requires a cross-edition bridge. The ADR currently assumes the opposite source topology.

**Why blocking.** D59 correctly forbids lemma, ordinal, gloss-string, fuzzy, embedding and LLM matching. With those fallbacks forbidden and Stage-01 semantics frozen for slice-6, the advertised primary importer has no defined executable mapping to the actual canonical identity. A worker can only guess, reject all rows, or silently invent a cross-edition mapper.

**Affected contract.** D57–D60; §3.1–§3.3; §7; `tasks/slice-6.md` A2/A4; accepted Stage-01 semantic identity in `tools/build_dict.py` / ADR-0004 D47.

**Required remedy direction.** Rebase the source cascade on the canonical identity that actually exists. Either define and prove an exact stable cross-edition mapping from the persisted English-edition source sense to a German-Wiktionary sense, make German Wiktionary optional/fail-closed when that mapping is unavailable, or explicitly redesign/rebuild canonical Stage-01 identity in a separately authorized architecture change. Also distinguish a direct translation attached to the exact canonical English-edition sense from a genuinely cross-source EN bridge. Do not use lemma, ordinal, gloss text, fuzzy, embedding or LLM matching as the repair.

#### O2 — BLOCKING. Pending ADR-0006 is simultaneously non-binding and given forward precedence over frozen ADR-0004.

**Concrete defect.** ADR-0006's header and §10 correctly say its supersession activates only on acceptance and that ADR-0004 remains binding until then. In conflict, `tasks/slice-6.md` says pending ADR-0006 "controls every conflict with ADR-0004 ... until its cold review resolves," and `docs/plan.md` calls it the forward design constraint for slice-6 planning. `STATE.md` still points toward slice-6 Phase-A dispatch. These are not merely historical notes: the slice brief is executable worker authority and already requires the pending source-first architecture.

**Why blocking.** A worker cannot know whether to implement frozen ADR-0004's generated-Persian path or unaccepted ADR-0006's source-first path. Treating a `NEEDS COLD REVIEW` ADR as binding before its review defeats the governance boundary; treating ADR-0004 as binding makes the current slice brief contradictory and capable of building the wrong architecture before acceptance.

**Affected contract.** ADR-0006 header / §10; `tasks/slice-6.md` Authority and A2–A6; `docs/plan.md` slice-6 row and pending ADR-0006 amendment; `STATE.md` next-action contract; ADR-0004 accepted/frozen status.

**Required remedy direction.** Make the pre-acceptance authority rule unambiguous across all forward contracts. Architecture-changing slice-6 implementation must remain blocked until ADR-0006 is accepted, or any pre-acceptance work must be explicitly limited to non-binding investigation/fixtures that cannot materialize the pending architecture. The accepted ADR alone may supersede ADR-0004.

#### O3 — BLOCKING. Source mapping ambiguity is not separated from valid multi-translation cardinality, deduplication and precedence.

**Concrete defect.** §3.1 says a "non-unique" required relation is rejected, while D61 and the existing `sense_meaning` model permit multiple ordered localized rows for one sense. A single exact source sense may legitimately contain several Persian translations that are synonyms, variant wording, or duplicate extraction rows. ADR-0006 does not define whether all exact translations are retained, how exact/normalized duplicates are collapsed, how deterministic `ord` is assigned, or whether a secondary source may add wording when the primary already safely yielded one or more rows.

**Why blocking.** Without this distinction an importer can incorrectly reject a perfectly exact sense relation merely because it has several valid Persian strings, arbitrarily keep a first hit, or produce unstable rows/order across rebuilds. Those outcomes directly affect dictionary semantics, provenance, coverage counts and Stage-05 reproducibility.

**Affected contract.** D57, D59, D61; §3.1, §3.4, §3.5; `sense_meaning` cardinality/ordering contract from ADR-0004 D36/D45 and PART-A schema.

**Required remedy direction.** Define mapping uniqueness separately from translation-row multiplicity. State the deterministic rule for retaining a set of valid exact-sense FA translations, duplicate normalization/collapse, stable ordering, and source precedence. A secondary source should run only under an explicit rule when the primary produced no accepted set (or, if additive secondary wording is intended, that must be stated explicitly with provenance). Do not force one Persian string per sense unless deliberately chosen.

#### O4 — BLOCKING. D65's source-first German eligibility predicate contains semantic/user-level judgments that are not mechanically decidable as specified.

**Concrete defect.** D65/§4 requires a deterministic non-LLM predicate to decide that source text is "semantically correct, concise, learner-useful, and D33-compatible." Exact attachment to the canonical sense can establish source-sense membership, but "learner-useful" and approximate A2–B1 suitability are not made executable by saying the predicate is deterministic/conservative. Length or punctuation alone cannot prove those semantic quality properties, and no positive-evidence rule or mandatory uncertainty fallback is defined.

**Why blocking.** This predicate decides whether source wording becomes the final learner-facing German meaning or whether a paid isolated generation job exists. An implementation-specific heuristic can silently accept complex, circular, meta-lexicographic or otherwise unsuitable source definitions merely to reduce cost, which violates D33's quality contract without any later universal QA to catch it.

**Affected contract.** D65; §4; ADR-0004 D33; `tasks/slice-6.md` A2/A4.

**Required remedy direction.** Define a deliberately conservative mechanically checkable positive-eligibility contract and an explicit fail-closed rule: any property that cannot be established by allowed deterministic source/structural evidence falls through to the isolated DE generation job. It is acceptable for this to create more DE work. Do not make a deterministic heuristic pretend to perform semantic/CEFR judgment it cannot prove.

#### O5 — BLOCKING. `SUBMISSION_AMBIGUOUS` prevents duplicate submission but has no executable reconciliation path for a provider-created Batch whose ID was lost locally.

**Concrete defect.** D68 persists the provider batch ID only after a known successful submission and says an ambiguous create must STOP. It does not define how a later owner/session determines whether the provider actually created the Batch after the process/network failed between provider creation and local ID persistence. In that state, merely stopping is safe against automatic rebilling but can permanently orphan paid work and valid results.

The current OpenAI Batch contract exposes durable Batch IDs, the uploaded `input_file_id`, attachable metadata, list/retrieve operations, output/error artifacts and per-request completion/failure counts. ADR-0006 does not require any provider-side deterministic manifest correlation or ownership/reconciliation procedure that uses those facilities.

**Why blocking.** The stated invariant is stronger than "never auto-retry": D68 says restart must neither duplicate possibly billed work nor lose valid partial work. The current state machine cannot satisfy both after provider creation/local-persist loss. Manual intervention is not executable when it has no exact reconciliation key or single-owner decision rule.

**Affected contract.** D68–D69; §5.2; §9 Batch durability evidence; `tasks/slice-6.md` A6.

**Required remedy direction.** Add a durable submission-ownership/reconciliation contract. Before create, persist the provider upload identity and a deterministic manifest correlation value; submit that correlation through provider-supported metadata/idempotency facilities when available. A later explicit reconciliation owner must be able to enumerate/retrieve provider batches and recover exactly one matching provider ID, or remain blocked on zero/multiple/contradictory matches. Ambiguous work must still never be automatically resubmitted. If the provider later lacks an adequate reconciliation facility, the architecture must state the fail-closed manual evidence/abandonment path rather than guessing.

#### O6 — BLOCKING. "One Batch" is not bounded or partitioned against provider limits, so the production architecture is non-executable for a large queue.

**Concrete defect.** D67/§5 describes a Batch manifest but does not define deterministic partitioning into multiple independently durable manifests. As of this review, the official OpenAI create-Batch contract permits at most 50,000 requests and 200 MB in one Batch input file. The existing historical Stage-03 measurement is on the order of 480,221 DE jobs before D65 source-first reduction, so a production queue can easily exceed one provider manifest even if source-first filtering substantially reduces it.

**Why blocking.** A production run cannot rely on an implementation constant or accidental queue size to fit one provider object. Without a partition/restart contract, transport grouping can leak into semantic identity, a later manifest failure can invalidate or cause resubmission of earlier work, and restart cannot prove that completed partitions will not be billed again.

**Affected contract.** D67–D69; §5.1–§5.2; §9; `tasks/slice-6.md` A6; cost/operational-complexity assumptions.

**Required remedy direction.** Require deterministic bounded manifest partitioning under the provider limits verified at execution time, without freezing today's commercial limits into architecture. Partition identity/order must derive from the already-stable item stream/content, transport grouping must not change enrichment-item semantic identity, each manifest must be independently durable/reconcilable, completed manifests must never be resubmitted, and a later manifest failure must preserve earlier completed/rejected per-item results.

#### O7 — BLOCKING. The bounded human review of source-backed Persian has no explicit acceptance owner or failure consequence.

**Concrete defect.** D70 says a bounded human-review sample assesses Persian source extraction quality, while D62/D71 require a coverage report and owner visibility/acceptance. The ADR never states who receives the D70 sample, what evidence accompanies it, whether source acceptance depends on that review, or what must happen if the sample exposes wrong sense mapping/extraction despite passing deterministic structural checks.

**Why blocking.** Source-backed FA deliberately receives no LLM semantic QA. The human sample is therefore the only stated semantic sanity check on the extraction/mapping implementation. If its result has no explicit stop/accept owner, a structurally valid but systematically mis-mapped source import can proceed to Stage-05 with no architecture-level decision point.

**Affected contract.** D58, D62, D70–D71; §3.2, §3.5, §6, §9; `tasks/slice-6.md` A4.

**Required remedy direction.** Make the source-acceptance packet explicitly include the deterministic human-review sample and its mapping/provenance evidence, identify the owner/orchestrator as the acceptance authority, and require STOP/rejection of the source mapping/build when review finds a material extraction or sense-binding defect. No arbitrary percentage threshold is required; the important contract is explicit evidence, owner acceptance, and fail-closed handling of a bad sample.