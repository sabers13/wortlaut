# ADR-0005 — Pronunciation audio precedence and user overrides

**Status:** ACCEPTED / FROZEN. Approved at cold review #2 — FOCUSED REMEDY VERIFICATION (2026-08-21). `NEEDS COLD REVIEW` is removed.

**Decision IDs:** D48–D56.

**Context:** This is a new additive architecture lineage after accepted
ADR-0001, ADR-0002 and ADR-0004. It does not reopen their unrelated decisions.

**Amends / clarifies:**

- ADR-0001 §11 Pronunciation (`IPA + audio`) by defining the runtime audio-source
  precedence and user override lifecycle;
- ADR-0002 D26 by placing its optional remote `/speak` path inside the automatic
  TTS fallback layer rather than making it the top-level pronunciation source.

**Preserves unchanged:**

- ADR-0001 D1 / AGENTS R1: no runtime LLM;
- ADR-0001 D8 / AGENTS R4: rendered faces are never stored;
- ADR-0001's IPA behavior: Wiktionary IPA with espeak-ng fallback;
- ADR-0002 D26: Piper remains authoritative local TTS capability; an optional
  configured remote `/speak` request is opportunistic only, has total timeout
  <= 1 second, and every remote failure falls back locally;
- ADR-0002's standalone architecture and browser boundary;
- AGENTS R9 separation between disposable dictionary/assets and sacred user data;
- ADR-0004 D47 stable semantic identity: numeric lemma/sense IDs are per-asset
  caches and never durable cross-version identity.

This ADR decides pronunciation **audio**, not IPA generation, card scheduling,
meaning generation, or a generic media-authoring system.

---

## 1. Context

The existing architecture already requires pronunciation on a German vocabulary
card and already chooses Piper as the reliable local TTS path. What it does not
yet define is what happens when better human audio exists, when the learner wants
to record or upload their own pronunciation, how those files survive dictionary
replacement, and which audio is disposable versus sacred user data.

Without one explicit precedence/lifecycle contract, implementation can easily
produce contradictory behavior:

- generated Piper audio overriding a learner's own recording;
- a downloaded human recording disappearing and making cards unusable offline;
- custom audio accidentally stored in a disposable cache;
- numeric dictionary IDs rebinding a user's recording to a different word after
  dictionary replacement;
- every Wikimedia/Wiktionary file being treated as if it had one blanket license;
- audio generation being pulled into the Stage-04 LLM pipeline even though no
  LLM is needed.

The architecture therefore needs a small pronunciation-source state machine with
clear ownership and failure behavior.

---

## 2. Decisions

### D48 — Pronunciation audio precedence

For pronunciation audio of a vocabulary target, selection order is:

1. **saved custom user audio**, when a valid explicit user override exists;
2. otherwise a **validated human pronunciation recording** obtained from an
   approved Wiktionary/Wikimedia source when safely available with sufficient
   provenance/license metadata;
3. otherwise the **automatic TTS path**, with local Piper always available as
   the correctness fallback.

When ADR-0002 D26's optional `tts_remote_url` is configured, its remote `/speak`
provider remains only an opportunistic optimization inside the automatic TTS
layer. It:

- does not override saved custom audio;
- does not override an already selected valid human recording;
- remains bounded by D26's <= 1 second total timeout;
- silently falls back to local Piper on timeout, connection error, non-2xx or
  invalid payload;
- never becomes a card/review/export correctness dependency.

With no optional remote composition provider configured, the effective
standalone precedence is therefore:

