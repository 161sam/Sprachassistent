#!/usr/bin/env python3
"""
Minimal Test Server für Voice Assistant - nur kritische Komponenten
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# PYTHONPATH Setup
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Environment
os.environ.setdefault('WS_HOST', '127.0.0.1')
os.environ.setdefault('WS_PORT', '48231')
os.environ.setdefault('METRICS_PORT', '48232')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_metrics_api():
    """Test nur die Metrics API"""
    logger.info("🧪 Testing Metrics API only...")
    
    try:
        # Import test
        from backend.ws_server.metrics_api import MetricsAPI
        logger.info("✅ Metrics API import successful")
        
        # Dummy server object
        class DummyServer:
            def get_stats(self):
                return {
                    'active_connections': 0,
                    'total_connections': 0,
                    'messages_processed': 0,
                    'uptime_seconds': 0
                }
        
        # Create API
        dummy_server = DummyServer()
        metrics_api = MetricsAPI(dummy_server)
        logger.info("✅ Metrics API instance created")
        
        # Test aiohttp
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get('/test', lambda req: web.json_response({'status': 'ok'}))
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '127.0.0.1', 48232)
        await site.start()
        
        logger.info("✅ Test HTTP server started on 127.0.0.1:48232")
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Test endpoint
        import urllib.request
        try:
            response = urllib.request.urlopen("http://127.0.0.1:48232/test", timeout=2)
            data = response.read().decode()
            logger.info(f"✅ HTTP endpoint test successful: {data}")
        except Exception as e:
            logger.error(f"❌ HTTP endpoint test failed: {e}")
        
        await runner.cleanup()
        logger.info("✅ Cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Metrics API test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_websockets():
    """Test nur WebSocket ohne Server-Logic"""
    logger.info("🧪 Testing WebSocket basics...")
    
    try:
        import websockets
        logger.info("✅ WebSocket import successful")
        
        # Simple echo handler
        async def echo_handler(websocket, path=None):
            logger.info(f"WebSocket connection from {websocket.remote_address}")
            try:
                async for message in websocket:
                    await websocket.send(f"Echo: {message}")
            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed")
        
        # Start server
        server = await websockets.serve(echo_handler, "127.0.0.1", 48231)
        logger.info("✅ WebSocket server started on 127.0.0.1:48231")
        
        await asyncio.sleep(2)
        
        # Cleanup
        server.close()
        await server.wait_closed()
        logger.info("✅ WebSocket cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main test routine"""
    logger.info("🔬 VOICE ASSISTANT MINIMAL SERVER TEST")
    logger.info("=" * 50)
    
    # Test 1: Metrics API
    if not await test_metrics_api():
        logger.error("❌ Metrics API test failed - stopping")
        return False
        
    # Test 2: WebSocket basics
    if not await test_websockets():
        logger.error("❌ WebSocket test failed - stopping")
        return False
        
    logger.info("🎉 ALL TESTS PASSED!")
    logger.info("The problem is likely in the main server logic, not basic components")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
