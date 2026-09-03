"""Seed and serve the compiled FastAPI product for Playwright.

This launcher deliberately has no network or Vite dependency. It creates the
small PART-A/PART-B fixtures in a worktree-local directory, then starts the
same ``create_app`` factory used in production. No Piper runner or remote TTS
URL is configured, which makes automatic-pronunciation fallback deterministic.

Slice 12 introduces two deterministic served-product harness states:

* ``state A`` (default; canonical Offline dictionary installed): the
  existing offline / fully-local product path.
* ``state B`` (no canonical full Offline dictionary + deterministic
  fixture Online provider): the chooser state, exercised against the
  Slice-11 Online corpus fixture built from the same Local dictionary.
  The fixture Online corpus is reachable only through the backend
  Product trust/test seam (the in-process ``e2e_online_provider``);
  the browser never supplies a URL or manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.api import _get_nlp, create_app  # noqa: E402


def lemma_ref(lemma: str, pos: str, gender: str | None) -> str:
    payload = json.dumps(
        ["de", unicodedata.normalize("NFC", lemma), pos, gender or "<null>"],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"lemma:v1:{hashlib.sha256(payload).hexdigest()}"


def sense_ref(lemma: str, pos: str, gender: str | None, source_ref: str) -> str:
    lemma_semantic_ref = lemma_ref(lemma, pos, gender)
    payload = json.dumps(
        [lemma_semantic_ref, "wiktextract:enwiktionary", source_ref],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return f"sense:v1:{hashlib.sha256(payload).hexdigest()}"


def part_a_schema() -> str:
    schema = (REPO_ROOT / "reference" / "schema.sql").read_text(encoding="utf-8")
    part_a, marker, _ = schema.partition("-- PART B")
    if not marker:
        raise RuntimeError("reference/schema.sql has no PART B marker")
    return part_a


def reset_state(state_dir: Path) -> None:
    """Remove only deterministic artifacts owned by this E2E launcher."""
    state_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "dictionary.sqlite",
        "replacement.sqlite",
        "user.sqlite",
        "online-cache",
    ):
        target = state_dir / filename
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
    for dirname in ("media", "cache"):
        candidate = state_dir / dirname
        if candidate.exists():
            shutil.rmtree(candidate)


def build_dictionary(path: Path, *, include_tisch: bool) -> None:
    entries = [
        (
            1,
            "Haus",
            "NOUN",
            "das",
            "Häuser",
            "Hauses",
            0,
            None,
            None,
            None,
            "house, building",
            "Das Haus ist alt.",
            "The house is old.",
        ),
        (
            2,
            "See",
            "NOUN",
            "der",
            "Seen",
            "Sees",
            0,
            None,
            None,
            None,
            "lake",
            "Der See ist tief.",
            "The lake is deep.",
        ),
        (
            3,
            "See",
            "NOUN",
            "die",
            "Seen",
            None,
            0,
            None,
            None,
            None,
            "sea, ocean",
            "Die See ist stürmisch.",
            "The sea is stormy.",
        ),
        (
            4,
            "anrufen",
            "VERB",
            None,
            None,
            None,
            1,
            "an",
            "rief an",
            "angerufen",
            "to call, phone",
            "Ich rufe dich morgen an.",
            "I will call you tomorrow.",
        ),
        (
            5,
            "Tisch",
            "NOUN",
            "der",
            "Tische",
            "Tisches",
            0,
            None,
            None,
            None,
            "table",
            "Der Tisch ist rund.",
            "The table is round.",
        ),
    ]
    if not include_tisch:
        entries = entries[:-1]
    conn = sqlite3.connect(path)
    try:
        conn.executescript(part_a_schema())
        for entry in entries:
            (
                ident,
                word,
                pos,
                gender,
                plural,
                genitive,
                separable,
                particle,
                past,
                participle,
                gloss,
                example_de,
                example_en,
            ) = entry
            lref = lemma_ref(word, pos, gender)
            sref = sense_ref(word, pos, gender, f"e2e:{ident}")
            conn.execute(
                """INSERT INTO lemma (
                   id, semantic_ref, lemma, pos, gender, plural, genitive_sg,
                   separable, particle, praeteritum_3sg, partizip_ii, ipa,
                   ipa_source, freq_rank, source, license
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ident,
                    lref,
                    word,
                    pos,
                    gender,
                    plural,
                    genitive,
                    separable,
                    particle,
                    past,
                    participle,
                    "test",
                    "fixture",
                    ident * 10,
                    "fixture",
                    "CC0",
                ),
            )
            conn.execute(
                "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, "
                "source_ref, ord, source, license) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (ident, ident, sref, "wiktextract:enwiktionary", f"e2e:{ident}", "fixture", "CC0"),
            )
            conn.execute(
                "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, "
                "source, license) VALUES (?, ?, 'en', 'translation', 0, ?, 'fixture', 'CC0')",
                (ident, ident, gloss),
            )
            conn.execute(
                "INSERT INTO example (id, de, en, source, source_ref, license, "
                "token_count) VALUES (?, ?, ?, 'fixture', ?, 'CC0', 5)",
                (ident, example_de, example_en, f"e2e:{ident}"),
            )
            conn.execute(
                "INSERT INTO example_lemma (lemma_id, example_id) VALUES (?, ?)", (ident, ident)
            )
        conn.executemany(
            "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
            [("Häuser", 1), ("ruft an", 4), ("rief an", 4)],
        )
        conn.commit()
    finally:
        conn.close()


