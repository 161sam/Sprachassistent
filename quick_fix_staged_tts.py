#!/usr/bin/env python3
"""
Quick-Fix für Staged TTS Probleme
Behebt die wichtigsten Probleme sofort
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class StagedTTSQuickFix:
    """Schnelle Problemlösung für Staged TTS"""
    
    def __init__(self, project_root="/home/saschi/Sprachassistent"):
        self.project_root = Path(project_root)
        self.env_file = self.project_root / ".env"
        self.fixes_applied = []
    
    def run_all_fixes(self):
        """Führt alle verfügbaren Quick-Fixes aus"""
        print("🔧 Starte Staged TTS Quick-Fix...\n")
        
        # Backup der .env erstellen
        self._backup_env()
        
        # Fixes anwenden
        self._fix_timeout_settings()
        self._fix_text_sanitization()
        self._fix_fallback_settings()
        self._add_phoneme_fixes()
        self._optimize_chunking()
        
        # Zusammenfassung
        self._print_summary()
        
        # Neustart empfehlen
        self._suggest_restart()
    
    def _backup_env(self):
        """Erstellt Backup der .env-Datei"""
        if self.env_file.exists():
            backup_file = self.env_file.with_suffix(f'.env.backup.{int(time.time())}')
            import shutil
            shutil.copy(self.env_file, backup_file)
            logger.info(f"✅ Backup erstellt: {backup_file}")
        else:
            logger.warning("⚠️  .env-Datei nicht gefunden - erstelle neue")
    
    def _fix_timeout_settings(self):
        """Behebt Timeout-Probleme"""
        print("⏱️  Behebe Timeout-Einstellungen...")
        
        timeout_fixes = {
            'STAGED_TTS_INTRO_TIMEOUT': '6.0',      # Reduziert von 10s
            'STAGED_TTS_CHUNK_TIMEOUT': '10.0',     # Reduziert von 15s
            'STAGED_TTS_TOTAL_TIMEOUT': '35.0',     # Reduziert von 45s
            'STAGED_TTS_MAX_RETRIES': '1',          # Schnellere Fallbacks
            'STAGED_TTS_RETRY_DELAY': '0.3',        # Kürzere Retry-Delays
        }
        
        for key, value in timeout_fixes.items():
            self._update_env_var(key, value)
        
        self.fixes_applied.append("Timeout-Einstellungen optimiert")
        print("✅ Timeout-Einstellungen korrigiert")
    
    def _fix_text_sanitization(self):
        """Aktiviert und konfiguriert Text-Bereinigung"""
        print("🧹 Konfiguriere Text-Bereinigung...")
        
        sanitization_fixes = {
            'STAGED_TTS_SANITIZE_TEXT': 'true',
            'STAGED_TTS_REMOVE_DIACRITICS': 'true',
            'PIPER_NORMALIZE_TEXT': 'true',
            'PIPER_FALLBACK_ON_UNKNOWN': 'true',
            'PIPER_PHONEME_STRICT': 'false',
            'UNICODE_NORMALIZE': 'NFKC',
            'REMOVE_PROBLEMATIC_CHARS': 'true',
        }
        
        for key, value in sanitization_fixes.items():
            self._update_env_var(key, value)
        
        self.fixes_applied.append("Text-Bereinigung aktiviert")
        print("✅ Text-Bereinigung konfiguriert")
    
    def _fix_fallback_settings(self):
        """Konfiguriert robuste Fallback-Mechanismen"""
        print("🔄 Konfiguriere Fallback-Mechanismen...")
        
        fallback_fixes = {
            'STAGED_TTS_FALLBACK_ON_TIMEOUT': 'true',
            'STAGED_TTS_FALLBACK_ON_ERROR': 'true',
            'STAGED_TTS_ALLOW_PARTIAL': 'true',
            'STAGED_TTS_FALLBACK_ENGINE': 'zonos',
        }
        
        for key, value in fallback_fixes.items():
            self._update_env_var(key, value)
        
        self.fixes_applied.append("Fallback-Mechanismen verstärkt")
        print("✅ Fallback-Einstellungen optimiert")
    
    def _add_phoneme_fixes(self):
        """Fügt spezielle Fixes für Phonem-Probleme hinzu"""
        print("🔤 Implementiere Phonem-Problem-Fixes...")
        
        phoneme_fixes = {
            'TTS_TEXT_PREPROCESSING': 'true',
            'PIPER_SKIP_UNKNOWN_PHONEMES': 'true',
            'TTS_UNICODE_NORMALIZATION': 'aggressive',
            'TTS_FALLBACK_CHARS': 'c,ss,ae,oe,..,-',
        }
        
        for key, value in phoneme_fixes.items():
            self._update_env_var(key, value)
        
        # Spezielle Zeichen-Ersetzungen
        char_replacements = {
            'TTS_CHAR_REPLACE_CEDILLA': '',         # ̧ entfernen
            'TTS_CHAR_REPLACE_CCEDILLA': 'c',       # ç → c
            'TTS_CHAR_REPLACE_EMDASH': '-',         # — → -
            'TTS_CHAR_REPLACE_ENDASH': '-',         # – → -
            'TTS_CHAR_REPLACE_ELLIPSIS': '...',     # … → ...
            'TTS_CHAR_REPLACE_EURO': 'Euro',        # € → Euro
        }
        
        for key, value in char_replacements.items():
            self._update_env_var(key, value)
        
        self.fixes_applied.append("Phonem-Problem-Fixes implementiert")
        print("✅ Phonem-Handling verbessert")
    
    def _optimize_chunking(self):
        """Optimiert Text-Chunking für bessere Performance"""
        print("✂️  Optimiere Text-Chunking...")
        
        chunking_fixes = {
            'STAGED_TTS_MAX_INTRO_LENGTH': '120',   # Reduziert für Stabilität
            'STAGED_TTS_MAX_RESPONSE_LENGTH': '600', # Reduziert für Performance
            'STAGED_TTS_CHUNK_SIZE_MIN': '80',
            'STAGED_TTS_CHUNK_SIZE_MAX': '180',     # Kleinere Chunks
            'STAGED_TTS_MAX_CHUNKS': '4',           # Weniger Chunks
        }
        
        for key, value in chunking_fixes.items():
            self._update_env_var(key, value)
        
        self.fixes_applied.append("Chunking-Parameter optimiert")
        print("✅ Chunking optimiert")
    
    def _update_env_var(self, key: str, value: str):
        """Aktualisiert oder fügt Umgebungsvariable hinzu"""
        if not self.env_file.exists():
            self.env_file.touch()
        
        # Lese aktuelle .env
        content = ""
        if self.env_file.exists():
            content = self.env_file.read_text(encoding='utf-8')
        
        # Suche nach existierender Variable
        import re
        pattern = rf'^{re.escape(key)}=.*$'
        
        if re.search(pattern, content, re.MULTILINE):
            # Variable existiert - ersetzen
            content = re.sub(pattern, f'{key}={value}', content, flags=re.MULTILINE)
        else:
            # Variable existiert nicht - anhängen
            if content and not content.endswith('\n'):
                content += '\n'
            content += f'{key}={value}\n'
        
        # Schreibe zurück
        self.env_file.write_text(content, encoding='utf-8')
    
    def _print_summary(self):
        """Zeigt Zusammenfassung der angewendeten Fixes"""
        print("\n" + "="*60)
        print("🎭 STAGED TTS QUICK-FIX ZUSAMMENFASSUNG")
        print("="*60)
        
        print(f"✅ Angewendete Fixes ({len(self.fixes_applied)}):")
        for i, fix in enumerate(self.fixes_applied, 1):
            print(f"  {i}. {fix}")
        
        print(f"\n📁 Konfiguration aktualisiert: {self.env_file}")
        print(f"⏰ Fix durchgeführt um: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n🔧 Wichtige Änderungen:")
        print("  • Intro-Timeout: 6s (vorher: 10s)")
        print("  • Chunk-Timeout: 10s (vorher: 15s)")
        print("  • Text-Bereinigung: aktiviert")
        print("  • Phonem-Fixes: implementiert")
        print("  • Fallbacks: verstärkt")
    
    def _suggest_restart(self):
        """Empfiehlt Neustart des Systems"""
        print("\n🔄 NEUSTART ERFORDERLICH")
        print("="*30)
        print("Die Änderungen werden erst nach einem Neustart wirksam.")
        print()
        print("Desktop-App neustarten:")
        print(f"  cd {self.project_root}/voice-assistant-apps/desktop")
        print("  npm start")
        print()
        print("Oder komplettes System neustarten:")
        print("  sudo systemctl restart ws-server.service")
        print()
        
        # Auto-Neustart anbieten
        try:
            choice = input("Soll die Desktop-App automatisch neugestartet werden? (j/n): ").lower().strip()
            if choice in ('j', 'ja', 'y', 'yes'):
                self._restart_desktop_app()
        except KeyboardInterrupt:
            print("\nAbgebrochen.")
    
    def _restart_desktop_app(self):
        """Startet Desktop-App neu"""
        desktop_dir = self.project_root / "voice-assistant-apps" / "desktop"
        
        if not desktop_dir.exists():
            print(f"❌ Desktop-App-Verzeichnis nicht gefunden: {desktop_dir}")
            return
        
        print("🔄 Starte Desktop-App neu...")
        
        try:
            # Alte Prozesse beenden
            subprocess.run(["pkill", "-f", "electron"], capture_output=True)
            time.sleep(2)
            
            # Neue App starten
            os.chdir(desktop_dir)
            subprocess.Popen(["npm", "start"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            print("✅ Desktop-App wird neugestartet...")
            
        except Exception as e:
            print(f"❌ Fehler beim Neustart: {e}")
            print("Bitte starte die App manuell neu.")

def main():
    """Hauptfunktion"""
    print("🎭 Staged TTS Quick-Fix Tool")
    print("Behebt die häufigsten TTS-Probleme sofort\n")
    
    # Prüfe ob wir im richtigen Verzeichnis sind
    project_candidates = [
        "/home/saschi/Sprachassistent",
        os.path.expanduser("~/Sprachassistent"),
        Path.cwd(),
    ]
    
    project_root = None
    for candidate in project_candidates:
        candidate_path = Path(candidate)
        if (candidate_path / ".env").exists() or (candidate_path / "ws-server").exists():
            project_root = candidate_path
            break
    
    if not project_root:
        print("❌ Projekt-Verzeichnis nicht gefunden!")
        print("Bitte führe das Script im Sprachassistent-Verzeichnis aus.")
        return
    
    print(f"📁 Projekt-Verzeichnis: {project_root}")
    
    # Quick-Fix ausführen
    quick_fix = StagedTTSQuickFix(project_root)
    quick_fix.run_all_fixes()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
        print("\nBitte melde diesen Fehler als GitHub-Issue.")
