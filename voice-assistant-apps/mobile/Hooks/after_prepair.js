#!/usr/bin/env node

'use strict';

const fs = require('fs');
const path = require('path');

module.exports = function(context) {
    console.log('🔧 After Prepare Hook: Mobile App anpassen');

    const platformPath = path.join(context.opts.projectRoot, 'platforms', 'android');
    const wwwPath = path.join(context.opts.projectRoot, 'www');
    
    if (fs.existsSync(platformPath)) {
        // Android-spezifische Anpassungen
        configureAndroidApp(context, platformPath, wwwPath);
    }
    
    // Allgemeine Mobile-Anpassungen
    configureMobileFeatures(context, wwwPath);
    
    console.log('✅ After Prepare Hook abgeschlossen');
};

function configureAndroidApp(context, platformPath, wwwPath) {
    console.log('📱 Konfiguriere Android-spezifische Features...');
    
    // Network Security Config für HTTP-Verbindungen
    createNetworkSecurityConfig(platformPath);
    
    // Android-spezifische Permissions optimieren
    optimizeAndroidPermissions(platformPath);
    
    // Proguard-Konfiguration für Release-Builds
    configureProguard(platformPath);
    
    // Icons und Splash Screens validieren
    validateAndroidAssets(platformPath);
}

function createNetworkSecurityConfig(platformPath) {
    const networkConfigPath = path.join(platformPath, 'app', 'src', 'main', 'res', 'xml');
    const networkConfigFile = path.join(networkConfigPath, 'network_security_config.xml');
    
    // Erstelle xml-Ordner falls nicht vorhanden
    if (!fs.existsSync(networkConfigPath)) {
        fs.mkdirSync(networkConfigPath, { recursive: true });
    }
    
    const networkSecurityConfig = `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">127.0.0.1</domain>
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">raspi4.local</domain>
        <domain includeSubdomains="true">*.tailscale.net</domain>
        <domain includeSubdomains="true">*.ts.net</domain>
    </domain-config>
    <base-config cleartextTrafficPermitted="false" />
</network-security-config>`;

    fs.writeFileSync(networkConfigFile, networkSecurityConfig);
    console.log('📄 Network Security Config erstellt');
    
    // Referenz in AndroidManifest.xml hinzufügen
    updateAndroidManifest(platformPath);
}

function updateAndroidManifest(platformPath) {
    const manifestPath = path.join(platformPath, 'app', 'src', 'main', 'AndroidManifest.xml');
    
    if (fs.existsSync(manifestPath)) {
        let manifest = fs.readFileSync(manifestPath, 'utf8');
        
        // Network Security Config hinzufügen falls nicht vorhanden
        if (!manifest.includes('android:networkSecurityConfig')) {
            manifest = manifest.replace(
                '<application',
                '<application android:networkSecurityConfig="@xml/network_security_config"'
            );
            
            fs.writeFileSync(manifestPath, manifest);
            console.log('📄 AndroidManifest.xml aktualisiert');
        }
    }
}

function optimizeAndroidPermissions(platformPath) {
    const manifestPath = path.join(platformPath, 'app', 'src', 'main', 'AndroidManifest.xml');
    
    if (fs.existsSync(manifestPath)) {
        let manifest = fs.readFileSync(manifestPath, 'utf8');
        
        // Entferne unnötige Permissions für bessere Store-Akzeptanz
        const unnecessaryPermissions = [
            'android.permission.ACCESS_COARSE_LOCATION',
            'android.permission.ACCESS_FINE_LOCATION',
            'android.permission.CAMERA'
        ];
        
        unnecessaryPermissions.forEach(permission => {
            const permissionRegex = new RegExp(`\\s*<uses-permission android:name="${permission}"[^>]*/>`, 'g');
            manifest = manifest.replace(permissionRegex, '');
        });
        
        fs.writeFileSync(manifestPath, manifest);
        console.log('🔒 Android Permissions optimiert');
    }
}

function configureProguard(platformPath) {
    const proguardPath = path.join(platformPath, 'app', 'proguard-rules.pro');
    
    const proguardRules = `
# Voice Assistant App - Proguard Rules
-keep class com.voiceassistant.mobile.** { *; }
-keep class org.apache.cordova.** { *; }

# Keep JavaScript Interface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# WebView related
-keep class android.webkit.** { *; }
-dontwarn android.webkit.**

# Audio/Media related
-keep class android.media.** { *; }
-keep class androidx.media.** { *; }

# Network related
-keep class okhttp3.** { *; }
-keep class retrofit2.** { *; }
-dontwarn okhttp3.**
-dontwarn retrofit2.**

# Cordova plugins
-keep class org.apache.cordova.whitelist.** { *; }
-keep class org.apache.cordova.statusbar.** { *; }
-keep class org.apache.cordova.device.** { *; }
-keep class org.apache.cordova.splashscreen.** { *; }
-keep class org.apache.cordova.networkinfo.** { *; }
-keep class org.apache.cordova.vibration.** { *; }
-keep class org.apache.cordova.mediacapture.** { *; }
-keep class org.apache.cordova.media.** { *; }
-keep class org.apache.cordova.file.** { *; }

# Remove logging in release builds
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}
`;

    fs.writeFileSync(proguardPath, proguardRules);
    console.log('🛡️ Proguard-Regeln konfiguriert');
}