```text
custom user audio
    ↓
validated human recording
    ↓
local Piper generation/cache
````

Audio-source selection is computed from structured state. It is not baked into a
rendered card face.

### D49 — Custom pronunciation editing in v1

v1 supports **both**:

* browser microphone recording; and
* local audio-file upload.

The recording flow is intentionally small:

```text
Record
Stop
Preview
Save as pronunciation
Retake
Revert to automatic
```

A microphone take is never saved merely because recording stopped. Saving custom
audio is an explicit learner action.

Before explicit Save, microphone and upload preview bytes remain browser-local
only. The browser may hold them as temporary Blob/object-URL state or an
equivalent browser-local representation. Preview, Retake, and choosing another
upload replace only that temporary browser-local state.

The backend receives the media bytes only when the learner explicitly chooses
Save as pronunciation. Page close, navigation, refresh, or abandoning the edit
naturally discards the unsaved browser-local preview. Unsaved preview is not
sacred user data, is not backup/export state, and can never be an active custom
override.

On explicit Save, microphone and upload bytes enter the same backend
untrusted-media validation and durable-save contract. A failed validation or
failed save leaves any previously saved custom pronunciation unchanged.

If microphone permission is denied, unavailable or unsupported:

* Upload remains usable;
* Automatic pronunciation remains usable;
* the card remains functional.

Out of scope for v1:

* waveform editing;
* trimming UI;
* noise reduction;
* audio normalization editor;
* multi-track editing;
* any general audio-production interface.

### D50 — Sacred custom data vs. disposable automatic cache

Custom pronunciation audio explicitly saved by the learner is **sacred user
data**.

It must survive:

* application restart;
* container replacement/update;
* dictionary replacement;
* deletion/recreation of automatic pronunciation caches.

It therefore lives with user data, not with the disposable dictionary asset or
automatic media cache.

Backup/export policy for user-owned durable state must include custom
pronunciation audio where that backup/export operation claims to preserve user
data.

By contrast:

* cached human-audio downloads are disposable/reconstructable;
* Piper-generated audio is disposable/reconstructable.

Deleting or rebuilding an automatic cache must never delete learner custom
audio.

Saving a custom override does not destroy the automatic pronunciation path.

**Revert to automatic** removes or disables only the custom override needed to
restore automatic selection. It must not require deleting the human/Piper source
capability.

Replacing an existing saved custom pronunciation is commit-after-validation,
never delete-then-create. The candidate replacement is first received, bounded,
validated as actual media, and durably written under a non-active object identity.
Only after those steps succeed may the durable override metadata atomically
switch to the new object.

Until that activation commit succeeds, the old saved custom object remains the
active pronunciation and must not be destroyed. Failure or crash before the
activation commit leaves the old object active. Any unreferenced candidate object
left by an interrupted save is cleanup-only state and may be reclaimed
deterministically after recovery. After a successful activation commit, the
superseded object may be reclaimed according to implementation-owned cleanup
rules.

Exact paths and physical transaction/file mechanics are implementation-owned,
but no saved override may reference an incomplete or unvalidated object.

### D51 — Stable pronunciation target identity

Durable pronunciation state never treats asset-local numeric `lemma_id`,
`sense_id`, cache row IDs, or variant ordinals as authoritative identity.

v1 custom pronunciation ownership is **note-local**: a learner saves an override
for one vocabulary note. Custom media is not automatically shared or reused
between two notes merely because their dictionary targets happen to match.
Dictionary semantic identity is nevertheless persisted with the note-local media
so dictionary replacement can determine whether the saved association is still
safe.

The durable pronunciation-target hierarchy is:

1. A stable ADR-0004 D47 `lemma.semantic_ref` is sufficient only when the
   pronunciation is genuinely uniform for that lemma target.
2. When real pronunciation differs by semantic sense, the stable
   `sense.semantic_ref` is mandatory in addition to the lemma ref.
3. When a real pronunciation distinction exists that is not represented by
   sense identity, a deterministic stable `pronunciation_variant_ref` is
   mandatory.

`pronunciation_variant_ref` is intentionally narrow machinery, not a generic
pronunciation ontology. It is a namespaced/versioned deterministic fingerprint
over the stable lemma ref, the required stable sense ref when applicable, and the
canonical pronunciation-distinguishing information actually available for that
variant. The distinguishing information may include normalized IPA and an
upstream stable variant identifier or stable locale/dialect/region qualifier when
such metadata exists. A variant's ordinal, list position, database row number, or
other ordering local to one dictionary build is never durable identity.

If real variants exist but the available stable data cannot uniquely distinguish
the intended pronunciation, the identity is ambiguous and the association fails
closed. The implementation must not guess a variant, fall back to a first/nearest
variant, or fuzzy/closest rebind.

On dictionary replacement, only an exact unambiguous stable-identity match may
reactivate a saved association. Missing, disappeared, duplicate, or ambiguous
identity leaves the learner-owned media preserved but temporarily unbound. No
dictionary replacement may delete the recording merely because it cannot
currently be rebound.

### D52 — Offline and network failure behavior

Human pronunciation lookup/download is opportunistic.

No card, review, lookup, capture, export, or pronunciation correctness path may
depend on network availability.

If human audio is:

* unavailable;
* offline;
* timed out;
* invalid;
* unsupported;
* missing sufficient provenance/license information;

selection falls through to the automatic Piper-capable path.

A cached human recording is "still-valid" only when it satisfies D53's current
source/media-use-policy eligibility and D54's exact-object validation/integrity
contract. An entry that no longer satisfies either is disposable and is ignored
or invalidated; source selection continues through the automatic TTS path.

A previously cached and still-valid human recording may be used offline.

The implementation must not make first use appear broken while waiting for a
human-audio network fetch. Automatic local pronunciation remains available.

### D53 — Human-audio provenance, discovery and media-use policy

There is no blanket Wiktionary/Wikimedia pronunciation-audio license assumed by
the application.

Eligibility is governed by a **versioned, source-controlled application
human-media policy owned by the application maintainers**. Runtime responses,
remote free text, and per-user configuration cannot silently redefine that
policy. A policy version maps normalized upstream license/classification keys to
explicit application decisions, including whether disposable runtime caching is
permitted, whether redistribution/packaging is permitted, and which attribution
fields must be retained. The software contract records classifications and
applies the maintained policy; this ADR does not itself make a copyright
conclusion about an upstream work.

For v1, approved runtime human-audio discovery is deliberately narrow:

- generic live Wiktionary API lookup/page parsing remains rejected;
- no runtime free-text Wiktionary or Wikimedia search by lemma is introduced;
- a human recording may be considered only when source-backed dictionary data or
  an application-shipped/versioned pronunciation manifest already provides an
  exact upstream Wikimedia Commons file/page identity;
- from that exact identity, the runtime may resolve the corresponding Commons
  file metadata/media object using the approved metadata mechanism;
- if no exact approved identifier exists, human audio is simply unavailable and
  selection falls through to automatic TTS/Piper.

This is a pronunciation-file metadata capability, not a reopening of
ADR-0001's rejected "Live Wiktionary API at runtime" design: the application does
not fetch dictionary entries, parse wiki fields, depend on generic search, or make
human discovery a correctness dependency.

For every retained human recording, provenance metadata binds at least:

- application media-policy version;
- upstream source/site;
- canonical stable upstream file/page identifier or equivalent source reference;
- upstream metadata/revision identifier when supplied;
- immutable/retrieved media source reference;
- retrieval/cache metadata;
- author/attribution text when supplied or required;
- exact raw upstream license/classification;
- normalized policy classification key;
- the applicable runtime-cache and redistribution/packaging eligibility result.

Unknown, unsupported, conflicting, or insufficient required metadata fails
closed: that recording is ineligible and selection falls through to automatic
TTS/Piper.

Disposable runtime caching and redistribution/packaging are separate policy
decisions. A recording may be eligible for a reconstructable local runtime cache
without being eligible for redistribution. Packaging requires an explicit
policy result permitting redistribution and retention of every required
attribution/provenance field.

Piper engine, model/voice, and training-dataset classifications are separate from
human-recording classifications and remain independently recorded.

### D54 — Recording/upload validation boundary

Learner-supplied audio is untrusted input.

The implementation must enforce bounded acceptance, including:

* a supported audio container/codec set;
* bounded file size;
* bounded duration;
* validation of actual media content rather than trusting filename extension or
  browser-provided MIME alone;
* safe generated storage names/paths;
* no path traversal;
* no executable interpretation of uploaded content.

Exact safe limits and exact supported formats are implementation-slice decisions
and must be executable-tested unless a later cold-review blocker demonstrates
that a particular limit belongs in architecture.

Browser recording uses `getUserMedia` / `MediaRecorder` or equivalent normal
browser capability.

Microphone permission is requested only as needed for a user-initiated recording
action.

Downloaded human pronunciation media is untrusted input under the same
actual-content principle. Before downloaded bytes can become a valid automatic
cache entry, the application validates actual media content against
implementation-owned bounded supported container/codec, byte-size, and duration
limits.

After validation, provenance/license/policy metadata is bound to the exact
validated cached object through an immutable byte identity consisting of a
collision-resistant digest plus exact byte size, or an equivalent immutable
object identity. The chosen digest algorithm and safe media bounds are
implementation-owned and executable-tested.

On cache load, any missing bytes, corruption, digest mismatch, size mismatch,
metadata/object mismatch, unsupported content, or media-validation failure
invalidates that disposable entry. Invalid remote/downloaded media never becomes
a valid cache hit.

Invalidating human cache state always falls through to the automatic TTS path,
including ADR-0002 D26's optional bounded remote `/speak` optimization when
configured and local Piper as the correctness fallback. A corrupt human cache
must never make card display, review, lookup, export, or pronunciation unusable.

### D55 — No LLM or bulk pronunciation-generation pipeline

Pronunciation audio does **not** enter the multilingual LLM pipeline.

Specifically:

* no GPT/LLM pronunciation generation;
* no GPT-5.6 Luna pronunciation job;
* no runtime LLM;
* no bulk LLM-generated audio database;
* no whole-dictionary pre-generation of Piper audio in v1.

Piper audio is generated and cached on demand.

Human recordings may be fetched and cached opportunistically.

This keeps pronunciation media independent of slice-6's Stage-04 multilingual
meaning-generation workload.

### D56 — Ownership and sequencing

slice-6 retains its existing Stage-03/04/05 multilingual meaning-enrichment and
packaging scope. It additionally owns **only the build/runtime prerequisite**
needed to make the already-accepted Piper correctness floor executable before
runtime pronunciation work begins.

The slice-6 Docker/runtime foundation must:

- install and pin the Piper engine at image-build time;
- install one explicitly selected/pinned German voice/model at image-build time;
- verify the engine and selected voice/model are actually present and can be
  invoked in the built runtime image;
- record/verify the selected engine, voice/model and relevant dataset
  distribution license/classification and preserve any required notices or
  attribution;
- fail closed during the build/release process if the pinned artifact,
  classification, integrity information, or required distribution metadata
  cannot be established.

The initial pinned prerequisite is:

- engine package: `piper-tts==1.6.0`, current OHF-Voice Piper lineage,
  package classification `GPL-3.0-or-later`;
- German voice/model: `de_DE-thorsten-high` from `rhasspy/piper-voices`, pinned
  to immutable source revision
  `8aaa3c9839d2b669cb57a94e1ec92ae0928897e8`;
- model SHA-256:
  `9df1c43c61149ef9b39e618e2b861fbe41e1fcea9390b2dac62e8761573ea4f1`;
- preserve the voice repository's declared MIT metadata and the model card's
  Thorsten-Voice dataset classification `CC0`.

These records are artifact classifications used by the build/release contract,
not a claim that one license universally describes every Piper-related artifact.
If authoritative upstream metadata for the pinned artifact conflicts with the
recorded classification at implementation/release time, STOP at governance
rather than guessing.

This slice-6 addition is **not pronunciation feature implementation**. slice-6
must not add:

- bulk pre-generated Piper audio;
- a pronunciation database;
- runtime pronunciation source selection;
- a pronunciation/audio HTTP API;
- automatic pronunciation cache behavior;
- custom recording or upload persistence;
- human-audio discovery/download behavior;
- pronunciation UI/browser behavior.

Piper audio remains generated on demand by the later runtime feature; no
whole-dictionary pronunciation asset is created.

Primary feature ownership remains:

- **slice-7:** runtime/user-data pronunciation behavior: note-local custom
  recording/upload persistence, stable pronunciation targeting, source
  precedence, approved human discovery, human/Piper cache behavior, crash-safe
  replacement, and relevant API/render integration;
- **slice-8:** end-to-end pronunciation smoke including custom override,
  Revert-to-automatic, offline/Piper fallback, unsafe-media rejection,
  human-cache corruption fallback, preview lifecycle, and
  dictionary-replacement/stable-pronunciation-identity scenarios.

Future implementation briefs still apply WORKFLOW §6 path-based risk lookup from
their actual allowlists.

---

## 3. Automatic pronunciation behavior

Automatic pronunciation means the path used when no valid custom override is
active.

Conceptually:

```text
automatic(target)
    |
    +-- valid cached/available human recording? --> use human
    |
    +-- otherwise optional D26 remote speak?
    |       |
    |       +-- valid bounded response --> use response
    |       +-- failure ------------+
    |                                |
    +--------------------------------+
                                     v
                                local Piper
