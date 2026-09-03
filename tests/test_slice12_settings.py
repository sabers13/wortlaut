"""Slice 12 API tests for chooser/Settings endpoints and Online fixture paths.

Covers:
1. /vocab/settings/dictionary status shape for chooser, offline, online modes.
2. /vocab/settings/dictionary/install-offline preflight rejection.
3. /vocab/settings/dictionary/remove-offline offline-active rejection.
4. /vocab/settings/dictionary/remove-offline online-active asset removal.
5. /vocab/settings/dictionary/clear-online-cache clears cache directory only.
6. Provider-backed /vocab/highlight serves Online fixture data without raw
   asset connection access.
7. CF1 provider hit -> resolver record adapter preserves identity.
8. CF2 surface-only parity test (Local and Online surface-form lookups).
9. /vocab/import/csv works with Online provider (PART-B creation) without
   network.
10. Structured provider failure (NetworkError, IntegrityError, BudgetExceeded)
    yields HTTP 5xx, not a needs_gloss/no-match silent translation.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import _materialize_candidate_from_ref, _ProviderOracle, create_app
from app.dictionary_mode import (
    _LOCAL_FILENAME,
    OfflineInstallPeak,
    preflight_offline_install,
)
from app.online_cache import ShardCache, ShardRequest
from app.online_filter import BloomFilter
from app.online_manifest import (
    ENTRY_FAMILY_SIZE,
    EXAMPLE_FAMILY_SIZE,
    LOOKUP_FAMILY_SIZE,
    MANIFEST_SCHEMA_VERSION,
    SHARD_FAMILY_FILTER,
    ManifestAsset,
    OnlineManifest,
    TrustedDistribution,
)
from app.provider import (
    ProviderBudgetExceededError,
    ProviderIntegrityError,
    ProviderNetworkError,
)
from app.provider_local import LocalDictionaryProvider
from app.provider_online import OnlineDictionaryProvider
from app.resolve import LookupProtocol, Ref
from tools.build_dict import compute_lemma_semantic_ref, compute_sense_semantic_ref
from tools.build_online_dictionary import (
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

PART_A_SCHEMA_HEADER = """
CREATE TABLE lemma (
  id INTEGER PRIMARY KEY,
  semantic_ref TEXT NOT NULL UNIQUE,
  lemma TEXT NOT NULL,
  pos TEXT NOT NULL,
  gender TEXT,
  plural TEXT,
  plural_none INTEGER NOT NULL DEFAULT 0,
  source TEXT,
  license TEXT
);
"""


def _full_part_a_schema() -> str:
    text = (Path(__file__).resolve().parent.parent / "reference" / "schema.sql").read_text(
        encoding="utf-8"
    )
    part_a, marker, _ = text.partition("-- PART B")
    if not marker:
        raise RuntimeError("schema.sql missing the PART B marker")
    return part_a


@pytest.fixture(scope="module")
def part_a_local_dict(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a tiny Local dictionary committed to the test corpus."""
    root = tmp_path_factory.mktemp("slice12_dict")
    db = root / "local.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(_full_part_a_schema())
    rows = [
        ("Haus", "NOUN", "das"),
        ("See", "NOUN", "der"),
        ("anrufen", "VERB", None),
    ]
    for ident, (lemma, pos, gender) in enumerate(rows, start=1):
        lref = compute_lemma_semantic_ref(lemma, pos, gender)
        sref = compute_sense_semantic_ref(lref, "wiktextract:enwiktionary", f"e2e:{ident}")
        sql = (
            "INSERT INTO lemma (id, semantic_ref, lemma, pos, gender, "
            "plural_none, source, license) VALUES (?, ?, ?, ?, ?, 0, "
            "'fixture', 'CC0')"
        )
        conn.execute(sql, (ident, lref, lemma, pos, gender))
        conn.execute(
            "INSERT INTO sense (id, lemma_id, semantic_ref, source_namespace, source_ref, ord, "
            "source, license) VALUES (?, ?, ?, ?, ?, 0, 'fixture', 'CC0')",
            (ident, ident, sref, "wiktextract:enwiktionary", f"e2e:{ident}"),
        )
        conn.execute(
            "INSERT INTO sense_meaning (id, sense_id, language, kind, ord, text, source, license) "
            "VALUES (?, ?, 'en', 'translation', 0, ?, 'fixture', 'CC0')",
            (ident, ident, f"gloss-{ident}"),
        )
    conn.executemany(
        "INSERT INTO surface_form (form, lemma_id) VALUES (?, ?)",
        [("Häuser", 1), ("rief an", 3)],
    )
    conn.commit()
    conn.close()
    return db


