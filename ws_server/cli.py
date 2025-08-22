#!/usr/bin/env python3
import asyncio, os, logging
from ws_server.transport.server import VoiceServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main():
    server = VoiceServer()
    await server.initialize()
    host = os.getenv("WS_HOST","127.0.0.1")
    port = int(os.getenv("WS_PORT","48231"))
    import websockets
    async with websockets.serve(server.handle_websocket, host, port, ping_interval=20, ping_timeout=10):
        logging.info("Unified WS-Server listening on ws://%s:%s", host, port)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
