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
2. Run the specified production differential sample against the local provider
   and fail closed on any semantic, routing, count, or integrity mismatch.
3. Create a separate `dictionary-online-v2` GitHub Release, upload exactly the
   manifest, 577 assets and required attribution material, then anonymously
   verify manifest and assets through the product trust path. Do not modify the
   existing `dictionary-v2` release.
4. Perform final end-user Online and Offline tests and record exact commands,
   release URLs/asset hashes, results, and any public-release review evidence.

Stop-and-ask: either prerequisite not accepted, insufficient storage, a build
or differential mismatch, missing upload/anonymous verification evidence, any
change to `dictionary-v2`, a request to publish before final review/approval, or
any path outside the allowlist.

Risk: public-api, auth-security, data-loss.

Model: gpt-5.6-terra / T3 / high

Why: WORKFLOW §4's public distribution trust boundary and irreversible public
publication require the highest judgment tier.

Fallback: opus-5 / T3 / high.
