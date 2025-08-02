#!/usr/bin/env python3
"""
⚡ Voice Assistant Performance Test Suite
Tests Audio-Latenz, Concurrent Connections und System Performance
"""

import asyncio
import websockets
import json
import time
import base64
import numpy as np
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict
import logging

@dataclass
class LatencyTest:
    test_type: str
    latency_ms: float
    success: bool
    timestamp: float
    error: str = None

class PerformanceTester:
    def __init__(self, server_url: str = "ws://localhost:8123"):
        self.server_url = server_url
        self.results: List[LatencyTest] = []
        self.logger = logging.getLogger(__name__)
        
    async def test_websocket_latency(self, iterations: int = 10) -> List[float]:
        """Test WebSocket ping-pong latency"""
        latencies = []
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.logger.info(f"🏓 Testing WebSocket latency ({iterations} iterations)")
                
                for i in range(iterations):
                    start_time = time.time()
                    
                    # Send ping
                    ping_message = {
                        'type': 'ping',
                        'timestamp': start_time
                    }
                    await websocket.send(json.dumps(ping_message))
                    
                    # Wait for pong
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    end_time = time.time()
                    
                    try:
                        data = json.loads(response)
                        if data.get('type') == 'pong':
                            latency = (end_time - start_time) * 1000  # Convert to ms
                            latencies.append(latency)
                            
                            self.results.append(LatencyTest(
                                test_type='websocket_ping',
                                latency_ms=latency,
                                success=True,
                                timestamp=start_time
                            ))
                            
                            self.logger.debug(f"Ping {i+1}: {latency:.1f}ms")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid response for ping {i+1}")
                        
                    # Wait between tests
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"WebSocket latency test failed: {e}")
            
        return latencies
        
    async def test_audio_processing_latency(self, iterations: int = 5) -> List[float]:
        """Test audio processing latency with fake audio data"""
        latencies = []
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.logger.info(f"🎵 Testing audio processing latency ({iterations} iterations)")
                
                for i in range(iterations):
                    start_time = time.time()
                    
                    # Start audio stream
                    await websocket.send(json.dumps({
                        'type': 'start_audio_stream'
                    }))
                    
                    # Wait for stream confirmation
                    response = await websocket.recv()
                    stream_data = json.loads(response)
                    stream_id = stream_data.get('stream_id')
                    
                    if stream_id:
                        # Send fake audio chunk (1 second of silence)
                        fake_audio = self.generate_fake_audio(duration_ms=1000)
                        await websocket.send(json.dumps({
                            'type': 'audio_chunk',
                            'stream_id': stream_id,
                            'chunk': fake_audio,
                            'sequence': 0
                        }))
                        
                        # End stream
                        await websocket.send(json.dumps({
                            'type': 'end_audio_stream',
                            'stream_id': stream_id
                        }))
                        
                        # Wait for response
                        while True:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            data = json.loads(response)
                            
                            if data.get('type') == 'response':
                                end_time = time.time()
                                latency = (end_time - start_time) * 1000
                                latencies.append(latency)
                                
                                self.results.append(LatencyTest(
                                    test_type='audio_processing',
                                    latency_ms=latency,
                                    success=True,
                                    timestamp=start_time
                                ))
                                
                                self.logger.debug(f"Audio processing {i+1}: {latency:.0f}ms")
                                break
                                
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            self.logger.error(f"Audio processing test failed: {e}")
            
        return latencies
        
    def generate_fake_audio(self, duration_ms: int = 1000, sample_rate: int = 16000) -> str:
        """Generate fake audio data (silence) for testing"""
        samples = int(duration_ms * sample_rate / 1000)
        
        # Create silence with occasional small variations to simulate speech
        audio_data = np.zeros(samples, dtype=np.int16)
        
        # Add some random noise to simulate actual audio
        noise = np.random.normal(0, 50, samples).astype(np.int16)
        audio_data = audio_data + noise
        
        # Convert to base64
        audio_bytes = audio_data.tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')
        
    async def test_concurrent_connections(self, connections: int = 10, duration: int = 30) -> Dict:
        """Test concurrent connection handling"""
        self.logger.info(f"🔗 Testing {connections} concurrent connections for {duration}s")
        
        results = {
            'connections_attempted': connections,
            'connections_successful': 0,
            'connections_failed': 0,
            'total_messages': 0,
            'test_duration': duration
        }
        
        async def single_connection_test(connection_id: int):
            try:
                async with websockets.connect(self.server_url) as websocket:
                    results['connections_successful'] += 1
                    
                    # Send periodic pings
                    start_time = time.time()
                    message_count = 0
                    
                    while time.time() - start_time < duration:
                        await websocket.send(json.dumps({
                            'type': 'ping',
                            'timestamp': time.time(),
                            'connection_id': connection_id
                        }))
                        
                        # Try to receive response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            message_count += 1
                        except asyncio.TimeoutError:
                            pass
                            
                        await asyncio.sleep(1)
                        
                    results['total_messages'] += message_count
                    
            except Exception as e:
                self.logger.warning(f"Connection {connection_id} failed: {e}")
                results['connections_failed'] += 1
                
        # Run all connections concurrently
        tasks = [single_connection_test(i) for i in range(connections)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
        
    def analyze_results(self) -> Dict:
        """Analyze test results and provide recommendations"""
        if not self.results:
            return {"status": "no_data"}
            
        # Group by test type
        ping_tests = [r for r in self.results if r.test_type == 'websocket_ping' and r.success]
        audio_tests = [r for r in self.results if r.test_type == 'audio_processing' and r.success]
        
        analysis = {
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': sum(1 for r in self.results if r.success),
                'failed_tests': sum(1 for r in self.results if not r.success)
            }
        }
        
        # Analyze ping latency
        if ping_tests:
            ping_latencies = [r.latency_ms for r in ping_tests]
            analysis['websocket_latency'] = {
                'average_ms': statistics.mean(ping_latencies),
                'median_ms': statistics.median(ping_latencies),
                'min_ms': min(ping_latencies),
                'max_ms': max(ping_latencies),
                'std_dev': statistics.stdev(ping_latencies) if len(ping_latencies) > 1 else 0,
                'test_count': len(ping_latencies)
            }
            
        # Analyze audio processing latency
        if audio_tests:
            audio_latencies = [r.latency_ms for r in audio_tests]
            analysis['audio_processing'] = {
                'average_ms': statistics.mean(audio_latencies),
                'median_ms': statistics.median(audio_latencies),
                'min_ms': min(audio_latencies),
                'max_ms': max(audio_latencies),
                'std_dev': statistics.stdev(audio_latencies) if len(audio_latencies) > 1 else 0,
                'test_count': len(audio_latencies)
            }
            
        # Performance recommendations
        recommendations = []
        
        if ping_tests:
            avg_ping = statistics.mean([r.latency_ms for r in ping_tests])
            if avg_ping > 100:
                recommendations.append("High WebSocket latency detected - check network connection")
            elif avg_ping < 20:
                recommendations.append("Excellent WebSocket latency")
                
        if audio_tests:
            avg_audio = statistics.mean([r.latency_ms for r in audio_tests])
            if avg_audio > 2000:
                recommendations.append("High audio processing latency - consider faster STT model")
            elif avg_audio < 1000:
                recommendations.append("Good audio processing performance")
                
        analysis['recommendations'] = recommendations
        
        return analysis
        
    def print_results(self, analysis: Dict, concurrent_results: Dict = None):
        """Print formatted test results"""
        print(f"\n{'='*70}")
        print(f"⚡ Voice Assistant Performance Test Results")
        print(f"{'='*70}")
        
        # Summary
        summary = analysis.get('summary', {})
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {summary.get('total_tests', 0)}")
        print(f"   Successful:  {summary.get('successful_tests', 0)}")
        print(f"   Failed:      {summary.get('failed_tests', 0)}")
        print()
        
        # WebSocket Latency
        if 'websocket_latency' in analysis:
            ws = analysis['websocket_latency']
            print(f"🏓 WebSocket Latency:")
            print(f"   Average:  {ws['average_ms']:.1f}ms")
            print(f"   Median:   {ws['median_ms']:.1f}ms")
            print(f"   Range:    {ws['min_ms']:.1f}ms - {ws['max_ms']:.1f}ms")
            print(f"   Std Dev:  {ws['std_dev']:.1f}ms")
            print()
            
        # Audio Processing
        if 'audio_processing' in analysis:
            audio = analysis['audio_processing']
            print(f"🎵 Audio Processing Latency:")
            print(f"   Average:  {audio['average_ms']:.0f}ms")
            print(f"   Median:   {audio['median_ms']:.0f}ms")
            print(f"   Range:    {audio['min_ms']:.0f}ms - {audio['max_ms']:.0f}ms")
            print(f"   Std Dev:  {audio['std_dev']:.0f}ms")
            print()
            
        # Concurrent connections
        if concurrent_results:
            print(f"🔗 Concurrent Connection Test:")
            print(f"   Attempted:   {concurrent_results['connections_attempted']}")
            print(f"   Successful:  {concurrent_results['connections_successful']}")
            print(f"   Failed:      {concurrent_results['connections_failed']}")
            print(f"   Messages:    {concurrent_results['total_messages']}")
            print(f"   Duration:    {concurrent_results['test_duration']}s")
            
            success_rate = (concurrent_results['connections_successful'] / 
                          concurrent_results['connections_attempted'] * 100)
            print(f"   Success Rate: {success_rate:.1f}%")
            print()
            
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"💡 Recommendations:")
            for rec in recommendations:
                print(f"   • {rec}")
        print()

async def main():
    parser = argparse.ArgumentParser(description='Voice Assistant Performance Tester')
    parser.add_argument('--server', default='ws://localhost:8123', help='WebSocket server URL')
    parser.add_argument('--ping-tests', type=int, default=10, help='Number of ping tests')
    parser.add_argument('--audio-tests', type=int, default=3, help='Number of audio tests')
    parser.add_argument('--concurrent', type=int, default=0, help='Test concurrent connections')
    parser.add_argument('--duration', type=int, default=30, help='Concurrent test duration')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    tester = PerformanceTester(args.server)
    
    print(f"🚀 Starting Voice Assistant Performance Tests")
    print(f"📍 Server: {args.server}")
    print()
    
    # Run tests
    try:
        if args.ping_tests > 0:
            await tester.test_websocket_latency(args.ping_tests)
            
        if args.audio_tests > 0:
            await tester.test_audio_processing_latency(args.audio_tests)
            
        concurrent_results = None
        if args.concurrent > 0:
            concurrent_results = await tester.test_concurrent_connections(
                args.concurrent, args.duration
            )
            
        # Analyze and print results
        analysis = tester.analyze_results()
        tester.print_results(analysis, concurrent_results)
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
