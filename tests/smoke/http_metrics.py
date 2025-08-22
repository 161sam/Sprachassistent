import asyncio

import aiohttp
from aiohttp import web

from ws_server.metrics.http_api import create_app


async def _run_checks() -> None:
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://127.0.0.1:{port}/health") as resp:
            assert resp.status == 200

        async with session.get(f"http://127.0.0.1:{port}/metrics") as resp:
            assert resp.status == 200
            assert resp.headers["Content-Type"].startswith("text/plain")

    await runner.cleanup()


def test_http_metrics_smoke() -> None:
    asyncio.run(_run_checks())

