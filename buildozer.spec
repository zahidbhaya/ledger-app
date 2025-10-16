[app]
# ── Identity ────────────────────────────────────────────────────────────────
title = Ledger
package.name = ledger
package.domain = org.aktest

# Versioning
version = 1.0
numeric_version = 10000

# ── Sources / Assets ────────────────────────────────────────────────────────
source.dir = .
entrypoint = main.py
# Include common assets + fonts (OTF so your custom font won’t crash on launch)
source.include_exts = py,kv,png,jpg,jpeg,webp,gif,svg,ttf,otf,txt,json,ini,xml
# If you keep structured assets/data, they’ll be bundled:
source.include_patterns = assets/*, assets/**, data/*, data/**

# Keep build folder if error occurs
buildozer.clean_build_on_error = 0

# ── Runtime / Window ───────────────────────────────────────────────────────
orientation = portrait
fullscreen = 1
log_level = 2

# ── Python-for-Android / Deps ──────────────────────────────────────────────
# Notes:
# - sqlite3: local DB for clients & unique mobile constraint
# - fpdf2: PDF generation (lists & individual entries)
# - android: for ACTION_SEND sharing (share PDFs to Gmail/WhatsApp/Drive)
# - openssl/certifi/urllib3/requests: stable HTTPS if you ever sync/backup
requirements = python3,kivy==2.3.0,sqlite3,fpdf2,android,openssl,certifi,urllib3,requests,plyer
p4a.python = 3.11
p4a.bootstrap = sdl2
p4a.branch = master

# ── Android Targets / NDK / Arch ───────────────────────────────────────────
android.minapi = 21
android.api = 34
android.target = 34
android.ndk = 25c
android.archs = arm64-v8a,armeabi-v7a

# ── Permissions ────────────────────────────────────────────────────────────
# Keep minimal. INTERNET only if you plan to sync/back up later.
# Sharing PDFs via Android’s share sheet does NOT require storage permissions
# when you share from app-internal files via a FileProvider/SAF intent.
android.permissions = INTERNET

# If you absolutely must write directly to external "Downloads" on old Androids,
# you could add (deprecated on API 30+): WRITE_EXTERNAL_STORAGE
# Prefer SAF/Share Intent in code instead of adding storage permissions.

# ── Packaging / Gradle (safe defaults) ─────────────────────────────────────
# Let p4a manage Gradle; custom paths cause issues across machines.
use_system_gradle = 0

# ── Optional: Icons / Presplash (uncomment & set if you have them) ─────────
# icon.filename = assets/icon.png
# presplash.filename = assets/presplash.png
# presplash.keep_ratio = 1
# presplash_color = #222222

# ── Optional: Logcat filter while debugging ────────────────────────────────
# android.logcat_filters = *:S python:D AndroidRuntime:E

[buildozer]
log_level = 2
warn_on_root = 1
