#!/usr/bin/env python3
"""
Final Test für den reparierten Voice Assistant Server
"""

import subprocess
import time
import sys
import signal
import os

def run_test():
    """Führe vollständigen Server-Test durch"""
    
    print("🎯 FINAL VOICE ASSISTANT SERVER TEST")
    print("="*60)
    
    # 1. Kill existing processes
    print("1️⃣  Cleaning up existing processes...")
    subprocess.run(["fuser", "-k", "48231/tcp"], capture_output=True)
    subprocess.run(["fuser", "-k", "48232/tcp"], capture_output=True)
    time.sleep(2)
    
    # 2. Start server with timeout
    print("2️⃣  Starting server with detailed monitoring...")
    
    cmd = [
        "/home/saschi/Sprachassistent/.venv/bin/python",
        "/home/saschi/Sprachassistent/backend/ws-server/ws-server.py"
    ]
    
    env = os.environ.copy()
    env.update({
        'WS_HOST': '127.0.0.1',
        'WS_PORT': '48231', 
        'METRICS_PORT': '48232',
        'LOGLEVEL': 'INFO'
        # Use actual .env settings for TTS_ENGINE and STT_DEVICE
    })
    
    print(f"   Command: {' '.join(cmd)}")
    print(f"   Working Dir: /home/saschi/Sprachassistent")
    
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
        
        print("3️⃣  Monitoring server output...")
        
        startup_success = False
        metrics_ready = False
        websocket_ready = False
        
        # Monitor for 60 seconds (Zonos model loading can take time)
        for i in range(60):
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                print(f"❌ Server process terminated with code: {process.returncode}")
                # Read any remaining output
                output = process.stdout.read()
                if output:
                    print("Final output:")
                    print("-" * 40)
                    print(output)
                    print("-" * 40)
                return False
                
            # Try to read output
            try:
                import select
                if select.select([process.stdout], [], [], 0.1) == ([process.stdout], [], []):
                    line = process.stdout.readline()
                    if line:
                        print(f"   📋 {line.strip()}")
                        
                        # Check for success indicators
                        if "✅ Server initialization completed" in line:
                            startup_success = True
                        elif "✅ Metrics API started successfully" in line:
                            metrics_ready = True
                        elif "🚀 Optimized Voice Server" in line:
                            websocket_ready = True
                        elif "✨ Server startup completed successfully!" in line:
                            print(f"🎉 Server startup completed! ({i+1}s)")
                            break
                            
            except Exception as e:
                print(f"   ⚠️  Output read error: {e}")
            
            print(f"   ⏱️  Monitoring: {i+1}/60s (Init: {'✅' if startup_success else '⏳'}, "
                  f"Metrics: {'✅' if metrics_ready else '⏳'}, WS: {'✅' if websocket_ready else '⏳'})")
        
        # 4. Test endpoints if server seems to be running
        if process.poll() is None:
            print("4️⃣  Testing HTTP endpoints...")
            
            # Wait a bit more for server to be fully ready
            time.sleep(3)

            import urllib.request
            import json
            import asyncio
            import websockets

            # Test health endpoint
            try:
                response = urllib.request.urlopen("http://127.0.0.1:48232/health", timeout=5)
                data = response.read().decode()
                health_data = json.loads(data)
                print(f"   ✅ Health endpoint: {health_data.get('status', 'unknown')}")
                startup_success = True
            except Exception as e:
                print(f"   ❌ Health endpoint failed: {e}")

            # Test metrics endpoint
            try:
                response = urllib.request.urlopen("http://127.0.0.1:48232/metrics", timeout=5)
                data = response.read().decode()
                metrics_data = json.loads(data)
                conn_count = metrics_data.get('active_connections', 'unknown')
                print(f"   ✅ Metrics endpoint: {conn_count} active connections")
                metrics_ready = True
            except Exception as e:
                print(f"   ❌ Metrics endpoint failed: {e}")

            # Test WebSocket connection
            try:
                async def check_ws():
                    uri = "ws://127.0.0.1:48231"
                    async with websockets.connect(uri):
                        return True

                asyncio.get_event_loop().run_until_complete(check_ws())
                print("   ✅ WebSocket endpoint: connection successful")
                websocket_ready = True
            except Exception as e:
                print(f"   ❌ WebSocket endpoint failed: {e}")
        
        # 5. Cleanup
        print("5️⃣  Stopping server...")
        if process.poll() is None:
            process.terminate()
            time.sleep(3)
            if process.poll() is None:
                process.kill()
                time.sleep(1)
        
        print("6️⃣  Test summary...")
        if startup_success and (metrics_ready or websocket_ready):
            print("🎉 SUCCESS: Server can start and initialize properly!")
            print("   ✅ Server startup completed")
            if metrics_ready:
                print("   ✅ Metrics API working") 
            if websocket_ready:
                print("   ✅ WebSocket server working")
            return True
        else:
            print("❌ PARTIAL SUCCESS: Server started but some components failed")
            print(f"   Startup: {'✅' if startup_success else '❌'}")
            print(f"   Metrics: {'✅' if metrics_ready else '❌'}")
            print(f"   WebSocket: {'✅' if websocket_ready else '❌'}")
            return False
            
    except Exception as e:
        print(f"💥 Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    try:
        success = run_test()
        if success:
            print("\n🏆 VOICE ASSISTANT SERVER REPAIRS SUCCESSFUL!")
            print("The server should now start properly.")
            print("\nTo start manually:")
            print("cd /home/saschi/Sprachassistent")
            print("source .venv/bin/activate")
            print("python backend/ws-server/ws-server.py")
        else:
            print("\n🔧 VOICE ASSISTANT SERVER NEEDS MORE WORK")
            print("Check the detailed output above for specific issues.")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        sys.exit(1)
