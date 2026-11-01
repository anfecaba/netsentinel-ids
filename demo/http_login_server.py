"""Servidor HTTP de laboratorio (sin cifrar) en 127.0.0.1:8080.

Sirve el formulario de `login.html` y acepta `POST /login`. Todo el cuerpo de
la petición —incluidas las credenciales sintéticas— viaja en texto plano, que
es exactamente lo que el sniffer pasivo del laboratorio observa.

Uso:
    python http_login_server.py
    python http_login_server.py --host 127.0.0.1 --port 8080

No persiste nada: ni logs con el cuerpo, ni ficheros, ni base de datos.
"""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from common import make_handler

SCHEME = "HTTP"
EXPLANATION = (
    "Como esta página viaja por HTTP, cualquier observador pasivo de la red puede leer "
    "el usuario y la contraseña del POST en claro."
)


def build_server(host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    handler = make_handler(SCHEME, EXPLANATION)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Servidor HTTP de laboratorio (sin cifrar)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = build_server(args.host, args.port)
    print(f"[demo] HTTP  http://{args.host}:{server.server_address[1]}/")
    print("[demo] Formulario con credenciales sintéticas (ver demo/README.md).")
    print("[demo] Este servidor no registra ni guarda lo que recibe. Ctrl+C para salir.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo] servidor HTTP detenido")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
