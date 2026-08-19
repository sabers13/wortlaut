# ADR-0003 — Five-level confidence rating (CBR-style) layered over FSRS

**Status:** Accepted 2026-08-19 (owner-approved in conversation). Cold review approved 2026-08-19 after revision; see `## Cold review`.
**Amends:** ADR-0001 §10 body semantics for `POST /vocab/review` and
`GET /vocab/decks`, whose `/vocab` route prefix is fixed by ADR-0002 D25, and
ADR-0001 §11 (rating UI only). D6 (FSRS + append-only `review_log`) is explicitly
unchanged.

## 1. Context

Brainscape's Confidence-Based Repetition asks, after each card, not "did you get
it right" but "how confident are you," on a 1–5 scale (1 = clueless … 5 = 100%
sure you'll never forget). Its product uses a characteristic interval *shape*
(very low confidence returns sooner; high confidence graduates farther out), a
per-deck **mastery %**, and a metacognition loop in which each reappearance tests
the previous self-rating. Its exact scheduling core is proprietary and
unpublished.

This ADR adopts the five-level confidence framing and mastery surface, **not a
promise to reproduce Brainscape's five interval bands**. FSRS remains the
scheduler. With the v1 FSRS configuration, confidence 1 and 2 intentionally map
to the same FSRS grade and therefore schedule identically on a new card; §4
states that cost explicitly.

## 2. Decisions

| # | Decision | Rationale |
|---|---|---|
| D27 | **The review UI shows five confidence buttons** (1 "not at all" … 5 "never forget"), with confidence phrasing, not correctness phrasing | The metacognitive framing is CBR's real contribution and is pure UI |
| D28 | **A single function maps confidence → FSRS rating:** `{1: Again, 2: Again, 3: Hard, 4: Good, 5: Easy}` | FSRS defines Hard as *successful* recall with difficulty; feeding failures in as Hard is the classic misuse that corrupts scheduling. Confidence 1 and 2 are both "I didn't really know it" |
| D29 | **`review_log` stores the raw confidence (1–5) alongside the mapped rating (1–4)** | The mapping stays revisable for free: change the dict, replay the log (the derived-state option ADR-0001 §14 reserves). Without the raw value, a mapping change is irreversible |
| D30 | **Deck mastery % includes every enabled card in the deck; unreviewed = 0.** `100 * SUM(COALESCE(latest_confidence(card), 0)) / (5 * COUNT(deck_cards))`; empty deck = 0% | 100% is reachable only when every enabled card has latest confidence 5. The card set follows D5 templates; adding templates changes the denominator, so mastery is not cross-version comparable. Because D12 shares card state across decks, the latest confidence may come from a review launched from another deck; mastery means competence over this deck's cards, not reviews performed inside this deck |
| D31 | **FSRS learning steps are enabled as `(1 min, 10 min)` for v1** | Gives short within-session repetition while preserving FSRS grade semantics. It does not distinguish confidence 1 from 2 in scheduling; the raw distinction remains in the log and mastery surface |

## 3. Rejected

| Rejected | Reason |
|---|---|
| Implementing Brainscape's actual scheduler (interval table keyed on confidence + staleness heuristics) | Hand-tuning a worse algorithm to imitate a closed one; FSRS gives the same visible behaviour with published, per-user-optimisable retention math |
| Replacing FSRS with CBR | Loses log-based parameter optimisation and the current state of the art for an unreproducible proprietary design |
| Mapping 2 → Hard | Violates FSRS grade semantics (Hard = successful recall); known failure mode |

## 4. Cost, stated

The five UI values collapse onto four FSRS grades. For a **new card** under the
v1 compatibility baseline (`fsrs==6.3.2`, `learning_steps=(1 min, 10 min)`),
the expected first transition is:

| Confidence | Mapped grade | Expected next state / interval |
|---|---|---|
| 1 | Again | Learning step 0 — 1 min |
| 2 | Again | Learning step 0 — 1 min; identical to 1 |
| 3 | Hard | Learning, approximately 5.5 min |
| 4 | Good | Learning step 1 — 10 min |
| 5 | Easy | graduates to Review; FSRS-computed interval in days |

