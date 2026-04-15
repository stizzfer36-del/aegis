from __future__ import annotations

import platform
import socket
import time
from typing import Any, Dict, List

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


def _missing() -> Dict[str, Any]:
    return {"error": "psutil not installed — pip install psutil"}


def sys_info() -> Dict[str, Any]:
    if psutil is None:
        return _missing()
    vm = psutil.virtual_memory()
    disks: List[Dict[str, Any]] = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        disks.append({"mount": part.mountpoint, "used": usage.used, "total": usage.total, "percent": usage.percent})
    return {"cpu_percent": psutil.cpu_percent(interval=0.1), "ram": {"used": vm.used, "total": vm.total, "percent": vm.percent, "free": vm.available}, "disk": disks, "uptime_seconds": int(time.time() - psutil.boot_time()), "hostname": socket.gethostname(), "os": platform.platform()}


def process_list() -> Dict[str, Any]:
    if psutil is None:
        return _missing()
    procs: List[Dict[str, Any]] = []
    for p in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_info", "status"]):
        info = p.info
        mem = float(getattr(info.get("memory_info"), "rss", 0.0)) / (1024 * 1024)
        procs.append({"pid": info.get("pid"), "name": info.get("name") or "", "cpu_percent": float(info.get("cpu_percent") or 0.0), "memory_mb": round(mem, 2), "status": info.get("status") or "unknown"})
    return {"processes": sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:20]}


def network_interfaces() -> Dict[str, Any]:
    if psutil is None:
        return _missing()
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    counters = psutil.net_io_counters(pernic=True)
    interfaces: List[Dict[str, Any]] = []
    for name, nic_addrs in addrs.items():
        ip = ""
        mac = ""
        for addr in nic_addrs:
            fam = str(getattr(addr, "family", ""))
            if fam.endswith("AF_INET") or fam == "2":
                ip = addr.address
            elif "AF_PACKET" in fam or fam in {"17", "-1"}:
                mac = addr.address
        nic_counter = counters.get(name)
        interfaces.append({"name": name, "ip": ip, "mac": mac, "bytes_sent": int(getattr(nic_counter, "bytes_sent", 0)), "bytes_recv": int(getattr(nic_counter, "bytes_recv", 0)), "is_up": bool(getattr(stats.get(name), "isup", False))})
    return {"interfaces": interfaces}


def battery_status() -> Dict[str, Any]:
    if psutil is None:
        return _missing()
    battery = psutil.sensors_battery()
    if battery is None:
        return {"percent": None, "plugged_in": None, "minutes_remaining": None}
    mins = None if battery.secsleft in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) else int(battery.secsleft / 60)
    return {"percent": battery.percent, "plugged_in": battery.power_plugged, "minutes_remaining": mins}
