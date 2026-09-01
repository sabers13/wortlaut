# Slice 9 — Lecture-app compose-level integration

Task:        Compose the standalone browser product from `main` with the
             lecture-app on a single loopback-bound deployment unit per
             ADR-0002 §7, without coupling the flashcard repository to the
             lecture repository (AGENTS R7). Resolve the two pre-existing
             blockers recorded in STATE.md before any code moves: lecture-app
             Phase-4 decomposition (out of this repository) and the missing
             donor-evidence file `tasks/adr-0002-donor-notes.md`.

Depends:     slice-8

## Status at handoff pickup

* `main` is at the slice-8 closure HEAD; the standalone browser product is
  accepted, the FastAPI app factory, R12 browser guards, `/vocab` API, the
  full Lit/Vite/TypeScript/Playwright frontend, the deterministic-loading
  Playwright E2E, the real `.apkg` export, the audio precedence, and the
  Docker production image (frontend build stage → `uvicorn …
  create_production_app --factory --host 127.0.0.1 --port 8000`) are all
  shipped.
* `tasks/adr-0002-donor-notes.md` does not yet exist. It must be written
  before the first implementation dispatch of this slice.
* The lecture app's Phase-4 decomposition (its own `HostContext`
  simplification, content-boundary checks scoped to its rules, FABLE
  governance) is owned by the lecture-app repository, not this one. The
  flashcard side must compose via HTTP only.
* `recovery/s8e-rp20-final-candidate` is an audit-only ref recording the
  slice-8 closure lineage; it is not the canonical slice branch for this
  slice.

## Pre-dispatch prerequisites

1. **Donor-evidence file.** Author `tasks/adr-0002-donor-notes.md` per
   ADR-0002 §3 / WORKFLOW §12. The file records the read-only donor
   inspection findings (gating rules inherited, donor machinery
   excluded, lecture-app `HostContext` failure mode that ADR-0002 §7
   exists to prevent on the flashcard side). Donor inspection is
   read-only, complete-local-repo only, and must precede the first
   implementation dispatch.
2. **Lecture-app Phase-4 decomposition.** Confirm with the lecture-app
   repository owner that its Phase-4 decomposition is closed on the
     lecture side. Do not begin compose work while the lecture-app side
   is still decomposing HostContext.
3. **Orchestrator handshake.** A fresh orchestrator session reads this
   repository (governance, plan, backlog, ADRs, STATE.md, this brief,
   the slice-8 closure report), confirms the slice-8 closure lineage
   matches the committed tree, and runs the standard fresh-startup
   preflight before dispatching slice-9 implementation.

## Binding product contract

The controlling requirements are ADR-0002 §7, AGENTS R7 and R8 (zero
coupling + loopback binding), and the existing slice-8 contract. Any
slice-9 work that touches the lecture app's repository, the lecture app's
build, or the lecture app's persistence is out of scope and is a
Stop-and-ask condition.

## Outcomes

* The flashcard and the lecture app run as one loopback-bound deployment
  unit. The lecture app continues to own its own auth, content
  boundaries, and persistence; the flashcard continues to own its
  PART-A/PART-B separation, AGENTS R1/R3/R6/R7/R9/R10/R12/R13, and its
  FSRS scheduling authority.
* No new runtime dependency, no new build dep, no new persisted state,
  no second scheduler. Compose is an HTTP / loopback story only.
* Final authoritative gate on the compose-level candidate passes; the
  standalone slice-8 product continues to be exercisable in isolation.

## Risk

`public-api`, `auth-security` — compose surfaces cross-app HTTP paths
and any auth/token handoff between the apps; the full slice-9 brief must
spell out the cross-app security review per AGENTS R8 + R12 + the
accepted lecture-app auth model.

## Model

`codex/gpt-5.6-terra / T3 / high`

## Why

WORKFLOW §4 highest row: cross-cutting public-API surface, auth handoff,
and a binding contract from ADR-0002 §7 require design judgment.

## Fallback

`antigravity/gemini-3.7-flash / T3 / high` for implementation evidence;
the mandatory T3 cross-app risk review remains a fresh T3 Gemini/GPT
session.

## STOP conditions

Stop if any lecture-app code is required to land in this repository, any
AGENTS R7 coupling appears, any pre-existing blocker (donor-evidence
file, lecture-app Phase-4 decomposition) is not yet closed, the
slice-8 closure lineage does not match the committed tree, or any
required verification fails.

## Required closure evidence

Before Worker CLOSE, the Slice-9 orchestrator supplies `EXPECTED_MAIN_HEAD`
and the worker verifies the branch/base, runs the project gate using the
authoritative venv paths supplied by the orchestrator, runs frontend
build/type/Playwright checks, and proves only the union of the new
slice-9 allowlists plus the report changed. Then it records the exact
commands, gate numbers, compose-level E2E evidence, cross-app
auth-handoff evidence, and mandatory T3 review result in
`tasks/slice-9.report.md`. The closure worker alone performs the
mechanical merge, post-closure gate, handoff, and push under WORKFLOW
§11.