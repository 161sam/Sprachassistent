#!/usr/bin/env python3
"""
Migration script to upgrade existing installation to binary audio support
"""

import os
import shutil
import json
from pathlib import Path
import sys

def migrate_to_binary_support():
    """Migrate existing installation"""
    
    print("🔄 Migrating to Binary Audio Support...")
    
    # Get the directory where the script is located
    script_dir = Path(__file__).parent
    ws_server_dir = script_dir.parent
    project_root = ws_server_dir.parent.parent
    
    print(f"📁 Working directory: {ws_server_dir}")
    print(f"📁 Project root: {project_root}")
    
    # 1. Backup existing configuration
    config_path = ws_server_dir / "config.json"
    env_path = ws_server_dir / ".env"
    
    if config_path.exists():
        backup_path = config_path.parent / "config.json.backup"
        shutil.copy2(config_path, backup_path)
        print(f"✅ Configuration backed up to {backup_path}")
    
    if env_path.exists():
        backup_path = env_path.parent / ".env.backup"
        shutil.copy2(env_path, backup_path)
        print(f"✅ Environment file backed up to {backup_path}")
    
    # 2. Update configuration with new features
    config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print("⚠️  Config file exists but is not valid JSON, starting fresh")
    
    # Add new configuration options
    config.update({
        "binary_audio_enabled": True,
        "vad_enabled": True,
        "performance_metrics_enabled": True,
        "protocol_version": "2.0",
        "backwards_compatibility": True,
        "migration_completed": True,
        "migration_date": str(Path(__file__).stat().st_mtime)
    })
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuration updated with binary audio support")
    
    # 3. Update .env file with new variables
    env_additions = """
# Binary Audio Support (added by migration)
ENABLE_BINARY_AUDIO=true
ENABLE_HTTP_METRICS=true
VAD_THRESHOLD=0.02
VAD_SILENCE_DURATION=1.0
MAX_CONCURRENT_STREAMS=10
AUDIO_BUFFER_SIZE=4096
"""
    
    if env_path.exists():
        with open(env_path, 'a') as f:
            f.write(env_additions)
    else:
        with open(env_path, 'w') as f:
            f.write(env_additions.strip())
    
    print("✅ Environment variables updated")
    
    # 4. Check dependencies
    missing_deps = []
    
    try:
        import psutil
        print("✅ psutil available for system metrics")
    except ImportError:
        missing_deps.append("psutil")
        print("⚠️  psutil not found - needed for system metrics")
    
    try:
        import numpy
        print("✅ numpy available for audio analysis")
    except ImportError:
        missing_deps.append("numpy")
        print("⚠️  numpy not found - needed for audio analysis")
    
    try:
        import websockets
        print("✅ websockets available")
    except ImportError:
        missing_deps.append("websockets")
        print("⚠️  websockets not found - needed for WebSocket server")
    
    # 5. Check if files were deployed correctly
    required_files = [
        "binary_audio_handler.py",
        "enhanced_websocket_server.py", 
        "performance_metrics.py",
        "integration/compatibility_layer.py",
        "integration/__init__.py"
    ]
    
    all_files_present = True
    for file_name in required_files:
        file_path = ws_server_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name} deployed")
        else:
            print(f"❌ {file_name} missing")
            all_files_present = False
    
    # 6. Backup existing ws-server.py
    ws_server_py = ws_server_dir / "ws-server.py"
    if ws_server_py.exists():
        backup_name = f"ws-server.py.bak_binary_migration_{int(time.time())}"
        backup_path = ws_server_dir / backup_name
        shutil.copy2(ws_server_py, backup_path)
        print(f"✅ Original ws-server.py backed up to {backup_name}")
    
    print("\n" + "="*60)
    print("🎉 Migration completed!")
    print("="*60)
    
    if missing_deps:
        print("📋 Install missing dependencies:")
        print(f"   pip install {' '.join(missing_deps)}")
        print()
    
    if all_files_present:
        print("✅ All required files are in place")
    else:
        print("⚠️  Some files are missing - please check deployment")
    
    print("📋 Next steps:")
    print("  1. Install missing dependencies (if any)")
    print("  2. Test the new binary audio server:")
    print("     python enhanced_websocket_server.py")
    print("  3. Update your frontend to use binary protocol")
    print("  4. Test with both binary and legacy JSON clients")
    print("  5. Monitor performance with new metrics API")
    
    print("\n🔄 Backwards compatibility notes:")
    print("  - All existing .env configurations still work")
    print("  - JSON audio messages continue to be supported")
    print("  - Staged TTS integration preserved")
    print("  - No breaking changes to existing API")
    
    return True

