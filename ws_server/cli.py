#!/usr/bin/env python3
import argparse
import asyncio
import logging

from backend.tts.model_validation import list_voices_with_aliases
from ws_server.core.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-models",
        action="store_true",
        help="TTS-Modelle prüfen und verfügbare Stimmen anzeigen",
    )
    args = parser.parse_args()

    alias_map = list_voices_with_aliases()
    if args.validate_models:
        for voice, aliases in alias_map.items():
            if aliases:
                print(f"{voice}: {', '.join(aliases)}")
            else:
                print(voice)
        return

    for voice, aliases in alias_map.items():
        if aliases:
            logging.info(
                "Verfügbare Stimme: %s (Aliase: %s)", voice, ", ".join(aliases)
            )
        else:
            logging.info("Verfügbare Stimme: %s", voice)

    from ws_server.transport.server import VoiceServer
    from ws_server.metrics.collector import collector
    from ws_server.metrics.http_api import start_http_server

    server = VoiceServer()
    await server.initialize()

    host = config.ws_host
    port = config.ws_port
    metrics_port = config.metrics_port

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
