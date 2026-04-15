"""Network Sniffing — Scapy / tshark / mitmproxy integrations."""
from __future__ import annotations


class NetworkSniffingTopic:
    name = "network_sniffing"
    tools = ["wireshark", "scapy", "zeek", "suricata", "mitmproxy", "networkminer", "tshark"]

    def capture(self, iface: str = "eth0", count: int = 100) -> list:
        try:
            from scapy.all import sniff
            pkts = sniff(iface=iface, count=count, timeout=10)
            return [str(p.summary()) for p in pkts]
        except ImportError:
            return ["scapy not installed — pip install scapy"]
