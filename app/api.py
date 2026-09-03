"""Standalone HTTP application, API endpoints, and browser loopback security guards.

Implements ADR-0001, ADR-0002 §4.1 / D24 / D25, ADR-0003, ADR-0004, ADR-0005,
ADR-0007 D80, and AGENTS rules R4, R5, R6, R9, R10, R12, R13, C1, C2.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, cast

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.audio import (
    PIPER_PINNED_VOICE,
    CustomAudioError,
    HumanAudioProvenance,
    MediaValidationError,
    evaluate_human_audio_policy,
    get_custom_pronunciation,
    revert_custom_pronunciation,
    save_custom_pronunciation,
    select_pronunciation_audio,
    validate_audio_bytes,
)
from app.deck import (
    DeckError,
    DictionaryClosedError,
    DictionaryRuntime,
    DictionaryRuntimeError,
    add_note_to_deck,
    create_deck,
    create_note,
    delete_deck,
    delete_user_meaning,
    review,
    set_meaning_languages,
    set_user_meaning,
)
from app.dictionary import DictionaryAssetError, validate_candidate_dictionary
from app.dictionary_mode import (
    OFFLINE_INSTALL_DEFAULT_MANIFEST_BYTES,
    OfflineInstallRefused,
    preflight_offline_install,
    remove_canonical_offline,
    session_status,
)
from app.dictionary_session import DictionarySession, OnlineSessionInfo
from app.examples import rank_examples
from app.export import ExportAudio, build_apkg
from app.provider import (
    DictionaryProvider,
    ProviderBudgetExceededError,
    ProviderIntegrityError,
    ProviderNetworkError,
    ProviderUnavailableError,
)
from app.render import (
    AudioTrigger,
    CardRenderInput,
    DerivedComponent,
    MeaningBlock,
    RenderExample,
    RenderLemmaData,
    render_card,
    validate_selected_languages,
)
from app.resolve import LemmaRecord, LookupProtocol, Ref, SenseRecord, resolve_token, resolve_word

_NLP_MODEL: Any = None
_NLP_INITIALIZED: bool = False


def _get_nlp() -> Any | None:
    global _NLP_MODEL, _NLP_INITIALIZED
    if not _NLP_INITIALIZED:
        _NLP_INITIALIZED = True
        try:
            import spacy

            _NLP_MODEL = spacy.load("de_core_news_md")
        except Exception:
            _NLP_MODEL = None
    return _NLP_MODEL


class _ConnectionLookupOracle(LookupProtocol):
    """Legacy SQL-backed oracle retained only for legacy tests of the old path.

    The served-product endpoints migrated onto ``_ProviderOracle`` (see
    below); this class is preserved so non-product unit tests can
    exercise the raw SQLite lookup closure under the same resolver
    signature. New code MUST go through :class:`DictionaryProvider`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaRecord]:
        query = (
            "SELECT id, semantic_ref, lemma, pos, gender, freq_rank "
            "FROM lemma WHERE (lemma = ? OR lower(lemma) = ?) "
        )
        params: list[Any] = [lemma, lemma.lower()]
        if pos is not None:
            query += "AND pos = ? "
            params.append(pos)
        if gender is not None:
            query += "AND gender = ? "
            params.append(gender)
        query += (
            "ORDER BY freq_rank ASC NULLS LAST, pos ASC, "
            "gender ASC NULLS LAST, semantic_ref ASC"
        )
        cur = self.conn.execute(query, params)
        return [
            LemmaRecord(
                id=int(r[0]),
                semantic_ref=str(r[1]),
                lemma=str(r[2]),
                pos=str(r[3]),
                gender=str(r[4]) if r[4] is not None else None,
                freq_rank=int(r[5]) if r[5] is not None else None,
            )
            for r in cur.fetchall()
        ]

    def lookup_surface_form(self, form: str) -> Sequence[LemmaRecord]:
        cur = self.conn.execute(
            """
            SELECT l.id, l.semantic_ref, l.lemma, l.pos, l.gender, l.freq_rank
            FROM surface_form sf
            JOIN lemma l ON sf.lemma_id = l.id
            WHERE (sf.form = ? OR lower(sf.form) = ?)
            ORDER BY l.freq_rank ASC NULLS LAST, l.pos ASC,
                     l.gender ASC NULLS LAST, l.semantic_ref ASC
            """,
            (form, form.lower()),
        )

        seen: set[int] = set()
        res: list[LemmaRecord] = []
        for r in cur.fetchall():
            lid = int(r[0])
            if lid not in seen:
                seen.add(lid)
                res.append(
                    LemmaRecord(
                        id=lid,
                        semantic_ref=str(r[1]),
                        lemma=str(r[2]),
                        pos=str(r[3]),
                        gender=str(r[4]) if r[4] is not None else None,
                        freq_rank=int(r[5]) if r[5] is not None else None,
                    )
                )
        return res

    def lookup_senses(self, lemma_id: int) -> Sequence[SenseRecord]:
        cur = self.conn.execute(
            """
            SELECT id, lemma_id, ord, semantic_ref
            FROM sense WHERE lemma_id = ?
            ORDER BY ord ASC, semantic_ref ASC, id ASC
            """,
            (lemma_id,),
        )
        return [
            SenseRecord(
                id=int(r[0]),
                lemma_id=int(r[1]),
                ord=int(r[2]),
                semantic_ref=str(r[3]) if r[3] is not None else None,
            )
            for r in cur.fetchall()
        ]


_PROVIDER_FAILURE_CODES: Final[MappingProxyType[str, int]] = MappingProxyType(
    {
        "network": 502,
        "integrity": 502,
        "budget": 503,
        "unavailable": 503,
    }
)


def _provider_failure_to_response(exc: BaseException) -> JSONResponse:
    """Translate a provider failure to a structured HTTP response.

    The product contract refuses to map provider failures onto a silent
    ``needs_gloss`` / ``not_found`` outcome or successful PART-B write.
    The error carries a stable code clients can distinguish.
    """
    if isinstance(exc, ProviderBudgetExceededError):
        detail_code = "budget"
    elif isinstance(exc, ProviderNetworkError):
        detail_code = "network"
    elif isinstance(exc, ProviderIntegrityError):
        detail_code = "integrity"
    else:
        detail_code = "unavailable"
    status_code = int(_PROVIDER_FAILURE_CODES[detail_code])
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": f"online_provider_error: {detail_code}",
            "code": detail_code,
            "message": str(exc),
        },
    )


class _ProviderOracle(LookupProtocol):
    """Provider-backed resolver oracle used by every served-product endpoint.

    CF1: the provider's hit type is ``LemmaHit`` with field ``lemma_id``,
    while the resolver's :class:`LemmaRecord` exposes ``id``. This is
    the smallest mechanical adapter at the integration boundary; neither
    contract is redesigned for the field name.
    """

    def __init__(self, provider: DictionaryProvider) -> None:
        self._provider = provider

    def lookup_exact(
        self, lemma: str, pos: str | None = None, gender: str | None = None
    ) -> Sequence[LemmaRecord]:
        hits = self._provider.lookup_exact(lemma, pos=pos, gender=gender)
        return tuple(
            LemmaRecord(
                id=int(hit.lemma_id),
                lemma=str(hit.lemma),
                pos=str(hit.pos),
                gender=hit.gender,
                semantic_ref=str(hit.semantic_ref),
                freq_rank=hit.freq_rank,
            )
            for hit in hits
        )

    def lookup_surface_form(self, form: str) -> Sequence[LemmaRecord]:
        # CF2: surface-form lookup must preserve Local's surface-only
        # semantics. We delegate to the provider's
        # ``lookup_surface_form`` directly; Local and Online both probe
        # ONLY the surface-form table (no implicit lemma-table
        # pre-query that could suppress valid surface results).
        hits = self._provider.lookup_surface_form(form)
        return tuple(
            LemmaRecord(
                id=int(hit.lemma_id),
                lemma=str(hit.lemma),
                pos=str(hit.pos),
                gender=hit.gender,
                semantic_ref=str(hit.semantic_ref),
                freq_rank=hit.freq_rank,
            )
            for hit in hits
        )

    def lookup_senses(self, lemma_id: int) -> Sequence[SenseRecord]:
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


def _materialize_candidate_from_ref(
    ref: Ref,
    provider: DictionaryProvider,
    oracle: _ProviderOracle,
    *,
    known_lemmas: Sequence[str] | None = None,
) -> dict[str, Any] | None:
    if ref.status == "resolved":
        # Slice 12 provider migration: the served-product materialization
        # no longer opens a raw ``asset.connection`` or issues SQL. It
        # routes through ``LookupProtocol.lookup_exact`` (provider-backed)
        # to resolve the durable lemma ref, then asks the provider for a
        # composite entry and examples through the Slice-11 contract.
        lemma_hits = provider.lookup_exact(
            ref.lemma, pos=ref.pos, gender=ref.gender
        )
        if not lemma_hits:
            return None
        matched_hit = next(
            (
                hit
                for hit in lemma_hits
                if hit.pos == ref.pos and hit.gender == ref.gender
            ),
            None,
        )
        if matched_hit is None:
            return None
        lemma_id = int(matched_hit.lemma_id)
        entry = provider.entry_for_id(lemma_id)
        if entry is None:
            return None

        lem_ref = str(entry.lemma.semantic_ref)

        senses_list: list[dict[str, Any]] = []
        for sense in entry.senses:
            sid = int(sense.sense_id)
            s_sref = str(sense.semantic_ref)
            s_means = [
                {
                    "language": str(m.language),
                    "kind": str(m.kind),
                    "ord": int(m.ord),
                    "text": str(m.text),
                    "source": str(m.source),
                    "license": str(m.license),
                }
                for m in entry.meanings
                if int(m.sense_id) == sid
            ]
            gloss_text = s_means[0]["text"] if s_means else ""
            senses_list.append({
                "sense_id": sid,
                "sense_semantic_ref": s_sref,
                "ref": s_sref,
                "ord": int(sense.ord),
                "gloss": gloss_text,
                "meanings": s_means,
            })

        raw_examples = [
            {
                "id": int(ex.example_id),
                "de": str(ex.de),
                "en": str(ex.en) if ex.en is not None else None,
                "source": str(ex.source) if ex.source is not None else "",
                "license": str(ex.license) if ex.license is not None else "",
                "token_count": int(ex.token_count) if ex.token_count is not None else None,
                "has_proper": bool(ex.has_proper),
            }
            for ex in entry.examples
        ]
        ranked_exs = rank_examples(raw_examples, known_lemmas=known_lemmas)

        grammar_data = {
            "pos": str(entry.lemma.pos),
            "gender": entry.lemma.gender,
            "plural": entry.lemma.plural,
            "genitive_sg": entry.lemma.genitive_sg,
            "aux": entry.lemma.aux,
            "separable": bool(entry.lemma.separable),
            "particle": entry.lemma.particle,
            "reflexive": bool(entry.lemma.reflexive),
            "praesens_3sg": entry.lemma.praesens_3sg,
            "praeteritum_3sg": entry.lemma.praeteritum_3sg,
            "partizip_ii": entry.lemma.partizip_ii,
            "governs": entry.lemma.governs,
            "comparative": entry.lemma.comparative,
            "superlative": entry.lemma.superlative,
            "ipa": entry.lemma.ipa,
        }

        return {
            "ref": lem_ref,
            "lemma_semantic_ref": lem_ref,
            "lemma": str(entry.lemma.lemma),
            "pos": str(entry.lemma.pos),
            "gender": entry.lemma.gender,
            "status": "resolved",
            "senses": senses_list,
            "grammar": grammar_data,
            "examples": ranked_exs,
        }

    elif ref.status == "derived_compound":
        comp_refs = (
            [(cb.lemma_ref, cb.sense_ref) for cb in ref.component_bindings]
            if ref.component_bindings
            else []
        )
        comp_data = []
        if ref.component_bindings:
            for cb in ref.component_bindings:
                comp_data.append({
                    "lemma": cb.lemma,
                    "lemma_ref": cb.lemma_ref,
                    "sense_ref": cb.sense_ref,
                })
        lem_ref_str = (
            f"lemma:v1:{ref.lemma.lower()}_{ref.pos.lower()}_{ref.gender.lower()}"
            if ref.gender
            else f"lemma:v1:{ref.lemma.lower()}_{ref.pos.lower()}"
        )
        return {
            "ref": lem_ref_str,
            "lemma_semantic_ref": lem_ref_str,
            "lemma": ref.lemma,
            "pos": ref.pos,
            "gender": ref.gender,
            "status": "derived_compound",
            "component_refs": comp_refs,
            "components": comp_data,
            "senses": [],
            "grammar": {
                "pos": ref.pos,
                "gender": ref.gender,
            },
            "examples": [],
        }

    else:
        lem_ref_str = f"lemma:v1:{ref.lemma.lower()}_{ref.pos.lower()}"
        return {
            "ref": lem_ref_str,
            "lemma_semantic_ref": lem_ref_str,
            "lemma": ref.lemma,
            "pos": ref.pos,
            "gender": ref.gender,
            "status": "needs_gloss",
            "senses": [],
            "grammar": {},
            "examples": [],
        }


LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({
    "127.0.0.1",
    "localhost",
    "[::1]",
})


def _is_loopback_host(host_header: str | None, *, port: int) -> bool:
    """Return whether ``Host`` is one exact loopback endpoint for ``port``.

    ``Host`` is a browser security boundary, not a hint for routing.  Parsing
    it by splitting on ``:`` accepted malformed IPv6 and silently ignored a
    supplied port.  The service never listens on an arbitrary port, so accept
    only the three contract host spellings with the configured port.
    """
    if not host_header or host_header != host_header.strip():
        return False
    host = host_header.lower()
    return host in {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}


class BrowserSecurityMiddleware(BaseHTTPMiddleware):
    """ASGI middleware enforcing AGENTS R12 and ADR-0002 §4.1 browser trust boundary."""

    def __init__(
        self,
        app: ASGIApp,
        cors_origins: set[str],
        service_port: int,
    ) -> None:
        super().__init__(app)
        self.cors_origins = cors_origins
        self.service_port = service_port

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Host header validation
        host = request.headers.get("host")
        if not _is_loopback_host(host, port=self.service_port):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Host header must be a loopback endpoint on the configured port"
                },
            )

        # 2. Origin header validation (when present)
        origin = request.headers.get("origin")
        if origin is not None and origin not in self.cors_origins:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Forbidden origin: {origin}"},
            )

        # Handle CORS preflight OPTIONS request
        if request.method == "OPTIONS":
            response = Response(status_code=status.HTTP_200_OK)
            if origin is not None and origin in self.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, DELETE, OPTIONS, PUT, PATCH"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, X-Flashcards-Request"
                )
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # 3. Non-GET /vocab route security checks
        path = request.url.path
        if path.startswith("/vocab") and request.method != "GET":
            # Header X-Flashcards-Request must equal "1"
            custom_header = request.headers.get("x-flashcards-request")
            if custom_header != "1":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": "Missing/invalid X-Flashcards-Request; must be exactly '1'"
                    },
                )

            # JSON Content-Type check on JSON routes
            is_audio_upload = request.method == "POST" and "/audio" in path
            is_delete = request.method == "DELETE"
            if not is_audio_upload and not is_delete:
                content_type = request.headers.get("content-type", "")
                media_type = content_type.split(";", maxsplit=1)[0].strip().lower()
                if media_type != "application/json":
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Content-Type must be application/json"},
                    )

        response = await call_next(request)

        # Set CORS headers on response if origin is valid
        if origin is not None and origin in self.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


def _to_json_compatible(val: Any) -> Any:
    if isinstance(val, (MappingProxyType, dict)):
        return {k: _to_json_compatible(v) for k, v in val.items()}
    if isinstance(val, (tuple, list, set, frozenset)):
        return [_to_json_compatible(item) for item in val]
    return val


def _render_input_from_observation(
    obs: Mapping[str, Any],
    *,
    with_audio: bool = True,
) -> CardRenderInput:
    note_id = int(obs["note_id"])
    note_status = str(obs["note_status"])
    lemma_ref = str(obs["lemma_semantic_ref"])
    sense_ref = str(obs["sense_semantic_ref"]) if obs["sense_semantic_ref"] else None
    selected_langs = tuple(str(x) for x in obs["selected_languages"])
    user_meanings_dict = cast(Mapping[str, str], obs["user_meanings"])
    components = cast(Sequence[Mapping[str, Any]], obs["components"])
    lem_map = cast(Mapping[str, Any] | None, obs["lemma"])
    senses_list = cast(Sequence[Mapping[str, Any]], obs["senses"])
    meanings_list = cast(Sequence[Mapping[str, Any]], obs["meanings"])
    examples_list = cast(Sequence[Mapping[str, Any]], obs["examples"])

    if lem_map is None:
        raw_headword = lemma_ref.split(":")[-1]
        lemma_data = RenderLemmaData(lemma=raw_headword, pos="NOUN")
    else:
        lemma_data = RenderLemmaData(
            lemma=str(lem_map["lemma"]),
            pos=str(lem_map["pos"]),
            gender=lem_map["gender"],
            plural=lem_map["plural"],
            plural_none=int(lem_map["plural_none"]),
            genitive_sg=lem_map["genitive_sg"],
            aux=lem_map["aux"],
            separable=int(lem_map["separable"]),
            particle=lem_map["particle"],
            reflexive=int(lem_map["reflexive"]),
            praesens_3sg=lem_map["praesens_3sg"],
            praeteritum_3sg=lem_map["praeteritum_3sg"],
            partizip_ii=lem_map["partizip_ii"],
            governs=lem_map["governs"],
            comparative=lem_map["comparative"],
            superlative=lem_map["superlative"],
            ipa=lem_map["ipa"],
        )

    meaning_blocks: list[MeaningBlock] = []
    if note_status == "derived_compound" and components:
        for lang in ("de", "en"):
            if lang in selected_langs:
                if lang in user_meanings_dict:
                    meaning_blocks.append(
                        MeaningBlock(
                            language=lang,
                            origin="user",
                            texts=(user_meanings_dict[lang],),
                        )
                    )
                else:
                    components_list = [
                        DerivedComponent(
                            lemma=str(c["lemma"]),
                            text=cast(Mapping[str, str], c["meanings"]).get(lang),
                        )
                        for c in components
                    ]
                    if components_list:
                        meaning_blocks.append(
                            MeaningBlock(
                                language=lang,
                                origin="derived_component",
                                components=tuple(components_list),
                            )
                        )
    else:
        for lang in ("de", "en"):
            if lang in selected_langs:
                if lang in user_meanings_dict:
                    meaning_blocks.append(
                        MeaningBlock(
                            language=lang,
                            origin="user",
                            texts=(user_meanings_dict[lang],),
                        )
                    )
                else:
                    sense_match_ids = [
                        s["id"] for s in senses_list if s["semantic_ref"] == sense_ref
                    ]
                    has_matching_sense = any(
                        s["semantic_ref"] == sense_ref for s in senses_list
                    )
                    matching_m = [
                        str(m["text"])
                        for m in meanings_list
                        if m["language"] == lang
                        and (
                            sense_ref is None
                            or m["sense_id"] in sense_match_ids
                            or not has_matching_sense
                        )
                    ]
                    if matching_m:
                        meaning_blocks.append(
                            MeaningBlock(
                                language=lang,
                                origin="dictionary",
                                texts=tuple(matching_m),
                            )
                        )

    render_examples_list = tuple(
        RenderExample(de=str(e["de"]), en=e.get("en"))
        for e in examples_list
    )

    audio_trigger: AudioTrigger | None = None
    if with_audio:
        if obs.get("has_custom_audio", False):
            audio_trigger = AudioTrigger(
                available=True,
                lemma=lemma_data.lemma,
                token=f"custom:{note_id}",
            )
        else:
            audio_trigger = AudioTrigger(available=True, lemma=lemma_data.lemma)

    return CardRenderInput(
        lemma=lemma_data,
        selected_languages=selected_langs,
        meanings=tuple(meaning_blocks),
        examples=render_examples_list,
        audio_trigger=audio_trigger,
    )


