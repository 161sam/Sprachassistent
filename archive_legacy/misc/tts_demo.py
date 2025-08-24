#!/usr/bin/env python3
"""
Praktisches Beispiel für TTS Engine Switching
Zeigt die Verwendung des flexiblen TTS-Systems in verschiedenen Szenarien
"""

import asyncio
import logging
import time
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from tts import TTSManager, TTSEngineType, TTSConfig, quick_synthesize

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TTSDemo:
    """Demonstration des TTS Engine Switching Systems"""
    
    def __init__(self):
        self.output_dir = "tts_demo_output"
        self.ensure_output_dir()
        
    def ensure_output_dir(self):
        """Erstelle Output-Verzeichnis für Audio-Dateien"""
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def demo_basic_usage(self):
        """Demo: Einfache TTS-Verwendung"""
        print("\n🎯 Demo 1: Einfache TTS-Verwendung")
        print("-" * 40)
        
        # Piper TTS
        print("🔊 Teste Piper TTS...")
        result = await quick_synthesize(
            "Hallo, dies ist ein Test von Piper TTS mit deutscher Stimme.",
            engine="piper",
            voice="de-thorsten-low"
        )
        
        if result.success:
            output_file = os.path.join(self.output_dir, "demo1_piper.wav")
            with open(output_file, 'wb') as f:
                f.write(result.audio_data)
            print(f"✅ Piper: {result.processing_time_ms:.1f}ms -> {output_file}")
        else:
            print(f"❌ Piper Fehler: {result.error_message}")
            
        # Kokoro TTS
        print("🔊 Teste Kokoro TTS...")
        result = await quick_synthesize(
            "Hello, this is a test of Kokoro TTS with English voice.",
            engine="kokoro", 
            voice="af_sarah"
        )
        
        if result.success:
            output_file = os.path.join(self.output_dir, "demo1_kokoro.wav")
            with open(output_file, 'wb') as f:
                f.write(result.audio_data)
            print(f"✅ Kokoro: {result.processing_time_ms:.1f}ms -> {output_file}")
        else:
            print(f"❌ Kokoro Fehler: {result.error_message}")
            
    async def demo_manager_switching(self):
        """Demo: Manager-basiertes Engine-Switching"""
        print("\n🔄 Demo 2: Engine-Switching mit Manager")
        print("-" * 40)
        
        manager = TTSManager()
        
        try:
            # Manager initialisieren
            print("🚀 Initialisiere TTS-Manager...")
            piper_config = TTSConfig(
                engine_type="piper",
                voice="de-kerstin-low",  # Weibliche deutsche Stimme
                speed=1.1,
                language="de"
            )
            
            kokoro_config = TTSConfig(
                engine_type="kokoro",
                voice="af_heart",  # Warme englische Stimme
                speed=0.9,
                language="en"
            )
            
            success = await manager.initialize(piper_config, kokoro_config, TTSEngineType.PIPER)
            if not success:
                print("❌ Manager-Initialisierung fehlgeschlagen")
                return
                
            print("✅ TTS-Manager initialisiert")
            
            # Switching-Szenarien
            scenarios = [
                {
                    "engine": TTSEngineType.PIPER,
                    "voice": "de-kerstin-low", 
                    "text": "Willkommen beim Sprachassistenten. Ich verwende Piper TTS.",
                    "filename": "demo2_piper_kerstin.wav"
                },
                {
                    "engine": TTSEngineType.KOKORO,
                    "voice": "af_heart",
                    "text": "Now switching to Kokoro TTS with a warm English voice.",
                    "filename": "demo2_kokoro_heart.wav"
                },
                {
                    "engine": TTSEngineType.PIPER,
                    "voice": "de-thorsten-low",
                    "text": "Zurück zu Piper mit männlicher deutscher Stimme.",
                    "filename": "demo2_piper_thorsten.wav"
                },
                {
                    "engine": TTSEngineType.KOKORO,
                    "voice": "af_sky",
                    "text": "And finally Kokoro with a clear, crisp voice.",
                    "filename": "demo2_kokoro_sky.wav"
                }
            ]
            
            for i, scenario in enumerate(scenarios, 1):
                print(f"\n🔀 Szenario {i}: Wechsel zu {scenario['engine'].value}")
                
                # Engine wechseln
                start_time = time.time()
                await manager.switch_engine(scenario['engine'])
                await manager.set_voice(scenario['voice'])
                
                # Synthese
                result = await manager.synthesize(scenario['text'])
                total_time = time.time() - start_time
                
                if result.success:
                    output_file = os.path.join(self.output_dir, scenario['filename'])
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                    
                    print(f"✅ {scenario['engine'].value}: {result.processing_time_ms:.1f}ms TTS, {total_time*1000:.1f}ms total")
                    print(f"   Stimme: {result.voice_used}, Output: {scenario['filename']}")
                else:
                    print(f"❌ Fehler: {result.error_message}")
                    
        finally:
            await manager.cleanup()
            
    async def demo_performance_comparison(self):
        """Demo: Performance-Vergleich der Engines"""
        print("\n📊 Demo 3: Performance-Vergleich")
        print("-" * 40)
        
        test_texts = [
            "Kurzer Test.",
            "Dies ist ein mittellanger Text für den Performance-Vergleich der TTS-Engines.",
            "Dies ist ein längerer Text, der verwendet wird, um die Performance-Charakteristika der verschiedenen TTS-Engines zu vergleichen. Wir messen sowohl die Verarbeitungszeit als auch die Qualität der Sprachsynthese."
        ]
        
        manager = TTSManager()
        
        try:
            await manager.initialize()
            
            results = {}
            
            for i, text in enumerate(test_texts, 1):
                text_length = len(text)
                print(f"\n📝 Test {i}: {text_length} Zeichen")
                print(f"Text: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                # Test beide Engines
                for engine_type in [TTSEngineType.PIPER, TTSEngineType.KOKORO]:
                    await manager.switch_engine(engine_type)
                    
                    # 3 Durchläufe für Durchschnitt
                    times = []
                    for run in range(3):
                        start_time = time.time()
                        result = await manager.synthesize(text)
                        total_time = time.time() - start_time
                        
                        if result.success:
                            times.append(result.processing_time_ms)
                            
                            if run == 0:  # Erste Datei speichern
                                filename = f"demo3_perf_{i}_{engine_type.value}.wav"
                                output_file = os.path.join(self.output_dir, filename)
                                with open(output_file, 'wb') as f:
                                    f.write(result.audio_data)
                        else:
                            print(f"   ❌ {engine_type.value} Fehler: {result.error_message}")
                            break
                            
                    if times:
                        avg_time = sum(times) / len(times)
                        min_time = min(times)
                        max_time = max(times)
                        
                        key = f"{engine_type.value}_text{i}"
                        results[key] = {
                            'avg': avg_time,
                            'min': min_time,
                            'max': max_time,
                            'text_length': text_length
                        }
                        
                        print(f"   {engine_type.value:>6}: {avg_time:6.1f}ms ⌀ ({min_time:.1f}-{max_time:.1f}ms)")
                        
            # Ergebnisse zusammenfassen
            print(f"\n📈 Performance-Zusammenfassung:")
            print("-" * 40)
            
            for i in range(1, len(test_texts) + 1):
                piper_key = f"piper_text{i}"
                kokoro_key = f"kokoro_text{i}"
                
                if piper_key in results and kokoro_key in results:
                    piper_avg = results[piper_key]['avg']
                    kokoro_avg = results[kokoro_key]['avg']
                    text_len = results[piper_key]['text_length']
                    
                    faster_engine = "Kokoro" if kokoro_avg < piper_avg else "Piper"
                    speed_diff = abs(piper_avg - kokoro_avg)
                    
                    print(f"Text {i} ({text_len:3d} Zeichen): {faster_engine} {speed_diff:.1f}ms schneller")
                    
        finally:
            await manager.cleanup()
            
    async def demo_voice_comparison(self):
        """Demo: Vergleich verschiedener Stimmen"""
        print("\n🎵 Demo 4: Stimmen-Vergleich")
        print("-" * 40)
        
        manager = TTSManager()
        
        try:
            await manager.initialize()
            
            # Deutsche Stimmen (Piper)
            german_text = "Dies ist ein Test verschiedener deutscher Stimmen."
            german_voices = ["de-thorsten-low", "de-kerstin-low", "de-eva_k-low"]
            
            await manager.switch_engine(TTSEngineType.PIPER)
            print("🇩🇪 Deutsche Stimmen (Piper):")
            
            for voice in german_voices:
                success = await manager.set_voice(voice)
                if success:
                    result = await manager.synthesize(german_text)
                    if result.success:
                        filename = f"demo4_german_{voice.replace('-', '_')}.wav"
                        output_file = os.path.join(self.output_dir, filename)
                        with open(output_file, 'wb') as f:
                            f.write(result.audio_data)
                        print(f"   ✅ {voice}: {result.processing_time_ms:.1f}ms -> {filename}")
                    else:
                        print(f"   ❌ {voice}: {result.error_message}")
                else:
                    print(f"   ⚠️  {voice}: Stimme nicht verfügbar")
                    
            # Englische Stimmen (Kokoro)
            english_text = "This is a test of different English voices."
            english_voices = ["af_sarah", "af_heart", "af_sky", "af_nova"]
            
            await manager.switch_engine(TTSEngineType.KOKORO)
            print("\n🇺🇸 Englische Stimmen (Kokoro):")
            
            for voice in english_voices:
                success = await manager.set_voice(voice)
                if success:
                    result = await manager.synthesize(english_text)
                    if result.success:
                        filename = f"demo4_english_{voice}.wav"
                        output_file = os.path.join(self.output_dir, filename)
                        with open(output_file, 'wb') as f:
                            f.write(result.audio_data)
                        print(f"   ✅ {voice}: {result.processing_time_ms:.1f}ms -> {filename}")
                    else:
                        print(f"   ❌ {voice}: {result.error_message}")
                else:
                    print(f"   ⚠️  {voice}: Stimme nicht verfügbar")
                    
        finally:
            await manager.cleanup()
            
    async def demo_conversation_scenario(self):
        """Demo: Konversations-Szenario mit dynamischem Engine-Switching"""
        print("\n💬 Demo 5: Konversations-Szenario")
        print("-" * 40)
        
        manager = TTSManager()
        
        try:
            await manager.initialize()
            
            # Konversations-Verlauf
            conversation = [
                {
                    "speaker": "Assistent",
                    "engine": TTSEngineType.PIPER,
                    "voice": "de-thorsten-low",
                    "text": "Hallo! Ich bin Ihr Sprachassistent. Wie kann ich Ihnen helfen?"
                },
                {
                    "speaker": "User",
                    "engine": TTSEngineType.KOKORO,
                    "voice": "af_heart",
                    "text": "Hello, can you tell me about the weather?"
                },
                {
                    "speaker": "Assistent",
                    "engine": TTSEngineType.PIPER,
                    "voice": "de-kerstin-low",
                    "text": "Gerne kann ich Ihnen bei Wetterinformationen helfen. Welche Stadt interessiert Sie?"
                },
                {
                    "speaker": "User",
                    "engine": TTSEngineType.KOKORO,
                    "voice": "af_sky",
                    "text": "I'd like to know about Berlin."
                },
                {
                    "speaker": "Assistent",
                    "engine": TTSEngineType.PIPER,
                    "voice": "de-thorsten-low",
                    "text": "Das Wetter in Berlin ist heute sonnig mit 18 Grad Celsius."
                }
            ]
            
            print("🎭 Simuliere Konversation mit automatischem Engine-Switching:")
            print()
            
            for i, turn in enumerate(conversation, 1):
                # Engine für Sprecher wechseln
                await manager.switch_engine(turn['engine'])
                await manager.set_voice(turn['voice'])
                
                # Text synthesieren
                result = await manager.synthesize(turn['text'])
                
                if result.success:
                    filename = f"demo5_conversation_{i:02d}_{turn['speaker'].lower()}.wav"
                    output_file = os.path.join(self.output_dir, filename)
                    with open(output_file, 'wb') as f:
                        f.write(result.audio_data)
                    
                    print(f"{turn['speaker']:>10} ({turn['engine'].value}/{turn['voice']}):")
                    print(f"             \"{turn['text']}\"")
                    print(f"             ⏱️  {result.processing_time_ms:.1f}ms -> {filename}")
                    print()
                else:
                    print(f"❌ Fehler bei {turn['speaker']}: {result.error_message}")
                    
        finally:
            await manager.cleanup()
            
    async def run_all_demos(self):
        """Führe alle Demos aus"""
        print("🎤 TTS Engine Switching - Praktische Beispiele")
        print("=" * 50)
        print()
        print("Diese Demo zeigt die Verwendung des flexiblen TTS-Systems")
        print("mit Realtime-Switching zwischen Piper und Kokoro TTS.")
        print()
        print(f"📁 Audio-Ausgabe: {self.output_dir}/")
        print()
        
        start_time = time.time()
        
        try:
            await self.demo_basic_usage()
            await self.demo_manager_switching() 
            await self.demo_performance_comparison()
            await self.demo_voice_comparison()
            await self.demo_conversation_scenario()
            
        except Exception as e:
            print(f"\n❌ Demo fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
            
        total_time = time.time() - start_time
        
        print(f"\n🎉 Alle Demos abgeschlossen in {total_time:.1f}s")
        print(f"📁 Audio-Dateien erstellt in: {self.output_dir}/")
        print()
        print("💡 Nächste Schritte:")
        print("   - Hören Sie die Audio-Dateien ab um die Qualität zu vergleichen")
        print("   - Starten Sie den Sprachassistenten mit TTS-Switching")
        print("   - Testen Sie das Engine-Switching in der GUI")
        
def main():
    """Hauptfunktion"""
    demo = TTSDemo()
    asyncio.run(demo.run_all_demos())

if __name__ == "__main__":
    main()
