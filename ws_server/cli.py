#!/usr/bin/env python3
import argparse
import asyncio
import logging
import os

from ws_server.transport.server import VoiceServer
from ws_server.metrics.collector import collector
from ws_server.metrics.http_api import start_http_server
from backend.tts.model_validation import list_voices_with_aliases, validate_models
from ws_server.core.config import load_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-models",
        action="store_true",
        help="TTS-Modelle prüfen und verfügbare Stimmen anzeigen",
    )
    args = parser.parse_args()

    voices = validate_models()
    if args.validate_models:
        alias_map = list_voices_with_aliases()
        for voice in voices:
            aliases = alias_map.get(voice, [])
            if aliases:
                print(f"{voice}: {', '.join(aliases)}")
            else:
                print(voice)
        return

    load_env()

    server = VoiceServer()
    await server.initialize()

    host = os.getenv("WS_HOST")
    port = int(os.getenv("WS_PORT"))
    metrics_port = int(os.getenv("METRICS_PORT"))

    collector.start()
    await start_http_server(metrics_port)

    import websockets

    async with websockets.serve(
        server.handle_websocket, host, port, ping_interval=20, ping_timeout=10
    ):
        logging.info("Unified WS-Server listening on ws://%s:%s", host, port)
        logging.info("📊 Metrics at :%s", metrics_port)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
