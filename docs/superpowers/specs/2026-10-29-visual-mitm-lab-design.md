# Visual MITM Lab — Diseño de integración en NetSentinel

**Fecha:** 2026-10-29  
**Estado:** propuesto para aprobación  
**Proyecto:** `netsentinel-ids`  
**Objetivo académico:** demostrar, en laboratorio autorizado, cómo se ve el tráfico HTTP/DNS sin cifrar y por qué HTTPS/DoH/VPN son obligatorios.

---

## 1. Contexto

NetSentinel IDS ya existe como dashboard defensivo en Nuxt 3. Lee `/proc/net` en Linux, detecta colisiones ARP y mide la postura criptográfica. La retroalimentación del docente pide añadir el prototipo **Visual MITM**: captura pasiva con Scapy, extracción de credenciales en formularios POST, peticiones DNS, transmisión por WebSocket con latencia menor a 1.5 s y un grafo interactivo a 30 FPS con hasta 100 nodos.

La integración no reemplaza el IDS: añade una segunda narrativa. La pestaña **Defensa** explica cómo detectar y mitigar; la pestaña **Laboratorio** muestra, en un entorno controlado, qué expone el tráfico sin cifrar.

> **Aclaración:** el backend se implementa con **Scapy** (captura y disección de paquetes). Scrapy es un framework de scraping web y no se usa aquí.

---

## 2. Decisiones cerradas con el usuario

| Decisión | Elección |
|---|---|
| Entorno de demo | Windows 11 + Npcap y VM Linux (Ubuntu). Código multiplataforma. |
| Integración UI | Pestañas **Defensa** / **Laboratorio** en el layout actual. |
| Credenciales en pantalla | Valores completos, con advertencia visible. Sin persistencia por defecto. |
| Entregables | Código + documentos académicos en `docs/visual-mitm/`. |
| Captura | Solo pasiva: `sniff`, sin inyección, sin ARP spoofing, sin SSL stripping, sin romper TLS. |
| Persistencia | En memoria. El log JSONL es opcional y redactado por defecto. |

---

## 3. No objetivos / anti-objetivos

- No se implementa envenenamiento ARP, degradación de TLS ni suplantación de gateway.
- No se capturan credenciales de terceros ni de redes sin autorización.
- No se almacenan credenciales en base de datos, archivos ni repositorio.
- No se promete capturar tráfico ajeno en redes conmutadas/WPA2 sin puerto espejo o laboratorio controlado.
- No se sustituye el IDS defensivo; se conserva y se enlaza con la demo.

---

## 4. Arquitectura

```
┌──────────────────────────── Navegador ────────────────────────────┐
│  Nuxt 3 SPA :3090                                                 │
│  ├── /            → pestaña Defensa (IDS actual)                  │
│  └── /laboratorio → pestaña Visual MITM                           │
│        ├── LabGraphCanvas (Canvas + d3-force, 30 FPS, 100 nodos)  │
│        ├── LabCredentialFeed (valores completos, alerta roja)      │
│        ├── LabDnsFeed / LabFlowTable / LabKpiRow                  │
│        └── useLabSocket ── WebSocket ──┐                          │
└────────────────────────────────────────┼──────────────────────────┘
                                         │ ws://127.0.0.1:8765
                                         ▼
┌──────────────────── Python bridge (capture/) ─────────────────────┐
│  main.py (CLI, gate legal, --demo, --list-ifaces)                 │
│  sniffer.py (Scapy sniff, BPF, promisc=True)                      │
│  http_parser.py (TCP reassembly acotado, request/response)        │
│  credentials.py (form, JSON, Basic auth, cookies)                 │
│  dns_parser.py (DNSQR, qtype)                                     │
│  ws_server.py (websockets, broadcast, origin/token, backpressure) │
│  models.py (eventos JSON camelCase)                               │
└───────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
                              NIC (Npcap / libpcap)
```

### Flujo de datos

