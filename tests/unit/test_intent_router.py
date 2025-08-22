import asyncio
from unittest.mock import AsyncMock

import pytest

from ws_server.routing.intent_router import IntentRouter


@pytest.mark.asyncio
async def test_routes_local_skill():
    router = IntentRouter()
    result = await router.route("hallo")
    assert "Hallo" in result


@pytest.mark.asyncio
async def test_routes_flowise(monkeypatch):
    monkeypatch.setenv("FLOWISE_URL", "http://flowise")
    router = IntentRouter()
    mock_call = AsyncMock(return_value="flowise-answer")
    monkeypatch.setattr(router, "_call_flowise", mock_call)
    out = await router.route("frage zum wetter")
    mock_call.assert_awaited_once()
    assert out == "flowise-answer"


@pytest.mark.asyncio
async def test_routes_n8n(monkeypatch):
    monkeypatch.setenv("N8N_HOST", "localhost")
    router = IntentRouter()
    mock_call = AsyncMock(return_value="automation-done")
    monkeypatch.setattr(router, "_call_n8n", mock_call)
    out = await router.route("schalte das licht ein")
    mock_call.assert_awaited_once()
    assert out == "automation-done"
