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
        self.app.router.add_get('/status', self.get_status)
        self.app.router.add_options('/{path:.*}', self.handle_cors)
        self.app.middlewares.append(self.cors_handler)

    async def cors_handler(self, request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    async def handle_cors(self, request):
        return web.Response(headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
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
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Metrics API error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def health_check(self, request):
        try:
            stats = self.voice_server.get_stats()
            health_status = 'healthy'
            if stats['active_connections'] > 100: health_status = 'degraded'
            if stats['processing_queue_size'] > 20: health_status = 'unhealthy'
            return web.json_response({
                'status': health_status,
                'timestamp': time.time(),
                'uptime': stats['uptime_seconds'],
                'connections': stats['active_connections']
            })
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response({'status': 'error', 'error': str(e)}, status=500)

    async def get_status(self, request):
        try:
            stats = self.voice_server.get_stats()
            return web.json_response({
                'server': 'Voice Assistant Backend',
                'version': '2.1.0',
                'status': 'running',
                'uptime_hours': round(stats['uptime_seconds'] / 3600, 1),
                'connections': stats['active_connections'],
                'streams': stats['active_audio_streams']
            })
        except Exception as e:
            return web.json_response({'status': 'error', 'error': str(e)}, status=500)

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
