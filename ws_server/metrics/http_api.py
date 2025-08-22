"""HTTP endpoints for metrics and health checks.

The module exposes :func:`create_app` used by tests and
:func:`start_http_server` which launches an ``aiohttp`` web server in the
background.  The ``/metrics`` endpoint returns Prometheus text format metrics
and ``/health`` reports basic service status.
"""

from __future__ import annotations

import logging
from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .collector import collector
from ws_server.core.config import config

logger = logging.getLogger(__name__)


async def _metrics_handler(request: web.Request) -> web.StreamResponse:
    data = generate_latest(collector.registry)
    return web.Response(body=data, headers={"Content-Type": CONTENT_TYPE_LATEST})


async def _health_handler(request: web.Request) -> web.StreamResponse:
    return web.json_response({"status": "green"})


def create_app() -> web.Application:
    """Create an ``aiohttp`` application exposing metrics endpoints."""

    app = web.Application()
    app.router.add_get("/metrics", _metrics_handler)
    app.router.add_get("/health", _health_handler)
    return app


async def start_http_server(port: int | None = None) -> web.AppRunner:
    """Start the metrics HTTP server on ``port``.

    Returns the underlying :class:`~aiohttp.web.AppRunner` so that callers can
    shut down the service again during tests.
    """

    host = config.ws_host
    port = port or config.metrics_port

    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("📊 Metrics API server running on %s:%s", host, port)
    return runner


__all__ = ["create_app", "start_http_server"]

