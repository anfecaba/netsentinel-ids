"""Servidor HTTPS de laboratorio (TLS) en 127.0.0.1:8443.

Sirve el mismo formulario que la versión HTTP, pero el socket va envuelto en
TLS con el certificado autofirmado de `generate_cert.py`. Un observador pasivo
que no descifra TLS solo ve metadatos: IPs, puertos, tamaños y horas.

Uso:
    python generate_cert.py
    python https_login_server.py

No persiste nada: ni logs con el cuerpo, ni ficheros, ni base de datos.
"""

from __future__ import annotations

import argparse
import ssl
from http.server import ThreadingHTTPServer
from pathlib import Path

from common import make_handler

SCHEME = "HTTPS"
EXPLANATION = (
    "Aunque el formulario es idéntico, aquí viaja dentro de TLS: un observador pasivo ve la "
    "conexión y sus metadatos, pero no el usuario ni la contraseña."
)

CERT_DIR = Path(__file__).resolve().parent / "certs"
KEY_PATH = CERT_DIR / "lab.key"
CERT_PATH = CERT_DIR / "lab.crt"


def build_server(
    host: str = "127.0.0.1",
    port: int = 8443,
    cert_path: Path = CERT_PATH,
    key_path: Path = KEY_PATH,
) -> ThreadingHTTPServer:
    if not cert_path.exists() or not key_path.exists():
        raise SystemExit(
            "Falta el certificado. Ejecuta primero:\n"
            f"  python {Path(__file__).name.replace('https_login_server', 'generate_cert')}"
        )

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    handler = make_handler(SCHEME, EXPLANATION)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Servidor HTTPS de laboratorio (TLS)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args()

    server = build_server(args.host, args.port)
    print(f"[demo] HTTPS https://{args.host}:{server.server_address[1]}/")
    print("[demo] Certificado autofirmado: el navegador pedirá aceptarlo (esperado).")
    print("[demo] Este servidor no registra ni guarda lo que recibe. Ctrl+C para salir.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo] servidor HTTPS detenido")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
