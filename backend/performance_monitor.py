#!/usr/bin/env python3
"""
🔍 Performance Monitor für Voice Assistant Backend
Überwacht Audio-Latenz, Memory-Usage und Connection-Metriken
"""

import asyncio
import aiohttp
import time
import json
import psutil
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import argparse

@dataclass
class PerformanceMetrics:
    timestamp: float
    active_connections: int
    total_connections: int
    messages_processed: int
    audio_streams_processed: int
    uptime_seconds: float
    active_audio_streams: int
    processing_queue_size: int
    
    # System metrics
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    network_bytes_sent: int
    network_bytes_recv: int

class VoiceAssistantMonitor:
    def __init__(self, server_url: str = "http://localhost:8123", interval: int = 5):
        self.server_url = server_url
        self.interval = interval
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 1000  # Keep last 1000 measurements
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    async def collect_metrics(self) -> Optional[PerformanceMetrics]:
        """Collect current performance metrics"""
        try:
            # Get server metrics via HTTP endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/metrics") as response:
                    if response.status == 200:
                        server_stats = await response.json()
                    else:
                        self.logger.warning(f"Server metrics not available: {response.status}")
                        server_stats = {}
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            network = psutil.net_io_counters()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                active_connections=server_stats.get('active_connections', 0),
                total_connections=server_stats.get('total_connections', 0),
                messages_processed=server_stats.get('messages_processed', 0),
                audio_streams_processed=server_stats.get('audio_streams_processed', 0),
                uptime_seconds=server_stats.get('uptime_seconds', 0),
                active_audio_streams=server_stats.get('active_audio_streams', 0),
                processing_queue_size=server_stats.get('processing_queue_size', 0),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return None
            
    def analyze_performance(self) -> Dict:
        """Analyze performance trends"""
        if len(self.metrics_history) < 2:
            return {"status": "insufficient_data"}
            
        latest = self.metrics_history[-1]
        previous = self.metrics_history[-2]
        
        # Calculate rates
        time_diff = latest.timestamp - previous.timestamp
        message_rate = (latest.messages_processed - previous.messages_processed) / time_diff
        
        # Performance assessment
        performance_score = 100
        issues = []
        
        if latest.cpu_percent > 80:
            performance_score -= 20
            issues.append("High CPU usage")
            
        if latest.memory_percent > 80:
            performance_score -= 20
            issues.append("High memory usage")
            
        if latest.processing_queue_size > 10:
            performance_score -= 15
            issues.append("High processing queue")
            
        if message_rate < 1 and latest.active_connections > 0:
            performance_score -= 15
            issues.append("Low message processing rate")
            
        # Performance category
        if performance_score >= 90:
            category = "excellent"
        elif performance_score >= 70:
            category = "good"
        elif performance_score >= 50:
            category = "fair"
        else:
            category = "poor"
            
        return {
            "status": "analyzed",
            "performance_score": performance_score,
            "category": category,
            "issues": issues,
            "message_rate": round(message_rate, 2),
            "latest_metrics": asdict(latest)
        }
        
    def print_metrics(self, metrics: PerformanceMetrics, analysis: Dict):
        """Print formatted metrics to console"""
        print(f"\n{'='*60}")
        print(f"📊 Voice Assistant Performance Monitor")
        print(f"{'='*60}")
        print(f"⏰ Time: {time.strftime('%H:%M:%S', time.localtime(metrics.timestamp))}")
        print(f"")
        print(f"🔗 Connections:")
        print(f"   Active: {metrics.active_connections}")
        print(f"   Total:  {metrics.total_connections}")
        print(f"")
        print(f"🎵 Audio Streams:")
        print(f"   Active:    {metrics.active_audio_streams}")
        print(f"   Processed: {metrics.audio_streams_processed}")
        print(f"   Queue:     {metrics.processing_queue_size}")
        print(f"")
        print(f"💻 System Resources:")
        print(f"   CPU:    {metrics.cpu_percent:.1f}%")
        print(f"   Memory: {metrics.memory_percent:.1f}% ({metrics.memory_mb:.0f} MB)")
        print(f"")
        print(f"📈 Performance:")
        print(f"   Score:    {analysis.get('performance_score', 0)}/100")
        print(f"   Category: {analysis.get('category', 'unknown').upper()}")
        
        if analysis.get('issues'):
            print(f"   Issues:   {', '.join(analysis['issues'])}")
            
        if analysis.get('message_rate'):
            print(f"   Msg Rate: {analysis['message_rate']:.1f}/sec")
            
        print(f"")
        print(f"⏱️  Uptime: {metrics.uptime_seconds/3600:.1f}h")
        
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("🔍 Starting Voice Assistant Performance Monitor")
        
        try:
            while True:
                # Collect metrics
                metrics = await self.collect_metrics()
                
                if metrics:
                    # Store in history
                    self.metrics_history.append(metrics)
                    
                    # Limit history size
                    if len(self.metrics_history) > self.max_history:
                        self.metrics_history.pop(0)
                    
                    # Analyze performance
                    analysis = self.analyze_performance()
                    
                    # Print to console
                    self.print_metrics(metrics, analysis)
                    
                    # Log warnings for performance issues
                    if analysis.get('category') in ['fair', 'poor']:
                        self.logger.warning(f"Performance degraded: {analysis.get('category')} - {analysis.get('issues')}")
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitor stopped by user")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")
            
    def export_metrics(self, filename: str):
        """Export metrics to JSON file"""
        try:
            data = {
                'export_time': time.time(),
                'metrics_count': len(self.metrics_history),
                'metrics': [asdict(m) for m in self.metrics_history]
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Metrics exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Voice Assistant Performance Monitor')
    parser.add_argument('--server', default='http://localhost:8123', help='Server URL')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds')
    parser.add_argument('--export', help='Export metrics to JSON file on exit')
    
    args = parser.parse_args()
    
    monitor = VoiceAssistantMonitor(args.server, args.interval)
    
    try:
        await monitor.monitor_loop()
    finally:
        if args.export:
            monitor.export_metrics(args.export)

if __name__ == "__main__":
    asyncio.run(main())
