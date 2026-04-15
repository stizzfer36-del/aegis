from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass
class SoftwareToolBinding:
    name: str
    description: str
    available: bool
    path: str | None
    source: str = "software"


_TOOL_GROUPS = {
    "python3": "Python interpreter",
    "python": "Python interpreter",
    "node": "Node.js runtime",
    "npm": "Node package manager",
    "git": "Version control",
    "docker": "Container runtime",
    "docker-compose": "Container orchestration",
    "curl": "HTTP client",
    "wget": "Download utility",
    "ffmpeg": "Media transcoding",
    "vim": "Terminal editor",
    "nano": "Terminal editor",
    "code": "VS Code",
    "aider": "AI coding assistant",
    "google-chrome": "Chrome browser",
    "chromium": "Chromium browser",
    "firefox": "Firefox browser",
    "brave-browser": "Brave browser",
    "msedge": "Microsoft Edge",
    "nmap": "Network scanner",
    "bettercap": "Network attack framework",
    "aircrack-ng": "WiFi auditing suite",
    "airodump-ng": "WiFi packet capture",
    "aireplay-ng": "WiFi injection",
    "rtl_adsb": "ADS-B decoder",
    "dump1090": "ADS-B decoder",
    "netdiscover": "ARP discovery",
    "masscan": "High-speed scanner",
    "hydra": "Password audit tool",
    "hashcat": "Password recovery",
    "john": "Password recovery",
    "sqlmap": "SQL injection testing",
    "nikto": "Web scanner",
    "burpsuite": "Web proxy scanner",
    "wireshark": "Packet analyzer",
    "tcpdump": "Packet sniffer",
    "metasploit": "Penetration testing framework",
    "msfconsole": "Metasploit console",
    "bluetoothctl": "Bluetooth control",
    "hcitool": "Bluetooth utility",
    "btmgmt": "Bluetooth manager",
    "rtl_test": "RTL-SDR test",
    "rtl_fm": "RTL-SDR demod",
    "rtl_sdr": "RTL-SDR capture",
    "gqrx": "SDR receiver",
    "gnuradio": "SDR toolkit",
    "arduino-cli": "Arduino CLI",
    "esptool": "ESP flashing tool",
    "avrdude": "AVR flasher",
    "openocd": "On-chip debugger",
    "picocom": "Serial terminal",
    "minicom": "Serial terminal",
    "screen": "Terminal multiplexer",
    "vlc": "Media player",
    "mpv": "Media player",
    "obs": "Streaming recorder",
    "gimp": "Image editor",
    "inkscape": "Vector editor",
    "libreoffice": "Office suite",
}


def get_available_tools() -> list[SoftwareToolBinding]:
    items: list[SoftwareToolBinding] = []
    for binary, description in _TOOL_GROUPS.items():
        path = shutil.which(binary)
        items.append(SoftwareToolBinding(name=binary, description=description, available=bool(path), path=path))
    return items