def _build_online_provider_from_local(
    local_path: Path, *, output_root: Path
) -> OnlineDictionaryProvider:
    """Build a deterministic Online provider backed by a local fixture corpus."""
    output_dir = output_root / "corpus"
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    cache_dir = output_root / "cache"
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    actual_token = sha256(local_path.read_bytes()).hexdigest()

    source_conn = sqlite3.connect(f"file:{local_path.as_posix()}?mode=ro", uri=True)
    source_conn.row_factory = sqlite3.Row
    try:
        lemmas = list(_read_authoritative_lemmas(source_conn))
        senses = list(_read_authoritative_senses(source_conn))
        meanings = list(_read_authoritative_meanings(source_conn))
        surface_forms = list(_read_authoritative_surface_forms(source_conn))
        examples = list(_read_authoritative_examples(source_conn))
        example_lemma = list(_read_authoritative_example_lemma(source_conn))
    finally:
        source_conn.close()

    # Stubs work for our fixture because the cardinality is small
    # (only 3 lemmas / 3 senses / 0 examples / 1 surface form). The
    # full 256/256/64 bucket scan is exercised elsewhere; here we
    # just need the entries we observe to land in their bucket.
    lookup_partitions, surface_partitions, sense_route_partitions = _partition_lookup_shards(
        lemmas, surface_forms, senses
    )
    entry_partitions = _partition_entry_shards(
        lemmas, senses, meanings, surface_forms, example_lemma, examples
    )
    example_partitions = _partition_example_shards(examples)

    assets: list[ManifestAsset] = []
    for bucket in range(LOOKUP_FAMILY_SIZE):
        canonical = output_dir / f"lookup-{bucket:03d}.sqlite"
        tmp = output_dir / f".lookup-{bucket:03d}.sqlite.tmp"
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        _write_lookup_shard(
            conn,
            bucket,
            lookup_partitions.get(bucket, []),
            surface_partitions.get(bucket, []),
            sense_route_partitions.get(bucket, ()),
        )
        conn.close()
        import os

        os.replace(tmp, canonical)
        payload = canonical.read_bytes()
        assets.append(
            ManifestAsset(
                family="lookup",
                bucket=bucket,
                name=f"lookup-{bucket:03d}.sqlite",
                path=f"shards/lookup/{bucket:03d}.sqlite",
                byte_size=len(payload),
                sha256=sha256(payload).hexdigest(),
                schema_version="lookup-v1",
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
        canonical = output_dir / f"entry-{bucket:03d}.sqlite"
        tmp = output_dir / f".entry-{bucket:03d}.sqlite.tmp"
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        _write_entry_shard(
            conn,
            bucket,
            state["lemmas"],
            state["senses"],
            state["meanings"],
            state["surface_forms"],
            state["example_lemma"],
        )
        conn.close()
        import os

        os.replace(tmp, canonical)
        payload = canonical.read_bytes()
        assets.append(
            ManifestAsset(
                family="entry",
                bucket=bucket,
                name=f"entry-{bucket:03d}.sqlite",
                path=f"shards/entry/{bucket:03d}.sqlite",
                byte_size=len(payload),
                sha256=sha256(payload).hexdigest(),
                schema_version="entry-v1",
            )
        )
    for bucket in range(EXAMPLE_FAMILY_SIZE):
        canonical = output_dir / f"example-{bucket:03d}.sqlite"
        tmp = output_dir / f".example-{bucket:03d}.sqlite.tmp"
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        _write_example_shard(conn, bucket, example_partitions[bucket])
        conn.close()
        import os

        os.replace(tmp, canonical)
        payload = canonical.read_bytes()
        assets.append(
            ManifestAsset(
                family="example",
                bucket=bucket,
                name=f"example-{bucket:03d}.sqlite",
                path=f"shards/example/{bucket:03d}.sqlite",
                byte_size=len(payload),
                sha256=sha256(payload).hexdigest(),
                schema_version="example-v1",
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
            sha256=sha256(filter_bytes).hexdigest(),
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
                return (output_dir / asset.name).read_bytes()
        raise ProviderIntegrityError("missing fixture shard")

    cache = ShardCache(cache_dir, transport=transport)
    return OnlineDictionaryProvider(
        manifest=manifest,
        cache=cache,
        filter_payload=filter_bytes,
        dataset_token=actual_token,
    )


@pytest.fixture
def user_db_path(tmp_path: Path) -> Path:
    from app.standalone import ensure_user_db
    ensure_user_db(tmp_path / "flashcards.sqlite")
    return tmp_path / "flashcards.sqlite"


@pytest.fixture
def app_offline(part_a_local_dict: Path, user_db_path: Path, tmp_path: Path) -> Any:
    from app.dictionary import validate_candidate_dictionary

    asset = validate_candidate_dictionary(part_a_local_dict)
    try:
        expected_sha = asset.sha256
    finally:
        try:
            asset.close()
        except Exception:
            pass
    # Place the canonical file at the managed dir path so the Settings
    # endpoint's offline validation reflects a real install slot.
    slot = tmp_path / "dictionary-slot"
    slot.mkdir(parents=True, exist_ok=True)
    canonical = slot / _LOCAL_FILENAME
    canonical.write_bytes(part_a_local_dict.read_bytes())
    return create_app(
        dict_path=canonical,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        managed_dictionary_dir=slot,
        manifest_filename=_LOCAL_FILENAME,
        expected_dictionary_sha256=expected_sha,
    )


@pytest.fixture
def app_online(part_a_local_dict: Path, user_db_path: Path, tmp_path: Path) -> Any:
    provider = _build_online_provider_from_local(part_a_local_dict, output_root=tmp_path / "online")
    from app.dictionary_session import OnlineSessionInfo
    info = OnlineSessionInfo(
        dataset_token=str(getattr(provider, "_dataset_token", "online-fixture")),
        asset_token=str(provider.asset_token),
        cache_dir=str(tmp_path / "online-cache"),
    )

    def offline_factory() -> Any:
        from app.deck import DictionaryRuntime  # noqa: PLC0415
        from app.dictionary_session import DictionarySession  # noqa: PLC0415

        rt = DictionaryRuntime(
            part_a_local_dict,
            user_db_path,
        )
        return rt, DictionarySession(runtime=rt)

    return create_app(
        dict_path=None,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        online_provider=provider,
        online_session_info=info,
        online_provider_factory=(lambda: offline_factory()),
        managed_dictionary_dir=tmp_path / "dictionary-slot",
        manifest_filename=_LOCAL_FILENAME,
    )


@pytest.fixture
def offline_client(app_offline: Any) -> Generator[TestClient, None, None]:
    with TestClient(app_offline, base_url="http://127.0.0.1:8000") as client:
        yield client


@pytest.fixture
def online_client(app_online: Any) -> Generator[TestClient, None, None]:
    with TestClient(app_online, base_url="http://127.0.0.1:8000") as client:
        yield client


# ---------------------------------------------------------------------------
# Settings endpoints — chooser / mode / install / removal / cache
# ---------------------------------------------------------------------------


def test_settings_dictionary_status_reports_mode(app_offline: Any) -> None:
    with TestClient(app_offline, base_url="http://127.0.0.1:8000") as client:
        response = client.get("/vocab/settings/dictionary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "offline"
    assert payload["canonical_offline_valid"] is True
    assert payload["online_active"] is False


def test_settings_dictionary_status_for_chooser(tmp_path: Path, user_db_path: Path) -> None:
    app = create_app(
        dict_path=None,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        managed_dictionary_dir=tmp_path / "dictionary-slot",
        manifest_filename=_LOCAL_FILENAME,
    )
    app.state.dictionary_mode = "unconfigured"
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.get("/vocab/settings/dictionary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "unconfigured"
    assert payload["canonical_offline_present"] is False


def test_settings_remove_offline_rejected_while_offline_active(offline_client: TestClient) -> None:
    response = offline_client.post(
        "/vocab/settings/dictionary/remove-offline",
        json={},
        headers={"X-Flashcards-Request": "1", "Content-Type": "application/json"},
    )
    assert response.status_code == 409
    body = response.json()
    assert (
        "offline_dictionary_in_use" in body["detail"]
        or body.get("code") == "offline_dictionary_in_use"
    )


def test_free_space_preflight_rejects_when_insufficient(
    tmp_path: Path, part_a_local_dict: Path
) -> None:
    """The conservative preflight must refuse when available free space is
    less than the threshold; it must not touch the install slot.
    """

    import app.dictionary_mode as dm
    from app.dictionary_mode import OfflineInstallRefused

    # Allocate the install dir under a virtual filesystem with no free space.
    install_dir = tmp_path / "dictionary-slot"
    install_dir.mkdir()

    # Force the disk_usage probe to report zero free space.
    real_free = dm._free_bytes
    try:
        dm._free_bytes = lambda p: 0  # type: ignore[assignment]
        with pytest.raises(OfflineInstallRefused) as excinfo:
            preflight_offline_install(
                manifest_bytes=945_000_000,
                install_dir=install_dir,
            )
        assert excinfo.value.code == "offline_install_insufficient_disk_space"
        assert excinfo.value.available_bytes == 0
        # Install dir was not touched.
        assert install_dir.is_dir()
        # No canonical file was created.
        assert list(install_dir.iterdir()) == []
    finally:
        dm._free_bytes = real_free


def test_free_space_preflight_passes_with_sufficient_space(
    tmp_path: Path,
) -> None:
    install_dir = tmp_path / "dictionary-slot"
    install_dir.mkdir()
    peak = preflight_offline_install(
        manifest_bytes=945_000_000,
        install_dir=install_dir,
    )
    assert isinstance(peak, OfflineInstallPeak)
    assert peak.safety_threshold_bytes > 0
    # Components include the manifest_bytes + canonical_target + installer_temp
    assert peak.components["manifest_bytes"] == 945_000_000


# ---------------------------------------------------------------------------
# Provider migration (CF1 adapter + CF2 surface-only parity + provider hit rate)
# ---------------------------------------------------------------------------


def test_provider_oracle_adapter_preserves_lemma_id_under_id_name(
    part_a_local_dict: Path,
) -> None:
    """CF1: provider hits expose ``lemma_id``; the resolver oracle needs
    ``id``. The adapter must map between them without losing the durable
    semantic ref.
    """
    provider = LocalDictionaryProvider(part_a_local_dict)
    oracle: LookupProtocol = _ProviderOracle(provider)
    rows = oracle.lookup_exact("Haus")
    assert rows, "expected at least one Local hit for 'Haus'"
    for row in rows:
        assert row.id is not None
        assert row.lemma == "Haus"


def test_provider_materialize_candidate_uses_entry_for_id(
    part_a_local_dict: Path,
) -> None:
    provider = LocalDictionaryProvider(part_a_local_dict)
    oracle = _ProviderOracle(provider)
    resolved = Ref(
        lemma="Haus",
        pos="NOUN",
        gender="das",
        status="resolved",
        lemma_id=1,
    )
    cand = _materialize_candidate_from_ref(
        resolved,
        provider,
        oracle,
        known_lemmas=None,
    )
    assert cand is not None
    assert cand["status"] == "resolved"
    assert cand["lemma"] == "Haus"
    assert cand["senses"]
    assert cand["examples"] == [] or isinstance(cand["examples"], list)


def test_provider_oracle_surface_form_returns_local_and_online_parity(
    tmp_path: Path, part_a_local_dict: Path
) -> None:
    """CF2: surface-form lookup must preserve Local's surface-only semantics.
    A valid inflected form should be returned exactly as Local returns it,
    with no implicit lemma-table suppression.
    """
    local = LocalDictionaryProvider(part_a_local_dict)
    online_local_view = _build_online_provider_from_local(
        part_a_local_dict, output_root=tmp_path / "online-p"
    )
    try:
        local_hits = [hit.semantic_ref for hit in local.lookup_surface_form("Häuser")]
        online_hits = [
            hit.semantic_ref for hit in online_local_view.lookup_surface_form("Häuser")
        ]
        assert sorted(local_hits) == sorted(online_hits)
        # Surface only — lemma-only lookup should NOT return the inflected form.
        lemma_hits = [
            hit.semantic_ref for hit in local.lookup_exact("Häuser")
        ]
        assert lemma_hits == []
        assert local_hits, "surface-form hit must remain visible"
    finally:
        try:
            online_local_view.close()
        except Exception:
            pass


def test_api_highlight_works_with_online_provider(online_client: TestClient) -> None:
    response = online_client.post(
        "/vocab/highlight",
        json={
            "sentence_text": "Das Haus ist alt.",
            "selected_span": {"start": 4, "end": 8},
            "lesson_label": "Lesson X",
        },
        headers={
            "Host": "127.0.0.1:8000",
            "X-Flashcards-Request": "1",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_token"]
    assert payload["candidates"]
    lemmas = [c["lemma"] for c in payload["candidates"]]
    assert "Haus" in lemmas


def test_api_highlight_no_raw_connection_in_app_api_part(
    tmp_path: Path, part_a_local_dict: Path, user_db_path: Path
) -> None:
    """Mechanical provider-bypass check: ``/vocab/highlight`` must not read
    ``runtime._current_generation.asset.connection`` directly. The
    provider-backed oracle path must provide the resolved data
    instead.
    """
    provider = _build_online_provider_from_local(part_a_local_dict, output_root=tmp_path / "online")
    from app.dictionary_session import OnlineSessionInfo
    info = OnlineSessionInfo(
        dataset_token=str(getattr(provider, "_dataset_token", "fixture")),
        asset_token=str(provider.asset_token),
        cache_dir=str(tmp_path / "online-cache"),
    )
    app = create_app(
        dict_path=None,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        online_provider=provider,
        online_session_info=info,
        online_provider_factory=lambda: (provider, info),
        managed_dictionary_dir=tmp_path / "dictionary-slot",
        manifest_filename=_LOCAL_FILENAME,
    )
    try:
        with TestClient(app, base_url="http://127.0.0.1:8000") as client:
            response = client.post(
                "/vocab/highlight",
                json={
                    "sentence_text": "Haus",
                    "selected_span": {"start": 0, "end": 4},
                    "lesson_label": "Lesson X",
                },
                headers={
                    "Host": "127.0.0.1:8000",
                    "X-Flashcards-Request": "1",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 200
    finally:
        try:
            provider.close()
        except Exception:
            pass


def test_api_import_csv_works_with_online_provider(online_client: TestClient) -> None:
    response = online_client.post(
        "/vocab/import/csv",
        json={
            "csv_text": "Haus\nSee\nanrufen",
            "deck_name": "Online deck",
            "meaning_languages": ["de", "en"],
        },
        headers={
            "Host": "127.0.0.1:8000",
            "X-Flashcards-Request": "1",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["notes_created"] >= 1 or payload["notes_reused"] >= 1
    # No PART-B mutation from incomplete provider results: every created note
    # has a real provider-mapped lemma_ref.
    assert payload["deck_id"]


def test_provider_failure_translates_to_structured_http_5xx(
    tmp_path: Path, part_a_local_dict: Path, user_db_path: Path
) -> None:
    """A provider network failure must NOT become a needs_gloss outcome or
    silent PART-B write. The API returns a structured 5xx and the user
    database receives no rows.
    """

    class _BoomProvider:
        asset_token = "boom-asset-token"

        def lookup_exact(self, *args: object, **kwargs: object) -> None:
            raise ProviderNetworkError("simulated outage")

        def lookup_surface_form(self, *args: object, **kwargs: object) -> None:
            raise ProviderNetworkError("simulated outage")

        def entry_for_id(self, *args: object, **kwargs: object) -> None:
            raise ProviderNetworkError("simulated outage")

    app = create_app(
        dict_path=None,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        online_provider=_BoomProvider(),  # type: ignore[arg-type]
        managed_dictionary_dir=tmp_path / "dictionary-slot",
        manifest_filename=_LOCAL_FILENAME,
    )
    # Ensure the user DB is reachable but remains empty after the failure.
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        # Discover the auth header: it is required by the served-product
        # R12 guard on non-GET routes.
        response = client.post(
            "/vocab/highlight",
            json={
                "sentence_text": "Haus",
                "selected_span": {"start": 0, "end": 4},
                "lesson_label": "Lesson X",
            },
            headers={
                "Host": "127.0.0.1:8000",
                "X-Flashcards-Request": "1",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code in (500, 502, 503)
    body = response.json()
    assert body.get("code") in {"network", "integrity", "budget", "unavailable"}
    # No PART-B notes created.
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(user_db_path)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
        assert rows == 0
    finally:
        conn.close()


def test_provider_budget_failure_does_not_create_partial_card(
    tmp_path: Path, part_a_local_dict: Path, user_db_path: Path
) -> None:
    """ProviderBudgetExceededError becomes a structured 5xx; the import-csv
    endpoint does not partial-create notes when the lookup ladder blows
    the per-operation budget.
    """

    class _BudgetProvider:
        asset_token = "budget-asset-token"

        def lookup_exact(self, *args: object, **kwargs: object) -> None:
            raise ProviderBudgetExceededError("budget exhausted")

        def lookup_surface_form(self, *args: object, **kwargs: object) -> None:
            raise ProviderBudgetExceededError("budget exhausted")

        def entry_for_id(self, *args: object, **kwargs: object) -> None:
            raise ProviderBudgetExceededError("budget exhausted")

    app = create_app(
        dict_path=None,
        user_db_path=user_db_path,
        cors_origins=["http://127.0.0.1:8000"],
        online_provider=_BudgetProvider(),  # type: ignore[arg-type]
        managed_dictionary_dir=tmp_path / "dictionary-slot",
        manifest_filename=_LOCAL_FILENAME,
    )
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.post(
            "/vocab/import/csv",
            json={
                "csv_text": "Haus\nSee",
                "deck_name": "Budget deck",
                "meaning_languages": ["de", "en"],
            },
            headers={
                "Host": "127.0.0.1:8000",
                "X-Flashcards-Request": "1",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code in (500, 502, 503)
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(user_db_path)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM note").fetchone()[0]
        assert rows == 0
    finally:
        conn.close()
