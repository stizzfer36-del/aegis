from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List


def wifi_scan() -> Dict[str, Any]:
    try:
        from scapy.all import Dot11, sniff  # type: ignore

        seen = {}

        def cb(pkt):
            if pkt.haslayer(Dot11):
                bssid = pkt[Dot11].addr2
                ssid = (pkt.info.decode(errors="ignore") if hasattr(pkt, "info") else "") or "<hidden>"
                if bssid and bssid not in seen:
                    seen[bssid] = {"ssid": ssid, "bssid": bssid, "channel": None, "signal_dbm": None, "encryption": None}

        sniff(prn=cb, timeout=5, store=False)
        return {"networks": list(seen.values())}
    except Exception:
        pass

    try:
        proc = subprocess.run(["iwlist", "scan"], capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            return {"error": proc.stderr.strip() or "iwlist failed", "networks": []}
        out = []
        cell = {"ssid": "", "bssid": "", "channel": None, "signal_dbm": None, "encryption": None}
        for line in proc.stdout.splitlines():
            s = line.strip()
            if s.startswith("Cell") and "Address:" in s:
                if cell.get("bssid"):
                    out.append(cell)
                cell = {"ssid": "", "bssid": s.split("Address:")[-1].strip(), "channel": None, "signal_dbm": None, "encryption": None}
            elif "ESSID:" in s:
                cell["ssid"] = s.split("ESSID:", 1)[1].strip().strip('"')
            elif "Channel:" in s:
                cell["channel"] = s.split("Channel:", 1)[1].strip()
            elif "Signal level=" in s:
                cell["signal_dbm"] = s.split("Signal level=", 1)[1].split()[0]
            elif "Encryption key:" in s:
                cell["encryption"] = "on" if s.endswith("on") else "off"
        if cell.get("bssid"):
            out.append(cell)
        return {"networks": out}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"wifi scan unavailable: {exc}", "networks": []}


def bluetooth_scan(timeout: float = 5.0) -> Dict[str, Any]:
    try:
        import asyncio
        from bleak import BleakScanner

        async def _scan():
            devices = await BleakScanner.discover(timeout=timeout)
            return [{"name": d.name or "", "address": d.address, "rssi": getattr(d, "rssi", None)} for d in devices]

        return {"devices": asyncio.run(_scan())}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"bluetooth scan unavailable: {exc}", "devices": []}


def bettercap_command(cmd: str) -> Dict[str, Any]:
    import urllib.request

    payload = json.dumps({"cmd": cmd}).encode("utf-8")
    req = urllib.request.Request("http://localhost:8083/api/session", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def network_scan(target: str = "192.168.1.0/24") -> Dict[str, Any]:
    try:
        import nmap
    except ImportError as exc:
        raise ImportError("python-nmap not installed — pip install python-nmap") from exc
    scanner = nmap.PortScanner()
    scanner.scan(hosts=target, arguments="-sV -O --open")
    hosts: List[Dict[str, Any]] = []
    for host in scanner.all_hosts():
        tcp = scanner[host].get("tcp", {})
        ports = [int(p) for p, pdata in tcp.items() if pdata.get("state") == "open"]
        os_guess = ""
        matches = scanner[host].get("osmatch", [])
        if matches:
            os_guess = matches[0].get("name", "")
        hosts.append({"ip": host, "hostname": scanner[host].hostname(), "open_ports": ports, "os_guess": os_guess})
    return {"hosts": hosts}
