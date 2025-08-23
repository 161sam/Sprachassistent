# ws_server/metrics/collector.py – network & memory metrics

## Problem
Collector lacked system memory usage and network throughput metrics; TODO requested tracking both.

## Approach
- Add `system_memory_percent` gauge and counters for bytes sent/received.
- Track network I/O via `psutil.net_io_counters`; keep last values to emit deltas.
- Extend `_update_system_metrics` to update memory and network counters periodically.
- Provide tests using a stubbed `psutil` to verify counter increments.
