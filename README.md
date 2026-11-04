<div align="center">

# NetSentinel IDS

**Dos módulos de auditoría defensiva en una sola aplicación:**
un IDS pasivo que lee el kernel y un laboratorio de captura HTTP/DNS que demuestra *por qué* TLS importa.

![Nuxt](https://img.shields.io/badge/Nuxt-3.13.2-00DC82?style=flat-square&logo=nuxtdotjs&logoColor=white)
![Pinia](https://img.shields.io/badge/Pinia-2.1.7-FFD859?style=flat-square)
![Scapy](https://img.shields.io/badge/Scapy-2.8.0-1D9BF0?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![Vitest](https://img.shields.io/badge/Vitest-2.1.9-6E9F18?style=flat-square)
![pytest](https://img.shields.io/badge/pytest-50%20passed-0A9EDC?style=flat-square)
![Tests](https://img.shields.io/badge/Vitest-42%20passed-brightgreen?style=flat-square)
![Postura](https://img.shields.io/badge/postura-100%25%20pasiva-0f766e?style=flat-square)

</div>

---

## Qué es este proyecto

NetSentinel IDS nace como un IDS pasivo para Linux y crece con un segundo módulo
que convierte un concepto abstracto —"HTTP viaja en claro"— en algo que se ve,
se mide y se explica.

| Módulo | Ruta | Qué hace | Fuente de datos |
| :--- | :--- | :--- | :--- |
| **Defensa** | `/` | Detecta ARP spoofing, deriva de gateway y tráfico sin cifrar. Muestra score de integridad, alertas y remediaciones. | `/proc/net/*` del kernel Linux |
| **Laboratorio** | `/laboratorio` | Captura HTTP y DNS con Scapy, extrae credenciales en texto plano, publica eventos por WebSocket y los dibuja en un grafo de hasta 100 nodos a 30 FPS. | Tráfico real de la NIC, o generador sintético |

El módulo de Defensa no se modificó: sigue funcionando igual que antes. El
Laboratorio es un proceso aparte que el dashboard consume, y si no está
encendido la página lo dice en lugar de inventar datos.

**Contexto académico.** El módulo Laboratorio se entrega con el análisis de
riesgos (MAGERIT v3), la correspondencia con ISO/IEC 27001:2022, el marco penal
colombiano (Ley 1273 de 2009) y un checklist de evidencias medibles. Todo está
en [`docs/visual-mitm/`](./docs/visual-mitm/).

---

## Postura ética

NetSentinel es un laboratorio de auditoría defensiva. No ataca, no inyecta y no intercepta.

- **Solo lectura en el módulo Defensa.** Los sensores abren `/proc/net/arp`, `/proc/net/route`, `/proc/net/dev`, `/proc/net/tcp`, `/proc/net/udp`, `/proc/net/tcp6` y `/proc/net/udp6`. Nada más.
- **Captura estrictamente pasiva en el Laboratorio.** No hay ARP spoofing, SSL stripping, inyección de paquetes ni intento de descifrar TLS. Scapy lee lo que la interfaz ya recibe.
- **Sin sockets crudos de transmisión.** El módulo Defensa no importa `node:dgram` ni `node:net`: no existe código capaz de emitir una trama.
- **Sin generación de tráfico ofensivo.** Los escenarios añaden filas en memoria y dejan que el motor de detección las evalúe.
- **Uso previsto.** Verificar la integridad de tu propio segmento y documentar qué sale sin cifrar. Solo sobre redes propias o con autorización escrita.

Capturar tráfico de terceros sin autorización puede constituir el delito de
interceptación de datos informáticos (Ley 1273 de 2009, art. 269C, Colombia).
El backend exige `--i-have-authorization` y sin esa bandera termina con código 2.

Si necesitas el vector ofensivo, esta herramienta no lo tiene. Y no lo tendrá.

---

## Estado verificado

Cifras medidas en esta máquina, no estimaciones. El detalle y los comandos están
en [`docs/visual-mitm/evidencias.md`](./docs/visual-mitm/evidencias.md).

| Métrica | Resultado | Requisito |
| :--- | ---: | :--- |
| Latencia WebSocket (máx., 197 eventos) | **2,8 ms** | < 1500 ms ✅ |
| Nodos en el grafo | **99 / 100** | hasta 100 ✅ |
| Render del grafo | **29,9 FPS** medidos en pantalla (120 Hz) | 30 FPS ✅ |
| Coste por fotograma (99 nodos, 188 aristas) | **1,0–1,6 ms** | 33,3 ms a 30 FPS ✅ |
| Tests backend (pytest) | **50 passed** | — ✅ |
| Tests frontend (Vitest) | **42 passed** + 1 fallo preexistente | — ⚠️ |
| Build de producción | exit 0 | — ✅ |
| Demo HTTP vs HTTPS | HTTP 200/200/400 · HTTPS 200/200 · sin `-k` = 000 | — ✅ |

**Por qué 99 y no 100 nodos:** el store deduplica por IP y la simulación reserva
una IP para el propio sensor. El contador muestra 99/100 de forma honesta en
lugar de inflar el número.

---

## Arquitectura

```
┌────────────────────────────── Navegador (SPA, ssr: false) ──────────────────────────────┐
│                                                                                          │
│  /  (Defensa)                              /laboratorio  (Laboratorio Visual MITM)       │
│   ├─ SentinelKpiRow                         ├─ LabKpiRow        flujos · credenciales    │
│   ├─ NetworkTopologyRadar                   ├─ LabGraphCanvas   d3-force + Canvas 30 FPS  │
│   ├─ ArpDefenseTable                        ├─ LabCredentialFeed valores completos       │
│   ├─ CryptoPosturePanel                     ├─ LabDnsFeed       consultas en vivo         │
│   ├─ ProtocolTelemetryFeed                  ├─ LabFlowTable     HTTP vs HTTPS             │
│   └─ RemediationModal                       └─ LabWarningBanner simulación / límites      │
└───────────────┬──────────────────────────────────────────────┬───────────────────────────┘
                │ $fetch /api/*                                │ WebSocket ws://127.0.0.1:8765
                ▼                                              ▼
   stores/sentinel.store.ts (Pinia)                  composables/useLabSocket.ts
                │                                              │
                ▼                                              ▼
   Nitro: server/api/telemetry.ts                    capture/lab_capture/ws_server.py
   server/api/simulate-scenario.ts                   (websockets · token · Origin)
                │                                              ▲
                ▼                                              │ JSON Lines
   server/utils/  ──►  /proc/net/*                   capture/lab_capture/sniffer.py
   arpInspector · protocolTelemetry                   Scapy · HTTP · DNS · credenciales
                                                              ▲
                                                              │ Npcap / libpcap
                                                     NIC en modo promiscuo
```

Separación de responsabilidades:

- **Nitro** solo lee el kernel. No emite tráfico ni captura paquetes.
- **`capture/`** es un proyecto Python independiente con su propio `pyproject.toml`, `uv.lock` y suite de tests. Nunca escribe credenciales a disco por defecto.
- **El navegador** no habla con la NIC: recibe eventos por WebSocket y los valida con Zod.

---

## Estructura del repositorio

```
netsentinel-ids/
├── pages/
│   ├── index.vue                 # Módulo Defensa
│   └── laboratorio.vue           # Módulo Laboratorio
├── layouts/default.vue           # Navegación entre los dos módulos
├── error.vue                     # Página de error global tematizada
├── components/
│   ├── ui/                       # AppButton, AppCard, AppInput, AppBadge, AppModal
│   ├── sentinel/                 # Radar, tabla ARP, feed, KPIs, modal (Defensa)
│   └── lab/                      # 7 componentes del Laboratorio
├── composables/
│   ├── useSentinelTelemetry.ts   # fetch + polling de /api/telemetry
│   ├── useSentinelMotion.ts      # anime.js, respeta prefers-reduced-motion
│   └── useLabSocket.ts           # WebSocket con reconexión y backoff
├── stores/
│   ├── sentinel.store.ts         # Estado normalizado de Defensa
│   └── lab.store.ts              # Flujos, credenciales, DNS, grafo (tope 500/100)
├── server/
│   ├── api/                      # GET /api/telemetry · POST /api/simulate-scenario
│   └── utils/                    # Sensores /proc, scoring, esquemas Zod, envelope
├── utils/
│   ├── labMetrics.ts             # advanceFrame (cadencia), FpsMeter, latencia
│   ├── labGraphModel.ts          # Grafo dirigido con deduplicación por IP
│   └── labGraphStyle.ts          # Color por rol, radio por grado, aristas
├── types/                        # Contratos TypeScript (network.ts, lab.ts)
├── tests/                        # 6 archivos Vitest (43 casos)
│
├── capture/                      # Proyecto Python independiente
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── README.md                 # Guía completa del backend de captura
│   ├── lab_capture/
│   │   ├── config.py             # Constantes, filtro BPF, aviso legal
│   │   ├── models.py             # Contrato de eventos en camelCase
│   │   ├── http_parser.py        # Parser HTTP + ensamblador TCP acotado
│   │   ├── credentials.py        # form, JSON, Basic auth, cookies
│   │   ├── dns_parser.py         # Consultas DNS
│   │   ├── sniffer.py            # CaptureEngine (Scapy) y list_interfaces
│   │   ├── ws_server.py          # LabHub: token, Origin, broadcast
│   │   ├── demo.py               # Generador sintético de 100 nodos
│   │   └── main.py               # CLI y gates de seguridad
│   ├── tests/                    # 50 tests con pytest
│   └── tools/ws_probe.py         # Sonda de latencia y nodos
│
├── demo/                         # Servidores de la comparación HTTP vs HTTPS
│   ├── common.py                 # Handler compartido; no registra el cuerpo
│   ├── http_login_server.py      # :8080
│   ├── https_login_server.py     # :8443 (TLS autofirmado)
│   ├── generate_cert.py          # Certificado local para la demo
│   └── login.html
│
└── docs/
    ├── superpowers/specs/        # Diseño del módulo Laboratorio
    ├── superpowers/plans/        # Plan de 11 tareas con comandos de verificación
    └── visual-mitm/              # Entregables académicos + capturas
```

---

## Requisitos

| Entorno | Necesitas |
| :--- | :--- |
| Dashboard | [Bun](https://bun.sh) (hay `bun.lock` en la raíz) |
| Módulo Defensa | Linux, porque los sensores leen `/proc`. En Windows arranca, pero sin tabla ARP real ni sockets del kernel |
| Backend de captura | [uv](https://docs.astral.sh/uv/) — descarga el intérprete de Python, no hace falta instalarlo aparte |
| Captura real en Windows 11 | [Npcap](https://npcap.com) con el modo compatible WinPcap y PowerShell **como administrador** |
| Captura real en Linux | `libpcap-dev` y `CAP_NET_RAW` (o `sudo`) |
| Demo HTTPS | El extra `demo` de Python (`cryptography`) |

---

## Cómo ejecutarlo

### Arranque rápido (sin tocar la red)

Cuatro terminales. El modo `--demo` no abre la NIC: genera eventos sintéticos
marcados `synthetic: true` y la interfaz los rotula como **SIMULACIÓN**.

**Linux / macOS (bash / zsh):**

```bash
# 1 · Dashboard
bun install
bun run dev                                    # http://localhost:3090

# 2 · Backend de captura en modo simulación
cd capture
uv sync --extra dev --extra demo
uv run python -m lab_capture.main --demo --nodes 100 --rate 30

# 3 · Demo HTTP (en otra terminal)
cd demo
../capture/.venv/bin/python http_login_server.py      # :8080

# 4 · Demo HTTPS (en otra terminal)
cd demo
../capture/.venv/bin/python generate_cert.py          # una sola vez
../capture/.venv/bin/python https_login_server.py     # :8443
```

**Windows (PowerShell):**

```powershell
# 1 · Dashboard
bun install
bun run dev                                    # http://localhost:3090

# 2 · Backend de captura en modo simulación
cd capture
uv sync --extra dev --extra demo
uv run python -m lab_capture.main --demo --nodes 100 --rate 30

# 3 · Demo HTTP (en otra terminal)
cd demo
..\capture\.venv\Scripts\python.exe http_login_server.py      # :8080

# 4 · Demo HTTPS (en otra terminal)
cd demo
..\capture\.venv\Scripts\python.exe generate_cert.py          # una sola vez
..\capture\.venv\Scripts\python.exe https_login_server.py     # :8443
```

Abre `http://localhost:3090/laboratorio`. Deberías ver los KPIs subiendo, el
grafo estabilizándose cerca de 100 nodos, credenciales apareciendo con sus
valores completos y el indicador `RENDER 30 FPS`.

### Captura real

Windows (PowerShell **como administrador**):

```powershell
cd capture
uv run python -m lab_capture.main --list-ifaces
uv run python -m lab_capture.main --iface "Wi-Fi" --i-have-authorization
```

Linux (requiere `libpcap-dev` y `CAP_NET_RAW`):

```bash
cd capture
sudo uv run python -m lab_capture.main --iface wlo1 --i-have-authorization
```

macOS (requiere `libpcap`, incluido por defecto):

```bash
cd capture
sudo uv run python -m lab_capture.main --iface en0 --i-have-authorization
```

Sin `--i-have-authorization` imprime el aviso legal y sale con código 2. No hay
forma de saltarse ese control desde la interfaz.

Notas por plataforma:

- **Windows:** abre PowerShell como administrador. Npcap con modo compatible
  WinPcap es obligatorio. El `--iface` acepta el nombre o la descripción que
  devuelve `--list-ifaces` (por ejemplo `"Wi-Fi"` o `"Ethernet"`).
- **Linux:** usa `sudo` o otorga `CAP_NET_RAW` al intérprete del venv con
  `sudo setcap cap_net_raw+eip $(readlink -f capture/.venv/bin/python)`.
- **macOS:** Scapy usa `libpcap`; la captura requiere `sudo`.
- **Loopback:** en Windows puede requerir el adaptador "Npcap Loopback
  Adapter"; si no captura en loopback, usa la interfaz LAN con tráfico propio.

### Exponer el WebSocket en LAN (opcional)

```bash
uv run python -m lab_capture.main --iface wlo1 --i-have-authorization \
  --host 0.0.0.0 --token "cadena-larga-aleatoria" \
  --origin "http://192.168.1.50:3090"
```

Fuera de `localhost` el token es obligatorio y se valida el encabezado `Origin`
cuando se declara `--origin`. El navegador se conecta a `ws://<ip>:8765/?token=...`.

### Exponer el WebSocket en LAN (opcional)

```bash
uv run python -m lab_capture.main --iface wlo1 --i-have-authorization \
  --host 0.0.0.0 --token "cadena-larga-aleatoria" \
  --origin "http://192.168.1.50:3090"
```

Fuera de `localhost` el token es obligatorio y se valida el encabezado `Origin`
cuando se declara `--origin`. El navegador se conecta a `ws://<ip>:8765/?token=...`.

### Comandos del dashboard

```bash
bun run dev          # desarrollo en http://localhost:3090
bun run build        # bundle de producción con Nitro
bun run test         # Vitest
bun run generate     # sitio estático
bun run preview      # previsualizar el build
```

> Si el build falla con un error de bloqueo de Nuxt, hay un `bun run dev`
> activo: páralo o usa `NUXT_IGNORE_LOCK=1 bun run build`.

---

## Módulo Defensa

### Qué detecta

| Vector | Capa OSI | Mecanismo implementado | Severidad | Mitigación |
| :--- | :--- | :--- | :--- | :--- |
| ARP Spoofing / Poisoning | 2, Enlace | Agrupa IPs por MAC normalizada. Si una MAC reclama más de una IP, todas sus filas pasan a `collision` y se emite una alerta `ARP_SPOOFING`. | `critical` | `rem-dai` |
| Gateway Drift | 2 y 3 | Compara la MAC de la entrada `isGateway` contra la MAC de referencia del payload (`trustedGatewayMac`). También conserva filas que ya llegan con `status: gateway_drift`. | `high` | `rem-static-arp` |
| Cleartext HTTP / FTP | 6 y 7 | Flujos simulados en 80 y 21 se emiten como `HTTP`/`FTP` con `encrypted: false`. Un socket real que no coincide con ningún puerto cifrado también cae en `HTTP`. | `high` (simulado) / `medium` (kernel) | `rem-tls13` |
| DNS sin cifrar | 7 | Consulta `DNS` con `encrypted: false` (UDP/53). DoT en 853 y mDNS en 5353 se clasifican como cifrados y no alertan. | `medium` | `rem-dnssec` |

**Score de integridad ARP.** Arranca en 100. Cada MAC en colisión resta 45
puntos; la deriva de gateway resta 25. Se recorta al rango 0–100.

**Postura global.** `CRITICAL_ALERT` si hay colisiones activas o el score cae por
debajo de 60. `DEGRADED` si existe al menos un flujo en texto claro o el score no
llega a 100. `SECURE` en cualquier otro caso.

**Clasificación de sockets.** 443 y 8443 salen como `TLSv1.3`/`HTTPS` cifrados;
22 como `SSHv2`; 853 como `DNSSEC`; 67, 68, 546 y 547 como DHCP; 53 como `DNS`
sin cifrar; 5353 como mDNS seguro; loopback se marca cifrado; cualquier otro
socket abierto se reporta como `HTTP` sin cifrar.

### API

Envelope común para todas las respuestas, generado en `server/utils/response.ts`:

```json
{
  "success": true,
  "data": { "scenario": "baseline", "metrics": { "arpIntegrityScore": 100 } },
  "message": "Telemetría defensiva sincronizada",
  "error": null
}
```

| Método | Ruta | Parámetros | Respuesta |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/telemetry` | `scenario` (`baseline` \| `arp_spoof_detected` \| `cleartext_exposure`), `protocolFilter` (comparación exacta, `ALL` o vacío no filtra), `search` (substring sobre IP origen/destino, protocolo, `cipherSuite`, `inspectionNote`) | `TelemetryPayload` con flujos filtrados |
| `POST` | `/api/simulate-scenario` | Body JSON `{ "scenario": "..." }` validado con Zod | `TelemetryPayload` completo; fija el escenario en el proceso Nitro |

Errores de validación devuelven HTTP 400 con `success: false`, `data: null` y el
`flatten()` de Zod en `error`.

```bash
curl -s http://localhost:3090/api/telemetry | jq '.data.metrics'
curl -s "http://localhost:3090/api/telemetry?scenario=baseline&protocolFilter=HTTPS" | jq '.data.flows'
curl -s "http://localhost:3090/api/telemetry?scenario=baseline&search=192.168.44.1" | jq '.data.flows'
curl -s -X POST http://localhost:3090/api/simulate-scenario \
  -H 'Content-Type: application/json' -d '{"scenario":"arp_spoof_detected"}' | jq '.data.alerts'
```

### Escenarios

Solo esos tres valores son aceptados; cualquier otro string produce 400.

| Escenario | Qué cambia respecto a `baseline` | Efecto medible |
| :--- | :--- | :--- |
| `baseline` | Nada. Tabla ARP real, interfaces de `/proc/net/dev` y sockets del kernel. | Score 100 sin anomalías reales. Máximo 20 flujos, sin el puerto 3090 del propio dashboard. |
| `arp_spoof_detected` | Añade una fila con IP `<subred>.250` y la MAC del gateway. Antepone un flujo ARP hacia el gateway. | `activeCollisions` ≥ 1, score 55, alerta `ARP_SPOOFING` crítica, postura `CRITICAL_ALERT`. |
| `cleartext_exposure` | Antepone dos flujos: HTTP/80 con 15 820 bytes y FTP/21 con 4 120 bytes, desde `<subred>.23` hacia `<subred>.7`. | Dos alertas `CLEARTEXT_PROTOCOL` altas, `encryptionRatio` por debajo de 100, postura `DEGRADED`. |

Los escenarios no tocan la red: todo ocurre en el array que devuelve
`buildTelemetryPayload()`.

**Fallback sin `/proc`.** `readSystemProcArp()` captura la excepción y devuelve
`rows: []` con `interfaceSource: "Linux Kernel /proc/net/arp (unavailable)"`. La
tabla se llena con las interfaces de `os.networkInterfaces()`, marcadas como
estáticas y confiables. `readDefaultGatewayFromRoute()` cae a `192.168.1.1` y
`TRUSTED_GATEWAY_MAC` usa un valor fijo. No hay datos de relleno silenciosos: si
el kernel no expone nada, la pantalla lo dice.

---

## Módulo Laboratorio

### Contrato de eventos (WebSocket)

El backend publica JSON Lines; el frontend los valida con Zod. Todos los eventos
llevan `type`, `id`, `capturedAt` (ISO 8601 UTC) y `synthetic`.

| `type` | Contenido |
| :--- | :--- |
| `hello` | `serverId`, `version`, `startedAt`, `iface`, `mode` (`live`\|`demo`), `capabilities`. Es lo que permite a la UI saber si está en simulación. |
| `flow` | `sourceIp`, `sourcePort`, `destinationIp`, `destinationPort`, `protocol`, `encrypted`, `bytes`, `riskLevel` y, si aplica, `host`, `method`, `path`, `note`. |
| `credential` | `sourceIp`, `destinationIp`, `host`, `method`, `path`, `fields[]` con `{ name, value, category, confidence }`. |
| `dns` | `sourceIp`, `destinationIp`, `query`, `qtype`, `encrypted`. |
| `stats` | `packets`, `flows`, `credentials`, `dnsQueries`, `pps`, `clients`, `queue`. |
| `error` | `code`, `message`. Errores explícitos, nunca silenciados. |

### Qué extrae de verdad

- **HTTP:** método, host, ruta, cabeceras y cuerpo, con un ensamblador TCP que
  cubre segmentos consecutivos, retransmisiones y pipelining básico.
- **Credenciales:** `application/x-www-form-urlencoded`, JSON, `Authorization:
  Basic` y cookies. Se clasifican por categoría y llevan un `confidence`.
- **DNS:** nombre consultado y tipo, marcando si el transporte estaba cifrado.
- **TLS:** solo metadatos. No hay descifrado, ni con certificado propio.

### Límites reales (no se ocultan)

- **Red conmutada o WPA2:** el modo promiscuo no ve tráfico de otros equipos sin
  puerto espejo, un AP de laboratorio o ARP spoofing (prohibido aquí). Para la
  demo usa tráfico propio, loopback o una VM en la misma red.
- **Reensamblado TCP:** no es un stack completo. Un `Content-Length` incorrecto
  descarta la petición en lugar de inventar credenciales.
- **HTTP/2 y `Transfer-Encoding: chunked`:** se emite el flujo, pero el cuerpo no
  se inspecciona.
- **Npcap en loopback:** puede requerir el adaptador "Npcap Loopback Adapter".
- **Latencia:** se mide con `capturedAt` del servidor; con relojes desfasados
  entre máquinas el valor no es fiable.
- **Sin persistencia:** las credenciales viven en memoria del navegador. El log
  opcional (`--log`) las redacta; `--log-raw` las escribe en claro y solo debe
  usarse en un equipo aislado.

---

## Demo HTTP vs HTTPS

El guion completo, con comandos para Windows y Linux, está en
[`docs/visual-mitm/demo-http-vs-https.md`](./docs/visual-mitm/demo-http-vs-https.md).

| Petición | HTTP `:8080` | HTTPS `:8443` |
| :--- | ---: | ---: |
| `GET /` | 200 | 200 |
| `POST /login` con `username` + `password` | 200 | 200 |
| `POST /login` incompleto | **400** | 400 |
| `GET /` sin `-k` (validación del certificado) | — | **000** |

El `000` de la última fila es la prueba de que TLS hace su trabajo: sin
certificado de confianza, no hay conexión. En HTTP el mismo POST viaja legible y
el backend lo muestra en el panel de credenciales; en HTTPS aparece como flujo
cifrado y **no** se extrae ningún campo.

El servidor de la demo no registra el cuerpo de las peticiones en su consola: las
credenciales solo se ven en el dashboard, que es el punto pedagógico.

---

## Tests

### Backend de captura (pytest)

```bash
cd capture
uv run pytest -v
```

**50 tests.** No necesitan root, Npcap ni red: construyen paquetes Scapy en
memoria y levantan el WebSocket en `127.0.0.1` con puerto efímero. Cubren parser
HTTP, extracción de credenciales, DNS, contrato de eventos, motor de captura y
servidor WebSocket (token, Origin, broadcast).

### Frontend (Vitest)

```bash
bun run test
```

**42 passed + 1 fallo preexistente.** Seis archivos:

| Archivo | Casos | Qué prueba |
| :--- | ---: | :--- |
| `tests/defensive-engine.spec.ts` | 5 | Motor defensivo y esquemas Zod |
| `tests/lab-store.spec.ts` | 11 | Deduplicación, topes, filtros del store |
| `tests/lab-metrics.spec.ts` | 12 | `advanceFrame` a 60/75/90/120/144 Hz, `FpsMeter`, latencia |
| `tests/lab-graph-style.spec.ts` | 7 | Color por rol, radio por grado, aristas |
| `tests/lab-graph-model.spec.ts` | 4 | Construcción del grafo y deduplicación por IP |
| `tests/lab-events.spec.ts` | 3 | Validación Zod de los eventos del WebSocket |

**El fallo conocido:** `tests/defensive-engine.spec.ts:82` depende de
`/proc/net/arp` y falla en Windows por entorno, no por lógica. Está documentado
en `docs/visual-mitm/evidencias.md` y no se oculta ni se marca como *skip*.

---

## Documentación académica

Todo en [`docs/visual-mitm/`](./docs/visual-mitm/):

| Documento | Contenido |
| :--- | :--- |
| [`datos-sensibles.md`](./docs/visual-mitm/datos-sensibles.md) | **Empieza aquí si vienes de fuera:** qué datos sensibles maneja el proyecto, dónde viven y qué se construyó, en una página |
| [`informe-final.md`](./docs/visual-mitm/informe-final.md) | Informe listo para entregar: objetivos, metodología, resultados, limitaciones y referencias |
| [`evidencias.md`](./docs/visual-mitm/evidencias.md) | Checklist E1–E9 con comandos, resultados medidos y límites declarados |
| [`magerit-v3.md`](./docs/visual-mitm/magerit-v3.md) | Análisis de riesgos: activos, amenazas, valoración y salvaguardas |
| [`iso-27001-2022.md`](./docs/visual-mitm/iso-27001-2022.md) | Control del Anexo A → evidencia en NetSentinel → brecha |
| [`ley-1273-2009.md`](./docs/visual-mitm/ley-1273-2009.md) | Marco penal colombiano, art. 269C, autorización y minimización |
| [`demo-http-vs-https.md`](./docs/visual-mitm/demo-http-vs-https.md) | Guion reproducible de la demo con umbrales de aceptación |
| `evidencias/*.png, *.jpg` | Capturas del grafo, del rendimiento y del indicador a 30 FPS |

El diseño y el plan de implementación están en
[`docs/superpowers/`](./docs/superpowers/), con las 11 tareas y sus comandos de
verificación.

---

## Limitaciones declaradas

1. **La captura real nunca se ejecutó en esta máquina.** No hay Npcap instalado y
   requiere PowerShell como administrador. Todas las cifras de tráfico provienen
   del modo `--demo` con `synthetic: true`, y así está declarado en los
   documentos. El código de captura está probado con paquetes en memoria.
2. **Los 30 FPS se verifican en una pantalla de 120 Hz.** Para 60, 75, 90 y 144 Hz
   la evidencia es la simulación unitaria de `advanceFrame`, no una observación en
   ese hardware.
3. **Red conmutada o WPA2:** un sniffer pasivo no ve tráfico de terceros sin
   puerto espejo o AP propio. Es una limitación del escenario, no del software.
4. **Un fallo de test preexistente** en Windows por dependencia de `/proc/net`.
5. **Los documentos normativos son adaptaciones académicas**, no auditorías
   certificadas ni dictámenes jurídicos.
6. **El módulo Defensa es Linux-only** para datos reales; el Laboratorio funciona
   en Windows y Linux.

---

## Git

Modelo Safe-Nav de tres ramas. Nada de ramas efímeras por feature.

| Rama | Rol |
| :--- | :--- |
| `dev` | Desarrollo activo. Aquí se hacen los cambios y los commits atómicos. |
| `test` | Staging y QA. Se valida antes de promover. |
| `main` | Release. Solo recibe merges desde `test`, nunca push directo. |

```bash
git checkout dev
git add -A && git commit -m "feat(ids): ..."
git push origin dev
```

**Convención de commits:** `feat(scope)`, `fix(scope)`, `docs(scope)`,
`test(scope)`, `chore(scope)`. Los mensajes van en español, en imperativo y
explicando el *por qué* cuando el cambio no es obvio.
