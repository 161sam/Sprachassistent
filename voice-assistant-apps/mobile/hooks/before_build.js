#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

module.exports = function(context) {
    console.log('🚀 Before Build Hook: Build-Vorbereitung');

    const projectRoot = context.opts.projectRoot;
    const platformPath = path.join(projectRoot, 'platforms', 'android');
    const wwwPath = path.join(projectRoot, 'www');
    
    // Build-Informationen generieren
    generateBuildInfo(projectRoot, wwwPath);
    
    // Release-spezifische Optimierungen
    if (context.opts.options && context.opts.options.release) {
        console.log('📦 Release-Build erkannt - Optimierungen werden angewendet');
        optimizeForRelease(wwwPath);
        configureReleaseAndroid(platformPath);
    } else {
        console.log('🔧 Debug-Build erkannt - Debug-Features aktiviert');
        configureDebugMode(wwwPath);
    }
    
    // Ressourcen validieren
    validateBuildResources(projectRoot);
    
    // Build-Statistiken erstellen
    generateBuildStats(projectRoot, wwwPath);
    
    console.log('✅ Before Build Hook abgeschlossen');
};

function generateBuildInfo(projectRoot, wwwPath) {
    console.log('📋 Generiere Build-Informationen...');
    
    const packageJsonPath = path.join(projectRoot, 'package.json');
    const configXmlPath = path.join(projectRoot, 'config.xml');
    
    let version = '2.1.0';
    let buildNumber = Date.now().toString();
    
    // Version aus config.xml lesen
    if (fs.existsSync(configXmlPath)) {
        const configXml = fs.readFileSync(configXmlPath, 'utf8');
        const versionMatch = configXml.match(/version=['"]([^'"]+)['"]/);
        if (versionMatch) {
            version = versionMatch[1];
        }
    }
    
    // Git-Informationen sammeln (falls verfügbar)
    let gitInfo = {};
    try {
        const { execSync } = require('child_process');
        gitInfo = {
            commit: execSync('git rev-parse HEAD', { encoding: 'utf8', cwd: projectRoot }).trim(),
            branch: execSync('git rev-parse --abbrev-ref HEAD', { encoding: 'utf8', cwd: projectRoot }).trim(),
            tag: execSync('git describe --tags --abbrev=0', { encoding: 'utf8', cwd: projectRoot }).trim().replace(/\n/g, '')
        };
    } catch (error) {
        gitInfo = {
            commit: 'unknown',
            branch: 'unknown', 
            tag: 'unknown'
        };
    }
    
    const buildInfo = {
        version: version,
        buildNumber: buildNumber,
        buildDate: new Date().toISOString(),
        buildType: process.env.NODE_ENV || 'development',
        platform: 'android',
        git: gitInfo,
        cordova: {
            version: context.cordova?.version || 'unknown',
            platforms: context.cordova?.platforms || []
        }
    };
    
    // Build-Info als JavaScript-Datei speichern
    const buildInfoJs = `
// Auto-generated build information
window.BUILD_INFO = ${JSON.stringify(buildInfo, null, 2)};

console.log('📦 Build Info:', window.BUILD_INFO);
`;
    
    const buildInfoPath = path.join(wwwPath, 'js', 'build-info.js');
    
    // Stelle sicher, dass js-Ordner existiert
    const jsDir = path.dirname(buildInfoPath);
    if (!fs.existsSync(jsDir)) {
        fs.mkdirSync(jsDir, { recursive: true });
    }
    
    fs.writeFileSync(buildInfoPath, buildInfoJs);
    console.log(`✅ Build-Informationen gespeichert: v${version} (${buildNumber})`);
}

function optimizeForRelease(wwwPath) {
    console.log('🎯 Optimiere für Release-Build...');
    
    // Console.log Statements entfernen/ersetzen
    removeDebugStatements(wwwPath);
    
    // CSS und JS minifizieren (einfache Version)
    minifyAssets(wwwPath);
    
    // Ungenutzte Assets entfernen
    removeUnusedAssets(wwwPath);
    
    // Service Worker Cache-Version aktualisieren
    updateServiceWorkerVersion(wwwPath);
}

function removeDebugStatements(wwwPath) {
    const jsFiles = [
        path.join(wwwPath, 'js', 'app.js'),
        path.join(wwwPath, 'js', 'mobile-app.js')
    ];
    
    jsFiles.forEach(jsFile => {
        if (fs.existsSync(jsFile)) {
            let content = fs.readFileSync(jsFile, 'utf8');
            
            // Console.log durch leere Funktion ersetzen (behält Funktionalität für Production)
            content = content.replace(/console\.(log|debug|info)/g, '(()=>{})');
            
            // Debug-Blöcke entfernen
            content = content.replace(/\/\*\s*DEBUG_START\s*\*\/[\s\S]*?\/\*\s*DEBUG_END\s*\*\//g, '');
            content = content.replace(/if\s*\(\s*settings\.debugMode\s*\)\s*\{[^}]*\}/g, '');
            
            fs.writeFileSync(jsFile, content);
            console.log(`🧹 Debug-Statements entfernt aus: ${path.basename(jsFile)}`);
        }
    });
}

