"""Servidor WebSocket del laboratorio.

Escucha en localhost por defecto. Si se expone en LAN, exige token y valida
el encabezado ``Origin``. Los clientes lentos se descartan en lugar de
bloquear la captura.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Iterable, Optional, Set
from urllib.parse import parse_qs, urlparse

import websockets

from .config import (
    DEFAULT_WS_HOST,
    DEFAULT_WS_PORT,
    VERSION,
    WS_SEND_TIMEOUT,
)
from .models import iso_utc, make_hello_event


class LabHub:
    """Difunde eventos JSON a los navegadores conectados."""

    def __init__(
        self,
        host: str = DEFAULT_WS_HOST,
        port: int = DEFAULT_WS_PORT,
        token: Optional[str] = None,
        allowed_origins: Optional[Iterable[str]] = None,
        iface: str = "demo",
        mode: str = "live",
        capabilities: Optional[Iterable[str]] = None,
        server_id: str = "lab-local",
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.allowed_origins = list(allowed_origins or [])
        self.iface = iface
        self.mode = mode
        self.capabilities = list(capabilities or ["http", "dns", "tls-metadata"])
        self.server_id = server_id
        self.started_at = None

        self._clients: Set[Any] = set()
        self._server: Any = None
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    async def start(self) -> int:
        self.started_at = self.started_at or __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
        self._server = await websockets.serve(
            self._handler, self.host, self.port, max_queue=64
        )
        socket = self._server.sockets[0]
        self.port = int(socket.getsockname()[1])
        return self.port

    async def close(self) -> None:
        for client in list(self._clients):
            try:
                await client.close(code=1001, reason="servidor detenido")
            except Exception:
                pass
        self._clients.clear()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def run(self) -> None:
        await self.start()
        try:
            await self._stop_event.wait()
        finally:
            await self.close()

    def request_stop(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Autorización
    # ------------------------------------------------------------------
    def is_authorized(self, websocket: Any) -> bool:
        headers = getattr(websocket, "request_headers", None)
        origin = headers.get("Origin") if headers is not None else None

        if self.allowed_origins and origin not in self.allowed_origins:
            return False

        if self.token:
            path = getattr(websocket, "path", "") or ""
            query = parse_qs(urlparse(path).query)
            if query.get("token", [None])[0] != self.token:
                return False

        return True

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def hello_event(self) -> Dict[str, Any]:
        return make_hello_event(
            server_id=self.server_id,
            iface=self.iface,
            mode=self.mode,
            capabilities=self.capabilities,
            version=VERSION,
            started_at=self.started_at,
        )

    async def _handler(self, websocket: Any) -> None:
        if not self.is_authorized(websocket):
            await websocket.close(code=1008, reason="no autorizado")
            return

        self._clients.add(websocket)
        try:
            await websocket.send(json.dumps(self.hello_event()))
            await websocket.wait_closed()
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        if not self._clients:
            return

        try:
            data = json.dumps(event, ensure_ascii=False)
        except (TypeError, ValueError):
            return

        for client in list(self._clients):
            try:
                await asyncio.wait_for(client.send(data), timeout=WS_SEND_TIMEOUT)
            except Exception:
                self._clients.discard(client)
                try:
                    await client.close(code=1013, reason="cliente lento")
                except Exception:
                    pass

    def broadcast_threadsafe(self, event: Dict[str, Any], loop: asyncio.AbstractEventLoop) -> None:
        """Publica desde un hilo de captura sin bloquearlo."""

        def _schedule() -> None:
            asyncio.ensure_future(self.broadcast(event))

        try:
            loop.call_soon_threadsafe(_schedule)
        except RuntimeError:
            # El loop ya se cerró: se descarta el evento.
            pass

    @property
    def clients(self) -> int:
        return len(self._clients)