def create_enhanced_ws_server():
    """Create enhanced ws-server.py with binary support"""
    
    script_dir = Path(__file__).parent
    ws_server_dir = script_dir.parent
    
    enhanced_server_content = '''#!/usr/bin/env python3
"""
Enhanced Voice Assistant WebSocket Server
Maintains backwards compatibility while adding binary audio support
"""

import asyncio
import websockets
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import enhanced components
from binary_audio_handler import WebSocketBinaryRouter
from enhanced_websocket_server import EnhancedWebSocketServer
from performance_metrics import MetricsIntegratedWebSocketServer

# Import existing components (your current implementation)
try:
    # Try to import your existing modules
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Import your existing STT and TTS processors
    # Modify these imports based on your actual implementation
    from stt.stt_processor import STTProcessor
    from tts.tts_processor import TTSProcessor
    from config.config import Config
    
except ImportError as e:
    print(f"Warning: Could not import existing modules: {e}")
    print("Using compatibility layer with mock processors")
    
    # Fallback to compatibility layer
    from integration.compatibility_layer import MockSTTProcessor as STTProcessor
    from integration.compatibility_layer import MockTTSProcessor as TTSProcessor
    from integration.compatibility_layer import MockConfig as Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceAssistantServer:
    """Main server class with binary audio support"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        
        # Initialize processors
        self.stt_processor = STTProcessor(self.config)
        self.tts_processor = TTSProcessor(self.config)
        
        # Create enhanced server with binary support
        self.enhanced_server = EnhancedWebSocketServer(
            self.stt_processor,
            self.tts_processor,
            self.config
        )
        
        # Add metrics integration
        self.metrics_server = MetricsIntegratedWebSocketServer(self.enhanced_server)
        
        logger.info("Voice Assistant Server initialized with binary audio support")
        logger.info(f"Server features: {self._get_server_features()}")
    
    def _get_server_features(self):
        """Get list of enabled server features"""
        features = [
            "Binary Audio Protocol v2.0",
            "Voice Activity Detection",
            "Streaming STT",
            "Performance Metrics",
            "Legacy JSON Compatibility"
        ]
        
        if hasattr(self.tts_processor, 'staged_tts_enabled'):
            features.append("Staged TTS")
        
        return features
    
    async def start_server(self, host='localhost', port=8765):
        """Start the WebSocket server"""
        try:
            # Create server
            server = await websockets.serve(
                self.handle_client,
                host,
                port,
                compression=None,  # Disable compression for binary frames
                max_size=10**7,    # 10MB max message size
                ping_interval=20,  # Ping every 20 seconds
                ping_timeout=10    # Timeout after 10 seconds
            )
            
            logger.info(f"🚀 Voice Assistant Server started on {host}:{port}")
            logger.info("📡 Protocols: WebSocket (binary + JSON), STT, TTS")
            logger.info("🎯 Performance monitoring active")
            logger.info("🔄 Backwards compatibility enabled")
            
            return server
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def handle_client(self, websocket, path):
        """Enhanced client handler with metrics and binary support"""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"🔗 New client connected: {client_info}")
        
        try:
            # Delegate to enhanced server with metrics
            await self.enhanced_server.handle_client(websocket, path)
            
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client disconnected: {client_info}")
        except Exception as e:
            logger.error(f"❌ Error handling client {client_info}: {e}")

def load_config():
    """Load configuration from environment and files"""
    config = Config()
    
    # Load from environment variables (backwards compatibility)
    config.stt_model = os.getenv('STT_MODEL', getattr(config, 'stt_model', 'base'))
    config.tts_model = os.getenv('TTS_MODEL', getattr(config, 'tts_model', 'piper'))
    config.host = os.getenv('WS_HOST', 'localhost')
    config.port = int(os.getenv('WS_PORT', '8765'))
    config.enable_binary_audio = os.getenv('ENABLE_BINARY_AUDIO', 'true').lower() == 'true'
    config.enable_http_metrics = os.getenv('ENABLE_HTTP_METRICS', 'false').lower() == 'true'
    config.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Update logging level
    logging.getLogger().setLevel(getattr(logging, config.log_level))
    
    return config

async def main():
    """Main server startup"""
    print("🎤 Voice Assistant Backend Starting...")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        # Create and start server
        server_instance = VoiceAssistantServer(config)
        server = await server_instance.start_server(config.host, config.port)
        
        print("✅ Server ready for connections!")
        print(f"📡 WebSocket: ws://{config.host}:{config.port}")
        if config.enable_http_metrics:
            print(f"📊 Metrics API: http://{config.host}:8766/api/metrics/realtime")
        print("🔄 Press Ctrl+C to stop")
        print("=" * 50)
        
        # Keep server running
        await server.wait_closed()
        
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    # Write the enhanced server file
    enhanced_ws_server_path = ws_server_dir / "ws-server-enhanced.py"
    with open(enhanced_ws_server_path, 'w') as f:
        f.write(enhanced_server_content)
    
    print(f"✅ Enhanced server created: {enhanced_ws_server_path}")
    print("   You can test it with: python ws-server-enhanced.py")

if __name__ == "__main__":
    import time
    
    print("🚀 Binary Audio Migration Tool")
    print("=" * 40)
    
    try:
        # Run migration
        success = migrate_to_binary_support()
        
        if success:
            print("\n📝 Create enhanced server? (y/n): ", end="")
            response = input().strip().lower()
            
            if response in ['y', 'yes', '']:
                create_enhanced_ws_server()
                print("\n🎉 Migration and server creation completed!")
            else:
                print("\n✅ Migration completed!")
                print("   You can integrate binary support into your existing ws-server.py")
        
    except Exception as e:
        print(f"\n💥 Migration failed: {e}")
        sys.exit(1)
