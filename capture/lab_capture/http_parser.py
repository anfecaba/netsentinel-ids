"""Parser de peticiones HTTP y ensamblador TCP acotado.

El laboratorio solo necesita reconstruir peticiones (request) para extraer
credenciales y metadatos. Las respuestas no se inspeccionan.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .config import MAX_HTTP_BODY, MAX_HTTP_BUFFER
from .models import HttpRequest

_REQUEST_LINE = re.compile(rb"^([A-Z]+) (\S+) HTTP/(\d\.\d)$")

FlowKey = Tuple[str, int, str, int]


class HttpParseError(ValueError):
    """Error interno de parseo que nunca debe escapar del ensamblador."""


def _decode_header(raw: bytes) -> str:
    return raw.decode("latin-1", errors="replace").strip()


def parse_http_request(
    raw: bytes,
    captured_at: Optional[datetime] = None,
    body_limit: int = MAX_HTTP_BODY,
) -> Optional[HttpRequest]:
    """Parsea una petición HTTP completa.

    Devuelve ``None`` cuando el buffer todavía no contiene una petición
    completa (sin ``\\r\\n\\r\\n`` o con body incompleto) o cuando la línea de
    request no es válida. Nunca lanza por datos corruptos.
    """

    if not raw:
        return None

    header_end = raw.find(b"\r\n\r\n")
    if header_end < 0:
        return None

    head = raw[:header_end]
    body_available = raw[header_end + 4 :]

    lines = head.split(b"\r\n")
    if not lines:
        return None

    match = _REQUEST_LINE.match(lines[0].strip())
    if not match:
        return None

    method = match.group(1).decode("ascii")
    path = match.group(2).decode("latin-1", errors="replace")

    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        name, separator, value = line.partition(b":")
        if not separator:
            return None
        headers[_decode_header(name).lower()] = _decode_header(value)

    content_length = 0
    raw_length = headers.get("content-length")
    if raw_length:
        try:
            content_length = int(raw_length.split(",")[0].strip())
        except (TypeError, ValueError):
            return None
        if content_length < 0:
            return None
        if content_length > body_limit:
            # Cuerpo fuera de límite: no se inspecciona, pero el flujo es válido.
            content_length = 0
            body_available = b""

    chunked = "chunked" in headers.get("transfer-encoding", "").lower()
    if chunked:
        # No se decodifica chunked: se emite el flujo sin cuerpo inspeccionable.
        body = b""
        consumed = header_end + 4
    else:
        if len(body_available) < content_length:
            return None
        body = bytes(body_available[:content_length])
        consumed = header_end + 4 + content_length

    return HttpRequest(
        method=method,
        path=path,
        host=headers.get("host", ""),
        headers=headers,
        body=body,
        captured_at=captured_at or datetime.now(timezone.utc),
        raw_bytes=consumed,
    )


class HttpRequestAssembler:
    """Reensambla peticiones HTTP a partir de segmentos TCP.

    Mantiene un buffer por 4-tupla, descarta duplicados por número de
    secuencia y corta el buffer cuando supera ``MAX_HTTP_BUFFER``. No
    reconstruye respuestas ni pretende ser un stack TCP completo.
    """

    def __init__(self, max_buffer: int = MAX_HTTP_BUFFER) -> None:
        self.max_buffer = max_buffer
        self._buffers: Dict[FlowKey, bytearray] = {}
        self._expected: Dict[FlowKey, int] = {}
        self.dropped_overflows = 0
        self.dropped_gaps = 0

    def reset(self, key: FlowKey) -> None:
        self._buffers.pop(key, None)
        self._expected.pop(key, None)

    def reset_all(self) -> None:
        self._buffers.clear()
        self._expected.clear()

    def feed(
        self,
        source_ip: str,
        source_port: int,
        destination_ip: str,
        destination_port: int,
        seq: int,
        payload: bytes,
        timestamp: Optional[datetime] = None,
    ) -> List[HttpRequest]:
        key: FlowKey = (source_ip, source_port, destination_ip, destination_port)
        if not payload:
            return []

        expected = self._expected.get(key)
        if expected is not None:
            if seq + len(payload) <= expected:
                # Retransmisión completa: ya fue procesada.
                return []
            if seq < expected:
                payload = payload[expected - seq :]
                seq = expected
            elif seq > expected:
                # Hueco: se descarta lo anterior y se reinicia el buffer.
                self.dropped_gaps += 1
                self._buffers[key] = bytearray()
        self._expected[key] = seq + len(payload)

        buffer = self._buffers.setdefault(key, bytearray())
        buffer.extend(payload)

        if len(buffer) > self.max_buffer:
            self.dropped_overflows += 1
            self.reset(key)
            return []

        requests: List[HttpRequest] = []
        captured = timestamp or datetime.now(timezone.utc)

        while buffer:
            parsed = parse_http_request(bytes(buffer), captured)
            if parsed is None:
                break
            consumed = max(1, parsed.raw_bytes)
            del buffer[:consumed]
            parsed.source_ip = source_ip
            parsed.source_port = int(source_port)
            parsed.destination_ip = destination_ip
            parsed.destination_port = int(destination_port)
            requests.append(parsed)

        if not buffer:
            # Se conserva ``_expected`` para detectar retransmisiones del
            # siguiente segmento; solo se libera la memoria del buffer.
            self._buffers.pop(key, None)

        return requests