function minifyAssets(wwwPath) {
    // Einfache CSS-Minifizierung
    const cssFiles = ['css/app.css', 'css/mobile.css'];
    
    cssFiles.forEach(cssFile => {
        const fullPath = path.join(wwwPath, cssFile);
        if (fs.existsSync(fullPath)) {
            let css = fs.readFileSync(fullPath, 'utf8');
            
            // Kommentare entfernen
            css = css.replace(/\/\*[\s\S]*?\*\//g, '');
            
            // Überflüssige Leerzeichen entfernen
            css = css.replace(/\s+/g, ' ');
            css = css.replace(/\s*{\s*/g, '{');
            css = css.replace(/;\s*/g, ';');
            css = css.replace(/\s*}\s*/g, '}');
            
            fs.writeFileSync(fullPath, css.trim());
            console.log(`📦 CSS minifiziert: ${cssFile}`);
        }
    });
}

function removeUnusedAssets(wwwPath) {
    // Entferne Development-spezifische Dateien
    const devFiles = [
        'js/dev-tools.js',
        'css/dev-styles.css',
        'test/',
        'docs/',
        '.gitkeep'
    ];
    
    devFiles.forEach(devFile => {
        const fullPath = path.join(wwwPath, devFile);
        if (fs.existsSync(fullPath)) {
            const stats = fs.statSync(fullPath);
            if (stats.isDirectory()) {
                fs.rmSync(fullPath, { recursive: true, force: true });
            } else {
                fs.unlinkSync(fullPath);
            }
            console.log(`🗑️ Development-Asset entfernt: ${devFile}`);
        }
    });
}

function updateServiceWorkerVersion(wwwPath) {
    const swPath = path.join(wwwPath, 'sw.js');
    
    if (fs.existsSync(swPath)) {
        let sw = fs.readFileSync(swPath, 'utf8');
        
        // Cache-Name mit aktuellem Timestamp aktualisieren
        const newCacheName = `voice-assistant-v${Date.now()}`;
        sw = sw.replace(/const CACHE_NAME = '[^']*'/, `const CACHE_NAME = '${newCacheName}'`);
        
        fs.writeFileSync(swPath, sw);
        console.log(`🔄 Service Worker Cache-Version aktualisiert: ${newCacheName}`);
    }
}

function configureReleaseAndroid(platformPath) {
    console.log('🤖 Konfiguriere Android für Release...');
    
    if (!fs.existsSync(platformPath)) return;
    
    // Gradle Build-Konfiguration optimieren
    const buildGradlePath = path.join(platformPath, 'app', 'build.gradle');
    
    if (fs.existsSync(buildGradlePath)) {
        let buildGradle = fs.readFileSync(buildGradlePath, 'utf8');
        
        // Proguard für Release aktivieren
        if (!buildGradle.includes('minifyEnabled true')) {
            buildGradle = buildGradle.replace(
                /release\s*{([^}]*)}/,
                'release {\n            minifyEnabled true\n            proguardFiles getDefaultProguardFile(\'proguard-android.txt\'), \'proguard-rules.pro\'\n$1}'
            );
        }
        
        // Zipalign aktivieren
        if (!buildGradle.includes('zipAlignEnabled true')) {
            buildGradle = buildGradle.replace(
                /release\s*{([^}]*)}/,
                'release {\n            zipAlignEnabled true\n$1}'
            );
        }
        
        fs.writeFileSync(buildGradlePath, buildGradle);
        console.log('📐 Android Build-Konfiguration für Release optimiert');
    }
    
    // Android Manifest für Release optimieren
    optimizeAndroidManifestForRelease(platformPath);
}

function optimizeAndroidManifestForRelease(platformPath) {
    const manifestPath = path.join(platformPath, 'app', 'src', 'main', 'AndroidManifest.xml');
    
    if (fs.existsSync(manifestPath)) {
        let manifest = fs.readFileSync(manifestPath, 'utf8');
        
        // Debug-Attribute entfernen
        manifest = manifest.replace(/android:debuggable="true"/g, 'android:debuggable="false"');
        
        // Allow Backup deaktivieren für bessere Sicherheit
        if (!manifest.includes('android:allowBackup')) {
            manifest = manifest.replace(
                '<application',
                '<application android:allowBackup="false"'
            );
        }
        
        fs.writeFileSync(manifestPath, manifest);
        console.log('📄 Android Manifest für Release optimiert');
    }
}

