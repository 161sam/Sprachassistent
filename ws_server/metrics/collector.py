"""Minimal metrics collector using Prometheus client.

This module exposes a singleton :data:`collector` that other parts of the
server can use to record counters and gauges.  The collector keeps track of
active connections, message counts and basic latency histograms.  It is
intentionally lightweight to avoid blocking the event loop.
"""

# TODO: track memory usage and network throughput metrics
#       (see TODO-Index.md: WS-Server / Protokolle)

from __future__ import annotations

import asyncio
import logging
from typing import Optional

try:  # pragma: no-cover - optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil may not be installed in tests
    psutil = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
    )
except Exception:  # pragma: no cover - provide no-op stand-ins
    class _Value:
        def __init__(self) -> None:
            self._val = 0

        def set(self, value, *_args, **_kwargs):  # pragma: no cover - stub
            self._val = value

        def get(self):  # pragma: no cover - stub
            return self._val

    class _DummyMetric:
        def __init__(self, *args, **kwargs):
            self._value = _Value()

        def labels(self, *args, **kwargs):  # pragma: no cover - stub
            return self

        def inc(self, amount: float = 1, *args, **kwargs):  # type: ignore[no-redef]
            self._value._val += amount

        def dec(self, amount: float = 1, *args, **kwargs):  # type: ignore[no-redef]
            self._value._val -= amount

        def observe(self, *args, **kwargs):  # type: ignore[no-redef]
            pass

    class _DummyRegistry:
        pass

    CollectorRegistry = _DummyRegistry  # type: ignore
    Counter = Gauge = Histogram = _DummyMetric  # type: ignore

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Central metrics registry used by the WebSocket server."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()

        # Gauges
        self.active_connections = Gauge(
            "ws_active_connections",
            "Number of active WebSocket connections",
            registry=self.registry,
        )
        self.cpu_percent = Gauge(
            "system_cpu_percent",
            "System wide CPU utilisation in percent",
            registry=self.registry,
        )
        self.memory_rss_bytes = Gauge(
            "process_resident_memory_bytes",
            "Resident memory size of the server process in bytes",
            registry=self.registry,
        )

        # Counters
        self.messages_total = Counter(
            "ws_messages_total",
            "Count of received WebSocket messages",
            ["protocol"],
            registry=self.registry,
        )
        self.errors_total = Counter(
            "ws_errors_total",
            "Number of error responses sent to clients",
            ["type"],
            registry=self.registry,
        )
        self.tts_cache_hits = Counter(
            "tts_cache_hits_total",
            "Number of TTS cache hits",
            registry=self.registry,
        )
        self.tts_cache_misses = Counter(
            "tts_cache_misses_total",
            "Number of TTS cache misses",
            registry=self.registry,
        )
        self.tts_chunk_emitted_total = Counter(
            "tts_chunk_emitted_total",
            "Number of emitted TTS chunks",
            ["engine"],
            registry=self.registry,
        )
        self.tts_sequence_timeout_total = Counter(
            "tts_sequence_timeout_total",
            "Number of TTS chunk timeouts",
            ["engine"],
            registry=self.registry,
        )
        self.tts_engine_unavailable_total = Counter(
            "tts_engine_unavailable_total",
            "Number of times a TTS engine was unavailable",
            ["engine"],
            registry=self.registry,
        )

        # Audio throughput counters
        self.audio_in_bytes_total = Counter(
            "audio_in_bytes_total",
            "Total number of audio bytes received from clients",
            registry=self.registry,
        )
        self.audio_out_bytes_total = Counter(
            "audio_out_bytes_total",
            "Total number of audio bytes sent to clients",
            registry=self.registry,
        )

        # Histograms for latency measurements
        self.stt_latency = Histogram(
            "stt_latency_seconds",
            "Latency of STT processing in seconds",
            registry=self.registry,
            buckets=(0.1, 0.5, 1, 2, 5, 10),
        )
        self.tts_latency = Histogram(
            "tts_latency_seconds",
            "Latency of TTS synthesis in seconds",
            registry=self.registry,
            buckets=(0.1, 0.5, 1, 2, 5, 10),
        )

        self._system_task: Optional[asyncio.Task] = None
        self._process = psutil.Process() if psutil is not None else None

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start background tasks for system metrics collection."""

        if self._system_task is None:
            loop = asyncio.get_event_loop()
            self._system_task = loop.create_task(self._update_system_metrics())

    async def _update_system_metrics(self) -> None:
        while True:
            try:
                if psutil is not None:  # pragma: no cover - not critical in tests
                    self.cpu_percent.set(psutil.cpu_percent())
                    if self._process is not None:
                        self.memory_rss_bytes.set(self._process.memory_info().rss)
            except Exception as exc:  # pragma: no cover - diagnostic only
                logger.debug("cpu metrics failed: %s", exc)
            await asyncio.sleep(5)


# Singleton instance used by the application
collector = MetricsCollector()


__all__ = ["collector", "MetricsCollector"]