1. Scapy captura con filtro BPF `tcp port 80 or tcp port 8080 or tcp port 443 or tcp port 8443 or udp port 53`.
2. El ensamblador reconstruye peticiones HTTP por flujo TCP (máx. 64 KB por buffer).
3. El extractor busca campos de credenciales en body y cabeceras.
4. Cada evento se serializa a JSON camelCase y se encola.
5. El WebSocket envía credenciales de inmediato y agrupa flujos cada 50 ms.
6. El navegador valida con Zod, actualiza Pinia y dibuja el grafo.

---

## 5. Contrato de eventos

Todos los eventos llevan `type`, `capturedAt` (ISO 8601 UTC) y `synthetic` (booleano). Los valores completos de credenciales se envían al frontend; nunca se registran por defecto.

```json
{ "type": "hello", "serverId": "lab-...", "version": "0.1.0", "startedAt": "...", "iface": "Wi-Fi", "mode": "live" | "demo", "capabilities": ["http", "dns", "tls-metadata"] }
```

```json
{ "type": "flow", "id": "flow-...", "capturedAt": "...", "sourceIp": "192.168.1.23", "sourcePort": 52301, "destinationIp": "192.168.1.7", "destinationPort": 80, "protocol": "HTTP" | "HTTPS" | "DNS" | "TLS" | "TCP" | "UDP", "encrypted": false, "bytes": 420, "host": "lab.local", "method": "POST", "path": "/login", "riskLevel": "safe" | "warning" | "danger", "note": "POST sin TLS", "synthetic": false }
```

```json
{ "type": "credential", "id": "cred-...", "capturedAt": "...", "flowId": "flow-...", "sourceIp": "...", "destinationIp": "...", "host": "lab.local", "method": "POST", "path": "/login", "fields": [{ "name": "username", "value": "alice", "category": "user" | "password" | "email" | "token" | "other", "confidence": 0.95 }], "synthetic": false }
```

```json
{ "type": "dns", "id": "dns-...", "capturedAt": "...", "sourceIp": "...", "destinationIp": "...", "query": "example.com", "qtype": "A", "encrypted": false, "synthetic": false }
```

```json
{ "type": "stats", "timestamp": "...", "packets": 120, "flows": 8, "credentials": 1, "dnsQueries": 4, "pps": 12.4, "clients": 1, "queue": 0 }
```

```json
{ "type": "error", "code": "capture_error", "message": "...", "timestamp": "..." }
```

### Reglas del contrato

- Los IDs son deterministas por evento (`flow-<hash>`, `cred-<hash>`) para deduplicar reconexiones.
- `capturedAt` se genera con `time.time_ns()` en el instante de captura.
- El frontend calcula `latencyMs = Date.now() - Date.parse(capturedAt)`; en la misma máquina es fiable. Entre máquinas se documenta el desfase de reloj y se muestra además `emittedAt - capturedAt`.
- Un evento inválido se descarta y se registra en consola; no rompe la UI.

---

## 6. Modelo de grafo

Función pura `buildLabGraph(flows, credentials, maxNodes = 100)`:

- **Nodo:** IP, rol (`local`, `gateway`, `dns`, `remote`), grado, último visto, riesgo, `hasCredential`.
- **Arista:** `sourceIp -> destinationIp`, protocolo, conteo, bytes, último visto, `hasCredential`.
- El nodo local se infiere por IP privada y por ser origen de la mayoría de flujos; el gateway se toma de `/proc/net/route` en Linux o de `ipconfig`/configuración en Windows.
- Se conservan los 100 nodos con actividad más reciente; los demás se evictan.
- Las credenciales marcan la arista y el nodo con alerta roja; el nodo parpadea mientras `now - lastCredentialAt < 10 s`.
- Tests: deduplicación, límite 100, marcado de credencial, evicción.

---

## 7. UI

### Layout

- Header con dos `NuxtLink`: **Defensa** (`/`) y **Laboratorio** (`/laboratorio`).
- En `/laboratorio`, badge de conexión WS (conectado / reconectando / error) y badge fijo **SOLO LABORATORIO**.
- Banner legal permanente: “Captura pasiva únicamente en redes propias o con autorización escrita. Capturar credenciales de terceros puede constituir delito (Ley 1273 de 2009, art. 269C).”

