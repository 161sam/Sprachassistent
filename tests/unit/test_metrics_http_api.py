import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer
from prometheus_client import CONTENT_TYPE_LATEST

from ws_server.metrics.http_api import create_app, start_http_server
from ws_server.core.config import config


@pytest.mark.asyncio
async def test_create_app_routes():
    app = create_app()
    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/health")
        assert resp.status == 200
        assert await resp.json() == {"status": "green"}

        resp = await client.get("/metrics")
        assert resp.status == 200
        assert resp.headers["Content-Type"] == CONTENT_TYPE_LATEST
        text = await resp.text()
        assert text.startswith("# HELP")


@pytest.mark.asyncio
async def test_start_http_server(unused_tcp_port):
    runner = await start_http_server(unused_tcp_port)
    try:
        async with ClientSession() as session:
            async with session.get(f"http://{config.ws_host}:{unused_tcp_port}/health") as resp:
                assert resp.status == 200
                assert await resp.json() == {"status": "green"}
    finally:
        await runner.cleanup()
