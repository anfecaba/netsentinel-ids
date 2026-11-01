import asyncio
import json
from datetime import datetime, timezone

import pytest
import websockets

from lab_capture.models import make_flow_event
from lab_capture.ws_server import LabHub

NOW = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def _flow(event_id: str = "flow-1"):
    return make_flow_event(
        source_ip="10.0.0.5",
        source_port=5000,
        destination_ip="10.0.0.9",
        destination_port=80,
        protocol="HTTP",
        encrypted=False,
        bytes_transferred=120,
        risk_level="warning",
        captured_at=NOW,
        host="lab.local",
        method="GET",
        path="/",
        event_id=event_id,
    )


async def test_envia_hello_al_conectar():
    hub = LabHub(host="127.0.0.1", port=0, mode="demo")
    port = await hub.start()
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as websocket:
            hello = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
            assert hello["type"] == "hello"
            assert hello["mode"] == "demo"
            assert hello["synthetic"] is True
            assert "http" in hello["capabilities"]
    finally:
        await hub.close()


async def test_broadcast_llega_al_cliente():
    hub = LabHub(host="127.0.0.1", port=0)
    port = await hub.start()
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/") as websocket:
            await asyncio.wait_for(websocket.recv(), timeout=2)
            await hub.broadcast(_flow())
            received = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
            assert received["type"] == "flow"
            assert received["id"] == "flow-1"
    finally:
        await hub.close()


async def test_token_invalido_cierra_con_1008():
    hub = LabHub(host="127.0.0.1", port=0, token="secreto")
    port = await hub.start()
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/?token=malo") as websocket:
            with pytest.raises(websockets.exceptions.ConnectionClosed) as info:
                await asyncio.wait_for(websocket.recv(), timeout=2)
            assert info.value.code == 1008
    finally:
        await hub.close()


async def test_token_correcto_permite_conectar():
    hub = LabHub(host="127.0.0.1", port=0, token="secreto")
    port = await hub.start()
    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/?token=secreto") as websocket:
            hello = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
            assert hello["type"] == "hello"
    finally:
        await hub.close()


async def test_origin_no_permitido_cierra_conexion():
    hub = LabHub(host="127.0.0.1", port=0, allowed_origins=["http://localhost:3090"])
    port = await hub.start()
    try:
        async with websockets.connect(
            f"ws://127.0.0.1:{port}/", extra_headers={"Origin": "http://evil.local"}
        ) as websocket:
            with pytest.raises(websockets.exceptions.ConnectionClosed) as info:
                await asyncio.wait_for(websocket.recv(), timeout=2)
            assert info.value.code == 1008
    finally:
        await hub.close()


async def test_broadcast_sin_clientes_no_falla():
    hub = LabHub(host="127.0.0.1", port=0)
    await hub.broadcast(_flow("flow-sin-clientes"))
