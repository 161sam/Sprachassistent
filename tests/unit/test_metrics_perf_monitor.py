import asyncio
import logging
import types
import pytest

from ws_server.metrics.perf_monitor import PerformanceMonitor


def _dummy_psutil(monkeypatch):
    class DummyProcess:
        def memory_info(self):
            return types.SimpleNamespace(rss=1024 * 1024)

        def memory_percent(self):
            return 12.0

        def cpu_percent(self):
            return 34.0

    dummy = types.SimpleNamespace(
        Process=lambda: DummyProcess(),
        virtual_memory=lambda: types.SimpleNamespace(total=2 ** 30, available=2 ** 29),
        cpu_percent=lambda: 56.0,
        cpu_count=lambda: 4,
        disk_usage=lambda _: types.SimpleNamespace(percent=78.0, free=2 ** 30),
    )
    monkeypatch.setattr("ws_server.metrics.perf_monitor.psutil", dummy)


def test_trackers(monkeypatch):
    _dummy_psutil(monkeypatch)
    mon = PerformanceMonitor()
    mon.track_connection(True)
    mon.track_connection(False)
    assert mon.connections_count == 0
    mon.track_request(True)
    mon.track_request(False)
    assert mon.total_requests == 2
    assert mon.error_count == 1


def test_get_system_metrics(monkeypatch):
    _dummy_psutil(monkeypatch)
    mon = PerformanceMonitor()
    mon.max_history_size = 0
    mon.start_time -= 10
    metrics = mon.get_system_metrics()
    assert metrics["cpu"]["process_percent"] == 34.0
    assert metrics["memory"]["percent"] == 12.0
    assert metrics["connections"]["active"] == 0
    assert mon.metrics_history == []


def test_get_performance_summary(monkeypatch):
    mon = PerformanceMonitor()

    def fake_metrics():
        return {
            "timestamp": "now",
            "uptime_seconds": 0,
            "memory": {"percent": 90, "used_mb": 0, "system_total_gb": 1, "system_available_gb": 0},
            "cpu": {"process_percent": 80, "system_percent": 0, "core_count": 1},
            "connections": {"active": 0, "total_requests": 1, "error_count": 1, "error_rate": 100},
            "disk": {"used_percent": 95, "free_gb": 0},
        }

    monkeypatch.setattr(mon, "get_system_metrics", fake_metrics)
    summary = mon.get_performance_summary()
    assert summary["status"] == "critical"
    assert "High memory usage" in summary["warnings"]
    assert "High CPU usage" in summary["warnings"]
    assert "High error rate" in summary["warnings"]
    assert "Low disk space" in summary["warnings"]


def test_get_performance_summary_healthy(monkeypatch):
    mon = PerformanceMonitor()

    monkeypatch.setattr(
        mon,
        "get_system_metrics",
        lambda: {
            "timestamp": "now",
            "uptime_seconds": 0,
            "memory": {"percent": 10, "used_mb": 0, "system_total_gb": 1, "system_available_gb": 1},
            "cpu": {"process_percent": 10, "system_percent": 0, "core_count": 1},
            "connections": {"active": 0, "total_requests": 1, "error_count": 0, "error_rate": 0},
            "disk": {"used_percent": 10, "free_gb": 1},
        },
    )
    summary = mon.get_performance_summary()
    assert summary["status"] == "healthy"


def test_get_performance_summary_warning(monkeypatch):
    mon = PerformanceMonitor()

    monkeypatch.setattr(
        mon,
        "get_system_metrics",
        lambda: {
            "timestamp": "now",
            "uptime_seconds": 0,
            "memory": {"percent": 90, "used_mb": 0, "system_total_gb": 1, "system_available_gb": 1},
            "cpu": {"process_percent": 75, "system_percent": 0, "core_count": 1},
            "connections": {"active": 0, "total_requests": 1, "error_count": 0, "error_rate": 0},
            "disk": {"used_percent": 10, "free_gb": 1},
        },
    )
    summary = mon.get_performance_summary()
    assert summary["status"] == "warning"


def test_format_uptime():
    mon = PerformanceMonitor()
    assert mon._format_uptime(120) == "2m"
    assert mon._format_uptime(7200) == "2h 0m"
    assert mon._format_uptime(90000).startswith("1d")


def test_log_performance_alert(caplog):
    mon = PerformanceMonitor()
    with caplog.at_level(logging.WARNING):
        mon.log_performance_alert("cpu", 99)
    assert "Performance Alert" in caplog.text


@pytest.mark.asyncio
async def test_monitor_loop_logs(monkeypatch, caplog):
    mon = PerformanceMonitor()
    monkeypatch.setattr(
        mon,
        "get_performance_summary",
        lambda: {
            "status": "warning",
            "warnings": ["high"],
            "health_score": 50,
            "metrics": {
                "memory": {"percent": 0},
                "cpu": {"process_percent": 0},
                "connections": {"active": 0},
                "uptime_seconds": 0,
            },
            "uptime_formatted": "0m",
        },
    )
    monkeypatch.setattr("ws_server.metrics.perf_monitor.time.time", lambda: 3600)

    async def fake_sleep(_):
        raise asyncio.CancelledError

    monkeypatch.setattr("ws_server.metrics.perf_monitor.asyncio.sleep", fake_sleep)
    with caplog.at_level(logging.INFO):
        with pytest.raises(asyncio.CancelledError):
            await mon.monitor_loop(interval=1)
    assert "Performance Status" in caplog.text
    assert "- high" in caplog.text


@pytest.mark.asyncio
async def test_monitor_loop_error(monkeypatch, caplog):
    mon = PerformanceMonitor()

    def raiser():
        raise RuntimeError("boom")

    monkeypatch.setattr(mon, "get_performance_summary", raiser)

    async def fake_sleep(_):
        raise asyncio.CancelledError

    monkeypatch.setattr("ws_server.metrics.perf_monitor.asyncio.sleep", fake_sleep)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(asyncio.CancelledError):
            await mon.monitor_loop(interval=1)
    assert "Error in performance monitoring" in caplog.text
