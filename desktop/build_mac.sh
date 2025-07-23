#!/bin/bash
echo "Building agent for macOS..."
python3 -m venv aiagent/venv
source aiagent/venv/bin/activate
pip install -r aiagent/requirements.txt
npm run build:agent:mac
npm run build:suggestor:mac
deactivate
echo "Done."