So 1/2 collapse completely for new-card scheduling, and the 3/4 spacing is much
closer than Brainscape-style marketing bands. This is accepted deliberately: (a)
FSRS grade semantics stay correct, (b) raw confidence is preserved for mastery
and replay, and (c) the UI promise is metacognitive confidence plus a monotone
*shape*, not five distinct scheduler buckets. A future design may differentiate
1/2 through scheduler configuration, but may not smuggle failure in as `Hard`
(the rejected 2 → Hard alternative remains rejected).

## 5. Persistence, API, and acceptance impact

`review_log.confidence` is not merely an optional column. Because no pre-ADR-0003
user database exists, every new row is constrained at the schema boundary:

- `confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5)`
- `rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4)`

Together with the append-only write path, those constraints make AGENTS R6
executable rather than review-only. `reference/schema.sql` is normative for the
rewrite.

ADR-0001 §10 is amended at the API **body-semantics** boundary. ADR-0002 D25
owns the route prefix, so the actual standalone routes are unambiguously:

- `POST /vocab/review` accepts **only** `confidence` 1–5 from clients. The server
  maps confidence → FSRS rating through the single D28 function and persists both.
  A client-supplied `rating` field is rejected.
- `GET /vocab/decks` returns `mastery_percent` alongside due counts, using D30's
  full denominator.

This prefix clarification does not change D27–D31; this ADR owns the
confidence/mastery request/response semantics, while ADR-0002 D25 owns the
`/vocab` path boundary.

`reference/smoke_test.py` remains the acceptance baseline but must be amended in
the first slice that makes it executable: `deck.review(db, card_id, confidence)`
replaces positional FSRS-grade calls, and the test asserts both raw `confidence`
and mapped `rating` were appended. Its separately filed import-path defect is
unchanged (docs/backlog.md).

## 6. FSRS compatibility pin and gate

v1 pins `fsrs==6.3.2`, the review-time compatibility baseline used for §4's
worked table. A version bump is an explicit dependency change: update the
five-case scheduler test and this table if behaviour changes. The gate test
creates a new card and submits confidence 1–5 through the server-side mapping;
it asserts the mapped grades, the 1/2 equality, the 3/4 learning-step intervals,
and confidence 5's graduation to Review.

---

## Cold review

**Reviewer:** fresh orchestrator session, 2026-08-19 (Opus 5). Repo-only context,
per WORKFLOW.md §7 / PROMPTS.md §ADR cold review. The draft was written outside
any orchestrator session, so this session is a valid cold reviewer.

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** The central insight (CBR's
value is the metacognitive framing, which is separable from its scheduler) is
correct, and D28's refusal to map 2 → Hard is the right call for the right
reason. The objections are that §1's behavioural promise is not delivered by
D28+D31, that D30's formula contradicts its own description, and that §5
understates the impact to one column when it is in fact a schema constraint, an
API contract, and the acceptance baseline. O1–O5 are BLOCKING; O6 is MINOR.

### O1 — BLOCKING. §1's behavioural spec is not reproduced, and §4 understates the collapse.

§1 sells CBR's user-visible behaviour as "1s return within minutes, 2s after
~10+ minutes, 3s in hours, 4s in days, 5s in weeks–months", and D31 claims
enabling learning steps "reproduces CBR's within-session return of 1s and 2s".
Worked through D28's mapping against py-fsrs's actual Learning-state logic with
the default `learning_steps = (1 min, 10 min)` that D31 cites:

| Confidence | FSRS grade | New card, actual next interval |
|---|---|---|
| 1 | Again | step → 0, **1 min** |
| 2 | Again | step → 0, **1 min** — identical to 1 |
| 3 | Hard | step unchanged, `(1 + 10) / 2` = **5.5 min** |
| 4 | Good | step → 1, **10 min** |
| 5 | Easy | leaves Learning, **days** |

So on a new card only confidence 5 behaves as §1 promises. 1 and 2 are
*indistinguishable*, which is the opposite of the "1s vs 2s" distinction D31
claims to reproduce; 3 returns in minutes, not hours; 4 in minutes, not days.
§4 "Cost, stated" mentions only that "two adjacent confidence levels can
schedule identically" and names 3/4 — the 1/2 collapse, which is the more
visible one because §1 advertises it, is unstated.

