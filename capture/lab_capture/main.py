"""CLI del laboratorio Visual MITM.

Ejemplos:
    python -m lab_capture.main --list-ifaces
    python -m lab_capture.main --demo --nodes 100 --rate 30
    sudo python -m lab_capture.main --iface eth0 --i-have-authorization
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import (
    DEFAULT_BPF,
    DEFAULT_WS_HOST,
    DEFAULT_WS_PORT,
    LEGAL_NOTICE,
    LOOPBACK_HOSTS,
    STATS_INTERVAL,
    VERSION,
)
from .demo import DemoGenerator
from .models import iso_utc, make_error_event, make_stats_event
from .sniffer import CaptureEngine, list_interfaces, resolve_interface
from .ws_server import LabHub

REDACTED = "[REDACTADO]"


def _redact(event: Dict[str, Any]) -> Dict[str, Any]:
    if event.get("type") != "credential":
        return event
    clone = dict(event)
    clone["fields"] = [
        {**field, "value": REDACTED} for field in event.get("fields", [])
    ]
    return clone


class EventLog:
    """Escritura JSONL opcional. Redacta credenciales salvo ``--log-raw``."""

    def __init__(self, path: Optional[str] = None, raw: bool = False) -> None:
        self.raw = raw
        self._file = None
        if path:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            self._file = target.open("a", encoding="utf-8")

    def write(self, event: Dict[str, Any]) -> None:
        if self._file is None:
            return
        payload = event if self.raw else _redact(event)
        try:
            self._file.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._file.flush()
        except (OSError, ValueError):
            pass

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lab_capture",
        description=(
            "Captura pasiva HTTP/DNS para el laboratorio Visual MITM de "
            "NetSentinel. No inyecta paquetes ni rompe TLS."
        ),
    )
    parser.add_argument("--iface", help="Interfaz de captura (ver --list-ifaces)")
    parser.add_argument("--host", default=DEFAULT_WS_HOST, help="Host del WebSocket")
    parser.add_argument("--port", type=int, default=DEFAULT_WS_PORT, help="Puerto del WebSocket")
    parser.add_argument("--token", help="Token obligatorio para exponer el WS en LAN")
    parser.add_argument("--origin", action="append", default=[], help="Origen permitido (repetible)")
    parser.add_argument("--demo", action="store_true", help="Genera eventos sintéticos sin tocar la red")
    parser.add_argument("--nodes", type=int, default=20, help="Nodos simulados en --demo")
    parser.add_argument("--rate", type=float, default=30.0, help="Eventos por segundo en --demo")
    parser.add_argument("--list-ifaces", action="store_true", help="Lista interfaces y sale")
    parser.add_argument(
        "--i-have-authorization",
        action="store_true",
        help="Confirma que tienes autorización escrita para capturar en esta red",
    )
    parser.add_argument("--filter", default=DEFAULT_BPF, help="Filtro BPF de Scapy")
    parser.add_argument("--log", help="Escribe eventos JSONL redactados en esta ruta")
    parser.add_argument("--log-raw", action="store_true", help="No redactar credenciales en --log")
    parser.add_argument("--version", action="version", version=f"lab_capture {VERSION}")
    return parser


async def _run_demo(hub: LabHub, generator: DemoGenerator, log: EventLog) -> None:
    async for event in generator.events():
        log.write(event)
        await hub.broadcast(event)


async def _run_live(hub: LabHub, args: argparse.Namespace, log: EventLog) -> None:
    loop = asyncio.get_running_loop()
    engine = CaptureEngine(
        iface=resolve_interface(args.iface or ""),
        on_event=lambda event: hub.broadcast_threadsafe(event, loop),
        bpf_filter=args.filter,
    )

    def _consume(event: Dict[str, Any]) -> None:
        log.write(event)

    engine.on_event = lambda event: (_consume(event), hub.broadcast_threadsafe(event, loop))

    thread = threading.Thread(target=engine.start, name="lab-capture", daemon=True)
    thread.start()

    try:
        while thread.is_alive():
            await hub.broadcast(
                make_stats_event(
                    packets=engine.packets_seen,
                    flows=engine.flows_emitted,
                    credentials=engine.credentials_found,
                    dns_queries=engine.dns_queries,
                    pps=0.0,
                    clients=hub.clients,
                    queue=0,
                )
            )
            await asyncio.sleep(STATS_INTERVAL)
    finally:
        engine.stop()


async def _run(args: argparse.Namespace, log: EventLog) -> None:
    hub = LabHub(
        host=args.host,
        port=args.port,
        token=args.token,
        allowed_origins=args.origin,
        iface=args.iface or ("demo" if args.demo else "auto"),
        mode="demo" if args.demo else "live",
    )
    port = await hub.start()
    print(f"[lab] WebSocket escuchando en ws://{args.host}:{port}")

    if args.demo:
        print("[lab] MODO SIMULACIÓN: los eventos son sintéticos y no tocan la red.")
        try:
            await _run_demo(hub, DemoGenerator(nodes=args.nodes, rate=args.rate), log)
        except asyncio.CancelledError:
            pass
        finally:
            await hub.close()
        return

    print(f"[lab] Captura pasiva en '{args.iface}' con filtro: {args.filter}")
    try:
        await _run_live(hub, args, log)
    finally:
        await hub.close()


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_ifaces:
        try:
            print(json.dumps(list_interfaces(), indent=2, ensure_ascii=False))
        except RuntimeError as error:
            print(f"[lab] {error}", file=sys.stderr)
            return 3
        return 0

    if not args.demo and not args.i_have_authorization:
        print(LEGAL_NOTICE, file=sys.stderr)
        return 2

    if not args.demo and not args.iface:
        print("[lab] Falta --iface. Usa --list-ifaces para ver las disponibles.", file=sys.stderr)
        return 2

    if args.host not in LOOPBACK_HOSTS and not args.token:
        print(
            "[lab] Exponer el WebSocket fuera de localhost exige --token.",
            file=sys.stderr,
        )
        return 2

    if args.log_raw and not args.log:
        print("[lab] --log-raw requiere --log.", file=sys.stderr)
        return 2
    if args.log_raw:
        print(
            "[lab] ADVERTENCIA: --log-raw escribe credenciales en claro. "
            "Úsalo solo en un equipo de laboratorio aislado.",
            file=sys.stderr,
        )

    log = EventLog(args.log, raw=args.log_raw)
    try:
        asyncio.run(_run(args, log))
    except KeyboardInterrupt:
        print("\n[lab] Captura detenida por el usuario.")
    except RuntimeError as error:
        print(f"[lab] {error}", file=sys.stderr)
        make_error = make_error_event("capture_error", str(error))
        print(json.dumps(make_error, ensure_ascii=False), file=sys.stderr)
        return 4
    finally:
        log.close()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
