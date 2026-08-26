"""Standalone HTTP application, API endpoints, and browser loopback security guards.

Implements ADR-0001, ADR-0002 §4.1 / D24 / D25, ADR-0003, ADR-0004, ADR-0005,
ADR-0007 D80, and AGENTS rules R4, R5, R6, R9, R10, R12, R13, C1, C2.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, cast

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.audio import (
    CustomAudioError,
    MediaValidationError,
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
    create_deck,
    create_note,
    delete_deck,
    delete_user_meaning,
    review,
    set_user_meaning,
)
from app.dictionary import DictionaryAssetError
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

LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({
    "127.0.0.1",
    "localhost",
    "[::1]",
    "::1",
})


def _is_loopback_host(host_header: str | None) -> bool:
    """Validate that Host header is a loopback endpoint (127.0.0.1, localhost, [::1])."""
    if not host_header:
        return False
    host = host_header.strip()
    if host.startswith("["):
        bracket_end = host.find("]")
        if bracket_end != -1:
            ipv6 = host[: bracket_end + 1].lower()
            return ipv6 == "[::1]"
    # Strip port if present
    base_host = host.split(":")[0].lower()
    return base_host in ("127.0.0.1", "localhost")


class BrowserSecurityMiddleware(BaseHTTPMiddleware):
    """ASGI middleware enforcing AGENTS R12 and ADR-0002 §4.1 browser trust boundary."""

    def __init__(
        self,
        app: ASGIApp,
        cors_origins: set[str],
    ) -> None:
        super().__init__(app)
        self.cors_origins = cors_origins

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Host header validation
        host = request.headers.get("host")
        if not _is_loopback_host(host):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Host header must be loopback (127.0.0.1, localhost, [::1])"
                },
            )

        # 2. Origin header validation (when present)
        origin = request.headers.get("origin")
        if origin is not None and origin.strip():
            norm_origin = origin.strip()
            if norm_origin not in self.cors_origins:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": f"Forbidden origin: {origin}"},
                )

        # Handle CORS preflight OPTIONS request
        if request.method == "OPTIONS":
            response = Response(status_code=status.HTTP_200_OK)
            if origin is not None and origin.strip() in self.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin.strip()
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
                if not content_type.lower().startswith("application/json"):
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Content-Type must be application/json"},
                    )

        response = await call_next(request)

        # Set CORS headers on response if origin is valid
        if origin is not None and origin.strip() in self.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin.strip()
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


def create_app(
    dict_path: Path | str,
    user_db_path: Path | str,
    cors_origins: Sequence[str] | set[str],
    *,
    tts_remote_url: str | None = None,
    media_dir: Path | str | None = None,
    cache_dir: Path | str | None = None,
) -> FastAPI:
    """Create and configure the standalone FastAPI vocabulary application.

    Zero module-level state; no environment reads at import time (AGENTS C1).
    """
    if not isinstance(cors_origins, (list, tuple, set, frozenset)):
        raise TypeError("cors_origins must be a sequence or set of origin strings")

    for orig in cors_origins:
        if not isinstance(orig, str):
            raise TypeError("cors_origins entries must be strings")
        if "*" in orig:
            raise ValueError(f"Wildcard origin is forbidden: {orig!r}")

    cors_origins_set = set(cors_origins)

    dict_p = Path(dict_path).resolve()
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

    runtime = DictionaryRuntime(dict_p, user_db_p)

    app = FastAPI(title="Flashcard Vocabulary API", version="0.1.0")

    app.state.dict_path = dict_p
    app.state.user_db_path = user_db_p
    app.state.cors_origins = cors_origins_set
    app.state.tts_remote_url = tts_remote_url
    app.state.media_dir = resolved_media_dir
    app.state.cache_dir = resolved_cache_dir
    app.state.runtime = runtime

    app.add_middleware(BrowserSecurityMiddleware, cors_origins=cors_origins_set)

    @app.on_event("shutdown")
    def shutdown_event() -> None:
        if hasattr(app.state, "runtime") and not app.state.runtime.is_closed:
            app.state.runtime.close()

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

        asset_token, candidates = runtime.materialize_lookup(clean_q)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": clean_q,
                "asset_token": asset_token,
                "candidates": _to_json_compatible(candidates),
            },
        )

    @app.post("/vocab/notes")
    async def capture_note_endpoint(request: Request) -> JSONResponse:
        body = await request.json()

        # 1. Stale picker token validation (ADR-0004 D47)
        picker_token = body.get("asset_token")

        with runtime.reading() as snapshot:
            active_token = snapshot.asset_token
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
                    deck_id = create_deck(conn, clean_deck_name)

            note_id = create_note(
                conn,
                lemma_semantic_ref=clean_lemma_ref,
                sense_semantic_ref=clean_sense_ref,
                status=status_val,
                component_bindings=component_refs or (),
                meaning_languages=validated_langs,
            )

            if deck_id is not None:
                conn.execute(
                    """
                    INSERT INTO note_deck (note_id, deck_id, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(note_id, deck_id) DO NOTHING
                    """,
                    (note_id, deck_id, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()

            if user_meanings_input:
                for um_lang, um_text in user_meanings_input.items():
                    set_user_meaning(conn, note_id, um_lang, um_text.strip())

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
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": str(exc)},
            )
        finally:
            conn.close()

    @app.get("/vocab/cards/next")
    def next_card_endpoint(deck_id: int | None = None) -> JSONResponse:
        card_obs = runtime.observe_card_render(deck_id=deck_id)
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

        try:
            runtime.activate_dictionary(path_val.strip(), version=version.strip())
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "activated",
                    "version": version.strip(),
                    "asset_token": runtime.asset_token,
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
        cards_obs = runtime.observe_export_payload(deck_id=deck_id)

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

    return app