def _get_user_db_conn(app: FastAPI) -> sqlite3.Connection:
    conn = sqlite3.connect(app.state.user_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _export_audio_for_observation(
    app: FastAPI, observation: Mapping[str, object]
) -> Mapping[str, ExportAudio]:
    """Resolve one APKG asset without changing application-owned state.

    Export intentionally omits the optional remote ``/speak`` layer.  It uses
    the shared D48 resolver for custom, policy-approved redistributable human,
    and local Piper audio, while passing no cache directory so an export cannot
    populate or otherwise mutate the disposable automatic-audio cache.
    """
    note_id = int(cast(int, observation["note_id"]))
    lemma_data = cast(Mapping[str, object], observation["lemma"])
    lemma = str(lemma_data["lemma"])

    exact_human_id: str | None = None
    human_id_for_observation = getattr(app.state, "human_audio_id_for_observation", None)
    if callable(human_id_for_observation):
        candidate_id = human_id_for_observation(observation)
        if isinstance(candidate_id, str) and candidate_id.strip():
            exact_human_id = candidate_id.strip()

    configured_human_resolver = getattr(app.state, "human_audio_resolver", None)

    def export_human_resolver(exact_id: str) -> tuple[bytes, HumanAudioProvenance]:
        if not callable(configured_human_resolver):
            raise LookupError("no human-audio resolver is configured")
        raw_bytes, provenance = configured_human_resolver(exact_id)
        if not (
            evaluate_human_audio_policy(provenance) and provenance.redistribution_eligible
        ):
            raise LookupError("human audio is not eligible for APKG redistribution")
        return raw_bytes, provenance

    conn = _get_user_db_conn(app)
    try:
        result = select_pronunciation_audio(
            lemma=lemma,
            note_id=note_id,
            user_db=conn,
            media_dir=app.state.media_dir,
            # Export must not write the automatic-audio cache.
            cache_dir=None,
            exact_human_id=exact_human_id,
            human_resolver=export_human_resolver if exact_human_id is not None else None,
            # Deliberately no tts_remote_url or remote_speak_client: remote
            # composition is not part of the APKG export contract.
            piper_runner=getattr(app.state, "piper_runner", None),
        )
    finally:
        conn.close()
    if (
        result.source is None
        or result.audio_bytes is None
        or result.format is None
        or result.sha256 is None
    ):
        return {}

    if result.source == "custom" and result.media_filename is not None:
        filename = result.media_filename
    else:
        filename = f"{result.source}-{result.sha256[:16]}.{result.format}"
    return {
        result.source: ExportAudio(filename=filename, data=result.audio_bytes, source=result.source)
    }


def _piper_runner_if_available() -> Callable[[str, str], bytes] | None:
    """Return the image-pinned Piper runner, or ``None`` outside that image."""
    executable = shutil.which("piper")
    voice_path = Path(os.environ.get("PIPER_VOICE_PATH", "/opt/piper/de_DE-thorsten-high.onnx"))
    if executable is None or not voice_path.is_file():
        return None

    def run_piper(text: str, voice: str) -> bytes:
        if voice != PIPER_PINNED_VOICE:
            raise ValueError(f"unexpected Piper voice: {voice}")
        with tempfile.TemporaryDirectory(prefix="flashcard-piper-") as tmp:
            output_path = Path(tmp) / "pronunciation.wav"
            subprocess.run(
                [executable, "--model", str(voice_path), "--output_file", str(output_path)],
                input=text.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            return output_path.read_bytes()

    return run_piper


def _runtime_or_unconfigured(
    app: FastAPI, runtime: "DictionaryRuntime | None"
) -> "JSONResponse | DictionaryRuntime":
    """Return the runtime or a 503 chooser-state response for Offline-only endpoints."""
    if runtime is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Offline-only endpoint called while a non-Offline "
                    "session is active or no provider is configured"
                ),
                "code": "offline_runtime_unavailable",
            },
        )
    return runtime


def _session_or_unconfigured(app: FastAPI) -> "JSONResponse | DictionarySession":
    """Return the bound ``DictionarySession`` or a 503 chooser-state response.

    The chooser-state response carries a stable ``code`` so the UI can
    show the runtime chooser without crashing other endpoints.
    """
    session = getattr(app.state, "session", None)
    if session is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "dictionary is not configured for this session; the "
                    "runtime chooser is visible"
                ),
                "code": "dictionary_unconfigured",
            },
        )
    return session  # type: ignore[no-any-return]


