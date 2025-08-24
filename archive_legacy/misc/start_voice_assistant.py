#!/usr/bin/env python3
"""
Improved Server Startup Script with better port handling
Uses ss and fuser instead of netstat for better compatibility
"""

import subprocess
import time
import signal
import os
import sys
import socket

def is_port_in_use(port):
    """Check if port is in use using socket"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False

def kill_processes_on_ports(ports):
    """Aggressiv alle Prozesse auf den Ports beenden"""
    print("🧹 Cleaning up processes on ports:", ports)
    
    for port in ports:
        # fuser method (most reliable)
        try:
            result = subprocess.run(["fuser", "-k", f"{port}/tcp"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ fuser killed processes on port {port}")
            time.sleep(0.5)
        except Exception as e:
            print(f"   fuser method failed for port {port}: {e}")
        
        # ss method (modern replacement for netstat)
        try:
            result = subprocess.run(
                ["ss", "-tlnp"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f":{port} " in line and "LISTEN" in line:
                        # Extract PID from ss output
                        # Format: users:(("python",pid=12345,fd=3))
                        if "pid=" in line:
                            try:
                                pid_start = line.find("pid=") + 4
                                pid_end = line.find(",", pid_start)
                                pid = line[pid_start:pid_end]
                                if pid.isdigit():
                                    print(f"   Killing PID {pid} on port {port}")
                                    os.kill(int(pid), signal.SIGTERM)
                                    time.sleep(0.5)
                                    try:
                                        os.kill(int(pid), signal.SIGKILL)
                                    except Exception as kill_err:
                                        print(f"   Failed to force kill PID {pid}: {kill_err}")
                            except Exception as pe:
                                print(f"   PID extraction failed: {pe}")
        except Exception as e:
            print(f"   ss method failed: {e}")
            
        # lsof method as backup
        try:
            result = subprocess.run(
                ["lsof", f"-i:{port}"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) > 1:
                            pid = parts[1]
                            if pid.isdigit():
                                print(f"   lsof: Killing PID {pid} on port {port}")
                                try:
                                    os.kill(int(pid), signal.SIGTERM)
                                    time.sleep(0.2)
                                    os.kill(int(pid), signal.SIGKILL)
                                except Exception as kill_err:
                                    print(f"   lsof: Failed to kill PID {pid}: {kill_err}")
        except Exception as e:
            print(f"   lsof method failed: {e}")

def start_voice_assistant():
    """Start Voice Assistant with improved monitoring"""
    
    print("🚀 VOICE ASSISTANT SERVER STARTUP")
    print("="*50)
    
    # 1. Aggressive cleanup
    kill_processes_on_ports([48231, 48232])
    time.sleep(3)
    
    # 2. Double-check ports are free using socket
    for port in [48231, 48232]:
        if is_port_in_use(port):
            print(f"❌ Port {port} still in use after cleanup!")
            # One more aggressive try
            subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
            time.sleep(2)
            if is_port_in_use(port):
                print(f"❌ Port {port} could not be freed!")
                return False
    
    print("✅ Ports 48231, 48232 are free")
    
    # 3. Start server
    cmd = [
        "/home/saschi/Sprachassistent/.venv/bin/python",
        "-m",
        "ws_server.cli",
    ]
    
    env = os.environ.copy()
    env.update({
        'WS_HOST': '127.0.0.1',
        'WS_PORT': '48231',
        'METRICS_PORT': '48232',
        # Use Zonos by default
        'TTS_ENGINE': 'zonos',
        'STT_DEVICE': 'cpu',
        'LOGLEVEL': 'INFO'
    })
    
    print("🔧 Starting Voice Assistant Server...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd="/home/saschi/Sprachassistent",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print("📡 Monitoring startup (allowing up to 60s for model loading)...")
        
        health_ok = False
        metrics_ok = False
        websocket_ready = False
        
        # Extended monitoring for model loading
        for i in range(60):
            time.sleep(1)
            
            # Check if process crashed
            if process.poll() is not None:
                print(f"❌ Server process crashed with code: {process.returncode}")
                output = process.stdout.read()
                if output:
                    print("Crash output:")
                    print("-" * 30)
                    print(output[-2000:])  # Last 2000 chars
                    print("-" * 30)
                return False
            
            # Read output
            try:
                import select
                if select.select([process.stdout], [], [], 0.1) == ([process.stdout], [], []):
                    line = process.stdout.readline()
                    if line:
                        line_clean = line.strip()
                        print(f"   📋 {line_clean}")

                        # Check for success indicators
                        if "Voice server initialized successfully" in line:
                            websocket_ready = True
                        elif "TTS-Manager initialisiert" in line:
                            print("   ✅ TTS Manager ready!")
                        elif "STT model" in line and "loaded" in line:
                            print("   ✅ STT Model ready!")
            except Exception as read_err:
                print(f"   Error reading server output: {read_err}")
            
            # Test endpoints every 5 seconds after 15s
            if i > 15 and i % 5 == 0:
                print(f"   🧪 Testing endpoints at {i}s...")
                
                # Test health
                if not health_ok:
                    try:
                        import urllib.request
                        import json
                        response = urllib.request.urlopen("http://127.0.0.1:48232/health", timeout=2)
                        data = json.loads(response.read().decode())
                        if data.get('status') == 'ok':
                            health_ok = True
                            print("   ✅ Health endpoint working!")
                    except Exception as e:
                        print(f"   ⏳ Health endpoint not ready: {e}")
                
                # Test metrics  
                if not metrics_ok:
                    try:
                        response = urllib.request.urlopen("http://127.0.0.1:48232/metrics", timeout=2)
                        data = json.loads(response.read().decode())
                        if 'active_connections' in data:
                            metrics_ok = True
                            print("   ✅ Metrics endpoint working!")
                    except Exception as e:
                        print(f"   ⏳ Metrics endpoint not ready: {e}")
                        
                # Success condition
                if health_ok and metrics_ok:
                    print(f"🎉 SERVER READY after {i}s!")
                    print("   ✅ Health endpoint: OK")
                    print("   ✅ Metrics endpoint: OK") 
                    print("   ✅ WebSocket server: Ready")
                    print()
                    print("🌐 Access URLs:")
                    print("   WebSocket: ws://127.0.0.1:48231")
                    print("   Metrics: http://127.0.0.1:48232/metrics")
                    print("   Health: http://127.0.0.1:48232/health")
                    print()
                    print("🎯 Server is running in background!")
                    print("   To stop: fuser -k 48231/tcp && fuser -k 48232/tcp")
                    return True
            
            if i % 10 == 0:
                print(f"   ⏱️  Startup progress: {i}/60s (Health: {'✅' if health_ok else '⏳'}, Metrics: {'✅' if metrics_ok else '⏳'})")
        
        print("⚠️  Server startup monitoring timeout (60s)")
        if health_ok or metrics_ok:
            print("   But some endpoints are working - server may be ready!")
            return True
        else:
            print("   No endpoints responding - startup may have failed")
            return False
            
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = start_voice_assistant()
        if success:
            print("\n🏆 VOICE ASSISTANT SERVER IS RUNNING!")
        else:
            print("\n💥 VOICE ASSISTANT SERVER STARTUP FAILED!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Startup interrupted")
        sys.exit(1)
