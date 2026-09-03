# Slice 13 — Online dictionary production publication

**BLOCKED until ADR-0009 is frozen and Slices 11 and 12 are accepted and
merged.**

Task: Publish the validated ADR-0009 v2 online shard corpus only after the
infrastructure and session/UI slices are accepted.

Depends: ADR-0009 approved and frozen; slices-11 and -12 accepted and merged.

Allowlist:
- `release/dictionary-online-manifest-v2.json`, `release/README.md`, and new
  online-release attribution/validation records under `release/`
- `tools/build_online_dictionary.py` and new
  `tools/verify_online_dictionary_release.py`
- `tasks/slice-13.report.md`

Required reading: `docs/adr/0009-session-scoped-online-dictionary.md`,
`AGENTS.md`, the accepted Slice-11 and Slice-12 reports, current release
manifest/attribution files, publication tooling, and `tasks/slice-13.md`.

Acceptance:

1. Build the production corpus from the verified v2 full dictionary using the
   accepted deterministic builder; record input identity, all output hashes,
   counts, size distribution, free-space checks, and the same logical dataset
   token.
2. Run the specified production differential sample against the local
   provider and fail closed on any semantic, routing, count, or integrity
   mismatch. The differential sample explicitly includes lookup
   normalization/routing per the accepted `bucket256_v1` closure rule (ASCII
   case, umlauts, ß, NFC and deliberately non-NFC input, surface forms, exact
   lemmas, unknown values), not only lemma/sense content parity.
3. Count **all** uploaded release files against GitHub's 1,000-asset-per-release
   ceiling, not merely the 577 corpus assets (manifest, attribution, and any
   other uploaded material all count).
4. Create a separate `dictionary-online-v2` GitHub Release, upload exactly the
   manifest, 577 corpus assets and required attribution material, then
   anonymously verify manifest and assets through the product trust path. Do
   not modify the existing `dictionary-v2` release.
5. Publication may not proceed unless the accepted Slice-12 report proves
   every served dictionary-read path (`POST /vocab/highlight`,
   `POST /vocab/import/csv`, candidate/card materialization, and any other
   product dictionary read named in the Slice-11 contract-coverage map) uses
   the provider contract, with no direct
   `runtime._current_generation.asset.connection` dictionary-read use
   remaining in `app/api.py`. Verify this from the accepted Slice-12 report
   and mechanical-check evidence rather than re-deriving it.
6. Perform final end-user Online and Offline tests and record exact commands,
   release URLs/asset hashes, results, and any public-release review
   evidence. If this end-user test exposes a code/provider bypass or other
   basic API/provider migration defect, STOP publication immediately — do
   not repair product code inside this publication slice; return the defect
   to a Slice-12-scope fix instead.

Stop-and-ask: either prerequisite not accepted, insufficient storage, a build
or differential mismatch (including a normalization/routing mismatch), the
uploaded-asset count approaching or exceeding the 1,000-per-release ceiling,
missing upload/anonymous verification evidence, any change to `dictionary-v2`,
evidence that a served dictionary-read path still bypasses the provider, a
request to publish before final review/approval, or any path outside the
allowlist. Never add production application code to this slice's allowlist to
fix such a defect.

Risk: public-api, auth-security, data-loss.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's public distribution trust boundary and irreversible public
publication require the highest judgment tier.

Fallback: opus-5 / T3 / high.
