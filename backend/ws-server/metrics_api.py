#!/usr/bin/env python3
"""
🌐 HTTP API Server für Voice Assistant Metriken
Ergänzt den WebSocket-Server um HTTP-Endpoints für Monitoring
"""

import asyncio
import json
import time
from aiohttp import web, ClientSession
import logging

logger = logging.getLogger(__name__)

class MetricsAPI:
    """HTTP API für Performance-Metriken"""
    
    def __init__(self, voice_server):
        self.voice_server = voice_server
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/metrics', self.get_metrics)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.get_status)
        self.app.router.add_options('/{path:.*}', self.handle_cors)
        
        # CORS middleware
        self.app.middlewares.append(self.cors_handler)
        
    async def cors_handler(self, request, handler):
        """Handle CORS for monitoring tools"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    async def handle_cors(self, request):
        """Handle OPTIONS requests"""
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    async def get_metrics(self, request):
        """Get detailed server metrics"""
        try:
            stats = self.voice_server.get_stats()
            
            # Add additional system metrics
            metrics = {
                **stats,
                'server_time': time.time(),
                'api_version': '2.1.0',
                'endpoints': {
                    'websocket': 'ws://localhost:8123',
                    'metrics': 'http://localhost:8124/metrics',
                    'health': 'http://localhost:8124/health'
                }
            }
            
            return web.json_response(metrics)
            
        except Exception as e:
            logger.error(f"Metrics API error: {e}")
            return web.json_response(
                {'error': 'Internal server error'}, 
                status=500
            )
            
    async def health_check(self, request):
        """Simple health check endpoint"""
        try:
            stats = self.voice_server.get_stats()
            
            # Determine health status
            health_status = 'healthy'
            if stats['active_connections'] > 100:
                health_status = 'degraded'
            if stats['processing_queue_size'] > 20:
                health_status = 'unhealthy'
                
            return web.json_response({
                'status': health_status,
                'timestamp': time.time(),
                'uptime': stats['uptime_seconds'],
                'connections': stats['active_connections']
            })
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {'status': 'error', 'error': str(e)}, 
                status=500
            )
            
    async def get_status(self, request):
        """Get simple status information"""
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
            return web.json_response(
                {'status': 'error', 'error': str(e)}, 
                status=500
            )

async def start_metrics_api(voice_server, port=8124):
    """Start the HTTP metrics API server"""
    metrics_api = MetricsAPI(voice_server)
    
    runner = web.AppRunner(metrics_api.app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"📊 Metrics API server running on port {port}")
    return runner

if __name__ == "__main__":
    # This can be imported and used by the main server
    pass
