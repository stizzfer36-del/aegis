#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="$(cd "$(dirname "$0")/.." && pwd)"
OS="$(uname -s)"

if [[ "$OS" == "Linux" ]]; then
  sudo tee /etc/systemd/system/aegis.service >/dev/null <<EOF
[Unit]
Description=AEGIS chat service
After=network.target

[Service]
WorkingDirectory=$REPO_PATH
ExecStart=/usr/bin/env python $REPO_PATH/chat.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
  sudo tee /etc/systemd/system/aegis-lens.service >/dev/null <<EOF
[Unit]
Description=AEGIS lens service
After=network.target

[Service]
WorkingDirectory=$REPO_PATH/lens
ExecStart=/usr/bin/env npm start
Restart=always

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable aegis
  sudo systemctl enable aegis-lens
elif [[ "$OS" == "Darwin" ]]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$HOME/Library/LaunchAgents/com.aegis.chat.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.aegis.chat</string><key>ProgramArguments</key><array><string>/usr/bin/env</string><string>python</string><string>$REPO_PATH/chat.py</string></array><key>RunAtLoad</key><true/></dict></plist>
EOF
  cat > "$HOME/Library/LaunchAgents/com.aegis.lens.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.aegis.lens</string><key>ProgramArguments</key><array><string>/usr/bin/env</string><string>npm</string><string>start</string></array><key>WorkingDirectory</key><string>$REPO_PATH/lens</string><key>RunAtLoad</key><true/></dict></plist>
EOF
else
  echo "Use scripts/install_boot.ps1 on Windows."
fi
