"""Piezas compartidas por los servidores de demostración HTTP y HTTPS.

Ambos servidores sirven el mismo formulario y responden igual; la única
diferencia es si el socket va envuelto en TLS. Ninguno registra ni persiste
las credenciales recibidas.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qsl

HERE = Path(__file__).resolve().parent
LOGIN_PAGE = HERE / "login.html"

# Cabeceras comunes: sin caché y sin sniffing de tipo.
BASE_HEADERS: Dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

RECEIVED_PAGE = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Credenciales recibidas · laboratorio</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        background: #070a12;
        color: #e8eef7;
        font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif;
      }}
      .card {{
        max-width: 460px;
        padding: 28px;
        border: 1px solid #1e2637;
        border-radius: 16px;
        background: #0d1220;
      }}
      h1 {{ margin: 0 0 8px; font-size: 19px; }}
      p {{ margin: 0 0 10px; color: #94a3b8; font-size: 13px; line-height: 1.6; }}
      code {{ font-family: ui-monospace, monospace; color: #cbd5e1; }}
      a {{ color: #34d399; font-size: 13px; }}
    </style>
  </head>
  <body>
    <main class="card">
      <h1>Credenciales recibidas</h1>
      <p>El servidor de laboratorio recibió un <code>POST /login</code> por {scheme}.</p>
      <p>
        No se muestran ni se registran los valores: este servidor no persiste credenciales, ni
        siquiera en memoria más allá de procesar la petición.
      </p>
      <p>{explanation}</p>
      <a href="/">&larr; Volver al formulario</a>
    </main>
  </body>
</html>
"""


def _field_names(body: bytes) -> set:
    """Devuelve solo los nombres de campo, nunca sus valores."""

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - decode con replace no lanza
        return set()
    return {
        name.strip().lower()
        for name, _value in parse_qsl(text, keep_blank_values=False)
    }


class LabLoginHandler(BaseHTTPRequestHandler):
    """Handler del formulario de laboratorio.

    ``scheme`` y ``explanation`` los define cada servidor para explicar en la
    página de respuesta qué se ve (o no) al otro lado del cable.
    """

    scheme = "HTTP"
    explanation = ""
    server_version = "LabDemo/0.1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _send(
        self,
        status: int,
        body: bytes,
        content_type: str = "text/html; charset=utf-8",
        extra: Optional[Dict[str, str]] = None,
    ) -> None:
        self.send_response(status)
        for name, value in BASE_HEADERS.items():
            self.send_header(name, value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, payload: str) -> None:
        self._send(status, payload.encode("utf-8"), "application/json; charset=utf-8")

    # ------------------------------------------------------------------
    # Rutas
    # ------------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - nombre impuesto por http.server
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html", "/login"):
            try:
                page = LOGIN_PAGE.read_bytes()
            except OSError:
                self._send(500, b"login.html no encontrado", "text/plain; charset=utf-8")
                return
            self._send(200, page)
            return

        if path == "/health":
            self._send_json(200, '{"status":"ok"}')
            return

        self._send(404, b"No encontrado", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802 - nombre impuesto por http.server
        path = self.path.split("?", 1)[0]
        if path != "/login":
            self._send(404, b"No encontrado", "text/plain; charset=utf-8")
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0

        # Se lee el cuerpo para consumirlo, pero nunca se guarda ni se imprime.
        body = self.rfile.read(length) if 0 < length <= 64 * 1024 else b""

        if not {"username", "password"}.issubset(_field_names(body)):
            self._send(
                400,
                b"Faltan campos username/password",
                "text/plain; charset=utf-8",
            )
            return

        page = RECEIVED_PAGE.format(scheme=self.scheme, explanation=self.explanation)
        self._send(200, page.encode("utf-8"))

    def do_HEAD(self) -> None:  # noqa: N802 - nombre impuesto por http.server
        self.do_GET()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - firma heredada
        # Solo método, ruta y estado: nunca el cuerpo ni las cabeceras.
        status = args[1] if len(args) > 1 else ""
        method = getattr(self, "command", "-") or "-"
        print(
            f"[demo] {method} {self.path.split('?', 1)[0]} -> {status}",
            flush=True,
        )


def make_handler(scheme: str, explanation: str):
    """Devuelve una subclase del handler con textos propios del esquema."""

    return type(
        f"LoginHandler{scheme}",
        (LabLoginHandler,),
        {"scheme": scheme, "explanation": explanation},
    )
