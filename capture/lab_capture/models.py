"""Contratos de eventos del laboratorio Visual MITM.

Los eventos se serializan en camelCase para que el frontend Nuxt los valide
directamente con Zod. No se guardan credenciales en disco.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: Optional[datetime] = None) -> str:
    moment = value or utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


@dataclass
class CredentialField:
    name: str
    value: str
    category: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "category": self.category,
            "confidence": round(float(self.confidence), 4),
        }


@dataclass
class HttpRequest:
    method: str
    path: str
    host: str
    headers: Dict[str, str]
    body: bytes
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    captured_at: datetime


@dataclass
class DnsQuery:
    query: str
    qtype: str
    source_ip: str
    source_port: int
    destination_ip: str
    destination_port: int
    captured_at: datetime


def make_hello_event(
    server_id: str,
    iface: str,
    mode: str,
    capabilities: List[str],
    version: str = "0.1.0",
    started_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    if mode not in ("live", "demo"):
        raise ValueError("mode debe ser 'live' o 'demo'")
    return {
        "type": "hello",
        "serverId": server_id,
        "version": version,
        "startedAt": iso_utc(started_at),
        "iface": iface,
        "mode": mode,
        "capabilities": list(capabilities),
        "synthetic": mode == "demo",
    }


def make_flow_event(
    source_ip: str,
    source_port: int,
    destination_ip: str,
    destination_port: int,
    protocol: str,
    encrypted: bool,
    bytes_transferred: int,
    risk_level: str,
    captured_at: Optional[datetime] = None,
    host: Optional[str] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    note: Optional[str] = None,
    synthetic: bool = False,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    captured = captured_at or utc_now()
    identifier = event_id or stable_id(
        "flow",
        source_ip,
        source_port,
        destination_ip,
        destination_port,
        protocol,
        iso_utc(captured),
    )
    event: Dict[str, Any] = {
        "type": "flow",
        "id": identifier,
        "capturedAt": iso_utc(captured),
        "sourceIp": source_ip,
        "sourcePort": int(source_port),
        "destinationIp": destination_ip,
        "destinationPort": int(destination_port),
        "protocol": protocol,
        "encrypted": bool(encrypted),
        "bytes": int(bytes_transferred),
        "riskLevel": risk_level,
        "synthetic": bool(synthetic),
    }
    if host:
        event["host"] = host
    if method:
        event["method"] = method
    if path:
        event["path"] = path
    if note:
        event["note"] = note
    return event


def make_credential_event(
    source_ip: str,
    destination_ip: str,
    host: str,
    method: str,
    path: str,
    fields: List[CredentialField],
    captured_at: Optional[datetime] = None,
    flow_id: Optional[str] = None,
    synthetic: bool = False,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    captured = captured_at or utc_now()
    identifier = event_id or stable_id(
        "cred",
        source_ip,
        destination_ip,
        host,
        method,
        path,
        iso_utc(captured),
    )
    event: Dict[str, Any] = {
        "type": "credential",
        "id": identifier,
        "capturedAt": iso_utc(captured),
        "sourceIp": source_ip,
        "destinationIp": destination_ip,
        "host": host,
        "method": method,
        "path": path,
        "fields": [field.to_dict() for field in fields],
        "synthetic": bool(synthetic),
    }
    if flow_id:
        event["flowId"] = flow_id
    return event


def make_dns_event(
    source_ip: str,
    destination_ip: str,
    query: str,
    qtype: str,
    captured_at: Optional[datetime] = None,
    source_port: int = 0,
    destination_port: int = 53,
    encrypted: bool = False,
    synthetic: bool = False,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    captured = captured_at or utc_now()
    identifier = event_id or stable_id(
        "dns", source_ip, destination_ip, query, qtype, iso_utc(captured)
    )
    return {
        "type": "dns",
        "id": identifier,
        "capturedAt": iso_utc(captured),
        "sourceIp": source_ip,
        "destinationIp": destination_ip,
        "query": query,
        "qtype": qtype,
        "encrypted": bool(encrypted),
        "synthetic": bool(synthetic),
    }


def make_stats_event(
    packets: int,
    flows: int,
    credentials: int,
    dns_queries: int,
    pps: float,
    clients: int,
    queue: int,
    synthetic: bool = False,
) -> Dict[str, Any]:
    return {
        "type": "stats",
        "timestamp": iso_utc(),
        "packets": int(packets),
        "flows": int(flows),
        "credentials": int(credentials),
        "dnsQueries": int(dns_queries),
        "pps": round(float(pps), 2),
        "clients": int(clients),
        "queue": int(queue),
        "synthetic": bool(synthetic),
    }


def make_error_event(code: str, message: str) -> Dict[str, Any]:
    return {
        "type": "error",
        "code": code,
        "message": message,
        "timestamp": iso_utc(),
        "synthetic": False,
    }
