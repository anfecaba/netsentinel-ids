"""Generador de tráfico sintético para validar la interfaz sin tocar la red.

Todo evento emitido aquí lleva ``synthetic: true`` y la UI lo marca como
SIMULACIÓN. Sirve para medir 30 FPS y latencia con 100 nodos.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List

from .config import VERSION
from .models import (
    CredentialField,
    make_credential_event,
    make_dns_event,
    make_flow_event,
    make_hello_event,
    make_stats_event,
    utc_now,
)

DEMO_USER = "alice"
DEMO_PASSWORD = "SuperSecret123"
DEMO_HOST = "portal.lab.local"
DEMO_SERVER_IP = "10.10.9.9"
DEMO_DNS_IP = "10.10.9.53"


class DemoGenerator:
    """Emite flujos, credenciales y DNS sintéticos a un ritmo fijo."""

    def __init__(
        self,
        nodes: int = 20,
        rate: float = 30.0,
        credentials_every: int = 10,
        server_id: str = "lab-demo",
    ) -> None:
        self.nodes = max(2, int(nodes))
        self.rate = max(1.0, float(rate))
        self.credentials_every = max(2, int(credentials_every))
        self.server_id = server_id

    def _client_ip(self, index: int) -> str:
        third = index // 200
        fourth = index % 200 + 1
        return f"10.10.{third}.{fourth}"

    def _flow(self, counter: int) -> Dict[str, Any]:
        index = counter % self.nodes
        source = self._client_ip(index)
        if counter % 3 == 0:
            return make_flow_event(
                source_ip=source,
                source_port=40000 + (counter % 20000),
                destination_ip=DEMO_SERVER_IP,
                destination_port=80,
                protocol="HTTP",
                encrypted=False,
                bytes_transferred=320 + (counter % 800),
                risk_level="warning",
                host=DEMO_HOST,
                method="GET",
                path="/",
                note="HTTP sin cifrar (simulación)",
                synthetic=True,
                event_id=f"demo-flow-{counter}",
            )
        return make_flow_event(
            source_ip=source,
            source_port=40000 + (counter % 20000),
            destination_ip=DEMO_SERVER_IP,
            destination_port=443,
            protocol="HTTPS",
            encrypted=True,
            bytes_transferred=1400 + (counter % 4000),
            risk_level="safe",
            note="Solo metadatos TLS; el payload no se descifra (simulación)",
            synthetic=True,
            event_id=f"demo-flow-{counter}",
        )

    def _credential(self, counter: int) -> Dict[str, Any]:
        index = counter % self.nodes
        return make_credential_event(
            source_ip=self._client_ip(index),
            destination_ip=DEMO_SERVER_IP,
            host=DEMO_HOST,
            method="POST",
            path="/login",
            fields=[
                CredentialField("username", DEMO_USER, "user", 0.99),
                CredentialField("password", DEMO_PASSWORD, "password", 1.0),
            ],
            synthetic=True,
            event_id=f"demo-cred-{counter}",
        )

    def _dns(self, counter: int) -> Dict[str, Any]:
        index = counter % self.nodes
        return make_dns_event(
            source_ip=self._client_ip(index),
            destination_ip=DEMO_DNS_IP,
            query=DEMO_HOST,
            qtype="A",
            source_port=40000 + (counter % 20000),
            destination_port=53,
            synthetic=True,
            event_id=f"demo-dns-{counter}",
        )

    async def events(self) -> AsyncIterator[Dict[str, Any]]:
        started = utc_now()
        yield make_hello_event(
            server_id=self.server_id,
            iface="demo",
            mode="demo",
            capabilities=["http", "dns", "tls-metadata"],
            version=VERSION,
            started_at=started,
        )

        counter = 1
        while True:
            if counter % (self.credentials_every * 5) == 0:
                event = make_stats_event(
                    packets=counter,
                    flows=counter,
                    credentials=counter // self.credentials_every,
                    dns_queries=counter // 7,
                    pps=float(self.rate),
                    clients=1,
                    queue=0,
                    synthetic=True,
                )
            elif counter % self.credentials_every == 0:
                event = self._credential(counter)
            elif counter % 7 == 0:
                event = self._dns(counter)
            else:
                event = self._flow(counter)

            yield event
            counter += 1
            await asyncio.sleep(1.0 / self.rate)

    async def take(self, count: int) -> List[Dict[str, Any]]:
        """Utilidad de test: devuelve ``count`` eventos sin bucle infinito."""

        collected: List[Dict[str, Any]] = []
        async for event in self.events():
            collected.append(event)
            if len(collected) >= count:
                break
        return collected
