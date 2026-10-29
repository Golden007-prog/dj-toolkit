#!/bin/bash
# macOS: double-click to start DJ Toolkit from source (after the setup in docs/getting-started.md).
# Most people should download the app instead: see the README.
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python main.py
