#!/usr/bin/env python3
"""
🌐 HTTP API Server für Voice Assistant Metriken
Ergänzt den WebSocket-Server um HTTP-Endpoints für Monitoring.
Alle Hosts/Ports sind ENV-gesteuert (WS_HOST, WS_PORT, METRICS_PORT).
"""

import asyncio
import os
import json
import time
import logging
from aiohttp import web

from aiohttp import web

@web.middleware
async def cors_middleware(request, handler):
    try:
        resp = await handler(request)
    except web.HTTPException as ex:
        resp = ex
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

logger = logging.getLogger(__name__)

# ENV
WS_HOST = os.getenv('WS_HOST', '127.0.0.1')
WS_PORT = int(os.getenv('WS_PORT', '48231'))
METRICS_PORT = int(os.getenv('METRICS_PORT', '48232'))

# Für "0.0.0.0" Links trotzdem localhost zeigen
def _display_host(h: str) -> str:
    return '127.0.0.1' if h in ('0.0.0.0', '::') else h

def _endpoints():
    host_disp = _display_host(WS_HOST)
    met_disp  = _display_host(WS_HOST)
    return {
        'websocket': f'ws://{host_disp}:{WS_PORT}',
        'metrics':   f'http://{met_disp}:{METRICS_PORT}/metrics',
        'health':    f'http://{met_disp}:{METRICS_PORT}/health'
    }

class MetricsAPI:
    """HTTP API für Performance-Metriken"""
    def __init__(self, voice_server):
        self.voice_server = voice_server
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        self.app.router.add_get('/metrics', self.get_metrics)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status_handler)
        self.app.router.add_options('/{path:.*}', self.handle_cors)
        self.app.middlewares.append(cors_middleware)

    async def handle_cors(self, request):
        from aiohttp import web
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        })



    async def get_metrics(self, request):
        try:
            stats = self.voice_server.get_stats()
            metrics = {
                **stats,
                'server_time': time.time(),
                'api_version': '2.1.0',
                'endpoints': _endpoints()
            }
            import json
            return web.json_response(metrics, dumps=lambda d: json.dumps(d, default=str))
        except Exception as e:
            logger.error(f"Metrics API error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    def get_status(self):
        """Interner Status für Boot‑Checks und /health."""
        engines = []
        default_engine = None
        try:
            tm = getattr(self, 'voice_server', None)
            if tm and getattr(tm, 'tts_manager', None):
                ttm = tm.tts_manager
                engines = list(getattr(ttm, 'engines', {}).keys())
                cur = getattr(ttm, 'get_current_engine', lambda: None)()
                if cur is not None:
                    default_engine = getattr(cur, 'value', str(cur))
        except Exception:
            pass
        return {
            'service': 'metrics',
            'ok': True,
            'engines': [str(e) for e in engines],
            'default_engine': default_engine,
        }


    async def status_handler(self, request):
        from aiohttp import web
        return web.json_response(self.get_status())










    async def health_check(self, request):
        from aiohttp import web
        data = {'status': 'ok', **self.get_status()}
        return web.json_response(data)









async def start_metrics_api(voice_server, port=METRICS_PORT):
    """Startet die HTTP Metrics API (bindet auf WS_HOST, Port aus Param/ENV)."""
    metrics_api = MetricsAPI(voice_server)
    runner = web.AppRunner(metrics_api.app)
    await runner.setup()
    site = web.TCPSite(runner, WS_HOST, port)
    await site.start()
    logger.info(f"📊 Metrics API server running on {WS_HOST}:{port}")
    return runner

if __name__ == "__main__":
    pass