function validateAndroidAssets(platformPath) {
    const requiredIcons = [
        'app/src/main/res/mipmap-ldpi/ic_launcher.png',
        'app/src/main/res/mipmap-mdpi/ic_launcher.png',
        'app/src/main/res/mipmap-hdpi/ic_launcher.png',
        'app/src/main/res/mipmap-xhdpi/ic_launcher.png',
        'app/src/main/res/mipmap-xxhdpi/ic_launcher.png',
        'app/src/main/res/mipmap-xxxhdpi/ic_launcher.png'
    ];
    
    const requiredSplashScreens = [
        'app/src/main/res/drawable-land-ldpi/screen.png',
        'app/src/main/res/drawable-land-mdpi/screen.png',
        'app/src/main/res/drawable-land-hdpi/screen.png',
        'app/src/main/res/drawable-port-ldpi/screen.png',
        'app/src/main/res/drawable-port-mdpi/screen.png',
        'app/src/main/res/drawable-port-hdpi/screen.png'
    ];
    
    const missingAssets = [];
    
    [...requiredIcons, ...requiredSplashScreens].forEach(asset => {
        const assetPath = path.join(platformPath, asset);
        if (!fs.existsSync(assetPath)) {
            missingAssets.push(asset);
        }
    });
    
    if (missingAssets.length > 0) {
        console.warn('⚠️ Fehlende Assets:');
        missingAssets.forEach(asset => console.warn(`   - ${asset}`));
        console.warn('   Verwende: cordova-res android --skip-config --copy');
    } else {
        console.log('✅ Alle Android Assets vorhanden');
    }
}

function configureMobileFeatures(context, wwwPath) {
    console.log('📱 Konfiguriere Mobile Features...');
    
    // Service Worker für bessere Performance
    createServiceWorker(wwwPath);
    
    // Manifest.json für PWA-Features
    createWebAppManifest(wwwPath);
    
    // Mobile-spezifische Meta-Tags optimieren
    optimizeMobileHTML(wwwPath);
}

function createServiceWorker(wwwPath) {
    const swPath = path.join(wwwPath, 'sw.js');
    
    const serviceWorker = `
// Voice Assistant Service Worker
const CACHE_NAME = 'voice-assistant-v2.1.0';
const urlsToCache = [
  '/',
  '/index.html',
  '/js/app.js',
  '/js/mobile-app.js',
  '/css/app.css'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  // Nur GET-Requests cachen
  if (event.request.method !== 'GET') return;
  
  // WebSocket-Verbindungen nicht cachen
  if (event.request.url.includes('ws://') || event.request.url.includes('wss://')) return;
  
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
`;

    fs.writeFileSync(swPath, serviceWorker);
    console.log('🔄 Service Worker erstellt');
}

function createWebAppManifest(wwwPath) {
    const manifestPath = path.join(wwwPath, 'manifest.json');
    
    const manifest = {
        "name": "KI-Sprachassistent",
        "short_name": "VoiceAssistant",
        "description": "Intelligenter Sprachassistent für mobile Geräte",
        "version": "2.1.0",
        "start_url": "/",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": "#0f0f23",
        "background_color": "#0f0f23",
        "icons": [
            {
                "src": "res/android/icon/drawable-ldpi-icon.png",
                "sizes": "36x36",
                "type": "image/png",
                "density": "0.75"
            },
            {
                "src": "res/android/icon/drawable-mdpi-icon.png",
                "sizes": "48x48",
                "type": "image/png",
                "density": "1.0"
            },
            {
                "src": "res/android/icon/drawable-hdpi-icon.png",
                "sizes": "72x72",
                "type": "image/png",
                "density": "1.5"
            },
            {
                "src": "res/android/icon/drawable-xhdpi-icon.png",
                "sizes": "96x96",
                "type": "image/png",
                "density": "2.0"
            },
            {
                "src": "res/android/icon/drawable-xxhdpi-icon.png",
                "sizes": "144x144",
                "type": "image/png",
                "density": "3.0"
            },
            {
                "src": "res/android/icon/drawable-xxxhdpi-icon.png",
                "sizes": "192x192",
                "type": "image/png",
                "density": "4.0"
            }
        ]
    };
    
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    console.log('📄 Web App Manifest erstellt');
}

function optimizeMobileHTML(wwwPath) {
    const htmlPath = path.join(wwwPath, 'index.html');
    
    if (fs.existsSync(htmlPath)) {
        let html = fs.readFileSync(htmlPath, 'utf8');
        
        // Füge PWA-Meta-Tags hinzu
        const pwaMetaTags = `
  <!-- PWA Meta Tags -->
  <link rel="manifest" href="manifest.json">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="KI-Assistent">
  
  <!-- Service Worker Registration -->
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
          .then((registration) => {
            console.log('SW registered: ', registration);
          })
          .catch((registrationError) => {
            console.log('SW registration failed: ', registrationError);
          });
      });
    }
  </script>`;
        
        // Füge Meta-Tags vor </head> ein
        html = html.replace('</head>', pwaMetaTags + '\n</head>');
        
        fs.writeFileSync(htmlPath, html);
        console.log('📱 Mobile HTML optimiert');
    }
}`;

fs.writeFileSync(hookPath, hookContent);
console.log('✅ After Prepare Hook erstellt');
}

createAfterPrepareHook();
