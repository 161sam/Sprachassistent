#!/usr/bin/env python3
"""
TTS-Diagnose-Tool für Sprachassistent
Identifiziert und behebt Probleme mit Staged TTS
"""

import asyncio
import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unicodedata

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTSDiagnostics:
    """Diagnose-Tool für TTS-Probleme"""
    
    def __init__(self, models_dir: str = "/home/saschi/Sprachassistent/models"):
        self.models_dir = Path(models_dir)
        self.piper_dir = self.models_dir / "piper"
        self.results = {}
    
    async def run_full_diagnosis(self) -> Dict:
        """Führt vollständige TTS-Diagnose durch"""
        print("🔍 Starte TTS-Diagnose...\n")
        
        self.results = {
            "timestamp": time.time(),
            "system_info": await self._check_system_info(),
            "model_files": await self._check_model_files(),
            "phoneme_test": await self._test_phoneme_handling(),
            "timeout_test": await self._test_timeout_scenarios(),
            "text_sanitization": await self._test_text_sanitization(),
            "staging_config": await self._analyze_staging_config(),
            "recommendations": []
        }
        
        # Empfehlungen generieren
        self._generate_recommendations()
        
        # Ergebnisse ausgeben
        self._print_results()
        
        return self.results
    
    async def _check_system_info(self) -> Dict:
        """Prüft System-Informationen"""
        print("📊 Prüfe System-Informationen...")
        
        info = {
            "python_version": sys.version,
            "models_dir_exists": self.models_dir.exists(),
            "piper_dir_exists": self.piper_dir.exists(),
            "cuda_available": False,
            "env_vars": {}
        }
        
        # CUDA-Verfügbarkeit prüfen
        try:
            import torch
            info["cuda_available"] = torch.cuda.is_available()
            if info["cuda_available"]:
                info["cuda_device_count"] = torch.cuda.device_count()
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
        except ImportError:
            info["cuda_available"] = "torch_not_installed"
        
        # Wichtige Umgebungsvariablen prüfen
        important_vars = [
            "STAGED_TTS_ENABLED", "STAGED_TTS_INTRO_ENGINE", "STAGED_TTS_MAIN_ENGINE",
            "STAGED_TTS_INTRO_TIMEOUT", "STAGED_TTS_CHUNK_TIMEOUT", "TTS_VOICE",
            "ZONOS_MODEL", "PIPER_MODEL_DIR"
        ]
        
        for var in important_vars:
            info["env_vars"][var] = os.getenv(var, "NOT_SET")
        
        print("✅ System-Check abgeschlossen")
        return info
    
    async def _check_model_files(self) -> Dict:
        """Prüft Modell-Dateien"""
        print("📁 Prüfe Modell-Dateien...")
        
        result = {
            "piper_models": [],
            "missing_models": [],
            "model_sizes": {},
            "model_health": {}
        }
        
        # Piper-Modelle prüfen
        expected_piper_models = [
            "de_DE-thorsten-low.onnx",
            "de_DE-thorsten-low.onnx.json",
            "de-thorsten-low.onnx",
            "de-thorsten-low.onnx.json"
        ]
        
        for model_name in expected_piper_models:
            model_path = self.piper_dir / model_name
            if model_path.exists():
                result["piper_models"].append(str(model_path))
                result["model_sizes"][model_name] = model_path.stat().st_size
                
                # Einfacher Gesundheitscheck
                if model_name.endswith('.onnx'):
                    result["model_health"][model_name] = self._check_onnx_health(model_path)
            else:
                result["missing_models"].append(model_name)
        
        print(f"✅ Gefunden: {len(result['piper_models'])} Piper-Modelle")
        if result["missing_models"]:
            print(f"⚠️  Fehlend: {result['missing_models']}")
        
        return result
    
    def _check_onnx_health(self, model_path: Path) -> Dict:
        """Prüft ONNX-Modell-Gesundheit"""
        try:
            size = model_path.stat().st_size
            return {
                "readable": True,
                "size_mb": round(size / 1024 / 1024, 2),
                "size_ok": size > 1024 * 1024,  # Mindestens 1MB
            }
        except Exception as e:
            return {
                "readable": False,
                "error": str(e)
            }
    
    async def _test_phoneme_handling(self) -> Dict:
        """Testet Phonem-Probleme"""
        print("🔤 Teste Phonem-Behandlung...")
        
        # Problematische Test-Strings
        test_texts = [
            "Hallo! Dies ist ein Test mit ̧ Sonderzeichen.",  # Cedilla-Problem
            "Café, naïve, résumé, façade",                    # Diakritika
            "Das kostet 19,99€ — sehr günstig!",             # Unicode-Zeichen
            ""Anführungszeichen" und 'Apostrophe'",          # Smart Quotes
            "Größer ≥ kleiner… interessant.",                # Mathematische Symbole
            "Test\u00A0mit\u2013verschiedenen\u2014Unicode-Zeichen",  # Problematische Unicode
        ]
        
        results = {
            "test_texts": [],
            "problematic_characters": set(),
            "sanitization_effective": True
        }
        
        for text in test_texts:
            test_result = {
                "original": text,
                "problematic_chars": self._find_problematic_chars(text),
                "sanitized": self._sanitize_text_simple(text),
                "safe_for_piper": True
            }
            
            # Prüfe ob nach Bereinigung noch Probleme da sind
            remaining_problems = self._find_problematic_chars(test_result["sanitized"])
            test_result["safe_for_piper"] = len(remaining_problems) == 0
            test_result["remaining_problems"] = remaining_problems
            
            results["test_texts"].append(test_result)
            results["problematic_characters"].update(test_result["problematic_chars"])
            
            if not test_result["safe_for_piper"]:
                results["sanitization_effective"] = False
        
        results["problematic_characters"] = list(results["problematic_characters"])
        
        print(f"✅ Phonem-Test abgeschlossen. Problematische Zeichen: {len(results['problematic_characters'])}")
        return results
    
    def _find_problematic_chars(self, text: str) -> List[str]:
        """Findet problematische Zeichen für Piper TTS"""
        problematic = []
        
        # Bekannt problematische Zeichen
        known_problems = {
            '̧',   # Cedilla (Hauptproblem aus Log)
            '"', '"', ''', ''',  # Smart quotes
            '—', '–',            # Dashes
            '…',                 # Ellipsis
            '€', '§', '©', '®',  # Symbole
        }
        
        for char in text:
            # Unicode-Kategorie prüfen
            category = unicodedata.category(char)
            
            if char in known_problems:
                problematic.append(char)
            elif ord(char) > 127 and char not in 'äöüÄÖÜß':
                # Non-ASCII Zeichen (außer deutsche Umlaute)
                if category.startswith('M'):  # Mark (Diakritika)
                    problematic.append(char)
                elif category.startswith('S'):  # Symbole
                    problematic.append(char)
                elif ord(char) > 255:  # Erweiterte Unicode-Bereiche
                    problematic.append(char)
        
        return list(set(problematic))
    
    def _sanitize_text_simple(self, text: str) -> str:
        """Einfache Text-Bereinigung (Fallback-Implementation)"""
        # Unicode normalisieren
        text = unicodedata.normalize('NFKC', text)
        
        # Bekannte Ersetzungen
        replacements = {
            '̧': '',      # Cedilla entfernen (Hauptproblem)
            'ç': 'c',     # c mit Cedilla
            '"': '"', '"': '"',  # Smart quotes
            ''': "'", ''': "'",  # Smart apostrophe
            '—': '-', '–': '-',  # Dashes
            '…': '...',   # Ellipsis
            '€': 'Euro',
            '§': 'Paragraph',
            '≥': 'groesser gleich',
            '≤': 'kleiner gleich',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Diakritika entfernen (NFD-Zerlegung + Mark-Entfernung)
        normalized = unicodedata.normalize('NFD', text)
        without_marks = ''.join(
            char for char in normalized 
            if unicodedata.category(char) != 'Mn'
        )
        
        # Multiple Spaces normalisieren
        import re
        text = re.sub(r'\s+', ' ', without_marks)
        
        return text.strip()
    
    async def _test_timeout_scenarios(self) -> Dict:
        """Testet Timeout-Szenarien"""
        print("⏱️  Teste Timeout-Szenarien...")
        
        scenarios = [
            ("short_text", "Kurzer Test."),
            ("medium_text", "Dies ist ein mittellanger Text, der getestet werden soll für die Staged TTS Funktionalität."),
            ("long_text", "Dies ist ein sehr langer Text " * 20),
            ("problematic_text", "Text mit ̧ problematischen Zeichen und "speziellen" Symbolen wie € und —."),
        ]
        
        results = {
            "timeout_config": {
                "intro_timeout": float(os.getenv("STAGED_TTS_INTRO_TIMEOUT", "10.0")),
                "chunk_timeout": float(os.getenv("STAGED_TTS_CHUNK_TIMEOUT", "15.0")),
                "total_timeout": float(os.getenv("STAGED_TTS_TOTAL_TIMEOUT", "45.0")),
            },
            "scenario_analysis": []
        }
        
        for scenario_name, text in scenarios:
            analysis = {
                "scenario": scenario_name,
                "text_length": len(text),
                "estimated_chunks": max(1, len(text) // 120),
                "problematic_chars": self._find_problematic_chars(text),
                "timeout_risk": "low"
            }
            
            # Risiko-Bewertung
            if len(analysis["problematic_chars"]) > 0:
                analysis["timeout_risk"] = "high"
            elif len(text) > 500:
                analysis["timeout_risk"] = "medium"
            
            # Geschätzte Verarbeitungszeit
            analysis["estimated_processing_time"] = len(text) * 0.1  # 100ms per Zeichen Schätzung
            
            results["scenario_analysis"].append(analysis)
        
        print("✅ Timeout-Analyse abgeschlossen")
        return results
    
    async def _test_text_sanitization(self) -> Dict:
        """Testet Text-Bereinigungslogik"""
        print("🧹 Teste Text-Bereinigung...")
        
        test_cases = [
            "Normal text",
            "Text mit ̧ Cedilla",
            "Café and naïve",
            "Unicode\u00A0spaces",
            "Smart "quotes" and —dashes",
        ]
        
        results = {
            "sanitization_enabled": os.getenv("STAGED_TTS_SANITIZE_TEXT", "true").lower() == "true",
            "test_cases": []
        }
        
        for text in test_cases:
            test_result = {
                "original": text,
                "sanitized": self._sanitize_text_simple(text),
                "char_count_before": len(text),
                "char_count_after": 0,
                "problematic_removed": False
            }
            
            test_result["char_count_after"] = len(test_result["sanitized"])
            test_result["problematic_removed"] = len(self._find_problematic_chars(test_result["sanitized"])) == 0
            
            results["test_cases"].append(test_result)
        
        print("✅ Text-Bereinigung getestet")
        return results
    
    async def _analyze_staging_config(self) -> Dict:
        """Analysiert Staging-Konfiguration"""
        print("⚙️  Analysiere Staging-Konfiguration...")
        
        config = {
            "enabled": os.getenv("STAGED_TTS_ENABLED", "true").lower() == "true",
            "intro_engine": os.getenv("STAGED_TTS_INTRO_ENGINE", "piper"),
            "main_engine": os.getenv("STAGED_TTS_MAIN_ENGINE", "zonos"),
            "intro_timeout": float(os.getenv("STAGED_TTS_INTRO_TIMEOUT", "10.0")),
            "chunk_timeout": float(os.getenv("STAGED_TTS_CHUNK_TIMEOUT", "15.0")),
            "fallback_on_timeout": os.getenv("STAGED_TTS_FALLBACK_ON_TIMEOUT", "true").lower() == "true",
            "sanitize_text": os.getenv("STAGED_TTS_SANITIZE_TEXT", "true").lower() == "true",
        }
        
        analysis = {
            "config": config,
            "issues": [],
            "optimizations": []
        }
        
        # Konfiguration analysieren
        if config["intro_timeout"] > 10.0:
            analysis["issues"].append("Intro-Timeout zu hoch (>10s)")
            analysis["optimizations"].append("Reduziere STAGED_TTS_INTRO_TIMEOUT auf 6-8 Sekunden")
        
        if not config["fallback_on_timeout"]:
            analysis["issues"].append("Fallback bei Timeout deaktiviert")
            analysis["optimizations"].append("Aktiviere STAGED_TTS_FALLBACK_ON_TIMEOUT=true")
        
        if not config["sanitize_text"]:
            analysis["issues"].append("Text-Bereinigung deaktiviert")
            analysis["optimizations"].append("Aktiviere STAGED_TTS_SANITIZE_TEXT=true")
        
        print("✅ Konfigurations-Analyse abgeschlossen")
        return analysis
    
    def _generate_recommendations(self) -> None:
        """Generiert Empfehlungen basierend auf Diagnose"""
        recommendations = []
        
        # Modell-Probleme
        if self.results["model_files"]["missing_models"]:
            recommendations.append({
                "type": "critical",
                "title": "Fehlende Piper-Modelle",
                "description": f"Fehlende Modelle: {self.results['model_files']['missing_models']}",
                "action": "Lade fehlende Piper-Modelle herunter oder überprüfe PIPER_MODEL_DIR"
            })
        
        # Phonem-Probleme
        if not self.results["phoneme_test"]["sanitization_effective"]:
            recommendations.append({
                "type": "high",
                "title": "Text-Bereinigung unzureichend",
                "description": "Text-Sanitization entfernt nicht alle problematischen Zeichen",
                "action": "Implementiere erweiterte Text-Bereinigung (text_sanitizer.py)"
            })
        
        # Timeout-Probleme
        staging_config = self.results["staging_config"]["config"]
        if staging_config["intro_timeout"] > 8.0:
            recommendations.append({
                "type": "medium",
                "title": "Intro-Timeout zu hoch",
                "description": f"Aktuell: {staging_config['intro_timeout']}s",
                "action": "Setze STAGED_TTS_INTRO_TIMEOUT=6.0"
            })
        
        # Fallback-Konfiguration
        if not staging_config["fallback_on_timeout"]:
            recommendations.append({
                "type": "high",
                "title": "Fallback deaktiviert",
                "description": "Bei Piper-Timeout wird nicht zu Zonos gewechselt",
                "action": "Setze STAGED_TTS_FALLBACK_ON_TIMEOUT=true"
            })
        
        self.results["recommendations"] = recommendations
    
    def _print_results(self) -> None:
        """Gibt Diagnose-Ergebnisse aus"""
        print("\n" + "="*60)
        print("🎭 TTS DIAGNOSE-ERGEBNIS")
        print("="*60)
        
        # System-Info
        print(f"\n📊 System:")
        print(f"  CUDA verfügbar: {self.results['system_info']['cuda_available']}")
        print(f"  Models-Dir: {self.results['system_info']['models_dir_exists']}")
        
        # Modelle
        print(f"\n📁 Modelle:")
        print(f"  Piper-Modelle gefunden: {len(self.results['model_files']['piper_models'])}")
        if self.results['model_files']['missing_models']:
            print(f"  ⚠️  Fehlende Modelle: {self.results['model_files']['missing_models']}")
        
        # Phoneme
        print(f"\n🔤 Phonem-Test:")
        phoneme_result = self.results['phoneme_test']
        print(f"  Problematische Zeichen: {len(phoneme_result['problematic_characters'])}")
        print(f"  Bereinigung effektiv: {phoneme_result['sanitization_effective']}")
        
        # Empfehlungen
        print(f"\n💡 Empfehlungen ({len(self.results['recommendations'])}):")
        for i, rec in enumerate(self.results['recommendations'], 1):
            priority_icon = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}
            icon = priority_icon.get(rec['type'], "ℹ️")
            print(f"  {i}. {icon} {rec['title']}")
            print(f"     {rec['description']}")
            print(f"     Aktion: {rec['action']}")
        
        print(f"\n✅ Diagnose abgeschlossen um {time.strftime('%H:%M:%S')}")
        print("="*60)
    
    def save_report(self, filename: str = "tts_diagnosis_report.json") -> None:
        """Speichert Diagnose-Bericht als JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        print(f"📄 Bericht gespeichert: {filename}")

async def main():
    """Hauptfunktion"""
    print("🎭 TTS-Diagnose-Tool für Sprachassistent")
    print("=" * 50)
    
    # .env laden falls vorhanden
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env-Datei geladen")
    
    # Diagnose starten
    diagnostics = TTSDiagnostics()
    results = await diagnostics.run_full_diagnosis()
    
    # Bericht speichern
    diagnostics.save_report()
    
    # Quick-Fix anbieten
    if results['recommendations']:
        print("\n🔧 Quick-Fix verfügbar!")
        print("Soll die optimierte .env-Konfiguration erstellt werden? (j/n): ", end="")
        
        try:
            choice = input().lower().strip()
            if choice in ('j', 'ja', 'y', 'yes'):
                create_optimized_env()
        except KeyboardInterrupt:
            print("\nAbgebrochen.")

def create_optimized_env():
    """Erstellt optimierte .env-Datei"""
    optimized_config = """# Optimierte TTS-Konfiguration (Auto-generiert)
STAGED_TTS_ENABLED=true
STAGED_TTS_INTRO_TIMEOUT=6.0
STAGED_TTS_CHUNK_TIMEOUT=10.0
STAGED_TTS_TOTAL_TIMEOUT=35.0
STAGED_TTS_FALLBACK_ON_TIMEOUT=true
STAGED_TTS_SANITIZE_TEXT=true
STAGED_TTS_DEBUG=true
"""
    
    backup_file = Path(".env.backup")
    env_file = Path(".env")
    
    # Backup erstellen falls .env existiert
    if env_file.exists():
        import shutil
        shutil.copy(env_file, backup_file)
        print(f"✅ Backup erstellt: {backup_file}")
    
    # Optimierte Einstellungen anhängen/aktualisieren
    with open(env_file, 'a', encoding='utf-8') as f:
        f.write(f"\n# TTS-Optimierungen - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(optimized_config)
    
    print(f"✅ Optimierte Konfiguration in {env_file} erstellt")
    print("🔄 Starte den Sprachassistent neu, um Änderungen zu übernehmen")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
