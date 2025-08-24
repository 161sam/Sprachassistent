#!/bin/bash
# Quick commands for Voice Assistant management

echo "🎮 VOICE ASSISTANT QUICK COMMANDS"
echo "================================="
echo

case "$1" in
    "start")
        echo "🚀 Starting Voice Assistant Server..."
        python3 /home/saschi/Sprachassistent/start_voice_assistant.py
        ;;
    "stop") 
        echo "🛑 Stopping Voice Assistant Server..."
        fuser -k 48231/tcp 2>/dev/null || true
        fuser -k 48232/tcp 2>/dev/null || true
        echo "✅ Server stopped"
        ;;
    "status")
        echo "📊 Voice Assistant Status:"
        echo
        echo "🔍 Checking ports..."
        if netstat -tln | grep -q ":48231 "; then
            echo "   ✅ WebSocket Server (48231): RUNNING"
        else
            echo "   ❌ WebSocket Server (48231): STOPPED"
        fi
        
        if netstat -tln | grep -q ":48232 "; then
            echo "   ✅ Metrics API (48232): RUNNING"
        else
            echo "   ❌ Metrics API (48232): STOPPED"
        fi
        
        echo
        echo "🧪 Testing endpoints..."
        if curl -s http://127.0.0.1:48232/health >/dev/null 2>&1; then
            echo "   ✅ Health endpoint: OK"
        else
            echo "   ❌ Health endpoint: FAILED"
        fi
        
        if curl -s http://127.0.0.1:48232/metrics >/dev/null 2>&1; then
            echo "   ✅ Metrics endpoint: OK"  
        else
            echo "   ❌ Metrics endpoint: FAILED"
        fi
        ;;
    "logs")
        echo "📋 Voice Assistant Logs (last 50 lines):"
        if [ -f /tmp/va.log ]; then
            tail -n 50 /tmp/va.log
        else
            echo "   No log file found at /tmp/va.log"
        fi
        ;;
    "install-kokoro")
        echo "📦 Installing Kokoro TTS..."
        cd /home/saschi/Sprachassistent
        source .venv/bin/activate
        pip install kokoro-onnx soundfile
        
        echo "📥 Downloading Kokoro models..."
        mkdir -p models/kokoro
        cd models/kokoro
        
        if [ ! -f kokoro-v1.0.onnx ]; then
            wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
        fi
        
        if [ ! -f voices-v1.0.bin ]; then
            wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
        fi
        
        echo "✅ Kokoro TTS installation completed!"
        echo "   To use Kokoro, set TTS_ENGINE=kokoro in your .env"
        ;;
    "test")
        echo "🧪 Testing Voice Assistant..."
        python3 /home/saschi/Sprachassistent/final_server_test.py
        ;;
    "health")
        echo "🏥 Health Check:"
        curl -s http://127.0.0.1:48232/health | jq . 2>/dev/null || curl -s http://127.0.0.1:48232/health
        ;;
    "metrics")  
        echo "📊 Metrics:"
        curl -s http://127.0.0.1:48232/metrics | jq . 2>/dev/null || curl -s http://127.0.0.1:48232/metrics
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|install-kokoro|test|health|metrics}"
        echo
        echo "Commands:"
        echo "  start         - Start the Voice Assistant server"
        echo "  stop          - Stop the Voice Assistant server"  
        echo "  status        - Show server status and test endpoints"
        echo "  logs          - Show recent server logs"
        echo "  install-kokoro- Install Kokoro TTS engine"
        echo "  test          - Run full server test"
        echo "  health        - Quick health check"
        echo "  metrics       - Show server metrics"
        echo
        echo "Examples:"
        echo "  $0 start      # Start server"
        echo "  $0 status     # Check if running"
        echo "  $0 stop       # Stop server"
        ;;
esac
