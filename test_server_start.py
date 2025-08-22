#!/usr/bin/env python3
"""
Einfacher Test für den Voice Assistant Server Start
"""

import subprocess
import sys
import time

def test_server_start():
    """Teste Server-Start mit detaillierter Ausgabe"""
    
    print("🧪 TESTING Voice Assistant Server Start")
    print("="*50)
    
    # Kill existing processes
    print("1️⃣  Killing existing processes...")
    subprocess.run(["fuser", "-k", "48231/tcp"], capture_output=True)
    subprocess.run(["fuser", "-k", "48232/tcp"], capture_output=True)
    time.sleep(2)
    
    # Start server
    print("2️⃣  Starting server...")
    cmd = [
        "/home/saschi/Sprachassistent/.venv/bin/python",
        "-m",
        "ws_server.cli",
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run server in background and capture output
        process = subprocess.Popen(
            cmd,
            cwd="/home/saschi/Sprachassistent",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        print("3️⃣  Monitoring server startup...")
        
        # Monitor for 10 seconds
        for i in range(10):
            time.sleep(1)
            if process.poll() is not None:
                # Process has terminated
                print(f"❌ Server terminated with code: {process.returncode}")
                output = process.stdout.read()
                print("Server output:")
                print("-" * 30)
                print(output)
                print("-" * 30)
                return False
                
            print(f"   Startup monitoring: {i+1}/10 seconds...")
            
            # Check if we can read some output
            try:
                # Non-blocking read
                import select
                if select.select([process.stdout], [], [], 0) == ([process.stdout], [], []):
                    line = process.stdout.readline()
                    if line:
                        print(f"   📋 {line.strip()}")
            except:
                pass
        
        print("4️⃣  Testing endpoints...")
        
        # Test metrics endpoint
        import urllib.request
        import json
        
        try:
            response = urllib.request.urlopen("http://127.0.0.1:48232/health", timeout=5)
            data = response.read().decode()
            health_data = json.loads(data)
            print(f"✅ Health endpoint working: {health_data}")
        except Exception as e:
            print(f"❌ Health endpoint failed: {e}")
            
        try:
            response = urllib.request.urlopen("http://127.0.0.1:48232/metrics", timeout=5)
            data = response.read().decode()
            metrics_data = json.loads(data)
            print(f"✅ Metrics endpoint working: Keys={list(metrics_data.keys())}")
        except Exception as e:
            print(f"❌ Metrics endpoint failed: {e}")
        
        print("5️⃣  Stopping server...")
        process.terminate()
        time.sleep(2)
        if process.poll() is None:
            process.kill()
            
        print("✅ TEST COMPLETED")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_server_start()
    sys.exit(0 if success else 1)