def create_app(
    dict_path: Path | str | None = None,
    user_db_path: Path | str | None = None,
    cors_origins: Sequence[str] | set[str] | None = None,
    *,
    tts_remote_url: str | None = None,
    media_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
    service_port: int = 8000,
    expected_dictionary_sha256: str | None = None,
    expected_dictionary_version: str = "v1",
    runtime: "DictionaryRuntime | None" = None,
    online_provider: "DictionaryProvider | None" = None,
    online_session_info: "OnlineSessionInfo | None" = None,
    online_provider_factory: (
        "Callable[[], tuple[DictionaryProvider, OnlineSessionInfo]] | None"
    ) = None,
    manifest_filename: str = "dictionary.sqlite",
    managed_dictionary_dir: Path | str | None = None,
    human_audio_id_for_observation: Callable[[Mapping[str, object]], str | None] | None = None,
    human_audio_resolver: Callable[[str], tuple[bytes, HumanAudioProvenance]] | None = None,
    piper_runner: Callable[[str, str], bytes] | None = None,
) -> FastAPI:
    """Create and configure the standalone FastAPI vocabulary application.

    Zero module-level state; no environment reads at import time (AGENTS C1).

    Two construction modes:

    1. ``dict_path`` is provided — the application builds a
       ``DictionaryRuntime`` from the canonical Offline dictionary. This
       is the legacy fully-local mode and the canonical launcher's mode.
    2. ``runtime`` is provided — a pre-built ``DictionaryRuntime`` (with
       a verified canonical asset) is reused; E2E harnesses use this to
       share a single runtime across endpoints.
    3. ``online_provider`` is provided — an ``OnlineDictionaryProvider``
       built against the deterministic Slice 11 harness. The application
       binds a session to that provider instead of a runtime. No PART-B
       migration is performed when Online mode is bound; ``user_db_path``
       is still required for fresh note creation against existing user
       state.

    The session-scoped chooser/preference state is held on ``app.state``
    but never persisted.
    """
    if user_db_path is None:
        raise ValueError("user_db_path is required")
    if not isinstance(cors_origins, (list, tuple, set, frozenset)):
        raise TypeError("cors_origins must be a sequence or set of origin strings")
    if isinstance(service_port, bool) or not isinstance(service_port, int):
        raise TypeError("service_port must be an integer")
    if not 1 <= service_port <= 65535:
        raise ValueError("service_port must be in 1..65535")

    for orig in cors_origins:
        if not isinstance(orig, str):
            raise TypeError("cors_origins entries must be strings")
        if "*" in orig:
            raise ValueError(f"Wildcard origin is forbidden: {orig!r}")

    cors_origins_set = set(cors_origins)

    user_db_p = Path(user_db_path).resolve()

    resolved_media_dir = (
        Path(media_dir).resolve()
        if media_dir is not None
        else user_db_p.parent / "media"
    )
    resolved_cache_dir = (
        Path(cache_dir).resolve()
        if cache_dir is not None
        else user_db_p.parent / "cache"
    )

    resolved_media_dir.mkdir(parents=True, exist_ok=True)
    resolved_cache_dir.mkdir(parents=True, exist_ok=True)

    if runtime is None and online_provider is None:
        if dict_path is None:
            # Slice 12 chooser state: no provider bound yet. The runtime
            # Settings endpoint exposes
            # ``/vocab/settings/dictionary/install-offline`` /
            # ``use-online`` etc. which construct a session at runtime.
            # The /vocab/lookup + dictionary reads in chooser state are
            # themselves not used (the UI shows the chooser).
            runtime = None
        else:
            dict_p = Path(dict_path).resolve()
            runtime = DictionaryRuntime(
                dict_p,
                user_db_p,
                expected_sha256=expected_dictionary_sha256,
                expected_version=expected_dictionary_version,
            )
    elif online_provider is not None:
        if dict_path is not None or runtime is not None:
            raise ValueError(
                "online_provider cannot be combined with dict_path or runtime"
            )

    resolved_managed_dir = (
        Path(managed_dictionary_dir).resolve()
        if managed_dictionary_dir is not None
        else user_db_p.parent / "dictionary"
    )

    app = FastAPI(title="Wortlaut Vocabulary API", version="0.1.0")

    app.state.user_db_path = user_db_p
    app.state.cors_origins = cors_origins_set
    app.state.tts_remote_url = tts_remote_url
    app.state.media_dir = resolved_media_dir
    app.state.cache_dir = resolved_cache_dir
    app.state.human_audio_id_for_observation = human_audio_id_for_observation
    app.state.human_audio_resolver = human_audio_resolver
    app.state.piper_runner = piper_runner or _piper_runner_if_available()
    app.state.manifest_filename = manifest_filename
    app.state.managed_dictionary_dir = resolved_managed_dir
    app.state.online_provider_factory = online_provider_factory
    app.state.expected_dictionary_sha256 = expected_dictionary_sha256
    app.state.expected_dictionary_version = expected_dictionary_version

    if runtime is not None:
        app.state.dict_path = runtime.managed_dir / "dictionary.sqlite"
        app.state.runtime = runtime
        session = DictionarySession(runtime=runtime)
        app.state.session = session
        app.state.dictionary_mode = "offline"
        app.state.online_session_info = None
    elif online_provider is not None:
        info = online_session_info or OnlineSessionInfo(
            dataset_token=str(getattr(online_provider, "_dataset_token", "online")),
            asset_token=str(online_provider.asset_token),
            cache_dir=str(getattr(online_provider, "_cache_dir", "")),
        )
        app.state.online_provider = online_provider
        app.state.dict_path = None
        session = DictionarySession(provider=online_provider, online_info=info)
        app.state.session = session
        app.state.dictionary_mode = "online"
        app.state.online_session_info = info
        app.state.runtime = None
    else:
        # Slice 12 chooser state: no dictionary provider bound yet. The
        # session is intentionally None; the Settings endpoint rebuilds
        # it once the user chooses. Most served-product reads will
        # surface a structured 503 until the chooser resolves.
        app.state.runtime = None
        app.state.online_provider = None
        app.state.online_session_info = None
        app.state.session = None
        app.state.dictionary_mode = "unconfigured"
        app.state.dict_path = None

    app.add_middleware(
        BrowserSecurityMiddleware,
        cors_origins=cors_origins_set,
        service_port=service_port,
    )

    @app.on_event("shutdown")
    def shutdown_event() -> None:
        try:
            if runtime is not None and not runtime.is_closed:
                runtime.close()
        except Exception:
            pass
        try:
            session.close()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Endpoints under /vocab prefix
    # -----------------------------------------------------------------------

    @app.get("/vocab/lookup")
    def lookup_endpoint(q: str = Query(...)) -> JSONResponse:
        clean_q = q.strip()
        if not clean_q:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Query parameter 'q' must not be empty"},
            )

        guard = _session_or_unconfigured(app)
        if isinstance(guard, JSONResponse):
            return guard
        try:
            asset_token, candidates = guard.materialize_lookup(clean_q)
        except ProviderUnavailableError as exc:
            return _provider_failure_to_response(exc)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": clean_q,
                "asset_token": asset_token,
                "candidates": _to_json_compatible(candidates),
            },
        )

    @app.post("/vocab/lookup")
    async def lookup_post_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        query = body.get("query") or body.get("q")
        if not query or not isinstance(query, str) or not query.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "query must not be empty"},
            )
        clean_q = query.strip()
        guard = _session_or_unconfigured(app)
        if isinstance(guard, JSONResponse):
            return guard
        try:
            asset_token, candidates = guard.materialize_lookup(clean_q)
        except ProviderUnavailableError as exc:
            return _provider_failure_to_response(exc)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": clean_q,
                "asset_token": asset_token,
                "candidates": _to_json_compatible(candidates),
            },
        )

    @app.post("/vocab/highlight")
    async def highlight_endpoint(request: Request) -> JSONResponse:
        body = await request.json()

        # 1. Validate sentence_text
        sentence_text = body.get("sentence_text")
        if not sentence_text or not isinstance(sentence_text, str) or not sentence_text.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "sentence_text is required and must not be empty"},
            )

        # 2. Validate selected_span
        selected_span = body.get("selected_span")
        if not isinstance(selected_span, dict):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "selected_span must be an object with start and end"},
            )

        start = selected_span.get("start")
        end = selected_span.get("end")
        if (
            start is None
            or end is None
            or isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "selected_span start and end must be integers"},
            )

        if not (0 <= start <= end <= len(sentence_text)):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "selected_span bounds are invalid for sentence_text"},
            )

        # 3. Validate lesson_label
        lesson_label = body.get("lesson_label")
        if not lesson_label or not isinstance(lesson_label, str) or not lesson_label.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "lesson_label is required and must not be blank"},
            )

        lesson_id = body.get("lesson_id")
        known_lemmas_raw = body.get("known_lemmas")
        known_lemmas: Sequence[str] | None = None
        if known_lemmas_raw is not None and isinstance(known_lemmas_raw, (list, tuple)):
            known_lemmas = [str(lem) for lem in known_lemmas_raw]

        selected_text = sentence_text[start:end].strip()

        guard = _session_or_unconfigured(app)
        if isinstance(guard, JSONResponse):
            return guard
        with guard.reading():
            token = guard.asset_token()
            # Perform candidate resolution through the Slice-11
            # provider contract; the served-product read path no longer
            # opens the asset's raw SQLite connection.
            provider = guard.provider()
            oracle = _ProviderOracle(provider)

            # Try spacy token resolution if possible
            refs: list[Ref] = []
            nlp = _get_nlp()
            if nlp is not None:
                try:
                    doc = nlp(sentence_text)
                    target_tokens = [
                        t for t in doc if t.idx < end and (t.idx + len(t.text)) > start
                    ]
                    for tok in target_tokens:
                        try:
                            for r in resolve_token(tok, oracle):
                                if r not in refs:
                                    refs.append(r)
                        except ProviderUnavailableError as exc:
                            return _provider_failure_to_response(exc)
                except Exception:
                    refs = []

            if not refs and selected_text:
                try:
                    refs = list(resolve_word(selected_text, oracle))
                except ProviderUnavailableError as exc:
                    return _provider_failure_to_response(exc)

            if not refs and selected_text:
                refs = [
                    Ref(
                        lemma=selected_text,
                        pos="UNKNOWN",
                        gender=None,
                        status="needs_gloss",
                    )
                ]

            candidates: list[dict[str, Any]] = []
            for r in refs:
                try:
                    cand = _materialize_candidate_from_ref(
                        r, provider, oracle, known_lemmas=known_lemmas
                    )
                except ProviderUnavailableError as exc:
                    return _provider_failure_to_response(exc)
                if cand is not None:
                    candidates.append(cand)

            provenance: dict[str, Any] = {
                "char_start": start,
                "char_end": end,
            }
            if lesson_id and isinstance(lesson_id, str) and lesson_id.strip():
                provenance["lesson_id"] = lesson_id.strip()

            capture_context: dict[str, Any] = {
                "sentence_text": sentence_text,
                "selected_span": {"start": start, "end": end},
                "lesson_label": lesson_label.strip(),
                "provenance": provenance,
            }

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "asset_token": token,
                    "candidates": _to_json_compatible(candidates),
                    "capture_context": capture_context,
                },
            )

    @app.post("/vocab/cards")
    async def capture_cards_endpoint(request: Request) -> JSONResponse:
        body = await request.json()

        picker_token = body.get("asset_token")
        if not picker_token or not isinstance(picker_token, str):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "asset_token is required"},
            )

        selections_raw = body.get("selections")
        if not isinstance(selections_raw, list) or len(selections_raw) == 0:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "selections must be a non-empty list"},
            )

        deck_input = body.get("deck")
        if not deck_input:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "deck target is required"},
            )
        if isinstance(deck_input, dict):
            deck_name = deck_input.get("name") or deck_input.get("lesson_label")
        elif isinstance(deck_input, str):
            deck_name = deck_input
        else:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "deck must be an object or string"},
            )
        if not deck_name or not isinstance(deck_name, str) or not deck_name.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "deck name is required and must not be blank"},
            )
        clean_deck_name = deck_name.strip()

        capture_context = body.get("capture_context")
        if capture_context is not None:
            if not isinstance(capture_context, dict):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "capture_context must be an object"},
                )
            sent_text = capture_context.get("sentence_text")
            span_raw = capture_context.get("selected_span")
            if span_raw is not None:
                if not isinstance(span_raw, dict):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "selected_span must be an object"},
                    )
                st = span_raw.get("start")
                en = span_raw.get("end")
                if (
                    st is None
                    or en is None
                    or isinstance(st, bool)
                    or isinstance(en, bool)
                    or not isinstance(st, int)
                    or not isinstance(en, int)
                ):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "selected_span start and end must be integers"},
                    )
                if sent_text is not None and isinstance(sent_text, str):
                    if not (0 <= st <= en <= len(sent_text)):
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "selected_span out of bounds"},
                        )

        with session.reading() as snapshot:
            active_token = session.asset_token()
            if picker_token != active_token:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "detail": "Asset token mismatch; dictionary has changed",
                        "picker_token": picker_token,
                        "active_token": active_token,
                    },
                )

            seen_identities: set[tuple[Any, ...]] = set()
            validated_selections: list[dict[str, Any]] = []

            for sel in selections_raw:
                if not isinstance(sel, dict):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "Each selection must be an object"},
                    )

                lem_ref = sel.get("ref") or sel.get("lemma_semantic_ref")
                if not lem_ref or not isinstance(lem_ref, str) or not lem_ref.strip():
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "ref / lemma_semantic_ref is required for selection"},
                    )
                clean_lem_ref = lem_ref.strip()
                if clean_lem_ref not in snapshot.lemma_ids:
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={
                            "detail": (
                                "Unknown lemma semantic reference in active dictionary: "
                                f"{clean_lem_ref}"
                            )
                        },
                    )
                expected_lem_id = snapshot.lemma_ids[clean_lem_ref]

                status_val = sel.get("status")
                sense_ref = sel.get("sense_semantic_ref") or sel.get("sense_ref")
                clean_sense_ref = (
                    sense_ref.strip()
                    if (sense_ref and isinstance(sense_ref, str) and sense_ref.strip())
                    else None
                )

                if clean_sense_ref is not None:
                    if clean_sense_ref not in snapshot.sense_ids:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": (
                                    "Unknown sense semantic reference in active dictionary: "
                                    f"{clean_sense_ref}"
                                )
                            },
                        )
                    _, actual_lem_id = snapshot.sense_ids[clean_sense_ref]
                    if actual_lem_id != expected_lem_id:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": (
                                    f"Sense {clean_sense_ref} does not belong to lemma "
                                    f"{clean_lem_ref}"
                                )
                            },
                        )
                    if status_val is None:
                        status_val = "resolved"

                comp_refs_raw = sel.get("component_refs") or sel.get("component_bindings")
                comp_bindings: list[tuple[str, str]] = []
                if comp_refs_raw is not None:
                    for item in comp_refs_raw:
                        if isinstance(item, (list, tuple)) and len(item) == 2:
                            c_l, c_s = str(item[0]).strip(), str(item[1]).strip()
                        elif (
                            isinstance(item, dict)
                            and "lemma_semantic_ref" in item
                            and "sense_semantic_ref" in item
                        ):
                            c_l = str(item["lemma_semantic_ref"]).strip()
                            c_s = str(item["sense_semantic_ref"]).strip()
                        elif (
                            isinstance(item, dict)
                            and "lemma_ref" in item
                            and "sense_ref" in item
                        ):
                            c_l = str(item["lemma_ref"]).strip()
                            c_s = str(item["sense_ref"]).strip()
                        else:
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={"detail": "Invalid component_refs format"},
                            )
                        if c_l not in snapshot.lemma_ids:
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={"detail": f"Unknown component lemma ref: {c_l}"},
                            )
                        if c_s not in snapshot.sense_ids:
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={"detail": f"Unknown component sense ref: {c_s}"},
                            )
                        c_exp_lid = snapshot.lemma_ids[c_l]
                        _, c_act_lid = snapshot.sense_ids[c_s]
                        if c_act_lid != c_exp_lid:
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={
                                    "detail": (
                                        f"Component sense {c_s} does not belong to "
                                        f"component lemma {c_l}"
                                    )
                                },
                            )
                        comp_bindings.append((c_l, c_s))
                    if status_val is None and comp_bindings:
                        status_val = "derived_compound"

                if status_val is None:
                    status_val = "resolved" if clean_sense_ref else "needs_gloss"

                if status_val == "derived_compound" and not comp_bindings:
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "derived compounds require component bindings"},
                    )
                if status_val == "resolved" and not clean_sense_ref:
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "resolved notes require a sense semantic reference"},
                    )

                # Identity for duplicate check
                if status_val == "resolved":
                    identity_key: tuple[Any, ...] = ("resolved", clean_sense_ref)
                elif status_val == "derived_compound":
                    identity_key = ("derived_compound", tuple(comp_bindings))
                else:
                    identity_key = ("needs_gloss", clean_lem_ref)

                if identity_key in seen_identities:
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={
                            "detail": (
                                f"Duplicate same-identity selection in request: {identity_key}"
                            )
                        },
                    )
                seen_identities.add(identity_key)

                # Validate overrides
                overrides = sel.get("overrides", {})
                if not isinstance(overrides, dict):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "overrides must be an object"},
                    )

                allowed_override_keys = {
                    "front_override",
                    "back_override",
                    "meaning_langs",
                    "user_meanings",
                }
                for k in overrides:
                    if k not in allowed_override_keys:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": f"Unknown override key: {k}"},
                        )

                front_ov = overrides.get("front_override")
                if front_ov is not None:
                    if not isinstance(front_ov, str) or not front_ov.strip():
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "front_override must be non-empty string or null"},
                        )

                back_ov = overrides.get("back_override")
                if back_ov is not None:
                    if not isinstance(back_ov, str) or not back_ov.strip():
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "back_override must be non-empty string or null"},
                        )

                raw_ml = overrides.get("meaning_langs")
                validated_ml: tuple[str, ...] | None = None
                if raw_ml is not None:
                    if not isinstance(raw_ml, (list, tuple)) or not raw_ml:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "meaning_langs must be a non-empty list"},
                        )
                    for lang_code in raw_ml:
                        if lang_code == "fa":
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={
                                    "detail": "Persian (fa) is deferred and unsupported in v1"
                                },
                            )
                        if lang_code not in ("de", "en"):
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={"detail": f"Unsupported meaning language: {lang_code}"},
                            )
                    if len(set(raw_ml)) != len(raw_ml):
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "Duplicate meaning languages"},
                        )
                    validated_ml = tuple(raw_ml)

                raw_um = overrides.get("user_meanings")
                validated_um: dict[str, str | None] | None = None
                if raw_um is not None:
                    if not isinstance(raw_um, dict) or not raw_um:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "user_meanings must be a non-empty object"},
                        )
                    validated_um = {}
                    for um_l, um_v in raw_um.items():
                        if um_l == "fa":
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={
                                    "detail": "Persian (fa) is deferred and unsupported in v1"
                                },
                            )
                        if um_l not in ("de", "en"):
                            return JSONResponse(
                                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                content={"detail": f"Unsupported user meaning language: {um_l}"},
                            )
                        if um_v is not None:
                            if not isinstance(um_v, str) or not um_v.strip():
                                return JSONResponse(
                                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    content={"detail": "user_meaning text must not be empty"},
                                )
                            validated_um[um_l] = um_v.strip()
                        else:
                            validated_um[um_l] = None

                validated_selections.append({
                    "lemma_semantic_ref": clean_lem_ref,
                    "sense_semantic_ref": clean_sense_ref,
                    "status": status_val,
                    "component_bindings": tuple(comp_bindings),
                    "meaning_langs": validated_ml,
                    "user_meanings": validated_um,
                    "front_override": front_ov.strip() if front_ov is not None else None,
                    "back_override": back_ov.strip() if back_ov is not None else None,
                    "identity_key": identity_key,
                })

            # All validations complete; execute atomic DB transaction
            conn = _get_user_db_conn(app)
            try:
                conn.execute("BEGIN IMMEDIATE")
                deck_row = conn.execute(
                    "SELECT id FROM deck WHERE name = ?", (clean_deck_name,)
                ).fetchone()
                if deck_row is not None:
                    deck_id = int(deck_row[0])
                else:
                    deck_id = create_deck(conn, clean_deck_name, _manage_transaction=False)

                result_notes: list[dict[str, Any]] = []
                for vsel in validated_selections:
                    st_val = vsel["status"]
                    l_ref = vsel["lemma_semantic_ref"]
                    s_ref = vsel["sense_semantic_ref"]
                    c_binds = vsel["component_bindings"]
                    m_langs = vsel["meaning_langs"]
                    u_means = vsel["user_meanings"]

                    existing_note_id: int | None = None
                    if st_val == "resolved" and s_ref is not None:
                        row = conn.execute(
                            "SELECT id FROM note WHERE status = 'resolved' "
                            "AND sense_semantic_ref = ?",
                            (s_ref,),
                        ).fetchone()
                        if row is not None:
                            existing_note_id = int(row[0])
                    elif st_val == "derived_compound" and c_binds:
                        c_count = len(c_binds)
                        candidate_notes = conn.execute(
                            """
                            SELECT note_id FROM note_dictionary_binding
                            WHERE role = 'component' AND component_count = ?
                            GROUP BY note_id HAVING COUNT(*) = ?
                            """,
                            (c_count, c_count),
                        ).fetchall()
                        for cn in candidate_notes:
                            nid_cand = int(cn[0])
                            b_rows = conn.execute(
                                """
                                SELECT component_ord, lemma_semantic_ref, sense_semantic_ref
                                FROM note_dictionary_binding
                                WHERE note_id = ? AND role = 'component'
                                ORDER BY component_ord ASC
                                """,
                                (nid_cand,),
                            ).fetchall()
                            if (
                                len(b_rows) == c_count
                                and tuple((str(r[1]), str(r[2])) for r in b_rows) == c_binds
                            ):
                                existing_note_id = nid_cand
                                break
                    elif st_val == "needs_gloss":
                        row = conn.execute(
                            "SELECT id FROM note WHERE status = 'needs_gloss' "
                            "AND lemma_semantic_ref = ?",
                            (l_ref,),
                        ).fetchone()
                        if row is not None:
                            existing_note_id = int(row[0])

                    if existing_note_id is not None:
                        note_id = existing_note_id
                        is_created = False
                        if m_langs is not None:
                            set_meaning_languages(
                                conn, note_id, m_langs, _manage_transaction=False
                            )
                        if u_means is not None:
                            for um_l, um_t in u_means.items():
                                if um_t is not None:
                                    set_user_meaning(
                                        conn, note_id, um_l, um_t, _manage_transaction=False
                                    )
                                else:
                                    delete_user_meaning(
                                        conn, note_id, um_l, _manage_transaction=False
                                    )
                    else:
                        is_created = True
                        initial_langs = m_langs if m_langs is not None else ("de", "en")
                        note_id = create_note(
                            conn,
                            lemma_semantic_ref=l_ref,
                            sense_semantic_ref=s_ref,
                            status=st_val,
                            component_bindings=c_binds,
                            meaning_languages=initial_langs,
                            _manage_transaction=False,
                        )
                        if u_means is not None:
                            for um_l, um_t in u_means.items():
                                if um_t is not None:
                                    set_user_meaning(
                                        conn, note_id, um_l, um_t, _manage_transaction=False
                                    )

                    add_note_to_deck(conn, note_id, deck_id, _manage_transaction=False)
                    result_notes.append({
                        "note_id": note_id,
                        "status": st_val,
                        "created": is_created,
                        "deck_id": deck_id,
                    })

                conn.commit()
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "notes": result_notes,
                        "deck_id": deck_id,
                    },
                )
            except Exception as exc:
                conn.rollback()
                if isinstance(exc, DeckError):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": str(exc)},
                    )
                raise
            finally:
                conn.close()

    @app.post("/vocab/import/csv")
    async def import_csv_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        csv_text = body.get("csv_text")
        if not csv_text or not isinstance(csv_text, str) or not csv_text.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "csv_text is required and must not be empty"},
            )

        deck_name = body.get("deck_name")
        if not deck_name or not isinstance(deck_name, str) or not deck_name.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "deck_name is required and must not be blank"},
            )
        clean_deck_name = deck_name.strip()

        raw_langs = body.get("meaning_languages") or body.get("meaning_langs")
        if raw_langs is not None:
            if not isinstance(raw_langs, (list, tuple)) or not raw_langs:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "meaning_languages must be non-empty list"},
                )
            for lang_code in raw_langs:
                if lang_code == "fa":
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "Persian (fa) is deferred and unsupported in v1"},
                    )
                if lang_code not in ("de", "en"):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": f"Unsupported meaning language: {lang_code}"},
                    )
            meaning_languages = tuple(raw_langs)
        else:
            meaning_languages = ("de", "en")

        lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
        if not lines:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "csv_text contains no valid lines"},
            )

        guard = _session_or_unconfigured(app)
        if isinstance(guard, JSONResponse):
            return guard
        with guard.reading():
            # Provider-backed oracle; the served-product read path no
            # longer opens the asset's raw SQLite connection.
            provider = guard.provider()
            oracle = _ProviderOracle(provider)

            conn = _get_user_db_conn(app)
            try:
                conn.execute("BEGIN IMMEDIATE")
                deck_row = conn.execute(
                    "SELECT id FROM deck WHERE name = ?", (clean_deck_name,)
                ).fetchone()
                if deck_row is not None:
                    deck_id = int(deck_row[0])
                else:
                    deck_id = create_deck(conn, clean_deck_name, _manage_transaction=False)

                created_count = 0
                reused_count = 0

                for word in lines:
                    try:
                        refs = list(resolve_word(word, oracle))
                    except ProviderUnavailableError as exc:
                        return _provider_failure_to_response(exc)
                    if refs:
                        top_ref = refs[0]
                    else:
                        top_ref = Ref(
                            lemma=word,
                            pos="UNKNOWN",
                            gender=None,
                            status="needs_gloss",
                        )

                    st_val = top_ref.status
                    try:
                        exact_lemmas = oracle.lookup_exact(top_ref.lemma, pos=top_ref.pos)
                    except ProviderUnavailableError as exc:
                        return _provider_failure_to_response(exc)
                    if exact_lemmas and exact_lemmas[0].semantic_ref:
                        clean_lem_ref = str(exact_lemmas[0].semantic_ref)
                    else:
                        clean_lem_ref = f"lemma:v1:{top_ref.lemma.lower()}_{top_ref.pos.lower()}"

                    clean_sense_ref = None
                    c_binds: tuple[tuple[str, str], ...] = ()

                    if st_val == "resolved":
                        try:
                            senses = oracle.lookup_senses(top_ref.lemma_id or 0)
                        except ProviderUnavailableError as exc:
                            return _provider_failure_to_response(exc)
                        if senses and senses[0].semantic_ref:
                            clean_sense_ref = str(senses[0].semantic_ref)
                        else:
                            st_val = "needs_gloss"
                    elif st_val == "derived_compound" and top_ref.component_bindings:
                        c_binds = tuple(
                            (cb.lemma_ref, cb.sense_ref)
                            for cb in top_ref.component_bindings
                        )

                    # Check existence
                    existing_id: int | None = None
                    if st_val == "resolved" and clean_sense_ref is not None:
                        row = conn.execute(
                            "SELECT id FROM note WHERE status = 'resolved' "
                            "AND sense_semantic_ref = ?",
                            (clean_sense_ref,),
                        ).fetchone()
                        if row is not None:
                            existing_id = int(row[0])
                    elif st_val == "needs_gloss":
                        row = conn.execute(
                            "SELECT id FROM note WHERE status = 'needs_gloss' "
                            "AND lemma_semantic_ref = ?",
                            (clean_lem_ref,),
                        ).fetchone()
                        if row is not None:
                            existing_id = int(row[0])

                    if existing_id is not None:
                        note_id = existing_id
                        reused_count += 1
                    else:
                        note_id = create_note(
                            conn,
                            lemma_semantic_ref=clean_lem_ref,
                            sense_semantic_ref=clean_sense_ref,
                            status=st_val,
                            component_bindings=c_binds,
                            meaning_languages=meaning_languages,
                            _manage_transaction=False,
                        )
                        created_count += 1

                    add_note_to_deck(conn, note_id, deck_id, _manage_transaction=False)

                conn.commit()
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "deck_id": deck_id,
                        "notes_created": created_count,
                        "notes_reused": reused_count,
                        "total_words": len(lines),
                    },
                )
            except Exception as exc:
                conn.rollback()
                if isinstance(exc, DeckError):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": str(exc)},
                    )
                raise
            finally:
                conn.close()

    @app.post("/vocab/notes")
    async def capture_note_endpoint(request: Request) -> JSONResponse:
        body = await request.json()

        # 1. Stale picker token validation (ADR-0004 D47)
        picker_token = body.get("asset_token")

        with session.reading() as snapshot:
            active_token = session.asset_token()
            if picker_token != active_token:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "detail": "Asset token mismatch; dictionary has changed",
                        "picker_token": picker_token,
                        "active_token": active_token,
                    },
                )

            # 2. Validate meaning languages
            raw_langs = (
                body.get("meaning_languages")
                or body.get("meaning_langs")
                or body.get("selected_languages")
            )
            if not raw_langs or not isinstance(raw_langs, (list, tuple)):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": "meaning_languages must be non-empty list from {'de', 'en'}"
                    },
                )

            for lang in raw_langs:
                if lang == "fa":
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "Persian (fa) is deferred and unsupported in v1"},
                    )
                if lang not in ("de", "en"):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={
                            "detail": (
                                f"Unsupported meaning language: {lang!r}; must be 'de' or 'en'"
                            )
                        },
                    )

            try:
                validated_langs = validate_selected_languages(raw_langs)
            except ValueError as exc:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": str(exc)},
                )

            lemma_ref = body.get("lemma_semantic_ref") or body.get("ref")
            if not lemma_ref or not isinstance(lemma_ref, str) or not lemma_ref.strip():
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "lemma_semantic_ref is required"},
                )
            clean_lemma_ref = lemma_ref.strip()

            # Active ref validation for lemma
            if clean_lemma_ref not in snapshot.lemma_ids:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": (
                            "Unknown lemma semantic reference in active dictionary: "
                            f"{clean_lemma_ref}"
                        )
                    },
                )

            sense_ref = body.get("sense_semantic_ref")
            clean_sense_ref = (
                sense_ref.strip()
                if sense_ref and isinstance(sense_ref, str)
                else None
            )

            status_val = body.get("status", "resolved")
            if status_val not in ("resolved", "needs_gloss", "derived_compound", "orphaned"):
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": f"Invalid status: {status_val}"},
                )

            if status_val == "resolved" and not clean_sense_ref:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "resolved notes require a sense semantic reference"},
                )

            # Active ref validation for sense
            if clean_sense_ref is not None:
                if clean_sense_ref not in snapshot.sense_ids:
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={
                            "detail": (
                                "Unknown sense semantic reference in active dictionary: "
                                f"{clean_sense_ref}"
                            )
                        },
                    )

            component_refs_raw = body.get("component_refs")
            component_refs: Sequence[tuple[str, str]] | None = None
            if component_refs_raw is not None:
                comp_list: list[tuple[str, str]] = []
                for item in component_refs_raw:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        comp_list.append((str(item[0]), str(item[1])))
                    elif (
                        isinstance(item, dict)
                        and "lemma_semantic_ref" in item
                        and "sense_semantic_ref" in item
                    ):
                        comp_list.append((
                            str(item["lemma_semantic_ref"]),
                            str(item["sense_semantic_ref"]),
                        ))
                    else:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "Invalid component_refs format"},
                        )
                component_refs = tuple(comp_list)

            if status_val == "derived_compound" and not component_refs:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "derived compounds require component bindings"},
                )

            # Active ref validation for component refs
            if component_refs is not None:
                for c_lem, c_sns in component_refs:
                    c_lem_clean = c_lem.strip()
                    c_sns_clean = c_sns.strip()
                    if not c_lem_clean or not c_sns_clean:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": "component bindings require non-blank semantic references"
                            },
                        )
                    if c_lem_clean not in snapshot.lemma_ids:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": (
                                    "Unknown component lemma semantic reference in active "
                                    f"dictionary: {c_lem_clean}"
                                )
                            },
                        )
                    if c_sns_clean not in snapshot.sense_ids:
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={
                                "detail": (
                                    "Unknown component sense semantic reference in active "
                                    f"dictionary: {c_sns_clean}"
                                )
                            },
                        )

            user_meanings_input = body.get("user_meanings")
            if user_meanings_input is not None:
                if not isinstance(user_meanings_input, dict):
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "user_meanings must be an object"},
                    )
                for um_lang, um_text in user_meanings_input.items():
                    if um_lang == "fa":
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "Persian (fa) is deferred and unsupported in v1"},
                        )
                    if um_lang not in ("de", "en"):
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": f"Unsupported user meaning language: {um_lang}"},
                        )
                    if not isinstance(um_text, str) or not um_text.strip():
                        return JSONResponse(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            content={"detail": "user_meaning text must not be empty"},
                        )

            conn = _get_user_db_conn(app)
            try:
                conn.execute("BEGIN IMMEDIATE")
                deck_name = body.get("deck_name") or body.get("lesson_label")
                deck_id: int | None = None
                if deck_name and isinstance(deck_name, str) and deck_name.strip():
                    clean_deck_name = deck_name.strip()
                    row = conn.execute(
                        "SELECT id FROM deck WHERE name = ?", (clean_deck_name,)
                    ).fetchone()
                    if row is not None:
                        deck_id = int(row[0])
                    else:
                        deck_id = create_deck(conn, clean_deck_name, _manage_transaction=False)

                note_id = create_note(
                    conn,
                    lemma_semantic_ref=clean_lemma_ref,
                    sense_semantic_ref=clean_sense_ref,
                    status=status_val,
                    component_bindings=component_refs or (),
                    meaning_languages=validated_langs,
                    _manage_transaction=False,
                )

                if deck_id is not None:
                    add_note_to_deck(conn, note_id, deck_id, _manage_transaction=False)

                if user_meanings_input:
                    for um_lang, um_text in user_meanings_input.items():
                        set_user_meaning(
                            conn, note_id, um_lang, um_text.strip(), _manage_transaction=False
                        )

                conn.commit()
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "note_id": note_id,
                        "status": status_val,
                        "meaning_languages": list(validated_langs),
                        "deck_id": deck_id,
                    },
                )
            except DeckError as exc:
                conn.rollback()
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": str(exc)},
                )
            finally:
                conn.close()

    @app.get("/vocab/cards/next")
    def next_card_endpoint(deck_id: int | None = None) -> JSONResponse:
        guard = _runtime_or_unconfigured(app, runtime)
        if isinstance(guard, JSONResponse):
            return guard
        card_obs = guard.observe_card_render(deck_id=deck_id)
        if card_obs is None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"card": None},
            )

        render_input = _render_input_from_observation(card_obs, with_audio=True)
        rendered = render_card(render_input)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "card": {
                    "card_id": cast(int, card_obs["card_id"]),
                    "note_id": cast(int, card_obs["note_id"]),
                    "due_at": str(card_obs["due_at"]),
                    "state": cast(int, card_obs["state"]),
                    "front": {
                        "headword": rendered.front.headword,
                        "display_headword": rendered.front.display_headword,
                        "pos": rendered.front.pos,
                        "gender": rendered.front.gender,
                        "article": rendered.front.article,
                        "ipa": rendered.front.ipa,
                        "text": rendered.front.text,
                        "audio_trigger": {
                            "available": rendered.front.audio_trigger.available,
                            "lemma": rendered.front.audio_trigger.lemma,
                            "token": rendered.front.audio_trigger.token,
                        },
                    },
                    "back": {
                        "display_headword": rendered.back.display_headword,
                        "pos": rendered.back.pos,
                        "gender": rendered.back.gender,
                        "article": rendered.back.article,
                        "ipa": rendered.back.ipa,
                        "plural": rendered.back.plural,
                        "text": rendered.back.text,
                        "grammar": {
                            "pos": rendered.back.grammar.pos,
                            "lines": list(rendered.back.grammar.lines),
                        },
                        "meanings": [
                            {
                                "language": mb.language,
                                "origin": mb.origin,
                                "is_user_authored": mb.is_user_authored,
                                "heading": mb.heading,
                                "lines": list(mb.lines),
                            }
                            for mb in rendered.back.meanings
                        ],
                        "examples": [
                            {
                                "de": ex.de,
                                "en": ex.en,
                                "lines": list(ex.lines),
                            }
                            for ex in rendered.back.examples
                        ],
                    },
                }
            },
        )

    @app.post("/vocab/cards/{card_id}/review")
    async def review_card_endpoint(card_id: int, request: Request) -> JSONResponse:
        body = await request.json()

        # Reject client-supplied rating field with 422
        if "rating" in body:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Client-supplied rating is forbidden; submit confidence 1..5 only"
                },
            )

        if (
            "confidence" not in body
            or not isinstance(body["confidence"], int)
            or isinstance(body["confidence"], bool)
        ):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "confidence must be an integer between 1 and 5"},
            )

        conf = body["confidence"]
        if conf < 1 or conf > 5:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "confidence must be an integer between 1 and 5"},
            )

        conn = _get_user_db_conn(app)
        try:
            card_row = conn.execute(
                "SELECT id FROM card WHERE id = ?", (card_id,)
            ).fetchone()
            if card_row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Card {card_id} not found"},
                )

            res = review(conn, card_id, conf)
            state_val = (
                res.state.value
                if hasattr(res.state, "value")
                else int(res.state)
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "card_id": res.card_id,
                    "confidence": res.confidence,
                    "rating": res.rating,
                    "due_at": res.due_at.isoformat(),
                    "interval_days": res.interval_days,
                    "state": state_val,
                },
            )
        except DeckError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        finally:
            conn.close()

    @app.post("/vocab/notes/{note_id}/gloss")
    async def set_gloss_endpoint(note_id: int, request: Request) -> JSONResponse:
        body = await request.json()
        lang = body.get("language") or body.get("lang")
        if not lang or not isinstance(lang, str):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "language is required"},
            )

        if lang == "fa":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Persian (fa) is deferred and unsupported in v1"},
            )

        if lang not in ("de", "en"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": f"Unsupported language: {lang!r}; must be 'de' or 'en'"},
            )

        text = body.get("meaning_text") or body.get("text")
        if not text or not isinstance(text, str) or not text.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "meaning_text must not be empty"},
            )

        conn = _get_user_db_conn(app)
        try:
            note_row = conn.execute(
                "SELECT id FROM note WHERE id = ?", (note_id,)
            ).fetchone()
            if note_row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Note {note_id} not found"},
                )

            set_user_meaning(conn, note_id, lang, text.strip())
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "note_id": note_id,
                    "language": lang,
                    "meaning_text": text.strip(),
                },
            )
        except DeckError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        finally:
            conn.close()

    @app.delete("/vocab/notes/{note_id}/gloss")
    def delete_gloss_endpoint(note_id: int, language: str = Query(...)) -> JSONResponse:
        if language == "fa":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Persian (fa) is deferred and unsupported in v1"},
            )

        if language not in ("de", "en"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": f"Unsupported language: {language!r}; must be 'de' or 'en'"},
            )

        conn = _get_user_db_conn(app)
        try:
            note_row = conn.execute(
                "SELECT id FROM note WHERE id = ?", (note_id,)
            ).fetchone()
            if note_row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Note {note_id} not found"},
                )

            delete_user_meaning(conn, note_id, language)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"note_id": note_id, "language": language, "deleted": True},
            )
        except DeckError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        finally:
            conn.close()

    @app.post("/vocab/notes/{note_id}/audio")
    async def upload_audio_endpoint(note_id: int, request: Request) -> JSONResponse:
        conn = _get_user_db_conn(app)
        try:
            note_row = conn.execute(
                "SELECT id FROM note WHERE id = ?", (note_id,)
            ).fetchone()
            if note_row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Note {note_id} not found"},
                )

            content_type = request.headers.get("content-type", "")
            raw_bytes: bytes

            if "multipart/form-data" in content_type:
                form = await request.form()
                file_obj = form.get("file") or form.get("audio")
                if file_obj is None or isinstance(file_obj, str) or not hasattr(file_obj, "read"):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Missing file field in form upload"},
                    )
                raw_bytes = await file_obj.read()
            else:
                raw_bytes = await request.body()

            if not raw_bytes:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Empty audio payload"},
                )

            try:
                rec = save_custom_pronunciation(
                    conn,
                    note_id,
                    raw_bytes,
                    app.state.media_dir,
                    source_type="uploaded",
                )
                return JSONResponse(
                    status_code=status.HTTP_201_CREATED,
                    content={
                        "note_id": rec.note_id,
                        "media_filename": rec.media_filename,
                        "sha256": rec.sha256,
                        "byte_size": rec.byte_size,
                        "format": rec.format,
                        "source_type": rec.source_type,
                    },
                )
            except MediaValidationError as exc:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": f"Audio validation failed: {exc}"},
                )
            except CustomAudioError as exc:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": f"Custom audio error: {exc}"},
                )
        finally:
            conn.close()

    @app.delete("/vocab/notes/{note_id}/audio")
    def revert_audio_endpoint(note_id: int) -> JSONResponse:
        conn = _get_user_db_conn(app)
        try:
            note_row = conn.execute(
                "SELECT id FROM note WHERE id = ?", (note_id,)
            ).fetchone()
            if note_row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Note {note_id} not found"},
                )

            revert_custom_pronunciation(conn, note_id, app.state.media_dir)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"note_id": note_id, "reverted": True},
            )
        finally:
            conn.close()

    @app.get("/vocab/audio/{audio_id}")
    def get_audio_endpoint(audio_id: str) -> Response:
        clean_id = audio_id.strip()
        media_directory = Path(app.state.media_dir)
        cache_directory = Path(app.state.cache_dir)

        # 1. Direct filename or custom note ID check
        if clean_id.isdigit():
            conn = _get_user_db_conn(app)
            try:
                rec = get_custom_pronunciation(conn, int(clean_id))
                if rec is not None:
                    target = media_directory / rec.media_filename
                    if target.is_file():
                        raw_bytes = target.read_bytes()
                        validated = validate_audio_bytes(
                            raw_bytes, declared_format=rec.format
                        )
                        return Response(
                            content=raw_bytes, media_type=validated.mime_type
                        )
            finally:
                conn.close()

        # 2. Check media_dir directly
        candidate_media = media_directory / clean_id
        if candidate_media.is_file():
            raw_bytes = candidate_media.read_bytes()
            validated = validate_audio_bytes(raw_bytes)
            return Response(content=raw_bytes, media_type=validated.mime_type)

        # 3. Check cache_dir directly
        candidate_cache = cache_directory / clean_id
        if candidate_cache.is_file():
            raw_bytes = candidate_cache.read_bytes()
            validated = validate_audio_bytes(raw_bytes)
            return Response(content=raw_bytes, media_type=validated.mime_type)

        # 4. Resolve via domain precedence (e.g. lemma text)
        conn = _get_user_db_conn(app)
        try:
            res = select_pronunciation_audio(
                lemma=clean_id,
                user_db=conn,
                media_dir=app.state.media_dir,
                cache_dir=app.state.cache_dir,
                tts_remote_url=app.state.tts_remote_url,
            )
            if res.audio_bytes is not None and res.mime_type is not None:
                return Response(content=res.audio_bytes, media_type=res.mime_type)
        finally:
            conn.close()

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Audio for {clean_id!r} not found"},
        )

    @app.post("/vocab/dictionary/activate")
    async def activate_dictionary_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        path_val = body.get("path") or body.get("filename")
        if not path_val or not isinstance(path_val, str) or not path_val.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Candidate dictionary path or filename is required"},
            )

        version = body.get("version", "v1")
        if not isinstance(version, str) or not version.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "version must be a non-blank string"},
            )

        guard = _runtime_or_unconfigured(app, runtime)
        if isinstance(guard, JSONResponse):
            return guard
        try:
            guard.activate_dictionary(path_val.strip(), version=version.strip())
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "activated",
                    "version": version.strip(),
                    "asset_token": guard.asset_token,
                },
            )
        except DictionaryClosedError as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": str(exc)},
            )
        except (
            DictionaryAssetError,
            DictionaryRuntimeError,
            DeckError,
            ValueError,
            TypeError,
        ) as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error during dictionary activation"},
            )

    @app.get("/vocab/decks")
    def get_decks_endpoint() -> JSONResponse:
        conn = _get_user_db_conn(app)
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            rows = conn.execute(
                """
                SELECT d.id, d.name, d.created_at,
                       COUNT(c.id) AS card_count,
                       SUM(CASE WHEN c.due_at <= ? THEN 1 ELSE 0 END) AS due_count,
                       SUM(COALESCE(n.last_confidence, 0)) AS sum_confidence
                FROM deck d
                LEFT JOIN note_deck nd ON nd.deck_id = d.id
                LEFT JOIN note n ON n.id = nd.note_id
                LEFT JOIN card c ON c.note_id = n.id
                GROUP BY d.id, d.name, d.created_at
                ORDER BY d.id ASC
                """,
                (now_iso,),
            ).fetchall()

            decks_list: list[dict[str, Any]] = []
            for r in rows:
                card_cnt = int(r["card_count"] or 0)
                due_cnt = int(r["due_count"] or 0)
                sum_conf = float(r["sum_confidence"] or 0)
                # D30 mastery percent formula: 100 * SUM(confidence) / (5 * COUNT(cards))
                mastery = (100.0 * sum_conf / (5.0 * card_cnt)) if card_cnt > 0 else 0.0
                decks_list.append({
                    "id": int(r["id"]),
                    "name": str(r["name"]),
                    "created_at": str(r["created_at"]),
                    "card_count": card_cnt,
                    "due_count": due_cnt,
                    "mastery_percent": round(mastery, 2),
                })

            return JSONResponse(status_code=status.HTTP_200_OK, content=decks_list)
        finally:
            conn.close()

    @app.post("/vocab/decks")
    async def create_deck_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        name = body.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Deck name is required and must not be blank"},
            )

        conn = _get_user_db_conn(app)
        try:
            deck_id = create_deck(conn, name.strip())
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={"id": deck_id, "name": name.strip()},
            )
        except (DeckError, sqlite3.IntegrityError) as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": str(exc)},
            )
        finally:
            conn.close()

    @app.delete("/vocab/decks/{deck_id}")
    def delete_deck_endpoint(deck_id: int) -> JSONResponse:
        conn = _get_user_db_conn(app)
        try:
            row = conn.execute(
                "SELECT id FROM deck WHERE id = ?", (deck_id,)
            ).fetchone()
            if row is None:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": f"Deck {deck_id} not found"},
                )

            delete_deck(conn, deck_id)
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"id": deck_id, "deleted": True},
            )
        finally:
            conn.close()

    @app.get("/vocab/export/anki")
    def export_anki_endpoint(deck_id: int | None = None) -> Response:
        guard = _runtime_or_unconfigured(app, runtime)
        if isinstance(guard, JSONResponse):
            return guard
        cards_obs = guard.observe_export_payload(deck_id=deck_id)

        tsv_lines: list[str] = [
            "#separator:tab",
            "#html:true",
            "#notetype:German Vocabulary",
            "#columns:Front\tBack\tGrammar\tExample\tIPA\tTags",
        ]

        def _sanitize(text: str | None) -> str:
            if not text:
                return ""
            s = text.replace("\t", " ")
            s = re.sub(r"\r\n|\r|\n", "<br>", s)
            return s

        for card_obs in cards_obs:
            note_status = str(card_obs["note_status"])
            deck_names_str = str(card_obs["deck_names"]) if card_obs.get("deck_names") else ""
            render_input = _render_input_from_observation(card_obs, with_audio=False)
            rendered = render_card(render_input)

            front_text = _sanitize(rendered.front.text)
            if note_status == "needs_gloss" or not rendered.back.meanings:
                back_text = ""
            else:
                back_sections: list[str] = []
                for mb in rendered.back.meanings:
                    if mb.lines:
                        lines_formatted = [
                            f"• {line}" if len(mb.lines) > 1 else line
                            for line in mb.lines
                        ]
                        back_sections.append(
                            f"{mb.heading}\n" + "\n".join(lines_formatted)
                        )
                back_text = _sanitize("\n\n".join(back_sections))

            grammar_text = _sanitize("\n".join(rendered.back.grammar.lines))
            ex_lines: list[str] = []
            for ex in rendered.back.examples:
                ex_lines.append(ex.de)
                if ex.en:
                    ex_lines.append(f"  {ex.en}")
            example_text = _sanitize("\n".join(ex_lines))
            ipa_text = _sanitize(rendered.front.ipa or "")

            tag_list: list[str] = []
            if deck_names_str:
                for dname in deck_names_str.split(","):
                    clean_d = dname.strip().replace(" ", "_")
                    if clean_d:
                        tag_list.append(clean_d)
            if note_status == "needs_gloss":
                tag_list.append("needs_gloss")
            if note_status == "orphaned":
                tag_list.append("orphaned")
            tags_text = _sanitize(" ".join(tag_list))

            tsv_lines.append(
                f"{front_text}\t{back_text}\t{grammar_text}\t"
                f"{example_text}\t{ipa_text}\t{tags_text}"
            )

        tsv_body = "\n".join(tsv_lines) + "\n"
        return Response(
            content=tsv_body,
            media_type="text/tab-separated-values; charset=utf-8",
        )

    @app.get("/vocab/export/apkg")
    def export_apkg_endpoint(deck_id: int = Query(..., ge=1)) -> Response:
        """Export one existing deck as a real Anki package without app writes."""
        conn = _get_user_db_conn(app)
        try:
            deck_row = conn.execute(
                "SELECT name FROM deck WHERE id = ?", (deck_id,)
            ).fetchone()
        finally:
            conn.close()
        if deck_row is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": f"Deck {deck_id} not found"},
            )

        deck_name = str(deck_row["name"])
        guard = _runtime_or_unconfigured(app, runtime)
        if isinstance(guard, JSONResponse):
            return guard
        observations = guard.observe_export_payload(deck_id=deck_id)
        package_bytes = build_apkg(
            observations,
            deck_name=deck_name,
            render_input_for_observation=_render_input_from_observation,
            audio_for_observation=lambda observation: _export_audio_for_observation(
                app, observation
            ),
        )
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", deck_name).strip(".-") or "flashcards"
        return Response(
            content=package_bytes,
            media_type="application/apkg",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.apkg"'},
        )

    @app.get("/vocab/settings/dictionary")
    def settings_dictionary_get() -> JSONResponse:
        """Return the chooser/runtime status for the Settings UI."""
        mode = str(getattr(app.state, "dictionary_mode", "unconfigured"))
        managed = Path(app.state.managed_dictionary_dir)
        manifest_filename = str(getattr(app.state, "manifest_filename", "dictionary.sqlite"))
        canonical = managed / manifest_filename
        present = canonical.is_file()
        valid = False
        if present:
            try:
                asset = validate_candidate_dictionary(canonical)
                try:
                    valid = (
                        asset.path.name == manifest_filename
                        and asset.sha256.lower()
                        == str(
                            getattr(app.state, "expected_dictionary_sha256", "")
                            or asset.sha256
                        ).lower()
                    )
                finally:
                    try:
                        asset.close()
                    except Exception:
                        pass
            except Exception:
                valid = False
        info = getattr(app.state, "online_session_info", None)
        online_active = mode == "online" or info is not None
        from app.dictionary_mode import DictionaryModeName

        valid_mode: DictionaryModeName = (
            "offline" if mode == "offline" else "online" if mode == "online" else "unconfigured"
        )
        status_payload = session_status(
            mode=valid_mode,
            canonical_offline_path=canonical,
            canonical_offline_present=present,
            canonical_offline_valid=valid,
            online_active=online_active,
        )
        if info is not None:
            status_payload["online_info"] = {
                "dataset_token": info.dataset_token,
                "asset_token": info.asset_token,
                "cache_dir": info.cache_dir,
            }
        return JSONResponse(status_code=200, content=status_payload)

    @app.post("/vocab/settings/dictionary/install-offline")
    async def settings_install_offline(request: Request) -> JSONResponse:
        """Run the hardened full Offline installer.

        The chooser/Online-active flows use this endpoint to populate
        the managed canonical slot. The preflight is enforced before
        any download begins: insufficient free space is rejected
        immediately, no existing valid Offline dictionary is replaced,
        and no user data is mutated.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        manifest_bytes_raw = body.get("manifest_bytes")
        manifest_bytes: int | None
        if (
            isinstance(manifest_bytes_raw, int)
            and not isinstance(manifest_bytes_raw, bool)
            and manifest_bytes_raw > 0
        ):
            manifest_bytes = int(manifest_bytes_raw)
        else:
            manifest_bytes = OFFLINE_INSTALL_DEFAULT_MANIFEST_BYTES

        managed = Path(app.state.managed_dictionary_dir)
        install_path = managed / str(app.state.manifest_filename)
        # Refuse early when the canonical file is already a valid asset.
        # The installer's contract refuses to overwrite a validated file;
        # this matches AGENTS R9 / ADR-0001 §12.
        if install_path.is_file():
            try:
                asset = validate_candidate_dictionary(install_path)
                try:
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "already_present",
                            "canonical_offline_path": str(install_path),
                            "sha256": asset.sha256,
                            "byte_size": install_path.stat().st_size,
                        },
                    )
                finally:
                    try:
                        asset.close()
                    except Exception:
                        pass
            except Exception:
                # existing file is unusable; fall through to a fresh install
                pass

        try:
            peak = preflight_offline_install(
                manifest_bytes=manifest_bytes, install_dir=managed
            )
        except OfflineInstallRefused as exc:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": str(exc),
                    "code": exc.code,
                    "available_bytes": exc.available_bytes,
                    "required_bytes": exc.required_bytes,
                },
            )

        try:
            from app.dict_install import (  # noqa: PLC0415  # noqa: PLC0415
                DictionaryInstallerError,
                DictionaryManifest,
                install_dictionary,
                parse_manifest_payload,
            )

            manifest_payload = {
                "version": "v2",
                "filename": str(app.state.manifest_filename),
                "sha256": str(app.state.expected_dictionary_sha256 or ""),
                "bytes": int(manifest_bytes),
                "classification": "settings-pull",
                "attribution": "ATTRIBUTION-v2.md",
                "download_url": body.get("download_url"),
            }
            manifest = parse_manifest_payload(
                manifest_payload, manifest_path=managed / "manifest.json"
            )
            assert isinstance(manifest, DictionaryManifest)
            install_dictionary(manifest, target_dir=managed)
        except DictionaryInstallerError as exc:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": str(exc),
                    "code": "offline_install_failed",
                },
            )
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"install failed: {exc}",
                    "code": "offline_install_exception",
                },
            )

        # Successful install — record the canonical path/identity on app state.
        try:
            asset = validate_candidate_dictionary(install_path)
            try:
                app.state.dict_path = install_path
                app.state.expected_dictionary_sha256 = asset.sha256
            finally:
                try:
                    asset.close()
                except Exception:
                    pass
        except Exception:
            pass

        return JSONResponse(
            status_code=200,
            content={
                "status": "installed",
                "canonical_offline_path": str(install_path),
                "measured_bytes": peak.measured_bytes,
                "safety_threshold_bytes": peak.safety_threshold_bytes,
            },
        )

    @app.post("/vocab/settings/dictionary/remove-offline")
    async def settings_remove_offline(request: Request) -> JSONResponse:
        """Remove the managed canonical full Offline dictionary.

        The contract is:

        * Offline ACTIVE: refused with a structured, actionable conflict
          (``offline_dictionary_in_use``). Canonical file remains;
          ``active_dictionary_metadata`` unchanged; zero user-data
          mutation.
        * Online ACTIVE: the canonical file is removed after verifying
          it is the managed canonical asset; the Online cache and the
          ``active_dictionary_metadata`` row stay untouched; zero
          user-data mutation.

        Across both branches, user data (notes, cards, ``review_log``,
        user/audio/sense refs) never changes.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        mode = str(getattr(app.state, "dictionary_mode", ""))
        if mode != "online":
            # Per ADR-0009, Offline-active removal is rejected with a
            # structured conflict. The user is told to switch to Online
            # for this session first.
            return JSONResponse(
                status_code=409,
                content={
                    "detail": (
                        "offline_dictionary_in_use: switch the session to "
                        "Online for this session before removing the "
                        "canonical Offline dictionary."
                    ),
                    "code": "offline_dictionary_in_use",
                    "current_mode": mode,
                },
            )

        managed = Path(app.state.managed_dictionary_dir)
        target_filename = str(
            body.get("filename") or app.state.manifest_filename
        )
        expected_sha = (
            str(app.state.expected_dictionary_sha256)
            if app.state.expected_dictionary_sha256
            else None
        )
        expected_bytes = (
            int(app.state.expected_dictionary_bytes)
            if getattr(app.state, "expected_dictionary_bytes", None)
            else None
        )
        removed, detail = remove_canonical_offline(
            managed_dir=managed,
            target_filename=target_filename,
            expected_sha256=expected_sha,
            expected_bytes=expected_bytes,
        )
        if not removed:
            return JSONResponse(
                status_code=409,
                content={"detail": detail, "code": "offline_removal_failed"},
            )
        app.state.dict_path = None
        app.state.expected_dictionary_sha256 = None
        return JSONResponse(
            status_code=200,
            content={
                "status": "removed",
                "detail": detail,
                "canonical_offline_path": str(managed / target_filename),
            },
        )

    @app.post("/vocab/settings/dictionary/clear-online-cache")
    def settings_clear_online_cache() -> JSONResponse:
        """Clear the Online provider's immutable shard cache directory.

        The Online provider must already be bound, and this only removes
        Online shard artifacts — user data, the dictionary asset path,
        and ``active_dictionary_metadata`` are untouched.
        """
        info = getattr(app.state, "online_session_info", None)
        cache_dir = Path(info.cache_dir) if info is not None else None
        if cache_dir is None or not cache_dir.exists():
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "online cache is not configured",
                    "code": "online_cache_not_configured",
                },
            )
        removed_count = 0
        for entry in cache_dir.iterdir():
            try:
                if entry.is_dir():
                    import shutil

                    shutil.rmtree(entry)
                else:
                    entry.unlink()
                removed_count += 1
            except OSError:
                pass
        return JSONResponse(
            status_code=200,
            content={"status": "cleared", "removed_count": int(removed_count)},
        )

    @app.post("/vocab/settings/dictionary/use-online")
    async def settings_use_online(request: Request) -> JSONResponse:
        """Switch the session provider to Online for this process.

        Reuses the ``online_provider_factory`` set on ``app.state``. The
        canonical Offline dictionary file is preserved; only the
        dictionary source for the running session changes. The
        ``active_dictionary_metadata`` row and all user data remain
        intact.
        """
        factory = getattr(app.state, "online_provider_factory", None)
        if factory is None:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "online_provider_factory is not configured on this server",
                    "code": "online_provider_unavailable",
                },
            )
        try:
            provider, info = factory()
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=409,
                content={
                    "detail": f"online factory failed: {exc}",
                    "code": "online_factory_failed",
                },
            )

        # Tear down the previous runtime, if any.
        previous_runtime = getattr(app.state, "runtime", None)
        if previous_runtime is not None and not previous_runtime.is_closed:
            try:
                previous_runtime.close()
            except Exception:
                pass

        previous_session = getattr(app.state, "session", None)
        if previous_session is not None:
            try:
                previous_session.close()
            except Exception:
                pass

        new_session = DictionarySession(provider=provider, online_info=info)
        app.state.session = new_session
        app.state.online_provider = provider
        app.state.online_session_info = info
        app.state.dictionary_mode = "online"
        app.state.runtime = None
        return JSONResponse(
            status_code=200,
            content={
                "status": "online",
                "online_info": {
                    "dataset_token": info.dataset_token,
                    "asset_token": info.asset_token,
                    "cache_dir": info.cache_dir,
                },
            },
        )

    @app.post("/vocab/settings/dictionary/use-offline")
    async def settings_use_offline(request: Request) -> JSONResponse:
        """Switch the session provider to Offline for this process.

        Requires a verified canonical full Offline dictionary at the
        managed path. Refuses with a structured actionable conflict when
        no valid asset is present (the user must ``install-offline``
        first).
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        managed = Path(app.state.managed_dictionary_dir)
        install_path = managed / str(app.state.manifest_filename)
        if not install_path.is_file():
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "no canonical full Offline dictionary available; install first",
                    "code": "offline_unavailable",
                    "canonical_offline_path": str(install_path),
                },
            )
        # Validate the asset before swapping the session.
        try:
            asset = validate_candidate_dictionary(install_path)
        except Exception as exc:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": f"offline dictionary is not valid: {exc}",
                    "code": "offline_unavailable",
                },
            )
        asset_sha = str(asset.sha256)
        try:
            new_runtime = DictionaryRuntime(
                install_path,
                Path(app.state.user_db_path),
                expected_sha256=asset_sha,
                expected_version=str(app.state.expected_dictionary_version),
            )
        except Exception as exc:
            try:
                asset.close()
            except Exception:
                pass
            return JSONResponse(
                status_code=409,
                content={
                    "detail": f"could not activate offline dictionary: {exc}",
                    "code": "offline_activation_failed",
                },
            )
        try:
            asset.close()
        except Exception:
            pass

        previous_session = getattr(app.state, "session", None)
        if previous_session is not None:
            try:
                previous_session.close()
            except Exception:
                pass
        previous_online_provider = getattr(app.state, "online_provider", None)
        if previous_online_provider is not None:
            try:
                previous_online_provider.close()
            except Exception:
                pass

        new_session = DictionarySession(runtime=new_runtime)
        app.state.session = new_session
        app.state.runtime = new_runtime
        app.state.dictionary_mode = "offline"
        app.state.online_provider = None
        app.state.online_session_info = None
        app.state.dict_path = install_path
        app.state.expected_dictionary_sha256 = asset_sha
        return JSONResponse(
            status_code=200,
            content={
                "status": "offline",
                "asset_token": new_runtime.asset_token,
                "canonical_offline_path": str(install_path),
            },
        )

    frontend_dir = Path(__file__).with_name("frontend")

    @app.get("/")
    @app.get("/{frontend_path:path}")
    def frontend_endpoint(frontend_path: str = "") -> Response:
        """Serve the generated Vite application after every concrete API route."""
        candidate = (frontend_dir / frontend_path).resolve()
        try:
            candidate.relative_to(frontend_dir.resolve())
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not found"}
            )
        if candidate.is_file():
            return FileResponse(candidate)
        index = frontend_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not found"})

    return app


def create_production_app() -> FastAPI:
    """Container entry point with separate disposable and persistent mounts."""
    return create_app(
        dict_path="/dictionary/dictionary.sqlite",
        user_db_path="/data/flashcards.sqlite",
        cors_origins=("http://127.0.0.1:8000", "http://localhost:8000"),
        service_port=8000,
    )
