#!/usr/bin/env python3
"""
Performance Monitor für WebSocket-Server
Überwacht Speicher, CPU und Verbindungen
"""

import psutil
import asyncio
import time
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.connections_count = 0
        self.total_requests = 0
        self.error_count = 0
        self.metrics_history: List[Dict] = []
        self.max_history_size = 100
        
    def track_connection(self, connected: bool = True):
        """Track WebSocket connections"""
        if connected:
            self.connections_count += 1
        else:
            self.connections_count = max(0, self.connections_count - 1)
    
    def track_request(self, success: bool = True):
        """Track request statistics"""
        self.total_requests += 1
        if not success:
            self.error_count += 1
    
    def get_system_metrics(self) -> Dict:
        """Get current system performance metrics"""
        process = psutil.Process()
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': time.time() - self.start_time,
            'memory': {
                'used_mb': process.memory_info().rss / 1024 / 1024,
                'percent': process.memory_percent(),
                'system_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'system_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024
            },
            'cpu': {
                'process_percent': process.cpu_percent(),
                'system_percent': psutil.cpu_percent(),
                'core_count': psutil.cpu_count()
            },
            'connections': {
                'active': self.connections_count,
                'total_requests': self.total_requests,
                'error_count': self.error_count,
                'error_rate': (self.error_count / max(1, self.total_requests)) * 100
            },
            'disk': {
                'used_percent': psutil.disk_usage('/').percent,
                'free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024
            }
        }
        
        # Add to history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
        
        return metrics
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary and health status"""
        current_metrics = self.get_system_metrics()
        
        # Calculate health score (0-100)
        health_score = 100
        warnings = []
        
        # Memory checks
        if current_metrics['memory']['percent'] > 80:
            health_score -= 20
            warnings.append("High memory usage")
        
        # CPU checks
        if current_metrics['cpu']['process_percent'] > 70:
            health_score -= 15
            warnings.append("High CPU usage")
        
        # Error rate checks
        if current_metrics['connections']['error_rate'] > 10:
            health_score -= 25
            warnings.append("High error rate")
        
        # Disk space checks
        if current_metrics['disk']['used_percent'] > 90:
            health_score -= 20
            warnings.append("Low disk space")
        
        # Determine status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "warning"
        else:
            status = "critical"
        
        return {
            'status': status,
            'health_score': max(0, health_score),
            'warnings': warnings,
            'metrics': current_metrics,
            'uptime_formatted': self._format_uptime(current_metrics['uptime_seconds'])
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def log_performance_alert(self, threshold_type: str, value: float):
        """Log performance alerts"""
        logger.warning(f"Performance Alert: {threshold_type} = {value:.2f}")
        
    async def monitor_loop(self, interval: int = 60):
        """Continuous monitoring loop"""
        while True:
            try:
                summary = self.get_performance_summary()
                
                if summary['status'] != 'healthy':
                    logger.warning(f"Performance Status: {summary['status']} (Score: {summary['health_score']})")
                    for warning in summary['warnings']:
                        logger.warning(f"  - {warning}")
                
                # Log critical metrics every hour
                if int(time.time()) % 3600 < interval:
                    logger.info(f"Performance Summary: {summary['status']} | "
                              f"Memory: {summary['metrics']['memory']['percent']:.1f}% | "
                              f"CPU: {summary['metrics']['cpu']['process_percent']:.1f}% | "
                              f"Connections: {summary['metrics']['connections']['active']} | "
                              f"Uptime: {summary['uptime_formatted']}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(interval)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
