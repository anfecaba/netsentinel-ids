# `capture/` — captura pasiva para el laboratorio Visual MITM

Proceso independiente que lee tráfico con **Scapy**, reconstruye peticiones
HTTP, extrae credenciales en texto plano y publica eventos JSON por WebSocket
al dashboard de NetSentinel.

> **Solo pasivo.** No hace ARP spoofing, no inyecta paquetes, no hace SSL
> stripping y no intenta descifrar TLS. Lee lo que la interfaz ya recibe.
>
> **Aviso legal.** Capturar tráfico de terceros sin autorización escrita puede
> constituir el delito de interceptación de datos informáticos (Ley 1273 de
> 2009, art. 269C, Colombia). Usa únicamente redes propias o un laboratorio
> autorizado.

## Requisitos

| Entorno | Requisitos |
|---|---|
| Windows 11 | [Npcap](https://npcap.com) instalado con el modo compatible WinPcap, PowerShell **como administrador** |
| Linux (Ubuntu) | `libpcap-dev` y permisos de `CAP_NET_RAW` (o `sudo`) |
| Python | 3.10+ (el repo se prueba con el Python gestionado por `uv`) |

No hace falta Python del sistema: `uv` descarga el intérprete.

## Instalación

```bash
cd capture
uv sync --extra dev
```

## Uso

### 1. Listar interfaces

```bash
uv run python -m lab_capture.main --list-ifaces
```

En Windows verás rutas tipo `\Device\NPF_{GUID}` con su descripción
(`Wi-Fi`, `Ethernet`). Puedes pasar el nombre o la descripción a `--iface`.

### 2. Validar la interfaz sin tocar la red

```bash
uv run python -m lab_capture.main --demo --nodes 100 --rate 30
```

Genera eventos sintéticos (`synthetic: true`, la UI muestra **SIMULACIÓN**),
suficientes para medir 30 FPS y latencia con 100 nodos. Abre
`http://localhost:3090/laboratorio`.

### 3. Captura real en laboratorio

Windows (PowerShell como administrador):

```powershell
uv run python -m lab_capture.main --iface "Wi-Fi" --i-have-authorization
```

Linux:

```bash
sudo uv run python -m lab_capture.main --iface wlo1 --i-have-authorization
```

Sin `--i-have-authorization` el programa imprime el aviso legal y termina con
código 2. No hay forma de saltarse ese control desde la interfaz.

### 4. Exponer el WebSocket en LAN (opcional)

```bash
uv run python -m lab_capture.main --iface wlo1 --i-have-authorization \
  --host 0.0.0.0 --token "cadena-larga-aleatoria" \
  --origin "http://192.168.1.50:3090"
```

Con `--host` distinto de localhost el token es obligatorio y se valida el
encabezado `Origin` cuando se declara `--origin`. El navegador debe conectarse
a `ws://<ip>:8765/?token=...`.

## Opciones

| Flag | Efecto |
|---|---|
| `--iface` | Interfaz de captura (nombre o descripción) |
| `--demo` | Eventos sintéticos, sin abrir la NIC |
| `--nodes` / `--rate` | Nodos y eventos por segundo en `--demo` |
| `--host` / `--port` | Bind del WebSocket (default `127.0.0.1:8765`) |
| `--token` | Token de acceso; obligatorio fuera de localhost |
| `--origin` | Origen permitido (repetible) |
| `--filter` | Filtro BPF (default HTTP/HTTPS/DNS) |
| `--i-have-authorization` | Confirma autorización escrita |
| `--log` | JSONL **redactado** |
| `--log-raw` | JSONL con credenciales en claro (solo equipo aislado) |
| `--list-ifaces` | Lista interfaces y sale |

## Límites reales (no se ocultan)

- **Red conmutada o WPA2:** el modo promiscuo no ve tráfico de otros equipos
  sin puerto espejo, un AP de laboratorio o ARP spoofing (prohibido aquí).
  Para la demo usa tráfico propio, loopback o una VM en la misma red.
- **Reensamblado TCP:** se cubren segmentos consecutivos, retransmisiones y
  pipelining básico; no es un stack TCP completo. Un `Content-Length`
  incorrecto descarta la petición en lugar de inventar credenciales.
- **HTTP/2 y `Transfer-Encoding: chunked`:** se emite el flujo, pero el cuerpo
  no se inspecciona.
- **TLS:** solo metadatos. No hay descifrado, ni con certificado propio.
- **Latencia:** se mide con `capturedAt` del servidor; con relojes desfasados
  entre máquinas el valor no es fiable.
- **Npcap en loopback:** puede requerir el adaptador "Npcap Loopback Adapter".
  Si no captura, usa la interfaz LAN con tráfico propio.

## Tests

```bash
cd capture
uv run pytest -v
```

Los tests no necesitan root, Npcap ni red: construyen paquetes Scapy en memoria
y levantan el WebSocket en `127.0.0.1` con puerto efímero.

## Estructura

```
capture/
├── lab_capture/
│   ├── config.py        constantes, filtro BPF y aviso legal
│   ├── models.py        contrato de eventos (camelCase)
│   ├── http_parser.py   parser HTTP + ensamblador TCP acotado
│   ├── credentials.py   form, JSON, Basic auth y cookies
│   ├── dns_parser.py    consultas DNS
│   ├── sniffer.py       CaptureEngine (Scapy) y list_interfaces
│   ├── ws_server.py     LabHub (websockets, token, Origin)
│   ├── demo.py          generador sintético
│   └── main.py          CLI y gates de seguridad
└── tests/               50 tests con pytest
```
