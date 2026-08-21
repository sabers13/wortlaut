# ADR-0005 — Pronunciation audio precedence and user overrides

**Status:** NEEDS COLD REVIEW

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

Upload and microphone recording use the same backend validation and persistence
contract.

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

### D51 — Stable pronunciation target identity

Durable custom pronunciation must never be keyed solely by asset-local numeric
`lemma_id` or `sense_id`.

The minimum durable target identity is ADR-0004 D47's stable lemma semantic
reference.

An optional stable sense/variant discriminator may additionally be used when a
real pronunciation distinction requires it.

A dictionary replacement must not silently attach a learner's recording to an
unrelated word because a numeric SQLite ID was recycled.

On dictionary replacement:

* exact stable semantic re-binding may restore the active association;
* no fuzzy/closest pronunciation-target guessing is allowed;
* if a target cannot be safely rebound, fail closed;
* preserve the learner-owned recording and its durable semantic identity even
  when it is temporarily unbound.

Custom-audio lifecycle must therefore follow the same general durable-identity
principle as ADR-0004 D47.

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

A previously cached and still-valid human recording may be used offline.

The implementation must not make first use appear broken while waiting for a
human-audio network fetch. Automatic local pronunciation remains available.

### D53 — Human-audio provenance and licensing

There is **no blanket Wiktionary/Wikimedia pronunciation-audio license** assumed
by this application.

License and attribution may differ per recording.

For each human recording retained in the automatic cache or distributed by an
approved packaging mechanism, metadata must retain enough information to identify
at least:

* upstream source/site;
* upstream stable file/page identifier or equivalent source reference;
* author/attribution when supplied or required;
* exact license/classification supplied for that recording;
* retrieval/cache metadata needed by the implementation to validate provenance.

If the required provenance/license metadata is insufficient under the
application's media-use policy, that human recording is ineligible and selection
falls through to Piper.

Piper engine/model/voice licensing is a separate licensing concern from
Wikimedia/Wiktionary human-audio licensing and must not be conflated with it.

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

This ADR does **not** change slice-6's Stage-03/04/05 multilingual
meaning-enrichment scope.

No bulk pronunciation asset is added to slice-6.

Primary implementation ownership is:

* **slice-7:** runtime/user-data pronunciation behavior, durable custom
  recording/upload persistence, stable semantic targeting, automatic precedence,
  human/Piper cache behavior, and the relevant API/render integration;
* **slice-8:** end-to-end smoke verification including custom override,
  Revert-to-automatic, offline fallback, unsafe-media rejection as applicable,
  and dictionary-replacement/stable-ref scenarios.

If cold review establishes that a real build-time metadata prerequisite must land
before slice-7, return to governance and amend sequencing explicitly. Do not
silently expand slice-6.

Future implementation briefs must independently apply WORKFLOW §6's path-based
risk lookup. In particular, user-data migration, public API or data-loss paths
may make the implementation risk-labeled even though this ADR drafting operation
is not a slice.

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
* slice-6 remains focused on Stage-03/04/05 multilingual meaning enrichment.
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
* runtime dependency graph remains free of LLM SDKs.

Exact HTTP/schema/file-layout assertions belong to the owning implementation
brief rather than this ADR unless cold review finds a missing architectural
contract.

---

## Cold review

This ADR has not yet received cold review.

Next required session:

**Cold review #1 — broad architecture challenge**, per WORKFLOW §7 / AGENTS G7.

No pronunciation implementation may begin while `NEEDS COLD REVIEW` remains.
