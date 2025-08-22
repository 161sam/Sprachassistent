"""
Performance Metrics API for Voice Assistant
Provides real-time monitoring and diagnostics for binary audio pipeline
"""

import asyncio
import json
import time
import psutil
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class LatencyMetric:
    """Individual latency measurement"""
    timestamp: float
    operation: str  # 'stt', 'tts', 'audio_processing', 'binary_decode'
    latency_ms: float
    stream_id: str = ""
    additional_info: Dict[str, Any] = None

@dataclass
class AudioQualityMetric:
    """Audio quality measurement"""
    timestamp: float
    stream_id: str
    sample_rate: int
    bit_depth: int
    signal_to_noise_ratio: float = 0.0
    peak_amplitude: float = 0.0
    rms_level: float = 0.0
    frequency_response: Dict[str, float] = None

@dataclass
class ConnectionMetric:
    """Connection quality measurement"""
    timestamp: float
    connection_id: str
    latency_ms: float
    packet_loss: float = 0.0
    bandwidth_usage: int = 0  # bytes per second
    connection_type: str = "websocket"

class MetricsCollector:
    """Collects and aggregates performance metrics"""
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        
        # Metric storage
        self.latency_metrics: deque = deque(maxlen=max_history_size)
        self.audio_quality_metrics: deque = deque(maxlen=max_history_size)
        self.connection_metrics: deque = deque(maxlen=max_history_size)
        
        # Real-time aggregations
        self.current_stats = {
            'latency': defaultdict(list),
            'throughput': defaultdict(int),
            'error_rates': defaultdict(int),
            'system_resources': {}
        }
        
        # Performance tracking
        self.operation_timers: Dict[str, float] = {}
        self.active_streams: Dict[str, Dict] = {}
        
        # Start background aggregation
        self.aggregation_thread = threading.Thread(target=self._background_aggregation, daemon=True)
        self.aggregation_thread.start()
        
        logger.info("MetricsCollector initialized")
    
    def start_operation_timer(self, operation_id: str, operation_type: str, stream_id: str = ""):
        """Start timing an operation"""
        timer_key = f"{operation_id}_{operation_type}"
        self.operation_timers[timer_key] = {
            'start_time': time.time(),
            'operation_type': operation_type,
            'stream_id': stream_id
        }
    
    def end_operation_timer(self, operation_id: str, operation_type: str, additional_info: Dict = None):
        """End timing an operation and record latency"""
        timer_key = f"{operation_id}_{operation_type}"
        
        if timer_key in self.operation_timers:
            timer_info = self.operation_timers.pop(timer_key)
            latency_ms = (time.time() - timer_info['start_time']) * 1000
            
            metric = LatencyMetric(
                timestamp=time.time(),
                operation=operation_type,
                latency_ms=latency_ms,
                stream_id=timer_info['stream_id'],
                additional_info=additional_info or {}
            )
            
            self.latency_metrics.append(metric)
            self.current_stats['latency'][operation_type].append(latency_ms)
            
            # Keep only recent measurements for real-time stats
            if len(self.current_stats['latency'][operation_type]) > 100:
                self.current_stats['latency'][operation_type] = \
                    self.current_stats['latency'][operation_type][-50:]
    
    def record_audio_quality(self, stream_id: str, sample_rate: int, audio_data: bytes, 
                           additional_metrics: Dict = None):
        """Record audio quality metrics"""
        try:
            import numpy as np
            
            # Convert audio data to numpy array for analysis
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate basic audio metrics
            rms_level = float(np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)))
            peak_amplitude = float(np.max(np.abs(audio_array)))
            
            # Estimate SNR (simplified)
            signal_power = np.mean(audio_array.astype(np.float32) ** 2)
            noise_floor = 0.01 * signal_power  # Simplified estimate
            snr = 10 * np.log10(signal_power / max(noise_floor, 1e-10))
            
            metric = AudioQualityMetric(
                timestamp=time.time(),
                stream_id=stream_id,
                sample_rate=sample_rate,
                bit_depth=16,  # Assuming 16-bit
                signal_to_noise_ratio=float(snr),
                peak_amplitude=peak_amplitude,
                rms_level=rms_level,
                frequency_response=additional_metrics or {}
            )
            
            self.audio_quality_metrics.append(metric)
            
        except Exception as e:
            logger.warning(f"Error calculating audio quality metrics: {e}")
    
    def record_connection_metric(self, connection_id: str, latency_ms: float, 
                               bandwidth_usage: int = 0, packet_loss: float = 0.0):
        """Record connection quality metrics"""
        metric = ConnectionMetric(
            timestamp=time.time(),
            connection_id=connection_id,
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            bandwidth_usage=bandwidth_usage
        )
        
        self.connection_metrics.append(metric)
    
    def update_throughput(self, operation_type: str, count: int = 1):
        """Update throughput counter"""
        self.current_stats['throughput'][operation_type] += count
    
    def record_error(self, error_type: str):
        """Record error occurrence"""
        self.current_stats['error_rates'][error_type] += 1
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics"""
        current_time = time.time()
        
        # Calculate latency statistics
        latency_stats = {}
        for operation, latencies in self.current_stats['latency'].items():
            if latencies:
                latency_stats[operation] = {
                    'avg_ms': statistics.mean(latencies),
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'p95_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
                    'p99_ms': statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
                    'count': len(latencies)
                }
        
        # System resource metrics
        system_metrics = self._get_system_metrics()
        
        # Audio quality statistics
        audio_quality_stats = self._get_audio_quality_stats()
        
        # Connection statistics
        connection_stats = self._get_connection_stats()
        
        return {
            'timestamp': current_time,
            'latency': latency_stats,
            'system': system_metrics,
            'audio_quality': audio_quality_stats,
            'connections': connection_stats,
            'throughput': dict(self.current_stats['throughput']),
            'error_rates': dict(self.current_stats['error_rates']),
            'active_streams': len(self.active_streams)
        }
    
    def get_historical_metrics(self, time_range_seconds: int = 300) -> Dict[str, Any]:
        """Get historical metrics for specified time range"""
        cutoff_time = time.time() - time_range_seconds
        
        # Filter metrics by time range
        recent_latency = [m for m in self.latency_metrics if m.timestamp >= cutoff_time]
        recent_audio = [m for m in self.audio_quality_metrics if m.timestamp >= cutoff_time]
        recent_connections = [m for m in self.connection_metrics if m.timestamp >= cutoff_time]
        
        return {
            'time_range_seconds': time_range_seconds,
            'latency_metrics': [asdict(m) for m in recent_latency],
            'audio_quality_metrics': [asdict(m) for m in recent_audio],
            'connection_metrics': [asdict(m) for m in recent_connections]
        }
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available // (1024 * 1024),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': disk.free // (1024 * 1024 * 1024),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.warning(f"Error getting system metrics: {e}")
            return {}
    
    def _get_audio_quality_stats(self) -> Dict[str, Any]:
        """Get aggregated audio quality statistics"""
        if not self.audio_quality_metrics:
            return {}
        
        recent_metrics = list(self.audio_quality_metrics)[-50:]  # Last 50 measurements
        
        snr_values = [m.signal_to_noise_ratio for m in recent_metrics if m.signal_to_noise_ratio > 0]
        rms_values = [m.rms_level for m in recent_metrics if m.rms_level > 0]
        
        stats = {}
        if snr_values:
            stats['avg_snr_db'] = statistics.mean(snr_values)
            stats['min_snr_db'] = min(snr_values)
        
        if rms_values:
            stats['avg_rms_level'] = statistics.mean(rms_values)
            stats['peak_rms_level'] = max(rms_values)
        
        stats['sample_count'] = len(recent_metrics)
        return stats
    
    def _get_connection_stats(self) -> Dict[str, Any]:
        """Get connection quality statistics"""
        if not self.connection_metrics:
            return {}
        
        recent_metrics = list(self.connection_metrics)[-50:]
        
        latencies = [m.latency_ms for m in recent_metrics]
        bandwidths = [m.bandwidth_usage for m in recent_metrics if m.bandwidth_usage > 0]
        
        stats = {
            'connection_count': len(recent_metrics),
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0
        }
        
        if bandwidths:
            stats['avg_bandwidth_bps'] = statistics.mean(bandwidths)
            stats['peak_bandwidth_bps'] = max(bandwidths)
        
        return stats
    
    def _background_aggregation(self):
        """Background thread for metric aggregation and cleanup"""
        while True:
            try:
                time.sleep(30)  # Run every 30 seconds
                
                # Clear old real-time stats
                current_time = time.time()
                
                # Reset throughput counters every minute
                if int(current_time) % 60 == 0:
                    self.current_stats['throughput'].clear()
                
                # Clear old latency measurements
                for operation_type in list(self.current_stats['latency'].keys()):
                    if len(self.current_stats['latency'][operation_type]) > 200:
                        self.current_stats['latency'][operation_type] = \
                            self.current_stats['latency'][operation_type][-100:]
                
                logger.debug("Metrics aggregation completed")
                
            except Exception as e:
                logger.error(f"Error in background aggregation: {e}")

class MetricsAPI:
    """HTTP API for accessing metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
    
    async def handle_metrics_request(self, request_path: str, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Handle metrics API requests"""
        try:
            if request_path == '/api/metrics/realtime':
                return {
                    'status': 'success',
                    'data': self.metrics_collector.get_real_time_metrics()
                }
            
            elif request_path == '/api/metrics/historical':
                time_range = int(query_params.get('time_range', '300'))
                return {
                    'status': 'success',
                    'data': self.metrics_collector.get_historical_metrics(time_range)
                }
            
            elif request_path == '/api/metrics/system':
                return {
                    'status': 'success',
                    'data': self.metrics_collector._get_system_metrics()
                }
            
            elif request_path == '/api/metrics/audio':
                return {
                    'status': 'success',
                    'data': self.metrics_collector._get_audio_quality_stats()
                }
            
            else:
                return {
                    'status': 'error',
                    'message': f'Unknown metrics endpoint: {request_path}'
                }
                
        except Exception as e:
            logger.error(f"Error handling metrics request: {e}")
            return {
                'status': 'error',
                'message': f'Internal server error: {str(e)}'
            }

# Integration with WebSocket server
class MetricsIntegratedWebSocketServer:
    """WebSocket server with integrated metrics collection"""
    
    def __init__(self, enhanced_server):
        self.enhanced_server = enhanced_server
        self.metrics_collector = MetricsCollector()
        self.metrics_api = MetricsAPI(self.metrics_collector)
        
        # Integrate metrics into existing handlers
        self._integrate_metrics()
    
    def _integrate_metrics(self):
        """Integrate metrics collection into existing server"""
        # Wrap existing methods with metrics collection
        original_handle_binary = self.enhanced_server.binary_router.binary_handler.handle_binary_message
        original_handle_audio = self.enhanced_server.binary_router.message_handler.handle_audio_message
        
        async def instrumented_binary_handler(websocket, data, stt_processor, message_handler):
            # Start timer
            operation_id = f"binary_{time.time()}"
            self.metrics_collector.start_operation_timer(operation_id, "binary_decode")
            
            try:
                result = await original_handle_binary(websocket, data, stt_processor, message_handler)
                
                # Record metrics
                self.metrics_collector.update_throughput("binary_messages")
                if len(data) > 0:
                    # Record connection metrics
                    connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                    self.metrics_collector.record_connection_metric(
                        connection_id, 
                        0,  # Would need actual latency measurement
                        len(data)
                    )
                
                return result
                
            except Exception as e:
                self.metrics_collector.record_error("binary_processing")
                raise
            finally:
                self.metrics_collector.end_operation_timer(operation_id, "binary_decode")
        
        async def instrumented_audio_handler(websocket, data):
            operation_id = f"audio_{time.time()}"
            self.metrics_collector.start_operation_timer(operation_id, "stt")
            
            try:
                result = await original_handle_audio(websocket, data)
                self.metrics_collector.update_throughput("audio_processed")
                return result
            except Exception as e:
                self.metrics_collector.record_error("stt_processing")
                raise
            finally:
                self.metrics_collector.end_operation_timer(operation_id, "stt")
        
        # Replace methods with instrumented versions
        self.enhanced_server.binary_router.binary_handler.handle_binary_message = instrumented_binary_handler
        self.enhanced_server.binary_router.message_handler.handle_audio_message = instrumented_audio_handler
    
    async def handle_metrics_websocket_request(self, websocket, message):
        """Handle metrics request via WebSocket"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            
            if data.get('type') == 'get_metrics':
                metrics_type = data.get('metrics_type', 'realtime')
                
                if metrics_type == 'realtime':
                    metrics_data = self.metrics_collector.get_real_time_metrics()
                elif metrics_type == 'historical':
                    time_range = data.get('time_range', 300)
                    metrics_data = self.metrics_collector.get_historical_metrics(time_range)
                else:
                    metrics_data = {'error': 'Unknown metrics type'}
                
                response = {
                    'type': 'metrics_response',
                    'request_id': data.get('request_id'),
                    'timestamp': time.time(),
                    'data': metrics_data
                }
                
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error handling metrics WebSocket request: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            'server_metrics': self.enhanced_server.get_server_metrics(),
            'performance_metrics': self.metrics_collector.get_real_time_metrics(),
            'collection_info': {
                'total_latency_measurements': len(self.metrics_collector.latency_metrics),
                'total_audio_quality_measurements': len(self.metrics_collector.audio_quality_metrics),
                'total_connection_measurements': len(self.metrics_collector.connection_metrics)
            }
        }

# Example usage
if __name__ == "__main__":
    # This would integrate with your existing server
    collector = MetricsCollector()
    
    # Simulate some metrics
    collector.start_operation_timer("test1", "stt", "stream_123")
    time.sleep(0.1)
    collector.end_operation_timer("test1", "stt")
    
    print("Real-time metrics:", json.dumps(collector.get_real_time_metrics(), indent=2))
