"""Deterministic production-image structure checks; no Docker daemon required."""

from __future__ import annotations

from pathlib import Path


def test_dockerfile_builds_frontend_and_starts_single_fastapi_service() -> None:
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:22-bookworm-slim AS frontend-build" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "COPY --from=frontend-build /app/frontend ./app/frontend" in dockerfile
    assert '"uvicorn", "app.api:create_production_app", "--factory"' in dockerfile
    assert '"--host", "127.0.0.1", "--port", "8000"' in dockerfile
    assert "flashcard runtime ready" not in dockerfile