This matters beyond documentation: the metacognition loop in §1 depends on the
user perceiving that their rating changed something. Two buttons that do
provably nothing different train the user to stop distinguishing them.

*Remedy:* one of —
(a) restate §1 as an interval *shape* the design approximates, and rewrite §4 to
state both collapses explicitly, including the new-card table above; or
(b) differentiate 1 and 2 without breaking FSRS grade semantics — e.g. a
three-step `learning_steps` where confidence 2 advances the step and confidence
1 resets it, which is a scheduler-configuration decision, not a grade
misuse, and would need its own decision row plus a note on how it interacts with
`relearning_steps`.
Do not resolve it by mapping 2 → Hard; §3 rejects that correctly.

**Resolution (2026-08-19 revision): APPLIED, option (a).** §1 now promises the
five-level confidence framing and an interval shape, not Brainscape's exact
bands. D31 fixes v1 learning steps at 1/10 minutes, and §4 includes the new-card
table with the 1/2 collapse and compressed 3/4 spacing stated as accepted cost.
The rejected 2 → Hard mapping remains rejected.

### O2 — BLOCKING. D30's formula contradicts §1's "100% only when everything is a 5".

`AVG(latest confidence per card) / 5` is an average over cards that **have** a
latest confidence. A deck of 100 cards with one review of 5 evaluates to 100%.
§1 states mastery reaches 100% "only when everything is a 5", so the ADR
contradicts itself. The formula is also underspecified against two ADR-0001
decisions it must live with:

- **D5** — three templates per note, each its own `card` row with its own FSRS
  state. Is mastery over cards or over notes? Over cards, a v1 deck (recognition
  only) and a v2 deck (three templates) are not comparable numbers.
- **D12** — notes are many-to-many with decks. Mastery of a lecture deck counts
  cards mostly reviewed from a different deck. That is defensible (one FSRS
  state is the point of D12) but should be stated, or the number reads as a lie
  about that lecture.

