#!/usr/bin/env python3
"""
Test-Script für TTS-Engine-Switching
Testet beide Engines (Piper und Kokoro) einzeln und mit dem Manager
"""

import asyncio
import logging
import time
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tts import TTSManager, TTSEngineType, TTSConfig, PiperTTSEngine, KokoroTTSEngine

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TTSSystemTester:
    """Comprehensive TTS system tester"""
    
    def __init__(self):
        self.test_texts = {
            "short": "Hallo Welt",
            "medium": "Dies ist ein Test der deutschen Sprachsynthese mit verschiedenen TTS-Engines.",
            "long": "Heute testen wir die Funktionalität unseres Sprachassistenten. Das System unterstützt sowohl Piper TTS für hochqualitative deutsche Stimmen als auch Kokoro TTS für kompakte und effiziente Sprachsynthese. Beide Engines können in Echtzeit gewechselt werden.",
            "english": "This is a test of the English speech synthesis capabilities.",
            "numbers": "Die Zahlen eins, zwei, drei, vier, fünf werden korrekt ausgesprochen.",
            "special": "Können Sonderzeichen wie ä, ö, ü, ß korrekt verarbeitet werden? Ja!"
        }
        
    async def test_individual_engines(self):
        """Teste jede Engine einzeln"""
        logger.info("🧪 Teste individuelle TTS-Engines...")
        
        # Test Piper TTS
        logger.info("\n📢 Teste Piper TTS Engine:")
        await self._test_piper_engine()
        
        # Test Kokoro TTS  
        logger.info("\n🎤 Teste Kokoro TTS Engine:")
        await self._test_kokoro_engine()
        
    async def _test_piper_engine(self):
        """Teste Piper TTS Engine"""
        try:
            config = TTSConfig(
                engine_type="piper",
                model_path="",  # Auto-detection
                voice="de-thorsten-low",
                speed=1.0,
                language="de"
            )
            
            engine = PiperTTSEngine(config)
            success = await engine.initialize()
            
            if not success:
                logger.error("❌ Piper Engine konnte nicht initialisiert werden")
                return
                
            logger.info("✅ Piper Engine erfolgreich initialisiert")
            logger.info(f"📋 Engine Info: {engine.get_engine_info()}")
            logger.info(f"🎵 Verfügbare Stimmen: {engine.get_available_voices()}")
            
            # Test verschiedene Texte
            for text_type, text in self.test_texts.items():
                if text_type == "english":  # Skip English for Piper (German focus)
                    continue
                    
                logger.info(f"  🔊 Teste '{text_type}': {text[:30]}...")
                result = await engine.synthesize(text)
                
                if result.success:
                    logger.info(f"  ✅ Synthese erfolgreich: {result.processing_time_ms:.1f}ms, {len(result.audio_data)} bytes")
                    
                    # Speichere Testdatei
                    output_file = f"test_piper_{text_type}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                    logger.info(f"  💾 Audio gespeichert: {output_file}")
                else:
                    logger.error(f"  ❌ Synthese fehlgeschlagen: {result.error_message}")
                    
            await engine.cleanup()
            
        except Exception as e:
            logger.error(f"❌ Piper Engine Test fehlgeschlagen: {e}")
            
    async def _test_kokoro_engine(self):
        """Teste Kokoro TTS Engine"""
        try:
            config = TTSConfig(
                engine_type="kokoro",
                model_path="",  # Auto-detection
                voice="af_sarah",
                speed=1.0,
                language="en"
            )
            
            engine = KokoroTTSEngine(config)
            success = await engine.initialize()
            
            if not success:
                logger.error("❌ Kokoro Engine konnte nicht initialisiert werden")
                return
                
            logger.info("✅ Kokoro Engine erfolgreich initialisiert")
            logger.info(f"📋 Engine Info: {engine.get_engine_info()}")
            logger.info(f"🎵 Verfügbare Stimmen: {engine.get_available_voices()}")
            
            # Test verschiedene Texte
            for text_type, text in self.test_texts.items():
                logger.info(f"  🔊 Teste '{text_type}': {text[:30]}...")
                
                # Voice für Text-Type wählen
                voice = "af_sarah"  # Standard
                if text_type == "english":
                    voice = "af_heart"
                elif text_type == "special":
                    voice = "af_sky"
                    
                result = await engine.synthesize(text, voice=voice)
                
                if result.success:
                    logger.info(f"  ✅ Synthese erfolgreich: {result.processing_time_ms:.1f}ms, {len(result.audio_data)} bytes")
                    
                    # Speichere Testdatei
                    output_file = f"test_kokoro_{text_type}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                    logger.info(f"  💾 Audio gespeichert: {output_file}")
                else:
                    logger.error(f"  ❌ Synthese fehlgeschlagen: {result.error_message}")
                    
            await engine.cleanup()
            
        except Exception as e:
            logger.error(f"❌ Kokoro Engine Test fehlgeschlagen: {e}")
            
    async def test_tts_manager(self):
        """Teste TTS-Manager mit Engine-Switching"""
        logger.info("\n🎛️ Teste TTS-Manager mit Engine-Switching...")
        
        manager = TTSManager()
        
        try:
            # Initialisiere mit benutzerdefinierten Configs
            piper_config = TTSConfig(
                engine_type="piper",
                voice="de-thorsten-low",
                speed=1.1,  # Etwas schneller
                language="de"
            )
            
            kokoro_config = TTSConfig(
                engine_type="kokoro",
                voice="af_sarah",
                speed=0.9,  # Etwas langsamer
                language="en"
            )
            
            success = await manager.initialize(piper_config, kokoro_config, TTSEngineType.PIPER)
            
            if not success:
                logger.error("❌ TTS-Manager konnte nicht initialisiert werden")
                return
                
            logger.info("✅ TTS-Manager erfolgreich initialisiert")
            
            # Zeige verfügbare Engines
            engines = await manager.get_available_engines()
            logger.info(f"🚀 Verfügbare Engines: {len(engines)}")
            for engine in engines:
                logger.info(f"  - {engine['name']}: {engine['engine_type']} {'(aktiv)' if engine['is_active'] else ''}")
                
            # Test Engine-Switching mit verschiedenen Texten
            test_scenarios = [
                (TTSEngineType.PIPER, "de-thorsten-low", "Das ist Piper TTS mit deutscher Stimme."),
                (TTSEngineType.KOKORO, "af_sarah", "This is Kokoro TTS with English voice."),
                (TTSEngineType.PIPER, "de-kerstin-low", "Wechsel zu einer anderen deutschen Stimme."),
                (TTSEngineType.KOKORO, "af_heart", "Switching to different English voice."),
            ]
            
            for i, (engine_type, voice, text) in enumerate(test_scenarios, 1):
                logger.info(f"\n🔄 Szenario {i}: Wechsel zu {engine_type.value} mit Stimme '{voice}'")
                
                # Engine wechseln
                switch_success = await manager.switch_engine(engine_type)
                if not switch_success:
                    logger.error(f"❌ Wechsel zu {engine_type.value} fehlgeschlagen")
                    continue
                    
                # Stimme setzen
                voice_success = await manager.set_voice(voice)
                if not voice_success:
                    logger.warning(f"⚠️ Stimme '{voice}' konnte nicht gesetzt werden")
                    
                # Synthese
                start_time = time.time()
                result = await manager.synthesize(text)
                switch_time = time.time() - start_time
                
                if result.success:
                    logger.info(f"✅ Synthese erfolgreich: {result.processing_time_ms:.1f}ms (Switch+Synthese: {switch_time*1000:.1f}ms)")
                    logger.info(f"   Engine: {result.engine_used}, Voice: {result.voice_used}")
                    
                    # Speichere Test-Audio
                    output_file = f"test_manager_scenario_{i}_{engine_type.value}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                    logger.info(f"💾 Audio gespeichert: {output_file}")
                else:
                    logger.error(f"❌ Synthese fehlgeschlagen: {result.error_message}")
                    
            # Performance-Test: Schneller Engine-Wechsel
            logger.info("\n⚡ Performance-Test: Schnelle Engine-Wechsel")
            await self._performance_test(manager)
            
            # Zeige finale Statistiken
            logger.info("\n📊 Finale Engine-Statistiken:")
            stats = manager.get_engine_stats()
            for engine_name, engine_stats in stats.items():
                logger.info(f"  {engine_name}:")
                logger.info(f"    Requests: {engine_stats['total_requests']}")
                logger.info(f"    Success: {engine_stats['successful_requests']}")
                logger.info(f"    Avg Time: {engine_stats['average_processing_time_ms']:.1f}ms")
                
        finally:
            await manager.cleanup()
            
    async def _performance_test(self, manager: TTSManager):
        """Performance-Test für schnelle Engine-Wechsel"""
        test_text = "Performance-Test"
        switch_times = []
        
        engines = [TTSEngineType.PIPER, TTSEngineType.KOKORO]
        
        for i in range(6):  # 6 Wechsel
            target_engine = engines[i % 2]
            
            start_time = time.time()
            await manager.switch_engine(target_engine)
            result = await manager.synthesize(test_text)
            total_time = time.time() - start_time
            
            switch_times.append(total_time * 1000)
            
            if result.success:
                logger.info(f"  Wechsel {i+1} zu {target_engine.value}: {total_time*1000:.1f}ms")
            else:
                logger.error(f"  Wechsel {i+1} fehlgeschlagen")
                
        if switch_times:
            avg_time = sum(switch_times) / len(switch_times)
            min_time = min(switch_times)
            max_time = max(switch_times)
            
            logger.info(f"📈 Performance-Ergebnisse:")
            logger.info(f"   Durchschnitt: {avg_time:.1f}ms")
            logger.info(f"   Minimum: {min_time:.1f}ms")
            logger.info(f"   Maximum: {max_time:.1f}ms")
            
    async def test_all_engines_comparison(self):
        """Vergleichstest aller Engines mit identischem Text"""
        logger.info("\n🔍 Vergleichstest aller Engines...")
        
        manager = TTSManager()
        
        try:
            await manager.initialize()
            
            test_text = "Dies ist ein Vergleichstest zwischen verschiedenen TTS-Engines für optimale Sprachqualität."
            
            engines_results = await manager.test_all_engines(test_text)
            
            logger.info(f"📊 Vergleichsergebnisse für: '{test_text}'")
            logger.info("-" * 60)
            
            for engine_name, result in engines_results.items():
                if result.success:
                    logger.info(f"{engine_name:10} | ✅ | {result.processing_time_ms:6.1f}ms | {result.voice_used}")
                    
                    # Audio speichern für manuellen Vergleich
                    output_file = f"comparison_{engine_name}.wav"
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                else:
                    logger.info(f"{engine_name:10} | ❌ | {'':>8} | {result.error_message}")
                    
        finally:
            await manager.cleanup()
            
    async def run_all_tests(self):
        """Führe alle Tests aus"""
        logger.info("🚀 Starte TTS-System Tests...")
        logger.info("=" * 60)
        
        try:
            # Test 1: Individuelle Engines
            await self.test_individual_engines()
            
            # Test 2: TTS-Manager
            await self.test_tts_manager()
            
            # Test 3: Vergleichstest
            await self.test_all_engines_comparison()
            
            logger.info("\n🎉 Alle Tests abgeschlossen!")
            logger.info("💾 Audio-Dateien wurden erstellt - hören Sie sie zur Qualitätsprüfung ab.")
            
        except Exception as e:
            logger.error(f"❌ Test-Suite fehlgeschlagen: {e}")
            
def main():
    """Main test function"""
    print("TTS Engine Test Suite")
    print("====================")
    print()
    print("Teste das flexible TTS-System mit Piper und Kokoro TTS...")
    print()
    
    # Prüfe Abhängigkeiten
    missing_deps = []
    
    try:
        import kokoro_onnx
        import soundfile
    except ImportError:
        missing_deps.append("Kokoro TTS (pip install kokoro-onnx soundfile)")
        
    try:
        import subprocess
        result = subprocess.run(["piper", "--version"], capture_output=True)
        if result.returncode != 0:
            missing_deps.append("Piper TTS (siehe Installation)")
    except FileNotFoundError:
        missing_deps.append("Piper TTS (siehe Installation)")
        
    if missing_deps:
        print("⚠️ Fehlende Abhängigkeiten:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print()
        print("Einige Tests werden möglicherweise fehlschlagen.")
        print()
        
    # Tests ausführen
    tester = TTSSystemTester()
    asyncio.run(tester.run_all_tests())

if __name__ == "__main__":
    main()
