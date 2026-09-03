"""Dictionary session facade: the runtime view of the active provider.

The :class:`DictionarySession` is the bound, process-wide facade used by
``app/api.py`` after Slice 12. It hides the choice of provider
(``LocalDictionaryProvider`` vs ``OnlineDictionaryProvider``) behind the
:func:`reading` context manager, the same lookup oracle shape the
frontend resolver already uses, and the structured ``asset_token``
snapshot used to validate stale picker tokens (ADR-0004 D47).

No persisted mode/state is introduced: every :class:`DictionarySession`
exists only for the lifetime of one process, and removal/activation
modes bind state to runtime attributes, not to the user database.

The class does not reimplement the resolver's lookup ladder; it wraps
the abstract :class:`DictionaryProvider` so ``resolve_token`` and
``resolve_word`` from :mod:`app.resolve` can be called unchanged.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from app.deck import ReadingSnapshot
from app.provider import DictionaryProvider
from app.resolve import LookupProtocol


class _RuntimeLocalFacade(Protocol):
    """Minimal surface of ``DictionaryRuntime`` that the session uses."""

    @property
    def asset_token(self) -> str: ...

    @property
    def lemma_ids(self) -> Mapping[str, int]: ...

    @property
    def sense_ids(self) -> Mapping[str, tuple[int, int]]: ...

    def reading(self) -> Any: ...

    def provider(self) -> DictionaryProvider: ...

    def materialize_lookup(
        self, query: str
    ) -> tuple[str, tuple[Mapping[str, object], ...]]: ...

    def observe_card_render(
        self,
        card_id: int | None = None,
        *,
        deck_id: int | None = None,
    ) -> Mapping[str, object] | None: ...

    def observe_export_payload(
        self, deck_id: int | None = None
    ) -> tuple[Mapping[str, object], ...]: ...


@dataclass
class _LocalBackedSnapshot:
    """Adapter from a ``ReadingSnapshot`` to the session shape the API needs."""

    asset_token: str
    lemma_ids: MappingProxyType[str, int]
    sense_ids: MappingProxyType[str, tuple[int, int]]
    provider: DictionaryProvider


class _ProviderBackedLemmaIds:
    """A read-only Mapping that looks up ``lemma_ref -> lemma_id`` via the provider.

    Used only for Online mode, where the provider exposes
    ``lemma_for_ref`` (O(1) entry-shard lookup) but does not maintain an
    upfront inverse map. Off-line mode keeps the eager ``MappingProxy``
    populated by ``DictionaryRuntime``. The proxy supports
    ``__contains__`` and ``__getitem__`` only as needed for the
    served-product endpoints (``in`` membership checks).
    """

    def __init__(self, provider: DictionaryProvider) -> None:
        self._provider = provider

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self._provider.lemma_for_ref(key) is not None

    def __getitem__(self, key: str) -> int:
        entry = self._provider.lemma_for_ref(key)
        if entry is None:
            raise KeyError(key)
        return int(entry.lemma_id)


class _ProviderBackedSenseIds:
    """A read-only Mapping proxy that looks up ``sense_ref -> (sense_id, lemma_id)``.

    Used in Online mode. The provider exposes ``senses_for_ref`` via the
    entry-shard; the proxy materializes the tuple on demand. Iteration
    is intentionally unsupported: the served-product paths only need
    membership and ``__getitem__``.
    """

    def __init__(self, provider: DictionaryProvider) -> None:
        self._provider = provider

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self._provider.sense_route(key) is not None

    def __getitem__(self, key: str) -> tuple[int, int]:
        route = self._provider.sense_route(key)
        if route is None:
            raise KeyError(key)
        lemma_ref, _ = route
        senses = self._provider.senses_for_ref(lemma_ref)
        for s in senses:
            if str(s.semantic_ref) == key:
                return (int(s.sense_id), int(s.lemma_id))
        raise KeyError(key)


class _ProviderOracle(LookupProtocol):
    """Provider-backed :class:`LookupProtocol` (CF1 adapter).

    The provider's hit type uses ``lemma_id`` while ``app.resolve``'s
    ``LemmaRecord`` uses ``id``; this adapter is the smallest possible
    mechanical bridge at the integration boundary.
    """

    def __init__(self, provider: DictionaryProvider) -> None:
        self._provider = provider

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[Any]:
        from app.resolve import LemmaRecord

        hits = self._provider.lookup_exact(lemma, pos=pos, gender=gender)
        out = []
        for hit in hits:
            out.append(
                LemmaRecord(
                    id=int(hit.lemma_id),
                    lemma=str(hit.lemma),
                    pos=str(hit.pos),
                    gender=hit.gender,
                    semantic_ref=str(hit.semantic_ref),
                    freq_rank=hit.freq_rank,
                )
            )
        return tuple(out)

    def lookup_surface_form(self, form: str) -> Sequence[Any]:
        from app.resolve import LemmaRecord

        hits = self._provider.lookup_surface_form(form)
        out = []
        for hit in hits:
            out.append(
                LemmaRecord(
                    id=int(hit.lemma_id),
                    lemma=str(hit.lemma),
                    pos=str(hit.pos),
                    gender=hit.gender,
                    semantic_ref=str(hit.semantic_ref),
                    freq_rank=hit.freq_rank,
                )
            )
        return tuple(out)

    def lookup_senses(self, lemma_id: int) -> Sequence[Any]:
        from app.resolve import SenseRecord

        hits = self._provider.lookup_senses(int(lemma_id))
        return tuple(
            SenseRecord(
                id=int(h.sense_id),
                lemma_id=int(h.lemma_id),
                ord=int(h.ord),
                semantic_ref=str(h.semantic_ref),
            )
            for h in hits
        )


@dataclass(frozen=True)
class OnlineSessionInfo:
    """Exposed online-session metadata for the Settings UI and tests."""

    dataset_token: str
    asset_token: str
    cache_dir: str


class DictionarySession:
    """The Slice 12 session-scoped provider facade used by ``app/api.py``.

    A session owns one of:

    * a ``DictionaryRuntime`` (Offline mode) — exposes its asset as a
      :class:`LocalDictionaryProvider` plus the existing
      ``ReadingSnapshot`` data;
    * an :class:`OnlineDictionaryProvider` directly (Online mode).

    There is no persisted representation; the chosen mode lives only in
    this process. Restart behavior is derived from the canonical
    Offline asset + CLI invocation per ADR-0009.
    """

    def __init__(
        self,
        *,
        runtime: _RuntimeLocalFacade | None = None,
        provider: DictionaryProvider | None = None,
        online_info: OnlineSessionInfo | None = None,
    ) -> None:
        if runtime is None and provider is None:
            raise ValueError("DictionarySession requires either a runtime or a provider")
        if runtime is not None and provider is not None:
            raise ValueError("DictionarySession accepts only one of runtime or provider")
        self._runtime = runtime
        self._direct_provider = provider
        self._online_info = online_info
        self._closed = False

    @property
    def is_online(self) -> bool:
        return self._direct_provider is not None

    @property
    def online_info(self) -> OnlineSessionInfo | None:
        return self._online_info

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._direct_provider is not None:
                self._direct_provider.close()
        except Exception:
            pass

    def asset_token(self) -> str:
        if self._runtime is not None:
            return str(self._runtime.asset_token)
        assert self._direct_provider is not None
        return str(self._direct_provider.asset_token)

    def provider(self) -> DictionaryProvider:
        if self._runtime is not None:
            return self._runtime.provider()
        assert self._direct_provider is not None
        return self._direct_provider

    def oracle(self) -> LookupProtocol:
        """Return a provider-backed :class:`LookupProtocol` for the resolver."""
        return _ProviderOracle(self.provider())

    @contextmanager
    def reading(self) -> Iterator[ReadingSnapshot | _LocalBackedSnapshot]:
        """Yield an inert immutable snapshot under one read pin."""
        if self._runtime is not None:
            with self._runtime.reading() as snap:
                yield snap
            return
        assert self._direct_provider is not None
        prov = self._direct_provider
        yield _LocalBackedSnapshot(
            asset_token=str(prov.asset_token),
            lemma_ids=_ProviderBackedLemmaIds(prov),  # type: ignore[arg-type]
            sense_ids=_ProviderBackedSenseIds(prov),  # type: ignore[arg-type]
            provider=prov,
        )

    def materialize_lookup(
        self, query: str
    ) -> tuple[str, tuple[Mapping[str, object], ...]]:
        """Lookup helper matching the legacy runtime/materialize_lookup return shape."""
        if self._runtime is not None:
            result = self._runtime.materialize_lookup(query)
            return (result[0], tuple(result[1]))
        # Online path: produce the same MappingProxyType[str, object] shape.
        from types import MappingProxyType as _MP

        assert self._direct_provider is not None
        candidates = self._direct_provider.candidate_lookup(query)
        token = str(self._direct_provider.asset_token)
        out = []
        for cand in candidates:
            lemma = cand.lemma
            senses_data = []
            for sense, meanings in cand.senses:
                senses_data.append(
                    _MP(
                        {
                            "sense_id": int(sense.sense_id),
                            "sense_semantic_ref": str(sense.semantic_ref),
                            "source_namespace": str(sense.source_namespace),
                            "source_ref": str(sense.source_ref),
                            "ord": int(sense.ord),
                            "register": sense.register,
                            "meanings": tuple(
                                _MP(
                                    {
                                        "language": str(m.language),
                                        "kind": str(m.kind),
                                        "text": str(m.text),
                                        "ord": int(m.ord),
                                    }
                                )
                                for m in meanings
                            ),
                        }
                    )
                )
            out.append(
                _MP(
                    {
                        "lemma_id": int(lemma.lemma_id),
                        "lemma_semantic_ref": str(lemma.semantic_ref),
                        "lemma": str(lemma.lemma),
                        "pos": str(lemma.pos),
                        "gender": lemma.gender,
                        "senses": tuple(senses_data),
                        "examples": tuple(
                            _MP(
                                {
                                    "de": str(ex.de),
                                    "en": str(ex.en) if ex.en is not None else None,
                                }
                            )
                            for ex in cand.examples
                        ),
                    }
                )
            )
        return (token, tuple(out))

    def observe_card_render(
        self,
        card_id: int | None = None,
        *,
        deck_id: int | None = None,
    ) -> Mapping[str, object] | None:
        """Observe a card-render observation under a single read pin."""
        if self._runtime is not None:
            return self._runtime.observe_card_render(card_id=card_id, deck_id=deck_id)
        # Online path does not maintain a card-render queue; this slot is
        # intentionally limited to Local/Offline mode for the production
        # runtime path; the API converts ``None`` into an empty card.
        return None

    def observe_export_payload(
        self, deck_id: int | None = None
    ) -> tuple[Mapping[str, object], ...]:
        """Observe export payloads inside a single read pin."""
        if self._runtime is not None:
            return self._runtime.observe_export_payload(deck_id=deck_id)
        return ()

    def materialized_lookup_token(self) -> str:
        """Return the asset token without IO (helper for materialised shims)."""
        return self.asset_token()


__all__ = [
    "DictionarySession",
    "OnlineSessionInfo",
]
