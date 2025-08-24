#!/usr/bin/env python3
import argparse
import asyncio
import logging

from ws_server.tts.voice_validation import list_voices_with_aliases
from ws_server.core.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
async def _async_main() -> None:
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
    main()

# --- auto-added robust console entrypoint for 'va' ---
def _wrapped_main():
    import inspect, asyncio
    # Prefer sync wrapper if present
    try:
        res = _wrapped_main()
    except NameError:
        # Fallback to async if only async is defined
        try:
            coro = _async_main()
        except NameError:
            # Nothing defined? then no-op
            return
        else:
            return asyncio.run(coro)
    else:
        # If a sync wrapper returned a coroutine, run it.
        if inspect.iscoroutine(res):
            return asyncio.run(res)
        return res
