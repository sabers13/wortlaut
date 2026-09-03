"""Trusted Product HTTP transport tests for the Online dictionary.

These tests prove the Slice 11 Product transport trust policy:
HTTPS only; userinfo rejected; unexpected ports rejected; arbitrary
hosts rejected; approved GitHub Release redirect destinations accepted;
plain HTTP rejected; userinfo redirect rejected; redirect loop
rejected; non-2xx response rejected; network failure rejected; no
caller/browser Product source parameter.

The transport policy is the unit under test. An injectable low-level
opener seam drives every redirect case so the tests never reach the
public GitHub network.
"""

from __future__ import annotations

import socket
import ssl
import urllib.error
from typing import Any

import pytest

from app.online_manifest import (
    DEFAULT_DATASET_TOKEN,
    MANIFEST_SCHEMA_VERSION,
    SHARD_FAMILY_ENTRY,
    ManifestAsset,
    OnlineManifest,
    TrustedDistribution,
)
from app.online_transport import (
    DEFAULT_GITHUB_REPO,
    GitHubReleaseProductTransport,
    create_product_online_provider,
    create_product_shard_cache,
)
from app.provider import ProviderNetworkError


def _build_manifest() -> OnlineManifest:
    entry_asset = ManifestAsset(
        family=SHARD_FAMILY_ENTRY,
        bucket=0,
        name="entry-000.sqlite",
        path="shards/entry/000.sqlite",
        byte_size=5,
        sha256="a" * 64,
        schema_version="entry-shard-v1",
    )
    filter_asset = ManifestAsset(
        family="membership_filter",
        bucket=0,
        name="membership-filter.bin",
        path="shards/membership-filter.bin",
        byte_size=len(b"placeholder-filter-bytes"),
        sha256="b" * 64,
        schema_version="membership-filter-v1",
    )
    return OnlineManifest(
        dataset_token=DEFAULT_DATASET_TOKEN,
        schema_version=MANIFEST_SCHEMA_VERSION,
        distribution=TrustedDistribution(
            base_origin="https://github.com",
            release_tag="dictionary-online-v2",
            redirect_policy="github_release_redirect_only",
        ),
        assets=(entry_asset, filter_asset),
    )


def _build_request(manifest: OnlineManifest) -> Any:
    from app.online_cache import ShardIdentity, ShardRequest

    asset = next(iter(manifest.assets))
    return ShardRequest(
        identity=ShardIdentity(family=asset.family, bucket=asset.bucket),
        asset=asset,
    )


class _FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        return None


class _SeamOpener:
    """A test-only opener that drives the transport policy deterministically."""

    def __init__(self, script: list[Any]) -> None:
        self._script = list(script)
        self.calls: list[str] = []

    def open(self, request: Any, timeout: float = 30.0) -> Any:  # noqa: ARG002
        self.calls.append(request.full_url)
        if not self._script:
            raise RuntimeError("seam opener: no scripted response")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            return item(request)
        return item


def _http_error_redirect(code: int, location: str) -> urllib.error.HTTPError:
    from email.message import Message

    hdrs: Message = Message()
    hdrs["Location"] = location
    return urllib.error.HTTPError(
        url="https://github.com/sabers13/wortlaut/releases/download/dictionary-online-v2/entry-000.sqlite",
        code=code,
        msg="redirect",
        hdrs=hdrs,
        fp=None,
    )


def _transport_for(manifest: OnlineManifest, opener: Any) -> GitHubReleaseProductTransport:
    return GitHubReleaseProductTransport(
        distribution=manifest.distribution,
        opener=opener,
        max_redirects=3,
        github_repo=DEFAULT_GITHUB_REPO,
    )


def test_initial_url_is_exact_github_release_form() -> None:
    """The initial request must resolve to the approved GitHub Release URL."""
    manifest = _build_manifest()
    opener = _SeamOpener([_FakeResponse(200, {}, b"hello")])
    transport = _transport_for(manifest, opener)
    payload = transport(_build_request(manifest))
    assert payload == b"hello"
    assert len(opener.calls) == 1
    assert (
        opener.calls[0]
        == "https://github.com/sabers13/wortlaut/releases/download/dictionary-online-v2/entry-000.sqlite"
    )


def test_approved_release_redirect_is_accepted() -> None:
    """``objects.githubusercontent.com`` redirects resolve to the asset."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(
                302,
                "https://objects.githubusercontent.com/asset/abc",
            ),
            _FakeResponse(200, {}, b"payload-bytes"),
        ]
    )
    transport = _transport_for(manifest, opener)
    payload = transport(_build_request(manifest))
    assert payload == b"payload-bytes"
    assert len(opener.calls) == 2


def test_arbitrary_host_redirect_is_rejected() -> None:
    """An arbitrary non-GitHub host is rejected before follow-through."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(
                302,
                "https://attacker.example.com/asset",
            ),
        ]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="not on the approved distribution"):
        transport(_build_request(manifest))