function configureDebugMode(wwwPath) {
    console.log('🔧 Konfiguriere Debug-Modus...');
    
    // Debug-spezifische Konfiguration
    const debugConfig = `
// Debug-Konfiguration
window.DEBUG_MODE = true;
window.DEBUG_CONFIG = {
    enableConsoleLog: true,
    showNetworkRequests: true,
    enablePerformanceMetrics: true,
    mockWebSocketConnection: false
};

console.log('🔧 Debug-Modus aktiviert');
`;
    
    const debugConfigPath = path.join(wwwPath, 'js', 'debug-config.js');
    
    // Stelle sicher, dass js-Ordner existiert
    const jsDir = path.dirname(debugConfigPath);
    if (!fs.existsSync(jsDir)) {
        fs.mkdirSync(jsDir, { recursive: true });
    }
    
    fs.writeFileSync(debugConfigPath, debugConfig);
    console.log('🔧 Debug-Konfiguration erstellt');
}

function validateBuildResources(projectRoot) {
    console.log('✅ Validiere Build-Ressourcen...');
    
    const requiredFiles = [
        'config.xml',
        'www/index.html',
        'www/js/app.js',
        'www/js/mobile-app.js'
    ];
    
    const missingFiles = [];
    
    requiredFiles.forEach(file => {
        const filePath = path.join(projectRoot, file);
        if (!fs.existsSync(filePath)) {
            missingFiles.push(file);
        }
    });
    
    if (missingFiles.length > 0) {
        console.error('❌ Fehlende erforderliche Dateien:');
        missingFiles.forEach(file => console.error(`   - ${file}`));
        throw new Error('Build kann nicht fortgesetzt werden - fehlende Dateien');
    }
    
    // Plugin-Validierung
    validateCordovaPlugins(projectRoot);
    
    console.log('✅ Alle erforderlichen Ressourcen vorhanden');
}

function validateCordovaPlugins(projectRoot) {
    const packageJsonPath = path.join(projectRoot, 'package.json');
    const configXmlPath = path.join(projectRoot, 'config.xml');
    
    if (fs.existsSync(packageJsonPath) && fs.existsSync(configXmlPath)) {
        // Prüfe ob alle Plugins aus config.xml auch in package.json sind
        const configXml = fs.readFileSync(configXmlPath, 'utf8');
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        
        const configPlugins = [...configXml.matchAll(/<plugin name="([^"]+)"/g)].map(match => match[1]);
        const packagePlugins = Object.keys(packageJson.cordova?.plugins || {});
        
        const missingPlugins = configPlugins.filter(plugin => !packagePlugins.includes(plugin));
        
        if (missingPlugins.length > 0) {
            console.warn('⚠️ Plugins in config.xml aber nicht in package.json:');
            missingPlugins.forEach(plugin => console.warn(`   - ${plugin}`));
        }
    }
}

function generateBuildStats(projectRoot, wwwPath) {
    console.log('📊 Generiere Build-Statistiken...');
    
    const stats = {
        timestamp: new Date().toISOString(),
        files: {},
        totalSize: 0,
        fileCount: 0
    };
    
    // Rekursiv alle Dateien in www durchgehen
    function analyzeDirectory(dir, relativePath = '') {
        const files = fs.readdirSync(dir);
        
        files.forEach(file => {
            const fullPath = path.join(dir, file);
            const relativeFilePath = path.join(relativePath, file);
            const stat = fs.statSync(fullPath);
            
            if (stat.isDirectory()) {
                analyzeDirectory(fullPath, relativeFilePath);
            } else {
                const fileSize = stat.size;
                const fileExt = path.extname(file);
                
                stats.files[relativeFilePath] = {
                    size: fileSize,
                    type: fileExt,
                    modified: stat.mtime.toISOString()
                };
                
                stats.totalSize += fileSize;
                stats.fileCount++;
            }
        });
    }
    
    analyzeDirectory(wwwPath);
    
    // Statistiken zusammenfassen
    const summary = {
        totalFiles: stats.fileCount,
        totalSizeMB: (stats.totalSize / 1024 / 1024).toFixed(2),
        byType: {}
    };
    
    Object.values(stats.files).forEach(file => {
        const type = file.type || 'no-extension';
        if (!summary.byType[type]) {
            summary.byType[type] = { count: 0, size: 0 };
        }
        summary.byType[type].count++;
        summary.byType[type].size += file.size;
    });
    
    // Statistiken in Build-Info einfügen
    const buildStatsPath = path.join(wwwPath, 'build-stats.json');
    fs.writeFileSync(buildStatsPath, JSON.stringify({ stats, summary }, null, 2));
    
    console.log(`📊 Build-Statistiken: ${summary.totalFiles} Dateien, ${summary.totalSizeMB} MB`);
    console.log('   Dateitypen:', Object.keys(summary.byType).join(', '));
}
