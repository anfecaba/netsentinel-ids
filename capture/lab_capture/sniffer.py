"""Motor de captura pasiva con Scapy.

No inyecta paquetes, no altera ARP y no intenta romper TLS: solo lee lo que
la interfaz ya recibe. Cualquier limitación de red conmutada se documenta en
``capture/README.md``.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import Packet

from .config import DEFAULT_BPF, DNS_PORT, HTTP_PORTS, MAX_HTTP_BUFFER, TLS_PORTS
from .credentials import extract_credentials
from .dns_parser import parse_dns_packet
from .http_parser import HttpRequestAssembler
from .models import (
    make_credential_event,
    make_flow_event,
)

EventCallback = Callable[[Dict[str, Any]], None]


def _timestamp(packet: Packet) -> datetime:
    try:
        return datetime.fromtimestamp(float(packet.time), tz=timezone.utc)
    except (AttributeError, TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


def list_interfaces() -> List[Dict[str, Any]]:
    """Lista interfaces de captura de forma serializable.

    En Windows devuelve nombre de dispositivo, descripción, MAC e IPs. En
    Linux devuelve los nombres de ``get_if_list``.
    """

    if sys.platform.startswith("win"):
        try:
            from scapy.arch.windows import get_windows_if_list
        except Exception as error:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                "No se pudo cargar el soporte de Windows de Scapy. "
                "Instala Npcap (https://npcap.com) y vuelve a intentarlo."
            ) from error

        try:
            entries = get_windows_if_list()
        except Exception as error:  # pragma: no cover - depende del entorno
            raise RuntimeError(
                "Npcap no responde. Instala Npcap con el modo compatible "
                "WinPcap y ejecuta la consola como administrador."
            ) from error

        return [
            {
                "name": entry.get("name", ""),
                "description": entry.get("description", "") or entry.get("name", ""),
                "mac": entry.get("mac", ""),
                "ips": entry.get("ips", []),
            }
            for entry in entries
        ]

    try:
        from scapy.interfaces import get_if_list
    except Exception as error:  # pragma: no cover
        raise RuntimeError(
            "Scapy no pudo enumerar interfaces. Instala libpcap "
            "(paquete libpcap-dev en Debian/Ubuntu) y ejecuta con sudo."
        ) from error

    return [
        {"name": name, "description": name, "mac": "", "ips": []}
        for name in get_if_list()
    ]


def resolve_interface(name: str) -> str:
    """Acepta un nombre o una descripción y devuelve el nombre de Scapy."""

    try:
        for entry in list_interfaces():
            if name in (entry["name"], entry["description"]):
                return entry["name"]
            if name and name.lower() in str(entry["description"]).lower():
                return entry["name"]
    except RuntimeError:
        return name
    return name


class CaptureEngine:
    """Diseca paquetes y emite eventos del contrato Visual MITM."""

    def __init__(
        self,
        iface: str,
        on_event: EventCallback,
        bpf_filter: str = DEFAULT_BPF,
    ) -> None:
        self.iface = iface
        self.on_event = on_event
        self.bpf_filter = bpf_filter
        self.assembler = HttpRequestAssembler(MAX_HTTP_BUFFER)
        self._running = False

        self.packets_seen = 0
        self.flows_emitted = 0
        self.credentials_found = 0
        self.dns_queries = 0

    # ------------------------------------------------------------------
    # Emisión
    # ------------------------------------------------------------------
    def _emit(self, event: Dict[str, Any]) -> None:
        try:
            self.on_event(event)
        except Exception:  # pragma: no cover - el callback no debe tumbar la captura
            pass

    # ------------------------------------------------------------------
    # Disección
    # ------------------------------------------------------------------
    def handle_packet(self, packet: Packet) -> None:
        self.packets_seen += 1

        if IP not in packet:
            return

        captured_at = _timestamp(packet)
        ip_layer = packet[IP]

        if UDP in packet and int(packet[UDP].dport) == DNS_PORT:
            self._handle_dns(packet, captured_at)
            return

        if TCP not in packet:
            return

        tcp_layer = packet[TCP]
        source_port = int(tcp_layer.sport)
        destination_port = int(tcp_layer.dport)

        if destination_port in TLS_PORTS:
            self._handle_tls(packet, captured_at)
            return

        if destination_port in HTTP_PORTS:
            self._handle_http(packet, captured_at)

    def _handle_dns(self, packet: Packet, captured_at: datetime) -> None:
        event = parse_dns_packet(packet, captured_at)
        if not event:
            return

        self.dns_queries += 1
        self._emit(event)

        ip_layer = packet[IP]
        self.flows_emitted += 1
        self._emit(
            make_flow_event(
                source_ip=str(ip_layer.src),
                source_port=int(packet[UDP].sport),
                destination_ip=str(ip_layer.dst),
                destination_port=int(packet[UDP].dport),
                protocol="DNS",
                encrypted=False,
                bytes_transferred=len(bytes(packet)),
                risk_level="warning",
                captured_at=captured_at,
                host=str(event["query"]),
                note="Consulta DNS sin cifrar: el proveedor ve qué dominios visitas",
            )
        )

    def _handle_tls(self, packet: Packet, captured_at: datetime) -> None:
        tcp_layer = packet[TCP]
        payload = bytes(tcp_layer.payload) if tcp_layer.payload else b""
        if not payload:
            return

        ip_layer = packet[IP]
        self.flows_emitted += 1
        self._emit(
            make_flow_event(
                source_ip=str(ip_layer.src),
                source_port=int(tcp_layer.sport),
                destination_ip=str(ip_layer.dst),
                destination_port=int(tcp_layer.dport),
                protocol="HTTPS",
                encrypted=True,
                bytes_transferred=len(payload),
                risk_level="safe",
                captured_at=captured_at,
                note="Solo metadatos TLS; el payload no se descifra",
            )
        )

    def _handle_http(self, packet: Packet, captured_at: datetime) -> None:
        tcp_layer = packet[TCP]
        payload = bytes(tcp_layer.payload) if tcp_layer.payload else b""
        if not payload:
            return

        ip_layer = packet[IP]
        requests = self.assembler.feed(
            source_ip=str(ip_layer.src),
            source_port=int(tcp_layer.sport),
            destination_ip=str(ip_layer.dst),
            destination_port=int(tcp_layer.dport),
            seq=int(getattr(tcp_layer, "seq", 0) or 0),
            payload=payload,
            timestamp=captured_at,
        )

        for request in requests:
            fields = extract_credentials(request)
            has_credentials = bool(fields)

            self.flows_emitted += 1
            flow = make_flow_event(
                source_ip=request.source_ip,
                source_port=request.source_port,
                destination_ip=request.destination_ip,
                destination_port=request.destination_port,
                protocol="HTTP",
                encrypted=False,
                bytes_transferred=max(request.raw_bytes, len(request.body)),
                risk_level="danger" if has_credentials else "warning",
                captured_at=captured_at,
                host=request.host or None,
                method=request.method,
                path=request.path,
                note=(
                    "POST con credenciales en texto plano"
                    if has_credentials
                    else "HTTP sin cifrar"
                ),
            )
            self._emit(flow)

            if not has_credentials:
                continue

            self.credentials_found += 1
            self._emit(
                make_credential_event(
                    source_ip=request.source_ip,
                    destination_ip=request.destination_ip,
                    host=request.host or request.destination_ip,
                    method=request.method,
                    path=request.path,
                    fields=fields,
                    captured_at=captured_at,
                    flow_id=str(flow["id"]),
                )
            )

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._running = False

    def start(self) -> None:
        """Arranca ``sniff`` en modo promiscuo (bloqueante)."""

        from scapy.all import sniff

        self._running = True
        try:
            sniff(
                iface=self.iface,
                filter=self.bpf_filter,
                prn=self.handle_packet,
                store=False,
                promisc=True,
                stop_filter=lambda _packet: not self._running,
            )
        except PermissionError as error:
            raise RuntimeError(
                "Permisos insuficientes para capturar. En Linux usa sudo; "
                "en Windows abre PowerShell como administrador."
            ) from error
        except OSError as error:
            raise RuntimeError(
                f"No se pudo abrir la interfaz '{self.iface}'. Verifica Npcap "
                f"(Windows) o libpcap (Linux) y el nombre con --list-ifaces. "
                f"Detalle: {error}"
            ) from error

    def stats(self, clients: int = 0, queue: int = 0) -> Dict[str, Any]:
        from .models import make_stats_event

        return make_stats_event(
            packets=self.packets_seen,
            flows=self.flows_emitted,
            credentials=self.credentials_found,
            dns_queries=self.dns_queries,
            pps=0.0,
            clients=clients,
            queue=queue,
        )