def build_user_db(path: Path) -> None:
    schema = (REPO_ROOT / "reference" / "schema.sql").read_text(encoding="utf-8")
    _, marker, part_b = schema.partition("-- PART B")
    if not marker:
        raise RuntimeError("reference/schema.sql has no PART B marker")
    conn = sqlite3.connect(path)
    try:
        conn.executescript("-- PART B" + part_b)
    finally:
        conn.close()


def _build_online_provider(state_dir: Path) -> "object":
    """Build a deterministic fixture-backed Online provider for state B.

    This is the in-process equivalent of the Slice-11 Online corpus,
    assembled once per serve from the same Local fixture used for
    state A. It uses a static in-process transport that never reaches
    GitHub and never accepts a browser-supplied URL.
    """
    from app.online_cache import ShardCache, ShardRequest  # noqa: PLC0415
    from app.online_filter import BloomFilter  # noqa: PLC0415
    from app.online_manifest import (  # noqa: PLC0415
        ENTRY_FAMILY_SIZE,
        EXAMPLE_FAMILY_SIZE,
        LOOKUP_FAMILY_SIZE,
        MANIFEST_SCHEMA_VERSION,
        SHARD_FAMILY_FILTER,
        ManifestAsset,
        OnlineManifest,
        TrustedDistribution,
    )
    from app.provider import ProviderIntegrityError  # noqa: PLC0415
    from app.provider_online import OnlineDictionaryProvider  # noqa: PLC0415
    from tools.build_online_dictionary import (  # noqa: PLC0415
        _partition_entry_shards,
        _partition_example_shards,
        _partition_lookup_shards,
        _read_authoritative_example_lemma,
        _read_authoritative_examples,
        _read_authoritative_lemmas,
        _read_authoritative_meanings,
        _read_authoritative_senses,
        _read_authoritative_surface_forms,
        _write_entry_shard,
        _write_example_shard,
        _write_lookup_shard,
    )

    local_fixture = state_dir / "dictionary.sqlite"
    cache_dir = state_dir / "online-cache"
    shard_dir = state_dir / "online-shards"
    if shard_dir.exists():
        shutil.rmtree(shard_dir)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Local fixture's authoritative sha gives us a single dataset token
    # for both Local and Online (the Provider contract's invariant).
    actual_token = hashlib.sha256(local_fixture.read_bytes()).hexdigest()

    source_conn = sqlite3.connect(
        f"file:{local_fixture.as_posix()}?mode=ro", uri=True
    )
    source_conn.row_factory = sqlite3.Row
    try:
        lemmas = _read_authoritative_lemmas(source_conn)
        senses = _read_authoritative_senses(source_conn)
        meanings = _read_authoritative_meanings(source_conn)
        surface_forms = _read_authoritative_surface_forms(source_conn)
        examples = _read_authoritative_examples(source_conn)
        example_lemma = _read_authoritative_example_lemma(source_conn)
    finally:
        source_conn.close()

    lookup_partitions, surface_partitions, sense_route_partitions = (
        _partition_lookup_shards(lemmas, surface_forms, senses)
    )
    entry_partitions = _partition_entry_shards(
        lemmas, senses, meanings, surface_forms, example_lemma, examples
    )
    example_partitions = _partition_example_shards(examples)

    assets: list[ManifestAsset] = []

    def _write_shard(
        family: str, bucket: int, writer: Any, partition_data: Any
    ) -> ManifestAsset:
        canonical = shard_dir / f"{family}-{bucket:03d}.sqlite"
        tmp = shard_dir / f".{family}-{bucket:03d}.sqlite.tmp"
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        writer(conn, bucket, *partition_data)
        conn.close()
        os.replace(tmp, canonical)
        payload = canonical.read_bytes()
        return ManifestAsset(
            family=family,
            bucket=bucket,
            name=f"{family}-{bucket:03d}.sqlite",
            path=f"shards/{family}/{bucket:03d}.sqlite",
            byte_size=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            schema_version=f"{family}-v1",
        )

    for bucket in range(LOOKUP_FAMILY_SIZE):
        assets.append(
            _write_shard(
                "lookup",
                bucket,
                _write_lookup_shard,
                (
                    lookup_partitions.get(bucket, []),
                    surface_partitions.get(bucket, []),
                    sense_route_partitions.get(bucket, ()),
                ),
            )
        )
    for bucket in range(ENTRY_FAMILY_SIZE):
        state = entry_partitions.get(
            bucket,
            {
                "lemmas": [],
                "senses": [],
                "meanings": [],
                "surface_forms": [],
                "example_lemma": [],
            },
        )
        assets.append(
            _write_shard(
                "entry",
                bucket,
                _write_entry_shard,
                (
                    state["lemmas"],
                    state["senses"],
                    state["meanings"],
                    state["surface_forms"],
                    state["example_lemma"],
                ),
            )
        )
    for bucket in range(EXAMPLE_FAMILY_SIZE):
        assets.append(
            _write_shard(
                "example",
                bucket,
                _write_example_shard,
                (example_partitions[bucket],),
            )
        )

    closure_keys: list[str] = []
    seen_closure: set[str] = set()
    for row in lemmas:
        text = str(row[2])
        for variant in (text, text.lower()):
            if variant in seen_closure:
                continue
            seen_closure.add(variant)
            closure_keys.append(variant)
    filter_bytes = BloomFilter.from_closure_keys(closure_keys).to_bytes()
    assets.append(
        ManifestAsset(
            family=SHARD_FAMILY_FILTER,
            bucket=0,
            name="membership-filter.bin",
            path="shards/membership-filter.bin",
            byte_size=len(filter_bytes),
            sha256=hashlib.sha256(filter_bytes).hexdigest(),
            schema_version="membership-filter-v1",
        )
    )

    manifest = OnlineManifest(
        dataset_token=actual_token,
        schema_version=MANIFEST_SCHEMA_VERSION,
        distribution=TrustedDistribution(
            base_origin="https://github.com",
            release_tag="dictionary-online-fixture",
            redirect_policy="github_release_redirect_only",
        ),
        assets=tuple(assets),
    )

    def transport(request: ShardRequest) -> bytes:
        for asset in manifest.assets:
            if (
                asset.family == request.identity.family
                and asset.bucket == request.identity.bucket
            ):
                return (shard_dir / asset.name).read_bytes()
        raise ProviderIntegrityError("missing fixture shard")

    cache = ShardCache(cache_dir, transport=transport)
    return OnlineDictionaryProvider(
        manifest=manifest,
        cache=cache,
        filter_payload=filter_bytes,
        dataset_token=actual_token,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("E2E_PORT", "8817")))
    parser.add_argument(
        "--state",
        choices=("A", "B"),
        default=os.environ.get("E2E_STATE", "A"),
        help=(
            "Deterministic served-product harness state. "
            "A: valid canonical Offline dictionary installed; "
            "B: no canonical full Offline dictionary + Online fixture "
            "(chooser rendered in UI, deterministic online corpus)."
        ),
    )
    args = parser.parse_args()
    state_dir = Path(os.environ.get("E2E_STATE_DIR", REPO_ROOT / ".e2e-state")).resolve()
    reset_state(state_dir)
    build_dictionary(state_dir / "dictionary.sqlite", include_tisch=False)
    build_dictionary(state_dir / "replacement.sqlite", include_tisch=True)
    build_user_db(state_dir / "user.sqlite")

    state_a = args.state.upper() == "A"
    if state_a:
        app = create_app(
            state_dir / "dictionary.sqlite",
            state_dir / "user.sqlite",
            cors_origins=(f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"),
            service_port=args.port,
        )
    else:
        # Slice 12 state B: no canonical full Offline asset. The chooser
        # is shown in the UI and the Online provider serves the
        # deterministic fixture corpus. The corpus and transport live
        # entirely under the e2e state dir; the browser never receives a
        # network endpoint to point at.
        online_provider: Any = _build_online_provider(state_dir)
        from app.dictionary_session import OnlineSessionInfo  # noqa: PLC0415
        info = OnlineSessionInfo(
            dataset_token=str(getattr(online_provider, "_dataset_token", "online-fixture")),
            asset_token=str(online_provider.asset_token),
            cache_dir=str(state_dir / "online-cache"),
        )

        def offline_factory() -> Tuple[Any, Any]:
            from app.deck import DictionaryRuntime  # noqa: PLC0415
            from app.dictionary_session import DictionarySession  # noqa: PLC0415

            rt = DictionaryRuntime(
                state_dir / "dictionary.sqlite",
                state_dir / "user.sqlite",
            )
            return rt, DictionarySession(runtime=rt)

        # In state B the canonical offline slot is intentionally absent;
        # the chooser endpoint rebuilds the session when the user picks
        # either "Use Online" (already active) or "Download for Offline
        # use" later.
        app = create_app(
            dict_path=None,
            user_db_path=state_dir / "user.sqlite",
            cors_origins=(f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"),
            service_port=args.port,
            online_provider=online_provider,
            online_session_info=info,
            online_provider_factory=(lambda: (offline_factory()[1])),
            managed_dictionary_dir=state_dir / "dictionary",
            manifest_filename="dictionary.sqlite",
        )
        # Override the default "online" stamping: state B keeps the
        # canonical asset slot intact and shows the chooser because
        # there is no offline asset to validate against.
        app.state.dictionary_mode = "unconfigured"
        app.state.dict_path = None
        # Do not overwrite app.state.session: the Online session stays
        # bound so /vocab/lookup/highlight/import/csv accept the fixture
        # corpus. The UI distinguishes chooser vs Online via
        # app.state.dictionary_mode.

    _get_nlp()
    import uvicorn

    print(f"[e2e-server] FastAPI state: {state_dir} state={args.state.upper()}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
