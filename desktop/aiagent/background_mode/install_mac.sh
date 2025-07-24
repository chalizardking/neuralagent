#!/bin/bash
set -e

echo "[*] Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
  echo "Homebrew not found. Please install it from https://brew.sh/"
  exit 1
fi

echo "[*] Updating Homebrew..."
brew update

echo "[*] Installing dependencies..."
brew install --cask xquartz
brew install --cask google-chrome

echo "[*] Enabling screen sharing..."
# This is for the built-in VNC server
# May require administrative privileges
sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.screensharing.plist

echo "[✅] Setup complete: XQuartz, Google Chrome, and Screen Sharing enabled."
