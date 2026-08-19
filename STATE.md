# STATE

Single entry point for any new session. One screen, maintained by deletion.
Updated only at session CLOSE, only from repository/gate evidence — never from
memory of a conversation.

## What landed

* **slice-0, slice-1 and slice-2 are accepted and merged.** They established the
  repository/gate skeleton, canonical resolver and read-only dictionary boundary,
  executable R3, and the accepted Gate-1 spaCy label result.
* **slice-3 implementation is ACCEPTED but NOT merged and NOT closed.** The
  accepted Attempt-1 branch remains exactly
  `7ceea14e39a7c831edfc803632d3c868ea0f3091` on local and origin `slice/3`,
  `Risk: none`. Its stage-01 implementation was correct against its original
  English-only brief; that acceptance still stands. Closure is paused because
  ADR-0004 later changed the required Stage-01 data contract.
* **ADR-0004 O1–O5 governance revision is complete but still requires fresh cold
  review.** `docs/adr/0004-multilingual-learner-meanings.md` deliberately remains
  **`NEEDS COLD REVIEW`**. O1–O5 and all prior resolution records are preserved.
  D43 separates persisted resolver status from computed
  `meaning_state = none | partial | complete`; D44 normalizes DE/EN/FA
  note-local user meanings; D45 records derivation/provenance for generated
  localized meanings.
* **O4 is resolved by D46 pending cold-review approval.** v1 retains
  `derived_compound` learner meanings as a computed ordered component
  decomposition, never a synthesized whole-compound translation. Component and
  source-sense selection are deterministic; note-local user meaning wins per
  language; dictionary-derived availability is all-components-or-none; exact
  rendered component rows carry provenance; no composed meaning or card face is
  persisted; resolver status and scheduling remain independent.
* **O5 is resolved by D47 pending cold-review approval.** Numeric dictionary
  `lemma_id` / `sense_id` are per-asset caches only. Durable identity uses stable
  lemma/sense semantic refs. Replacement dictionaries are candidate assets until
  checksum/integrity/stable-ref validation plus an atomic PART-B relink and active
  version+SHA update succeed. Missing bindings fail closed without losing user
  meanings/history; ambiguous refs roll back activation; stale picker asset
  tokens return HTTP 409 before writes; mixed old-binding/new-asset states are
  forbidden. Exact relinking is not a second resolver; any true semantic
  re-resolution must call canonical `app/resolve.py`.
* **Cross-file pending ADR-0004 amendments are aligned.** ADR-0001 records the
  pending supersession of numeric dictionary identity, replacement lifecycle and
  historical compound-gloss composition. ADR-0002 keeps the standalone
  architecture and Gate-2 ordering unchanged while compatibly extending picker
  identity with stable refs, immutable asset token and stale-token 409 semantics.
  `AGENTS.md` extends R11 for computed compound provenance and adds executable
  R13: numeric dictionary IDs are never durable semantic identity.
* **Implementation ownership is explicit.** slice-3 alignment owns Stage-01 /
  PART-A stable refs, `sense.source_ref`, D36/D45 representation shape, D46
  component semantic-binding information and the existing plural shape. slice-6
  remains the offline multilingual enrichment owner. slice-7 owns PART-B
  bindings, active dictionary metadata, D43/D44/D46 runtime/render behavior,
  D47 activation/relink/rollback, picker asset-token semantics and R13 runtime
  enforcement. slice-8 owns corresponding end-to-end replacement/stale-picker
  smoke verification.
* **`reference/schema.sql` remains intentionally stale.** It still lacks the
  ADR-0004 localized-meaning/user-meaning model, stable semantic refs,
  `sense.source_ref`, durable dictionary binding relation and active dictionary
  metadata, and still makes numeric note dictionary IDs appear durable. The
  documented mismatch is repaired by its owning implementation slices, not by
  governance.
* **ADR-0001, ADR-0002 and ADR-0003 remain accepted.** ADR-0004 is the only
  active `NEEDS COLD REVIEW` ADR. The pre-existing ADR-0002/ADR-0003 D27 ID
  collision remains parked and is not reopened by this revision.
* **Two Authorities / supervised-worker fallback remains active.** Local
  Git/terminal is authoritative for working-tree/runtime/gate facts; private
  `origin` is the persistent authoritative mirror for committed/pushed state.

## Gate

* Fresh governance-revision gate on 2026-08-19 — **PASS**:
  `.venv/bin/ruff check .` — all checks passed;
  `.venv/bin/mypy --strict .` — success, no issues in **10 source files**;
  `.venv/bin/pytest -q` — **80 passed**;
  `.venv/bin/python tools/check_agents.py` — R1 (runtime LLM), R3 (resolver cache
  key), R7 (lecture coupling) pass.
* R13 is now an executable architectural rule but its implementation checks are
  intentionally assigned to the later D47-owning alignment/runtime/smoke work;
  the current gate scaffold therefore still reports R1/R3/R7 only.
* slice-3 remains unmerged, so main's 10-source-file / 80-test gate is expected
  to be smaller than slice-3's accepted worker gate. That divergence is not a
  regression.

## Escalation status

* none. slice-3 remains accepted on Attempt 1 under `Risk: none`. The ADR-0004
  governance revisions are owner-driven contract changes after acceptance, not
  WORKFLOW §5 implementation failures; no attempts or escalation positions are
  added.

## Sessions since last audit

* 3    <!-- unchanged: non-slice governance sessions do not increment it. Audit at >= 10 or a phase boundary. -->

## Blocked

* **ADR-0004 approval is the immediate blocker.** No implementation dispatch is
  allowed until a fresh cold orchestrator reviews the O4/O5 revision. If it
  approves, the review may administratively remove `NEEDS COLD REVIEW`; if it
  files new objections, AGENTS G7 requires another revision followed by another
  fresh cold review.
* **slice-3 closure remains PAUSED.** `slice/3` must not be merged, rebased or
  rewritten before ADR-0004 approval. After approval, the existing slice-3
  orchestrator must issue the implementation-alignment brief against the accepted
  D36/D45/D46/D47 Stage-01 contract, then obtain fresh gate/report acceptance
  before normal closure.
* **`reference/schema.sql` remains intentionally implementation-stale** against
  ADR-0004. PART-A omissions belong to slice-3 alignment; PART-B/runtime
  persistence belongs to slice-7; end-to-end replacement verification belongs to
  slice-8.
* **ADR-0002 D27 / ADR-0003 D27 share one decision ID.** Both accepted decisions
  remain valid; repair is separately parked.
* **`reference/smoke_test.py` remains path-broken/excluded.** slice-8 owns the
  repair and the D47 replacement/stale-picker smoke cases.
* **Compose integration remains independently blocked** by the lecture-app Phase
  4 decomposition/donor-evidence requirement; slice-9 owns that later check.
* **Build stage 04 remains time-bound to mid-September 2026** and now includes
  ADR-0004 multilingual enrichment. Its sequencing is unchanged.

## Next three actions

1. **Fresh ADR-0004 cold review** (WORKFLOW §7 / AGENTS G7) against committed
   repository-only context, specifically verifying D46/D47 and every cross-file
   pending amendment. No implementation dispatch.
2. **If approved:** remove `NEEDS COLD REVIEW` as the cold-review administrative
   close and return to the existing slice-3 orchestrator for the Stage-01
   implementation-alignment brief. **If objected:** revise the new numbered
   objections, then run another fresh cold review.
3. **After ADR-0004 approval and slice-3 alignment:** obtain a fresh gate/report
   acceptance for the aligned slice-3 work, then perform normal slice-3 closure.
