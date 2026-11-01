"""Constantes compartidas del laboratorio Visual MITM."""

from __future__ import annotations

VERSION = "0.1.0"

# Filtro BPF por defecto: solo tráfico HTTP/DNS/TLS que el laboratorio necesita.
DEFAULT_BPF = (
    "tcp port 80 or tcp port 8080 or tcp port 443 or tcp port 8443 "
    "or udp port 53"
)

HTTP_PORTS = frozenset({80, 8000, 8080, 8888})
TLS_PORTS = frozenset({443, 8443})
DNS_PORT = 53

# Límites de memoria: una ráfaga maliciosa no debe tumbar el proceso.
MAX_HTTP_BUFFER = 64 * 1024
MAX_HTTP_BODY = 64 * 1024
MAX_CREDENTIAL_VALUE = 512
MAX_JSON_DEPTH = 3

# WebSocket
DEFAULT_WS_HOST = "127.0.0.1"
DEFAULT_WS_PORT = 8765
WS_SEND_TIMEOUT = 1.0
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

# Estadísticas
STATS_INTERVAL = 2.0

# Aviso legal mostrado cuando falta autorización explícita.
LEGAL_NOTICE = (
    "AVISO LEGAL\n"
    "Este programa captura tráfico de red en modo pasivo.\n"
    "Ejecutarlo sobre redes de terceros sin autorización escrita puede\n"
    "constituir el delito de interceptación de datos informáticos\n"
    "(Ley 1273 de 2009, artículo 269C, Colombia).\n\n"
    "Usa únicamente redes propias o un laboratorio autorizado.\n"
    "Para confirmar la autorización, repite el comando con:\n"
    "  --i-have-authorization\n"
    "Para probar la interfaz sin tocar la red:\n"
    "  --demo\n"
)
