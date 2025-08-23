import asyncio
import types
import pytest

from ws_server.metrics.collector import MetricsCollector


@pytest.mark.asyncio
async def test_collector_start_updates_system_metrics(monkeypatch):
    calls = {"cpu": 0, "rss": 0}

    class DummyProcess:
        def memory_info(self):
            calls["rss"] += 1
            return types.SimpleNamespace(rss=123)

    dummy_psutil = types.SimpleNamespace(
        cpu_percent=lambda: calls.update(cpu=calls["cpu"] + 1) or 11,
        Process=lambda: DummyProcess(),
    )
    monkeypatch.setattr("ws_server.metrics.collector.psutil", dummy_psutil)

    async def fake_sleep(_):
        raise asyncio.CancelledError

    monkeypatch.setattr("ws_server.metrics.collector.asyncio.sleep", fake_sleep)

    collector = MetricsCollector()
    collector.start()
    assert collector._system_task is not None

    with pytest.raises(asyncio.CancelledError):
        await collector._system_task

    # ensure our dummy psutil functions were invoked
    assert calls["cpu"] == 1
    assert calls["rss"] == 1