### Pestaña Laboratorio

- **KPI row:** flujos, credenciales, consultas DNS, latencia (ms), FPS, clientes WS.
- **LabGraphCanvas:** canvas con d3-force; nodos por IP, aristas por flujo; rojo y pulso para credenciales; etiquetas para los nodos de mayor grado; zoom/pan opcional.
- **LabCredentialFeed:** lista de credenciales con host, ruta, método, hora y campos completos; botón **Limpiar**; sin exportación.
- **LabDnsFeed:** consultas DNS con qtype y origen.
- **LabFlowTable:** últimos flujos con protocolo, cifrado y riesgo.
- **Estados:** `idle` (sin conexión), `connecting`, `empty` (conectado sin eventos), `error` (con reintento), `paused`.
- **Rendimiento:** simulación y render a 30 Hz; `requestAnimationFrame`; pausa al ocultar la pestaña; FPS medido en ventana de 1 s.
- **Accesibilidad:** `prefers-reduced-motion` desactiva el pulso; textos alternativos; foco visible.

---

## 8. Seguridad y legal

- CLI exige `--i-have-authorization` para captura real. Sin el flag, imprime el aviso legal y termina con código 2.
- `--demo` no toca la red: genera eventos sintéticos marcados `synthetic: true`; la UI muestra “SIMULACIÓN”.
- WS escucha en `127.0.0.1:8765` por defecto. Para LAN: `--host 0.0.0.0 --token <token>` y validación de `Origin`.
- Sin persistencia por defecto. `--log` escribe JSONL redactado; `--log-raw` es explícito y advierte.
- `.gitignore`: `capture/logs/`, `demo/certs/`, `*.pcap`, `.env`.
- No se implementa ARP spoofing, SSL stripping ni ruptura de TLS.
- Las credenciales de la demo son sintéticas (`alice` / `SuperSecret123`), nunca reales.

---

## 9. Rendimiento y métricas

| Requisito | Cómo se cumple | Cómo se verifica |
|---|---|---|
| Latencia < 1.5 s | WS push inmediato; sin polling | `latencyMs` en UI + log de `capturedAt`/`emittedAt` |
| 30 FPS con 100 nodos | d3-force + Canvas, tick a 30 Hz, render acotado | `--demo --nodes 100 --rate 30` + medidor FPS |
| 100 nodos | límite y evicción en `buildLabGraph` | test unitario + demo |
| Captura pasiva | `sniff(promisc=True)` sin inyección | revisión de código + demo HTTP/HTTPS |

---

## 10. Estructura de archivos

```
netsentinel-ids/
├── capture/
│   ├── pyproject.toml
│   ├── README.md
│   ├── lab_capture/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── http_parser.py
│   │   ├── credentials.py
│   │   ├── dns_parser.py
│   │   ├── sniffer.py
│   │   ├── ws_server.py
│   │   └── demo.py
│   └── tests/
│       ├── test_http_parser.py
│       ├── test_credentials.py
│       ├── test_dns_parser.py
│       ├── test_models.py
│       ├── test_sniffer.py
│       ├── test_ws_server.py
│       └── test_demo.py
├── demo/
│   ├── http_login_server.py
│   ├── https_login_server.py
│   ├── login.html
│   ├── generate_cert.py
│   └── README.md
├── pages/
│   ├── index.vue            (Defensa, existente)
│   └── laboratorio.vue      (nuevo)
├── components/lab/
│   ├── LabWarningBanner.vue
│   ├── LabKpiRow.vue
│   ├── LabGraphCanvas.vue
│   ├── LabCredentialFeed.vue
│   ├── LabDnsFeed.vue
│   ├── LabFlowTable.vue
│   └── LabEmptyState.vue
├── composables/useLabSocket.ts
├── stores/lab.store.ts
├── types/lab.ts
├── utils/labGraphModel.ts
├── tests/lab-events.spec.ts
├── tests/lab-graph-model.spec.ts
├── docs/visual-mitm/
│   ├── README.md
│   ├── magerit-v3.md
│   ├── iso-27001-2022.md
│   ├── ley-1273-2009.md
│   ├── demo-http-vs-https.md
│   ├── evidencias.md
│   └── informe-final.md
└── docs/superpowers/...
```

