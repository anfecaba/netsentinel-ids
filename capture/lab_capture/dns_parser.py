"""Parser de consultas DNS sin cifrar.

Solo se leen consultas (``qr == 0``). Las respuestas se ignoran porque el
laboratorio mide qué pide el cliente, no qué responde el servidor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, UDP
from scapy.packet import Packet

from .models import make_dns_event

QTYPE_NAMES: Dict[int, str] = {
    1: "A",
    2: "NS",
    5: "CNAME",
    6: "SOA",
    12: "PTR",
    15: "MX",
    16: "TXT",
    28: "AAAA",
    33: "SRV",
    65: "HTTPS",
    255: "ANY",
}


def _qtype_name(value: Any) -> str:
    if isinstance(value, int):
        return QTYPE_NAMES.get(value, f"TYPE-{value}")
    if isinstance(value, str):
        return value
    return "TYPE-0"


def parse_dns_packet(
    packet: Packet, captured_at: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """Convierte un paquete DNS de consulta en un evento del contrato.

    Devuelve ``None`` para respuestas, paquetes sin DNS o consultas vacías.
    """

    if IP not in packet or UDP not in packet or DNS not in packet:
        return None

    dns = packet[DNS]
    try:
        is_response = int(getattr(dns, "qr", 0)) == 1
    except (TypeError, ValueError):
        is_response = False
    if is_response:
        return None

    question = dns.qd
    if question is None:
        return None

    first = question[0] if isinstance(question, list) else question
    if not isinstance(first, DNSQR):
        return None

    qname = first.qname
    if isinstance(qname, bytes):
        qname = qname.decode("utf-8", errors="replace")
    if not qname:
        return None
    query = str(qname).rstrip(".")

    ip_layer = packet[IP]
    udp_layer = packet[UDP]

    return make_dns_event(
        source_ip=str(ip_layer.src),
        destination_ip=str(ip_layer.dst),
        query=query,
        qtype=_qtype_name(getattr(first, "qtype", None)),
        captured_at=captured_at,
        source_port=int(udp_layer.sport),
        destination_port=int(udp_layer.dport),
        encrypted=False,
        synthetic=False,
    )
