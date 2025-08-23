import asyncio
import types
import pytest

from ws_server.metrics.collector import MetricsCollector
import ws_server.metrics.http_api  # noqa: F401 - ensure coverage
import ws_server.metrics.perf_monitor  # noqa: F401 - ensure coverage


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
        virtual_memory=lambda: types.SimpleNamespace(percent=0),
        net_io_counters=lambda: types.SimpleNamespace(
            bytes_sent=0, bytes_recv=0
        ),
    )
    monkeypatch.setattr("ws_server.metrics.collector.psutil", dummy_psutil)

    collector = MetricsCollector()
    collector.start()
    assert collector._system_task is not None
    collector._system_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await collector._system_task
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(collector._update_system_metrics(), 0.01)

    # ensure our dummy psutil functions were invoked
    assert calls["cpu"] == 1
    assert calls["rss"] == 1


@pytest.mark.asyncio
async def test_network_counters(monkeypatch):
    class DummyProcess:
        def memory_info(self):
            return types.SimpleNamespace(rss=0)

    class DummyPsutil:
        def cpu_percent(self):
            return 0

        def Process(self):
            return DummyProcess()

        def virtual_memory(self):
            return types.SimpleNamespace(percent=0)

        def net_io_counters(self):
            return types.SimpleNamespace(bytes_sent=150, bytes_recv=90)

    dummy_psutil = DummyPsutil()
    monkeypatch.setattr("ws_server.metrics.collector.psutil", dummy_psutil)

    collector = MetricsCollector()
    collector._last_net_io = types.SimpleNamespace(
        bytes_sent=100,
        bytes_recv=50,
    )

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(collector._update_system_metrics(), 0.01)

    assert collector.network_bytes_sent_total._value.get() == 50
    assert collector.network_bytes_recv_total._value.get() == 40