```

The optional remote D26 branch is not required to exist.

Human-source discovery and D26 remote TTS are both opportunistic network
capabilities; local Piper is the standalone correctness floor.

The cache may remember generated/downloaded automatic audio, but that cache is
not semantic user state.

---

## 4. Custom override behavior

Conceptual user-visible behavior:

```text
Pronunciation

Automatic
  validated human recording → Piper fallback/cache

Custom
  [Record] [Upload]
  [Preview]
  [Save as pronunciation]
  [Revert to automatic]
```

This is a non-normative UI sketch, not a frozen visual-design contract.

Normative behavior is:

* recording/upload does not become active until explicit Save;
* one active saved custom override wins over automatic selection;
* Retake may replace the unsaved preview without altering the currently saved
  pronunciation;
* failed validation cannot replace the currently saved pronunciation;
* Revert restores automatic source selection;
* automatic sources remain recoverable while custom audio is active.

---

## 5. Persistence and cache boundaries

The physical schema and exact paths are owned by the implementation slice, but
the lifecycle boundary is fixed:

```text
user-data domain
  custom pronunciation media
  durable stable semantic target
  custom-override metadata

disposable automatic-media domain
  human recording cache
  Piper generated cache
```

Dictionary assets remain separately disposable under AGENTS R9.

A valid implementation may use files plus user-DB metadata rather than storing
audio blobs inside SQLite, provided transactional/failure semantics prevent a
saved override from referencing an incomplete or missing committed media object.

The implementation slice must define and test crash-safe save/replacement
semantics before custom audio becomes active.

---

## 6. Dictionary replacement

Dictionary replacement follows ADR-0004 D47 identity principles.

Custom pronunciation:

* survives numeric ID renumbering;
* survives replacement when stable semantic identity still exists;
* is preserved but fails closed if the semantic target disappears;
* is never guessed onto a textually similar replacement;
* must not be deleted merely because an automatic dictionary/cache asset changed.

Automatic human/Piper cache entries may be invalidated and reconstructed.

---

## 7. Security and privacy consequences

Microphone access is local browser capability initiated by the learner.

No microphone recording happens without the user's explicit recording action.

Uploaded/recorded audio is user content and must not be sent to an LLM or remote
service merely to validate or process it.

The ADR does not introduce cloud synchronization.

Existing localhost/browser trust rules from ADR-0002/AGENTS R12 remain binding.

Exact media endpoint shapes are implementation-owned and will be risk-classified
from their actual allowlist before implementation.

---

## 8. Rejected alternatives

| Rejected                                                             | Reason                                                                                                                       |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Bulk pre-generated Piper pronunciation database                      | Large reconstructable asset with little benefit; on-demand Piper already provides the offline correctness floor              |
| LLM-generated pronunciation/audio                                    | Adds cost and failure modes to a deterministic local media problem and conflicts with the project's no-runtime-LLM direction |
| GPT-5.6 Luna pronunciation pipeline                                  | Stage-04 models are for localized learner meanings, not pronunciation media                                                  |
| Upload-only custom audio                                             | Needlessly denies convenient in-browser recording                                                                            |
| Recording-only custom audio                                          | Prevents use of existing learner-owned recordings                                                                            |
| Autosave immediately after microphone Stop                           | An accidental/bad take would overwrite durable user state without confirmation                                               |
| Destructive custom override that permanently removes automatic audio | Makes Revert impossible and couples sacred user state to disposable source lifecycle                                         |
| One blanket Wiktionary/Wikimedia audio license                       | License/provenance varies by recording and must be retained per file                                                         |
| Numeric dictionary IDs as durable custom-audio identity              | Rebuilt assets can recycle IDs for unrelated semantic entries                                                                |
| Remote human audio as a correctness dependency                       | Breaks offline operation and turns a card feature into a network availability problem                                        |
| Whole-dictionary pre-generation of Piper audio                       | Large unnecessary cache; pronunciation can be generated on demand                                                            |
| Waveform editing/audio-production suite in v1                        | Substantially expands product scope without being required for pronunciation overrides                                       |

---

## 9. Consequences

* Learners may replace automatic pronunciation with their own durable recording
  without forfeiting automatic fallback.
* Human recordings can improve pronunciation quality where licensing/provenance
  is sufficient, while Piper preserves complete offline availability.
* Custom media becomes sacred user data and therefore requires implementation
  attention to backup, replacement and crash-safe persistence.
* Automatic media remains disposable and reconstructable.
* Dictionary replacement must treat pronunciation bindings by stable semantic
  identity rather than numeric IDs.
* Human-media licensing becomes per-recording metadata rather than a package-wide
  assumption.
* slice-6 keeps its Stage-03/04/05 multilingual meaning enrichment work and adds
  only the image-build Piper engine+voice prerequisite; runtime pronunciation
  remains slice-7 and pronunciation smoke remains slice-8.
* slice-7 gains the runtime/custom-audio implementation contract.
* slice-8 gains end-to-end pronunciation smoke scenarios.
* No runtime LLM or pronunciation-specific paid generation pipeline is added.

---

## 10. Required implementation verification

The owning implementation/smoke slices must cover at minimum:

* custom saved audio wins over automatic audio;
* unsaved recording/upload preview does not replace the active pronunciation;
* Revert restores automatic selection;
* failed custom-media validation preserves the previously active state;
* human unavailable/invalid/offline falls through to Piper-capable automatic
  pronunciation;
* custom audio survives automatic cache deletion;
* custom audio survives dictionary numeric-ID renumbering when stable semantic
  refs match;
* unrelated recycled numeric IDs do not rebind custom audio;
* disappeared stable target fails closed without deleting learner media;
* human recording metadata preserves its actual source/license information;
* custom uploads cannot escape their storage boundary;
* runtime dependency graph remains free of LLM SDKs;
* lemma-only pronunciation identity is used only when genuinely lemma-uniform;
* sense-distinct pronunciation requires stable sense identity;
* non-sense pronunciation variation requires an unambiguous deterministic stable
  variant ref; build-local variant ordinal is rejected;
* ambiguous/missing pronunciation identity fails closed and preserves user media;
* custom pronunciation ownership is note-local and is not silently shared across
  notes;
* microphone/upload preview remains browser-local before Save;
* failed Save/validation and replacement crash preserve the old active saved
  object;
* exact-id Commons pronunciation metadata discovery does not become generic live
  Wiktionary/free-text lookup;
* unknown/unsupported media policy metadata fails closed;
* runtime-cache eligibility and redistribution eligibility are independently
  enforced;
* downloaded human bytes are actual-media validated before caching;
* human cache metadata is bound to the validated object's digest+size/equivalent
  immutable identity;
* missing/corrupt/mismatched human cache always falls through to automatic
  TTS/local Piper.

Exact HTTP/schema/file-layout assertions belong to the owning implementation
brief rather than this ADR unless cold review finds a missing architectural
contract.

---

## Cold review

Cold review #1 — BROAD ARCHITECTURE CHALLENGE — recorded blocking objections
O1–O5 below. The 2026-08-21 governance revision applied the explicit remedies.
Cold review #2 — FOCUSED REMEDY VERIFICATION — approved the ADR. `NEEDS COLD REVIEW` is removed. ADR-0005 is ACCEPTED / FROZEN.

The slice-6 Piper image-build prerequisite is a build/runtime foundation
amendment, not pronunciation feature implementation. Runtime pronunciation
remains slice-7 and pronunciation smoke remains slice-8.

### Cold review #1 — BROAD ARCHITECTURE CHALLENGE — OBJECTIONS

**Reviewer:** fresh cold-review orchestrator session, 2026-08-21, repo-only
context per WORKFLOW §7 / AGENTS G7.

**Verdict: OBJECTIONS — `NEEDS COLD REVIEW` stays.** D48's top-level precedence,
D50's sacred-vs-disposable separation and crash-safety invariant, ADR-0002/R12
browser guards, opportunistic network fallback, the no-runtime-LLM boundary, and
the ordinary-export/full-backup distinction are sound. The blockers below are
concrete executability, persistent-identity, data-lifecycle, licensing, and cache
integrity defects.

### O1 — BLOCKING. Piper is the accepted offline floor, but no executable slice owns putting the engine/voice into the runtime image.

**Conflicting contract.** ADR-0001 §12 requires the Piper voice to be downloaded
at image-build time. ADR-0002 D26 makes local Piper the authoritative TTS fallback.
ADR-0005 D48/D52/D55 again require local Piper to be the always-usable offline
floor and generate/cache it on demand. Yet `tasks/slice-6.md` owns the project's
first Dockerfile and A12 limits that Docker foundation to Python/runtime
requirements plus `de_core_news_md`, says not to invent pronunciation/audio
architecture, and says a later accepted pronunciation ADR may require a brief
amendment. D56 instead says slice-6 remains unchanged and assigns pronunciation
implementation to slice-7/8; `docs/plan.md` likewise gives slice-7 runtime work
but no explicit Docker/Piper prerequisite.

**Concrete failure mode.** slice-6 can correctly close under its current brief
with an image containing no Piper engine or voice. slice-7 can then implement the
pronunciation state machine while the runtime image lacks the capability that
D26/D48 define as the correctness floor. A worker would have to silently expand a
closed slice, silently reopen the Docker contract in slice-7, or ship a runtime
whose offline fallback is false. The separate Piper engine/model/voice licensing
statement in D53 also has no owner at the point the distributable image must
choose and carry that artifact.

**Why blocking.** This is a direct accepted-ADR/slice sequencing contradiction and
makes the offline correctness floor non-executable as currently briefed.

**Required remedy direction.** Assign the build-time Piper prerequisite
explicitly before pronunciation runtime work. The straightforward repair is to
amend D56, `docs/plan.md`, `docs/backlog.md`, and `tasks/slice-6.md` so slice-6's
Dockerfile installs and verifies a pinned Piper engine plus selected voice/model
at image-build time, with the voice/model license/classification and attribution
checked for distribution. This is runtime capability only: it must not add a
bulk pre-generated audio database or pronunciation LLM work. If governance
instead deliberately assigns the Dockerfile amendment to slice-7, that ownership
must be explicit in D56/plan/the future slice-7 brief and must land before any
pronunciation path can claim Piper availability; it may not remain implicit.

**Resolution (2026-08-21 revision): APPLIED.** D56 now assigns slice-6 only the
Piper build/runtime prerequisite: a pinned engine and German voice/model are
installed and verified at image-build time with artifact
license/classification/integrity records. Runtime pronunciation behavior remains
slice-7 and end-to-end pronunciation smoke remains slice-8. No bulk audio,
pronunciation DB/API/cache/custom-media/human-discovery/UI work enters slice-6.
The same prerequisite is propagated through the accepted-ADR amendment records,
`docs/plan.md`, `docs/backlog.md`, and `tasks/slice-6.md`.

### O2 — BLOCKING. D51's lemma-only minimum identity can persistently bind audio to the wrong pronunciation variant.

**Conflicting contract.** D51 makes ADR-0004 D47's stable lemma semantic ref the
minimum durable pronunciation target and says a stable sense/variant discriminator
"may" be added when a real pronunciation distinction requires it. D47's
`lemma.semantic_ref` is derived from German lemma text, POS and gender, while
`sense.semantic_ref` is the stable sense-level identity. The lemma ref therefore
does not, by construction, distinguish every pronunciation-bearing sense or
variant.

**Concrete failure mode.** German can have pronunciation/stress/separability
distinctions under the same written lemma and POS. If an implementation exercises
D51's permitted lemma-only identity, custom audio saved for one such target can be
reused or rebound to a different pronunciation-bearing sense after note reuse or
dictionary replacement even though numeric IDs were avoided. That is a materially
wrong persistent association, not merely a UI preference.

**Why blocking.** The ADR's durable identity rule explicitly permits a key that is
not sufficiently discriminating for the state it persists.

**Required remedy direction.** Define the ownership/key of custom pronunciation
unambiguously (for example note-local versus reusable target media) and make a
stable discriminator mandatory whenever more than one real pronunciation can
share a lemma ref. Use a stable `sense_ref` when sense identity is the distinction,
or define a deterministic stable pronunciation-variant ref when the distinction
is not sense-based. Missing/ambiguous discriminators must fail closed; numeric
variant order and fuzzy/closest rebinding remain forbidden.

**Resolution (2026-08-21 revision): APPLIED.** D51 now makes v1 custom
pronunciation ownership note-local and defines an executable identity hierarchy:
lemma ref only for genuinely lemma-uniform pronunciation, mandatory stable
sense_ref for sense-distinct pronunciation, and a deterministic stable
pronunciation-variant ref when a real distinction is not represented by sense
identity. Numeric IDs and build-local variant ordinal/order are non-authoritative;
missing/ambiguous identity fails closed; no fuzzy/closest rebinding is permitted;
learner media is preserved while temporarily unbound.

### O3 — BLOCKING. Unsaved microphone/upload preview bytes have no lifecycle or storage owner.

**Conflicting contract.** D49 defines `Stop -> Preview -> Save`, says stopping is
not saving, and says upload and microphone recording share backend validation and
persistence semantics. D50/§5 classify saved custom media as sacred and automatic
human/Piper media as disposable, but the unsaved preview is in neither domain.
The ADR states that Retake may replace the preview, but does not say whether that
preview is browser-only, server-staged, persisted across restart, backed up, or
cleaned after abandonment/crash.

**Concrete failure mode.** A conforming backend can stage microphone/upload bytes
on disk for preview yet have no rule that removes an abandoned take after Retake,
page close, validation failure, process restart, or crash. Private user recordings
can accumulate indefinitely or be deleted/retained inconsistently because they
are neither sacred saved media nor an owned disposable cache.

**Why blocking.** This is an unowned user-content lifecycle at the microphone /
upload privacy boundary.

**Required remedy direction.** Classify unsaved preview explicitly. Either keep it
browser-local until Save, or define a dedicated temporary staging domain with a
single owner and deterministic cleanup/recovery rules. It must never become the
active override or full-backup data before explicit Save; Retake/failed validation
may alter only the preview; Save promotes validated media through the D50
crash-safe boundary without endangering the currently saved file. Exact TTLs and
file paths may remain implementation-owned.

**Resolution (2026-08-21 revision): APPLIED.** D49/D50 now choose the
browser-local preview model. Microphone/upload bytes stay in browser-local
temporary state until explicit Save; Retake or abandonment touches no saved
media, and navigation naturally discards the preview. Save is the first backend
media transfer and uses the common untrusted-media validation plus crash-safe
promotion contract. A replacement never destroys the old active object until the
new media is durably validated and atomically activated.

### O4 — BLOCKING. Human-recording eligibility is circular, and the runtime discovery path is not reconciled with the accepted live-Wiktionary rejection.

**Conflicting contract.** D48 permits a human recording only from an "approved
Wiktionary/Wikimedia source" and D53 rejects media whose metadata is insufficient
under "the application's media-use policy", but neither the approved-source set,
the media-use policy, nor the owner/version of that policy exists in the
repository. Separately, ADR-0001 §9 rejects a live Wiktionary API at runtime,
while D52/§3 introduce opportunistic human-source lookup/download without saying
whether that accepted rejection still applies to pronunciation discovery.

**Concrete failure mode.** slice-7 cannot deterministically decide whether a
recording with a particular license/classification is eligible for runtime cache
or packaging, nor whether querying Wiktionary live for pronunciation metadata is
forbidden or is a narrow supersession. Two conforming implementations can accept
different licenses/sources or one can silently violate an accepted rejected
runtime dependency.

**Why blocking.** Eligibility and discovery require product/distribution policy,
not a codec implementation detail; leaving them undefined makes the feature
non-deterministic and risks incompatible distribution/provenance handling.

**Required remedy direction.** Define a versioned/owned human-media eligibility
contract: approved discovery/source mechanisms, normalized license/classification
handling, required attribution fields, fail-closed treatment for unknown or
insufficient metadata, and any distinction between disposable runtime caching and
redistribution/packaging. Explicitly reconcile ADR-0001's live Wiktionary API
rejection: either keep it forbidden and choose a compliant discovery mechanism
(such as a permitted Wikimedia/static-metadata path), or record a narrow explicit
supersession for pronunciation metadata. Do not invent copyright conclusions;
make the software's accept/reject rule executable.

**Resolution (2026-08-21 revision): APPLIED.** D53 now gives human-media
eligibility one versioned source-controlled policy owned by the application
maintainers, defines required provenance/classification fields and fail-closed
behavior, and separates disposable runtime-cache eligibility from
redistribution/packaging eligibility. v1 discovery is limited to resolving exact
Wikimedia Commons file/page identities already supplied by source-backed
dictionary data or a versioned application manifest; generic live Wiktionary
lookup/page parsing and free-text runtime search remain rejected.

### O5 — BLOCKING. "Cached and still-valid human recording" has no byte-integrity/provenance-binding contract.

**Conflicting contract.** D48 selects only a validated human recording and D52
allows a cached human recording when "still-valid"; D53 requires provenance
metadata. But D54's actual-content, bounded-media validation applies only to
learner-supplied upload/recording, and no decision states how downloaded human
bytes remain bound to the provenance/license record that describes them.

**Concrete failure mode.** A downloaded cache file can be truncated, replaced, or
mismatched with stale metadata and still be served as the attributed/licensed
human recording; alternatively malformed remote media can bypass the explicit
learner-media validation boundary. In either case the application can serve
corrupt or misattributed bytes instead of invalidating the entry and using Piper.

**Why blocking.** This is an integrity/provenance failure in a runtime media path,
not a cache-eviction optimization.

**Required remedy direction.** Treat downloaded human media as untrusted bytes as
well. Define a cache-validity invariant that validates supported media/bounds
before first use and binds retained provenance to the exact validated object
(e.g. digest + byte size or an equivalent immutable identity). On cache load,
corruption, metadata/object mismatch, unsupported content, or failed validation
invalidates the disposable entry and falls through to Piper. Exact safe limits,
container/codec set, and chosen digest mechanics may remain implementation-slice
decisions.

**Resolution (2026-08-21 revision): APPLIED.** D52/D54 now define
"still-valid" human cache by both policy eligibility and exact-object integrity.
Downloaded media is untrusted and must pass actual-media validation before
becoming a cache entry; provenance/license/policy metadata is bound to the
validated bytes by digest+size or equivalent immutable identity. Missing,
corrupt, mismatched, unsupported, or failed-validation cache entries are
disposable and always fall through to automatic TTS/local Piper rather than
breaking pronunciation or card/review behavior.

### Cross-file remedy requirement

Resolving O1–O5 must propagate the resulting accepted contract through the
repository memory rather than relying on this ADR alone. In particular, use
amendment/supersession records rather than rewriting historical accepted ADR
bodies; reconcile ADR-0001 §11/§12/§9 and ADR-0002 D26 where the remedies require
it; update `docs/plan.md` slice-6/7/8 ownership and `docs/backlog.md`; and amend
`tasks/slice-6.md` before dispatch if O1 assigns the Piper image prerequisite to
slice-6. Existing AGENTS R1/R9/R12/R13 are otherwise sufficient; no new AGENTS
rule is required by this review.

### Cold review #2 — FOCUSED REMEDY VERIFICATION — APPROVED

**APPROVED — remove NEEDS COLD REVIEW.**

The focused remedy verification found no qualifying material blocker under
WORKFLOW.md §7 / AGENTS G7. O1–O5 and all of their resolution records remain
preserved. Their cross-file remedies are coherent, D48–D56 and every Rejected
alternative remain unchanged, and no serious correctness, executability,
integrity, persistent-state, security, or licensing-policy blocker remains.

ADR-0005 is accepted and frozen. Administrative approval/removal of
`NEEDS COLD REVIEW` does not create another cold-review requirement. No cold
review #3 is required for this approved lineage.