*Remedy:* define the denominator as every card in the deck with unreviewed cards
counting as 0 (which makes §1's claim true), state the card set explicitly with
respect to D5 templates, and state the D12 consequence in one line.

**Resolution (2026-08-19 revision): APPLIED.** D30 now includes every enabled
card whose note belongs to the deck, counts unreviewed cards as zero, defines an
empty deck as 0%, states that template expansion changes the denominator, and
records that D12-shared latest confidence can originate from a review launched
from another deck.

### O3 — BLOCKING. §5's "one column" is wrong on disk, and the column as applied cannot enforce AGENTS R6.

§5 says the schema impact is one column and that it is "already applied to
`reference/schema.sql`". On disk that column is:

```sql
confidence     INTEGER,               -- 1-5; NULL only for pre-ADR-0003 rows
```

There are no pre-ADR-0003 rows and there never will be: `app/` does not exist,
no user database has ever been created (STATE.md "Blocked"). The justification
for nullability is empty, while AGENTS R6 says "**Every** review row carries both
the raw 1–5 confidence and the mapped FSRS rating" and D29's whole value — the
mapping stays revisable by log replay — fails for any row where confidence is
NULL. A nullable column makes R6 unenforceable at the only layer that could
enforce it cheaply, and R6 is on docs/backlog.md's standing list of
`[reviewed]` → `[executable]` conversions.

*Remedy:* `confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5)`, plus
`CHECK (rating BETWEEN 1 AND 4)` on the mapped grade, and delete the
"pre-ADR-0003 rows" comment. State in §5 that this is what makes R6 executable.

**Resolution (2026-08-19 revision): APPLIED.** `reference/schema.sql` now
requires confidence 1–5 and rating 1–4 with `NOT NULL` + `CHECK`; the nonexistent
legacy-row exception is gone. §5 makes those constraints normative and AGENTS
R6 is now `[executable]` with schema/write-path gate coverage.

### O4 — BLOCKING. The API contract is not amended, and that lets R6 be bypassed.

The `Amends:` line says "ADR-0001 §11 (rating UI only)". But ADR-0001 §10 is the
endpoint table, and two rows of it are now wrong:

- `POST /review` — "Rating 1–4, returns next due". Under D27/D29 the request
  must carry confidence 1–5.
- `GET /decks` — "List with due counts". D30 puts mastery % on the deck list.

More than tidiness: if `/review` keeps accepting a `rating`, a client can submit
a mapped grade with no raw confidence, and R6's guarantee is gone at the API
boundary rather than the DB one.

*Remedy:* extend `Amends:` to ADR-0001 §10 and specify: the request field is
`confidence` (1–5); the confidence → grade mapping is applied server-side and
**only** server-side; `rating` is not accepted from clients; `GET /decks`
returns mastery alongside due counts.

**Resolution (2026-08-19 revision): APPLIED.** `Amends:` now includes ADR-0001
§10. §5 defines `POST /review` as confidence-only input with server-only D28
mapping and rejection of client `rating`; `GET /decks` returns
`mastery_percent` with due counts. The original ADR-0001 body remains immutable;
its supersession header already establishes later-ADR precedence.

### O5 — BLOCKING. The acceptance baseline contradicts D28/D29.

`reference/smoke_test.py` — named as the acceptance baseline for the `app/`
rewrite by both STATE.md and docs/backlog.md — calls:

```python
deck.review(udb, cid, 3)    # positional FSRS grade
deck.review(udb, cid, 1)
```

Under D28/D29 that signature must take a confidence and log both values. The ADR
does not mention the baseline, so a worker rewriting `deck.py` against it would
reproduce the pre-ADR-0003 contract and pass its acceptance test.

*Remedy:* state the baseline amendment as a consequence, naming the intended
signature (e.g. `deck.review(db, card_id, confidence)`), and require the test to
assert that both `confidence` and `rating` are persisted.

**Resolution (2026-08-19 revision): APPLIED.** §5 names
`deck.review(db, card_id, confidence)` as the baseline contract and requires the
smoke test to assert both raw confidence and mapped rating are appended. The
known path break is left for the `app/` rewrite.

### O6 — MINOR. D31's py-fsrs claim is correct but unpinned.

Verified: the `fsrs` package's `Scheduler` does accept `learning_steps` and
`relearning_steps`, and its documented default is 1 minute then 10 minutes —
D31's "(e.g. 1 min, 10 min)" and "py-fsrs supports it directly" both hold. But
the ADR pins no minimum version, and the Learning-state arithmetic that O1's
table depends on is version-specific behaviour.

*Remedy:* pin a minimum version in the ADR (current release at review time:
`fsrs` 6.3.2, 2026-08-09) so the interval table above is falsifiable, and add a
test that asserts the five confidence levels produce the intervals the ADR
claims — that converts O1's remedy into a gate check rather than a paragraph.

**Resolution (2026-08-19 revision): APPLIED, stronger than minimum pinning.**
§6 fixes the v1 compatibility baseline at `fsrs==6.3.2` and requires a five-case
gate test covering the mapping, 1/2 equality, 3/4 learning-step intervals, and
confidence 5 graduation. Any dependency bump must update the test/table if the
behaviour changes.

### Checked and found sound (no objection)

- **D28's mapping** against FSRS grade semantics — Hard means *successful*
  recall with difficulty; feeding a failure in as Hard corrupts difficulty
  estimation. Confidence 1 and 2 both being "I didn't know it" is the correct
  reading, and §3's rejection of 2 → Hard is right.
- **D29** against AGENTS R6 and ADR-0001 §14's reserved log-replay option — the
  raw value is what keeps the mapping revisable; this is the load-bearing
  decision of the ADR and it is correct.
- **D6 declared unchanged** — accurate: nothing here touches FSRS itself or the
  append-only property.
- **§3's rejections** — reimplementing a closed scheduler, and replacing FSRS,
  are both dismissed with stated costs rather than asserted.
- **§4's existence** — an ADR that states its own cost before review is doing
  the right thing; the objection is that the statement is incomplete (O1), not
  that it is missing.

### Fresh cold review — 2026-08-19

**Verdict: APPROVED — remove `NEEDS COLD REVIEW`.** O1–O6 are resolved as
recorded. The revised confidence contract is coherent with ADR-0001's
supersession header, AGENTS R6, `reference/schema.sql`, and the still-filed
smoke-test rewrite requirement: clients provide confidence only, the server maps
and logs both values, mastery counts unreviewed cards as zero, and the scheduler
behaviour is pinned and gate-specified. No unresolved objection remains.