---

## 11. Fases de implementación

1. **Contrato:** `types/lab.ts`, `capture/models.py`, esquemas Zod, modelo de grafo puro.
2. **Parsers Python:** HTTP, credenciales, DNS, tests unitarios.
3. **Captura + WS:** ensamblador TCP, `sniffer.py`, `ws_server.py`, CLI, `--demo`, gates de seguridad.
4. **Frontend:** `lab.store.ts`, `useLabSocket.ts`, `LabGraphCanvas`, componentes, página y pestañas.
5. **Demo HTTP/HTTPS:** servidores locales y certificado autofirmado.
6. **Docs académicos:** MAGERIT v3, ISO 27001:2022, Ley 1273, guion de demo, evidencias, informe.
7. **QA:** pytest + Vitest + build + demo sintética 100 nodos + captura loopback real (si el entorno lo permite).
8. **Revisión de seguridad:** legal, secretos, persistencia, binding, dependencias.

---

## 12. Criterios de aceptación

- [ ] `bun run build` y `bun run test` pasan en el repo.
- [ ] `uv run pytest` pasa en `capture/`.
- [ ] `--demo --nodes 100` dibuja 100 nodos a ≥30 FPS y muestra latencia <1.5 s.
- [ ] Una petición POST HTTP a un servidor local genera un evento `credential` con usuario y contraseña.
- [ ] La misma petición por HTTPS no genera credenciales; solo metadatos TLS.
- [ ] La pestaña Defensa sigue funcionando como antes.
- [ ] El banner legal y el gate `--i-have-authorization` están presentes.
- [ ] No hay credenciales persistidas en el repo ni en logs por defecto.
- [ ] `docs/visual-mitm/` contiene las plantillas y referencias solicitadas.

---

## 13. Riesgos y limitaciones

- **Windows:** Scapy requiere Npcap y una shell de administrador. Sin Npcap no hay captura real; los tests de parsers sí funcionan.
- **Loopback:** Npcap puede requerir el adaptador loopback; si falla, la demo usa LAN/VM.
- **Redes conmutadas/WPA2:** el modo promiscuo no ve tráfico ajeno sin puerto espejo, ARP spoofing (prohibido) o un AP de laboratorio. La demo debe usar tráfico propio o una VM.
- **TCP reassembly:** se implementa un ensamblador acotado; no cubre todos los casos de retransmisión/desorden. Se documenta.
- **Latencia entre máquinas:** el reloj puede desfasarse; la medición fiable es en la misma máquina o con NTP.
- **Certificado HTTPS:** autofirmado; el navegador mostrará advertencia. Es aceptable en laboratorio.
- **Valores completos:** decisión del usuario; se mitiga con banner, limpieza y no persistencia.

---

## 14. Documentos académicos

- `magerit-v3.md`: inventario de activos, matriz amenaza/vulnerabilidad, valoración inherente y residual, salvaguardas. Plantilla basada en MAGERIT v3, no puntuaciones oficiales.
- `iso-27001-2022.md`: correspondencia con Anexo A (A.5.15, A.5.17, A.8.5, A.8.12, A.8.15, A.8.16, A.8.20, A.8.21, A.8.24), con evidencia del proyecto.
- `ley-1273-2009.md`: artículo 269C y delitos relacionados; alcance, autorización y buenas prácticas.
- `demo-http-vs-https.md`: guion paso a paso y resultados esperados.
- `evidencias.md`: checklist de capturas, latencia, FPS, 100 nodos y matriz de riesgos.
- `informe-final.md`: estructura del informe extendido para el Momento 3.

---

## 15. Aprobación

Este diseño requiere aprobación antes de escribir código de producto. Si se aprueba, el siguiente paso es el plan de implementación en `docs/superpowers/plans/2026-10-29-visual-mitm-lab.md`.
