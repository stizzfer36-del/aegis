#!/usr/bin/env bash
set -euo pipefail

OS="$(uname -s)"
echo "Detected OS: $OS"
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[all]'
playwright install chromium || true
(
  cd lens
  npm install
)
docker compose up -d
python3 -m kernel.introspect doctor
