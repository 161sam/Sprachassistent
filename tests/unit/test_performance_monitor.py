import json
import types
import pytest
from backend.performance_monitor import VoiceAssistantMonitor, PerformanceMetrics

class DummyResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload
    async def json(self):
        return self._payload
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass

class DummySession:
    def __init__(self, response):
        self._response = response
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    def get(self, url):
        return self._response

@pytest.mark.asyncio
async def test_collect_metrics(monkeypatch):
    payload = {
        "active_connections": 1,
        "total_connections": 2,
        "messages_processed": 5,
        "audio_streams_processed": 3,
        "uptime_seconds": 8,
        "active_audio_streams": 1,
        "processing_queue_size": 0,
    }
    dummy = DummySession(DummyResponse(200, payload))
    monkeypatch.setattr("backend.performance_monitor.aiohttp.ClientSession", lambda: dummy)
    monkeypatch.setattr("backend.performance_monitor.psutil.cpu_percent", lambda interval=1: 42.0)
    mem = types.SimpleNamespace(percent=33.0, used=1024 * 1024 * 123)
    net = types.SimpleNamespace(bytes_sent=10, bytes_recv=20)
    monkeypatch.setattr("backend.performance_monitor.psutil.virtual_memory", lambda: mem)
    monkeypatch.setattr("backend.performance_monitor.psutil.net_io_counters", lambda: net)

    monitor = VoiceAssistantMonitor("http://test")
    metrics = await monitor.collect_metrics()
    assert metrics.active_connections == 1
    assert metrics.cpu_percent == 42.0
    assert metrics.memory_mb == pytest.approx(123)


def test_analyze_performance():
    monitor = VoiceAssistantMonitor()
    base = PerformanceMetrics(
        timestamp=0,
        active_connections=1,
        total_connections=1,
        messages_processed=0,
        audio_streams_processed=0,
        uptime_seconds=0,
        active_audio_streams=0,
        processing_queue_size=0,
        cpu_percent=10,
        memory_percent=10,
        memory_mb=10,
        network_bytes_sent=0,
        network_bytes_recv=0,
    )
    high = PerformanceMetrics(
        timestamp=1,
        active_connections=1,
        total_connections=1,
        messages_processed=0,
        audio_streams_processed=0,
        uptime_seconds=0,
        active_audio_streams=0,
        processing_queue_size=20,
        cpu_percent=90,
        memory_percent=90,
        memory_mb=10,
        network_bytes_sent=0,
        network_bytes_recv=0,
    )
    monitor.metrics_history = [base, high]
    result = monitor.analyze_performance()
    assert result["category"] == "poor"
    assert "High CPU usage" in result["issues"]
    assert "High memory usage" in result["issues"]
    assert "High processing queue" in result["issues"]


def test_export_metrics(tmp_path):
    monitor = VoiceAssistantMonitor()
    monitor.metrics_history = [
        PerformanceMetrics(
            timestamp=1,
            active_connections=0,
            total_connections=0,
            messages_processed=0,
            audio_streams_processed=0,
            uptime_seconds=0,
            active_audio_streams=0,
            processing_queue_size=0,
            cpu_percent=0,
            memory_percent=0,
            memory_mb=0,
            network_bytes_sent=0,
            network_bytes_recv=0,
        )
    ]
    out_file = tmp_path / "metrics.json"
    monitor.export_metrics(str(out_file))
    data = json.loads(out_file.read_text())
    assert data["metrics_count"] == 1
