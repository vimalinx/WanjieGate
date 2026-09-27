#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
app="$PWD/.data/native/Wanjie Intent.app"
mkdir -p "$app/Contents/MacOS"
swiftc integrations/vicinae/IntentPanel.swift -o "$app/Contents/MacOS/WanjieIntent" -framework Cocoa -framework WebKit
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>WanjieIntent</string>
<key>CFBundleIdentifier</key><string>local.wanjiegate.intent-panel</string>
<key>CFBundleName</key><string>万界门 · 意图泡泡</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSUIElement</key><true/>
<key>NSHighResolutionCapable</key><true/>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST
codesign --force --sign - "$app" >/dev/null 2>&1
printf '%s\n' "$app"
