"""Sonda de evidencias del WebSocket del laboratorio.

Conecta al backend, mide latencia de extremo a extremo y resume cuántos
nodos, flujos, credenciales y consultas DNS llegaron. No forma parte del
producto: sirve para el checklist de `docs/visual-mitm/evidencias.md`.

Uso:
    uv run python tools/ws_probe.py --seconds 8 --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import websockets


def _latency_ms(captured_at: str) -> float | None:
    try:
        moment = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - moment
    return max(0.0, delta.total_seconds() * 1000.0)


async def probe(url: str, seconds: float) -> Dict[str, Any]:
    latencies: List[float] = []
    nodes = set()
    flows = 0
    credentials = 0
    dns_queries = 0
    hello: Dict[str, Any] | None = None

    async with websockets.connect(url) as websocket:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=max(0.1, remaining))
            except asyncio.TimeoutError:
                break

            event = json.loads(raw)
            event_type = event.get("type")
            if event_type == "hello":
                hello = event
                continue

            captured_at = event.get("capturedAt") or event.get("timestamp")
            if captured_at:
                latency = _latency_ms(captured_at)
                if latency is not None:
                    latencies.append(latency)

            if event_type == "flow":
                flows += 1
                if event.get("sourceIp"):
                    nodes.add(event["sourceIp"])
                if event.get("destinationIp"):
                    nodes.add(event["destinationIp"])
            elif event_type == "credential":
                credentials += 1
                for ip in (event.get("sourceIp"), event.get("destinationIp")):
                    if ip:
                        nodes.add(ip)
            elif event_type == "dns":
                dns_queries += 1

    ordered = sorted(latencies)
    summary: Dict[str, Any] = {
        "url": url,
        "seconds": seconds,
        "hello": hello,
        "nodes": len(nodes),
        "flows": flows,
        "credentials": credentials,
        "dnsQueries": dns_queries,
        "eventsMeasured": len(ordered),
    }
    if ordered:
        summary["latencyMs"] = {
            "min": round(ordered[0], 1),
            "median": round(statistics.median(ordered), 1),
            "p95": round(ordered[int(len(ordered) * 0.95) - 1], 1),
            "max": round(ordered[-1], 1),
        }
        summary["under1500ms"] = ordered[-1] < 1500
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:8765")
    parser.add_argument("--seconds", type=float, default=8.0)
    parser.add_argument("--json", action="store_true", help="Salida JSON de una línea")
    args = parser.parse_args()

    summary = asyncio.run(probe(args.url, args.seconds))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