def test_plain_http_redirect_is_rejected() -> None:
    """A plain HTTP redirect target is rejected before follow-through."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(
                302,
                "http://github.com/sabers13/wortlaut/releases/download/dictionary-online-v2/entry-000.sqlite",
            ),
        ]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="must use HTTPS"):
        transport(_build_request(manifest))


def test_userinfo_redirect_is_rejected() -> None:
    """A redirect with userinfo is rejected."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(
                302,
                "https://user:pass@github.com/asset",
            ),
        ]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="userinfo"):
        transport(_build_request(manifest))


def test_unexpected_port_redirect_is_rejected() -> None:
    """A redirect with an unexpected port is rejected."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(
                302,
                "https://github.com:8443/asset",
            ),
        ]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="port"):
        transport(_build_request(manifest))


def test_redirect_loop_is_rejected() -> None:
    """A redirect loop is rejected when the redirect limit is exhausted."""
    manifest = _build_manifest()
    redirect = _http_error_redirect(
        302, "https://objects.githubusercontent.com/asset/loop"
    )
    opener = _SeamOpener([redirect, redirect, redirect, redirect])
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="redirect limit"):
        transport(_build_request(manifest))


def test_non_2xx_response_is_rejected() -> None:
    """A non-2xx final response is rejected as a network failure."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [
            _http_error_redirect(302, "https://objects.githubusercontent.com/asset/x"),
            _FakeResponse(500, {}, b""),
        ]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="unexpected status"):
        transport(_build_request(manifest))


def test_connection_failure_is_a_network_error() -> None:
    """A socket failure becomes a structured network error."""
    manifest = _build_manifest()
    opener = _SeamOpener([socket.error("dns failure")])
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="network failure"):
        transport(_build_request(manifest))


def test_ssl_failure_is_a_network_error() -> None:
    """An SSL failure becomes a structured network error."""
    manifest = _build_manifest()
    opener = _SeamOpener([ssl.SSLError("cert verify failed")])
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="network failure"):
        transport(_build_request(manifest))


def test_url_error_is_a_network_error() -> None:
    """A urllib URL error becomes a structured network error."""
    manifest = _build_manifest()
    opener = _SeamOpener(
        [urllib.error.URLError("connection refused")]
    )
    transport = _transport_for(manifest, opener)
    with pytest.raises(ProviderNetworkError, match="URL error"):
        transport(_build_request(manifest))


def test_successful_payload_is_returned() -> None:
    """A successful 200 response yields the body bytes."""
    manifest = _build_manifest()
    opener = _SeamOpener([_FakeResponse(200, {}, b"\x00\x01\x02payload")])
    transport = _transport_for(manifest, opener)
    payload = transport(_build_request(manifest))
    assert payload == b"\x00\x01\x02payload"


def test_caller_cannot_supply_arbitrary_product_source() -> None:
    """The transport must not expose host/URL/manifest knobs to the caller."""
    manifest = _build_manifest()
    opener = _SeamOpener([_FakeResponse(200, {}, b"x")])
    transport = _transport_for(manifest, opener)
    forbidden_args = ("host", "url", "manifest_url", "source")
    for arg in forbidden_args:
        assert not hasattr(transport, arg), (
            f"transport must not expose {arg!r}"
        )


def test_create_product_shard_cache_uses_trusted_transport(tmp_path: Any) -> None:
    """``create_product_shard_cache`` wires the trusted Product transport."""
    from app.online_cache import ShardCache

    manifest = _build_manifest()
    cache = create_product_shard_cache(manifest, tmp_path / "cache")
    assert isinstance(cache, ShardCache)


def test_create_product_online_provider_uses_trusted_transport(tmp_path: Any) -> None:
    """``create_product_online_provider`` returns a working provider."""
    from app.online_filter import BloomFilter
    from app.provider_online import OnlineDictionaryProvider

    manifest = _build_manifest()
    filter_payload = BloomFilter.from_closure_keys(["Haus", "See"]).to_bytes()
    opener = _SeamOpener(
        [
            _FakeResponse(200, {}, filter_payload),
        ]
    )
    provider = create_product_online_provider(
        manifest, tmp_path / "cache", opener=opener
    )
    assert isinstance(provider, OnlineDictionaryProvider)
    assert provider.asset_token == DEFAULT_DATASET_TOKEN
