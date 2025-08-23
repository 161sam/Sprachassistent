import pytest

from ws_server.routing.intent_router import IntentRouter


@pytest.mark.asyncio
async def test_intent_router_uses_skill():
    router = IntentRouter()
    response = await router.route("hallo")
    assert response.startswith("Hallo!")
