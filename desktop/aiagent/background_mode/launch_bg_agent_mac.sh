#!/bin/bash

export DISPLAY=:99
mkdir -p /agent/profile

echo "[*] Starting Xvfb..."
Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &
echo $! > /tmp/bg_xvfb.pid

# Wait until Xvfb is ready
tries=0
while ! xdpyinfo -display :99 >/dev/null 2>&1; do
  sleep 0.5
  tries=$((tries + 1))
  if [ "$tries" -gt 20 ]; then
    echo "❌ Xvfb failed to start."
    exit 1
  fi
done

echo "[*] Clearing previous Chrome session files..."
rm -f /agent/profile/Default/Last* /agent/profile/Default/Sessions/*

echo "[*] Launching Google Chrome with persistent profile and remote debugging..."
/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \
  --no-sandbox \
  --test-type \
  --disable-gpu \
  --disable-accelerated-2d-canvas \
  --force-device-scale-factor=1 \
  --remote-debugging-port=13783 \
  --user-data-dir=/agent/profile \
  --no-first-run \
  --restore-last-session=false \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --disable-default-apps \
  --disable-notifications \
  --window-size=1280,720 \
  https://www.google.com &

echo $! > /tmp/bg_chrome.pid
export BROWSER_CDP_URL=http://127.0.0.1:13783
sleep 2

echo "[*] Starting VNC server..."
# The VNC server is enabled via the install script.
# We just need to make sure it's running.
# The following command will start the VNC server if it's not already running.
sudo /System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -activate -configure -access -on -users admin -privs -all -restart -agent -menu

echo "[*] Launching NeuralAgent AI agent..."
# Assuming the agent executable is in the same directory as the script
"$(dirname "$0")/../agent"
