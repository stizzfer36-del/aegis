#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-pip docker.io docker-compose-plugin cloudflared
python3 -m pip install -e /opt/aegis
sudo tee /etc/systemd/system/aegis-kernel.service >/dev/null <<'UNIT'
[Unit]
Description=AEGIS Kernel
After=network.target docker.service

[Service]
Type=simple
WorkingDirectory=/opt/aegis
ExecStart=/usr/bin/python3 -m kernel.introspect demo-flow
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now aegis-kernel.service
